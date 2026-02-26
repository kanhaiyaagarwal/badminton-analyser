<template>
  <div class="mimic-session">

    <!-- Setup phase -->
    <div v-if="phase === 'setup'" class="setup-phase">
      <router-link to="/mimic" class="back-link">&larr; Back</router-link>
      <h1>{{ challengeTitle || 'Mimic Challenge' }}</h1>
      <p class="hint">Match the reference video as closely as you can</p>

      <div class="camera-preview-wrap">
        <video ref="previewVideo" autoplay playsinline muted class="camera-preview"></video>
        <div v-if="!cameraReady" class="camera-placeholder">
          <p>{{ cameraError || 'Initialising camera...' }}</p>
        </div>
      </div>

      <div class="setup-controls">
        <select v-model="selectedCamera" @change="switchCamera" class="camera-select">
          <option value="">Select camera...</option>
          <option v-for="cam in cameras" :key="cam.deviceId" :value="cam.deviceId">
            {{ cam.label || 'Camera' }}
          </option>
        </select>

        <div class="layout-toggle">
          <label>Layout:</label>
          <button :class="['toggle-btn', { active: layout === 'stacked' }]" @click="layout = 'stacked'">Stacked</button>
          <button :class="['toggle-btn', { active: layout === 'overlay' }]" @click="layout = 'overlay'">Overlay</button>
        </div>

        <button @click="startSession" :disabled="!cameraReady || starting" class="start-btn">
          {{ starting ? 'Starting...' : 'Start Mimic' }}
        </button>
      </div>
    </div>

    <!-- Active phase -->
    <div v-else-if="phase === 'active'" class="active-phase" :class="layout">

      <!-- Stacked layout: reference video on top, camera below -->
      <div v-if="layout === 'stacked'" class="stacked-layout">
        <div class="ref-video-wrap">
          <video ref="refVideo" :src="refVideoUrl" playsinline class="ref-video" @ended="onRefVideoEnded"></video>
          <div class="ref-label">Reference</div>
        </div>
        <div class="user-video-wrap">
          <video ref="streamVideo" autoplay playsinline muted class="stream-video"></video>
          <canvas ref="overlayCanvas" class="overlay-canvas"></canvas>
          <div class="user-label">You</div>
        </div>
      </div>

      <!-- Overlay layout: camera with ref skeleton drawn on it -->
      <div v-else class="overlay-layout">
        <div class="user-video-wrap">
          <video ref="streamVideo" autoplay playsinline muted class="stream-video"></video>
          <canvas ref="overlayCanvas" class="overlay-canvas"></canvas>
        </div>
      </div>

      <!-- Score HUD -->
      <div class="score-hud">
        <div class="score-main">
          <span class="score-value" :style="{ color: scoreColor }">{{ currentScore }}</span>
          <span class="score-label">Score</span>
        </div>
        <div class="score-details">
          <div class="score-detail">
            <span class="detail-value">{{ scores.upper_body || 0 }}</span>
            <span class="detail-label">Upper</span>
          </div>
          <div class="score-detail">
            <span class="detail-value">{{ scores.lower_body || 0 }}</span>
            <span class="detail-label">Lower</span>
          </div>
        </div>
        <div class="feedback-text" v-if="feedback">{{ feedback }}</div>
        <div class="elapsed-time">{{ formatElapsed(elapsed) }}</div>
      </div>

      <div class="active-controls">
        <button @click="endSession" class="end-btn">End Session</button>
      </div>
    </div>

    <!-- Connecting -->
    <div v-else-if="phase === 'connecting'" class="connecting">
      <p>Connecting...</p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useMimicStore } from '../stores/mimic'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const mimicStore = useMimicStore()

const challengeId = parseInt(route.params.challengeId)
const challengeTitle = ref('')
const refVideoUrl = ref('')

// Phase
const phase = ref('setup')
const starting = ref(false)
const layout = ref('stacked')

// Camera
const cameras = ref([])
const selectedCamera = ref('')
const cameraReady = ref(false)
const cameraError = ref('')
let mediaStream = null
const previewVideo = ref(null)
const streamVideo = ref(null)
const overlayCanvas = ref(null)
const refVideo = ref(null)

// Session state
let sessionId = null
let ws = null
let frameInterval = null
let startTime = null
const elapsed = ref(0)
let elapsedTimer = null

// Scores
const scores = ref({ cosine_raw: 0, cosine_normalized: 0, angle_score: 0, upper_body: 0, lower_body: 0 })
const feedback = ref('')
const playerDetected = ref(false)

const currentScore = computed(() => scores.value.angle_score || 0)
const scoreColor = computed(() => {
  const s = currentScore.value
  if (s >= 80) return '#2ecc71'
  if (s >= 50) return '#f1c40f'
  return '#e74c3c'
})

