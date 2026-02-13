<template>
  <div class="challenge-session">
    <!-- Placement guide overlay (first-time users) -->
    <div v-if="showPlacementGuide" class="placement-overlay" @click="dismissPlacementGuide">
      <div class="placement-card">
        <h2 class="placement-title">Phone Placement Guide</h2>
        <p class="placement-subtitle">Place your phone on the ground to the side, like this:</p>
        <div class="placement-img-wrap">
          <img src="/mobileplacement.png" alt="Phone placement guide" class="placement-img" />
          <div class="placement-highlight">
            <span class="highlight-ring"></span>
            <span class="highlight-label">Place phone here</span>
          </div>
        </div>
        <ul class="placement-tips">
          <li>Position at ground level, to your side</li>
          <li>Angle the camera so your full body is visible</li>
          <li>Keep ~1-2 meters distance</li>
        </ul>
        <button class="placement-btn" @click="dismissPlacementGuide">Got it, let's go!</button>
      </div>
    </div>

    <!-- Setup phase -->
    <div v-if="phase === 'setup'" class="setup-phase">
      <router-link :to="`/challenges/${challengeType}`" class="back-link">&larr; Back</router-link>
      <h1>{{ challengeTitle }}</h1>
      <p class="hint">{{ challengeHint }}</p>

      <div class="camera-preview-wrap" @click="cameraReady && !starting && startSession()">
        <video ref="previewVideo" autoplay playsinline muted class="camera-preview"></video>
        <div v-if="!cameraReady" class="camera-placeholder">
          <p>{{ cameraError || 'Initialising camera...' }}</p>
        </div>
        <div v-if="cameraReady && !starting" class="camera-tap-hint">
          <span>Tap here to start</span>
        </div>
      </div>

      <div class="controls">
        <select v-model="selectedCamera" @change="switchCamera" class="camera-select">
          <option value="">Select camera...</option>
          <option v-for="cam in cameras" :key="cam.deviceId" :value="cam.deviceId">
            {{ cam.label || 'Camera' }}
          </option>
        </select>

        <button @click="startSession" :disabled="!cameraReady || starting" class="start-btn">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="20" height="20" stroke-linecap="round" stroke-linejoin="round"><polygon points="6 3 20 12 6 21 6 3"/></svg>
          {{ starting ? 'Starting...' : 'Start Challenge' }}
        </button>
      </div>
    </div>

    <!-- Active phase -->
    <div v-else-if="phase === 'active'" class="active-phase">
      <div class="video-container">
        <video ref="streamVideo" autoplay playsinline muted class="stream-video"></video>
        <canvas ref="overlayCanvas" class="overlay-canvas"></canvas>

        <!-- "Get in position" overlay (before ready) -->
        <div v-if="!playerReady" class="position-overlay">
          <div class="position-prompt">
            <div class="position-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="48" height="48">
                <circle cx="12" cy="5" r="2.5"/>
                <path d="M4 17 L8 12 L12 14 L16 12 L20 17" stroke-linecap="round" stroke-linejoin="round"/>
                <line x1="8" y1="12" x2="6" y2="16" stroke-linecap="round"/>
                <line x1="16" y1="12" x2="18" y2="16" stroke-linecap="round"/>
              </svg>
            </div>
            <p class="position-text" v-if="!playerDetected">Step into frame — full body visible</p>
            <p class="position-text" v-else>{{ formFeedback || 'Get into position...' }}</p>
            <div v-if="playerDetected" class="position-detected">Body detected</div>
          </div>
        </div>

        <!-- Overlay HUD (only when ready) -->
        <div class="hud" v-if="playerReady">
          <div class="hud-metric primary">
            <span class="metric-value">{{ displayScore }}</span>
            <span class="metric-label">{{ scoreLabel }}</span>
          </div>
          <div :class="['hud-metric', { 'time-warn': timeWarning }]">
            <span class="metric-value">{{ timeRemainingDisplay }}</span>
            <span class="metric-label">Remaining</span>
          </div>
        </div>

        <!-- Leg status indicator (pushup only, when ready) -->
        <div
          v-if="playerReady && challengeType === 'pushup'"
          class="leg-status"
          :class="legsStraight ? 'legs-ok' : 'legs-warn'"
        >
          {{ legsStraight ? 'Legs straight' : 'Straighten legs' }}
        </div>

        <div class="form-feedback" v-if="playerReady && formFeedback" :class="feedbackClass">
          {{ formFeedback }}
        </div>

        <!-- Big rep counter popup -->
        <transition name="rep-pop">
          <div v-if="showRepPop" class="rep-pop-overlay" :key="repPopKey">
            <span class="rep-pop-number">{{ repPopValue }}</span>
          </div>
        </transition>

        <!-- Recording indicator -->
        <div v-if="isRecording" class="recording-status">
          <span class="recording-dot"></span>
          <span class="recording-time">{{ formatRecordingTime(recordingDuration) }}</span>
        </div>
      </div>

      <div class="session-actions">
        <button
          @click="toggleRecording"
          :class="['btn-record', { recording: isRecording }]"
        >
          <svg class="btn-icon" viewBox="0 0 24 24" fill="currentColor">
            <circle v-if="!isRecording" cx="12" cy="12" r="8"/>
            <rect v-else x="8" y="8" width="8" height="8" rx="1"/>
          </svg>
          {{ isRecording ? 'Stop Recording' : 'Record' }}
        </button>
        <button @click="endSession" class="stop-btn">End Challenge</button>
      </div>
    </div>

    <!-- Connecting overlay -->
    <div v-if="phase === 'connecting'" class="connecting-overlay">
      <p>Connecting...</p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useChallengesStore } from '../stores/challenges'
