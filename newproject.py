#!/usr/bin/env python3
"""
AI Pose Trainer Pro - Complete Enhanced Edition
Features: Exercise recommendations, achievements, streaks, BMI tracking,
         workout history, form scoring, rest timer, custom exercises
"""

import cv2
import mediapipe as mp
import numpy as np
import math
import os
import warnings
import tkinter as tk
from tkinter import messagebox, simpledialog
from PIL import Image, ImageTk
from collections import deque
import time
import json
from datetime import datetime, timedelta
import random

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
warnings.filterwarnings("ignore")

# MediaPipe setup
mp_drawing = mp.solutions.drawing_utils
mp_pose = mp.solutions.pose
L = mp_pose.PoseLandmark

# Cyberpunk Theme
COLORS = {
    "bg": "#0a0a0f",
    "bg_card": "#1a1a2e",
    "bg_card_hover": "#252540",
    "accent": "#00ff88",
    "accent_glow": "#00ffaa",
    "secondary": "#ff00ff",
    "text": "#ffffff",
    "text_dim": "#8892b0",
    "green": "#00ff88",
    "red": "#ff0055",
    "yellow": "#ffdd00",
    "purple": "#bd00ff",
    "blue": "#00d4ff",
    "orange": "#ff6b35",
    "cyan": "#00ffff"
}

ANGLE_SMOOTH = 5
FEEDBACK_DURATION = 2

