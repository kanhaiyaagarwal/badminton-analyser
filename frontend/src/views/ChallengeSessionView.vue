<template>
  <div class="challenge-session">
    <!-- Placement guide overlay -->
    <div v-if="showPlacementGuide" class="placement-overlay" @click="dismissPlacementGuide">
      <div class="placement-card" @click.stop>

        <div class="guide-steps">
          <div class="guide-step">
            <span class="step-number">1</span>
            <div class="step-content">
              <strong>First, START the challenge</strong>
              <p>Tap "Start Challenge" below, then place your phone.</p>
            </div>
          </div>
          <div class="guide-step">
            <span class="step-number">2</span>
            <div class="step-content">
              <strong>Place your phone at least a meter away</strong>
              <p>Place your phone on the white line, so that your entire body is visible on screen.</p>
            </div>
          </div>
        </div>

        <div class="placement-img-wrap">
          <img src="/position-guide.png" alt="Position guide" class="placement-img" />
        </div>

        <div class="guide-steps">
          <div class="guide-step">
            <span class="step-number">3</span>
            <div class="step-content">
              <strong>Wait for the <span class="inline-circle red"></span> cricle to turn <span class="inline-circle green"></span>, then begin Pushups</strong>
              <p>The circle turns green once you're in the correct position and your entire body is visible.</p>
            </div>
          </div>
          <div class="guide-step">
            <span class="step-number">4</span>
            <div class="step-content">
              <strong>Challenge auto-ends</strong>
              <p>When you stand up or drop out of position, the session ends on its own. Want more reps? Start a new challenge!</p>
            </div>
          </div>
        </div>

        <button class="placement-btn" @click="dismissPlacementGuide">Got it, let's go!</button>
      </div>
    </div>

    <!-- Setup phase -->
    <div v-if="phase === 'setup'" class="setup-phase">
      <router-link :to="`/challenges/${challengeType}`" class="back-link">&larr; Back</router-link>
      <h1>{{ challengeTitle }}</h1>
      <p class="hint">{{ challengeHint }} <span class="info-icon" @click="showPlacementGuide = true" title="How it works">&#9432;</span></p>

      <div :class="['camera-preview-wrap', { maximized }]" @click="cameraReady && !starting && startSession()">
        <video ref="previewVideo" autoplay playsinline muted class="camera-preview"></video>
        <div v-if="!cameraReady" class="camera-placeholder">
          <p>{{ cameraError || 'Initialising camera...' }}</p>
        </div>
        <div v-if="cameraReady && !starting && !maximized" class="camera-tap-hint">
          <span>Tap here to start</span>
        </div>
        <button class="maximize-btn" @click.stop="maximized = !maximized">
          <svg v-if="!maximized" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="20" height="20"><polyline points="15 3 21 3 21 9"/><polyline points="9 21 3 21 3 15"/><line x1="21" y1="3" x2="14" y2="10"/><line x1="3" y1="21" x2="10" y2="14"/></svg>
          <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="20" height="20"><polyline points="4 14 10 14 10 20"/><polyline points="20 10 14 10 14 4"/><line x1="14" y1="10" x2="21" y2="3"/><line x1="3" y1="21" x2="10" y2="14"/></svg>
        </button>
        <!-- Maximized overlay controls -->
        <div v-if="maximized && cameraReady && !starting" class="max-overlay-controls">
          <button class="max-start-btn" @click.stop="startSession">Tap to Start</button>
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

      <div class="setup-toggles">
        <label class="setup-toggle-item">
          <input type="checkbox" v-model="recordOnStart" />
          <svg class="toggle-icon" viewBox="0 0 24 24" fill="currentColor" width="16" height="16">
            <circle cx="12" cy="12" r="7"/>
          </svg>
          <span class="toggle-label">Record session</span>
        </label>
        <label class="setup-toggle-item">
          <input type="checkbox" v-model="showAnnotations" />
          <span class="toggle-label">Skeleton overlay</span>
        </label>
      </div>
    </div>

    <!-- Active phase -->
    <div v-else-if="phase === 'active'" class="active-phase">
      <div :class="['video-container', { maximized }]">
        <video ref="streamVideo" autoplay playsinline muted class="stream-video"></video>
        <canvas ref="overlayCanvas" class="overlay-canvas"></canvas>
        <button class="maximize-btn" @click="maximized = !maximized">
          <svg v-if="!maximized" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="20" height="20"><polyline points="15 3 21 3 21 9"/><polyline points="9 21 3 21 3 15"/><line x1="21" y1="3" x2="14" y2="10"/><line x1="3" y1="21" x2="10" y2="14"/></svg>
          <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="20" height="20"><polyline points="4 14 10 14 10 20"/><polyline points="20 10 14 10 14 4"/><line x1="14" y1="10" x2="21" y2="3"/><line x1="3" y1="21" x2="10" y2="14"/></svg>
        </button>

        <!-- "Get in position" overlay (before ready) -->
        <div v-if="!playerReady" class="position-overlay">
          <div class="position-prompt">
            <div class="status-circle red">
              <span class="status-circle-inner"></span>
            </div>
            <p class="position-text" v-if="!playerDetected">Step into frame</p>
            <p class="position-text" v-else>{{ formFeedback || 'Get into position' }}</p>
            <p class="position-subtext" v-if="!playerDetected">Full body must be visible</p>
            <div v-if="playerDetected" class="position-detected">Body detected</div>
            <button class="end-early-btn" @click="endSession">End Challenge</button>
          </div>
        </div>

        <!-- GO! flash overlay (when ready triggers) -->
        <transition name="go-flash">
          <div v-if="showGoFlash" class="position-overlay go-overlay">
            <div class="position-prompt">
              <div class="status-circle green">
                <span class="status-circle-inner"></span>
              </div>
              <p class="go-text">GO!</p>
            </div>
          </div>
        </transition>

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

        <!-- Maximized overlay actions -->
        <div v-if="maximized" class="max-overlay-actions">
          <button @click="toggleRecording" :class="['max-action-btn', { recording: isRecording }]">
            <svg viewBox="0 0 24 24" fill="currentColor" width="22" height="22">
              <circle v-if="!isRecording" cx="12" cy="12" r="8"/>
              <rect v-else x="8" y="8" width="8" height="8" rx="1"/>
            </svg>
            {{ isRecording ? 'Stop Rec' : 'Record' }}
          </button>
          <button @click="endSession" class="max-action-btn end">End</button>
        </div>
      </div>

      <div v-if="!maximized" class="session-actions">
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
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute, useRouter, onBeforeRouteLeave } from 'vue-router'
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