import api from '../api/client'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const challengesStore = useChallengesStore()

const challengeType = computed(() => route.params.type)

const CHALLENGE_META = {
  plank: { title: 'Plank Hold', hint: 'Get into a plank position in view of the camera, then start.', scoreLabel: 'Hold (s)', unit: 's' },
  squat: { title: 'Max Squats', hint: 'Stand facing the camera with full body visible.', scoreLabel: 'Reps', unit: 'reps' },
  pushup: { title: 'Max Pushups', hint: 'Position the camera to the side so your full body is visible.', scoreLabel: 'Reps', unit: 'reps' },
}

const meta = computed(() => CHALLENGE_META[challengeType.value] || CHALLENGE_META.squat)
const challengeTitle = computed(() => meta.value.title)
const challengeHint = computed(() => meta.value.hint)
const scoreLabel = computed(() => meta.value.scoreLabel)

// Placement guide — show until user has completed at least 1 challenge
const showPlacementGuide = ref(false)

async function checkPlacementGuide() {
  try {
    await challengesStore.fetchSessions()
    if (challengesStore.sessions.length === 0) {
      showPlacementGuide.value = true
    }
  } catch {
    // If fetch fails, don't block the user
  }
}

function dismissPlacementGuide() {
  showPlacementGuide.value = false
}

// Camera state
const cameras = ref([])
const selectedCamera = ref('')
const cameraReady = ref(false)
const cameraError = ref('')
const previewVideo = ref(null)
const streamVideo = ref(null)
const overlayCanvas = ref(null)
let mediaStream = null

// Session state
const phase = ref('setup') // setup | connecting | active
const starting = ref(false)
const sessionId = ref(null)
let ws = null
let frameInterval = null
let startTime = null
let elapsedTimer = null

// Real-time data from backend
const reps = ref(0)
const holdSeconds = ref(0)
const formFeedback = ref('')
const elapsed = ref(0)
const playerDetected = ref(false)
const playerReady = ref(false)
const legsStraight = ref(true)
const timeRemaining = ref(0)

// Recording state
const isRecording = ref(false)
const hasRecording = ref(false)
const recordingDuration = ref(0)
let recordingTimer = null

// Rep pop animation
const showRepPop = ref(false)
const repPopValue = ref(0)
const repPopKey = ref(0)
let repPopTimeout = null

const displayScore = computed(() => {
  if (challengeType.value === 'plank') return holdSeconds.value
  return reps.value
})

const elapsedDisplay = computed(() => {
  const m = Math.floor(elapsed.value / 60)
  const s = elapsed.value % 60
  return `${m}:${String(s).padStart(2, '0')}`
})

const timeRemainingDisplay = computed(() => {
  const t = Math.ceil(timeRemaining.value)
  if (t <= 0) return '0:00'
  const m = Math.floor(t / 60)
  const s = t % 60
  return `${m}:${String(s).padStart(2, '0')}`
})

