# Indian Sign Language (ISL) Web Studio

A Flask-based AI web application that translates English sentences into Indian Sign Language (ISL) video sequences with synchronized real-time MediaPipe skeleton landmark rendering and ML dataset export capabilities.

---

## 🌟 Key Features

- **ISL Translation Engine**: Intelligent grammar reordering (Subject-Object-Verb, time-first, base verbs, letter fingerspelling fallback) powered by Gemini API with rule-based fallback.
- **Automated Video Sourcing & Trimming**: Automatically maps glosses to [NLP_videos.csv](file:///c:/Users/MrHat/OneDrive/Desktop/sign-lan/NLP_videos.csv) and uses `yt-dlp` to download precise video ranges.
- **Smart Clip Concatenation**: Merges individual word videos into a seamless sentence video using `ffmpeg`.
- **Live Pipeline Terminal**: Server-Sent Events (SSE) streaming real-time status and download progress to the web interface.
- **Synchronized Video & Skeleton Visualizer**: HTML5 Video player paired in real-time with an interactive HTML5 Canvas skeleton visualizer rendering 33 MediaPipe pose landmarks with glowing connections.
- **ML Keypoint Dataset Export**: Download `.mp4` video, compressed `.npz` arrays, tabular `.csv` keypoints, and `.json` trajectories.
- **Searchable Sign Dictionary**: Interactive browser modal to search and inspect all 253 vocabulary signs in the dataset.

---

## 📁 Project Structure

```
sign-lan/
├── app.py                     # Flask web server & REST/SSE API endpoints
├── isl_engine.py              # Translation, video processing, & keypoint extraction pipeline
├── requirements.txt           # Python dependencies
├── NLP_videos.csv             # Sign language vocabulary dataset
├── pose_landmarker.task       # MediaPipe pose model
├── templates/
│   └── index.html             # Single-page modern glassmorphic web UI
├── static/
│   ├── css/
│   │   └── style.css          # Design system & glassmorphic styling
│   ├── js/
│   │   ├── app.js             # UI interactions, API client, & SSE handler
│   │   └── skeleton_player.js # Canvas 2D skeleton renderer
│   ├── outputs/               # Per-job generated videos, keypoints, & metadata
│   └── temp_segments/         # Temporary downloaded clip cache
├── README.md                  # Project documentation
└── .gitignore                 # Git ignore rules
```

---

## 🛠️ Setup & Running the Project

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Verify FFmpeg
FFmpeg is required for video extraction and concatenation. Ensure it is available on your PATH:
```bash
ffmpeg -version
```

### 3. Run the Web Application
```bash
python app.py
```
Open your browser and navigate to:
```
http://localhost:5000
```
