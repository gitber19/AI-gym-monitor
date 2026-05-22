// AI Gym Trainer Pro - Main Application
let detector = null;
let videoElement = null;
let canvasElement = null;
let ctx = null;
let currentExercise = null;
let isDetecting = false;
let animationFrame = null;

// Exercise definitions
const EXERCISES = {
    'squats': {
        name: 'Squats',
        icon: '🦵',
        category: 'Legs',
        targetReps: 12,
        targetSets: 3,
        muscleGroups: ['Quadriceps', 'Glutes', 'Hamstrings'],
        angleThresholds: {
            down: 80,
            up: 160
        },
        keypoints: {
            hip: 12,
            knee: 14,
            ankle: 16
        }
    },
    'pushups': {
        name: 'Push-ups',
        icon: '💪',
        category: 'Chest',
        targetReps: 10,
        targetSets: 3,
        muscleGroups: ['Chest', 'Triceps', 'Shoulders'],
        angleThresholds: {
            down: 90,
            up: 160
        },
        keypoints: {
            shoulder: 6,
            elbow: 8,
            wrist: 10
        }
    },
    'bicep_curls': {
        name: 'Bicep Curls',
        icon: '🔥',
        category: 'Arms',
        targetReps: 12,
        targetSets: 3,
        muscleGroups: ['Biceps', 'Forearms'],
        angleThresholds: {
            down: 40,
            up: 160
        },
        keypoints: {
            shoulder: 6,
            elbow: 8,
            wrist: 10
        }
    },
    'plank': {
        name: 'Plank',
        icon: '🏋️',
        category: 'Core',
        targetReps: 1, // Time-based
        targetSets: 3,
        muscleGroups: ['Core', 'Shoulders'],
        angleThresholds: {
            down: 170,
            up: 180
        },
        keypoints: {
            shoulder: 6,
            hip: 12,
            ankle: 16
        }
    },
    'lunges': {
        name: 'Lunges',
        icon: '🏃',
        category: 'Legs',
        targetReps: 10,
        targetSets: 3,
        muscleGroups: ['Quadriceps', 'Glutes'],
        angleThresholds: {
            down: 70,
            up: 160
        },
        keypoints: {
            hip: 12,
            knee: 14,
            ankle: 16
        }
    }
};

// User profile
let userProfile = {
    name: '',
    age: 0,
    gender: '',
    weight: 0,
    height: 0,
    bmi: 0,
    goal: 'general',
    totalWorkouts: 0,
    totalReps: 0,
    totalSets: 0,
    sessions: []
};

// Current workout session
let currentSession = {
    exercise: null,
    sets: [],
    currentSet: 1,
    reps: 0,
    formScores: [],
    startTime: null,
    endTime: null
};

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadProfile();
    initializeExercises();
    checkProfile();
});

// Screen navigation
function showScreen(screenName) {
    document.querySelectorAll('.screen').forEach(screen => {
        screen.classList.remove('active');
    });
    document.querySelectorAll('.nav-tab').forEach(tab => {
        tab.classList.remove('active');
    });
    
    document.getElementById(`${screenName}-screen`).classList.add('active');
    event.target.classList.add('active');
    
    if (screenName === 'routine') {
        generateRoutine();
    } else if (screenName === 'history') {
        displayHistory();
    }
}

// Profile management
function loadProfile() {
    const saved = localStorage.getItem('gymTrainerProfile');
    if (saved) {
        userProfile = JSON.parse(saved);
        displayProfile();
    }
}

function saveProfile() {
    const name = document.getElementById('profile-name').value;
    const age = parseInt(document.getElementById('profile-age').value);
    const gender = document.getElementById('profile-gender').value;
    const weight = parseFloat(document.getElementById('profile-weight').value);
    const height = parseFloat(document.getElementById('profile-height').value);
    const goal = document.getElementById('profile-goal').value;

    if (!name || !age || !weight || !height) {
        alert('Please fill in all fields');
        return;
    }

    userProfile.name = name;
    userProfile.age = age;
    userProfile.gender = gender;
    userProfile.weight = weight;
    userProfile.height = height;
    userProfile.bmi = calculateBMI(weight, height);
    userProfile.goal = goal;

    if (!userProfile.totalWorkouts) {
        userProfile.totalWorkouts = 0;
        userProfile.totalReps = 0;
        userProfile.totalSets = 0;
        userProfile.sessions = [];
    }

    localStorage.setItem('gymTrainerProfile', JSON.stringify(userProfile));
    displayProfile();
    alert('Profile saved successfully!');
}