const timeWarning = computed(() => timeRemaining.value > 0 && timeRemaining.value <= 30)

const feedbackClass = computed(() => {
  const fb = formFeedback.value.toLowerCase()
  if (fb.includes('good') || fb.includes('rep') || fb.includes('ready')) return 'positive'
  return 'corrective'
})

function triggerRepPop(count) {
  repPopValue.value = count
  repPopKey.value++
  showRepPop.value = true
  if (repPopTimeout) clearTimeout(repPopTimeout)
  repPopTimeout = setTimeout(() => {
    showRepPop.value = false
  }, 800)
}

// ---------- Camera ----------

async function enumerateCameras() {
  try {
    // Need to request permission first
    const tempStream = await navigator.mediaDevices.getUserMedia({ video: true })
    tempStream.getTracks().forEach(t => t.stop())
    const devices = await navigator.mediaDevices.enumerateDevices()
    cameras.value = devices.filter(d => d.kind === 'videoinput')
    if (cameras.value.length > 0 && !selectedCamera.value) {
      selectedCamera.value = cameras.value[0].deviceId
      await switchCamera()
    }
  } catch (err) {
    cameraError.value = 'Camera access denied'
  }
}

async function switchCamera() {
  if (mediaStream) {
    mediaStream.getTracks().forEach(t => t.stop())
  }
  if (!selectedCamera.value) return

  try {
    mediaStream = await navigator.mediaDevices.getUserMedia({
      video: { deviceId: { exact: selectedCamera.value }, width: { ideal: 640 }, height: { ideal: 480 } }
    })
    const videoEl = phase.value === 'setup' ? previewVideo.value : streamVideo.value
    if (videoEl) {
      videoEl.srcObject = mediaStream
    }
    cameraReady.value = true
    cameraError.value = ''
  } catch (err) {
    cameraError.value = 'Failed to start camera'
    cameraReady.value = false
  }
}

// ---------- Session lifecycle ----------

async function startSession() {
  starting.value = true
  try {
    const data = await challengesStore.createSession(challengeType.value)
    sessionId.value = data.session_id
    phase.value = 'connecting'
    await connectWebSocket(data.session_id)
  } catch (err) {
    starting.value = false
  }
}

async function connectWebSocket(sid) {
  await authStore.ensureValidToken()
  const token = authStore.accessToken
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = window.location.host
  const wsUrl = `${protocol}//${host}/ws/challenge/${sid}?token=${token}`

  ws = new WebSocket(wsUrl)

  ws.onopen = async () => {
    phase.value = 'active'
    starting.value = false

    startTime = Date.now()
    elapsed.value = 0
    elapsedTimer = setInterval(() => {
      elapsed.value = Math.floor((Date.now() - startTime) / 1000)
    }, 1000)

    // Wait for Vue to render the streamVideo element
    await nextTick()

    if (streamVideo.value && mediaStream) {
      streamVideo.value.srcObject = mediaStream
      // Wait for the video to be ready before capturing frames
      if (streamVideo.value.readyState >= 2) {
        startFrameCapture()
      } else {
        streamVideo.value.addEventListener('loadedmetadata', () => {
          startFrameCapture()
        }, { once: true })
      }
    }
  }

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      if (data.type === 'challenge_update') {
        const newReps = data.reps || 0
        if (newReps > reps.value && challengeType.value !== 'plank') {
          triggerRepPop(newReps)
        }
        reps.value = newReps
        holdSeconds.value = data.hold_seconds || 0
        formFeedback.value = data.form_feedback || ''
        playerDetected.value = !!data.player_detected
        playerReady.value = !!data.ready
        timeRemaining.value = data.time_remaining ?? 0
        if (data.exercise) {
          legsStraight.value = data.exercise.legs_straight !== false
        }
        if (data.pose) drawPose(data.pose)

        // Auto-end: backend says session is over
        if (data.auto_end) {
          endSession()
          return
        }
      } else if (data.type === 'session_ended') {
        handleSessionEnded(data.report)
      }
    } catch (e) { /* ignore parse errors */ }
  }

  ws.onerror = () => {
    phase.value = 'setup'
    starting.value = false
  }

  ws.onclose = () => {
    stopFrameCapture()
  }

  // Keep-alive
  const pingId = setInterval(() => {
    if (ws && ws.readyState === WebSocket.OPEN) ws.send('ping')
  }, 30000)
  ws._pingId = pingId
}

