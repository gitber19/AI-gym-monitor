import React, { useState, useEffect, useRef } from 'react';

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

// User Manager
const UserManager = {
  listUsers: () => {
    const users = [];
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key.startsWith('user_')) {
        users.push(key.substring(5));
      }
    }
    return users.sort();
  },

  createUser: (username, age, weight, height, dailyGoal, weeklyGoal, fitnessGoal) => {
    if (localStorage.getItem(`user_${username}`)) return false;
    
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
    
    localStorage.setItem(`user_${username}`, JSON.stringify(userData));
    return true;
  },

  loadUser: (username) => {
    const data = localStorage.getItem(`user_${username}`);
    return data ? JSON.parse(data) : null;
  },

  saveWorkout: (username, exercise, reps, calories) => {
    const userData = UserManager.loadUser(username);
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
    localStorage.setItem(`user_${username}`, JSON.stringify(userData));
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
    const userData = UserManager.loadUser(username);
    if (!userData) return 0;
    
    const today = new Date().toISOString().split('T')[0];
    return userData.workouts
      .filter(w => w.date.startsWith(today))
      .reduce((sum, w) => sum + w.calories_burned, 0);
  }
};

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
  const [poseDetectorReady, setPoseDetectorReady] = useState(false);
  const [cameraError, setCameraError] = useState(false);

  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const detectorRef = useRef(null);
  const animationRef = useRef(null);
  const angleBufferRef = useRef([]);
  const prevStateRef = useRef(null);
  const lastRepTimeRef = useRef(Date.now());

  useEffect(() => {
    setUsers(UserManager.listUsers());
  }, []);

  useEffect(() => {
    if (screen === 'exercise' && exercise) {
      initCamera();
    }
    return () => {
      stopCamera();
    };
  }, [screen, exercise]);

  const initCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ 
        video: { width: 640, height: 480 } 
      });
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        videoRef.current.onloadedmetadata = () => {
          videoRef.current.play();
          loadPoseDetector();
        };
      }
    } catch (err) {
      setCameraError(true);
      setFeedback('CAMERA ERROR - Please allow camera access');
      setFeedbackColor(COLORS.red);
    }
  };

  const loadPoseDetector = async () => {
    try {
      // Load MediaPipe Pose from CDN
      const script1 = document.createElement('script');
      script1.src = 'https://cdn.jsdelivr.net/npm/@mediapipe/pose@0.5.1675469404/pose.js';
      script1.crossOrigin = 'anonymous';
      
      const script2 = document.createElement('script');
      script2.src = 'https://cdn.jsdelivr.net/npm/@mediapipe/camera_utils@0.3.1675466862/camera_utils.js';
      script2.crossOrigin = 'anonymous';

      document.head.appendChild(script1);
      document.head.appendChild(script2);

      script1.onload = () => {
        script2.onload = () => {
          const pose = new window.Pose({
            locateFile: (file) => `https://cdn.jsdelivr.net/npm/@mediapipe/pose@0.5.1675469404/${file}`
          });

          pose.setOptions({
            modelComplexity: 1,
            smoothLandmarks: true,
            minDetectionConfidence: 0.5,
            minTrackingConfidence: 0.5
          });

          pose.onResults(onPoseResults);
          
          detectorRef.current = pose;
          
          const camera = new window.Camera(videoRef.current, {
            onFrame: async () => {
              if (!isPaused && detectorRef.current) {
                await detectorRef.current.send({image: videoRef.current});
              }
            },
            width: 640,
            height: 480
          });
          
          camera.start();
          setPoseDetectorReady(true);
        };
      };
    } catch (err) {
      console.error('Failed to load pose detector:', err);
      setFeedback('POSE DETECTION ERROR');
      setFeedbackColor(COLORS.red);
    }
  };

  const stopCamera = () => {
    if (animationRef.current) {
      cancelAnimationFrame(animationRef.current);
    }
    if (videoRef.current && videoRef.current.srcObject) {
      videoRef.current.srcObject.getTracks().forEach(track => track.stop());
    }
    setPoseDetectorReady(false);
  };

  const onPoseResults = (results) => {
    if (!results.poseLandmarks || isPaused) return;

    drawPose(results);
    processExercise(results.poseLandmarks);
  };

  const drawPose = (results) => {
    const canvas = canvasRef.current;
    const video = videoRef.current;
    if (!canvas || !video) return;

    const ctx = canvas.getContext('2d');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    ctx.save();
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(results.image, 0, 0, canvas.width, canvas.height);

    if (results.poseLandmarks) {
      // Draw connections
      const connections = [
        [11, 13], [13, 15], // Left arm
        [12, 14], [14, 16], // Right arm
        [11, 12], // Shoulders
        [11, 23], [12, 24], [23, 24], // Torso
        [23, 25], [25, 27], // Left leg
        [24, 26], [26, 28]  // Right leg
      ];

      ctx.strokeStyle = COLORS.cyan;
      ctx.lineWidth = 3;

      connections.forEach(([i, j]) => {
        const kp1 = results.poseLandmarks[i];
        const kp2 = results.poseLandmarks[j];
        if (kp1 && kp2) {
          ctx.beginPath();
          ctx.moveTo(kp1.x * canvas.width, kp1.y * canvas.height);
          ctx.lineTo(kp2.x * canvas.width, kp2.y * canvas.height);
          ctx.stroke();
        }
      });

      // Draw keypoints
      results.poseLandmarks.forEach(kp => {
        ctx.beginPath();
        ctx.arc(kp.x * canvas.width, kp.y * canvas.height, 5, 0, 2 * Math.PI);
        ctx.fillStyle = COLORS.accent;
        ctx.fill();
      });
    }

    ctx.restore();
  };

  const processExercise = (landmarks) => {
    let angle = 0;
    let low = 0, high = 180;
    let state = null;

    const getPoint = (idx) => ({
      x: landmarks[idx].x,
      y: landmarks[idx].y
    });

    switch (exercise) {
      case "Bicep Curl":
        const rShoulder = getPoint(12);
        const rElbow = getPoint(14);
        const rWrist = getPoint(16);
        angle = calculateAngle(rShoulder, rElbow, rWrist);
        angle = smoothAngle(angleBufferRef.current, angle);
        low = 40; high = 160;
        state = angle < 80 ? "UP" : angle > 140 ? "DOWN" : null;
        break;

      case "Squats":
        const rHip = getPoint(24);
        const rKnee = getPoint(26);
        const rAnkle = getPoint(28);
        angle = calculateAngle(rHip, rKnee, rAnkle);
        angle = smoothAngle(angleBufferRef.current, angle);
        low = 65; high = 170;
        state = angle < 100 ? "DOWN" : angle > 150 ? "UP" : null;
        break;

      case "Overhead Tricep Extension":
        const rShoulder2 = getPoint(12);
        const rElbow2 = getPoint(14);
        const rWrist2 = getPoint(16);
        angle = calculateAngle(rShoulder2, rElbow2, rWrist2);
        angle = smoothAngle(angleBufferRef.current, angle);
        low = 50; high = 160;
        state = angle > 140 ? "UP" : angle < 80 ? "DOWN" : null;
        break;

      case "Pushups":
        const rShoulder3 = getPoint(12);
        const rElbow3 = getPoint(14);
        const rWrist3 = getPoint(16);
        angle = calculateAngle(rShoulder3, rElbow3, rWrist3);
        angle = smoothAngle(angleBufferRef.current, angle);
        low = 70; high = 160;
        state = angle < 100 ? "DOWN" : angle > 140 ? "UP" : null;
        break;

      case "Leg Raises":
        const rHip2 = getPoint(24);
        const rKnee2 = getPoint(26);
        const rAnkle2 = getPoint(28);
        angle = calculateAngle(rHip2, rKnee2, rAnkle2);
        angle = smoothAngle(angleBufferRef.current, angle);
        low = 90; high = 160;
        state = angle < 110 ? "UP" : angle > 140 ? "DOWN" : null;
        break;

      case "Lunges":
        const rHip3 = getPoint(24);
        const rKnee3 = getPoint(26);
        const rAnkle3 = getPoint(28);
        angle = calculateAngle(rHip3, rKnee3, rAnkle3);
        angle = smoothAngle(angleBufferRef.current, angle);
        low = 70; high = 170;
        state = angle < 100 ? "DOWN" : angle > 150 ? "UP" : null;
        break;

      case "Jumping Jacks":
        const rShoulder4 = getPoint(12);
        const rHip4 = getPoint(24);
        const rKnee4 = getPoint(26);
        angle = calculateAngle(rShoulder4, rHip4, rKnee4);
        angle = smoothAngle(angleBufferRef.current, angle);
        low = 150; high = 180;
        state = angle > 170 ? "UP" : angle < 160 ? "DOWN" : null;
        break;
    }

    setCurrentAngle(Math.round(angle));

    if (state && state !== prevStateRef.current) {
      if (prevStateRef.current === "DOWN" && state === "UP") {
        const newReps = repCount + 1;
        const newCals = totalCalories + EXERCISES[exercise].calories;
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
      prevStateRef.current = state;
      setCurrentState(state);
    }

    if (repCount > 0 && (state === "UP" || state === "DOWN")) {
      const [suggestion, color] = getSuggestion(angle, low, high, exercise);
      setFeedback(suggestion);
      setFeedbackColor(color);
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
    setCameraError(false);
    angleBufferRef.current = [];
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
          
          {Object.entries({
            username: 'USERNAME',
            age: 'AGE',
            weight: 'WEIGHT (KG)',
            height: 'HEIGHT (CM)'
          }).map(([key, label]) => (
            <div key={key} style={{ marginBottom: '20px' }}>
              <label style={{ color: COLORS.text, fontWeight: 'bold', display: 'block', marginBottom: '5px' }}>{label}</label>
              <input
                type={key === 'username' ? 'text' : 'number'}
                value={formData[key]}
                onChange={(e) => setFormData({...formData, [key]: e.target.value})}
                style={{ width: '100%', padding: '10px', background: COLORS.bg, color: COLORS.text, border: 'none', borderRadius: '5px' }}
              />
            </div>
          ))}

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

  if (screen === 'dashboard') {
    const userData = UserManager.loadUser(currentUser);
    const todayCals = UserManager.getTodayCalories(currentUser);

    return (
      <div style={{ background: COLORS.bg, minHeight: '100vh', padding: '20px' }}>
        <div style={{ background: COLORS.card, padding: '30px', borderRadius: '10px', marginBottom: '20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h1 style={{ color: COLORS.accent, fontSize: '32px', fontWeight: 'bold', margin: 0 }}>⚡ {currentUser.toUpperCase()}</h1>
            <p style={{ color: COLORS.text, marginTop: '10px', fontSize: '14px' }}>
              🔥 {userData.streak_days} DAYS | 💪 {userData.total_reps} REPS | 🏋️ {userData.total_workouts} WORKOUTS
            </p>
          </div>
          <button
            onClick={() => setScreen('home')}
            style={{ background: COLORS.red, color: COLORS.text, padding: '15px 30px', border: 'none', borderRadius: '5px', fontSize: '14px', fontWeight: 'bold', cursor: 'pointer' }}
          >
            ⬅ BACK
          </button>
        </div>

        <div style={{ background: COLORS.card, padding: '30px', borderRadius: '10px', marginBottom: '30px', textAlign: 'center' }}>
          <h2 style={{ color: COLORS.yellow, fontSize: '24px', fontWeight: 'bold' }}>
            TODAY: {todayCals.toFixed(1)} / {userData.daily_calorie_goal} CAL
          </h2>
        </div>

        <h2 style={{ color: COLORS.accent, textAlign: 'center', fontSize: '28px', fontWeight: 'bold', marginBottom: '30px' }}>
          SELECT EXERCISE
        </h2>

        <div style={{ maxWidth: '1000px', margin: '0 auto' }}>
          {Object.entries(EXERCISES).map(([name, data]) => (
            <div
              key={name}
              onClick={() => startExercise(name)}
              style={{ background: COLORS.card, padding: '20px', marginBottom: '15px', borderRadius: '10px', cursor: 'pointer', transition: 'transform 0.2s' }}
              onMouseEnter={(e) => e.currentTarget.style.transform = 'scale(1.02)'}
              onMouseLeave={(e) => e.currentTarget.style.transform = 'scale(1)'}
            >
              <div style={{ color: COLORS.text, fontSize: '18px', fontWeight: 'bold' }}>
                {data.icon} {name.toUpperCase()} | {data.category} | 🔥 {data.calories} cal/rep
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (screen === 'exercise') {
    return (
      <div style={{ background: COLORS.bg, minHeight: '100vh' }}>
        <div style={{ background: COLORS.card, padding: '20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h1 style={{ color: COLORS.accent, fontSize: '28px', fontWeight: 'bold', margin: 0 }}>
            {EXERCISES[exercise].icon} {exercise.toUpperCase()}
          </h1>
          <div style={{ color: COLORS.yellow, fontSize: '22px', fontWeight: 'bold' }}>
            REPS: {repCount} | 🔥 {totalCalories.toFixed(1)} CAL
          </div>
        </div>

        <div style={{ position: 'relative', textAlign: 'center', padding: '10px' }}>
          <video
            ref={videoRef}
            style={{ display: 'none' }}
            playsInline
          />
          <canvas
            ref={canvasRef}
            style={{ maxWidth: '100%', borderRadius: '10px' }}
          />
          {cameraError && (
            <div style={{ color: COLORS.red, fontSize: '20px', fontWeight: 'bold', marginTop: '20px' }}>
              CAMERA ACCESS DENIED - Please allow camera permissions
            </div>
          )}
          {!poseDetectorReady && !cameraError && (
            <div style={{ color: COLORS.yellow, fontSize: '20px', fontWeight: 'bold', marginTop: '20px' }}>
              LOADING POSE DETECTOR...
            </div>
          )}
        </div>

        <div style={{ background: COLORS.card, margin: '20px', padding: '30px', borderRadius: '10px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-around', alignItems: 'center', flexWrap: 'wrap', gap: '40px' }}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ color: COLORS.dim, fontSize: '14px', fontWeight: 'bold', marginBottom: '10px' }}>ANGLE</div>
              <div style={{ color: COLORS.cyan, fontSize: '48px', fontWeight: 'bold' }}>{currentAngle}°</div>
            </div>
            <div style={{ textAlign: 'center' }}>
              <div style={{ color: COLORS.dim, fontSize: '14px', fontWeight: 'bold', marginBottom: '10px' }}>STATUS</div>
              <div style={{ 
                color: currentState === 'UP' ? COLORS.green : currentState === 'DOWN' ? COLORS.orange : COLORS.yellow, 
                fontSize: '48px', 
                fontWeight: 'bold' 
              }}>
                {currentState === 'UP' ? 'UP ⬆' : currentState === 'DOWN' ? 'DOWN ⬇' : 'READY'}
              </div>
            </div>
          </div>
        </div>

        <div style={{ background: COLORS.card, margin: '20px', padding: '30px', borderRadius: '10px', textAlign: 'center' }}>
          <div style={{ color: feedbackColor, fontSize: '32px', fontWeight: 'bold' }}>
            {isPaused ? '⏸ PAUSED' : feedback}
          </div>
        </div>

        <div style={{ textAlign: 'center', padding: '20px' }}>
          <button
            onClick={() => setIsPaused(!isPaused)}
            style={{ background: COLORS.yellow, color: COLORS.bg, padding: '15px 30px', border: 'none', borderRadius: '5px', fontSize: '16px', fontWeight: 'bold', cursor: 'pointer', marginRight: '10px' }}
          >
            {isPaused ? '▶ RESUME' : '⏸ PAUSE'}
          </button>
          <button
            onClick={finishWorkout}
            style={{ background: COLORS.green, color: COLORS.bg, padding: '15px 30px', border: 'none', borderRadius: '5px', fontSize: '16px', fontWeight: 'bold', cursor: 'pointer', marginRight: '10px' }}
          >
            ✓ FINISH
          </button>
          <button
            onClick={() => { stopCamera(); setScreen('dashboard'); }}
            style={{ background: COLORS.red, color: COLORS.text, padding: '15px 30px', border: 'none', borderRadius: '5px', fontSize: '16px', fontWeight: 'bold', cursor: 'pointer' }}
          >
            ✕ QUIT
          </button>
        </div>
      </div>
    );
  }

  return null;