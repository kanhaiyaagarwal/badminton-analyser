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
          <button :class="['toggle-btn', { active: layout === 'annotated' }]" @click="layout = 'annotated'">Stacked + Annotated</button>
          <button :class="['toggle-btn', { active: layout === 'overlay' }]" @click="layout = 'overlay'">Overlay</button>
        </div>

        <button @click="toggleVoice" :class="['voice-btn', { active: voiceEnabled }]"
                :title="voiceEnabled ? 'Voice commands ON — will activate when session starts' : 'Enable voice commands'">
          {{ voiceEnabled ? 'Mic ON' : 'Mic OFF' }}
        </button>
        <div v-if="voiceStatus && phase === 'setup'" class="voice-status">{{ voiceStatus }}</div>

        <button @click="startSession" :disabled="!cameraReady || starting" class="start-btn">
          {{ starting ? 'Starting...' : 'Start Mimic' }}
        </button>
      </div>
    </div>

    <!-- Active phase -->
    <div v-else-if="phase === 'active'" class="active-phase" :class="layout">

      <!-- Stacked layout: reference video on top, camera below -->
      <div v-if="layout === 'stacked' || layout === 'annotated'" class="stacked-layout">
        <div class="ref-video-wrap">
          <video ref="refVideo" :src="refVideoUrl" playsinline class="ref-video" @ended="onRefVideoEnded"></video>
          <canvas ref="refOverlayCanvas" class="overlay-canvas"></canvas>
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

      <!-- Hidden video for overlay mode audio (browsers won't extract audio from mp4 via <audio>) -->
      <video ref="refAudio" :src="refVideoUrl" preload="auto" playsinline
             style="width:0;height:0;position:absolute;opacity:0;pointer-events:none"
             @ended="onRefAudioEnded"></video>

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
        <div class="speed-controls">
          <span class="control-label">Speed:</span>
          <button v-for="rate in speedPresets" :key="rate"
                  :class="['speed-btn', { active: playbackRate === rate }]"
                  @click="setPlaybackRate(rate)">
            {{ rate }}x
          </button>
        </div>

        <button @click="togglePause" :class="['pause-btn', { paused }]">
          {{ paused ? 'Resume' : 'Pause' }}
        </button>

        <button @click="toggleVoice" :class="['voice-btn', { active: voiceEnabled }]"
                :title="voiceEnabled ? 'Voice commands ON' : 'Voice commands OFF'">
          {{ voiceEnabled ? 'Mic ON' : 'Mic OFF' }}
        </button>

        <button @click="endSession" class="end-btn">End Session</button>
      </div>

      <div v-if="voiceStatus" class="voice-status">{{ voiceStatus }}</div>
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
const refVideoUrl = computed(() =>
  `/api/v1/mimic/challenges/${challengeId}/video?token=${authStore.accessToken}`
)

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
const refOverlayCanvas = ref(null)
const refVideo = ref(null)
const refAudio = ref(null)

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

// Speed / Pause / Voice
const speedPresets = [0.5, 0.6, 0.8, 1.0]
const playbackRate = ref(1.0)
const paused = ref(false)
const voiceEnabled = ref(false)
const voiceStatus = ref('')
let micStream = null
let audioCtx = null
let audioWorkletNode = null
let pauseStartTime = null

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

    // Start reference video/audio playback
    if (refVideo.value && (layout.value === 'stacked' || layout.value === 'annotated')) {
      refVideo.value.play().catch(() => {})
    }
    if (layout.value === 'overlay' && refAudio.value) {
      refAudio.value.play().catch(() => {})
    }

    // Start audio streaming if mic was enabled in setup phase
    if (voiceEnabled.value && !audioCtx) {
      startAudioStreaming()
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

        // Sync reference video time (stacked/annotated mode)
        if (data.ref_time != null && refVideo.value && (layout.value === 'stacked' || layout.value === 'annotated')) {
          const drift = Math.abs(refVideo.value.currentTime - data.ref_time)
          if (drift > 0.5) {
            refVideo.value.currentTime = data.ref_time
          }
        }

        // Sync reference audio (overlay mode)
        if (data.ref_time != null && layout.value === 'overlay' && refAudio.value) {
          const drift = Math.abs(refAudio.value.currentTime - data.ref_time)
          if (drift > 0.5) {
            refAudio.value.currentTime = data.ref_time
          }
        }

        // Draw skeleton overlays
        if (data.pose || data.ref_landmarks) {
          drawOverlays(data)
        }

      } else if (data.type === 'voice_command') {
        handleVoiceCommand(data.command)
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
  if (frameInterval) return  // already capturing
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
        const currentRefTime = (layout.value === 'overlay')
          ? (refAudio.value ? refAudio.value.currentTime : 0)
          : (refVideo.value ? refVideo.value.currentTime : 0)
        ws.send(JSON.stringify({
          type: 'frame',
          data: base64,
          timestamp: (Date.now() - startTime) / 1000,
          ref_time: currentRefTime,
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

// Limb segment definitions: [startIdx, endIdx, widthStartRatio, widthEndRatio]
const LIMB_SEGMENTS = [
  [11, 13, 0.12, 0.09],  // L upper arm
  [12, 14, 0.12, 0.09],  // R upper arm
  [13, 15, 0.09, 0.06],  // L forearm
  [14, 16, 0.09, 0.06],  // R forearm
  [15, 19, 0.06, 0.04],  // L hand (wrist -> index)
  [16, 20, 0.06, 0.04],  // R hand (wrist -> index)
  [23, 25, 0.16, 0.12],  // L thigh
  [24, 26, 0.16, 0.12],  // R thigh
  [25, 27, 0.12, 0.07],  // L shin
  [26, 28, 0.12, 0.07],  // R shin
  [27, 31, 0.07, 0.04],  // L foot (ankle -> foot index)
  [28, 32, 0.07, 0.04],  // R foot (ankle -> foot index)
]

function _rescaleRefToUser(userLm, refLm) {
  // Scale + translate ref landmarks so they match the user's body size and position.
  // Uses separate X/Y scales so shoulder width AND torso height both match exactly.
  const vis = (lm) => lm && (lm.visibility || 0) >= 0.3
  const uLS = userLm[11], uRS = userLm[12], uLH = userLm[23], uRH = userLm[24]
  const rLS = refLm[11], rRS = refLm[12], rLH = refLm[23], rRH = refLm[24]
  if (!vis(uLS) || !vis(uRS) || !vis(uLH) || !vis(uRH)) return null
  if (!rLS || !rRS || !rLH || !rRH) return null

  // Horizontal: shoulder span
  const uW = Math.abs(uRS.x - uLS.x)
  const rW = Math.abs(rRS.x - rLS.x)
  if (rW < 1) return null

  // Vertical: shoulder-midpoint to hip-midpoint
  const uSMy = (uLS.y + uRS.y) / 2
  const uHMy = (uLH.y + uRH.y) / 2
  const rSMy = (rLS.y + rRS.y) / 2
  const rHMy = (rLH.y + rRH.y) / 2
  const uH = Math.abs(uHMy - uSMy)
  const rH = Math.abs(rHMy - rSMy)
  if (rH < 1) return null

  const sx = uW / rW
  const sy = uH / rH

  // Torso center
  const uCx = (uLS.x + uRS.x + uLH.x + uRH.x) / 4
  const uCy = (uLS.y + uRS.y + uLH.y + uRH.y) / 4
  const rCx = (rLS.x + rRS.x + rLH.x + rRH.x) / 4
  const rCy = (rLS.y + rRS.y + rLH.y + rRH.y) / 4
  const offX = uCx - rCx * sx
  const offY = uCy - rCy * sy

  return refLm.map(lm => ({
    x: lm.x * sx + offX,
    y: lm.y * sy + offY,
    visibility: lm.visibility,
    nx: lm.nx,
    ny: lm.ny,
  }))
}

function _toRefLm(rawLm, w, h) {
  return rawLm.map(lm => ({
    x: lm[0] * w,
    y: lm[1] * h,
    visibility: lm[2],
    nx: lm[0],
    ny: lm[1],
  }))
}

function _applyVideoFitTransform(ctx, canvas, videoWidth, videoHeight) {
  // Compensate for object-fit:contain — the video content may be
  // pillarboxed or letterboxed inside its CSS container.  We need
  // to translate + scale so that video-pixel coordinates land on
  // the actual content area within the canvas.
  const cw = canvas.width
  const ch = canvas.height
  const containerAR = cw / ch
  const videoAR = videoWidth / videoHeight

  let renderW, renderH, offsetX, offsetY
  if (videoAR > containerAR) {
    // Wider video → letterbox (bars top/bottom)
    renderW = cw
    renderH = cw / videoAR
    offsetX = 0
    offsetY = (ch - renderH) / 2
  } else {
    // Taller video → pillarbox (bars left/right)
    renderH = ch
    renderW = ch * videoAR
    offsetX = (cw - renderW) / 2
    offsetY = 0
  }

  ctx.translate(offsetX, offsetY)
  ctx.scale(renderW / videoWidth, renderH / videoHeight)
}

function drawOverlays(data) {
  const canvas = overlayCanvas.value
  if (!canvas) return
  const video = streamVideo.value
  if (!video) return

  const vw = video.videoWidth || 640
  const vh = video.videoHeight || 480

  // Set canvas resolution to CSS size so it aligns with the container
  canvas.width = canvas.clientWidth || vw
  canvas.height = canvas.clientHeight || vh
  const ctx = canvas.getContext('2d')
  ctx.clearRect(0, 0, canvas.width, canvas.height)

  // Transform so video-pixel coords map to the actual content area
  ctx.save()
  _applyVideoFitTransform(ctx, canvas, vw, vh)

  if (layout.value === 'overlay') {
    // Overlay mode: both meshes on user camera canvas
    if (data.pose && data.pose.landmarks) {
      drawBodyMesh(ctx, data.pose.landmarks, vw, vh, '0, 200, 0', 0.7, false, 'You')
    }
    if (data.ref_landmarks) {
      const refLm = _toRefLm(data.ref_landmarks, vw, vh)
      drawBodyMesh(ctx, refLm, vw, vh, '52, 152, 219', 0.7, true, 'Original')
    }
  } else if (layout.value === 'annotated') {
    // Annotated stacked — user mesh (blue) + ref mesh (orange) rescaled to user's body
    if (data.pose && data.pose.landmarks) {
      drawBodyMesh(ctx, data.pose.landmarks, vw, vh, '52, 152, 219', 0.5, false, 'You')
    }
    if (data.ref_landmarks && data.pose && data.pose.landmarks) {
      const refLm = _toRefLm(data.ref_landmarks, vw, vh)
      const scaled = _rescaleRefToUser(data.pose.landmarks, refLm)
      if (scaled) {
        drawBodyMesh(ctx, scaled, vw, vh, '255, 150, 0', 0.6, false, 'Original')
      } else {
        drawBodyMesh(ctx, refLm, vw, vh, '255, 150, 0', 0.6, true, 'Original')
      }
    }
  }
  // stacked (plain): no mesh drawn

  ctx.restore()
}

// Hand/foot landmark indices — MediaPipe gives these low visibility, use relaxed threshold
const LOW_VIS_INDICES = new Set([17, 18, 19, 20, 21, 22, 29, 30, 31, 32])

function drawBodyMesh(ctx, landmarks, w, h, rgb, alpha, useNormalized, label) {
  if (!landmarks || landmarks.length < 33) return

  const pt = (idx) => {
    const lm = landmarks[idx]
    if (!lm) return null
    const minVis = LOW_VIS_INDICES.has(idx) ? 0.05 : 0.3
    if ((lm.visibility || 0) < minVis) return null
    const x = useNormalized ? lm.nx * w : lm.x
    const y = useNormalized ? lm.ny * h : lm.y
    return { x, y }
  }

  const ls = pt(11)
  const rs = pt(12)
  if (!ls || !rs) return
  const baseW = Math.max(10, Math.hypot(ls.x - rs.x, ls.y - rs.y))

  ctx.fillStyle = `rgba(${rgb}, ${alpha})`

  // Torso quad
  const lh = pt(23)
  const rh = pt(24)
  if (ls && rs && lh && rh) {
    ctx.beginPath()
    ctx.moveTo(ls.x, ls.y)
    ctx.lineTo(rs.x, rs.y)
    ctx.lineTo(rh.x, rh.y)
    ctx.lineTo(lh.x, lh.y)
    ctx.closePath()
    ctx.fill()
  }

  // Limb trapezoids
  for (const [aIdx, bIdx, waR, wbR] of LIMB_SEGMENTS) {
    const pa = pt(aIdx)
    const pb = pt(bIdx)
    if (!pa || !pb) continue
    const dx = pb.x - pa.x
    const dy = pb.y - pa.y
    const len = Math.max(1, Math.hypot(dx, dy))
    const nx = -dy / len
    const ny = dx / len
    const wa = baseW * waR
    const wb = baseW * wbR
    ctx.beginPath()
    ctx.moveTo(pa.x + nx * wa, pa.y + ny * wa)
    ctx.lineTo(pa.x - nx * wa, pa.y - ny * wa)
    ctx.lineTo(pb.x - nx * wb, pb.y - ny * wb)
    ctx.lineTo(pb.x + nx * wb, pb.y + ny * wb)
    ctx.closePath()
    ctx.fill()
  }

  // Head circle
  const nose = pt(0)
  if (nose) {
    ctx.beginPath()
    ctx.arc(nose.x, nose.y, baseW * 0.30, 0, 2 * Math.PI)
    ctx.fill()
  }

  // Body label at stomach area (60% down from shoulders to hips)
  if (label && ls && rs && lh && rh) {
    const labelX = (ls.x + rs.x + lh.x + rh.x) / 4
    const shoulderY = (ls.y + rs.y) / 2
    const hipY = (lh.y + rh.y) / 2
    const labelY = shoulderY + (hipY - shoulderY) * 0.6
    const fontSize = Math.max(12, baseW * 0.22)
    ctx.save()
    ctx.font = `bold ${fontSize}px sans-serif`
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    ctx.fillStyle = `rgba(${rgb}, 1)`
    ctx.strokeStyle = 'rgba(0, 0, 0, 0.7)'
    ctx.lineWidth = 3
    ctx.strokeText(label, labelX, labelY)
    ctx.fillText(label, labelX, labelY)
    ctx.restore()
  }
}

// ---------- Speed / Pause / Voice ----------

function setPlaybackRate(rate) {
  playbackRate.value = rate
  if (refVideo.value) refVideo.value.playbackRate = rate
  if (refAudio.value) refAudio.value.playbackRate = rate
}

function togglePause() {
  if (paused.value) {
    resumePlayback()
  } else {
    pausePlayback()
  }
}

function pausePlayback() {
  paused.value = true
  pauseStartTime = Date.now()
  if (refVideo.value) refVideo.value.pause()
  if (refAudio.value) refAudio.value.pause()
  stopFrameCapture()
}

function resumePlayback() {
  paused.value = false

  // Shift startTime forward by the pause duration so elapsed time
  // and frame timestamps don't include time spent paused.
  if (pauseStartTime) {
    startTime += Date.now() - pauseStartTime
    pauseStartTime = null
  }

  // Restart elapsed display timer (stopFrameCapture killed it)
  if (!elapsedTimer) {
    elapsedTimer = setInterval(() => {
      elapsed.value = (Date.now() - startTime) / 1000
    }, 1000)
  }

  if (refVideo.value && (layout.value === 'stacked' || layout.value === 'annotated')) {
    refVideo.value.play().catch(() => {})
  }
  if (refAudio.value && layout.value === 'overlay') {
    refAudio.value.play().catch(() => {})
  }
  startFrameCapture()
}

function toggleVoice() {
  if (voiceEnabled.value) {
    stopVoice()
  } else {
    startVoice()
  }
}

async function startVoice() {
  if (voiceEnabled.value) return

  voiceEnabled.value = true
  voiceStatus.value = 'Requesting mic access...'

  try {
    micStream = await navigator.mediaDevices.getUserMedia({ audio: true })
  } catch (e) {
    voiceStatus.value = 'Mic denied — allow microphone in browser settings and retry'
    voiceEnabled.value = false
    return
  }

  // User may have toggled off while awaiting permission prompt
  if (!voiceEnabled.value) {
    micStream.getTracks().forEach(t => t.stop())
    micStream = null
    return
  }

  voiceStatus.value = 'Mic ready — will listen when session starts'

  // If session is already active (toggled during session), start streaming now
  if (phase.value === 'active' && ws && ws.readyState === WebSocket.OPEN) {
    startAudioStreaming()
  }
}

async function startAudioStreaming() {
  if (audioCtx) return  // already streaming
  if (!micStream) return

  try {
    audioCtx = new AudioContext({ sampleRate: 16000 })
    await audioCtx.audioWorklet.addModule('/pcm-processor.js')

    const source = audioCtx.createMediaStreamSource(micStream)
    audioWorkletNode = new AudioWorkletNode(audioCtx, 'pcm-processor')

    audioWorkletNode.port.onmessage = (e) => {
      if (!voiceEnabled.value || !ws || ws.readyState !== WebSocket.OPEN) return
      const bytes = new Uint8Array(e.data)
      let binary = ''
      for (let i = 0; i < bytes.length; i++) {
        binary += String.fromCharCode(bytes[i])
      }
      const b64 = btoa(binary)
      ws.send(JSON.stringify({ type: 'audio', data: b64 }))
    }

    source.connect(audioWorkletNode)
    audioWorkletNode.connect(audioCtx.destination)
    voiceStatus.value = 'Listening...'
  } catch (e) {
    voiceStatus.value = `Failed to start audio capture: ${e.message}`
  }
}

function stopVoice() {
  voiceEnabled.value = false
  voiceStatus.value = ''
  if (audioWorkletNode) {
    audioWorkletNode.disconnect()
    audioWorkletNode = null
  }
  if (audioCtx) {
    audioCtx.close().catch(() => {})
    audioCtx = null
  }
  if (micStream) {
    micStream.getTracks().forEach(t => t.stop())
    micStream = null
  }
}

function handleVoiceCommand(cmd) {
  if (cmd === 'pause') {
    voiceStatus.value = 'Heard: pause'
    pausePlayback()
  } else if (cmd === 'play') {
    voiceStatus.value = 'Heard: play'
    resumePlayback()
  } else if (cmd === 'slower') {
    const newRate = Math.max(0.3, Math.round((playbackRate.value - 0.2) * 10) / 10)
    setPlaybackRate(newRate)
    voiceStatus.value = `Heard: slower → ${newRate}x`
  } else if (cmd === 'faster') {
    const newRate = Math.min(1.0, Math.round((playbackRate.value + 0.2) * 10) / 10)
    setPlaybackRate(newRate)
    voiceStatus.value = `Heard: faster → ${newRate}x`
  }
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

function onRefAudioEnded() {
  // Loop the reference audio (overlay mode)
  if (refAudio.value) {
    refAudio.value.currentTime = 0
    refAudio.value.play().catch(() => {})
  }
}

function cleanup() {
  stopFrameCapture()
  stopVoice()
  paused.value = false
  pauseStartTime = null
  if (refAudio.value) {
    refAudio.value.pause()
  }
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
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.speed-controls {
  display: flex;
  align-items: center;
  gap: 0.3rem;
}

.control-label {
  font-size: 0.8rem;
  color: var(--text-muted);
  margin-right: 0.2rem;
}

.speed-btn {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md, 8px);
  padding: 0.35rem 0.6rem;
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 0.8rem;
}

.speed-btn.active {
  background: var(--color-primary);
  color: white;
  border-color: var(--color-primary);
}

.pause-btn {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md, 8px);
  padding: 0.4rem 1rem;
  color: var(--text-primary);
  cursor: pointer;
  font-size: 0.85rem;
  font-weight: 500;
}

.pause-btn.paused {
  background: #27ae60;
  color: white;
  border-color: #27ae60;
}

.voice-btn {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md, 8px);
  padding: 0.4rem 0.8rem;
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 0.8rem;
}

.voice-btn.active {
  background: #e74c3c;
  color: white;
  border-color: #e74c3c;
}

.voice-status {
  text-align: center;
  font-size: 0.8rem;
  color: var(--text-muted);
  padding: 0.25rem 0;
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