function startFrameCapture() {
  const canvas = document.createElement('canvas')
  const FPS = 10

  frameInterval = setInterval(() => {
    if (!streamVideo.value || !ws || ws.readyState !== WebSocket.OPEN) return

    const video = streamVideo.value
    canvas.width = video.videoWidth || 640
    canvas.height = video.videoHeight || 480
    const ctx = canvas.getContext('2d')
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height)

    canvas.toBlob((blob) => {
      if (!blob || !ws || ws.readyState !== WebSocket.OPEN) return
      const reader = new FileReader()
      reader.onloadend = () => {
        const base64 = reader.result.split(',')[1]
        ws.send(JSON.stringify({
          type: 'frame',
          data: base64,
          timestamp: (Date.now() - startTime) / 1000,
        }))
      }
      reader.readAsDataURL(blob)
    }, 'image/jpeg', 0.7)
  }, 1000 / FPS)
}

function stopFrameCapture() {
  if (frameInterval) {
    clearInterval(frameInterval)
    frameInterval = null
  }
  if (elapsedTimer) {
    clearInterval(elapsedTimer)
    elapsedTimer = null
  }
}

async function endSession() {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'end_session' }))
  }
  // The ws.onmessage handler will navigate to results when session_ended arrives.
  // Fallback: if WS is already closed, end via REST and navigate directly.
  if (!ws || ws.readyState !== WebSocket.OPEN) {
    try {
      const result = await challengesStore.endSession(sessionId.value)
      navigateToResults(sessionId.value, result)
    } catch (e) {
      router.push(`/challenges/${challengeType.value}`)
    }
  }
}

function handleSessionEnded(report) {
  cleanup()
  // End session via REST to persist results
  challengesStore.endSession(sessionId.value).then((result) => {
    navigateToResults(sessionId.value, result)
  }).catch(() => {
    // Still navigate with the WS report as fallback
    navigateToResults(sessionId.value, report)
  })
}

function navigateToResults(sid, data) {
  // Store result data in sessionStorage for the results page
  if (data) {
    // Include recording flag so results page knows to show download button
    const payload = { ...data, has_recording: hasRecording.value || isRecording.value || !!data.has_recording }
    sessionStorage.setItem(`challenge_result_${sid}`, JSON.stringify(payload))
  }
  router.push(`/challenges/results/${sid}`)
}

// ---------- Recording ----------

async function toggleRecording() {
  try {
    if (isRecording.value) {
      await api.post(`/api/v1/challenges/sessions/${sessionId.value}/recording/stop`)
      isRecording.value = false
      hasRecording.value = true
      stopRecordingTimer()
    } else {
      await api.post(`/api/v1/challenges/sessions/${sessionId.value}/recording/start`)
      isRecording.value = true
      recordingDuration.value = 0
      startRecordingTimer()
    }
  } catch (e) {
    console.error('Recording error:', e)
  }
}

function startRecordingTimer() {
  recordingTimer = setInterval(() => {
    recordingDuration.value++
  }, 1000)
}

function stopRecordingTimer() {
  if (recordingTimer) {
    clearInterval(recordingTimer)
    recordingTimer = null
  }
}

function formatRecordingTime(seconds) {
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
}

// ---------- Pose drawing ----------

// Body-part color map for skeleton drawing
const ARM_IDS = new Set([13, 14, 15, 16])
const LEG_IDS = new Set([25, 26, 27, 28])
const TORSO_IDS = new Set([11, 12, 23, 24])
const COLORS = { arms: '#42a5f5', torso: '#f9ca24', legs: '#ab47bc' }

function connectionColor(a, b) {
  // Arms: any connection involving elbow (13/14) or wrist (15/16)
  if (ARM_IDS.has(a) || ARM_IDS.has(b)) return COLORS.arms
  // Legs: any connection involving knee (25/26) or ankle (27/28)
  if (LEG_IDS.has(a) || LEG_IDS.has(b)) return COLORS.legs
  // Torso: shoulders / hips
  return COLORS.torso
}

function jointColor(idx) {
  if (ARM_IDS.has(idx)) return COLORS.arms
  if (LEG_IDS.has(idx)) return COLORS.legs
  if (TORSO_IDS.has(idx)) return COLORS.torso
  return '#aaa'
}

