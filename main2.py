#!/usr/bin/env python3
"""
AI Pose Trainer - Front View Optimized (Balanced Font Edition)
"""

import cv2
import mediapipe as mp
import numpy as np
import math
import os
import warnings
import tkinter as tk
from PIL import Image, ImageTk
from collections import deque
import time

# Suppress logs
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
warnings.filterwarnings("ignore")

# ---------- CONFIG ----------
mp_drawing = mp.solutions.drawing_utils
mp_pose = mp.solutions.pose
L = mp_pose.PoseLandmark
COLORS = {"bg": "#101010", "accent": "#ff007f", "text": "#ffffff"}
ANGLE_SMOOTH = 5
FEEDBACK_DURATION = 2  # seconds after each rep to display feedback
# ----------------------------

def angle(a, b, c):
    """Return angle (in degrees) between points a-b-c."""
    a, b, c = np.array(a), np.array(b), np.array(c)
    ba, bc = a - b, c - b
    denom = np.linalg.norm(ba) * np.linalg.norm(bc)
    if denom == 0:
        return 0.0
    cosang = np.clip(np.dot(ba, bc) / denom, -1.0, 1.0)
    return float(math.degrees(math.acos(cosang)))

def smooth(dq, val):
    dq.append(val)
    if len(dq) > ANGLE_SMOOTH:
        dq.popleft()
    return float(np.mean(dq))

class PoseTrainerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("🏋️ AI Pose Trainer - Front View Edition")
        self.root.geometry("1280x900")
        self.root.configure(bg=COLORS["bg"])

        self.cap = None
        self.pose = None
        self.exercise = None
        self.rep_count = 0
        self.angle_buf = deque()
        self.prev_state = None
        self.running = False
        self.last_rep_time = 0
        self.feedback_text = ""
        self.feedback_time = 0

        self.build_main_menu()

    def build_main_menu(self):
        for widget in self.root.winfo_children():
            widget.destroy()

        tk.Label(self.root, text="AI Pose Trainer", fg=COLORS["accent"], bg=COLORS["bg"],
                 font=("Helvetica", 36, "bold")).pack(pady=40)

        tk.Label(self.root, text="Choose an exercise (Front View Supported):",
                 fg=COLORS["text"], bg=COLORS["bg"], font=("Helvetica", 18)).pack()

        btn_frame = tk.Frame(self.root, bg=COLORS["bg"])
        btn_frame.pack(pady=30)

        exercises = ["Bicep Curl", "Squats", "Overhead Tricep Extension", "Pushups", "Leg Raises"]

        for ex in exercises:
            tk.Button(btn_frame, text=ex, width=28, height=2, bg=COLORS["accent"],
                      fg="white", relief="flat", font=("Helvetica", 13, "bold"),
                      activebackground="#ff3399", command=lambda e=ex: self.start_exercise(e)
                      ).pack(pady=10)

        tk.Label(self.root, text="Tip: Stand facing the camera with your full body visible.",
                 fg="#cccccc", bg=COLORS["bg"], font=("Helvetica", 11)).pack(pady=20)

    def start_exercise(self, exercise):
        for widget in self.root.winfo_children():
            widget.destroy()

        self.exercise = exercise
        self.rep_count = 0
        self.angle_buf.clear()
        self.prev_state = None
        self.running = True
        self.last_rep_time = time.time()
        self.feedback_text = ""

        self.pose = mp_pose.Pose(min_detection_confidence=0.6, min_tracking_confidence=0.6)
        self.cap = cv2.VideoCapture(0)

        self.video_label = tk.Label(self.root, bg=COLORS["bg"])
        self.video_label.pack(pady=10)

        # Info area below video
        info_frame = tk.Frame(self.root, bg=COLORS["bg"])
        info_frame.pack(pady=20)

        self.info_text = tk.Label(info_frame, text=f"Exercise: {exercise}", fg=COLORS["text"],
                                  bg=COLORS["bg"], font=("Helvetica", 30, "bold"))
        self.info_text.pack(pady=10)

        self.feedback_label = tk.Label(info_frame, text="Ready when you are!",
                                       fg="#cccccc", bg=COLORS["bg"], font=("Helvetica", 28, "bold"))
        self.feedback_label.pack(pady=10)

        tk.Button(self.root, text="⬅ Back to Menu", bg=COLORS["accent"], fg="white",
                  relief="flat", font=("Helvetica", 14, "bold"),
                  command=self.stop_exercise).pack(pady=20)

        self.update_frame()

    def stop_exercise(self):
        self.running = False
        if self.cap and self.cap.isOpened():
            self.cap.release()
        cv2.destroyAllWindows()
        self.build_main_menu()

    def rep_feedback(self, rep_duration, motion_range):
        if rep_duration < 0.6:
            return "Too Fast! 🟠"
        elif rep_duration > 5:
            return "Too Slow! 🟡"
        elif motion_range > 110:
            return "Perfect Form! ✅"
        elif motion_range > 80:
            return "Good Form 👍"
        else:
            return "Needs Improvement ⚠️"

    def update_frame(self):
        if not self.running:
            return

        ret, frame = self.cap.read()
        if not ret:
            self.feedback_label.config(text="No camera feed detected.")
            self.root.after(30, self.update_frame)
            return

        frame = cv2.flip(frame, 1)
        h, w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.pose.process(rgb)
        output = frame.copy()

        if results.pose_landmarks:
            lm = results.pose_landmarks.landmark
            def p(i): return (lm[i].x * w, lm[i].y * h)

            # ---- Exercise logic ----
            if self.exercise == "Bicep Curl":
                shoulder, elbow, wrist = p(L.RIGHT_SHOULDER), p(L.RIGHT_ELBOW), p(L.RIGHT_WRIST)
                ang = smooth(self.angle_buf, angle(shoulder, elbow, wrist))
                low, high = 40, 160

            elif self.exercise == "Squats":
                shoulder, hip, knee, ankle = p(L.RIGHT_SHOULDER), p(L.RIGHT_HIP), p(L.RIGHT_KNEE), p(L.RIGHT_ANKLE)
                knee_angle = smooth(self.angle_buf, angle(hip, knee, ankle))
                torso_angle = smooth(self.angle_buf, angle(shoulder, hip, knee))

                low_knee, high_knee = 65, 170
                torso_min = 35

                cur_state = "UP" if knee_angle > high_knee else "DOWN" if knee_angle < low_knee else None

                if self.prev_state == "DOWN" and cur_state == "UP":
                    now = time.time()
                    rep_duration = now - self.last_rep_time
                    self.last_rep_time = now
                    motion_range = high_knee - low_knee

                    if torso_angle < torso_min:
                        self.feedback_text = "Too much forward lean ⚠️"
                    elif knee_angle < 70:
                        self.feedback_text = "Too Deep! 🟠"
                    else:
                        self.feedback_text = self.rep_feedback(rep_duration, motion_range)

                    self.feedback_time = now
                    self.rep_count += 1

                if cur_state in ("UP", "DOWN"):
                    self.prev_state = cur_state

                ang = knee_angle
                low, high = low_knee, high_knee

            elif self.exercise == "Overhead Tricep Extension":
                shoulder, elbow, wrist = p(L.RIGHT_SHOULDER), p(L.RIGHT_ELBOW), p(L.RIGHT_WRIST)
                ang = smooth(self.angle_buf, angle(shoulder, elbow, wrist))
                low, high = 50, 160

            elif self.exercise == "Pushups":
                shoulder, elbow, wrist = p(L.RIGHT_SHOULDER), p(L.RIGHT_ELBOW), p(L.RIGHT_WRIST)
                ang = smooth(self.angle_buf, angle(shoulder, elbow, wrist))
                low, high = 70, 160

            elif self.exercise == "Leg Raises":
                hip, knee, ankle = p(L.RIGHT_HIP), p(L.RIGHT_KNEE), p(L.RIGHT_ANKLE)
                ang = smooth(self.angle_buf, angle(hip, knee, ankle))
                low, high = 90, 160

            # Rep detection for all exercises
            if self.exercise != "Squats":
                cur_state = "UP" if ang > high else "DOWN" if ang < low else None
                if self.prev_state == "DOWN" and cur_state == "UP":
                    now = time.time()
                    rep_duration = now - self.last_rep_time
                    self.last_rep_time = now
                    motion_range = high - low
                    self.feedback_text = self.rep_feedback(rep_duration, motion_range)
                    self.feedback_time = now
                    self.rep_count += 1
                if cur_state in ("UP", "DOWN"):
                    self.prev_state = cur_state

            mp_drawing.draw_landmarks(
                output, results.pose_landmarks, mp_pose.POSE_CONNECTIONS,
                mp_drawing.DrawingSpec(color=(255, 255, 255), thickness=2, circle_radius=2),
                mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=2)
            )

        img = Image.fromarray(cv2.cvtColor(output, cv2.COLOR_BGR2RGB))
        imgtk = ImageTk.PhotoImage(image=img)
        self.video_label.imgtk = imgtk
        self.video_label.configure(image=imgtk)

        self.info_text.config(text=f"{self.exercise} | Reps: {self.rep_count}")
        if time.time() - self.feedback_time < FEEDBACK_DURATION:
            self.feedback_label.config(text=self.feedback_text)
        else:
            self.feedback_label.config(text="Keep going!")

        self.root.after(10, self.update_frame)

if __name__ == "__main__":
    root = tk.Tk()
    app = PoseTrainerApp(root)
    root.mainloop()
