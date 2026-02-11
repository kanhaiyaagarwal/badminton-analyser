<template>
  <div class="challenge-session">
    <!-- Setup phase -->
    <div v-if="phase === 'setup'" class="setup-phase">
      <router-link to="/challenges" class="back-link">&larr; Back to Challenges</router-link>
      <h1>{{ challengeTitle }}</h1>
      <p class="hint">{{ challengeHint }}</p>

      <div class="camera-preview-wrap">
        <video ref="previewVideo" autoplay playsinline muted class="camera-preview"></video>
        <div v-if="!cameraReady" class="camera-placeholder">
          <p>{{ cameraError || 'Initialising camera...' }}</p>
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
          {{ starting ? 'Starting...' : 'Start Challenge' }}
        </button>
      </div>
    </div>

    <!-- Active phase -->
    <div v-else-if="phase === 'active'" class="active-phase">
      <div class="video-container">
        <video ref="streamVideo" autoplay playsinline muted class="stream-video"></video>
        <canvas ref="overlayCanvas" class="overlay-canvas"></canvas>

        <!-- Overlay HUD -->
        <div class="hud">
          <div class="hud-metric primary">
            <span class="metric-value">{{ displayScore }}</span>
            <span class="metric-label">{{ scoreLabel }}</span>
          </div>
          <div class="hud-metric">
            <span class="metric-value">{{ elapsedDisplay }}</span>
            <span class="metric-label">Elapsed</span>
          </div>
        </div>

        <div class="form-feedback" v-if="formFeedback" :class="feedbackClass">
          {{ formFeedback }}
        </div>

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

// Recording state
const isRecording = ref(false)
const hasRecording = ref(false)
const recordingDuration = ref(0)
let recordingTimer = null

const displayScore = computed(() => {
  if (challengeType.value === 'plank') return holdSeconds.value
  return reps.value
})

const elapsedDisplay = computed(() => {
  const m = Math.floor(elapsed.value / 60)
  const s = elapsed.value % 60
  return `${m}:${String(s).padStart(2, '0')}`
})

const feedbackClass = computed(() => {
  const fb = formFeedback.value.toLowerCase()
  if (fb.includes('good') || fb.includes('rep')) return 'positive'
  return 'corrective'
})

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
        reps.value = data.reps || 0
        holdSeconds.value = data.hold_seconds || 0
        formFeedback.value = data.form_feedback || ''
        if (data.pose) drawPose(data.pose)
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
      router.push('/challenges')
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

  // Draw connections
  ctx.strokeStyle = '#4ecca3'
  ctx.lineWidth = 2
  for (const [a, b] of poseData.connections) {
    const la = landmarks[a]
    const lb = landmarks[b]
    if (!la || !lb || la.visibility < 0.3 || lb.visibility < 0.3) continue
    ctx.beginPath()
    ctx.moveTo(la.x * sx, la.y * sy)
    ctx.lineTo(lb.x * sx, lb.y * sy)
    ctx.stroke()
  }

  // Draw joints
  ctx.fillStyle = '#4ecca3'
  for (const lm of landmarks) {
    if (lm.visibility < 0.3) continue
    ctx.beginPath()
    ctx.arc(lm.x * sx, lm.y * sy, 4, 0, 2 * Math.PI)
    ctx.fill()
  }
}

// ---------- Cleanup ----------

function cleanup() {
  stopFrameCapture()
  stopRecordingTimer()
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
  color: #888;
  text-decoration: none;
  font-size: 0.9rem;
}
.back-link:hover { color: #4ecca3; }

.setup-phase h1 {
  color: #eee;
  margin: 0.5rem 0 0.25rem;
}

.hint {
  color: #888;
  margin-bottom: 1.5rem;
}

.camera-preview-wrap {
  position: relative;
  background: #000;
  border-radius: 8px;
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
  color: #888;
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
  background: rgba(22, 33, 62, 0.8);
  border: 1px solid rgba(255,255,255,0.1);
  color: #eee;
  border-radius: 6px;
}

.start-btn {
  background: #4ecca3;
  color: #0a0a1a;
  border: none;
  padding: 0.7rem 1.5rem;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.2s;
}
.start-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.start-btn:hover:not(:disabled) { opacity: 0.9; }

/* Active phase */
.video-container {
  position: relative;
  background: #000;
  border-radius: 8px;
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
  border-radius: 8px;
  text-align: center;
}

.hud-metric.primary {
  border: 1px solid #4ecca3;
}

.metric-value {
  display: block;
  color: #4ecca3;
  font-size: 1.8rem;
  font-weight: 700;
  line-height: 1;
}

.metric-label {
  display: block;
  color: #888;
  font-size: 0.75rem;
  margin-top: 0.25rem;
}

.form-feedback {
  position: absolute;
  bottom: 1rem;
  left: 50%;
  transform: translateX(-50%);
  padding: 0.5rem 1.25rem;
  border-radius: 20px;
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
  background: #16213e;
  border: 2px solid #e74c3c;
  border-radius: 8px;
  color: #e74c3c;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}
.btn-record:hover { background: rgba(231, 76, 60, 0.1); }
.btn-record.recording {
  background: #e74c3c;
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
  border: 1px solid #e74c3c;
  color: #e74c3c;
  padding: 0.75rem;
  border-radius: 8px;
  cursor: pointer;
  font-size: 1rem;
  transition: all 0.2s;
}
.stop-btn:hover {
  background: #e74c3c;
  color: #fff;
}

/* Recording indicator */
.recording-status {
  position: absolute;
  top: 1rem;
  right: 1rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.4rem 0.8rem;
  background: rgba(231, 76, 60, 0.2);
  border-radius: 6px;
}
.recording-dot {
  width: 10px;
  height: 10px;
  background: #e74c3c;
  border-radius: 50%;
  animation: recording-pulse 1s infinite;
}
@keyframes recording-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}
.recording-time {
  color: #e74c3c;
  font-family: monospace;
  font-weight: bold;
  font-size: 0.85rem;
}

.connecting-overlay {
  position: fixed;
  inset: 0;
  background: rgba(10, 10, 26, 0.85);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #4ecca3;
  font-size: 1.2rem;
  z-index: 100;
}
</style>