function calculateBMI(weight, height) {
    const heightInMeters = height / 100;
    return (weight / (heightInMeters * heightInMeters)).toFixed(1);
}

function getBMICategory(bmi) {
    if (bmi < 18.5) return { category: 'Underweight', class: 'bmi-underweight', color: 'var(--gym-secondary)' };
    if (bmi < 25) return { category: 'Normal', class: 'bmi-normal', color: 'var(--gym-success)' };
    if (bmi < 30) return { category: 'Overweight', class: 'bmi-overweight', color: 'var(--gym-warning)' };
    return { category: 'Obese', class: 'bmi-obese', color: 'var(--gym-accent)' };
}

function displayProfile() {
    document.getElementById('profile-form').style.display = 'none';
    document.getElementById('profile-display').style.display = 'block';

    document.getElementById('display-bmi').textContent = userProfile.bmi;
    const bmiInfo = getBMICategory(userProfile.bmi);
    const bmiStatus = document.getElementById('bmi-status');
    bmiStatus.textContent = bmiInfo.category;
    bmiStatus.className = `bmi-indicator ${bmiInfo.class}`;

    document.getElementById('display-workouts').textContent = userProfile.totalWorkouts || 0;
    document.getElementById('display-reps').textContent = userProfile.totalReps || 0;
    document.getElementById('display-sets').textContent = userProfile.totalSets || 0;
}

function editProfile() {
    document.getElementById('profile-form').style.display = 'block';
    document.getElementById('profile-display').style.display = 'none';

    document.getElementById('profile-name').value = userProfile.name || '';
    document.getElementById('profile-age').value = userProfile.age || '';
    document.getElementById('profile-gender').value = userProfile.gender || 'male';
    document.getElementById('profile-weight').value = userProfile.weight || '';
    document.getElementById('profile-height').value = userProfile.height || '';
    document.getElementById('profile-goal').value = userProfile.goal || 'general';
}

function checkProfile() {
    if (!userProfile.name) {
        document.getElementById('profile-form').style.display = 'block';
        document.getElementById('profile-display').style.display = 'none';
    } else {
        displayProfile();
    }
}

// Exercise initialization
function initializeExercises() {
    const grid = document.getElementById('exercise-grid');
    grid.innerHTML = '';

    Object.keys(EXERCISES).forEach(key => {
        const exercise = EXERCISES[key];
        const card = document.createElement('div');
        card.className = 'exercise-card';
        card.onclick = () => startExercise(key);
        
        card.innerHTML = `
            <div class="exercise-icon">${exercise.icon}</div>
            <div class="exercise-name">${exercise.name}</div>
            <div class="exercise-info">
                <div>${exercise.category}</div>
                <div>${exercise.targetSets} sets × ${exercise.targetReps} reps</div>
            </div>
        `;
        
        grid.appendChild(card);
    });
}

// Start exercise
async function startExercise(exerciseKey) {
    if (!userProfile.name) {
        alert('Please create your profile first!');
        showScreen('profile');
        return;
    }

    currentExercise = { ...EXERCISES[exerciseKey], exercise: exerciseKey };
    currentSession = {
        exercise: exerciseKey,
        sets: [],
        currentSet: 1,
        reps: 0,
        formScores: [],
        startTime: new Date().toISOString(),
        endTime: null
    };

    document.getElementById('exercise-grid').style.display = 'none';
    document.getElementById('workout-session').style.display = 'block';
    document.getElementById('current-exercise-name').textContent = currentExercise.name;

    await initializeCamera();
    await initializePoseDetection();
    startDetection();
    updateWorkoutUI();
}

// Camera and pose detection
async function initializeCamera() {
    videoElement = document.getElementById('video');
    canvasElement = document.getElementById('canvas');
    ctx = canvasElement.getContext('2d');

    try {
        const stream = await navigator.mediaDevices.getUserMedia({
            video: { width: 640, height: 480 }
        });
        videoElement.srcObject = stream;
    } catch (error) {
        alert('Error accessing camera: ' + error.message);
        console.error(error);
    }
}

async function initializePoseDetection() {
    try {
        await tf.ready();
        const model = poseDetection.SupportedModels.MoveNet;
        detector = await poseDetection.createDetector(model, {
            modelType: poseDetection.movenet.modelType.SINGLEPOSE_LIGHTNING
        });
    } catch (error) {
        console.error('Error initializing pose detection:', error);
        alert('Error initializing pose detection');
    }
}

