"""
Django Views for Indian Sign Language (ISL) Translator & Keypoints Engine.
"""

import os
import uuid
import time
import json
import queue
import threading
from typing import Dict, Any

from django.shortcuts import render
from django.http import (
    JsonResponse,
    StreamingHttpResponse,
    FileResponse,
    HttpResponseNotFound,
    HttpResponseBadRequest,
)
from django.views.decorators.csrf import csrf_exempt

import isl_engine

# In-memory job state tracking
jobs: Dict[str, Dict[str, Any]] = {}
job_event_queues: Dict[str, list] = {}
jobs_lock = threading.Lock()


def index(request):
    """Render main application interface."""
    return render(request, 'index.html')


def diagnostics(request):
    """Return health check and subsystem status."""
    ffmpeg_loc = isl_engine.get_ffmpeg_location()
    dataset = isl_engine.load_dataset()
    model_cached = os.path.exists(isl_engine.MODEL_PATH)
    
    return JsonResponse({
        "status": "healthy",
        "ffmpeg": {
            "available": ffmpeg_loc is not None,
            "path": ffmpeg_loc
        },
        "dataset": {
            "count": len(dataset),
            "loaded": len(dataset) > 0
        },
        "mediapipe_model": {
            "cached": model_cached
        }
    })


def vocabulary(request):
    """Return all dataset vocabulary items with metadata."""
    items = isl_engine.get_all_vocabulary()
    return JsonResponse({
        "total": len(items),
        "items": items
    })


@csrf_exempt
def quick_translate(request):
    """Quick preview of ISL syntax reordering without video generation."""
    if request.method != 'POST':
        return HttpResponseBadRequest("POST required")

    try:
        data = json.loads(request.body.decode('utf-8')) if request.body else {}
    except Exception:
        data = {}

    text = data.get('text', '').strip()
    if not text:
        return JsonResponse({"error": "No text provided"}, status=400)

    data_lookup = isl_engine.load_dataset()
    isl_text = isl_engine.convert_to_isl(text, data_lookup)
    raw_words = isl_text.split()

    annotated_words = []
    for w in raw_words:
        tokens = isl_engine.resolve_word(w, data_lookup)
        for token in tokens:
            clean_w = token.lower().strip()
            in_vocab = clean_w in data_lookup
            annotated_words.append({
                "word": token,
                "in_vocab": in_vocab
            })

    return JsonResponse({
        "original_text": text,
        "isl_text": isl_text,
        "words": annotated_words
    })


def run_pipeline_thread(job_id: str, input_text: str):
    """Background worker executing the job pipeline and pushing events."""
    def progress_callback(message: str, step: int, status: str = "running"):
        event = {
            "job_id": job_id,
            "message": message,
            "progress": step,
            "status": status,
            "timestamp": time.time()
        }
        with jobs_lock:
            if job_id in jobs:
                jobs[job_id]["progress"] = step
                jobs[job_id]["status"] = status
                jobs[job_id]["last_message"] = message
                jobs[job_id]["logs"].append(event)
            if job_id in job_event_queues:
                for q in job_event_queues[job_id]:
                    q.put(event)

    try:
        result = isl_engine.process_isl_job(job_id, input_text, progress_callback=progress_callback)
        with jobs_lock:
            if job_id in jobs:
                jobs[job_id]["result"] = result
                jobs[job_id]["status"] = "completed"
    except Exception as e:
        error_event = {
            "job_id": job_id,
            "message": f"Error: {str(e)}",
            "progress": 100,
            "status": "failed",
            "error": str(e),
            "timestamp": time.time()
        }
        with jobs_lock:
            if job_id in jobs:
                jobs[job_id]["status"] = "failed"
                jobs[job_id]["error"] = str(e)
                jobs[job_id]["logs"].append(error_event)
            if job_id in job_event_queues:
                for q in job_event_queues[job_id]:
                    q.put(error_event)