// Annotations toggle
const showAnnotations = ref(true)

// Fullscreen / maximize
const maximized = ref(false)

// Placement guide — show until user has completed at least 1 challenge
const showPlacementGuide = ref(false)

async function checkPlacementGuide() {
  try {
    await challengesStore.fetchSessions()
    // Sum scores for this challenge type across all completed sessions
    const totalScore = challengesStore.sessions
      .filter(s => s.challenge_type === challengeType.value && s.status === 'ended')
      .reduce((sum, s) => sum + (s.score || 0), 0)
    if (totalScore < 5) {
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
const recordOnStart = ref(false)
const isRecording = ref(false)
const hasRecording = ref(false)
const recordingDuration = ref(0)
let recordingTimer = null

// Rep pop animation
const showRepPop = ref(false)
const repPopValue = ref(0)
const repPopKey = ref(0)
let repPopTimeout = null

// GO flash when player becomes ready
const showGoFlash = ref(false)
let goFlashTimeout = null

watch(playerReady, (ready) => {
  if (ready) {
    showGoFlash.value = true
    if (goFlashTimeout) clearTimeout(goFlashTimeout)
    goFlashTimeout = setTimeout(() => {
      showGoFlash.value = false
    }, 1500)
  }
})

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

    // Auto-start recording if user toggled it on in setup
    if (recordOnStart.value && sessionId.value) {
      try {
        await api.post(`/api/v1/challenges/sessions/${sessionId.value}/recording/start`)
        isRecording.value = true
        recordingDuration.value = 0
        startRecordingTimer()
      } catch (e) {
        console.error('Auto-start recording failed:', e)
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

let endingSession = false

async function endSession() {
  // Guard against multiple calls (auto_end can fire while awaiting recording stop)
  if (endingSession) return
  endingSession = true

  // Stop frame capture immediately so no more frames flow through WS
  stopFrameCapture()

  // Stop recording first so backend saves the video before session closes
  if (isRecording.value && sessionId.value) {
    try {
      await api.post(`/api/v1/challenges/sessions/${sessionId.value}/recording/stop`)
    } catch { /* best-effort */ }
    isRecording.value = false
    hasRecording.value = true
    stopRecordingTimer()
  }

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

  if (!showAnnotations.value) return

  const landmarks = poseData.landmarks
  if (!landmarks) return

  // Scale from pose detection resolution to canvas
  const sx = canvas.width / poseData.width
  const sy = canvas.height / poseData.height

  ctx.globalAlpha = 0.75

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

  ctx.globalAlpha = 1
}

// ---------- Cleanup ----------

/** End session + stop recording over WS before tearing down resources. */
function gracefulEnd() {
  if (ws && ws.readyState === WebSocket.OPEN) {
    // Stop recording first so backend saves the video
    if (isRecording.value) {
      try { api.post(`/api/v1/challenges/sessions/${sessionId.value}/recording/stop`) } catch {}
      isRecording.value = false
      hasRecording.value = true
    }
    ws.send(JSON.stringify({ type: 'end_session' }))
  }
}

function cleanup() {
  stopFrameCapture()
  stopRecordingTimer()
  if (repPopTimeout) { clearTimeout(repPopTimeout); repPopTimeout = null }
  if (goFlashTimeout) { clearTimeout(goFlashTimeout); goFlashTimeout = null }
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

// Intercept back-button / any navigation away from an active session
onBeforeRouteLeave((to, from, next) => {
  if (phase.value === 'active' || phase.value === 'connecting') {
    gracefulEnd()
    cleanup()
  }
  next()
})

onMounted(() => {
  checkPlacementGuide()
  enumerateCameras()
})

onUnmounted(() => {
  // Safety net — gracefulEnd + cleanup if component is destroyed without route change
  if (phase.value === 'active' || phase.value === 'connecting') {
    gracefulEnd()
  }
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

.info-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 1.1rem;
  color: var(--color-primary);
  cursor: pointer;
  opacity: 0.7;
  transition: opacity 0.15s;
  vertical-align: middle;
  margin-left: 0.25rem;
}
.info-icon:hover {
  opacity: 1;
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

.setup-toggles {
  display: flex;
  gap: 1.5rem;
  margin-top: 0.75rem;
  flex-wrap: wrap;
}

.setup-toggle-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--border-input);
  border-radius: var(--radius-md);
  transition: border-color 0.2s;
}

.setup-toggle-item:has(input:checked) {
  border-color: var(--color-primary);
}

.setup-toggle-item input {
  accent-color: var(--color-primary);
  width: 18px;
  height: 18px;
  cursor: pointer;
}

.setup-toggle-item .toggle-icon {
  color: var(--color-destructive);
  flex-shrink: 0;
}

.toggle-label {
  color: var(--text-muted);
  font-size: 0.85rem;
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
  background: rgba(0, 0, 0, 0.55);
  z-index: 5;
}

.position-overlay.go-overlay {
  background: rgba(0, 0, 0, 0.45);
  z-index: 6;
}

.position-prompt {
  text-align: center;
  padding: 2rem;
}

/* Big status circle indicator */
.status-circle {
  width: 120px;
  height: 120px;
  border-radius: 50%;
  margin: 0 auto 1.25rem;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
}

.status-circle.red {
  background: rgba(231, 76, 60, 0.2);
  border: 4px solid #e74c3c;
  box-shadow: 0 0 30px rgba(231, 76, 60, 0.4), 0 0 60px rgba(231, 76, 60, 0.15);
  animation: circle-pulse-red 2s ease-in-out infinite;
}

.status-circle.green {
  background: rgba(78, 204, 163, 0.25);
  border: 4px solid #4ecca3;
  box-shadow: 0 0 40px rgba(78, 204, 163, 0.5), 0 0 80px rgba(78, 204, 163, 0.2);
  animation: circle-pulse-green 1s ease-in-out infinite;
}

.status-circle-inner {
  width: 70%;
  height: 70%;
  border-radius: 50%;
}

.status-circle.red .status-circle-inner {
  background: radial-gradient(circle, #e74c3c 0%, rgba(231, 76, 60, 0.3) 100%);
}

.status-circle.green .status-circle-inner {
  background: radial-gradient(circle, #4ecca3 0%, rgba(78, 204, 163, 0.3) 100%);
}

@keyframes circle-pulse-red {
  0%, 100% { box-shadow: 0 0 20px rgba(231, 76, 60, 0.3), 0 0 40px rgba(231, 76, 60, 0.1); }
  50% { box-shadow: 0 0 40px rgba(231, 76, 60, 0.5), 0 0 80px rgba(231, 76, 60, 0.2); }
}

@keyframes circle-pulse-green {
  0%, 100% { box-shadow: 0 0 30px rgba(78, 204, 163, 0.4), 0 0 60px rgba(78, 204, 163, 0.15); }
  50% { box-shadow: 0 0 50px rgba(78, 204, 163, 0.6), 0 0 100px rgba(78, 204, 163, 0.25); }
}

.position-text {
  color: #fff;
  font-size: 1.4rem;
  font-weight: 700;
  margin: 0 0 0.25rem;
}

.position-subtext {
  color: rgba(255, 255, 255, 0.5);
  font-size: 0.9rem;
  font-weight: 400;
  margin: 0 0 0.5rem;
}

.go-text {
  color: #4ecca3;
  font-size: 3rem;
  font-weight: 900;
  margin: 0;
  text-shadow: 0 0 30px rgba(78, 204, 163, 0.6);
  letter-spacing: 0.1em;
}

.position-detected {
  color: #4ecca3;
  font-size: 0.85rem;
  font-weight: 600;
  margin-top: 0.25rem;
}

.end-early-btn {
  margin-top: 1.5rem;
  background: transparent;
  border: 1px solid rgba(231, 76, 60, 0.6);
  color: #e74c3c;
  padding: 0.5rem 1.5rem;
  border-radius: var(--radius-md);
  font-size: 0.9rem;
  cursor: pointer;
  transition: background 0.2s;
}
.end-early-btn:hover {
  background: rgba(231, 76, 60, 0.15);
}

/* GO flash transition */
.go-flash-enter-active {
  transition: all 0.3s ease-out;
}
.go-flash-leave-active {
  transition: all 0.6s ease-in;
}
.go-flash-enter-from {
  opacity: 0;
  transform: scale(0.8);
}
.go-flash-leave-to {
  opacity: 0;
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
  align-items: flex-start;
  justify-content: center;
  z-index: 200;
  padding: 1rem;
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
}

.placement-card {
  background: var(--bg-card);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-xl);
  padding: 2rem;
  max-width: 420px;
  width: 100%;
  text-align: center;
  margin: auto 0;
  flex-shrink: 0;
}

.placement-img-wrap {
  margin-bottom: 1rem;
}

.placement-img {
  width: 100%;
  border-radius: var(--radius-md);
  display: block;
}

.guide-steps {
  text-align: left;
  margin-bottom: 1.25rem;
}

.guide-step {
  display: flex;
  gap: 0.75rem;
  align-items: flex-start;
  padding: 0.5rem 0;
}

.step-number {
  flex-shrink: 0;
  width: 26px;
  height: 26px;
  background: var(--color-primary);
  color: #fff;
  border-radius: var(--radius-full);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.8rem;
  font-weight: 700;
  margin-top: 0.1rem;
}

.step-content strong {
  color: var(--text-primary);
  font-size: 0.9rem;
  display: block;
  margin-bottom: 0.1rem;
}

.step-content p {
  color: var(--text-muted);
  font-size: 0.8rem;
  margin: 0;
  line-height: 1.4;
}

.inline-circle {
  display: inline-block;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  vertical-align: middle;
  margin: 0 2px;
}
.inline-circle.red { background: #ef4444; }
.inline-circle.green { background: #22c55e; }

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

/* Maximize / fullscreen mode */
.maximize-btn {
  position: absolute;
  bottom: 0.75rem;
  right: 0.75rem;
  background: rgba(0, 0, 0, 0.5);
  border: none;
  color: #fff;
  width: 36px;
  height: 36px;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  z-index: 15;
  transition: background 0.2s;
}
.maximize-btn:hover {
  background: rgba(0, 0, 0, 0.7);
}

.camera-preview-wrap.maximized,
.video-container.maximized {
  position: fixed;
  inset: 0;
  z-index: 100;
  border-radius: 0;
  aspect-ratio: auto;
  margin: 0;
  background: #000;
}

.camera-preview-wrap.maximized .camera-preview,
.video-container.maximized .stream-video {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.max-overlay-controls {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 12;
  pointer-events: none;
}

.max-start-btn {
  pointer-events: auto;
  background: var(--gradient-primary);
  color: #fff;
  border: none;
  padding: 1rem 2.5rem;
  border-radius: var(--radius-lg);
  font-size: 1.2rem;
  font-weight: 700;
  cursor: pointer;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
  animation: tap-pulse 2.5s ease-in-out infinite;
}

.max-overlay-actions {
  position: absolute;
  bottom: 2rem;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  gap: 1rem;
  z-index: 15;
}

.max-action-btn {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  background: rgba(0, 0, 0, 0.6);
  border: 1.5px solid rgba(255, 255, 255, 0.3);
  color: #fff;
  padding: 0.6rem 1.2rem;
  border-radius: var(--radius-full);
  font-size: 0.85rem;
  font-weight: 600;
  cursor: pointer;
  backdrop-filter: blur(4px);
  transition: background 0.2s;
}
.max-action-btn:hover {
  background: rgba(0, 0, 0, 0.8);
}
.max-action-btn.recording {
  border-color: #e74c3c;
  color: #e74c3c;
}
.max-action-btn.end {
  border-color: rgba(231, 76, 60, 0.6);
  color: #e74c3c;
}
.max-action-btn svg {
  width: 18px;
  height: 18px;
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

  .status-circle {
    width: 100px;
    height: 100px;
  }

  .position-text {
    font-size: 1.1rem;
    padding: 0 1rem;
  }

  .go-text {
    font-size: 2.5rem;
  }
}

/* Landscape orientation — tighten HUD & overlay when rotated */
@media (orientation: landscape) and (max-height: 500px) {
  .hud {
    top: 0.5rem;
    left: 0.5rem;
    gap: 0.75rem;
  }

  .hud-metric {
    padding: 0.3rem 0.75rem;
  }

  .metric-value {
    font-size: 1.3rem;
  }

  .metric-label {
    font-size: 0.65rem;
  }

  .max-overlay-actions {
    bottom: 1rem;
  }

  .position-prompt {
    padding: 1rem;
  }

  .status-circle {
    width: 80px;
    height: 80px;
    margin-bottom: 0.75rem;
  }

  .position-text {
    font-size: 1rem;
  }

  .go-text {
    font-size: 2rem;
  }

  .end-early-btn {
    margin-top: 0.75rem;
    padding: 0.4rem 1.2rem;
    font-size: 0.8rem;
  }

  .leg-status {
    top: 0.5rem;
    right: 0.5rem;
  }

  .form-feedback {
    bottom: 0.5rem;
  }

  .recording-status {
    top: 2.5rem;
  }

  .rep-pop-number {
    font-size: 5rem;
  }

  .maximize-btn {
    bottom: 0.5rem;
    right: 0.5rem;
  }
}
</style>
