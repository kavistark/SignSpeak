"""
Flask Web Application for Indian Sign Language (ISL) Translator & Keypoints Engine.
"""

import os
import uuid
import time
import json
import queue
import threading
from typing import Dict, Any

from flask import Flask, render_template, request, jsonify, Response, send_file, url_for
from flask_cors import CORS

import isl_engine

app = Flask(__name__)
CORS(app)

# In-memory job state tracking
jobs: Dict[str, Dict[str, Any]] = {}
job_event_queues: Dict[str, list] = {}
jobs_lock = threading.Lock()


@app.route('/')
def index():
    """Render main application interface."""
    return render_template('index.html')


@app.route('/api/diagnostics', methods=['GET'])
def diagnostics():
    """Return health check and subsystem status."""
    ffmpeg_loc = isl_engine.get_ffmpeg_location()
    dataset = isl_engine.load_dataset()
    model_cached = os.path.exists(isl_engine.MODEL_PATH)
    
    return jsonify({
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


@app.route('/api/vocabulary', methods=['GET'])
def vocabulary():
    """Return all 253 dataset vocabulary items with metadata."""
    items = isl_engine.get_all_vocabulary()
    return jsonify({
        "total": len(items),
        "items": items
    })


@app.route('/api/translate', methods=['POST'])
def quick_translate():
    """Quick preview of ISL syntax reordering without video generation."""
    data = request.get_json(force=True, silent=True) or {}
    text = data.get('text', '').strip()
    if not text:
        return jsonify({"error": "No text provided"}), 400

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

    return jsonify({
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


@app.route('/api/process', methods=['POST'])
def process():
    """Initiate a video generation and keypoint processing job."""
    data = request.get_json(force=True, silent=True) or {}
    text = data.get('text', '').strip()
    if not text:
        return jsonify({"error": "Please enter an English sentence."}), 400

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

    return jsonify({
        "job_id": job_id,
        "status": "started",
        "stream_url": f"/api/stream/{job_id}",
        "result_url": f"/api/result/{job_id}"
    })


@app.route('/api/stream/<job_id>')
def stream(job_id):
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

    return Response(event_generator(), mimetype='text/event-stream', headers={
        'Cache-Control': 'no-cache',
        'X-Accel-Buffering': 'no'
    })


@app.route('/api/result/<job_id>', methods=['GET'])
def result(job_id):
    """Get the completed results and metadata for a job."""
    with jobs_lock:
        job = jobs.get(job_id)
        if not job:
            meta_path = os.path.join(isl_engine.STATIC_OUTPUTS_DIR, job_id, "meta.json")
            if os.path.exists(meta_path):
                with open(meta_path, "r", encoding="utf-8") as f:
                    return jsonify({"job_id": job_id, "status": "completed", "result": json.load(f)})
            return jsonify({"error": "Job not found"}), 404

        return jsonify({
            "job_id": job_id,
            "status": job["status"],
            "progress": job["progress"],
            "result": job["result"],
            "error": job["error"]
        })


@app.route('/api/keypoints/<job_id>', methods=['GET'])
def keypoints_json(job_id):
    """Return JSON keypoints animation timeline."""
    json_path = os.path.join(isl_engine.STATIC_OUTPUTS_DIR, job_id, "final_keypoints.json")
    if not os.path.exists(json_path):
        return jsonify({"error": "Keypoints not found"}), 404
    with open(json_path, "r", encoding="utf-8") as f:
        return jsonify(json.load(f))


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"Starting ISL Web Server on http://localhost:{port} ...")
    app.run(host='0.0.0.0', port=port, debug=False)
