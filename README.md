# Indian Sign Language (ISL) Web Studio (SignSpeak)

A Django-based AI web application that translates English sentences into Indian Sign Language (ISL) video sequences with synchronized real-time MediaPipe skeleton landmark rendering and ML dataset export capabilities.

---

## 🌟 Key Features

- **ISL Translation Engine**: Intelligent grammar reordering (Subject-Object-Verb, time-first, base verbs, letter fingerspelling fallback) powered by Gemini API with rule-based fallback.
- **Automated Video Sourcing & Trimming**: Automatically maps glosses to `NLP_videos.csv` and uses `yt-dlp` to download precise video ranges.
- **Smart Clip Concatenation**: Merges individual word videos into a seamless sentence video using `ffmpeg`.
- **Live Pipeline Terminal**: Server-Sent Events (SSE) streaming real-time status and download progress to the web interface.
- **Synchronized Video & Skeleton Visualizer**: HTML5 Video player paired in real-time with an interactive HTML5 Canvas skeleton visualizer rendering 33 MediaPipe pose landmarks with glowing connections.
- **ML Keypoint Dataset Export**: Download `.mp4` video, compressed `.npz` arrays, tabular `.csv` keypoints, and `.json` trajectories.
- **Searchable Sign Dictionary**: Interactive browser modal to search and inspect all 253 vocabulary signs in the dataset.

---

## 📁 Project Structure

```text
sign-lan/
├── manage.py                     # Django management CLI
├── db.sqlite3                    # SQLite database
├── NLP_videos.csv                # Sign language vocabulary dataset
├── pose_landmarker.task          # MediaPipe pose model
├── isl_engine.py                 # Translation, video processing, & keypoint extraction pipeline
├── requirements.txt              # Python dependencies (Django, OpenCV, MediaPipe, etc.)
│
├── signspeak/                    # Django Project Root
│   ├── __init__.py
│   ├── settings.py               # Django settings (Static, Templates, Apps)
│   ├── urls.py                   # Master URL routing
│   ├── wsgi.py                   # WSGI application entrypoint
│   └── asgi.py                   # ASGI application entrypoint
│
├── translator/                   # Django App
│   ├── __init__.py
│   ├── apps.py
│   ├── models.py
│   ├── urls.py                   # API routes (/api/diagnostics, /api/process, etc.)
│   └── views.py                  # Django views & Server-Sent Events (SSE) streaming
│
├── templates/
│   └── index.html                # Modern glassmorphic web UI
│
├── static/
│   ├── css/
│   │   └── style.css             # Design system & glassmorphic styling
│   ├── js/
│   │   ├── app.js                # UI interactions, API client, & SSE handler
│   │   └── skeleton_player.js    # Canvas 2D skeleton renderer
│   ├── outputs/                  # Per-job generated videos, keypoints, & metadata
│   └── temp_segments/            # Temporary downloaded clip cache
│
├── README.md                     # Project documentation
└── .gitignore                    # Git ignore rules
```

---

## 🛠️ Setup & Running the Project

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run Database Migrations
```bash
python manage.py migrate
```

### 3. Run the Django Server
```bash
python manage.py runserver 8000
```

Open your browser and navigate to:
```
http://127.0.0.1:8000
```