function drawPose(poseData) {
  const canvas = overlayCanvas.value
  if (!canvas || !poseData) return

  const video = streamVideo.value
  if (!video) return

  canvas.width = video.videoWidth || 640
  canvas.height = video.videoHeight || 480
  const ctx = canvas.getContext('2d')
  ctx.clearRect(0, 0, canvas.width, canvas.height)

  const landmarks = poseData.landmarks
  if (!landmarks) return

  // Scale from pose detection resolution to canvas
  const sx = canvas.width / poseData.width
  const sy = canvas.height / poseData.height

  // Draw connections with body-part colors
  ctx.lineWidth = 3
  for (const [a, b] of poseData.connections) {
    const la = landmarks[a]
    const lb = landmarks[b]
    if (!la || !lb || la.visibility < 0.3 || lb.visibility < 0.3) continue
    ctx.strokeStyle = connectionColor(a, b)
    ctx.beginPath()
    ctx.moveTo(la.x * sx, la.y * sy)
    ctx.lineTo(lb.x * sx, lb.y * sy)
    ctx.stroke()
  }

  // Draw joints with body-part colors
  for (let i = 0; i < landmarks.length; i++) {
    const lm = landmarks[i]
    if (lm.visibility < 0.3) continue
    ctx.fillStyle = jointColor(i)
    ctx.beginPath()
    ctx.arc(lm.x * sx, lm.y * sy, 5, 0, 2 * Math.PI)
    ctx.fill()
  }
}

// ---------- Cleanup ----------

function cleanup() {
  stopFrameCapture()
  stopRecordingTimer()
  if (repPopTimeout) { clearTimeout(repPopTimeout); repPopTimeout = null }
  if (ws) {
    if (ws._pingId) clearInterval(ws._pingId)
    ws.close()
    ws = null
  }
  if (mediaStream) {
    mediaStream.getTracks().forEach(t => t.stop())
    mediaStream = null
  }
}

onMounted(() => {
  checkPlacementGuide()
  enumerateCameras()
})

onUnmounted(() => {
  cleanup()
})
</script>

<style scoped>
.challenge-session {
  max-width: 800px;
  margin: 0 auto;
  padding: 1rem;
}

.back-link {
  color: var(--text-muted);
  text-decoration: none;
  font-size: 0.9rem;
}
.back-link:hover { color: var(--color-primary); }

.setup-phase h1 {
  color: var(--color-primary);
  margin: 0.5rem 0 0.25rem;
  font-size: 1.8rem;
}

.hint {
  color: var(--text-muted);
  margin-bottom: 1.5rem;
}

.camera-preview-wrap {
  position: relative;
  background: #000;
  border-radius: var(--radius-md);
  overflow: hidden;
  aspect-ratio: 4/3;
  margin-bottom: 1rem;
}

.camera-preview, .stream-video {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.camera-placeholder {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
  background: rgba(0,0,0,0.7);
}

.controls {
  display: flex;
  gap: 1rem;
  align-items: center;
}

.camera-select {
  flex: 1;
  padding: 0.6rem;
  background: var(--bg-input);
  border: 1px solid var(--border-input);
  color: var(--text-primary);
  border-radius: var(--radius-sm);
}

.start-btn {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  background: var(--gradient-primary);
  color: var(--text-on-primary);
  border: none;
  padding: 0.9rem 2rem;
  border-radius: var(--radius-md);
  font-weight: 600;
  font-size: 1.05rem;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
  box-shadow: 0 4px 14px rgba(124, 58, 237, 0.3);
}
.start-btn:disabled { opacity: 0.4; cursor: not-allowed; box-shadow: none; }
.start-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 6px 20px rgba(124, 58, 237, 0.4);
}

.camera-preview-wrap {
  cursor: pointer;
}

.camera-tap-hint {
  position: absolute;
  bottom: 1rem;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(0, 0, 0, 0.5);
  color: rgba(255, 255, 255, 0.8);
  padding: 0.4rem 1rem;
  border-radius: var(--radius-full);
  font-size: 0.8rem;
  pointer-events: none;
  animation: tap-pulse 2.5s ease-in-out infinite;
}

@keyframes tap-pulse {
  0%, 100% { opacity: 0.6; }
  50% { opacity: 1; }
}