@csrf_exempt
def process_job(request):
    """Initiate a video generation and keypoint processing job."""
    if request.method != 'POST':
        return HttpResponseBadRequest("POST required")

    try:
        data = json.loads(request.body.decode('utf-8')) if request.body else {}
    except Exception:
        data = {}

    text = data.get('text', '').strip()
    if not text:
        return JsonResponse({"error": "Please enter an English sentence."}, status=400)

    job_id = str(uuid.uuid4())[:8]
    job_info = {
        "job_id": job_id,
        "input_text": text,
        "status": "pending",
        "progress": 0,
        "last_message": "Job queued...",
        "logs": [],
        "created_at": time.time(),
        "result": None,
        "error": None
    }

    with jobs_lock:
        jobs[job_id] = job_info
        job_event_queues[job_id] = []

    worker = threading.Thread(target=run_pipeline_thread, args=(job_id, text), daemon=True)
    worker.start()

    return JsonResponse({
        "job_id": job_id,
        "status": "started",
        "stream_url": f"/api/stream/{job_id}",
        "result_url": f"/api/result/{job_id}"
    })


def stream_events(request, job_id):
    """Server-Sent Events (SSE) endpoint to stream real-time logs."""
    def event_generator():
        q = queue.Queue()
        with jobs_lock:
            if job_id not in jobs:
                yield f"data: {json.dumps({'error': 'Job not found', 'status': 'failed'})}\n\n"
                return
            
            # Send current logs history
            for log in jobs[job_id]["logs"]:
                yield f"data: {json.dumps(log)}\n\n"

            # Register queue for new events
            if jobs[job_id]["status"] in ["completed", "failed"]:
                return
            job_event_queues[job_id].append(q)

        try:
            while True:
                try:
                    event = q.get(timeout=25.0)
                    yield f"data: {json.dumps(event)}\n\n"
                    if event.get("status") in ["completed", "failed"]:
                        break
                except queue.Empty:
                    # Heartbeat
                    yield f": heartbeat\n\n"
        finally:
            with jobs_lock:
                if job_id in job_event_queues and q in job_event_queues[job_id]:
                    job_event_queues[job_id].remove(q)

    response = StreamingHttpResponse(event_generator(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response


def job_result(request, job_id):
    """Get the completed results and metadata for a job."""
    with jobs_lock:
        job = jobs.get(job_id)
        if not job:
            meta_path = os.path.join(isl_engine.STATIC_OUTPUTS_DIR, job_id, "meta.json")
            if os.path.exists(meta_path):
                with open(meta_path, "r", encoding="utf-8") as f:
                    return JsonResponse({"job_id": job_id, "status": "completed", "result": json.load(f)})
            return JsonResponse({"error": "Job not found"}, status=404)

        return JsonResponse({
            "job_id": job_id,
            "status": job["status"],
            "progress": job["progress"],
            "result": job["result"],
            "error": job["error"]
        })


def poll_status(request, job_id):
    """Fallback polling endpoint for platforms where SSE might be buffered."""
    with jobs_lock:
        job = jobs.get(job_id)
        if not job:
            meta_path = os.path.join(isl_engine.STATIC_OUTPUTS_DIR, job_id, "meta.json")
            if os.path.exists(meta_path):
                with open(meta_path, "r", encoding="utf-8") as f:
                    return JsonResponse({"job_id": job_id, "status": "completed", "progress": 100, "result": json.load(f), "logs": []})
            return JsonResponse({"error": "Job not found"}, status=404)

        return JsonResponse({
            "job_id": job_id,
            "status": job["status"],
            "progress": job["progress"],
            "last_message": job.get("last_message", ""),
            "logs": job.get("logs", []),
            "result": job.get("result"),
            "error": job.get("error")
        })


def keypoints_json(request, job_id):
    """Return JSON keypoints animation timeline."""
    json_path = os.path.join(isl_engine.STATIC_OUTPUTS_DIR, job_id, "final_keypoints.json")
    if not os.path.exists(json_path):
        return JsonResponse({"error": "Keypoints not found"}, status=404)
    with open(json_path, "r", encoding="utf-8") as f:
        return JsonResponse(json.load(f))


def serve_output_file(request, job_id, filename):
    """Serve generated output files (videos, npz, csv) with correct MIME types."""
    output_dir = os.path.join(isl_engine.STATIC_OUTPUTS_DIR, job_id)
    file_path = os.path.join(output_dir, filename)
    if not os.path.exists(file_path):
        return HttpResponseNotFound("File not found")

    content_type = 'application/octet-stream'
    if filename.endswith('.mp4'):
        content_type = 'video/mp4'
    elif filename.endswith('.json'):
        content_type = 'application/json'
    elif filename.endswith('.csv'):
        content_type = 'text/csv'
    elif filename.endswith('.npz'):
        content_type = 'application/octet-stream'

    return FileResponse(open(file_path, 'rb'), content_type=content_type)