let angleBuffer = [];
let lastState = null;
let repCount = 0;
let plankStartTime = null;
let plankTimer = null;

function startDetection() {
    if (isDetecting) return;
    isDetecting = true;
    detectPose();
}

async function detectPose() {
    if (!isDetecting || !detector || !videoElement) return;

    try {
        const poses = await detector.estimatePoses(videoElement);
        
        if (poses.length > 0) {
            const pose = poses[0];
            drawPose(pose);
            processExercise(pose);
        } else {
            showFeedback('No pose detected', 'warning');
        }
    } catch (error) {
        console.error('Detection error:', error);
    }

    if (isDetecting) {
        animationFrame = requestAnimationFrame(detectPose);
    }
}

function drawPose(pose) {
    const videoWidth = videoElement.videoWidth;
    const videoHeight = videoElement.videoHeight;

    canvasElement.width = videoWidth;
    canvasElement.height = videoHeight;

    ctx.clearRect(0, 0, videoWidth, videoHeight);
    ctx.drawImage(videoElement, 0, 0, videoWidth, videoHeight);

    // Draw keypoints
    pose.keypoints.forEach(kp => {
        if (kp.score > 0.3) {
            ctx.beginPath();
            ctx.arc(kp.x, kp.y, 5, 0, 2 * Math.PI);
            ctx.fillStyle = '#ff0040';
            ctx.fill();
        }
    });

    // Draw connections
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
            ctx.strokeStyle = '#00d4ff';
            ctx.lineWidth = 3;
            ctx.stroke();
        }
    });
}

function calculateAngle(p1, p2, p3) {
    const radians = Math.atan2(p3.y - p2.y, p3.x - p2.x) - Math.atan2(p1.y - p2.y, p1.x - p2.x);
    let angle = Math.abs(radians * 180.0 / Math.PI);
    if (angle > 180.0) angle = 360 - angle;
    return angle;
}

function smoothAngle(newAngle) {
    angleBuffer.push(newAngle);
    if (angleBuffer.length > 5) angleBuffer.shift();
    return angleBuffer.reduce((a, b) => a + b, 0) / angleBuffer.length;
}

function processExercise(pose) {
    if (!currentExercise) return;

    const kp = pose.keypoints;
    let angle = 0;
    let state = null;

    // Get exercise key from currentExercise
    const exerciseKey = currentExercise.exercise;
    
    // Get keypoints based on exercise type
    if (exerciseKey === 'squats' || exerciseKey === 'lunges') {
        const hip = kp[currentExercise.keypoints.hip];
        const knee = kp[currentExercise.keypoints.knee];
        const ankle = kp[currentExercise.keypoints.ankle];
        
        if (hip.score > 0.3 && knee.score > 0.3 && ankle.score > 0.3) {
            angle = calculateAngle(hip, knee, ankle);
            angle = smoothAngle(angle);
            
            if (angle < currentExercise.angleThresholds.down) {
                state = 'DOWN';
            } else if (angle > currentExercise.angleThresholds.up) {
                state = 'UP';
            }
        }
    } else if (exerciseKey === 'pushups' || exerciseKey === 'bicep_curls') {
        const shoulder = kp[currentExercise.keypoints.shoulder];
        const elbow = kp[currentExercise.keypoints.elbow];
        const wrist = kp[currentExercise.keypoints.wrist];
        
        if (shoulder.score > 0.3 && elbow.score > 0.3 && wrist.score > 0.3) {
            angle = calculateAngle(shoulder, elbow, wrist);
            angle = smoothAngle(angle);
            
            if (angle < currentExercise.angleThresholds.down) {
                state = 'DOWN';
            } else if (angle > currentExercise.angleThresholds.up) {
                state = 'UP';
            }
        }
    } else if (exerciseKey === 'plank') {
        // Plank is time-based, check alignment
        const shoulder = kp[currentExercise.keypoints.shoulder];
        const hip = kp[currentExercise.keypoints.hip];
        const ankle = kp[currentExercise.keypoints.ankle];
        
        if (shoulder.score > 0.3 && hip.score > 0.3 && ankle.score > 0.3) {
            // Check if body is straight (plank form)
            const bodyAngle = calculateAngle(shoulder, hip, ankle);
            angle = smoothAngle(bodyAngle);
            
            // For plank, we want the body to be relatively straight (close to 180)
            if (angle > 170) {
                state = 'GOOD';
            } else {
                state = 'BAD';
            }
        }
    }

    // Detect rep (for rep-based exercises) or track time (for plank)
    if (exerciseKey === 'plank') {
        if (state === 'GOOD' && !plankStartTime) {
            plankStartTime = Date.now();
            if (!plankTimer) {
                plankTimer = setInterval(() => {
                    if (plankStartTime) {
                        const elapsed = Math.floor((Date.now() - plankStartTime) / 1000);
                        // Update display - plank is time-based (target is usually 30-60 seconds)
                        const targetTime = 30; // 30 seconds per rep
                        if (elapsed >= targetTime) {
                            repCount++;
                            currentSession.reps++;
                            plankStartTime = null;
                            clearInterval(plankTimer);
                            plankTimer = null;
                            updateWorkoutUI();
                            showFeedback('Plank completed!', 'good');
                        }
                    }
                }, 1000);
            }
        } else if (state === 'BAD' && plankStartTime) {
            // Reset if form breaks
            plankStartTime = null;
            if (plankTimer) {
                clearInterval(plankTimer);
                plankTimer = null;
            }
        }
    } else {
        // Rep-based exercises
        if (state && state !== lastState) {
            if (lastState === 'DOWN' && state === 'UP') {
                repCount++;
                currentSession.reps++;
                currentSession.formScores.push(calculateFormScore(angle));
                updateWorkoutUI();
                showFeedback('Great rep!', 'good');
            }
            lastState = state;
        }
    }

    // Form feedback
    if (state) {
        const formFeedback = getFormFeedback(angle);
        updateFormDisplay(formFeedback);
    }
}

