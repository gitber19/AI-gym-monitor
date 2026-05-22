import React, { useState, useEffect, useRef } from 'react';
import * as tf from '@tensorflow/tfjs';
import * as poseDetection from '@tensorflow-models/pose-detection';

const COLORS = {
  bg: "#000000",
  card: "#1a1a1a",
  accent: "#00ff00",
  secondary: "#ff00ff",
  text: "#ffffff",
  dim: "#666666",
  green: "#00ff00",
  red: "#ff0000",
  yellow: "#ffff00",
  blue: "#0099ff",
  orange: "#ff6600",
  cyan: "#00ffff"
};

const EXERCISES = {
  "Squats": { calories: 0.38, icon: "🦵", category: "Legs" },
  "Bicep Curl": { calories: 0.15, icon: "💪", category: "Arms" },
  "Overhead Tricep Extension": { calories: 0.18, icon: "🔥", category: "Arms" },
  "Pushups": { calories: 0.35, icon: "🤜", category: "Chest" },
  "Leg Raises": { calories: 0.28, icon: "🦿", category: "Core" },
  "Lunges": { calories: 0.40, icon: "🏃", category: "Legs" },
  "Jumping Jacks": { calories: 0.45, icon: "⚡", category: "Cardio" }
};

const FITNESS_GOALS = {
  "Weight Loss": ["Jumping Jacks", "Squats", "Lunges"],
  "Muscle Building": ["Pushups", "Bicep Curl", "Overhead Tricep Extension"],
  "Endurance": ["Squats", "Jumping Jacks", "Leg Raises"],
  "General Fitness": ["Squats", "Pushups", "Leg Raises"]
};

// Utility functions
const calculateAngle = (a, b, c) => {
  const radians = Math.atan2(c.y - b.y, c.x - b.x) - Math.atan2(a.y - b.y, a.x - b.x);
  let angle = Math.abs(radians * 180.0 / Math.PI);
  if (angle > 180.0) angle = 360 - angle;
  return angle;
};

const smoothAngle = (buffer, newAngle, maxSize = 5) => {
  buffer.push(newAngle);
  if (buffer.length > maxSize) buffer.shift();
  return buffer.reduce((a, b) => a + b, 0) / buffer.length;
};

// FIX #5 & #6: Replace localStorage with in-memory storage + safe JSON parsing
const UserManager = (() => {
  const users = new Map(); // In-memory storage instead of localStorage
  
  const safeJSONParse = (str) => {
    try {
      return JSON.parse(str);
    } catch (e) {
      console.error('JSON parse error:', e);
      return null;
    }
  };

  return {
    listUsers: () => {
      return Array.from(users.keys()).sort();
    },

    createUser: (username, age, weight, height, dailyGoal, weeklyGoal, fitnessGoal) => {
      if (users.has(username)) return false;
      
      const bmi = weight / Math.pow(height / 100, 2);
      const userData = {
        username,
        age,
        weight,
        height,
        bmi: Math.round(bmi * 10) / 10,
        fitness_goal: fitnessGoal,
        daily_calorie_goal: dailyGoal,
        weekly_calorie_goal: weeklyGoal,
        created_date: new Date().toISOString(),
        total_workouts: 0,
        total_reps: 0,
        total_calories: 0,
        workouts: [],
        achievements: [],
        streak_days: 0,
        last_workout_date: null,
        personal_records: {}
      };
      
      users.set(username, userData);
      return true;
    },

    loadUser: (username) => {
      return users.get(username) || null;
    },

    saveWorkout: (username, exercise, reps, calories) => {
      const userData = users.get(username);
      if (!userData) return [];

      const workout = {
        date: new Date().toISOString(),
        exercise,
        reps,
        calories_burned: Math.round(calories * 100) / 100
      };

      userData.workouts.push(workout);
      userData.total_workouts++;
      userData.total_reps += reps;
      userData.total_calories += calories;

      if (!userData.personal_records[exercise] || reps > userData.personal_records[exercise]) {
        userData.personal_records[exercise] = reps;
      }

      const today = new Date().toISOString().split('T')[0];
      const lastDate = userData.last_workout_date;
      
      if (lastDate) {
        const last = new Date(lastDate);
        const todayDate = new Date(today);
        const diffDays = Math.floor((todayDate - last) / (1000 * 60 * 60 * 24));
        
        if (diffDays === 1) {
          userData.streak_days++;
        } else if (diffDays > 1) {
          userData.streak_days = 1;
        }
      } else {
        userData.streak_days = 1;
      }
      userData.last_workout_date = today;

      const newAchievements = UserManager.checkAchievements(userData);
      users.set(username, userData);
      return newAchievements;
    },

    checkAchievements: (userData) => {
      const achievements = userData.achievements || [];
      const newAchievements = [];
      const milestones = [
        [10, "🏆 First 10 Reps"],
        [50, "💪 Half Century"],
        [100, "🔥 Century Club"],
        [500, "⚡ Beast Mode"],
        [1000, "👑 Elite Athlete"]
      ];

      for (const [milestone, achievement] of milestones) {
        if (userData.total_reps >= milestone && !achievements.includes(achievement)) {
          newAchievements.push(achievement);
        }
      }

      userData.achievements = [...achievements, ...newAchievements];
      return newAchievements;
    },

    getTodayCalories: (username) => {
      const userData = users.get(username);
      if (!userData) return 0;
      
      const today = new Date().toISOString().split('T')[0];
      return userData.workouts
        .filter(w => w.date.startsWith(today))
        .reduce((sum, w) => sum + w.calories_burned, 0);
    }
  };
})();

