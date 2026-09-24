"""
Indian Sign Language (ISL) Translation & Video Processing Engine.
Provides modular pipeline for translation, segment downloading, keypoint extraction,
video concatenation, and frame-by-frame skeleton data generation.
"""

import os
import csv
import glob
import json
import time
import shutil
import subprocess
import urllib.request
from typing import Dict, List, Tuple, Optional, Callable

import cv2
import numpy as np
from yt_dlp import YoutubeDL
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
import nltk

# Initialize NLTK resources
nltk.download('punkt', quiet=True)
nltk.download('punkt_tab', quiet=True)
nltk.download('stopwords', quiet=True)

try:
    stop_words = set(stopwords.words('english'))
except Exception:
    stop_words = set()

DATASET_PATH = 'NLP_videos.csv'
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_OUTPUTS_DIR = os.path.join(BASE_DIR, 'static', 'outputs')
TEMP_SEGMENTS_DIR = os.path.join(BASE_DIR, 'static', 'temp_segments')

os.makedirs(STATIC_OUTPUTS_DIR, exist_ok=True)
os.makedirs(TEMP_SEGMENTS_DIR, exist_ok=True)

NUM_POSE = 33
NUM_FACE = 468
NUM_HAND = 21

POSE_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 7),
    (0, 4), (4, 5), (5, 6), (6, 8),
    (9, 10),
    (11, 12), (11, 23), (12, 24), (23, 24),
    (11, 13), (13, 15), (15, 17), (15, 19), (15, 21), (17, 19),
    (12, 14), (14, 16), (16, 18), (16, 20), (16, 22), (18, 20),
    (23, 25), (25, 27), (27, 29), (27, 31), (29, 31),
    (24, 26), (26, 28), (28, 30), (28, 32), (30, 32)
]

MODEL_URL = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_full/float16/1/pose_landmarker_full.task"
MODEL_PATH = os.path.join(BASE_DIR, "pose_landmarker.task")

GEMINI_API_KEY = "AQ.Ab8RN6IM_PcTUdy0sQjPb6XqiD2jbJ3Glj_VfssQTAh9T0kZIA"
GEMINI_MODEL = "gemini-3.6-flash"


def load_dataset(path: str = DATASET_PATH) -> Dict[str, Dict]:
    """Load the CSV dataset into a dict keyed by stripped, lowercased word."""
    full_path = os.path.join(BASE_DIR, path) if not os.path.isabs(path) else path
    lookup = {}
    if not os.path.exists(full_path):
        return lookup
    with open(full_path, 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            key = row['Name'].strip().lower()
            if key:
                lookup[key] = row
    return lookup


def get_all_vocabulary(path: str = DATASET_PATH) -> List[Dict]:
    """Return all available vocabulary items with metadata."""
    lookup = load_dataset(path)
    items = []
    for word, row in lookup.items():
        items.append({
            'word': word,
            'yt_name': row.get('yt_name', ''),
            'link': row.get('Link', ''),
            'start': f"{int(row.get('start_min', 0)):02d}:{int(row.get('start_sec', 0)):02d}",
            'end': f"{int(row.get('end_min', 0)):02d}:{int(row.get('end_sec', 0)):02d}"
        })
    items.sort(key=lambda x: x['word'])
    return items


def convert_to_isl_local(text: str, data_lookup: Optional[Dict] = None) -> str:
    """Robust local rule-based ISL reordering with vocabulary mapping fallback."""
    if not data_lookup:
        data_lookup = load_dataset()

    tokens = word_tokenize(text.lower())
    mapped_tokens = []
    for t in tokens:
        if t.isalnum():
            resolved = resolve_word(t, data_lookup)
            if resolved:
                mapped_tokens.extend(resolved)
            elif t in data_lookup:
                mapped_tokens.append(t)

    # Reorder Subject-Object-Verb if at least 3 tokens
    if len(mapped_tokens) >= 3:
        subject = mapped_tokens[0]
        obj = " ".join(mapped_tokens[1:-1])
        verb = mapped_tokens[-1]
        return f"{subject} {obj} {verb}".strip()

    if mapped_tokens:
        return " ".join(mapped_tokens)

    # Default fallback for unmapped input
    return "welcome"


def convert_to_isl(text: str, data_lookup: Optional[Dict] = None) -> str:
    """Convert an English sentence to ISL using Gemini API, falling back to local grammar rules."""
    if not data_lookup:
        data_lookup = load_dataset()

    vocab = list(data_lookup.keys())

    try:
        from google import genai
    except ImportError:
        return convert_to_isl_local(text, data_lookup)

    prompt = f"""
Convert the following English sentence into Indian Sign Language (ISL) glosses/words:
"{text}"

Follow these rules for the translation:
1. Translate to ISL grammar (typically Subject-Object-Verb order).
2. Place time words (e.g. tomorrow, yesterday, morning, evening, Sunday, etc.) at the beginning.
3. Place question words (e.g. what, who, why, where, how) at the end. Note: if "how" or "what" is used, map to "which" if present in vocabulary.
4. Use verbs in their base form (e.g. use "work" instead of "working" or "works", "eat" instead of "eating", "go" instead of "going").
5. Omit articles (a, an, the) and helping/auxiliary verbs (is, am, are, was, were, has, have, do, did, to).
6. Map pronouns to available vocabulary: map "you" to "your", "me" to "i", "him" to "he", "her" to "she".
7. For greetings like "how are you", "hello", "hi", output "your welcome" or "welcome".
8. Use ONLY words from the allowed vocabulary list below. Do NOT output empty text or single letters.

Allowed vocabulary list:
{", ".join(vocab)}

Provide ONLY the space-separated ISL words as output. Do not include any explanations, introduction, punctuation, single alphabet letters, or other text.
"""
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        models_to_try = [GEMINI_MODEL, "gemini-1.5-flash", "gemini-2.0-flash"]
        for model_name in models_to_try:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt
                )
                result = response.text.strip()
                if result:
                    result = result.replace('`', '').replace('"', '').replace("'", '').strip()
                    if result:
                        return result
            except Exception:
                continue
    except Exception:
        pass

    return convert_to_isl_local(text, data_lookup)


