# 💪 AI Gym Trainer Pro - Web Application

## Overview
A professional, tech-themed web application for AI-powered gym workout tracking with real-time pose detection, form analysis, and personalized workout recommendations based on BMI.

## Features

### ✅ Core Features
1. **User Profile Management**
   - Create and manage user profiles
   - BMI calculation and categorization
   - Fitness goal tracking

2. **5 Gym Exercises**
   - 🦵 Squats
   - 💪 Push-ups
   - 🔥 Bicep Curls
   - 🏋️ Plank (time-based)
   - 🏃 Lunges

3. **Real-Time Pose Detection**
   - Uses TensorFlow.js MoveNet model
   - Live camera feed with pose overlay
   - Automatic rep counting

4. **Form & Posture Analysis**
   - Real-time form scoring (0-100)
   - Visual feedback (Good/Warning/Bad)
   - Angle-based posture detection

5. **Workout Tracking**
   - Reps and sets tracking
   - Progress visualization
   - Session history

6. **BMI-Based Personalized Workouts**
   - Custom workout routines based on BMI category
   - Goal-specific recommendations (Weight Loss, Muscle Gain, etc.)
   - Adaptive difficulty levels

7. **Session Data Tracking**
   - Complete workout history
   - Statistics (total workouts, reps, sets)
   - Form scores per session
   - Local storage persistence

## How to Use

### 1. Setup
Simply open `index.html` in a modern web browser (Chrome, Firefox, Edge recommended).

### 2. Create Profile
1. Go to the **Profile** tab
2. Fill in your details:
   - Name
   - Age
   - Gender
   - Weight (kg)
   - Height (cm)
   - Fitness Goal
3. Click **Save Profile**

### 3. Start Workout
1. Go to the **Workout** tab
2. Select an exercise from the grid
3. Allow camera access when prompted
4. Position yourself in front of the camera
5. The app will automatically detect your pose and count reps

### 4. View Routine
1. Go to the **Routine** tab
2. View your personalized workout routine based on your BMI and goals
3. Follow the recommended exercises and sets

### 5. Check History
1. Go to the **History** tab
2. View all your past workout sessions
3. See statistics for each session

## Technical Details

### Technologies Used
- **HTML5/CSS3** - Modern responsive design
- **JavaScript (ES6+)** - Core functionality
- **TensorFlow.js** - Pose detection
- **MoveNet** - Lightweight pose detection model
- **LocalStorage** - Data persistence

### Browser Requirements
- Modern browser with WebRTC support (for camera)
- JavaScript enabled
- Camera access permissions

### Exercise Detection
- **Squats/Lunges**: Detects hip-knee-ankle angle
- **Push-ups/Bicep Curls**: Detects shoulder-elbow-wrist angle
- **Plank**: Detects body alignment (time-based)

### BMI Categories
- **Underweight** (BMI < 18.5): Focus on muscle building
- **Normal** (18.5-25): General fitness routines
- **Overweight** (25-30): Weight loss focus
- **Obese** (BMI > 30): Lower intensity, form-focused

## Design Theme
- **Dark gym aesthetic** with neon accents
- **Professional tech theme** with gradients
- **Responsive design** for all screen sizes
- **Smooth animations** and transitions

## Tips for Best Results
1. **Good Lighting**: Ensure you're in a well-lit area
2. **Full Body View**: Make sure your full body is visible in the camera
3. **Stable Position**: Keep the camera stable
4. **Clear Background**: Use a plain background for better detection
5. **Proper Form**: Focus on maintaining proper form for accurate detection

## Troubleshooting

### Camera Not Working
- Check browser permissions
- Try a different browser
- Ensure no other app is using the camera

### Pose Not Detected
- Ensure good lighting
- Stand further from camera
- Make sure your full body is visible

### Reps Not Counting
- Maintain proper form
- Complete full range of motion
- Check that all keypoints are visible

## Data Storage
All data is stored locally in your browser using LocalStorage. No data is sent to any server.

## Future Enhancements
- Export workout data to CSV/JSON
- Social sharing features
- Advanced analytics and charts
- More exercise types
- Workout scheduling
- Progress photos

---


