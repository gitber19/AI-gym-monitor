#!/usr/bin/env python3
# ATTENTION!! This is the main code for detecting all you major joints in your body use ai to edit 
"""
pose_corrector.py — Enhanced Real-time Pose Corrector using MediaPipe and OpenCV
Features: Sound alerts, statistics tracking, posture scoring, session timer, export data
"""

import math
import time
from collections import deque
import cv2
import mediapipe as mp
import numpy as np
import os
import warnings
from datetime import datetime
import json

# Try to import sound libraries
SOUND_AVAILABLE = False
SOUND_TYPE = None

try:
    import winsound  # Windows
    SOUND_AVAILABLE = True
    SOUND_TYPE = "winsound"
except ImportError:
    try:
        import pygame
        pygame.mixer.init()
        SOUND_AVAILABLE = True
        SOUND_TYPE = "pygame"
    except ImportError:
        SOUND_AVAILABLE = False
        print("⚠️  Sound libraries not available - audio alerts disabled")

# Silence absl and mediapipe warnings
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
warnings.filterwarnings("ignore")

# --------- CONFIG ----------
BACK_STRAIGHT_MIN = 160
BACK_STRAIGHT_MAX = 180
KNEE_ALIGNMENT_MIN = 165
KNEE_ALIGNMENT_MAX = 180
ELBOW_EXTENDED_MIN = 160
ELBOW_EXTENDED_MAX = 180
NECK_TILT_MAX = 20
SMOOTHING_WINDOW = 5
SOUND_ALERT_INTERVAL = 3.0  # Minimum seconds between sound alerts
POSTURE_SCORE_UPDATE_INTERVAL = 0.5  # Update score every 0.5 seconds
# ----------------------------

mp_drawing = mp.solutions.drawing_utils
mp_pose = mp.solutions.pose
L = mp_pose.PoseLandmark


def angle_between(a, b, c):
    a, b, c = np.array(a), np.array(b), np.array(c)
    ba, bc = a - b, c - b
    norm = np.linalg.norm(ba) * np.linalg.norm(bc)
    if norm == 0:
        return 0.0
    cosang = np.clip(np.dot(ba, bc) / norm, -1.0, 1.0)
    return math.degrees(math.acos(cosang))


def smooth_deque(dq, value):
    dq.append(value)
    if len(dq) > SMOOTHING_WINDOW:
        dq.popleft()
    return float(np.median(np.array(dq)))


def check_back_straight(shoulder, hip, ankle): return angle_between(shoulder, hip, ankle)
def check_knee_alignment(hip, knee, ankle): return angle_between(hip, knee, ankle)
def check_elbow_extension(shoulder, elbow, wrist): return angle_between(shoulder, elbow, wrist)


def neck_tilt_angle(shoulder, ear):
    s, e = np.array(shoulder), np.array(ear)
    v = s - e
    vert = np.array([0.0, 1.0])
    norm_v = np.linalg.norm(v)
    if norm_v == 0:
        return 0.0
    cosang = np.clip(np.dot(v / norm_v, vert), -1.0, 1.0)
    return math.degrees(math.acos(cosang))


def play_alert_sound():
    """Play alert sound if available"""
    if not SOUND_AVAILABLE:
        return
    try:
        if SOUND_TYPE == "winsound":
            winsound.Beep(800, 150)  # Frequency, duration in ms
        elif SOUND_TYPE == "pygame":
            # Generate a simple beep sound
            sample_rate = 22050
            duration = 0.15
            samples = int(sample_rate * duration)
            buf = np.sin(2 * np.pi * np.arange(samples) * 800 / sample_rate)
            buf = (buf * 32767).astype(np.int16)
            sound = pygame.sndarray.make_sound(buf)
            sound.set_volume(0.3)
            sound.play()
    except Exception:
        pass  # Silently fail if sound doesn't work


