# AI Gym Monitor

An AI-powered workout tracker that uses real-time pose estimation to count reps, track calories, and give live form feedback — all through your webcam.

## Features

- Real-time pose detection using MediaPipe
- Rep counting for 7 exercises
- Live form feedback (too fast, too slow, perfect)
- Calorie tracking per session
- User profiles with streaks and achievements
- Works as a desktop app (Python) or in the browser (web)

## Exercises supported

- Squats
- Bicep curl
- Pushups
- Overhead tricep extension
- Leg raises
- Lunges
- Jumping jacks

## How to run

### Option 1 — Python desktop app

Install dependencies:
```bash
pip install -r requirements.txt
```

Run:
```bash
python main4.py
```

### Option 2 — Web app (browser)

```bash
python start_server.py
```

Then open your browser and go to:
```
http://localhost:8000/index.html
```

Or on Windows, double-click `start_server.bat`.

## Requirements

- Python 3.9+
- Webcam
- Dependencies listed in `requirements.txt`

## Project structure

```
user_data/          — saved user profiles (JSON)
AIPoseTrainer.jsx   — web frontend component
app.js              — web server logic
index.html          — web UI entry point
main4.py            — Python desktop app
start_server.py     — starts the web server
start_server.bat    — Windows shortcut to start server
requirements.txt    — Python dependencies
```

## Tech stack

- Python, OpenCV, MediaPipe, Tkinter, Pillow
- JavaScript, HTML