# Exercise database with enhanced info
EXERCISES = {
    "Squats": {
        "calories": 0.38,
        "icon": "🦵",
        "difficulty": "Medium",
        "category": "Legs",
        "description": "Lower body strength and endurance",
        "form_tips": ["Keep back straight", "Knees behind toes", "Full depth"]
    },
    "Bicep Curl": {
        "calories": 0.15,
        "icon": "💪",
        "difficulty": "Easy",
        "category": "Arms",
        "description": "Arm muscle building",
        "form_tips": ["Elbow stationary", "Controlled motion", "Full range"]
    },
    "Overhead Tricep Extension": {
        "calories": 0.18,
        "icon": "🔥",
        "difficulty": "Medium",
        "category": "Arms",
        "description": "Tricep strength and definition",
        "form_tips": ["Elbows in", "Full extension", "Controlled descent"]
    },
    "Pushups": {
        "calories": 0.35,
        "icon": "🤜",
        "difficulty": "Medium",
        "category": "Chest",
        "description": "Full upper body workout",
        "form_tips": ["Straight body line", "Full depth", "Controlled pace"]
    },
    "Leg Raises": {
        "calories": 0.28,
        "icon": "🦿",
        "difficulty": "Medium",
        "category": "Core",
        "description": "Core and lower ab strength",
        "form_tips": ["Keep legs straight", "Slow and controlled", "Core engaged"]
    },
    "Lunges": {
        "calories": 0.40,
        "icon": "🏃",
        "difficulty": "Medium",
        "category": "Legs",
        "description": "Leg strength and balance",
        "form_tips": ["90 degree angles", "Knee stability", "Upright torso"]
    },
    "Jumping Jacks": {
        "calories": 0.45,
        "icon": "⚡",
        "difficulty": "Easy",
        "category": "Cardio",
        "description": "Full body cardio boost",
        "form_tips": ["Full range of motion", "Steady rhythm", "Land softly"]
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


class AnimatedLabel(tk.Label):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.glow_active = False
        self.pulse_active = False
        self.original_font = kwargs.get('font', ('Helvetica', 12))
    
    def start_glow(self):
        if not self.glow_active:
            self.glow_active = True
            self._animate_glow(0)
    
    def _animate_glow(self, step):
        if not self.glow_active or step > 30:
            self.glow_active = False
            return
        self.after(50, lambda: self._animate_glow(step + 1))
    
    def pulse(self, scale=1.2, duration=500):
        if self.pulse_active:
            return
        self.pulse_active = True
        size = int(self.original_font[1] * scale)
        self.config(font=(self.original_font[0], size))
        self.after(duration // 2, lambda: self.config(font=self.original_font))
        self.after(duration, lambda: setattr(self, 'pulse_active', False))


class GlowButton(tk.Button):
    def __init__(self, parent, **kwargs):
        self.default_bg = kwargs.get('bg', COLORS["accent"])
        self.hover_bg = kwargs.get('activebackground', COLORS["accent_glow"])
        super().__init__(parent, **kwargs)
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)
    
    def on_enter(self, e):
        self.config(bg=self.hover_bg, cursor="hand2")
    
    def on_leave(self, e):
        self.config(bg=self.default_bg)


class ModernEntry(tk.Frame):
    def __init__(self, parent, label_text, **kwargs):
        super().__init__(parent, bg=COLORS["bg_card"])
        
        tk.Label(self, text=label_text, fg=COLORS["text_dim"], 
                bg=COLORS["bg_card"], font=("Arial", 11)).pack(anchor="w", pady=(0,5))
        
        entry_container = tk.Frame(self, bg=COLORS["bg"])
        entry_container.pack(fill=tk.X)
        
        self.entry = tk.Entry(entry_container, font=("Arial", 14),
                             bg=COLORS["bg"], fg=COLORS["text"],
                             insertbackground=COLORS["accent"],
                             relief=tk.FLAT, bd=0)
        self.entry.pack(fill=tk.X, padx=2, pady=2, ipady=8)
        
        self.border = tk.Frame(self, bg=COLORS["text_dim"], height=2)
        self.border.pack(fill=tk.X)
        
        self.entry.bind("<FocusIn>", self.on_focus_in)
        self.entry.bind("<FocusOut>", self.on_focus_out)
        self.entry.bind("<Return>", lambda e: self.entry.tk_focusNext().focus())
    
    def on_focus_in(self, e):
        self.border.config(bg=COLORS["accent"], height=3)
    
    def on_focus_out(self, e):
        self.border.config(bg=COLORS["text_dim"], height=2)
    
    def get(self):
        return self.entry.get()


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
            "personal_records": {},
            "form_scores": []
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
    def save_workout(username, exercise, reps, calories, form_score=0):
        user_data = UserManager.load_user(username)
        if not user_data:
            return False
        
        workout = {
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "exercise": exercise,
            "reps": reps,
            "calories_burned": round(calories, 2),
            "form_score": form_score
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
        
        # Store form scores
        if "form_scores" not in user_data:
            user_data["form_scores"] = []
        user_data["form_scores"].append({
            "date": datetime.now().strftime("%Y-%m-%d"),
            "score": form_score
        })
        
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
            (1000, "👑 Elite Athlete"),
            (5000, "🌟 Legend")
        ]
        
        total_reps = user_data.get("total_reps", 0)
        for milestone, achievement in milestones:
            if total_reps >= milestone and achievement not in achievements:
                new_achievements.append(achievement)
        
        streak = user_data.get("streak_days", 0)
        streak_milestones = [
            (7, "🔥 Week Warrior"),
            (30, "💎 Monthly Master"),
            (100, "🌟 Consistency King"),
            (365, "👑 Year Champion")
        ]
        
        for days, achievement in streak_milestones:
            if streak >= days and achievement not in achievements:
                new_achievements.append(achievement)
        
        # Calorie achievements
        total_cals = user_data.get("total_calories", 0)
        cal_milestones = [
            (1000, "🔥 1K Calories Burned"),
            (5000, "💪 5K Calories Burned"),
            (10000, "⚡ 10K Calories Burned")
        ]
        
        for cals, achievement in cal_milestones:
            if total_cals >= cals and achievement not in achievements:
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
    
    @staticmethod
    def get_week_calories(username):
        user_data = UserManager.load_user(username)
        if not user_data:
            return 0
        week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        return round(sum(w["calories_burned"] for w in user_data["workouts"] 
                        if w["date"] >= week_ago), 2)
    
    @staticmethod
    def get_recommended_exercises(username):
        user_data = UserManager.load_user(username)
        if not user_data:
            return list(EXERCISES.keys())[:3]
        
        goal = user_data.get("fitness_goal", "General Fitness")
        daily_goal = user_data.get("daily_calorie_goal", 200)
        today_cals = UserManager.get_today_calories(username)
        remaining = daily_goal - today_cals
        
        if goal in FITNESS_GOALS:
            recommended = FITNESS_GOALS[goal]
        else:
            recommended = list(EXERCISES.keys())
        
        if remaining > 100:
            recommended = sorted(recommended, 
                               key=lambda x: EXERCISES[x]["calories"], 
                               reverse=True)
        
        return recommended[:3]


class RestTimer:
    """Rest timer between sets"""
    def __init__(self, parent, duration=60):
        self.window = tk.Toplevel(parent)
        self.window.title("⏱️ REST TIMER")
        self.window.geometry("400x300")
        self.window.configure(bg=COLORS["bg"])
        self.window.transient(parent)
        
        self.duration = duration
        self.remaining = duration
        self.running = True
        
        tk.Label(self.window, text="⏱️ REST TIME",
                fg=COLORS["accent"], bg=COLORS["bg"],
                font=("Arial", 24, "bold")).pack(pady=20)
        
        self.timer_label = tk.Label(self.window, text=f"{duration}",
                                    fg=COLORS["text"], bg=COLORS["bg"],
                                    font=("Arial", 72, "bold"))
        self.timer_label.pack(pady=20)
        
        self.progress = tk.Canvas(self.window, width=300, height=20,
                                 bg=COLORS["bg_card"], highlightthickness=0)
        self.progress.pack(pady=20)
        self.progress_bar = self.progress.create_rectangle(
            0, 0, 300, 20, fill=COLORS["accent"], outline=""
        )
        
        btn_frame = tk.Frame(self.window, bg=COLORS["bg"])
        btn_frame.pack(pady=10)
        
        GlowButton(btn_frame, text="SKIP", bg=COLORS["red"],
                  activebackground="#ff3366", font=("Arial", 14, "bold"),
                  padx=20, pady=10, command=self.skip).pack(side=tk.LEFT, padx=5)
        
        GlowButton(btn_frame, text="+30s", bg=COLORS["blue"],
                  activebackground=COLORS["cyan"], font=("Arial", 14, "bold"),
                  padx=20, pady=10, command=self.add_time).pack(side=tk.LEFT, padx=5)
        
        self.countdown()
    
    def countdown(self):
        if self.remaining > 0 and self.running:
            self.timer_label.config(text=f"{self.remaining}")
            width = int((self.remaining / self.duration) * 300)
            self.progress.coords(self.progress_bar, 0, 0, width, 20)
            
            if self.remaining <= 3:
                self.timer_label.config(fg=COLORS["red"])
            
            self.remaining -= 1
            self.window.after(1000, self.countdown)
        elif self.remaining == 0:
            self.window.destroy()
    
    def skip(self):
        self.running = False
        self.window.destroy()
    
    def add_time(self):
        self.remaining += 30
        self.duration += 30


class PoseTrainerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("⚡ AI POSE TRAINER PRO")
        self.root.geometry("1400x950")
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
        self.form_scores = deque(maxlen=10)
        self.target_reps = 10
        
        self.build_splash_screen()
    
    def build_splash_screen(self):
        for widget in self.root.winfo_children():
            widget.destroy()
        
        canvas = tk.Canvas(self.root, width=1400, height=950, 
                          bg=COLORS["bg"], highlightthickness=0)
        canvas.pack()
        
        # Particles
        particles = []
        for _ in range(30):
            x, y = random.randint(0, 1400), random.randint(0, 950)
            size = random.randint(2, 4)
            particles.append(canvas.create_oval(x, y, x+size, y+size, 
                                               fill=COLORS["accent"], outline=""))
        
        def animate_particles():
            if not canvas.winfo_exists():
                return
            for p in particles:
                coords = canvas.coords(p)
                if coords:
                    x1, y1, x2, y2 = coords
                    y1 += 1
                    y2 += 1
                    if y1 > 950:
                        y1, y2 = 0, y2-y1
                        x1 = random.randint(0, 1400)
                        x2 = x1 + (x2-x1)
                    canvas.coords(p, x1, y1, x2, y2)
            self.root.after(50, animate_particles)
        
        animate_particles()
        
        title = canvas.create_text(700, 300, text="⚡ AI POSE TRAINER",
                                  font=("Arial", 56, "bold"), fill=COLORS["accent"])
        canvas.create_text(700, 380, text="NEXT-GEN WORKOUT TRACKING",
                          font=("Arial", 24), fill=COLORS["text_dim"])
        canvas.create_text(700, 420, text="v2.0 ENHANCED EDITION",
                          font=("Arial", 12), fill=COLORS["secondary"])
        
        def pulse_title(scale=1.0, growing=True):
            if not canvas.winfo_exists():
                return
            new_scale = scale + 0.02 if growing else scale - 0.02
            if new_scale >= 1.1:
                growing = False
            elif new_scale <= 1.0:
                growing = True
            size = int(56 * new_scale)
            canvas.itemconfig(title, font=("Arial", size, "bold"))
            self.root.after(50, lambda: pulse_title(new_scale, growing))
        
        pulse_title()
        
        loading = canvas.create_text(700, 520, text="INITIALIZING...",
                                    font=("Arial", 16), fill=COLORS["secondary"])
        
        bar_w, bar_h, bar_x, bar_y = 400, 6, 500, 580
        canvas.create_rectangle(bar_x, bar_y, bar_x+bar_w, bar_y+bar_h, 
                               fill=COLORS["bg_card"], outline="")
        progress_bar = canvas.create_rectangle(bar_x, bar_y, bar_x, bar_y+bar_h,
                                               fill=COLORS["accent"], outline="")
        
        stages = ["LOADING NEURAL NETWORK...", "CALIBRATING SENSORS...",
                 "INITIALIZING POSE DETECTION...", "LOADING DATABASE...",
                 "OPTIMIZING PERFORMANCE...", "SYSTEM READY!"]
        
        def animate_loading(progress=0, stage=0):
            if progress >= 100:
                self.root.after(500, self.build_user_selection)
                return
            
            w = int((progress / 100) * bar_w)
            canvas.coords(progress_bar, bar_x, bar_y, bar_x+w, bar_y+bar_h)
            dots = "." * ((progress // 10) % 4)
            canvas.itemconfig(loading, text=f"{stages[min(stage, len(stages)-1)]}{dots}")
            next_stage = stage + 1 if progress % 16 == 0 and progress > 0 else stage
            self.root.after(30, lambda: animate_loading(progress + 2, next_stage))
        
        animate_loading()
        
        features = ["✓ Real-time Pose Detection", "✓ AI Form Analysis",
                   "✓ Personalized Recommendations", "✓ Achievements & Streaks",
                   "✓ Workout History", "✓ Rest Timer"]
        for i, f in enumerate(features):
            canvas.create_text(700, 650+i*30, text=f, font=("Arial", 14),
                             fill=COLORS["text_dim"])
    
    def build_user_selection(self):
        for widget in self.root.winfo_children():
            widget.destroy()
        
        main = tk.Frame(self.root, bg=COLORS["bg"])
        main.pack(fill=tk.BOTH, expand=True, padx=40, pady=40)
        
        header = tk.Frame(main, bg=COLORS["bg"])
        header.pack(pady=(0, 30))
        
        title = AnimatedLabel(header, text="⚡ SELECT PROFILE",
                             fg=COLORS["accent"], bg=COLORS["bg"],
                             font=("Arial", 42, "bold"))
        title.pack()
        title.start_glow()
        
        tk.Label(header, text="// ACCESS YOUR TRAINING DATA",
                fg=COLORS["text_dim"], bg=COLORS["bg"],
                font=("Arial", 14)).pack()
        
        users = UserManager.list_users()
        tk.Label(main, text=f"📊 TOTAL PROFILES: {len(users)}",
                fg=COLORS["text_dim"], bg=COLORS["bg"],
                font=("Arial", 13)).pack(pady=15)
        
        cards_frame = tk.Frame(main, bg=COLORS["bg"])
        cards_frame.pack(pady=20, fill=tk.BOTH, expand=True)
        
        if users:
            canvas = tk.Canvas(cards_frame, bg=COLORS["bg"], 
                             highlightthickness=0, height=400)
            scrollbar = tk.Scrollbar(cards_frame, orient="vertical", 
                                    command=canvas.yview)
            scrollable = tk.Frame(canvas, bg=COLORS["bg"])
            
            scrollable.bind("<Configure>",
                lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
            canvas.create_window((0, 0), window=scrollable, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)
            
            for user in users:
                data = UserManager.load_user(user)
                today_cals = UserManager.get_today_calories(user)
                
                card = tk.Frame(scrollable, bg=COLORS["bg_card"], relief=tk.FLAT)
                card.pack(pady=10, padx=20, fill=tk.X)
                
                def on_enter(e, c=card):
                    c.config(bg=COLORS["bg_card_hover"], cursor="hand2")
                def on_leave(e, c=card):
                    c.config(bg=COLORS["bg_card"])
                
                card.bind("<Enter>", on_enter)
                card.bind("<Leave>", on_leave)
                card.bind("<Button-1>", lambda e, u=user: self.select_user(u))
                
                content = tk.Frame(card, bg=COLORS["bg_card"])
                content.pack(padx=30, pady=20, fill=tk.X)
                
                left = tk.Frame(content, bg=COLORS["bg_card"])
                left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
                
                tk.Label(left, text=f"👤 {user.upper()}", fg=COLORS["accent"],
                        bg=COLORS["bg_card"], font=("Arial", 20, "bold")).pack(anchor="w")
                
                info_text = f"Age: {data.get('age')} | BMI: {data.get('bmi', 0)} | Goal: {data.get('fitness_goal', 'N/A')}"
                tk.Label(left, text=info_text, fg=COLORS["text_dim"],
                        bg=COLORS["bg_card"], font=("Arial", 11)).pack(anchor="w", pady=(5,0))
                
                stats_text = f"🏋️ {data.get('total_workouts', 0)} workouts | 💪 {data.get('total_reps', 0)} reps | 🔥 {data.get('total_calories', 0):.0f} cal"
                tk.Label(left, text=stats_text, fg=COLORS["text"],
                        bg=COLORS["bg_card"], font=("Arial", 11)).pack(anchor="w", pady=(8,0))
                
                right = tk.Frame(content, bg=COLORS["bg_card"])
                right.pack(side=tk.RIGHT)
                
                tk.Label(right, text=f"🔥 {data.get('streak_days', 0)} DAY STREAK",
                        fg=COLORS["orange"], bg=COLORS["bg_card"],
                        font=("Arial", 12, "bold")).pack(anchor="e")
                
                tk.Label(right, text=f"TODAY: {today_cals}/{data.get('daily_calorie_goal', 0)} cal",
                        fg=COLORS["green"], bg=COLORS["bg_card"],
                        font=("Arial", 11)).pack(anchor="e", pady=(5,0))
            
            canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        else:
            tk.Label(cards_frame, text="📭 NO PROFILES FOUND\nCREATE YOUR FIRST PROFILE TO BEGIN",
                    fg=COLORS["text_dim"], bg=COLORS["bg"],
                    font=("Arial", 16), justify=tk.CENTER).pack(pady=50)
        
        btn_frame = tk.Frame(main, bg=COLORS["bg"])
        btn_frame.pack(pady=30)
        
        GlowButton(btn_frame, text="➕ CREATE NEW PROFILE",
                  bg=COLORS["accent"], activebackground=COLORS["accent_glow"],
                  fg=COLORS["bg"], font=("Arial", 14, "bold"),
                  padx=30, pady=15, command=self.create_new_user).pack()
    
    def create_new_user(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("⚡ CREATE PROFILE")
        dialog.geometry("550x700")
        dialog.configure(bg=COLORS["bg"])
        dialog.transient(self.root)
        dialog.grab_set()
        
        tk.Label(dialog, text="⚡ CREATE NEW PROFILE",
                fg=COLORS["accent"], bg=COLORS["bg"],
                font=("Arial", 28, "bold")).pack(pady=30)
        
        form = tk.Frame(dialog, bg=COLORS["bg"])
        form.pack(pady=20, padx=50, fill=tk.BOTH, expand=True)
        
        fields = {}
        
        fields['username'] = ModernEntry(form, "USERNAME")
        fields['username'].pack(fill=tk.X, pady=10)
        
        fields['age'] = ModernEntry(form, "AGE")
        fields['age'].pack(fill=tk.X, pady=10)
        
        fields['weight'] = ModernEntry(form, "WEIGHT (KG)")
        fields['weight'].pack(fill=tk.X, pady=10)
        
        fields['height'] = ModernEntry(form, "HEIGHT (CM)")
        fields['height'].pack(fill=tk.X, pady=10)
        
        tk.Label(form, text="FITNESS GOAL", fg=COLORS["text_dim"],
                bg=COLORS["bg"], font=("Arial", 11)).pack(anchor="w", pady=(10,5))
        
        goal_var = tk.StringVar(value="General Fitness")
        goal_frame = tk.Frame(form, bg=COLORS["bg"])
        goal_frame.pack(fill=tk.X, pady=5)
        
        for goal in FITNESS_GOALS.keys():
            tk.Radiobutton(goal_frame, text=goal, variable=goal_var, value=goal,
                          bg=COLORS["bg"], fg=COLORS["text"],
                          selectcolor=COLORS["bg_card"],
                          activebackground=COLORS["bg"],
                          activeforeground=COLORS["accent"],
                          font=("Arial", 11)).pack(anchor="w")
        
        fields['daily_goal'] = ModernEntry(form, "DAILY CALORIE GOAL")
        fields['daily_goal'].pack(fill=tk.X, pady=10)
        
        fields['weekly_goal'] = ModernEntry(form, "WEEKLY CALORIE GOAL")
        fields['weekly_goal'].pack(fill=tk.X, pady=10)
        
        def validate_and_create():
            try:
                username = fields['username'].get().strip()
                if not username:
                    messagebox.showerror("⚠️ ERROR", "USERNAME REQUIRED")
                    return
                
                if not username.replace('_', '').replace('-', '').isalnum():
                    messagebox.showerror("⚠️ ERROR", "INVALID USERNAME")
                    return
                
                age = int(fields['age'].get())
                weight = float(fields['weight'].get())
                height = float(fields['height'].get())
                daily = int(fields['daily_goal'].get())
                weekly = int(fields['weekly_goal'].get())
                
                if not (10 <= age <= 120):
                    messagebox.showerror("⚠️ ERROR", "AGE MUST BE 10-120")
                    return
                
                if not (30 <= weight <= 300):
                    messagebox.showerror("⚠️ ERROR", "WEIGHT MUST BE 30-300 KG")
                    return
                
                if not (100 <= height <= 250):
                    messagebox.showerror("⚠️ ERROR", "HEIGHT MUST BE 100-250 CM")
                    return
                
                if daily <= 0 or weekly <= 0:
                    messagebox.showerror("⚠️ ERROR", "CALORIE GOALS MUST BE POSITIVE")
                    return
                
                if UserManager.create_user(username, age, weight, height, 
                                          daily, weekly, goal_var.get()):
                    messagebox.showinfo("✅ SUCCESS", 
                                      f"PROFILE '{username.upper()}' CREATED!")
                    dialog.destroy()
                    self.build_user_selection()
                else:
                    messagebox.showerror("⚠️ ERROR", "USERNAME ALREADY EXISTS")
            
            except ValueError:
                messagebox.showerror("⚠️ ERROR", "INVALID INPUT VALUES")
        
        btn_frame = tk.Frame(dialog, bg=COLORS["bg"])
        btn_frame.pack(pady=20)
        
        GlowButton(btn_frame, text="✓ CREATE PROFILE",
                  bg=COLORS["accent"], activebackground=COLORS["accent_glow"],
                  fg=COLORS["bg"], font=("Arial", 14, "bold"),
                  padx=30, pady=12, command=validate_and_create).pack(side=tk.LEFT, padx=10)
        
        GlowButton(btn_frame, text="✕ CANCEL",
                  bg=COLORS["red"], activebackground="#ff3366",
                  fg=COLORS["text"], font=("Arial", 14, "bold"),
                  padx=30, pady=12, command=dialog.destroy).pack(side=tk.LEFT, padx=10)
    
    def select_user(self, username):
        self.current_user = username
        self.build_dashboard()
    
    def build_dashboard(self):
        for widget in self.root.winfo_children():
            widget.destroy()
        
        user_data = UserManager.load_user(self.current_user)
        today_cals = UserManager.get_today_calories(self.current_user)
        week_cals = UserManager.get_week_calories(self.current_user)
        
        # Header
        header = tk.Frame(self.root, bg=COLORS["bg_card"], height=100)
        header.pack(fill=tk.X, padx=20, pady=20)
        header.pack_propagate(False)
        
        left_header = tk.Frame(header, bg=COLORS["bg_card"])
        left_header.pack(side=tk.LEFT, padx=30, pady=20)
        
        tk.Label(left_header, text=f"⚡ {self.current_user.upper()}",
                fg=COLORS["accent"], bg=COLORS["bg_card"],
                font=("Arial", 28, "bold")).pack(anchor="w")
        
        stats = f"🔥 {user_data.get('streak_days', 0)} day streak | 🏋️ {user_data.get('total_workouts', 0)} workouts | 💪 {user_data.get('total_reps', 0)} reps"
        tk.Label(left_header, text=stats, fg=COLORS["text_dim"],
                bg=COLORS["bg_card"], font=("Arial", 12)).pack(anchor="w")
        
        right_header = tk.Frame(header, bg=COLORS["bg_card"])
        right_header.pack(side=tk.RIGHT, padx=30)
        
        GlowButton(right_header, text="⬅ SWITCH PROFILE",
                  bg=COLORS["secondary"], activebackground="#ff33ff",
                  fg=COLORS["text"], font=("Arial", 12, "bold"),
                  padx=20, pady=10, command=self.build_user_selection).pack()
        
        # Main content
        content = tk.Frame(self.root, bg=COLORS["bg"])
        content.pack(fill=tk.BOTH, expand=True, padx=20)
        
        # Left panel - Stats
        left_panel = tk.Frame(content, bg=COLORS["bg"], width=400)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, padx=10)
        
        # Daily progress
        daily_card = tk.Frame(left_panel, bg=COLORS["bg_card"])
        daily_card.pack(fill=tk.X, pady=10, padx=10)
        
        tk.Label(daily_card, text="📊 TODAY'S PROGRESS",
                fg=COLORS["text"], bg=COLORS["bg_card"],
                font=("Arial", 16, "bold")).pack(anchor="w", padx=20, pady=(15,10))
        
        daily_goal = user_data.get('daily_calorie_goal', 200)
        progress_pct = min(100, (today_cals / daily_goal * 100)) if daily_goal > 0 else 0
        
        progress_frame = tk.Frame(daily_card, bg=COLORS["bg_card"])
        progress_frame.pack(fill=tk.X, padx=20, pady=15)
        
        tk.Label(progress_frame, text=f"{today_cals:.0f} / {daily_goal} cal",
                fg=COLORS["accent"], bg=COLORS["bg_card"],
                font=("Arial", 20, "bold")).pack()
        
        bar_canvas = tk.Canvas(progress_frame, height=25, bg=COLORS["bg"],
                              highlightthickness=0)
        bar_canvas.pack(fill=tk.X, pady=10)
        
        bar_canvas.create_rectangle(0, 0, 1000, 25, fill=COLORS["bg"], outline="")
        bar_width = int((progress_pct / 100) * 340)
        color = COLORS["green"] if progress_pct >= 100 else COLORS["accent"]
        bar_canvas.create_rectangle(0, 0, bar_width, 25, fill=color, outline="")
        bar_canvas.create_text(170, 12, text=f"{progress_pct:.0f}%",
                              fill=COLORS["text"], font=("Arial", 12, "bold"))
        
        # Weekly progress
        weekly_card = tk.Frame(left_panel, bg=COLORS["bg_card"])
        weekly_card.pack(fill=tk.X, pady=10, padx=10)
        
        tk.Label(weekly_card, text="📅 WEEKLY PROGRESS",
                fg=COLORS["text"], bg=COLORS["bg_card"],
                font=("Arial", 16, "bold")).pack(anchor="w", padx=20, pady=(15,10))
        
        weekly_goal = user_data.get('weekly_calorie_goal', 1000)
        week_pct = min(100, (week_cals / weekly_goal * 100)) if weekly_goal > 0 else 0
        
        week_frame = tk.Frame(weekly_card, bg=COLORS["bg_card"])
        week_frame.pack(fill=tk.X, padx=20, pady=15)
        
        tk.Label(week_frame, text=f"{week_cals:.0f} / {weekly_goal} cal",
                fg=COLORS["blue"], bg=COLORS["bg_card"],
                font=("Arial", 20, "bold")).pack()
        
        week_bar = tk.Canvas(week_frame, height=25, bg=COLORS["bg"],
                            highlightthickness=0)
        week_bar.pack(fill=tk.X, pady=10)
        
        week_bar.create_rectangle(0, 0, 1000, 25, fill=COLORS["bg"], outline="")
        week_bar_width = int((week_pct / 100) * 340)
        week_color = COLORS["green"] if week_pct >= 100 else COLORS["blue"]
        week_bar.create_rectangle(0, 0, week_bar_width, 25, fill=week_color, outline="")
        week_bar.create_text(170, 12, text=f"{week_pct:.0f}%",
                            fill=COLORS["text"], font=("Arial", 12, "bold"))
        
        # Achievements
        achieve_card = tk.Frame(left_panel, bg=COLORS["bg_card"])
        achieve_card.pack(fill=tk.BOTH, expand=True, pady=10, padx=10)
        
        tk.Label(achieve_card, text="🏆 ACHIEVEMENTS",
                fg=COLORS["text"], bg=COLORS["bg_card"],
                font=("Arial", 16, "bold")).pack(anchor="w", padx=20, pady=(15,10))
        
        achievements = user_data.get('achievements', [])
        if achievements:
            achieve_scroll = tk.Canvas(achieve_card, bg=COLORS["bg_card"],
                                      highlightthickness=0, height=150)
            achieve_scroll.pack(fill=tk.BOTH, padx=20, pady=(0,15))
            
            for i, ach in enumerate(achievements[-5:]):
                achieve_scroll.create_text(10, i*30, text=ach, anchor="w",
                                          fill=COLORS["yellow"],
                                          font=("Arial", 11, "bold"))
        else:
            tk.Label(achieve_card, text="Complete workouts to unlock achievements!",
                    fg=COLORS["text_dim"], bg=COLORS["bg_card"],
                    font=("Arial", 11)).pack(padx=20, pady=20)
        
        # Right panel - Exercises
        right_panel = tk.Frame(content, bg=COLORS["bg"])
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10)
        
        tk.Label(right_panel, text="💪 RECOMMENDED FOR YOU",
                fg=COLORS["accent"], bg=COLORS["bg"],
                font=("Arial", 24, "bold")).pack(pady=20)
        
        recommended = UserManager.get_recommended_exercises(self.current_user)
        
        for exercise in recommended:
            ex_data = EXERCISES[exercise]
            card = tk.Frame(right_panel, bg=COLORS["bg_card"])
            card.pack(fill=tk.X, pady=8, padx=20)
            
            def on_enter(e, c=card):
                c.config(bg=COLORS["bg_card_hover"], cursor="hand2")
            def on_leave(e, c=card):
                c.config(bg=COLORS["bg_card"])
            
            card.bind("<Enter>", on_enter)
            card.bind("<Leave>", on_leave)
            card.bind("<Button-1>", lambda e, ex=exercise: self.start_exercise(ex))
            
            inner = tk.Frame(card, bg=COLORS["bg_card"])
            inner.pack(fill=tk.X, padx=25, pady=20)
            
            left_ex = tk.Frame(inner, bg=COLORS["bg_card"])
            left_ex.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            
            title_text = f"{ex_data['icon']} {exercise.upper()}"
            tk.Label(left_ex, text=title_text, fg=COLORS["accent"],
                    bg=COLORS["bg_card"], font=("Arial", 18, "bold")).pack(anchor="w")
            
            tk.Label(left_ex, text=ex_data['description'],
                    fg=COLORS["text_dim"], bg=COLORS["bg_card"],
                    font=("Arial", 11)).pack(anchor="w", pady=(5,0))
            
            meta = f"🔥 {ex_data['calories']} cal/rep | {ex_data['difficulty']} | {ex_data['category']}"
            tk.Label(left_ex, text=meta, fg=COLORS["text"],
                    bg=COLORS["bg_card"], font=("Arial", 10)).pack(anchor="w", pady=(8,0))
            
            right_ex = tk.Frame(inner, bg=COLORS["bg_card"])
            right_ex.pack(side=tk.RIGHT)
            
            pr = user_data.get('personal_records', {}).get(exercise, 0)
            if pr > 0:
                tk.Label(right_ex, text=f"PR: {pr}",
                        fg=COLORS["yellow"], bg=COLORS["bg_card"],
                        font=("Arial", 14, "bold")).pack(anchor="e")
        
        # All exercises button
        GlowButton(right_panel, text="📋 VIEW ALL EXERCISES",
                  bg=COLORS["secondary"], activebackground="#ff33ff",
                  fg=COLORS["text"], font=("Arial", 14, "bold"),
                  padx=40, pady=15, command=self.show_all_exercises).pack(pady=30)
    
    def show_all_exercises(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("📋 ALL EXERCISES")
        dialog.geometry("900x700")
        dialog.configure(bg=COLORS["bg"])
        dialog.transient(self.root)
        
        tk.Label(dialog, text="📋 ALL EXERCISES",
                fg=COLORS["accent"], bg=COLORS["bg"],
                font=("Arial", 28, "bold")).pack(pady=30)
        
        canvas = tk.Canvas(dialog, bg=COLORS["bg"], highlightthickness=0)
        scrollbar = tk.Scrollbar(dialog, orient="vertical", command=canvas.yview)
        scrollable = tk.Frame(canvas, bg=COLORS["bg"])
        
        scrollable.bind("<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        for exercise, data in EXERCISES.items():
            card = tk.Frame(scrollable, bg=COLORS["bg_card"])
            card.pack(fill=tk.X, pady=8, padx=40)
            
            def make_handler(ex):
                return lambda e: (dialog.destroy(), self.start_exercise(ex))
            
            card.bind("<Button-1>", make_handler(exercise))
            
            def on_enter(e, c=card):
                c.config(bg=COLORS["bg_card_hover"], cursor="hand2")
            def on_leave(e, c=card):
                c.config(bg=COLORS["bg_card"])
            
            card.bind("<Enter>", on_enter)
            card.bind("<Leave>", on_leave)
            
            inner = tk.Frame(card, bg=COLORS["bg_card"])
            inner.pack(fill=tk.X, padx=25, pady=20)
            
            tk.Label(inner, text=f"{data['icon']} {exercise}",
                    fg=COLORS["accent"], bg=COLORS["bg_card"],
                    font=("Arial", 16, "bold")).pack(anchor="w")
            
            tk.Label(inner, text=data['description'],
                    fg=COLORS["text_dim"], bg=COLORS["bg_card"],
                    font=("Arial", 11)).pack(anchor="w", pady=(5,0))
            
            tips = " • " + " • ".join(data['form_tips'])
            tk.Label(inner, text=tips, fg=COLORS["text"],
                    bg=COLORS["bg_card"], font=("Arial", 9)).pack(anchor="w", pady=(8,0))
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=20, pady=20)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=20)
        
        GlowButton(dialog, text="✕ CLOSE",
                  bg=COLORS["red"], activebackground="#ff3366",
                  fg=COLORS["text"], font=("Arial", 14, "bold"),
                  padx=40, pady=12, command=dialog.destroy).pack(pady=20)
    
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
        self.feedback_text = "READY!"
        self.form_scores.clear()
        
        # Target reps dialog
        target = simpledialog.askinteger("🎯 SET TARGET",
                                        f"How many {exercise} reps?",
                                        minvalue=5, maxvalue=100,
                                        initialvalue=10)
        self.target_reps = target if target else 10
        
        self.pose = mp_pose.Pose(min_detection_confidence=0.6,
                                min_tracking_confidence=0.6)
        self.cap = cv2.VideoCapture(0)
        
        # Top bar
        top_bar = tk.Frame(self.root, bg=COLORS["bg_card"], height=80)
        top_bar.pack(fill=tk.X)
        top_bar.pack_propagate(False)
        
        tk.Label(top_bar, text=f"{EXERCISES[exercise]['icon']} {exercise.upper()}",
                fg=COLORS["accent"], bg=COLORS["bg_card"],
                font=("Arial", 24, "bold")).pack(side=tk.LEFT, padx=30, pady=20)
        
        self.stats_label = AnimatedLabel(top_bar,
                                         text=f"REPS: 0/{self.target_reps} | 🔥 0 CAL",
                                         fg=COLORS["text"], bg=COLORS["bg_card"],
                                         font=("Arial", 18, "bold"))
        self.stats_label.pack(side=tk.LEFT, padx=30)
        
        # Video
        self.video_label = tk.Label(self.root, bg=COLORS["bg"])
        self.video_label.pack(pady=20)
        
        # Feedback
        feedback_frame = tk.Frame(self.root, bg=COLORS["bg_card"], height=100)
        feedback_frame.pack(fill=tk.X, padx=20, pady=10)
        feedback_frame.pack_propagate(False)
        
        self.feedback_label = AnimatedLabel(feedback_frame,
                                           text="READY WHEN YOU ARE!",
                                           fg=COLORS["accent"],
                                           bg=COLORS["bg_card"],
                                           font=("Arial", 26, "bold"))
        self.feedback_label.pack(expand=True)
        
        # Controls
        controls = tk.Frame(self.root, bg=COLORS["bg"])
        controls.pack(pady=15)
        
        GlowButton(controls, text="⏸ PAUSE",
                  bg=COLORS["yellow"], activebackground="#ffee33",
                  fg=COLORS["bg"], font=("Arial", 12, "bold"),
                  padx=20, pady=10, command=self.toggle_pause).pack(side=tk.LEFT, padx=5)
        
        GlowButton(controls, text="⏱ REST TIMER",
                  bg=COLORS["blue"], activebackground=COLORS["cyan"],
                  fg=COLORS["text"], font=("Arial", 12, "bold"),
                  padx=20, pady=10, command=lambda: RestTimer(self.root, 60)).pack(side=tk.LEFT, padx=5)
        
        GlowButton(controls, text="✓ FINISH",
                  bg=COLORS["green"], activebackground="#33ff99",
                  fg=COLORS["bg"], font=("Arial", 12, "bold"),
                  padx=20, pady=10, command=self.finish_workout).pack(side=tk.LEFT, padx=5)
        
        GlowButton(controls, text="⬅ BACK",
                  bg=COLORS["red"], activebackground="#ff3366",
                  fg=COLORS["text"], font=("Arial", 12, "bold"),
                  padx=20, pady=10, command=self.stop_exercise).pack(side=tk.LEFT, padx=5)
        
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
        
        avg_form = np.mean(list(self.form_scores)) if self.form_scores else 0
        
        new_achievements = UserManager.save_workout(
            self.current_user, self.exercise,
            self.rep_count, self.total_calories, avg_form
        )
        
        msg = f"🎉 WORKOUT COMPLETE!\n\n"
        msg += f"Exercise: {self.exercise}\n"
        msg += f"Reps: {self.rep_count}/{self.target_reps}\n"
        msg += f"Calories: {self.total_calories:.1f}\n"
        msg += f"Avg Form Score: {avg_form:.0f}%\n"
        
        if new_achievements:
            msg += f"\n🏆 NEW ACHIEVEMENTS:\n"
            for ach in new_achievements:
                msg += f"   {ach}\n"
        
        messagebox.showinfo("✅ WORKOUT COMPLETE", msg)
        self.build_dashboard()
    
    def calculate_form_score(self, angle, low, high):
        """Calculate form quality score 0-100"""
        mid = (low + high) / 2
        range_size = high - low
        deviation = abs(angle - mid)
        score = max(0, 100 - (deviation / range_size * 200))
        return score
    
    def rep_feedback(self, rep_duration, form_score):
        if rep_duration < 0.6:
            return "TOO FAST! 🟠", COLORS["orange"]
        elif rep_duration > 5:
            return "TOO SLOW! 🟡", COLORS["yellow"]
        elif form_score >= 90:
            return "PERFECT FORM! ✅", COLORS["green"]
        elif form_score >= 70:
            return "GOOD FORM 👍", COLORS["blue"]
        else:
            return "NEEDS IMPROVEMENT ⚠️", COLORS["red"]
    
    def update_frame(self):
        if not self.running:
            return
        
        if self.is_paused:
            self.feedback_label.config(text="⏸ PAUSED", fg=COLORS["yellow"])
            self.update_id = self.root.after(100, self.update_frame)
            return
        
        ret, frame = self.cap.read()
        if not ret:
            self.feedback_label.config(text="📷 NO CAMERA", fg=COLORS["red"])
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
            
            # Exercise logic
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
                    
                    form_score = self.calculate_form_score(knee_angle, low_knee, high_knee)
                    self.form_scores.append(form_score)
                    
                    if torso_angle < torso_min:
                        self.feedback_text, color = "LEAN TOO FORWARD ⚠️", COLORS["red"]
                    elif knee_angle < 70:
                        self.feedback_text, color = "TOO DEEP! 🟠", COLORS["orange"]
                    else:
                        self.feedback_text, color = self.rep_feedback(rep_duration, form_score)
                    
                    self.rep_count += 1
                    self.total_calories += EXERCISES[self.exercise]["calories"]
                    
                    self.feedback_label.config(text=self.feedback_text, fg=color)
                    self.feedback_label.pulse()
                    
                    self.stats_label.config(
                        text=f"REPS: {self.rep_count}/{self.target_reps} | 🔥 {self.total_calories:.1f} CAL"
                    )
                    self.stats_label.pulse()
                
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
            
            elif self.exercise == "Lunges":
                hip, knee, ankle = p(L.RIGHT_HIP), p(L.RIGHT_KNEE), p(L.RIGHT_ANKLE)
                ang = smooth(self.angle_buf, angle(hip, knee, ankle))
                low, high = 70, 170
            
            elif self.exercise == "Jumping Jacks":
                shoulder, hip, knee = p(L.RIGHT_SHOULDER), p(L.RIGHT_HIP), p(L.RIGHT_KNEE)
                ang = smooth(self.angle_buf, angle(shoulder, hip, knee))
                low, high = 150, 180
            
            # Rep detection for non-squat exercises
            if self.exercise != "Squats":
                cur_state = "UP" if ang > high else "DOWN" if ang < low else None
                if self.prev_state == "DOWN" and cur_state == "UP":
                    now = time.time()
                    rep_duration = now - self.last_rep_time
                    self.last_rep_time = now
                    
                    form_score = self.calculate_form_score(ang, low, high)
                    self.form_scores.append(form_score)
                    
                    self.feedback_text, color = self.rep_feedback(rep_duration, form_score)
                    
                    self.rep_count += 1
                    self.total_calories += EXERCISES[self.exercise]["calories"]
                    
                    self.feedback_label.config(text=self.feedback_text, fg=color)
                    self.feedback_label.pulse()
                    
                    self.stats_label.config(
                        text=f"REPS: {self.rep_count}/{self.target_reps} | 🔥 {self.total_calories:.1f} CAL"
                    )
                    self.stats_label.pulse()
                
                if cur_state in ("UP", "DOWN"):
                    self.prev_state = cur_state
            
            # Draw landmarks
            mp_drawing.draw_landmarks(
                output, results.pose_landmarks, mp_pose.POSE_CONNECTIONS,
                mp_drawing.DrawingSpec(color=(0, 212, 255), thickness=3, circle_radius=4),
                mp_drawing.DrawingSpec(color=(0, 255, 136), thickness=3, circle_radius=3)
            )
        
        # Check if target reached
        if self.rep_count >= self.target_reps:
            self.finish_workout()
            return
        
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