/* Active phase */
.video-container {
  position: relative;
  background: #000;
  border-radius: var(--radius-md);
  overflow: hidden;
  aspect-ratio: 4/3;
}

.overlay-canvas {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

.hud {
  position: absolute;
  top: 1rem;
  left: 1rem;
  display: flex;
  gap: 1.5rem;
}

.hud-metric {
  background: rgba(0, 0, 0, 0.7);
  padding: 0.5rem 1rem;
  border-radius: var(--radius-md);
  text-align: center;
}

.hud-metric.primary {
  border: 1px solid var(--color-primary);
}

.hud-metric.time-warn {
  border: 1px solid var(--color-destructive);
}

.hud-metric.time-warn .metric-value {
  color: var(--color-destructive);
  animation: pulse-warn 1s ease-in-out infinite;
}

.metric-value {
  display: block;
  color: var(--color-primary);
  font-size: 1.8rem;
  font-weight: 700;
  line-height: 1;
}

.metric-label {
  display: block;
  color: #ccc;
  font-size: 0.75rem;
  font-weight: 500;
  margin-top: 0.25rem;
}

.form-feedback {
  position: absolute;
  bottom: 1rem;
  left: 50%;
  transform: translateX(-50%);
  padding: 0.5rem 1.25rem;
  border-radius: var(--radius-full);
  font-size: 0.9rem;
  font-weight: 500;
  white-space: nowrap;
}

.form-feedback.positive {
  background: rgba(78, 204, 163, 0.2);
  color: #4ecca3;
  border: 1px solid rgba(78, 204, 163, 0.4);
}

.form-feedback.corrective {
  background: rgba(231, 76, 60, 0.2);
  color: #e74c3c;
  border: 1px solid rgba(231, 76, 60, 0.4);
}

/* Session actions row */
.session-actions {
  display: flex;
  gap: 1rem;
  margin-top: 1rem;
}

.btn-record {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 0.75rem;
  background: var(--bg-card);
  border: 2px solid var(--color-destructive);
  border-radius: var(--radius-md);
  color: var(--color-destructive);
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}
.btn-record:hover { background: var(--color-destructive-light); }
.btn-record.recording {
  background: var(--color-destructive);
  color: white;
  animation: pulse-record 1s infinite;
}
.btn-record .btn-icon {
  width: 18px;
  height: 18px;
}

@keyframes pulse-record {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.8; }
}

.stop-btn {
  flex: 1;
  background: transparent;
  border: 1px solid var(--color-destructive);
  color: var(--color-destructive);
  padding: 0.75rem;
  border-radius: var(--radius-md);
  cursor: pointer;
  font-size: 1rem;
  transition: all 0.2s;
}
.stop-btn:hover {
  background: var(--color-destructive);
  color: #fff;
}

/* Recording indicator */
.recording-status {
  position: absolute;
  top: 3.5rem;
  right: 1rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.4rem 0.8rem;
  background: rgba(231, 76, 60, 0.2);
  border-radius: var(--radius-sm);
}
.recording-dot {
  width: 10px;
  height: 10px;
  background: var(--color-destructive);
  border-radius: var(--radius-full);
  animation: recording-pulse 1s infinite;
}
@keyframes recording-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}
.recording-time {
  color: var(--color-destructive);
  font-family: monospace;
  font-weight: bold;
  font-size: 0.85rem;
}

/* Position overlay (before ready) — dark overlay for camera feed visibility */
.position-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.5);
  z-index: 5;
}

.position-prompt {
  text-align: center;
  padding: 2rem;
}

.position-icon {
  color: var(--color-primary);
  margin-bottom: 1rem;
  animation: pulse-glow 2s ease-in-out infinite;
}

@keyframes pulse-glow {
  0%, 100% { opacity: 0.6; }
  50% { opacity: 1; }
}

.position-text {
  color: #fff;
  font-size: 1.3rem;
  font-weight: 600;
  margin: 0 0 0.5rem;
}

.position-detected {
  color: var(--color-primary);
  font-size: 0.85rem;
  font-weight: 500;
}

/* Leg status indicator — overlaid on camera feed */
.leg-status {
  position: absolute;
  top: 1rem;
  right: 1rem;
  padding: 0.35rem 0.75rem;
  border-radius: var(--radius-sm);
  font-size: 0.75rem;
  font-weight: 600;
  z-index: 4;
}