function calculateFormScore(angle) {
    // Simple form scoring based on angle range
    const mid = (currentExercise.angleThresholds.down + currentExercise.angleThresholds.up) / 2;
    const range = currentExercise.angleThresholds.up - currentExercise.angleThresholds.down;
    const deviation = Math.abs(angle - mid) / range;
    return Math.max(0, Math.min(100, (1 - deviation) * 100));
}

function getFormFeedback(angle) {
    const thresholds = currentExercise.angleThresholds;
    const mid = (thresholds.down + thresholds.up) / 2;
    
    if (Math.abs(angle - mid) < 20) {
        return { message: 'Perfect form!', type: 'good', score: 95 };
    } else if (angle < thresholds.down) {
        return { message: 'Go deeper', type: 'warning', score: 70 };
    } else if (angle > thresholds.up) {
        return { message: 'Not fully extended', type: 'warning', score: 75 };
    }
    return { message: 'Good form', type: 'good', score: 85 };
}

function updateFormDisplay(feedback) {
    const overlay = document.getElementById('feedback-overlay');
    overlay.textContent = feedback.message;
    overlay.className = `feedback-overlay feedback-${feedback.type}`;
    overlay.style.display = 'block';
    
    const avgScore = currentSession.formScores.length > 0
        ? Math.round(currentSession.formScores.reduce((a, b) => a + b, 0) / currentSession.formScores.length)
        : 0;
    document.getElementById('form-score').textContent = avgScore;
}

function showFeedback(message, type) {
    const overlay = document.getElementById('feedback-overlay');
    overlay.textContent = message;
    overlay.className = `feedback-overlay feedback-${type}`;
    overlay.style.display = 'block';
    
    setTimeout(() => {
        overlay.style.display = 'none';
    }, 2000);
}

// Workout UI updates
function updateWorkoutUI() {
    document.getElementById('current-set').textContent = currentSession.currentSet;
    document.getElementById('current-reps').textContent = currentSession.reps;
    document.getElementById('total-reps').textContent = userProfile.totalReps + currentSession.reps;
    
    const progress = (currentSession.reps / currentExercise.targetReps) * 100;
    const progressBar = document.getElementById('set-progress');
    progressBar.style.width = `${Math.min(100, progress)}%`;
    progressBar.textContent = `${Math.round(Math.min(100, progress))}%`;
    
    if (currentSession.reps >= currentExercise.targetReps) {
        document.getElementById('complete-set-btn').disabled = false;
    }
}