onMounted(async () => {
  // Fetch challenge info
  try {
    const ch = await mimicStore.fetchChallenge(challengeId)
    challengeTitle.value = ch.title
    // Build authenticated video URL
    const token = authStore.accessToken
    refVideoUrl.value = `/api/v1/mimic/challenges/${challengeId}/video`
  } catch (err) {
    // will show fallback title
  }
  enumerateCameras()
})

onUnmounted(() => {
  cleanup()
})

// ---------- Camera ----------

async function enumerateCameras() {
  try {
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

// ---------- Session ----------

async function startSession() {
  starting.value = true
  try {
    const data = await mimicStore.createSession(challengeId)
    sessionId = data.session_id
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
  const wsUrl = `${protocol}//${host}/ws/mimic/${sid}?token=${token}`

  ws = new WebSocket(wsUrl)

  ws.onopen = async () => {
    phase.value = 'active'
    starting.value = false
    startTime = Date.now()
    elapsed.value = 0
    elapsedTimer = setInterval(() => {
      elapsed.value = (Date.now() - startTime) / 1000
    }, 1000)

    await nextTick()

    // Attach camera to stream video element
    if (streamVideo.value && mediaStream) {
      streamVideo.value.srcObject = mediaStream
      if (streamVideo.value.readyState >= 2) {
        startFrameCapture()
      } else {
        streamVideo.value.addEventListener('loadedmetadata', () => {
          startFrameCapture()
        }, { once: true })
      }
    }

    // Start reference video playback (stacked mode)
    if (refVideo.value && layout.value === 'stacked') {
      refVideo.value.play().catch(() => {})
    }
  }

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      if (data.type === 'mimic_update') {
        if (data.scores) {
          scores.value = data.scores
        }
        feedback.value = data.feedback || ''
        playerDetected.value = !!data.player_detected

        // Sync reference video time (stacked mode)
        if (data.ref_time != null && refVideo.value && layout.value === 'stacked') {
          const drift = Math.abs(refVideo.value.currentTime - data.ref_time)
          if (drift > 0.5) {
            refVideo.value.currentTime = data.ref_time
          }
        }

        // Draw skeleton overlays
        if (data.pose || data.ref_landmarks) {
          drawOverlays(data)
        }

      } else if (data.type === 'session_ended') {
        handleSessionEnded(data.report)
      }
    } catch (e) { /* ignore */ }
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

// ---------- Drawing ----------

function drawOverlays(data) {
  const canvas = overlayCanvas.value
  if (!canvas) return
  const video = streamVideo.value
  if (!video) return

  canvas.width = video.videoWidth || 640
  canvas.height = video.videoHeight || 480
  const ctx = canvas.getContext('2d')
  ctx.clearRect(0, 0, canvas.width, canvas.height)

  // Draw user pose in green
  if (data.pose && data.pose.landmarks) {
    drawSkeleton(ctx, data.pose.landmarks, data.pose.connections, canvas.width, canvas.height, '#2ecc71', false)
  }

  // Draw reference pose in blue/transparent (overlay mode)
  if (layout.value === 'overlay' && data.ref_landmarks) {
    const refLm = data.ref_landmarks.map(lm => ({
      x: lm[0] * canvas.width,
      y: lm[1] * canvas.height,
      visibility: lm[2],
      nx: lm[0],
      ny: lm[1],
    }))
    const connections = data.pose?.connections || [
      [11,12],[11,13],[13,15],[12,14],[14,16],
      [11,23],[12,24],[23,24],[23,25],[25,27],[24,26],[26,28]
    ]
    drawSkeleton(ctx, refLm, connections, canvas.width, canvas.height, 'rgba(52, 152, 219, 0.6)', true)
  }
}

function drawSkeleton(ctx, landmarks, connections, w, h, color, useNormalized) {
  if (!landmarks || !landmarks.length) return

  ctx.globalAlpha = 0.8

  // Draw connections
  ctx.strokeStyle = color
  ctx.lineWidth = 3
  for (const [a, b] of (connections || [])) {
    const la = landmarks[a]
    const lb = landmarks[b]
    if (!la || !lb) continue
    if ((la.visibility || 0) < 0.3 || (lb.visibility || 0) < 0.3) continue

    const ax = useNormalized ? la.nx * w : la.x
    const ay = useNormalized ? la.ny * h : la.y
    const bx = useNormalized ? lb.nx * w : lb.x
    const by = useNormalized ? lb.ny * h : lb.y

    ctx.beginPath()
    ctx.moveTo(ax, ay)
    ctx.lineTo(bx, by)
    ctx.stroke()
  }

  // Draw joints
  ctx.fillStyle = color
  for (const lm of landmarks) {
    if (!lm || (lm.visibility || 0) < 0.3) continue
    const x = useNormalized ? lm.nx * w : lm.x
    const y = useNormalized ? lm.ny * h : lm.y
    ctx.beginPath()
    ctx.arc(x, y, 4, 0, 2 * Math.PI)
    ctx.fill()
  }

  ctx.globalAlpha = 1.0
}

// ---------- End ----------

async function endSession() {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'end_session' }))
  }
  // Wait briefly for the session_ended message, then navigate
  setTimeout(async () => {
    try {
      await mimicStore.endSession(sessionId)
    } catch (err) { /* already ended via WS */ }
    cleanup()
    router.push(`/mimic/results/${sessionId}`)
  }, 500)
}

