#!/usr/bin/env python3
"""
AI Pose Trainer Pro - Complete Enhanced Edition
Features: Sound effects, exercise recommendations, achievements, streaks, BMI tracking,
         workout history charts, form scoring, rest timer, custom exercises
"""

import cv2
import mediapipe as mp
import numpy as np
import math
import os
import warnings
import tkinter as tk
from tkinter import messagebox, ttk
from PIL import Image, ImageTk, ImageDraw, ImageFilter
from collections import deque
import time
import json
from datetime import datetime, timedelta
import threading
import random

# Sound effects
try:
    import pygame
    pygame.mixer.init()
    SOUND_AVAILABLE = True
except ImportError:
    SOUND_AVAILABLE = False
    print("⚠️  pygame not available - sound effects disabled")

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
SOUND_DIR = "sounds"
os.makedirs(USER_DATA_DIR, exist_ok=True)
os.makedirs(SOUND_DIR, exist_ok=True)

class SoundManager:
    """Enhanced sound effects manager"""
    sounds_cache = {}
    
    @staticmethod
    def create_sound(freq, duration=0.1):
        if not SOUND_AVAILABLE:
            return None
        try:
            sample_rate = 22050
            n_samples = int(duration * sample_rate)
            buf = np.sin(2 * np.pi * np.arange(n_samples) * freq / sample_rate)
            buf = (buf * 32767).astype(np.int16)
            sound = pygame.sndarray.make_sound(buf)
            sound.set_volume(0.3)
            return sound
        except:
            return None
    
    @staticmethod
    def play_rep_complete():
        if SOUND_AVAILABLE:
            sound = SoundManager.create_sound(800, 0.15)
            if sound: sound.play()
    
    @staticmethod
    def play_perfect():
        if SOUND_AVAILABLE:
            sound = SoundManager.create_sound(1000, 0.2)
            if sound: sound.play()
    
    @staticmethod
    def play_warning():
        if SOUND_AVAILABLE:
            sound = SoundManager.create_sound(400, 0.1)
            if sound: sound.play()
    
    @staticmethod
    def play_click():
        if SOUND_AVAILABLE:
            sound = SoundManager.create_sound(600, 0.05)
            if sound: sound.play()
    
    @staticmethod
    def play_success():
        if SOUND_AVAILABLE:
            for freq in [600, 800, 1000]:
                sound = SoundManager.create_sound(freq, 0.1)
                if sound:
                    sound.play()
                    time.sleep(0.05)

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
        self.bind("<Button-1>", self.on_click)
    
    def on_enter(self, e):
        self.config(bg=self.hover_bg, cursor="hand2")
    
    def on_leave(self, e):
        self.config(bg=self.default_bg)
    
    def on_click(self, e):
        SoundManager.play_click()

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
        SoundManager.play_click()
    
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
    
    @staticmethod
    def get_workout_history(username, days=7):
        """Get workout history for charts"""
        user_data = UserManager.load_user(username)
        if not user_data:
            return []
        
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        return [w for w in user_data.get("workouts", []) if w["date"] >= cutoff]

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
                SoundManager.play_warning()
            
            self.remaining -= 1
            self.window.after(1000, self.countdown)
        elif self.remaining == 0:
            SoundManager.play_success()
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
                SoundManager.play_success()
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
                   "✓ Workout History Charts", "✓ Rest Timer"]
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
                
                card.bind("<Enter>", on