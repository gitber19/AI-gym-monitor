#!/usr/bin/env python3
"""
AI Pose Trainer Pro - Simplified Edition
Features: Bold colors, real-time feedback, simplified UI
"""

import cv2
import mediapipe as mp
import numpy as np
import math
import os
import warnings
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
from collections import deque
import time
import json
from datetime import datetime, timedelta

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
warnings.filterwarnings("ignore")

# MediaPipe setup
mp_drawing = mp.solutions.drawing_utils
mp_pose = mp.solutions.pose
L = mp_pose.PoseLandmark

# Bold Vibrant Theme
COLORS = {
    "bg": "#000000",
    "card": "#1a1a1a",
    "accent": "#00ff00",
    "secondary": "#ff00ff",
    "text": "#ffffff",
    "dim": "#666666",
    "green": "#00ff00",
    "red": "#ff0000",
    "yellow": "#ffff00",
    "blue": "#0099ff",
    "orange": "#ff6600",
    "cyan": "#00ffff"
}

ANGLE_SMOOTH = 5

# Exercise database
EXERCISES = {
    "Squats": {
        "calories": 0.38,
        "icon": "🦵",
        "category": "Legs"
    },
    "Bicep Curl": {
        "calories": 0.15,
        "icon": "💪",
        "category": "Arms"
    },
    "Overhead Tricep Extension": {
        "calories": 0.18,
        "icon": "🔥",
        "category": "Arms"
    },
    "Pushups": {
        "calories": 0.35,
        "icon": "🤜",
        "category": "Chest"
    },
    "Leg Raises": {
        "calories": 0.28,
        "icon": "🦿",
        "category": "Core"
    },
    "Lunges": {
        "calories": 0.40,
        "icon": "🏃",
        "category": "Legs"
    },
    "Jumping Jacks": {
        "calories": 0.45,
        "icon": "⚡",
        "category": "Cardio"
    }
}

FITNESS_GOALS = {
    "Weight Loss": ["Jumping Jacks", "Squats", "Lunges"],
    "Muscle Building": ["Pushups", "Bicep Curl", "Overhead Tricep Extension"],
    "Endurance": ["Squats", "Jumping Jacks", "Leg Raises"],
    "General Fitness": ["Squats", "Pushups", "Leg Raises"]
}

USER_DATA_DIR = "user_data"
os.makedirs(USER_DATA_DIR, exist_ok=True)


def angle(a, b, c):
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


class SimpleButton(tk.Button):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.bind("<Enter>", lambda e: self.config(cursor="hand2"))