function handleSessionEnded(report) {
  cleanup()
  router.push(`/mimic/results/${sessionId}`)
}

function onRefVideoEnded() {
  // Loop the reference video
  if (refVideo.value) {
    refVideo.value.currentTime = 0
    refVideo.value.play().catch(() => {})
  }
}

function cleanup() {
  stopFrameCapture()
  if (ws) {
    if (ws._pingId) clearInterval(ws._pingId)
    if (ws.readyState === WebSocket.OPEN) ws.close()
    ws = null
  }
  if (mediaStream) {
    mediaStream.getTracks().forEach(t => t.stop())
    mediaStream = null
  }
}

function formatElapsed(secs) {
  const m = Math.floor(secs / 60)
  const s = Math.floor(secs % 60)
  return `${m}:${String(s).padStart(2, '0')}`
}
</script>

<style scoped>
.mimic-session {
  max-width: 900px;
  margin: 0 auto;
  padding: 1rem;
}

.back-link {
  color: var(--text-muted);
  text-decoration: none;
  font-size: 0.9rem;
}

.setup-phase h1 {
  color: var(--text-primary);
  font-size: 1.5rem;
  margin: 0.5rem 0 0.25rem;
}

.hint {
  color: var(--text-muted);
  font-size: 0.9rem;
  margin-bottom: 1rem;
}

.camera-preview-wrap {
  position: relative;
  border-radius: var(--radius-lg, 12px);
  overflow: hidden;
  background: #000;
  max-width: 480px;
  aspect-ratio: 4/3;
  margin-bottom: 1rem;
}

.camera-preview {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.camera-placeholder {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
}

.setup-controls {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.75rem;
}

.camera-select {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md, 8px);
  padding: 0.5rem 0.75rem;
  color: var(--text-primary);
  font-size: 0.85rem;
}

.layout-toggle {
  display: flex;
  align-items: center;
  gap: 0.4rem;
}

.layout-toggle label {
  color: var(--text-muted);
  font-size: 0.85rem;
}

.toggle-btn {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md, 8px);
  padding: 0.4rem 0.7rem;
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 0.8rem;
}

.toggle-btn.active {
  background: var(--color-primary);
  color: white;
  border-color: var(--color-primary);
}

.start-btn {
  background: var(--color-primary);
  color: white;
  border: none;
  padding: 0.6rem 1.5rem;
  border-radius: var(--radius-md, 8px);
  cursor: pointer;
  font-size: 0.95rem;
  font-weight: 500;
}

.start-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Active phase */
.active-phase {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.stacked-layout {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.ref-video-wrap, .user-video-wrap {
  position: relative;
  border-radius: var(--radius-lg, 12px);
  overflow: hidden;
  background: #000;
}

.stacked-layout .ref-video-wrap,
.stacked-layout .user-video-wrap {
  aspect-ratio: 16/9;
  max-height: 35vh;
}

.ref-video, .stream-video {
  width: 100%;
  height: 100%;
  object-fit: contain;
  display: block;
}

.overlay-canvas {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

.ref-label, .user-label {
  position: absolute;
  top: 8px;
  left: 8px;
  background: rgba(0, 0, 0, 0.6);
  color: white;
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
  font-size: 0.75rem;
}

.overlay-layout .user-video-wrap {
  max-height: 60vh;
}

/* Score HUD */
.score-hud {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg, 12px);
  padding: 0.75rem 1rem;
  display: flex;
  align-items: center;
  gap: 1rem;
  flex-wrap: wrap;
}

.score-main {
  display: flex;
  flex-direction: column;
  align-items: center;
  min-width: 60px;
}

.score-value {
  font-size: 2rem;
  font-weight: 700;
  line-height: 1;
}

.score-label {
  font-size: 0.75rem;
  color: var(--text-muted);
}

.score-details {
  display: flex;
  gap: 1rem;
}

.score-detail {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.detail-value {
  font-size: 1.2rem;
  font-weight: 600;
  color: var(--text-primary);
}

.detail-label {
  font-size: 0.7rem;
  color: var(--text-muted);
}

.feedback-text {
  flex: 1;
  font-size: 0.9rem;
  color: var(--text-secondary);
  text-align: center;
}

.elapsed-time {
  font-size: 0.9rem;
  color: var(--text-muted);
  font-family: monospace;
}

.active-controls {
  display: flex;
  justify-content: center;
}

.end-btn {
  background: #e74c3c;
  color: white;
  border: none;
  padding: 0.6rem 2rem;
  border-radius: var(--radius-md, 8px);
  cursor: pointer;
  font-size: 0.95rem;
  font-weight: 500;
}

.connecting {
  text-align: center;
  padding: 3rem;
  color: var(--text-muted);
}
</style>