def calculate_posture_score(hip_angle, left_knee, right_knee, left_elbow, right_elbow, neck):
    """Calculate overall posture score (0-100)"""
    score = 100.0
    issues = 0
    
    # Back alignment (weight: 30%)
    if hip_angle < BACK_STRAIGHT_MIN:
        back_penalty = (BACK_STRAIGHT_MIN - hip_angle) / BACK_STRAIGHT_MIN * 30
        score -= back_penalty
        issues += 1
    
    # Knees (weight: 20% each)
    if left_knee < KNEE_ALIGNMENT_MIN:
        knee_penalty = (KNEE_ALIGNMENT_MIN - left_knee) / KNEE_ALIGNMENT_MIN * 20
        score -= knee_penalty
        issues += 1
    if right_knee < KNEE_ALIGNMENT_MIN:
        knee_penalty = (KNEE_ALIGNMENT_MIN - right_knee) / KNEE_ALIGNMENT_MIN * 20
        score -= knee_penalty
        issues += 1
    
    # Elbows (weight: 10% each)
    if left_elbow < ELBOW_EXTENDED_MIN:
        elbow_penalty = (ELBOW_EXTENDED_MIN - left_elbow) / ELBOW_EXTENDED_MIN * 10
        score -= elbow_penalty
        issues += 1
    if right_elbow < ELBOW_EXTENDED_MIN:
        elbow_penalty = (ELBOW_EXTENDED_MIN - right_elbow) / ELBOW_EXTENDED_MIN * 10
        score -= elbow_penalty
        issues += 1
    
    # Neck (weight: 10%)
    if neck > NECK_TILT_MAX:
        neck_penalty = (neck - NECK_TILT_MAX) / NECK_TILT_MAX * 10
        score -= min(neck_penalty, 10)
        issues += 1
    
    return max(0, min(100, score)), issues


def draw_progress_bar(frame, x, y, width, height, progress, color):
    """Draw a progress bar on the frame"""
    cv2.rectangle(frame, (x, y), (x + width, y + height), (50, 50, 50), -1)
    cv2.rectangle(frame, (x, y), (x + int(width * progress / 100), y + height), color, -1)
    cv2.rectangle(frame, (x, y), (x + width, y + height), (255, 255, 255), 2)