function completeSet() {
    currentSession.sets.push({
        reps: currentSession.reps,
        formScore: currentSession.formScores.length > 0
            ? Math.round(currentSession.formScores.reduce((a, b) => a + b, 0) / currentSession.formScores.length)
            : 0
    });
    
    if (currentSession.currentSet < currentExercise.targetSets) {
        currentSession.currentSet++;
        currentSession.reps = 0;
        repCount = 0;
        angleBuffer = [];
        lastState = null;
        document.getElementById('complete-set-btn').disabled = true;
        document.getElementById('next-set-btn').style.display = 'none';
        showFeedback('Set completed! Ready for next set?', 'good');
    } else {
        endWorkout();
    }
}

function nextSet() {
    currentSession.reps = 0;
    repCount = 0;
    angleBuffer = [];
    lastState = null;
    document.getElementById('complete-set-btn').disabled = true;
    document.getElementById('next-set-btn').style.display = 'none';
}

function endWorkout() {
    if (isDetecting) {
        isDetecting = false;
        if (animationFrame) {
            cancelAnimationFrame(animationFrame);
        }
        if (videoElement && videoElement.srcObject) {
            videoElement.srcObject.getTracks().forEach(track => track.stop());
        }
        if (detector) {
            detector.dispose();
            detector = null;
        }
    }
    
    // Clean up plank timer
    if (plankTimer) {
        clearInterval(plankTimer);
        plankTimer = null;
    }
    plankStartTime = null;

    currentSession.endTime = new Date().toISOString();
    
    // Save session
    userProfile.sessions.push({
        ...currentSession,
        date: new Date().toISOString()
    });
    
    userProfile.totalWorkouts++;
    userProfile.totalReps += currentSession.reps;
    userProfile.totalSets += currentSession.sets.length;
    
    localStorage.setItem('gymTrainerProfile', JSON.stringify(userProfile));
    
    // Reset UI
    document.getElementById('exercise-grid').style.display = 'grid';
    document.getElementById('workout-session').style.display = 'none';
    
    alert(`Workout completed! ${currentSession.reps} reps across ${currentSession.sets.length} sets.`);
    
    currentExercise = null;
    currentSession = null;
    repCount = 0;
    angleBuffer = [];
    lastState = null;
    plankStartTime = null;
    if (plankTimer) {
        clearInterval(plankTimer);
        plankTimer = null;
    }
}

// Workout routine generation
function generateRoutine() {
    if (!userProfile.name) {
        document.getElementById('routine-content').innerHTML = `
            <p style="color: var(--gym-text-dim); text-align: center; padding: 40px;">
                Create your profile to get personalized workout recommendations based on your BMI and fitness goals.
            </p>
        `;
        return;
    }

    const bmi = parseFloat(userProfile.bmi);
    const goal = userProfile.goal;
    const routine = getPersonalizedRoutine(bmi, goal);
    
    let html = '<div>';
    routine.forEach((day, index) => {
        html += `
            <div class="routine-card">
                <div class="routine-day">Day ${index + 1}</div>
                ${day.exercises.map(ex => `
                    <div class="routine-exercise">
                        <span>${ex.icon} ${ex.name}</span>
                        <span>${ex.sets} sets × ${ex.reps} reps</span>
                    </div>
                `).join('')}
                <div style="margin-top: 10px; color: var(--gym-text-dim); font-size: 0.9em;">
                    ${day.reasoning}
                </div>
            </div>
        `;
    });
    html += '</div>';
    
    document.getElementById('routine-content').innerHTML = html;
}