class UserManager:
    @staticmethod
    def get_user_file(username):
        return os.path.join(USER_DATA_DIR, f"{username}.json")
    
    @staticmethod
    def list_users():
        return sorted([f[:-5] for f in os.listdir(USER_DATA_DIR) if f.endswith('.json')])
    
    @staticmethod
    def create_user(username, age, weight, height, daily_goal, weekly_goal, fitness_goal):
        user_file = UserManager.get_user_file(username)
        if os.path.exists(user_file):
            return False
        
        bmi = weight / ((height/100) ** 2) if height > 0 else 0
        
        user_data = {
            "username": username,
            "age": age,
            "weight": weight,
            "height": height,
            "bmi": round(bmi, 1),
            "fitness_goal": fitness_goal,
            "daily_calorie_goal": daily_goal,
            "weekly_calorie_goal": weekly_goal,
            "created_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_workouts": 0,
            "total_reps": 0,
            "total_calories": 0,
            "workouts": [],
            "achievements": [],
            "streak_days": 0,
            "last_workout_date": None,
            "personal_records": {}
        }
        
        with open(user_file, 'w') as f:
            json.dump(user_data, f, indent=4)
        return True
    
    @staticmethod
    def load_user(username):
        user_file = UserManager.get_user_file(username)
        if not os.path.exists(user_file):
            return None
        with open(user_file, 'r') as f:
            return json.load(f)
    
    @staticmethod
    def save_workout(username, exercise, reps, calories):
        user_data = UserManager.load_user(username)
        if not user_data:
            return False
        
        workout = {
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "exercise": exercise,
            "reps": reps,
            "calories_burned": round(calories, 2)
        }
        
        user_data["workouts"].append(workout)
        user_data["total_workouts"] = user_data.get("total_workouts", 0) + 1
        user_data["total_reps"] = user_data.get("total_reps", 0) + reps
        user_data["total_calories"] = user_data.get("total_calories", 0) + calories
        
        # Update personal records
        pr = user_data.get("personal_records", {})
        if exercise not in pr or reps > pr[exercise]:
            pr[exercise] = reps
        user_data["personal_records"] = pr
        
        # Update streak
        today = datetime.now().strftime("%Y-%m-%d")
        last = user_data.get("last_workout_date")
        if last:
            last_date = datetime.strptime(last, "%Y-%m-%d")
            today_date = datetime.strptime(today, "%Y-%m-%d")
            diff = (today_date - last_date).days
            if diff == 1:
                user_data["streak_days"] = user_data.get("streak_days", 0) + 1
            elif diff > 1:
                user_data["streak_days"] = 1
        else:
            user_data["streak_days"] = 1
        user_data["last_workout_date"] = today
        
        new_achievements = UserManager.check_achievements(user_data)
        
        with open(UserManager.get_user_file(username), 'w') as f:
            json.dump(user_data, f, indent=4)
        return new_achievements
    
    @staticmethod
    def check_achievements(user_data):
        achievements = user_data.get("achievements", [])
        new_achievements = []
        
        milestones = [
            (10, "🏆 First 10 Reps"),
            (50, "💪 Half Century"),
            (100, "🔥 Century Club"),
            (500, "⚡ Beast Mode"),
            (1000, "👑 Elite Athlete")
        ]
        
        total_reps = user_data.get("total_reps", 0)
        for milestone, achievement in milestones:
            if total_reps >= milestone and achievement not in achievements:
                new_achievements.append(achievement)
        
        user_data["achievements"] = achievements + new_achievements
        return new_achievements
    
    @staticmethod
    def get_today_calories(username):
        user_data = UserManager.load_user(username)
        if not user_data:
            return 0
        today = datetime.now().strftime("%Y-%m-%d")
        return round(sum(w["calories_burned"] for w in user_data["workouts"] 
                        if w["date"].startswith(today)), 2)


class PoseTrainerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("⚡ AI POSE TRAINER")
        self.root.geometry("1400x900")
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
        self.current_user = None
        self.total_calories = 0
        self.is_paused = False
        self.video_label = None
        self.update_id = None
        self.current_angle = 0
        self.current_state = "READY"
        
        self.build_home_screen()
    
    def build_home_screen(self):
        for widget in self.root.winfo_children():
            widget.destroy()
        
        main = tk.Frame(self.root, bg=COLORS["bg"])
        main.pack(fill=tk.BOTH, expand=True)
        
        # Title
        tk.Label(main, text="⚡ AI POSE TRAINER", 
                fg=COLORS["accent"], bg=COLORS["bg"],
                font=("Arial", 60, "bold")).pack(pady=50)
        
        # User list
        users = UserManager.list_users()
        
        if users:
            tk.Label(main, text="SELECT YOUR PROFILE", 
                    fg=COLORS["text"], bg=COLORS["bg"],
                    font=("Arial", 20)).pack(pady=20)
            
            for user in users:
                data = UserManager.load_user(user)
                
                btn_frame = tk.Frame(main, bg=COLORS["card"], height=80)
                btn_frame.pack(pady=8, padx=100, fill=tk.X)
                
                SimpleButton(btn_frame, text=f"👤 {user.upper()}\n🔥 {data.get('streak_days', 0)} days  |  💪 {data.get('total_reps', 0)} reps  |  🏋️ {data.get('total_workouts', 0)} workouts",
                           bg=COLORS["card"], fg=COLORS["text"],
                           font=("Arial", 16, "bold"),
                           relief=tk.FLAT, bd=0,
                           command=lambda u=user: self.select_user(u)).pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        else:
            tk.Label(main, text="NO PROFILES FOUND", 
                    fg=COLORS["dim"], bg=COLORS["bg"],
                    font=("Arial", 18)).pack(pady=40)
        
        # New user button
        SimpleButton(main, text="➕ CREATE NEW PROFILE",
                    bg=COLORS["green"], fg=COLORS["bg"],
                    font=("Arial", 18, "bold"),
                    relief=tk.FLAT, bd=0,
                    padx=40, pady=20,
                    command=self.create_new_user).pack(pady=40)
    
    def create_new_user(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("CREATE NEW PROFILE")
        dialog.geometry("500x650")
        dialog.configure(bg=COLORS["bg"])
        dialog.transient(self.root)
        dialog.grab_set()
        
        tk.Label(dialog, text="CREATE NEW PROFILE",
                fg=COLORS["accent"], bg=COLORS["bg"],
                font=("Arial", 28, "bold")).pack(pady=30)
        
        form = tk.Frame(dialog, bg=COLORS["bg"])
        form.pack(pady=20, padx=40, fill=tk.BOTH, expand=True)
        
        fields = {}
        
        def create_field(label_text):
            tk.Label(form, text=label_text, fg=COLORS["text"],
                    bg=COLORS["bg"], font=("Arial", 12, "bold")).pack(anchor="w", pady=(10,5))
            entry = tk.Entry(form, font=("Arial", 14), bg=COLORS["card"],
                           fg=COLORS["text"], insertbackground=COLORS["accent"],
                           relief=tk.FLAT, bd=5)
            entry.pack(fill=tk.X, pady=5)
            return entry
        
        fields['username'] = create_field("USERNAME")
        fields['age'] = create_field("AGE")
        fields['weight'] = create_field("WEIGHT (KG)")
        fields['height'] = create_field("HEIGHT (CM)")
        
        tk.Label(form, text="FITNESS GOAL", fg=COLORS["text"],
                bg=COLORS["bg"], font=("Arial", 12, "bold")).pack(anchor="w", pady=(10,5))
        
        goal_var = tk.StringVar(value="General Fitness")
        for goal in FITNESS_GOALS.keys():
            tk.Radiobutton(form, text=goal, variable=goal_var, value=goal,
                          bg=COLORS["bg"], fg=COLORS["text"],
                          selectcolor=COLORS["card"],
                          activebackground=COLORS["bg"],
                          activeforeground=COLORS["accent"],
                          font=("Arial", 11)).pack(anchor="w")
        
        fields['daily_goal'] = create_field("DAILY CALORIE GOAL")
        fields['weekly_goal'] = create_field("WEEKLY CALORIE GOAL")
        
        def validate_and_register():
            try:
                username = fields['username'].get().strip()
                if not username:
                    messagebox.showerror("ERROR", "Username required")
                    return
                
                age = int(fields['age'].get())
                weight = float(fields['weight'].get())
                height = float(fields['height'].get())
                daily = int(fields['daily_goal'].get())
                weekly = int(fields['weekly_goal'].get())
                
                if UserManager.create_user(username, age, weight, height, 
                                          daily, weekly, goal_var.get()):
                    messagebox.showinfo("SUCCESS", f"Profile '{username}' created!")
                    dialog.destroy()
                    self.build_home_screen()
                else:
                    messagebox.showerror("ERROR", "Username already exists")
            
            except ValueError:
                messagebox.showerror("ERROR", "Invalid input values")
        
        btn_frame = tk.Frame(dialog, bg=COLORS["bg"])
        btn_frame.pack(pady=20)
        
        SimpleButton(btn_frame, text="CREATE",
                    bg=COLORS["green"], fg=COLORS["bg"],
                    font=("Arial", 14, "bold"),
                    relief=tk.FLAT, padx=30, pady=10,
                    command=validate_and_register).pack(side=tk.LEFT, padx=10)
        
        SimpleButton(btn_frame, text="CANCEL",
                    bg=COLORS["red"], fg=COLORS["text"],
                    font=("Arial", 14, "bold"),
                    relief=tk.FLAT, padx=30, pady=10,
                    command=dialog.destroy).pack(side=tk.LEFT, padx=10)
    
    def select_user(self, username):
        self.current_user = username
        self.build_dashboard()
    
    def build_dashboard(self):
        for widget in self.root.winfo_children():
            widget.destroy()
        
        user_data = UserManager.load_user(self.current_user)
        today_cals = UserManager.get_today_calories(self.current_user)
        
        # Header
        header = tk.Frame(self.root, bg=COLORS["card"], height=100)
        header.pack(fill=tk.X, padx=20, pady=20)
        header.pack_propagate(False)
        
        tk.Label(header, text=f"⚡ {self.current_user.upper()}",
                fg=COLORS["accent"], bg=COLORS["card"],
                font=("Arial", 32, "bold")).pack(side=tk.LEFT, padx=30, pady=20)
        
        tk.Label(header, text=f"🔥 {user_data.get('streak_days', 0)} DAYS  |  💪 {user_data.get('total_reps', 0)} REPS  |  🏋️ {user_data.get('total_workouts', 0)} WORKOUTS",
                fg=COLORS["text"], bg=COLORS["card"],
                font=("Arial", 14, "bold")).pack(side=tk.LEFT, padx=20)
        
        SimpleButton(header, text="⬅ BACK",
                    bg=COLORS["red"], fg=COLORS["text"],
                    font=("Arial", 12, "bold"),
                    relief=tk.FLAT, padx=20, pady=10,
                    command=self.build_home_screen).pack(side=tk.RIGHT, padx=30)
        
        # Stats
        stats_frame = tk.Frame(self.root, bg=COLORS["bg"])
        stats_frame.pack(fill=tk.X, padx=40, pady=10)
        
        daily_goal = user_data.get('daily_calorie_goal', 200)
        
        tk.Label(stats_frame, text=f"TODAY: {today_cals} / {daily_goal} CAL",
                fg=COLORS["yellow"], bg=COLORS["bg"],
                font=("Arial", 24, "bold")).pack()
        
        # Exercises
        tk.Label(self.root, text="SELECT EXERCISE",
                fg=COLORS["accent"], bg=COLORS["bg"],
                font=("Arial", 28, "bold")).pack(pady=30)
        
        exercises_frame = tk.Frame(self.root, bg=COLORS["bg"])
        exercises_frame.pack(fill=tk.BOTH, expand=True, padx=40)
        
        for exercise in EXERCISES.keys():
            ex_data = EXERCISES[exercise]
            
            btn = tk.Frame(exercises_frame, bg=COLORS["card"], height=70)
            btn.pack(fill=tk.X, pady=8)
            
            SimpleButton(btn, text=f"{ex_data['icon']} {exercise.upper()}  |  {ex_data['category']}  |  🔥 {ex_data['calories']} cal/rep",
                        bg=COLORS["card"], fg=COLORS["text"],
                        font=("Arial", 18, "bold"),
                        relief=tk.FLAT, bd=0,
                        command=lambda ex=exercise: self.start_exercise(ex)).pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    def start_exercise(self, exercise):
        for widget in self.root.winfo_children():
            widget.destroy()
        
        self.exercise = exercise
        self.rep_count = 0
        self.total_calories = 0
        self.angle_buf.clear()
        self.prev_state = None
        self.running = True
        self.is_paused = False
        self.last_rep_time = time.time()
        self.feedback_text = "GET READY!"
        self.current_angle = 0
        self.current_state = "READY"
        
        self.pose = mp_pose.Pose(min_detection_confidence=0.6,
                                min_tracking_confidence=0.6)
        self.cap = cv2.VideoCapture(0)
        
        # Top bar
        top_bar = tk.Frame(self.root, bg=COLORS["card"], height=80)
        top_bar.pack(fill=tk.X)
        top_bar.pack_propagate(False)
        
        tk.Label(top_bar, text=f"{EXERCISES[exercise]['icon']} {exercise.upper()}",
                fg=COLORS["accent"], bg=COLORS["card"],
                font=("Arial", 28, "bold")).pack(side=tk.LEFT, padx=30, pady=20)
        
        self.stats_label = tk.Label(top_bar,
                                    text=f"REPS: 0 | 🔥 0 CAL",
                                    fg=COLORS["yellow"], bg=COLORS["card"],
                                    font=("Arial", 22, "bold"))
        self.stats_label.pack(side=tk.LEFT, padx=30)
        
        # Video
        self.video_label = tk.Label(self.root, bg=COLORS["bg"])
        self.video_label.pack(pady=10)
        
        # Live Metrics
        metrics_frame = tk.Frame(self.root, bg=COLORS["card"], height=100)
        metrics_frame.pack(fill=tk.X, padx=20, pady=10)
        metrics_frame.pack_propagate(False)
        
        metrics_inner = tk.Frame(metrics_frame, bg=COLORS["card"])
        metrics_inner.pack(expand=True)
        
        # Angle
        angle_frame = tk.Frame(metrics_inner, bg=COLORS["card"])
        angle_frame.pack(side=tk.LEFT, padx=60)
        
        tk.Label(angle_frame, text="ANGLE",
                fg=COLORS["dim"], bg=COLORS["card"],
                font=("Arial", 14, "bold")).pack()
        
        self.angle_label = tk.Label(angle_frame, text="0°",
                                    fg=COLORS["cyan"], bg=COLORS["card"],
                                    font=("Arial", 48, "bold"))
        self.angle_label.pack()
        
        # Status
        status_frame = tk.Frame(metrics_inner, bg=COLORS["card"])
        status_frame.pack(side=tk.LEFT, padx=60)
        
        tk.Label(status_frame, text="STATUS",
                fg=COLORS["dim"], bg=COLORS["card"],
                font=("Arial", 14, "bold")).pack()
        
        self.status_label = tk.Label(status_frame, text="READY",
                                     fg=COLORS["yellow"], bg=COLORS["card"],
                                     font=("Arial", 48, "bold"))
        self.status_label.pack()
        
        # Feedback
        feedback_frame = tk.Frame(self.root, bg=COLORS["card"], height=100)
        feedback_frame.pack(fill=tk.X, padx=20, pady=10)
        feedback_frame.pack_propagate(False)
        
        self.feedback_label = tk.Label(feedback_frame,
                                       text="GET READY!",
                                       fg=COLORS["accent"],
                                       bg=COLORS["card"],
                                       font=("Arial", 32, "bold"))
        self.feedback_label.pack(expand=True)
        
        # Controls
        controls = tk.Frame(self.root, bg=COLORS["bg"])
        controls.pack(pady=10)
        
        SimpleButton(controls, text="⏸ PAUSE",
                    bg=COLORS["yellow"], fg=COLORS["bg"],
                    font=("Arial", 14, "bold"),
                    relief=tk.FLAT, padx=25, pady=12,
                    command=self.toggle_pause).pack(side=tk.LEFT, padx=5)
        
        SimpleButton(controls, text="✓ FINISH",
                    bg=COLORS["green"], fg=COLORS["bg"],
                    font=("Arial", 14, "bold"),
                    relief=tk.FLAT, padx=25, pady=12,
                    command=self.finish_workout).pack(side=tk.LEFT, padx=5)
        
        SimpleButton(controls, text="✕ QUIT",
                    bg=COLORS["red"], fg=COLORS["text"],
                    font=("Arial", 14, "bold"),
                    relief=tk.FLAT, padx=25, pady=12,
                    command=self.stop_exercise).pack(side=tk.LEFT, padx=5)
        
        self.update_frame()
    
    def toggle_pause(self):
        self.is_paused = not self.is_paused
    
    def stop_exercise(self):
        self.running = False
        if self.cap and self.cap.isOpened():
            self.cap.release()
        if self.update_id:
            self.root.after_cancel(self.update_id)
        cv2.destroyAllWindows()
        self.build_dashboard()
    
    def finish_workout(self):
        self.running = False
        if self.cap and self.cap.isOpened():
            self.cap.release()
        if self.update_id:
            self.root.after_cancel(self.update_id)
        cv2.destroyAllWindows()
        
        new_achievements = UserManager.save_workout(
            self.current_user, self.exercise,
            self.rep_count, self.total_calories
        )
        
        msg = f"WORKOUT COMPLETE!\n\n"
        msg += f"Exercise: {self.exercise}\n"
        msg += f"Reps: {self.rep_count}\n"
        msg += f"Calories: {self.total_calories:.1f}\n"
        
        if new_achievements:
            msg += f"\nNEW ACHIEVEMENTS:\n"
            for ach in new_achievements:
                msg += f"   {ach}\n"
        
        messagebox.showinfo("WORKOUT COMPLETE", msg)
        self.build_dashboard()
    
    def get_suggestion(self, angle, low, high, exercise):
        """Generate real-time form suggestions"""
        if exercise == "Bicep Curl":
            if angle > 150:
                return "LOWER THE WEIGHT ⬇", COLORS["yellow"]
            elif angle < 50:
                return "CURL UP MORE ⬆", COLORS["yellow"]
            else:
                return "GOOD FORM! ✓", COLORS["green"]
        
        elif exercise == "Squats":
            if angle > 160:
                return "GO DEEPER ⬇", COLORS["yellow"]
            elif angle < 70:
                return "DON'T GO TOO LOW! ⬆", COLORS["orange"]
            else:
                return "PERFECT DEPTH! ✓", COLORS["green"]
        
        elif exercise == "Pushups":
            if angle > 150:
                return "GO LOWER ⬇", COLORS["yellow"]
            elif angle < 80:
                return "PUSH UP! ⬆", COLORS["yellow"]
            else:
                return "GREAT FORM! ✓", COLORS["green"]
        
        else:
            if angle > high - 10:
                return "EXTEND MORE! ⬆", COLORS["yellow"]
            elif angle < low + 10:
                return "RELEASE SLOWLY ⬇", COLORS["yellow"]
            else:
                return "KEEP IT UP! ✓", COLORS["green"]
    
    def update_frame(self):
        if not self.running:
            return
        
        if self.is_paused:
            self.feedback_label.config(text="⏸ PAUSED", fg=COLORS["yellow"])
            self.status_label.config(text="PAUSED", fg=COLORS["yellow"])
            self.update_id = self.root.after(100, self.update_frame)
            return
        
        ret, frame = self.cap.read()
        if not ret:
            self.feedback_label.config(text="NO CAMERA", fg=COLORS["red"])
            self.status_label.config(text="NO CAM", fg=COLORS["red"])
            self.update_id = self.root.after(30, self.update_frame)
            return
        
        frame = cv2.flip(frame, 1)
        h, w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.pose.process(rgb)
        output = frame.copy()
        
        if results.pose_landmarks:
            lm = results.pose_landmarks.landmark
            def p(i): return (lm[i].x * w, lm[i].y * h)
            
            # Exercise logic with correct detection
            if self.exercise == "Bicep Curl":
                shoulder, elbow, wrist = p(L.RIGHT_SHOULDER), p(L.RIGHT_ELBOW), p(L.RIGHT_WRIST)
                ang = smooth(self.angle_buf, angle(shoulder, elbow, wrist))
                low, high = 40, 160
                
                # FIXED: Bicep curl - UP when curled (small angle), DOWN when extended (large angle)
                cur_state = "UP" if ang < 80 else "DOWN" if ang > 140 else None
            
            elif self.exercise == "Squats":
                hip, knee, ankle = p(L.RIGHT_HIP), p(L.RIGHT_KNEE), p(L.RIGHT_ANKLE)
                ang = smooth(self.angle_buf, angle(hip, knee, ankle))
                low, high = 65, 170
                cur_state = "DOWN" if ang < 100 else "UP" if ang > 150 else None
            
            elif self.exercise == "Overhead Tricep Extension":
                shoulder, elbow, wrist = p(L.RIGHT_SHOULDER), p(L.RIGHT_ELBOW), p(L.RIGHT_WRIST)
                ang = smooth(self.angle_buf, angle(shoulder, elbow, wrist))
                low, high = 50, 160
                cur_state = "UP" if ang > 140 else "DOWN" if ang < 80 else None
            
            elif self.exercise == "Pushups":
                shoulder, elbow, wrist = p(L.RIGHT_SHOULDER), p(L.RIGHT_ELBOW), p(L.RIGHT_WRIST)
                ang = smooth(self.angle_buf, angle(shoulder, elbow, wrist))
                low, high = 70, 160
                cur_state = "DOWN" if ang < 100 else "UP" if ang > 140 else None
            
            elif self.exercise == "Leg Raises":
                 hip, knee, ankle = p(L.RIGHT_HIP), p(L.RIGHT_KNEE), p(L.RIGHT_ANKLE)
                 ang = angle(hip, knee, ankle)
                 ang = smooth(self.angle_buf, ang)
                 low, high = 90, 160
                 cur_state = "UP" if ang < 110 else "DOWN" if ang > 140 else None

            elif self.exercise == "Lunges":
                hip, knee, ankle = p(L.RIGHT_HIP), p(L.RIGHT_KNEE), p(L.RIGHT_ANKLE)
                ang = smooth(self.angle_buf, angle(hip, knee, ankle))
                low, high = 70, 170
                cur_state = "DOWN" if ang < 100 else "UP" if ang > 150 else None
            
            elif self.exercise == "Jumping Jacks":
                shoulder, hip, knee = p(L.RIGHT_SHOULDER), p(L.RIGHT_HIP), p(L.RIGHT_KNEE)
                ang = smooth(self.angle_buf, angle(shoulder, hip, knee))
                low, high = 150, 180
                cur_state = "UP" if ang > 170 else "DOWN" if ang < 160 else None
            
            else:
                ang = 0
                low, high = 0, 180
                cur_state = None
            
            # Rep detection and feedback
            if cur_state and cur_state != self.prev_state:
                # Count rep on transition from DOWN to UP
                if self.prev_state == "DOWN" and cur_state == "UP":
                    self.rep_count += 1
                    self.total_calories += EXERCISES[self.exercise]["calories"]
                    
                    # Update stats
                    self.stats_label.config(
                        text=f"REPS: {self.rep_count} | 🔥 {self.total_calories:.1f} CAL"
                    )
                    
                    # Rep feedback
                    rep_time = time.time() - self.last_rep_time
                    self.last_rep_time = time.time()
                    
                    if rep_time < 0.8:
                        self.feedback_label.config(text="TOO FAST! SLOW DOWN ⚠", fg=COLORS["orange"])
                    elif rep_time > 4:
                        self.feedback_label.config(text="TOO SLOW! SPEED UP ⚠", fg=COLORS["orange"])
                    else:
                        self.feedback_label.config(text="GREAT REP! KEEP GOING! ✓", fg=COLORS["green"])
                
                self.prev_state = cur_state
                self.current_state = cur_state
            
            # Update live angle
            self.current_angle = int(ang)
            self.angle_label.config(text=f"{self.current_angle}°")
            
            # Update status with colors
            if self.current_state == "UP":
                self.status_label.config(text="UP ⬆", fg=COLORS["green"])
            elif self.current_state == "DOWN":
                self.status_label.config(text="DOWN ⬇", fg=COLORS["orange"])
            else:
                self.status_label.config(text="READY", fg=COLORS["yellow"])
            
            # Real-time form suggestions
            suggestion, color = self.get_suggestion(ang, low, high, self.exercise)
            if self.rep_count > 0 and self.current_state in ["UP", "DOWN"]:
                self.feedback_label.config(text=suggestion, fg=color)
            
            # Draw landmarks
            mp_drawing.draw_landmarks(
                output, results.pose_landmarks, mp_pose.POSE_CONNECTIONS,
                mp_drawing.DrawingSpec(color=(0, 255, 136), thickness=3, circle_radius=4),
                mp_drawing.DrawingSpec(color=(0, 212, 255), thickness=3, circle_radius=3)
            )
        
        # Update video
        img = Image.fromarray(cv2.cvtColor(output, cv2.COLOR_BGR2RGB))
        imgtk = ImageTk.PhotoImage(image=img)
        self.video_label.imgtk = imgtk
        self.video_label.configure(image=imgtk)
        
        self.update_id = self.root.after(10, self.update_frame)


if __name__ == "__main__":
     root = tk.Tk()
     app = PoseTrainerApp(root)
     root.mainloop()