.leg-status.legs-ok {
  background: rgba(78, 204, 163, 0.2);
  color: #4ecca3;
  border: 1px solid rgba(78, 204, 163, 0.3);
}

.leg-status.legs-warn {
  background: rgba(231, 76, 60, 0.2);
  color: #e74c3c;
  border: 1px solid rgba(231, 76, 60, 0.3);
  animation: pulse-warn 1s ease-in-out infinite;
}

@keyframes pulse-warn {
  0%, 100% { opacity: 0.7; }
  50% { opacity: 1; }
}

/* Rep pop animation */
.rep-pop-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  pointer-events: none;
  z-index: 10;
}

.rep-pop-number {
  font-size: 8rem;
  font-weight: 900;
  color: #4ecca3;
  text-shadow: 0 0 40px rgba(78, 204, 163, 0.6), 0 4px 20px rgba(0, 0, 0, 0.8);
  line-height: 1;
}

.rep-pop-enter-active {
  transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.rep-pop-leave-active {
  transition: all 0.5s ease-out;
}
.rep-pop-enter-from {
  opacity: 0;
  transform: scale(0.3);
}
.rep-pop-enter-to {
  opacity: 1;
  transform: scale(1);
}
.rep-pop-leave-from {
  opacity: 1;
  transform: scale(1);
}
.rep-pop-leave-to {
  opacity: 0;
  transform: scale(1.5);
}

/* Placement guide overlay */
.placement-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 200;
  padding: 1rem;
}

.placement-card {
  background: var(--bg-card);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-xl);
  padding: 2rem;
  max-width: 420px;
  width: 100%;
  text-align: center;
}

.placement-title {
  font-size: 1.3rem;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 0.25rem;
}

.placement-subtitle {
  color: var(--text-secondary);
  font-size: 0.9rem;
  margin-bottom: 1.25rem;
}

.placement-img-wrap {
  position: relative;
  margin-bottom: 1.25rem;
}

.placement-img {
  width: 100%;
  border-radius: var(--radius-md);
  display: block;
}

.placement-highlight {
  position: absolute;
  bottom: 28%;
  left: 0%;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.highlight-ring {
  width: 52px;
  height: 52px;
  border-radius: var(--radius-full);
  border: 3px solid var(--color-primary);
  box-shadow: 0 0 0 6px rgba(79, 70, 229, 0.25);
  animation: ring-breathe 2s ease-in-out infinite;
}

@keyframes ring-breathe {
  0%, 100% { box-shadow: 0 0 0 4px rgba(79, 70, 229, 0.2); }
  50% { box-shadow: 0 0 0 10px rgba(79, 70, 229, 0.35); }
}

.highlight-label {
  background: var(--color-primary);
  color: #fff;
  font-size: 0.75rem;
  font-weight: 600;
  padding: 0.25rem 0.6rem;
  border-radius: var(--radius-full);
  white-space: nowrap;
}

.placement-tips {
  text-align: left;
  list-style: none;
  padding: 0;
  margin: 0 0 1.5rem;
}

.placement-tips li {
  color: var(--text-secondary);
  font-size: 0.85rem;
  padding: 0.3rem 0;
  padding-left: 1.25rem;
  position: relative;
}

.placement-tips li::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0.6rem;
  width: 6px;
  height: 6px;
  border-radius: var(--radius-full);
  background: var(--color-primary);
}

.placement-btn {
  width: 100%;
  padding: 0.85rem;
  background: var(--gradient-primary);
  color: var(--text-on-primary);
  border: none;
  border-radius: var(--radius-md);
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.2s;
}
.placement-btn:hover { opacity: 0.9; }

.connecting-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.85);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-primary);
  font-size: 1.2rem;
  z-index: 100;
}

@media (max-width: 640px) {
  .controls {
    flex-direction: column;
  }

  .camera-select,
  .start-btn {
    width: 100%;
  }

  .hud {
    gap: 0.75rem;
  }

  .metric-value {
    font-size: 1.3rem;
  }

  .form-feedback {
    font-size: 0.8rem;
    padding: 0.4rem 1rem;
  }

  .session-actions {
    flex-direction: column;
  }

  .position-text {
    font-size: 1rem;
    padding: 0 1rem;
  }
}
</style>