function getPersonalizedRoutine(bmi, goal) {
    const bmiCategory = getBMICategory(bmi).category;
    const routines = {
        'Underweight': {
            'muscle_gain': [
                {
                    exercises: [
                        { name: 'Squats', icon: '🦵', sets: 3, reps: 12 },
                        { name: 'Push-ups', icon: '💪', sets: 3, reps: 10 },
                        { name: 'Bicep Curls', icon: '🔥', sets: 3, reps: 12 }
                    ],
                    reasoning: 'Focus on compound movements for muscle building. Start with moderate weights.'
                },
                {
                    exercises: [
                        { name: 'Lunges', icon: '🏃', sets: 3, reps: 10 },
                        { name: 'Plank', icon: '🏋️', sets: 3, reps: 1 },
                        { name: 'Push-ups', icon: '💪', sets: 3, reps: 8 }
                    ],
                    reasoning: 'Continue building strength with variations. Focus on form over intensity.'
                }
            ]
        },
        'Normal': {
            'general': [
                {
                    exercises: [
                        { name: 'Squats', icon: '🦵', sets: 3, reps: 12 },
                        { name: 'Push-ups', icon: '💪', sets: 3, reps: 10 },
                        { name: 'Plank', icon: '🏋️', sets: 3, reps: 1 }
                    ],
                    reasoning: 'Balanced routine for overall fitness. Maintain current form.'
                },
                {
                    exercises: [
                        { name: 'Lunges', icon: '🏃', sets: 3, reps: 10 },
                        { name: 'Bicep Curls', icon: '🔥', sets: 3, reps: 12 },
                        { name: 'Squats', icon: '🦵', sets: 3, reps: 12 }
                    ],
                    reasoning: 'Variety in exercises to prevent plateaus.'
                }
            ]
        },
        'Overweight': {
            'weight_loss': [
                {
                    exercises: [
                        { name: 'Squats', icon: '🦵', sets: 3, reps: 10 },
                        { name: 'Lunges', icon: '🏃', sets: 3, reps: 8 },
                        { name: 'Plank', icon: '🏋️', sets: 3, reps: 1 }
                    ],
                    reasoning: 'Lower intensity, higher volume for calorie burn. Focus on form.'
                },
                {
                    exercises: [
                        { name: 'Push-ups', icon: '💪', sets: 2, reps: 8 },
                        { name: 'Squats', icon: '🦵', sets: 3, reps: 10 },
                        { name: 'Plank', icon: '🏋️', sets: 3, reps: 1 }
                    ],
                    reasoning: 'Build endurance while maintaining proper form.'
                }
            ]
        },
        'Obese': {
            'weight_loss': [
                {
                    exercises: [
                        { name: 'Squats', icon: '🦵', sets: 2, reps: 8 },
                        { name: 'Plank', icon: '🏋️', sets: 2, reps: 1 },
                        { name: 'Push-ups', icon: '💪', sets: 2, reps: 5 }
                    ],
                    reasoning: 'Start slow with lower reps. Focus on proper form and gradual progression.'
                },
                {
                    exercises: [
                        { name: 'Plank', icon: '🏋️', sets: 3, reps: 1 },
                        { name: 'Squats', icon: '🦵', sets: 2, reps: 8 },
                        { name: 'Lunges', icon: '🏃', sets: 2, reps: 6 }
                    ],
                    reasoning: 'Continue building strength. Listen to your body and rest when needed.'
                }
            ]
        }
    };

    // Default routine if specific combination not found
    const defaultRoutine = [
        {
            exercises: [
                { name: 'Squats', icon: '🦵', sets: 3, reps: 12 },
                { name: 'Push-ups', icon: '💪', sets: 3, reps: 10 },
                { name: 'Bicep Curls', icon: '🔥', sets: 3, reps: 12 }
            ],
            reasoning: 'General fitness routine. Adjust based on your progress.'
        }
    ];

    return (routines[bmiCategory] && routines[bmiCategory][goal]) || defaultRoutine;
}

// History display
function displayHistory() {
    if (!userProfile.sessions || userProfile.sessions.length === 0) {
        document.getElementById('history-content').innerHTML = `
            <p style="color: var(--gym-text-dim); text-align: center; padding: 40px;">
                No workout history yet. Start your first workout!
            </p>
        `;
        return;
    }

    let html = '';
    userProfile.sessions.slice().reverse().forEach(session => {
        const date = new Date(session.date);
        const exercise = EXERCISES[session.exercise];
        const totalReps = session.sets.reduce((sum, set) => sum + set.reps, 0);
        const avgFormScore = session.sets.length > 0
            ? Math.round(session.sets.reduce((sum, set) => sum + set.formScore, 0) / session.sets.length)
            : 0;

        html += `
            <div class="history-item">
                <div>
                    <div style="font-weight: bold; margin-bottom: 5px;">
                        ${exercise ? exercise.icon + ' ' + exercise.name : 'Exercise'}
                    </div>
                    <div class="history-date">${date.toLocaleDateString()} ${date.toLocaleTimeString()}</div>
                </div>
                <div class="history-stats">
                    <div class="history-stat">
                        <div class="history-stat-value">${session.sets.length}</div>
                        <div class="history-stat-label">Sets</div>
                    </div>
                    <div class="history-stat">
                        <div class="history-stat-value">${totalReps}</div>
                        <div class="history-stat-label">Reps</div>
                    </div>
                    <div class="history-stat">
                        <div class="history-stat-value">${avgFormScore}%</div>
                        <div class="history-stat-label">Form</div>
                    </div>
                </div>
            </div>
        `;
    });

    document.getElementById('history-content').innerHTML = html;
}