def get_ffmpeg_location() -> Optional[str]:
    """Return the ffmpeg executable path across Windows and Linux (PythonAnywhere)."""
    env_path = os.environ.get('FFMPEG_PATH')
    if env_path and os.path.isfile(env_path):
        return env_path

    ffmpeg_path = shutil.which('ffmpeg')
    if ffmpeg_path:
        return ffmpeg_path

    # Check Linux / PythonAnywhere standard paths
    linux_paths = [
        '/usr/bin/ffmpeg',
        '/usr/local/bin/ffmpeg',
        os.path.expanduser('~/.local/bin/ffmpeg'),
        os.path.expanduser('~/bin/ffmpeg'),
    ]
    for path in linux_paths:
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path

    # Check Windows paths
    windows_paths = [
        os.path.expandvars(r'%ProgramFiles%\\ffmpeg\\bin\\ffmpeg.exe'),
        os.path.expandvars(r'%ProgramFiles(x86)%\\ffmpeg\\bin\\ffmpeg.exe'),
        os.path.expandvars(r'%LocalAppData%\\Programs\\ffmpeg\\bin\\ffmpeg.exe'),
        os.path.expanduser(r'~\\scoop\\apps\\ffmpeg\\current\\bin\\ffmpeg.exe'),
        os.path.expanduser(r'~\\AppData\\Local\\Microsoft\\WindowsApps\\ffmpeg.exe'),
        r'C:\Users\MrHat\Downloads\ffmpeg-master-latest-win64-gpl-shared\ffmpeg-master-latest-win64-gpl-shared\bin\ffmpeg.EXE'
    ]
    for path in windows_paths:
        if os.path.isfile(path):
            return path

    # Try imageio_ffmpeg if installed
    try:
        import importlib
        imageio_ffmpeg = importlib.import_module("imageio_ffmpeg")
        candidate = getattr(imageio_ffmpeg, "get_ffmpeg_exe", lambda: None)()
        if candidate and os.path.isfile(candidate):
            return candidate
    except Exception:
        pass

    return None


def ensure_model_exists():
    """Ensure the MediaPipe Pose Landmarker model exists locally."""
    if not os.path.exists(MODEL_PATH):
        try:
            urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
        except Exception as e:
            raise RuntimeError(f"Failed to download MediaPipe model: {e}")


def download_video_segment(video_url: str, start_min: int, start_sec: int,
                           end_min: int, end_sec: int, output_name: str,
                           output_dir: str, ffmpeg_path: str) -> str:
    """Download only the requested segment of a video with robust format handling."""
    start_time = start_min * 60 + start_sec
    end_time = end_min * 60 + end_sec
    output_path = os.path.join(output_dir, f'{output_name}.mp4')

    if os.path.exists(output_path) and os.path.getsize(output_path) > 1024:
        return output_path

    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/bestvideo/best[ext=mp4]/best',
        'outtmpl': output_path,
        'download_ranges': lambda info, ydl_: [{'start_time': start_time, 'end_time': end_time}],
        'force_keyframes_at_cuts': True,
        'quiet': True,
        'no_warnings': True,
        'merge_output_format': 'mp4',
        'ffmpeg_location': os.path.dirname(ffmpeg_path),
    }
    with YoutubeDL(ydl_opts) as ydl:
        ydl.download([video_url])

    if not os.path.exists(output_path):
        raise RuntimeError(f"Download did not produce expected file: {output_path}")
    return output_path