export default function AIPoseTrainer() {
  const [screen, setScreen] = useState('home');
  const [users, setUsers] = useState([]);
  const [currentUser, setCurrentUser] = useState(null);
  const [exercise, setExercise] = useState(null);
  const [repCount, setRepCount] = useState(0);
  const [totalCalories, setTotalCalories] = useState(0);
  const [currentAngle, setCurrentAngle] = useState(0);
  const [currentState, setCurrentState] = useState('READY');
  const [feedback, setFeedback] = useState('GET READY!');
  const [feedbackColor, setFeedbackColor] = useState(COLORS.accent);
  const [isPaused, setIsPaused] = useState(false);
  const [showCreateUser, setShowCreateUser] = useState(false);

  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const detectorRef = useRef(null);
  const animationRef = useRef(null);
  const angleBufferRef = useRef([]);
  const prevStateRef = useRef(null);
  const lastRepTimeRef = useRef(Date.now());
  const isMountedRef = useRef(true); // FIX #7: Track component mount status

  useEffect(() => {
    setUsers(UserManager.listUsers());
  }, []);

  // FIX #3: Proper cleanup and dependency management
  useEffect(() => {
    isMountedRef.current = true;
    
    if (screen === 'exercise' && exercise) {
      initCamera();
    }
    
    return () => {
      isMountedRef.current = false;
      stopCamera();
    };
  }, [screen, exercise]);

  const initCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ 
        video: { width: 640, height: 480 } 
      });
      
      // FIX #10: Null check
      if (videoRef.current && isMountedRef.current) {
        videoRef.current.srcObject = stream;
        videoRef.current.onloadedmetadata = () => {
          if (videoRef.current && isMountedRef.current) {
            videoRef.current.play();
            loadPoseDetector();
          }
        };
      } else {
        // Clean up stream if component unmounted
        stream.getTracks().forEach(track => track.stop());
      }
    } catch (err) {
      console.error('Camera error:', err);
      if (isMountedRef.current) {
        setFeedback('CAMERA ERROR');
        setFeedbackColor(COLORS.red);
      }
    }
  };

  const loadPoseDetector = async () => {
    try {
      await tf.ready();
      const detector = await poseDetection.createDetector(
        poseDetection.SupportedModels.MoveNet,
        { modelType: poseDetection.movenet.modelType.SINGLEPOSE_LIGHTNING }
      );
      
      if (isMountedRef.current) {
        detectorRef.current = detector;
        detectPose();
      } else {
        // Clean up detector if component unmounted
        detector.dispose && detector.dispose();
      }
    } catch (err) {
      console.error('Pose detector error:', err);
      if (isMountedRef.current) {
        setFeedback('MODEL LOAD ERROR');
        setFeedbackColor(COLORS.red);
      }
    }
  };

  // FIX #8: Improved cleanup
  const stopCamera = () => {
    if (animationRef.current) {
      cancelAnimationFrame(animationRef.current);
      animationRef.current = null;
    }
    
    if (videoRef.current?.srcObject) {
      const tracks = videoRef.current.srcObject.getTracks();
      tracks.forEach(track => {
        track.stop();
        track.enabled = false;
      });
      videoRef.current.srcObject = null;
    }
    
    // FIX #2: Dispose TensorFlow resources
    if (detectorRef.current) {
      detectorRef.current.dispose && detectorRef.current.dispose();
      detectorRef.current = null;
    }
  };

  // FIX #4: Prevent race conditions
  const detectPose = async () => {
    // Stop if already running another loop
    if (animationRef.current !== null && animationRef.current !== undefined) {
      return;
    }

    const runDetection = async () => {
      // FIX #7 & #10: Check mounted status and null refs
      if (!isMountedRef.current || !detectorRef.current || !videoRef.current) {
        return;
      }

      if (isPaused) {
        animationRef.current = requestAnimationFrame(runDetection);
        return;
      }

      try {
        const poses = await detectorRef.current.estimatePoses(videoRef.current);
        
        if (poses.length > 0 && isMountedRef.current) {
          const pose = poses[0];
          drawPose(pose);
          processExercise(pose);
        }
      } catch (err) {
        console.error('Detection error:', err);
      }

      if (isMountedRef.current) {
        animationRef.current = requestAnimationFrame(runDetection);
      }
    };

    runDetection();
  };

  const drawPose = (pose) => {
    const canvas = canvasRef.current;
    const video = videoRef.current;
    if (!canvas || !video || !isMountedRef.current) return;

    const ctx = canvas.getContext('2d');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(video, 0, 0);

    pose.keypoints.forEach(kp => {
      if (kp.score > 0.3) {
        ctx.beginPath();
        ctx.arc(kp.x, kp.y, 5, 0, 2 * Math.PI);
        ctx.fillStyle = COLORS.accent;
        ctx.fill();
      }
    });

    const connections = [
      [5, 7], [7, 9], [6, 8], [8, 10],
      [5, 6], [5, 11], [6, 12], [11, 12],
      [11, 13], [13, 15], [12, 14], [14, 16]
    ];

    connections.forEach(([i, j]) => {
      const kp1 = pose.keypoints[i];
      const kp2 = pose.keypoints[j];
      if (kp1.score > 0.3 && kp2.score > 0.3) {
        ctx.beginPath();
        ctx.moveTo(kp1.x, kp1.y);
        ctx.lineTo(kp2.x, kp2.y);
        ctx.strokeStyle = COLORS.cyan;
        ctx.lineWidth = 3;
        ctx.stroke();
      }
    });
  };

  const processExercise = (pose) => {
    if (!isMountedRef.current) return; // FIX #7

    const kp = pose.keypoints;
    let angle = 0;
    let low = 0, high = 180;
    let state = null;

    const getKeypoint = (idx) => kp[idx];

    switch (exercise) {
      case "Bicep Curl":
        const rShoulder = getKeypoint(6);
        const rElbow = getKeypoint(8);
        const rWrist = getKeypoint(10);
        if (rShoulder.score > 0.3 && rElbow.score > 0.3 && rWrist.score > 0.3) {
          angle = calculateAngle(rShoulder, rElbow, rWrist);
          angle = smoothAngle(angleBufferRef.current, angle);
          low = 40; high = 160;
          state = angle < 80 ? "UP" : angle > 140 ? "DOWN" : null;
        }
        break;

      case "Squats":
        const rHip = getKeypoint(12);
        const rKnee = getKeypoint(14);
        const rAnkle = getKeypoint(16);
        if (rHip.score > 0.3 && rKnee.score > 0.3 && rAnkle.score > 0.3) {
          angle = calculateAngle(rHip, rKnee, rAnkle);
          angle = smoothAngle(angleBufferRef.current, angle);
          low = 65; high = 170;
          state = angle < 100 ? "DOWN" : angle > 150 ? "UP" : null;
        }
        break;

      case "Overhead Tricep Extension":
        const rShoulder2 = getKeypoint(6);
        const rElbow2 = getKeypoint(8);
        const rWrist2 = getKeypoint(10);
        if (rShoulder2.score > 0.3 && rElbow2.score > 0.3 && rWrist2.score > 0.3) {
          angle = calculateAngle(rShoulder2, rElbow2, rWrist2);
          angle = smoothAngle(angleBufferRef.current, angle);
          low = 50; high = 160;
          state = angle > 140 ? "UP" : angle < 80 ? "DOWN" : null;
        }
        break;

      case "Pushups":
        const rShoulder3 = getKeypoint(6);
        const rElbow3 = getKeypoint(8);
        const rWrist3 = getKeypoint(10);
        if (rShoulder3.score > 0.3 && rElbow3.score > 0.3 && rWrist3.score > 0.3) {
          angle = calculateAngle(rShoulder3, rElbow3, rWrist3);
          angle = smoothAngle(angleBufferRef.current, angle);
          low = 70; high = 160;
          state = angle < 100 ? "DOWN" : angle > 140 ? "UP" : null;
        }
        break;

      case "Leg Raises":
        const rHip2 = getKeypoint(12);
        const rKnee2 = getKeypoint(14);
        const rAnkle2 = getKeypoint(16);
        if (rHip2.score > 0.3 && rKnee2.score > 0.3 && rAnkle2.score > 0.3) {
          angle = calculateAngle(rHip2, rKnee2, rAnkle2);
          angle = smoothAngle(angleBufferRef.current, angle);
          low = 90; high = 160;
          state = angle < 110 ? "UP" : angle > 140 ? "DOWN" : null;
        }
        break;

      case "Lunges":
        const rHip3 = getKeypoint(12);
        const rKnee3 = getKeypoint(14);
        const rAnkle3 = getKeypoint(16);
        if (rHip3.score > 0.3 && rKnee3.score > 0.3 && rAnkle3.score > 0.3) {
          angle = calculateAngle(rHip3, rKnee3, rAnkle3);
          angle = smoothAngle(angleBufferRef.current, angle);
          low = 70; high = 170;
          state = angle < 100 ? "DOWN" : angle > 150 ? "UP" : null;
        }
        break;

      case "Jumping Jacks":
        const rShoulder4 = getKeypoint(6);
        const rHip4 = getKeypoint(12);
        const rKnee4 = getKeypoint(14);
        if (rShoulder4.score > 0.3 && rHip4.score > 0.3 && rKnee4.score > 0.3) {
          angle = calculateAngle(rShoulder4, rHip4, rKnee4);
          angle = smoothAngle(angleBufferRef.current, angle);
          low = 150; high = 180;
          state = angle > 170 ? "UP" : angle < 160 ? "DOWN" : null;
        }
        break;
    }

    if (!isMountedRef.current) return; // FIX #7
    setCurrentAngle(Math.round(angle));

    if (state && state !== prevStateRef.current) {
      if (prevStateRef.current === "DOWN" && state === "UP") {
        const newReps = repCount + 1;
        const newCals = totalCalories + EXERCISES[exercise].calories;
        
        if (isMountedRef.current) {
          setRepCount(newReps);
          setTotalCalories(newCals);

          const repTime = (Date.now() - lastRepTimeRef.current) / 1000;
          lastRepTimeRef.current = Date.now();

          if (repTime < 0.8) {
            setFeedback("TOO FAST! SLOW DOWN ⚠");
            setFeedbackColor(COLORS.orange);
          } else if (repTime > 4) {
            setFeedback("TOO SLOW! SPEED UP ⚠");
            setFeedbackColor(COLORS.orange);
          } else {
            setFeedback("GREAT REP! KEEP GOING! ✓");
            setFeedbackColor(COLORS.green);
          }
        }
      }
      prevStateRef.current = state;
      if (isMountedRef.current) {
        setCurrentState(state);
      }
    }

    if (repCount > 0 && (state === "UP" || state === "DOWN")) {
      const [suggestion, color] = getSuggestion(angle, low, high, exercise);
      if (isMountedRef.current) {
        setFeedback(suggestion);
        setFeedbackColor(color);
      }
    }
  };

  const getSuggestion = (angle, low, high, exercise) => {
    if (exercise === "Bicep Curl") {
      if (angle > 150) return ["LOWER THE WEIGHT ⬇", COLORS.yellow];
      if (angle < 50) return ["CURL UP MORE ⬆", COLORS.yellow];
      return ["GOOD FORM! ✓", COLORS.green];
    } else if (exercise === "Squats") {
      if (angle > 160) return ["GO DEEPER ⬇", COLORS.yellow];
      if (angle < 70) return ["DON'T GO TOO LOW! ⬆", COLORS.orange];
      return ["PERFECT DEPTH! ✓", COLORS.green];
    } else if (exercise === "Pushups") {
      if (angle > 150) return ["GO LOWER ⬇", COLORS.yellow];
      if (angle < 80) return ["PUSH UP! ⬆", COLORS.yellow];
      return ["GREAT FORM! ✓", COLORS.green];
    } else {
      if (angle > high - 10) return ["EXTEND MORE! ⬆", COLORS.yellow];
      if (angle < low + 10) return ["RELEASE SLOWLY ⬇", COLORS.yellow];
      return ["KEEP IT UP! ✓", COLORS.green];
    }
  };

  const startExercise = (ex) => {
    setExercise(ex);
    setRepCount(0);
    setTotalCalories(0);
    setCurrentAngle(0);
    setCurrentState('READY');
    setFeedback('GET READY!');
    setFeedbackColor(COLORS.accent);
    setIsPaused(false);
    angleBufferRef.current = []; // FIX #9: Reset angle buffer
    prevStateRef.current = null;
    lastRepTimeRef.current = Date.now();
    setScreen('exercise');
  };

  const finishWorkout = () => {
    stopCamera();
    const newAchievements = UserManager.saveWorkout(currentUser, exercise, repCount, totalCalories);
    
    let msg = `WORKOUT COMPLETE!\n\nExercise: ${exercise}\nReps: ${repCount}\nCalories: ${totalCalories.toFixed(1)}`;
    if (newAchievements.length > 0) {
      msg += `\n\nNEW ACHIEVEMENTS:\n${newAchievements.join('\n')}`;
    }
    alert(msg);
    setScreen('dashboard');
  };

  const CreateUserForm = () => {
    const [formData, setFormData] = useState({
      username: '',
      age: '',
      weight: '',
      height: '',
      dailyGoal: '200',
      weeklyGoal: '1400',
      fitnessGoal: 'General Fitness'
    });

    const handleSubmit = () => {
      try {
        const { username, age, weight, height, dailyGoal, weeklyGoal, fitnessGoal } = formData;
        if (!username) return alert('Username required');
        
        const success = UserManager.createUser(
          username,
          parseInt(age),
          parseFloat(weight),
          parseFloat(height),
          parseInt(dailyGoal),
          parseInt(weeklyGoal),
          fitnessGoal
        );

        if (success) {
          setUsers(UserManager.listUsers());
          setShowCreateUser(false);
        } else {
          alert('Username already exists');
        }
      } catch (err) {
        alert('Invalid input values');
      }
    };

    return (
      <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.9)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
        <div style={{ background: COLORS.card, padding: '40px', borderRadius: '10px', maxWidth: '500px', width: '90%', maxHeight: '90vh', overflow: 'auto' }}>
          <h2 style={{ color: COLORS.accent, marginBottom: '30px', textAlign: 'center' }}>CREATE NEW PROFILE</h2>
          
          <div style={{ marginBottom: '20px' }}>
            <label style={{ color: COLORS.text, fontWeight: 'bold', display: 'block', marginBottom: '5px' }}>USERNAME</label>
            <input
              type="text"
              value={formData.username}
              onChange={(e) => setFormData({...formData, username: e.target.value})}
              style={{ width: '100%', padding: '10px', background: COLORS.bg, color: COLORS.text, border: 'none', borderRadius: '5px' }}
            />
          </div>

          <div style={{ marginBottom: '20px' }}>
            <label style={{ color: COLORS.text, fontWeight: 'bold', display: 'block', marginBottom: '5px' }}>AGE</label>
            <input
              type="number"
              value={formData.age}
              onChange={(e) => setFormData({...formData, age: e.target.value})}
              style={{ width: '100%', padding: '10px', background: COLORS.bg, color: COLORS.text, border: 'none', borderRadius: '5px' }}
            />
          </div>

          <div style={{ marginBottom: '20px' }}>
            <label style={{ color: COLORS.text, fontWeight: 'bold', display: 'block', marginBottom: '5px' }}>WEIGHT (KG)</label>
            <input
              type="number"
              value={formData.weight}
              onChange={(e) => setFormData({...formData, weight: e.target.value})}
              style={{ width: '100%', padding: '10px', background: COLORS.bg, color: COLORS.text, border: 'none', borderRadius: '5px' }}
            />
          </div>

          <div style={{ marginBottom: '20px' }}>
            <label style={{ color: COLORS.text, fontWeight: 'bold', display: 'block', marginBottom: '5px' }}>HEIGHT (CM)</label>
            <input
              type="number"
              value={formData.height}
              onChange={(e) => setFormData({...formData, height: e.target.value})}
              style={{ width: '100%', padding: '10px', background: COLORS.bg, color: COLORS.text, border: 'none', borderRadius: '5px' }}
            />
          </div>

          <div style={{ marginBottom: '20px' }}>
            <label style={{ color: COLORS.text, fontWeight: 'bold', display: 'block', marginBottom: '10px' }}>FITNESS GOAL</label>
            {Object.keys(FITNESS_GOALS).map(goal => (
              <label key={goal} style={{ color: COLORS.text, display: 'block', marginBottom: '5px', cursor: 'pointer' }}>
                <input
                  type="radio"
                  value={goal}
                  checked={formData.fitnessGoal === goal}
                  onChange={(e) => setFormData({...formData, fitnessGoal: e.target.value})}
                  style={{ marginRight: '10px' }}
                />
                {goal}
              </label>
            ))}
          </div>

          <div style={{ marginBottom: '20px' }}>
            <label style={{ color: COLORS.text, fontWeight: 'bold', display: 'block', marginBottom: '5px' }}>DAILY CALORIE GOAL</label>
            <input
              type="number"
              value={formData.dailyGoal}
              onChange={(e) => setFormData({...formData, dailyGoal: e.target.value})}
              style={{ width: '100%', padding: '10px', background: COLORS.bg, color: COLORS.text, border: 'none', borderRadius: '5px' }}
            />
          </div>

          <div style={{ marginBottom: '30px' }}>
            <label style={{ color: COLORS.text, fontWeight: 'bold', display: 'block', marginBottom: '5px' }}>WEEKLY CALORIE GOAL</label>
            <input
              type="number"
              value={formData.weeklyGoal}
              onChange={(e) => setFormData({...formData, weeklyGoal: e.target.value})}
              style={{ width: '100%', padding: '10px', background: COLORS.bg, color: COLORS.text, border: 'none', borderRadius: '5px' }}
            />
          </div>

          <div style={{ display: 'flex', gap: '10px' }}>
            <button
              onClick={handleSubmit}
              style={{ flex: 1, padding: '15px', background: COLORS.green, color: COLORS.bg, border: 'none', borderRadius: '5px', fontWeight: 'bold', fontSize: '16px', cursor: 'pointer' }}
            >
              CREATE
            </button>
            <button
              onClick={() => setShowCreateUser(false)}
              style={{ flex: 1, padding: '15px', background: COLORS.red, color: COLORS.text, border: 'none', borderRadius: '5px', fontWeight: 'bold', fontSize: '16px', cursor: 'pointer' }}
            >
              CANCEL
            </button>
          </div>
        </div>
      </div>
    );
  };

  if (showCreateUser) {
    return <CreateUserForm />;
  }

  if (screen === 'home') {
    return (
      <div style={{ background: COLORS.bg, minHeight: '100vh', padding: '20px' }}>
        <h1 style={{ color: COLORS.accent, textAlign: 'center', fontSize: '60px', fontWeight: 'bold', marginTop: '50px' }}>⚡ AI POSE TRAINER</h1>
        
        {users.length > 0 && (
          <>
            <h2 style={{ color: COLORS.text, textAlign: 'center', fontSize: '20px', marginTop: '50px' }}>SELECT YOUR PROFILE</h2>
            <div style={{ maxWidth: '800px', margin: '30px auto' }}>
              {users.map(user => {
                const data = UserManager.loadUser(user);
                if (!data) return null; // FIX #10: Null check
                return (
                  <div
                    key={user}
                    onClick={() => { setCurrentUser(user); setScreen('dashboard'); }}
                    style={{ background: COLORS.card, padding: '20px', marginBottom: '15px', borderRadius: '10px', cursor: 'pointer', transition: 'transform 0.2s' }}
                    onMouseEnter={(e) => e.currentTarget.style.transform = 'scale(1.02)'}
                    onMouseLeave={(e) => e.currentTarget.style.transform = 'scale(1)'}
                  >
                    <div style={{ color: COLORS.text, fontSize: '20px', fontWeight: 'bold' }}>
                      👤 {user.toUpperCase()}
                    </div>
                    <div style={{ color: COLORS.dim, marginTop: '10px' }}>
                      🔥 {data.streak_days} days | 💪 {data.total_reps} reps | 🏋️ {data.total_workouts} workouts
                    </div>
                  </div>
                );
              })}
            </div>
          </>
        )}

        {users.length === 0 && (
          <p style={{ color: COLORS.dim, textAlign: 'center', fontSize: '18px', marginTop: '50px' }}>NO PROFILES FOUND</p>
        )}

        <div style={{ textAlign: 'center', marginTop: '50px' }}>
          <button
            onClick={() => setShowCreateUser(true)}
            style={{ background: COLORS.green, color: COLORS.bg, padding: '20px 40px', border: 'none', borderRadius: '10px', fontSize: '18px', fontWeight: 'bold', cursor: 'pointer' }}
          >
            ➕ CREATE NEW PROFILE
          </button>
        </div>
      </div>
    );
  }

  // FIX #1: Complete dashboard screen
  if (screen === 'dashboard') {
    const userData = UserManager.loadUser(currentUser);
    if (!userData) {
      setScreen('home');
      return null;
    }
    
    const todayCals = UserManager.getTodayCalories(currentUser);
    const dailyProgress = Math.min((todayCals / userData.daily_calorie_goal) * 100, 100);
    const recommendedExercises = FITNESS_GOALS[userData.fitness_goal] || [];

    return (
      <div style={{ background: COLORS.bg, minHeight: '100vh', padding: '20px' }}>
        <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '30px' }}>
            <h1 style={{ color: COLORS.accent, fontSize: '40px', fontWeight: 'bold' }}>
              👤 {currentUser.toUpperCase()}
            </h1>
            <button
              onClick={() => setScreen('home')}
              style={{ background: COLORS.red, color: COLORS.text, padding: '10px 20px', border: 'none', borderRadius: '5px', cursor: 'pointer', fontWeight: 'bold' }}
            >
              ← BACK
            </button>
          </div>

          {/* Stats Cards */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '20px', marginBottom: '30px' }}>
            <div style={{ background: COLORS.card, padding: '20px', borderRadius: '10px' }}>
              <div style={{ color: COLORS.dim, fontSize: '14px' }}>TOTAL WORKOUTS</div>
              <div style={{ color: COLORS.accent, fontSize: '32px', fontWeight: 'bold', marginTop: '10px' }}>
                {userData.total_workouts}
              </div>
            </div>
            <div style={{ background: COLORS.card, padding: '20px', borderRadius: '10px' }}>
              <div style={{ color: COLORS.dim, fontSize: '14px' }}>TOTAL REPS</div>
              <div style={{ color: COLORS.secondary, fontSize: '32px', fontWeight: 'bold', marginTop: '10px' }}>
                {userData.total_reps}
              </div>
            </div>
            <div style={{ background: COLORS.card, padding: '20px', borderRadius: '10px' }}>
              <div style={{ color: COLORS.dim, fontSize: '14px' }}>CALORIES BURNED</div>
              <div style={{ color: COLORS.orange, fontSize: '32px', fontWeight: 'bold', marginTop: '10px' }}>
                {Math.round(userData.total_calories)}
              </div>
            </div>
            <div style={{ background: COLORS.card, padding: '20px', borderRadius: '10px' }}>
              <div style={{ color: COLORS.dim, fontSize: '14px' }}>STREAK</div>
              <div style={{ color: COLORS.green, fontSize: '32px', fontWeight: 'bold', marginTop: '10px' }}>
                🔥 {userData.streak_days}
              </div>
            </div>
          </div>

          {/* Daily Goal Progress */}
          <div style={{ background: COLORS.card, padding: '20px', borderRadius: '10px', marginBottom: '30px' }}>
            <h3 style={{ color: COLORS.text, marginBottom: '15px' }}>TODAY'S CALORIE GOAL</h3>
            <div style={{ background: COLORS.bg, height: '30px', borderRadius: '15px', overflow: 'hidden' }}>
              <div style={{ 
                background: `linear-gradient(to right, ${COLORS.green}, ${COLORS.accent})`,
                height: '100%',
                width: `${dailyProgress}%`,
                transition: 'width 0.5s ease'
              }} />
            </div>
            <div style={{ color: COLORS.dim, marginTop: '10px' }}>
              {todayCals.toFixed(1)} / {userData.daily_calorie_goal} calories ({Math.round(dailyProgress)}%)
            </div>
          </div>

          {/* Recommended Exercises */}
          <div style={{ marginBottom: '30px' }}>
            <h2 style={{ color: COLORS.text, marginBottom: '20px' }}>
              RECOMMENDED EXERCISES ({userData.fitness_goal})
            </h2>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))', gap: '15px' }}>
              {recommendedExercises.map(ex => (
                <div
                  key={ex}
                  onClick={() => startExercise(ex)}
                  style={{ 
                    background: COLORS.card, 
                    padding: '20px', 
                    borderRadius: '10px', 
                    cursor: 'pointer',
                    border: `2px solid ${COLORS.accent}`,
                    transition: 'transform 0.2s'
                  }}
                  onMouseEnter={(e) => e.currentTarget.style.transform = 'scale(1.05)'}
                  onMouseLeave={(e) => e.currentTarget.style.transform = 'scale(1)'}
                >
                  <div style={{ fontSize: '40px', marginBottom: '10px' }}>{EXERCISES[ex].icon}</div>
                  <div style={{ color: COLORS.text, fontWeight: 'bold', fontSize: '18px' }}>{ex}</div>
                  <div style={{ color: COLORS.dim, marginTop: '5px' }}>
                    {EXERCISES[ex].calories} cal/rep • {EXERCISES[ex].category}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* All Exercises */}
          <div>
            <h2 style={{ color: COLORS.text, marginBottom: '20px' }}>ALL EXERCISES</h2>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))', gap: '15px' }}>
              {Object.entries(EXERCISES).map(([name, data]) => (
                <div
                  key={name}
                  onClick={() => startExercise(name)}
                  style={{ 
                    background: COLORS.card, 
                    padding: '20px', 
                    borderRadius: '10px', 
                    cursor: 'pointer',
                    transition: 'transform 0.2s',
                    border: '2px solid transparent'
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.transform = 'scale(1.05)';
                    e.currentTarget.style.borderColor = COLORS.secondary;
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.transform = 'scale(1)';
                    e.currentTarget.style.borderColor = 'transparent';
                  }}
                >
                  <div style={{ fontSize: '40px', marginBottom: '10px' }}>{data.icon}</div>
                  <div style={{ color: COLORS.text, fontWeight: 'bold', fontSize: '18px' }}>{name}</div>
                  <div style={{ color: COLORS.dim, marginTop: '5px' }}>
                    {data.calories} cal/rep • {data.category}
                  </div>
                  {userData.personal_records[name] && (
                    <div style={{ color: COLORS.accent, marginTop: '10px', fontSize: '14px' }}>
                      🏆 Best: {userData.personal_records[name]} reps
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Exercise Screen
  if (screen === 'exercise') {
    return (
      <div style={{ background: COLORS.bg, minHeight: '100vh', padding: '20px', position: 'relative' }}>
        <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
            <h1 style={{ color: COLORS.accent, fontSize: '36px', fontWeight: 'bold' }}>
              {exercise}
            </h1>
            <div style={{ display: 'flex', gap: '10px' }}>
              <button
                onClick={() => setIsPaused(!isPaused)}
                style={{ 
                  background: isPaused ? COLORS.green : COLORS.orange, 
                  color: COLORS.text, 
                  padding: '10px 20px', 
                  border: 'none', 
                  borderRadius: '5px', 
                  cursor: 'pointer', 
                  fontWeight: 'bold' 
                }}
              >
                {isPaused ? '▶ RESUME' : '⏸ PAUSE'}
              </button>
              <button
                onClick={finishWorkout}
                style={{ background: COLORS.red, color: COLORS.text, padding: '10px 20px', border: 'none', borderRadius: '5px', cursor: 'pointer', fontWeight: 'bold' }}
              >
                ✓ FINISH
              </button>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '20px' }}>
            {/* Video Feed */}
            <div style={{ position: 'relative' }}>
              <video
                ref={videoRef}
                style={{ display: 'none' }}
                playsInline
              />
              <canvas
                ref={canvasRef}
                style={{ 
                  width: '100%', 
                  height: 'auto', 
                  background: COLORS.card, 
                  borderRadius: '10px',
                  maxHeight: '70vh'
                }}
              />
              
              {/* Feedback Overlay */}
              <div style={{ 
                position: 'absolute', 
                top: '20px', 
                left: '50%', 
                transform: 'translateX(-50%)',
                background: 'rgba(0,0,0,0.8)',
                padding: '15px 30px',
                borderRadius: '10px',
                color: feedbackColor,
                fontSize: '24px',
                fontWeight: 'bold',
                textAlign: 'center',
                minWidth: '300px'
              }}>
                {feedback}
              </div>

              {/* Angle Display */}
              <div style={{ 
                position: 'absolute', 
                bottom: '20px', 
                left: '20px',
                background: 'rgba(0,0,0,0.8)',
                padding: '10px 20px',
                borderRadius: '10px',
                color: COLORS.cyan,
                fontSize: '32px',
                fontWeight: 'bold'
              }}>
                {currentAngle}°
              </div>

              {/* State Indicator */}
              <div style={{ 
                position: 'absolute', 
                bottom: '20px', 
                right: '20px',
                background: currentState === 'UP' ? COLORS.green : currentState === 'DOWN' ? COLORS.red : COLORS.yellow,
                padding: '10px 20px',
                borderRadius: '10px',
                color: COLORS.bg,
                fontSize: '20px',
                fontWeight: 'bold'
              }}>
                {currentState}
              </div>
            </div>

            {/* Stats Panel */}
            <div>
              <div style={{ background: COLORS.card, padding: '30px', borderRadius: '10px', marginBottom: '20px' }}>
                <div style={{ color: COLORS.dim, fontSize: '16px', marginBottom: '10px' }}>REPS</div>
                <div style={{ color: COLORS.accent, fontSize: '64px', fontWeight: 'bold' }}>
                  {repCount}
                </div>
              </div>

              <div style={{ background: COLORS.card, padding: '30px', borderRadius: '10px', marginBottom: '20px' }}>
                <div style={{ color: COLORS.dim, fontSize: '16px', marginBottom: '10px' }}>CALORIES</div>
                <div style={{ color: COLORS.orange, fontSize: '48px', fontWeight: 'bold' }}>
                  {totalCalories.toFixed(1)}
                </div>
              </div>

              <div style={{ background: COLORS.card, padding: '20px', borderRadius: '10px' }}>
                <div style={{ color: COLORS.dim, fontSize: '14px', marginBottom: '15px' }}>EXERCISE INFO</div>
                <div style={{ color: COLORS.text, marginBottom: '10px' }}>
                  <strong>Category:</strong> {EXERCISES[exercise].category}
                </div>
                <div style={{ color: COLORS.text, marginBottom: '10px' }}>
                  <strong>Cal/Rep:</strong> {EXERCISES[exercise].calories}
                </div>
                <div style={{ color: COLORS.text }}>
                  <strong>Goal:</strong> {UserManager.loadUser(currentUser)?.fitness_goal}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return null;
}