def main():
    print("🟢 Enhanced Pose Corrector starting...")
    print("📊 Features: Sound alerts, Statistics, Posture scoring, Session timer")
    print("⌨️  Controls: Q/Esc = Quit, S = Save stats, R = Reset stats")
    
    cap = cv2.VideoCapture(0)

    # Force camera open check
    if not cap.isOpened():
        print("❌ Could not open webcam. Try closing other apps using it.")
        print("💡 Tip: Try different camera indices (0, 1, 2...) if you have multiple cameras")
        return
    else:
        print("✅ Webcam opened successfully. Press 'Q' or 'Esc' to quit.")

    # Warm up camera for a moment
    time.sleep(1.0)

    # Statistics tracking
    session_start_time = time.time()
    good_posture_time = 0.0
    bad_posture_time = 0.0
    last_posture_time = time.time()
    last_posture_state = True
    posture_scores = deque(maxlen=100)  # Keep last 100 scores
    last_sound_time = 0.0
    last_score_update = time.time()
    total_issues_detected = 0

    with mp_pose.Pose(
        static_image_mode=False,
        model_complexity=1,
        enable_segmentation=False,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
    ) as pose:

        hip_angle_buf, knee_left_buf, knee_right_buf = deque(), deque(), deque()
        elbow_left_buf, elbow_right_buf, neck_buf = deque(), deque(), deque()

        fps_time = time.time()
        cv2.namedWindow("Pose Corrector - Enhanced Edition", cv2.WINDOW_NORMAL)  # Force window creation

        while True:
            ret, frame = cap.read()
            if not ret:
                print("⚠️ Frame not received. Retrying...")
                continue

            h, w = frame.shape[:2]
            frame_rgb = cv2.cvtColor(cv2.flip(frame, 1), cv2.COLOR_BGR2RGB)
            results = pose.process(frame_rgb)
            frame_out = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)

            feedbacks = []
            current_time = time.time()
            is_good_posture = True

            if results.pose_landmarks:
                lm = results.pose_landmarks.landmark

                def p(idx): return (lm[idx].x * w, lm[idx].y * h)

                left_sh, right_sh = p(L.LEFT_SHOULDER), p(L.RIGHT_SHOULDER)
                left_hip, right_hip = p(L.LEFT_HIP), p(L.RIGHT_HIP)
                left_ankle, right_ankle = p(L.LEFT_ANKLE), p(L.RIGHT_ANKLE)
                left_knee, right_knee = p(L.LEFT_KNEE), p(L.RIGHT_KNEE)
                left_el, right_el = p(L.LEFT_ELBOW), p(L.RIGHT_ELBOW)
                left_w, right_w = p(L.LEFT_WRIST), p(L.RIGHT_WRIST)
                left_ear, right_ear = p(L.LEFT_EAR), p(L.RIGHT_EAR)

                mid_sh = ((left_sh[0] + right_sh[0]) / 2, (left_sh[1] + right_sh[1]) / 2)
                mid_hip = ((left_hip[0] + right_hip[0]) / 2, (left_hip[1] + right_hip[1]) / 2)
                mid_ankle = ((left_ankle[0] + right_ankle[0]) / 2, (left_ankle[1] + right_ankle[1]) / 2)

                hip_angle_s = smooth_deque(hip_angle_buf, check_back_straight(mid_sh, mid_hip, mid_ankle))
                left_knee_s = smooth_deque(knee_left_buf, check_knee_alignment(left_hip, left_knee, left_ankle))
                right_knee_s = smooth_deque(knee_right_buf, check_knee_alignment(right_hip, right_knee, right_ankle))
                left_elbow_s = smooth_deque(elbow_left_buf, check_elbow_extension(left_sh, left_el, left_w))
                right_elbow_s = smooth_deque(elbow_right_buf, check_elbow_extension(right_sh, right_el, right_w))

                neck_angle = 0.0
                if lm[L.LEFT_EAR].visibility > 0.2:
                    neck_angle = neck_tilt_angle(left_sh, left_ear)
                elif lm[L.RIGHT_EAR].visibility > 0.2:
                    neck_angle = neck_tilt_angle(right_sh, right_ear)
                neck_s = smooth_deque(neck_buf, neck_angle)

                # Calculate posture score
                posture_score, issue_count = calculate_posture_score(
                    hip_angle_s, left_knee_s, right_knee_s, 
                    left_elbow_s, right_elbow_s, neck_s
                )
                
                # Update score tracking
                if current_time - last_score_update >= POSTURE_SCORE_UPDATE_INTERVAL:
                    posture_scores.append(posture_score)
                    last_score_update = current_time

                # Determine if posture is good
                is_good_posture = (issue_count == 0)
                if issue_count > 0:
                    total_issues_detected += 1

                # Track time in good/bad posture
                elapsed = current_time - last_posture_time
                if last_posture_state != is_good_posture:
                    if last_posture_state:
                        good_posture_time += elapsed
                    else:
                        bad_posture_time += elapsed
                    last_posture_time = current_time
                    last_posture_state = is_good_posture
                elif current_time - last_posture_time > 0.1:  # Update every 100ms
                    if is_good_posture:
                        good_posture_time += elapsed
                    else:
                        bad_posture_time += elapsed
                    last_posture_time = current_time

                # Build feedback messages with color coding
                if hip_angle_s < BACK_STRAIGHT_MIN:
                    feedbacks.append((f"⚠️ Back bent ({int(hip_angle_s)}°)", (0, 100, 255)))  # Orange
                if left_knee_s < KNEE_ALIGNMENT_MIN:
                    feedbacks.append((f"⚠️ Left knee bent ({int(left_knee_s)}°)", (0, 100, 255)))
                if right_knee_s < KNEE_ALIGNMENT_MIN:
                    feedbacks.append((f"⚠️ Right knee bent ({int(right_knee_s)}°)", (0, 100, 255)))
                if left_elbow_s < ELBOW_EXTENDED_MIN:
                    feedbacks.append((f"⚠️ L elbow bent ({int(left_elbow_s)}°)", (0, 100, 255)))
                if right_elbow_s < ELBOW_EXTENDED_MIN:
                    feedbacks.append((f"⚠️ R elbow bent ({int(right_elbow_s)}°)", (0, 100, 255)))
                if neck_s > NECK_TILT_MAX:
                    feedbacks.append((f"⚠️ Neck tilt {int(neck_s)}°", (0, 100, 255)))

                if not feedbacks:
                    feedbacks.append(("✅ Posture OK!", (0, 255, 0)))  # Green

                # Play sound alert for bad posture
                if not is_good_posture and (current_time - last_sound_time) >= SOUND_ALERT_INTERVAL:
                    play_alert_sound()
                    last_sound_time = current_time

                # Draw pose landmarks with dynamic colors based on posture
                landmark_color = (0, 255, 0) if is_good_posture else (0, 0, 255)
                connection_color = (0, 200, 0) if is_good_posture else (0, 100, 255)
                
                mp_drawing.draw_landmarks(
                    frame_out, results.pose_landmarks, mp_pose.POSE_CONNECTIONS,
                    mp_drawing.DrawingSpec(color=landmark_color, thickness=2, circle_radius=3),
                    mp_drawing.DrawingSpec(color=connection_color, thickness=2, circle_radius=2)
                )

                # Draw feedback with colors
                for i, (msg, color) in enumerate(feedbacks):
                    cv2.putText(frame_out, msg, (10, 40 + i * 25),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                
                # Draw posture score
                avg_score = np.mean(posture_scores) if posture_scores else posture_score
                score_color = (0, 255, 0) if avg_score >= 80 else (0, 200, 255) if avg_score >= 60 else (0, 0, 255)
                
                # Draw score panel
                score_panel_y = h - 200
                cv2.rectangle(frame_out, (w - 250, score_panel_y), (w - 10, h - 10), (40, 40, 40), -1)
                cv2.rectangle(frame_out, (w - 250, score_panel_y), (w - 10, h - 10), (100, 100, 100), 2)
                
                cv2.putText(frame_out, "POSTURE SCORE", (w - 240, score_panel_y + 25),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
                cv2.putText(frame_out, f"{int(avg_score)}/100", (w - 240, score_panel_y + 55),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.0, score_color, 2)
                
                # Draw score progress bar
                draw_progress_bar(frame_out, w - 240, score_panel_y + 70, 220, 20, avg_score, score_color)
                
                # Draw session stats
                session_duration = current_time - session_start_time
                good_percentage = (good_posture_time / session_duration * 100) if session_duration > 0 else 0
                
                cv2.putText(frame_out, f"Session: {int(session_duration)}s", (w - 240, score_panel_y + 110),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
                cv2.putText(frame_out, f"Good: {good_percentage:.1f}%", (w - 240, score_panel_y + 130),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
                cv2.putText(frame_out, f"Issues: {total_issues_detected}", (w - 240, score_panel_y + 150),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 100, 255), 1)
            else:
                cv2.putText(frame_out, "No pose detected.", (10, 40),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

            fps = 1.0 / (time.time() - fps_time)
            fps_time = time.time()
            
            # Draw FPS and controls
            cv2.putText(frame_out, f"FPS: {int(fps)}", (10, 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            cv2.putText(frame_out, "Q/Esc: Quit | S: Save Stats | R: Reset", (10, h - 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1)

            cv2.imshow("Pose Corrector - Enhanced Edition", frame_out)

            # Handle keyboard input
            key = cv2.waitKey(1) & 0xFF
            if key in [27, ord('q'), ord('Q')]:
                print("👋 Exiting Pose Corrector.")
                break
            elif key in [ord('s'), ord('S')]:
                # Save statistics
                session_duration = time.time() - session_start_time
                final_good_time = good_posture_time + (session_duration - last_posture_time) if last_posture_state else good_posture_time
                final_bad_time = bad_posture_time + (session_duration - last_posture_time) if not last_posture_state else bad_posture_time
                
                stats = {
                    "session_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "session_duration_seconds": round(session_duration, 2),
                    "good_posture_time_seconds": round(final_good_time, 2),
                    "bad_posture_time_seconds": round(final_bad_time, 2),
                    "good_posture_percentage": round(final_good_time / session_duration * 100, 2) if session_duration > 0 else 0,
                    "average_posture_score": round(np.mean(posture_scores), 2) if posture_scores else 0,
                    "total_issues_detected": total_issues_detected,
                    "min_score": round(min(posture_scores), 2) if posture_scores else 0,
                    "max_score": round(max(posture_scores), 2) if posture_scores else 0
                }
                
                filename = f"posture_stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                with open(filename, 'w') as f:
                    json.dump(stats, f, indent=4)
                
                print(f"✅ Statistics saved to {filename}")
                print(f"📊 Session Summary:")
                print(f"   Duration: {stats['session_duration_seconds']}s")
                print(f"   Good Posture: {stats['good_posture_percentage']:.1f}%")
                print(f"   Avg Score: {stats['average_posture_score']:.1f}/100")
                print(f"   Issues Detected: {stats['total_issues_detected']}")
                
                # Visual confirmation
                cv2.putText(frame_out, "STATS SAVED!", (w // 2 - 100, h // 2),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 3)
                cv2.imshow("Pose Corrector - Enhanced Edition", frame_out)
                cv2.waitKey(1000)
                
            elif key in [ord('r'), ord('R')]:
                # Reset statistics
                session_start_time = time.time()
                good_posture_time = 0.0
                bad_posture_time = 0.0
                last_posture_time = time.time()
                last_posture_state = True
                posture_scores.clear()
                total_issues_detected = 0
                print("🔄 Statistics reset!")

    # Final statistics update
    session_duration = time.time() - session_start_time
    final_good_time = good_posture_time + (session_duration - last_posture_time) if last_posture_state else good_posture_time
    final_bad_time = bad_posture_time + (session_duration - last_posture_time) if not last_posture_state else bad_posture_time
    
    print("\n" + "="*50)
    print("📊 FINAL SESSION STATISTICS")
    print("="*50)
    print(f"Session Duration: {session_duration:.1f} seconds ({session_duration/60:.1f} minutes)")
    print(f"Good Posture Time: {final_good_time:.1f}s ({final_good_time/session_duration*100:.1f}%)")
    print(f"Bad Posture Time: {final_bad_time:.1f}s ({final_bad_time/session_duration*100:.1f}%)")
    if posture_scores:
        print(f"Average Posture Score: {np.mean(posture_scores):.1f}/100")
        print(f"Best Score: {max(posture_scores):.1f}/100")
        print(f"Worst Score: {min(posture_scores):.1f}/100")
    print(f"Total Issues Detected: {total_issues_detected}")
    print("="*50)

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