def concat_videos(video_files: List[str], output_file: str, ffmpeg_path: Optional[str] = None) -> str:
    """Concatenate video clips into a single video file."""
    list_dir = os.path.dirname(output_file)
    file_list = os.path.join(list_dir, f"file_list_{int(time.time()*1000)}.txt")
    with open(file_list, "w", encoding="utf-8") as f:
        for video in video_files:
            f.write(f"file '{os.path.abspath(video)}'\n")

    ffmpeg_bin = ffmpeg_path or shutil.which('ffmpeg') or 'ffmpeg'

    try:
        # First attempt: fast stream copy
        cmd = [
            ffmpeg_bin, "-y", "-f", "concat", "-safe", "0", "-i", file_list,
            "-c", "copy", output_file
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0 or not os.path.exists(output_file):
            raise RuntimeError(result.stderr)
    except Exception:
        # Fallback: re-encode to unified H.264 / AAC
        cmd = [
            ffmpeg_bin, "-y", "-f", "concat", "-safe", "0", "-i", file_list,
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-movflags", "+faststart", output_file
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0 or not os.path.exists(output_file):
            raise RuntimeError(f"FFmpeg concat failed: {result.stderr}")
    finally:
        if os.path.exists(file_list):
            try:
                os.remove(file_list)
            except OSError:
                pass

    return output_file


def _keypoints_csv_header() -> List[str]:
    header = ['frame']
    header += [f'pose_{i}_{axis}' for i in range(NUM_POSE) for axis in ('x', 'y', 'z', 'v')]
    header += [f'face_{i}_{axis}' for i in range(NUM_FACE) for axis in ('x', 'y', 'z')]
    header += [f'lh_{i}_{axis}' for i in range(NUM_HAND) for axis in ('x', 'y', 'z')]
    header += [f'rh_{i}_{axis}' for i in range(NUM_HAND) for axis in ('x', 'y', 'z')]
    return header


def save_keypoints_csv(csv_path: str, pose_arr: np.ndarray, face_arr: np.ndarray, lh_arr: np.ndarray, rh_arr: np.ndarray):
    """Save keypoints array to a formatted CSV."""
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(_keypoints_csv_header())
        for i in range(pose_arr.shape[0]):
            row = [i]
            row.extend(pose_arr[i].tolist())
            row.extend(face_arr[i].tolist())
            row.extend(lh_arr[i].tolist())
            row.extend(rh_arr[i].tolist())
            writer.writerow(row)


def extract_keypoints_and_export(video_path: str, output_basepath: str) -> Tuple[str, str, Dict]:
    """
    Extract pose landmarks from video and export .npz, .csv, and lightweight .json for web playback.
    """
    ensure_model_exists()
    
    from mediapipe.tasks import python
    from mediapipe.tasks.python import vision
    import mediapipe as mp

    base_options = python.BaseOptions(model_asset_path=MODEL_PATH)
    options = vision.PoseLandmarkerOptions(
        base_options=base_options,
        running_mode=vision.RunningMode.VIDEO
    )

    pose_frames, face_frames, lh_frames, rh_frames = [], [], [], []
    json_timeline = []

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        fps = 30.0

    frame_idx = 0
    last_timestamp_ms = -1

    with vision.PoseLandmarker.create_from_options(options) as landmarker:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            timestamp_ms = int(frame_idx * 1000 / fps)
            if timestamp_ms <= last_timestamp_ms:
                timestamp_ms = last_timestamp_ms + 1
            last_timestamp_ms = timestamp_ms

            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
            results = landmarker.detect_for_video(mp_image, timestamp_ms)

            pose_flat = []
            pose_points_json = []

            if results and results.pose_landmarks and len(results.pose_landmarks) > 0:
                landmarks = results.pose_landmarks[0]
                for lm in landmarks:
                    x = round(float(lm.x), 4)
                    y = round(float(lm.y), 4)
                    z = round(float(lm.z), 4)
                    v = round(float(getattr(lm, 'visibility', 1.0)), 3)
                    pose_flat.extend([x, y, z, v])
                    pose_points_json.append({"x": x, "y": y, "z": z, "v": v})
            else:
                pose_flat = [0.0] * (NUM_POSE * 4)
                pose_points_json = [{"x": 0.0, "y": 0.0, "z": 0.0, "v": 0.0} for _ in range(NUM_POSE)]

            pose_frames.append(np.array(pose_flat, dtype=np.float32))
            face_frames.append(np.zeros(NUM_FACE * 3, dtype=np.float32))
            lh_frames.append(np.zeros(NUM_HAND * 3, dtype=np.float32))
            rh_frames.append(np.zeros(NUM_HAND * 3, dtype=np.float32))

            json_timeline.append({
                "frame": frame_idx,
                "time_ms": timestamp_ms,
                "landmarks": pose_points_json
            })
            frame_idx += 1

    cap.release()

    if not pose_frames:
        raise RuntimeError(f"No frames could be extracted from {video_path}")

    pose_arr = np.stack(pose_frames)
    face_arr = np.stack(face_frames)
    lh_arr = np.stack(lh_frames)
    rh_arr = np.stack(rh_frames)

    npz_path = f"{output_basepath}.npz"
    csv_path = f"{output_basepath}.csv"
    json_path = f"{output_basepath}.json"

    np.savez_compressed(
        npz_path,
        pose=pose_arr, face=face_arr, left_hand=lh_arr, right_hand=rh_arr
    )
    save_keypoints_csv(csv_path, pose_arr, face_arr, lh_arr, rh_arr)

    keypoint_data = {
        "fps": fps,
        "total_frames": frame_idx,
        "timeline": json_timeline,
        "connections": POSE_CONNECTIONS
    }

    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(keypoint_data, f)

    return npz_path, csv_path, keypoint_data


def resolve_word(word: str, data_lookup: Dict[str, Dict]) -> List[str]:
    """
    Resolve a word to a full vocabulary sign, its base lemma, or a mapped synonym.
    Only returns valid words present in data_lookup.
    """
    clean = word.lower().strip()
    if not clean:
        return []
    if clean in data_lookup:
        return [clean]

    # Lemmatization heuristics for common English verb/noun inflections
    if clean.endswith('ing') and clean[:-3] in data_lookup:
        return [clean[:-3]]
    if clean.endswith('ing') and (clean[:-3] + 'e') in data_lookup:
        return [clean[:-3] + 'e']
    if clean.endswith('s') and clean[:-1] in data_lookup:
        return [clean[:-1]]
    if clean.endswith('es') and clean[:-2] in data_lookup:
        return [clean[:-2]]
    if clean.endswith('ed') and clean[:-2] in data_lookup:
        return [clean[:-2]]
    if clean.endswith('ed') and clean[:-1] in data_lookup:
        return [clean[:-1]]

    # Common synonyms/greetings/pronouns/questions to vocabulary words
    synonyms = {
        'hi': ['welcome'],
        'hello': ['welcome'],
        'hey': ['welcome'],
        'greetings': ['welcome'],
        'thanks': ['welcome'],
        'thank': ['welcome'],
        'you': ['your'],
        'your': ['your'],
        'yours': ['your'],
        'me': ['i'],
        'my': ['my'],
        'myself': ['i'],
        'him': ['he'],
        'his': ['his'],
        'her': ['her'],
        'hers': ['her'],
        'how': ['which'],
        'what': ['which'],
        'where': ['which'],
        'who': ['which'],
        'why': ['which'],
        'good': ['welcome'],
        'fine': ['welcome'],
        'going': ['go'],
        'eats': ['eat'],
        'eating': ['eat'],
        'ate': ['eat'],
        'went': ['go'],
        'sees': ['watch'],
        'seen': ['watch'],
        'watching': ['watch'],
        'dad': ['father'],
        'mom': ['mother'],
        'automobile': ['car'],
        'vehicle': ['car'],
        'now': ['time']
    }
    if clean in synonyms:
        for syn in synonyms[clean]:
            if syn in data_lookup:
                return [syn]

    return []


def process_isl_job(job_id: str, input_text: str, progress_callback: Optional[Callable[[str, int, str], None]] = None) -> Dict:
    """
    Execute full pipeline for a job:
    1. Grammar Translation to ISL glosses
    2. Segment download per word
    3. Keypoint extraction
    4. Concat to final video
    5. Output bundle creation
    """
    def log(message: str, step: int, status: str = "running"):
        if progress_callback:
            progress_callback(message, step, status)

    job_dir = os.path.join(STATIC_OUTPUTS_DIR, job_id)
    os.makedirs(job_dir, exist_ok=True)

    ffmpeg_path = get_ffmpeg_location()
    if not ffmpeg_path:
        raise RuntimeError("FFmpeg executable was not found on your system.")

    data_lookup = load_dataset()

    log(f"Translating sentence '{input_text}' to ISL grammar...", 10)
    isl_text = convert_to_isl(input_text, data_lookup)
    log(f"ISL Syntax determined: '{isl_text}'", 20)

    raw_words = isl_text.split() if isl_text else []

    # Expand words with lemmatization & synonyms
    resolved_tokens = []
    for w in raw_words:
        tokens = resolve_word(w, data_lookup)
        resolved_tokens.extend(tokens)

    # Fallback if no direct words resolved
    if not resolved_tokens:
        for w in input_text.split():
            tokens = resolve_word(w, data_lookup)
            resolved_tokens.extend(tokens)

    if not resolved_tokens:
        resolved_tokens = ['welcome']
        log("No direct vocabulary match found, playing conversational sign 'welcome'", 25)

    video_files = []
    word_sequence = []
    missing_words = []
    downloaded_cache = {}

    total_words = len(resolved_tokens)
    for idx, token in enumerate(resolved_tokens):
        progress_pct = 25 + int((idx / max(1, total_words)) * 40)
        
        if token in downloaded_cache:
            video_files.append(downloaded_cache[token])
            word_sequence.append(token)
            log(f"Using cached clip for '{token}'", progress_pct)
            continue

        info = data_lookup.get(token.lower().strip())
        if not info:
            log(f"Word '{token}' not found in vocabulary. Skipping.", progress_pct)
            missing_words.append(token)
            continue

        log(f"Downloading clip for '{token}' ({info.get('yt_name', '')})...", progress_pct)
        try:
            clip_path = download_video_segment(
                info['Link'],
                int(info['start_min']), int(info['start_sec']),
                int(info['end_min']), int(info['end_sec']),
                f"clip_{token}",
                TEMP_SEGMENTS_DIR,
                ffmpeg_path=ffmpeg_path
            )
            downloaded_cache[token] = clip_path
            video_files.append(clip_path)
            word_sequence.append(token)
        except Exception as e:
            log(f"Failed downloading '{token}': {e}", progress_pct)
            missing_words.append(token)

    if not video_files:
        raise RuntimeError("No sign videos could be retrieved for this sentence.")

    log("Concatenating video segments...", 70)
    final_video_name = f"final_isl_{job_id}.mp4"
    final_video_path = os.path.join(job_dir, final_video_name)
    concat_videos(video_files, final_video_path, ffmpeg_path=ffmpeg_path)

    # Compute word subtitle durations
    word_durations = []
    current_time_ms = 0.0
    for word, path in zip(word_sequence, video_files):
        cap = cv2.VideoCapture(path)
        if cap.isOpened():
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
            dur_ms = (frame_count * 1000.0) / fps if fps > 0 and frame_count > 0 else 1000.0
            cap.release()
        else:
            dur_ms = 1000.0
        word_durations.append({
            "word": word,
            "start_ms": round(current_time_ms, 1),
            "end_ms": round(current_time_ms + dur_ms, 1),
            "duration_ms": round(dur_ms, 1)
        })
        current_time_ms += dur_ms

    log("Extracting MediaPipe Pose landmarks & skeleton data...", 85)
    final_basepath = os.path.join(job_dir, "final_keypoints")
    npz_path, csv_path, keypoint_data = extract_keypoints_and_export(final_video_path, final_basepath)

    # Save job metadata JSON
    result_meta = {
        "job_id": job_id,
        "original_text": input_text,
        "isl_text": isl_text,
        "words": word_sequence,
        "missing_words": missing_words,
        "word_durations": word_durations,
        "total_duration_ms": current_time_ms,
        "video_url": f"/static/outputs/{job_id}/{final_video_name}",
        "npz_url": f"/static/outputs/{job_id}/final_keypoints.npz",
        "csv_url": f"/static/outputs/{job_id}/final_keypoints.csv",
        "json_url": f"/static/outputs/{job_id}/final_keypoints.json",
        "total_frames": keypoint_data.get("total_frames", 0),
        "fps": keypoint_data.get("fps", 30.0)
    }

    meta_file = os.path.join(job_dir, "meta.json")
    with open(meta_file, "w", encoding="utf-8") as f:
        json.dump(result_meta, f, indent=2)

    log("Pipeline completed successfully! Ready to play.", 100, status="completed")
    return result_meta
