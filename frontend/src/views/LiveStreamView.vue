<template>
  <div class="live-stream-view">
    <div class="header">
      <router-link to="/dashboard" class="back-link">Back to Dashboard</router-link>
      <h1>Live Analysis</h1>
    </div>

    <!-- Loading State -->
    <div v-if="step === 'loading'" class="loading-section">
      <div class="section-card">
        <p>Checking for active sessions...</p>
      </div>
    </div>

    <!-- Resume Prompt -->
    <div v-if="step === 'resume_prompt'" class="resume-section">
      <div class="section-card">
        <h2>Active Session Found</h2>
        <p class="hint">You have an active streaming session. Would you like to resume?</p>

        <div class="active-session-info">
          <p><strong>Session:</strong> {{ activeSession?.title || `Session #${activeSession?.id}` }}</p>
          <p><strong>Status:</strong> {{ activeSession?.status }}</p>
          <p><strong>Shots detected:</strong> {{ activeSession?.total_shots || 0 }}</p>
        </div>

        <div class="resume-actions">
          <button @click="resumeSession" class="btn-primary">
            Resume Session
          </button>
          <button @click="abandonSession" class="btn-secondary">
            Start New Session
          </button>
        </div>
      </div>
    </div>

    <!-- Step 1: Create Session -->
    <div v-else-if="step === 'setup'" class="setup-section">
      <div class="section-card">
        <h2>1. Create Session</h2>
        <div class="form-group">
          <label>Session Title (optional)</label>
          <input v-model="sessionTitle" type="text" placeholder="My Practice Session" />
        </div>
        <button @click="createSession" :disabled="creating" class="btn-primary">
          {{ creating ? 'Creating...' : 'Create Session' }}
        </button>
      </div>
    </div>

    <!-- Step 2: Set Court Boundary -->
    <div v-else-if="step === 'court'" class="court-section">
      <div class="section-card">
        <h2>2. Set Court Boundary</h2>
        <p class="hint">
          Click on the 4 corners of the court in order:
          <span :class="['corner-label', { active: currentCorner === 0 }]">Top-Left</span> →
          <span :class="['corner-label', { active: currentCorner === 1 }]">Top-Right</span> →
          <span :class="['corner-label', { active: currentCorner === 2 }]">Bottom-Right</span> →
          <span :class="['corner-label', { active: currentCorner === 3 }]">Bottom-Left</span>
        </p>

        <!-- Court Selection Video Preview -->
        <div class="court-selection-container" ref="courtSelectionContainer">
          <video
            ref="courtPreviewVideo"
            autoplay
            playsinline
            muted
            class="court-preview-video"
          ></video>
          <canvas
            ref="courtSelectionCanvas"
            class="court-selection-canvas"
            @click="handleCourtClick"
          ></canvas>

          <div v-if="!courtCameraReady" class="camera-placeholder">
            <p>{{ courtCameraError || 'Initializing camera...' }}</p>
          </div>

          <div class="corner-indicator" v-if="courtCameraReady">
            <template v-if="currentCorner < 4">
              Selecting: {{ cornerNames[currentCorner] }} ({{ currentCorner + 1 }}/4)
            </template>
            <template v-else>
              All corners selected!
            </template>
          </div>
        </div>

        <div class="court-actions">
          <button @click="useFullFrame" class="btn-secondary btn-fullframe">
            Use Full Frame
          </button>
          <button @click="resetCourtPoints" class="btn-secondary" :disabled="selectedCorners === 0">
            Reset Points
          </button>
          <button @click="undoLastPoint" class="btn-secondary" :disabled="selectedCorners === 0">
            Undo Last
          </button>
        </div>

        <div class="court-status">
          <div v-for="(name, index) in cornerNames" :key="name" class="corner-status">
            <span class="corner-name">{{ name }}:</span>
            <span v-if="cornerSelected(index)" class="corner-coords">
              ({{ getCornerCoords(index)[0] }}, {{ getCornerCoords(index)[1] }})
            </span>
            <span v-else class="corner-pending">Click to select</span>
          </div>
        </div>

        <button @click="setupCourt" :disabled="!isCourtValid" class="btn-primary">
          {{ isCourtValid ? 'Set Court Boundary' : `Select ${4 - selectedCorners} more corner(s)` }}
        </button>
      </div>
    </div>

    <!-- Step 3: Live Streaming -->
    <div v-else-if="step === 'streaming'" class="streaming-section">
      <div class="stream-layout">
        <div class="stream-main">
          <CameraCapture
            ref="streamCamera"
            :court-overlay="courtBoundary"
            :pose-data="currentPose"
            :show-annotations="showAnnotations"
            :auto-start="true"
            @frame="handleFrame"
            @stream-start="handleStreamStart"
            @stream-stop="handleStreamStop"
            @error="handleError"
          />

          <!-- Stream Controls Bar -->
          <div class="stream-controls-bar">
            <!-- Session Info -->
            <div class="session-info-bar">
              <span class="info-label">Session #{{ sessionId }}</span>
              <span class="frames-label">{{ liveStats.framesProcessed }} frames</span>
            </div>

            <div class="controls-right">
              <!-- Annotation Toggle -->
              <label class="toggle-control">
                <input type="checkbox" v-model="showAnnotations" />
                <span class="toggle-slider"></span>
                <span class="toggle-text">Skeleton</span>
              </label>

              <!-- Recording Status -->
              <div v-if="isRecording" class="recording-status">
                <span class="recording-dot"></span>
                <span class="recording-time">{{ formatRecordingTime(recordingDuration) }}</span>
              </div>
            </div>
          </div>

          <div class="stream-actions">
            <button
              @click="toggleRecording"
              :class="['btn-record', { recording: isRecording }]"
            >
              <svg class="btn-icon" viewBox="0 0 24 24" fill="currentColor">
                <circle v-if="!isRecording" cx="12" cy="12" r="8"/>
                <rect v-else x="8" y="8" width="8" height="8" rx="1"/>
              </svg>
              {{ isRecording ? 'Stop Recording' : 'Start Recording' }}
            </button>
            <button @click="endSession" class="btn-end">
              End Session
            </button>
          </div>

          <!-- Recording Info -->
          <div v-if="hasRecording" class="recording-info">
            <svg class="info-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"/>
            </svg>
            <span>Recording saved - will be available for download when session ends</span>
          </div>
        </div>

        <div class="stream-sidebar">
          <LiveAnnotation
            :last-shot="liveStats.lastShotType"
            :last-shot-confidence="liveStats.lastShotConfidence"
            :position="lastPosition"
            :court-boundary="courtBoundary"
            :frames-processed="liveStats.framesProcessed"
          />
          <LiveStats :stats="liveStats" />
          <LiveHeatmap
            :positions="footPositions"
            :court-boundary="courtBoundary"
          />
        </div>
      </div>
    </div>

    <!-- Session Ended / Results -->
    <div v-else-if="step === 'ended'" class="results-section">
      <div class="section-card">
        <h2>Session Complete</h2>

        <div v-if="finalReport" class="report-summary">
          <div class="summary-stats">
            <div class="stat">
              <span class="value">{{ finalReport.summary?.total_shots || 0 }}</span>
              <span class="label">Total Shots</span>
            </div>
            <div class="stat">
              <span class="value">{{ finalReport.summary?.total_rallies || 0 }}</span>
              <span class="label">Rallies</span>
            </div>
            <div class="stat">
              <span class="value">{{ formatDuration(finalReport.summary?.session_duration) }}</span>
              <span class="label">Duration</span>
            </div>
          </div>

          <div class="shot-breakdown">
            <h3>Shot Distribution</h3>
            <div v-for="(count, type) in finalReport.shot_distribution" :key="type" class="shot-row">
              <span class="shot-type">{{ formatShotType(type) }}</span>
              <span class="shot-count">{{ count }}</span>
            </div>
          </div>
        </div>

        <button @click="startNewSession" class="btn-primary">
          Start New Session
        </button>
      </div>
    </div>

    <!-- Error Display -->
    <div v-if="error" class="error-toast">
      {{ error }}
      <button @click="error = ''" class="dismiss">X</button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import api from '../api/client'
import CameraCapture from '../components/CameraCapture.vue'
import LiveStats from '../components/LiveStats.vue'
import LiveHeatmap from '../components/LiveHeatmap.vue'
import LiveAnnotation from '../components/LiveAnnotation.vue'
import { useAuthStore } from '../stores/auth'

const authStore = useAuthStore()

const step = ref('loading') // Start with loading to check for active sessions
const activeSession = ref(null) // Store found active session
const sessionId = ref(null)
const sessionTitle = ref('')
const creating = ref(false)
const error = ref('')

const courtBoundary = ref({
  top_left: [0, 0],
  top_right: [0, 0],
  bottom_left: [0, 0],
  bottom_right: [0, 0]
})

// Court selection state
const courtPreviewVideo = ref(null)
const courtSelectionCanvas = ref(null)
const courtSelectionContainer = ref(null)
const courtCameraReady = ref(false)
const courtCameraError = ref('')
const currentCorner = ref(0)
const cornerNames = ['Top-Left', 'Top-Right', 'Bottom-Right', 'Bottom-Left']
let courtMediaStream = null

const isRecording = ref(false)
const hasRecording = ref(false)
const recordingDuration = ref(0)
const showAnnotations = ref(true)
const finalReport = ref(null)
let recordingTimer = null

// Live stats
const liveStats = ref({
  totalShots: 0,
  currentRally: 0,
  shotDistribution: {},
  lastShotType: null,
  lastShotConfidence: 0,
  framesProcessed: 0,
  detectionRate: 0,
  coachingTip: ''
})

const footPositions = ref([])
const lastPosition = ref(null)
const currentPose = ref(null)

// WebSocket
let ws = null

const isCourtValid = computed(() => {
  const c = courtBoundary.value
  return c.top_left[0] > 0 && c.top_left[1] > 0 &&
         c.top_right[0] > 0 && c.top_right[1] > 0 &&
         c.bottom_left[0] > 0 && c.bottom_left[1] > 0 &&
         c.bottom_right[0] > 0 && c.bottom_right[1] > 0
})

const selectedCorners = computed(() => {
  let count = 0
  const c = courtBoundary.value
  if (c.top_left[0] > 0 && c.top_left[1] > 0) count++
  if (c.top_right[0] > 0 && c.top_right[1] > 0) count++
  if (c.bottom_right[0] > 0 && c.bottom_right[1] > 0) count++
  if (c.bottom_left[0] > 0 && c.bottom_left[1] > 0) count++
  return count
})

onMounted(async () => {
  await checkActiveSession()
})

onUnmounted(() => {
  if (ws) {
    ws.close()
  }
  if (courtMediaStream) {
    courtMediaStream.getTracks().forEach(track => track.stop())
  }
  stopRecordingTimer()
})

async function checkActiveSession() {
  try {
    const response = await api.get('/api/v1/stream/sessions', {
      params: { status_filter: 'streaming', limit: 1 }
    })
    const sessions = response.data.sessions || []

    if (sessions.length > 0) {
      activeSession.value = sessions[0]
      step.value = 'resume_prompt'
    } else {
      step.value = 'setup'
    }
  } catch (e) {
    console.error('Failed to check active sessions:', e)
    step.value = 'setup'
  }
}

async function resumeSession() {
  if (!activeSession.value) return

  sessionId.value = activeSession.value.id
  sessionTitle.value = activeSession.value.title || ''

  // Get session status to get court boundary
  try {
    const statusResponse = await api.get(`/api/v1/stream/${sessionId.value}/status`)
    // The session should already have court set up

    // Ensure token is valid before WebSocket connection
    const tokenValid = await authStore.ensureValidToken()
    if (!tokenValid) {
      error.value = 'Session expired. Please log in again.'
      return
    }

    // Connect WebSocket and go to streaming
    connectWebSocket()
    step.value = 'streaming'
  } catch (e) {
    error.value = e.response?.data?.detail || 'Failed to resume session'
    step.value = 'setup'
  }
}

function abandonSession() {
  activeSession.value = null
  step.value = 'setup'
}

// Watch for step changes to initialize court camera
watch(step, async (newStep) => {
  console.log('Step changed to:', newStep)
  if (newStep === 'court') {
    await initCourtCamera()
  }
  // Note: camera is now released in setupCourt before transitioning to streaming
})

async function initCourtCamera() {
  try {
    // On mobile, explicitly request back camera
    const isMobile = /Android|iPhone|iPad|iPod/i.test(navigator.userAgent)
    const videoConstraints = {
      width: { ideal: 1280 },
      height: { ideal: 720 }
    }

    if (isMobile) {
      // Use exact facingMode on mobile to ensure back camera
      videoConstraints.facingMode = { exact: 'environment' }
    } else {
      videoConstraints.facingMode = 'environment'
    }

    try {
      courtMediaStream = await navigator.mediaDevices.getUserMedia({
        video: videoConstraints
      })
    } catch (e) {
      // If exact constraint fails, try without it
      console.log('Exact facingMode failed, trying without:', e.message)
      courtMediaStream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 1280 },
          height: { ideal: 720 },
          facingMode: 'environment'
        }
      })
    }

    if (courtPreviewVideo.value) {
      courtPreviewVideo.value.srcObject = courtMediaStream
      await courtPreviewVideo.value.play()
    }

    courtCameraReady.value = true
    courtCameraError.value = ''

    // Setup canvas size after video is ready
    setTimeout(() => {
      if (courtSelectionCanvas.value && courtPreviewVideo.value) {
        const container = courtSelectionContainer.value
        if (container) {
          courtSelectionCanvas.value.width = container.offsetWidth
          courtSelectionCanvas.value.height = container.offsetHeight
        }
      }
      drawCourtOverlay()
    }, 100)
  } catch (e) {
    courtCameraError.value = 'Camera access denied. Please allow camera access.'
    error.value = courtCameraError.value
  }
}

function handleCourtClick(event) {
  if (!courtCameraReady.value || currentCorner.value >= 4) return

  const canvas = courtSelectionCanvas.value
  const rect = canvas.getBoundingClientRect()

  // Get click position relative to canvas
  const x = Math.round(event.clientX - rect.left)
  const y = Math.round(event.clientY - rect.top)

  // Map to video coordinates (if video is different size)
  const video = courtPreviewVideo.value
  const scaleX = video.videoWidth / canvas.width
  const scaleY = video.videoHeight / canvas.height
  const videoX = Math.round(x * scaleX)
  const videoY = Math.round(y * scaleY)

  // Set the corner based on current selection index
  const cornerKeys = ['top_left', 'top_right', 'bottom_right', 'bottom_left']
  const key = cornerKeys[currentCorner.value]
  courtBoundary.value[key] = [videoX, videoY]

  currentCorner.value++
  drawCourtOverlay()
}

function drawCourtOverlay() {
  const canvas = courtSelectionCanvas.value
  if (!canvas) return

  const ctx = canvas.getContext('2d')
  ctx.clearRect(0, 0, canvas.width, canvas.height)

  const video = courtPreviewVideo.value
  if (!video) return

  const scaleX = canvas.width / (video.videoWidth || 1280)
  const scaleY = canvas.height / (video.videoHeight || 720)

  const corners = [
    courtBoundary.value.top_left,
    courtBoundary.value.top_right,
    courtBoundary.value.bottom_right,
    courtBoundary.value.bottom_left
  ]

  // Draw selected points
  const colors = ['#e74c3c', '#f39c12', '#2ecc71', '#3498db']
  corners.forEach((corner, index) => {
    if (corner[0] > 0 && corner[1] > 0) {
      const x = corner[0] * scaleX
      const y = corner[1] * scaleY

      // Draw point
      ctx.beginPath()
      ctx.arc(x, y, 10, 0, Math.PI * 2)
      ctx.fillStyle = colors[index]
      ctx.fill()
      ctx.strokeStyle = 'white'
      ctx.lineWidth = 2
      ctx.stroke()

      // Draw label
      ctx.fillStyle = 'white'
      ctx.font = 'bold 12px sans-serif'
      ctx.fillText(cornerNames[index], x + 15, y + 5)
    }
  })

  // Draw lines connecting selected points
  const selectedPoints = corners.filter(c => c[0] > 0 && c[1] > 0)
  if (selectedPoints.length >= 2) {
    ctx.strokeStyle = '#4ecca3'
    ctx.lineWidth = 2
    ctx.beginPath()

    const validCorners = corners.map((c, i) => ({ coords: c, index: i }))
      .filter(c => c.coords[0] > 0 && c.coords[1] > 0)

    if (validCorners.length >= 2) {
      const first = validCorners[0]
      ctx.moveTo(first.coords[0] * scaleX, first.coords[1] * scaleY)

      for (let i = 1; i < validCorners.length; i++) {
        const c = validCorners[i]
        ctx.lineTo(c.coords[0] * scaleX, c.coords[1] * scaleY)
      }

      // Close the shape if all 4 corners are selected
      if (validCorners.length === 4) {
        ctx.closePath()
        ctx.fillStyle = 'rgba(78, 204, 163, 0.15)'
        ctx.fill()
      }
      ctx.stroke()
    }
  }
}

function resetCourtPoints() {
  courtBoundary.value = {
    top_left: [0, 0],
    top_right: [0, 0],
    bottom_left: [0, 0],
    bottom_right: [0, 0]
  }
  currentCorner.value = 0
  drawCourtOverlay()
}

function undoLastPoint() {
  if (currentCorner.value > 0) {
    currentCorner.value--
    const cornerKeys = ['top_left', 'top_right', 'bottom_right', 'bottom_left']
    const key = cornerKeys[currentCorner.value]
    courtBoundary.value[key] = [0, 0]
    drawCourtOverlay()
  }
}

function useFullFrame() {
  // Set court boundary to full camera frame
  const video = courtPreviewVideo.value
  if (!video) {
    error.value = 'Camera not ready'
    return
  }

  const width = video.videoWidth || 1280
  const height = video.videoHeight || 720

  // Add small margin (5%) to avoid edge issues
  const marginX = Math.round(width * 0.02)
  const marginY = Math.round(height * 0.02)

  courtBoundary.value = {
    top_left: [marginX, marginY],
    top_right: [width - marginX, marginY],
    bottom_right: [width - marginX, height - marginY],
    bottom_left: [marginX, height - marginY]
  }
  currentCorner.value = 4 // All corners selected
  drawCourtOverlay()
}

function cornerSelected(index) {
  const cornerKeys = ['top_left', 'top_right', 'bottom_right', 'bottom_left']
  const key = cornerKeys[index]
  const c = courtBoundary.value[key]
  return c[0] > 0 && c[1] > 0
}

function getCornerCoords(index) {
  const cornerKeys = ['top_left', 'top_right', 'bottom_right', 'bottom_left']
  const key = cornerKeys[index]
  return courtBoundary.value[key]
}

async function createSession() {
  creating.value = true
  error.value = ''

  try {
    const response = await api.post('/api/v1/stream/create', {
      title: sessionTitle.value || 'Live Session',
      frame_rate: 10,
      quality: 'medium'
    })

    sessionId.value = response.data.session_id
    step.value = 'court'
  } catch (e) {
    error.value = e.response?.data?.detail || 'Failed to create session'
  } finally {
    creating.value = false
  }
}

async function setupCourt() {
  try {
    await api.post(`/api/v1/stream/${sessionId.value}/setup-court`, {
      court_boundary: courtBoundary.value
    })

    // Start the stream
    await api.post(`/api/v1/stream/${sessionId.value}/start`)

    // Stop the court camera first to release it
    if (courtMediaStream) {
      console.log('Releasing court camera...')
      courtMediaStream.getTracks().forEach(track => track.stop())
      courtMediaStream = null
      courtCameraReady.value = false
    }

    // Small delay to ensure camera is released
    await new Promise(resolve => setTimeout(resolve, 200))

    // Ensure token is valid before WebSocket connection
    const tokenValid = await authStore.ensureValidToken()
    if (!tokenValid) {
      error.value = 'Session expired. Please log in again.'
      return
    }

    // Connect WebSocket
    connectWebSocket()

    step.value = 'streaming'
  } catch (e) {
    error.value = e.response?.data?.detail || 'Failed to setup court'
  }
}

function connectWebSocket() {
  const token = authStore.accessToken
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = window.location.host
  const wsUrl = `${protocol}//${host}/ws/stream/${sessionId.value}?token=${token}`

  console.log('Connecting WebSocket to:', wsUrl)
  ws = new WebSocket(wsUrl)

  ws.onopen = () => {
    console.log('WebSocket connected successfully, readyState:', ws.readyState)
  }

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      // Debug: log received messages periodically
      if (data.type === 'analysis_result' && data.stats?.frames_processed % 30 === 0) {
        console.log('Received analysis result, frames:', data.stats?.frames_processed)
      }
      handleWebSocketMessage(data)
    } catch (e) {
      console.error('Failed to parse WS message', e)
    }
  }

  ws.onerror = (event) => {
    console.error('WebSocket error', event)
    error.value = 'Connection error'
  }

  ws.onclose = (event) => {
    console.log('WebSocket closed, code:', event.code, 'reason:', event.reason)
    // Handle specific close codes
    if (event.code === 4001) {
      error.value = 'Session expired. Please log in again.'
    } else if (event.code === 4004) {
      error.value = 'Stream session not found.'
    } else if (event.code === 4000) {
      error.value = 'Stream session not ready. Please set up court first.'
    } else if (event.code === 4002) {
      error.value = 'Another device is already streaming to this session.'
    }
  }
}

function handleWebSocketMessage(data) {
  if (data.type === 'analysis_result') {
    // Update stats
    if (data.stats) {
      liveStats.value = {
        totalShots: data.stats.total_shots || 0,
        currentRally: data.stats.current_rally || 0,
        shotDistribution: data.stats.shot_distribution || {},
        lastShotType: data.stats.last_shot_type,
        lastShotConfidence: data.stats.last_shot_confidence || 0,
        framesProcessed: data.stats.frames_processed || 0,
        detectionRate: data.stats.player_detection_rate || 0,
        coachingTip: ''
      }
    }

    // Update shot info
    if (data.shot) {
      console.log('New shot detected:', data.shot.shot_type, 'confidence:', data.shot.confidence)
      liveStats.value.lastShotType = data.shot.shot_type
      liveStats.value.lastShotConfidence = data.shot.confidence
      if (data.shot.coaching_tip) {
        liveStats.value.coachingTip = data.shot.coaching_tip
      }
    }

    // Update positions
    if (data.position) {
      lastPosition.value = {
        x: data.position.x,
        y: data.position.y
      }

      footPositions.value.push({
        x: data.position.x,
        y: data.position.y
      })

      // Keep last 500 positions
      if (footPositions.value.length > 500) {
        footPositions.value = footPositions.value.slice(-500)
      }
    }

    // Update pose for skeleton overlay
    if (data.pose) {
      currentPose.value = data.pose
      // Debug: log pose data occasionally
      if (liveStats.value.framesProcessed % 60 === 0) {
        console.log('Pose data received:', data.pose.landmarks?.length, 'landmarks')
      }
    } else if (liveStats.value.framesProcessed % 60 === 0) {
      console.log('No pose data in frame', liveStats.value.framesProcessed)
    }
  } else if (data.type === 'stream_ended') {
    finalReport.value = data.report
    step.value = 'ended'
  }
}

function handleFrame(frameData) {
  if (ws && ws.readyState === WebSocket.OPEN) {
    // Debug: log every 30th frame to avoid spam
    if (liveStats.value.framesProcessed % 30 === 0) {
      console.log('Sending frame', liveStats.value.framesProcessed, 'size:', frameData.data?.length)
    }
    ws.send(JSON.stringify({
      type: 'frame',
      data: frameData.data,
      timestamp: frameData.timestamp,
      width: frameData.width,
      height: frameData.height
    }))
  } else {
    console.warn('WebSocket not open, state:', ws?.readyState)
  }
}

function handlePreviewFrame(frameData) {
  // Preview frame for court setup - no analysis needed
}

function handleStreamStart(config) {
  console.log('CameraCapture stream started', config)
  console.log('WebSocket state:', ws?.readyState, 'Open=', WebSocket.OPEN)
}

function handleStreamStop() {
  console.log('Stream stopped')
}

function handleError(msg) {
  error.value = msg
}

async function toggleRecording() {
  try {
    if (isRecording.value) {
      await api.post(`/api/v1/stream/${sessionId.value}/recording/stop`)
      isRecording.value = false
      hasRecording.value = true
      stopRecordingTimer()
    } else {
      await api.post(`/api/v1/stream/${sessionId.value}/recording/start`)
      isRecording.value = true
      recordingDuration.value = 0
      startRecordingTimer()
    }
  } catch (e) {
    error.value = e.response?.data?.detail || 'Recording error'
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

async function endSession() {
  try {
    // Send end message via WebSocket
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'end_stream' }))
    }

    // Also call API endpoint
    const response = await api.post(`/api/v1/stream/${sessionId.value}/end`)
    finalReport.value = response.data.report

    if (ws) {
      ws.close()
    }

    step.value = 'ended'
  } catch (e) {
    error.value = e.response?.data?.detail || 'Failed to end session'
  }
}

function startNewSession() {
  sessionId.value = null
  sessionTitle.value = ''
  liveStats.value = {
    totalShots: 0,
    currentRally: 0,
    shotDistribution: {},
    lastShotType: null,
    lastShotConfidence: 0,
    framesProcessed: 0,
    detectionRate: 0,
    coachingTip: ''
  }
  footPositions.value = []
  lastPosition.value = null
  currentPose.value = null
  finalReport.value = null
  isRecording.value = false
  hasRecording.value = false
  recordingDuration.value = 0
  showAnnotations.value = true
  stopRecordingTimer()
  step.value = 'setup'
}

function formatShotType(type) {
  if (!type) return ''
  return type.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

function formatDuration(seconds) {
  if (!seconds) return '0s'
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  if (mins > 0) {
    return `${mins}m ${secs}s`
  }
  return `${secs}s`
}
</script>

<style scoped>
.live-stream-view {
  max-width: 1200px;
  margin: 0 auto;
  padding: 1rem;
}

.header {
  margin-bottom: 2rem;
}

.back-link {
  color: #888;
  text-decoration: none;
  font-size: 0.9rem;
}

.back-link:hover {
  color: #4ecca3;
}

h1 {
  color: #4ecca3;
  margin: 0.5rem 0 0 0;
}

.section-card {
  background: #16213e;
  border-radius: 12px;
  padding: 1.5rem;
}

.section-card h2 {
  color: #eee;
  margin: 0 0 1rem 0;
}

.hint {
  color: #888;
  margin-bottom: 1rem;
}

.form-group {
  margin-bottom: 1rem;
}

.form-group label {
  display: block;
  color: #888;
  margin-bottom: 0.5rem;
}

.form-group input {
  width: 100%;
  padding: 0.75rem;
  background: #0f0f1a;
  border: 1px solid #3a3a5a;
  border-radius: 8px;
  color: #eee;
  font-size: 1rem;
}

.btn-primary {
  display: inline-block;
  padding: 0.75rem 1.5rem;
  background: #4ecca3;
  color: #1a1a2e;
  border: none;
  border-radius: 8px;
  font-weight: bold;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-primary:hover:not(:disabled) {
  background: #3db892;
}

.btn-primary:disabled {
  background: #888;
  cursor: not-allowed;
}

.coord-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
  margin-bottom: 1rem;
}

.coord-input {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.coord-input label {
  color: #888;
  font-size: 0.85rem;
}

.coord-input input {
  padding: 0.5rem;
  background: #0f0f1a;
  border: 1px solid #3a3a5a;
  border-radius: 6px;
  color: #eee;
  width: 80px;
}

.stream-layout {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 1.5rem;
}

@media (max-width: 900px) {
  .stream-layout {
    grid-template-columns: 1fr;
  }
}

.stream-main {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.stream-actions {
  display: flex;
  gap: 1rem;
}

.btn-record {
  flex: 1;
  padding: 0.75rem;
  background: #16213e;
  border: 2px solid #e74c3c;
  border-radius: 8px;
  color: #e74c3c;
  font-weight: bold;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-record:hover {
  background: rgba(231, 76, 60, 0.1);
}

.btn-record.recording {
  background: #e74c3c;
  color: white;
  animation: pulse-record 1s infinite;
}

@keyframes pulse-record {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.8; }
}

.btn-end {
  padding: 0.75rem 1.5rem;
  background: rgba(231, 76, 60, 0.2);
  border: none;
  border-radius: 8px;
  color: #e74c3c;
  font-weight: bold;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-end:hover {
  background: #e74c3c;
  color: white;
}

.stream-sidebar {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.results-section .section-card {
  text-align: center;
}

.report-summary {
  margin: 1.5rem 0;
}

.summary-stats {
  display: flex;
  justify-content: center;
  gap: 2rem;
  margin-bottom: 1.5rem;
}

.stat {
  text-align: center;
}

.stat .value {
  display: block;
  font-size: 2rem;
  font-weight: bold;
  color: #4ecca3;
}

.stat .label {
  color: #888;
  font-size: 0.9rem;
}

.shot-breakdown {
  text-align: left;
  max-width: 300px;
  margin: 0 auto;
}

.shot-breakdown h3 {
  color: #eee;
  font-size: 1rem;
  margin-bottom: 0.75rem;
}

.shot-row {
  display: flex;
  justify-content: space-between;
  padding: 0.5rem 0;
  border-bottom: 1px solid #3a3a5a;
}

.shot-type {
  color: #888;
}

.shot-count {
  color: #4ecca3;
  font-weight: bold;
}

.error-toast {
  position: fixed;
  bottom: 2rem;
  left: 50%;
  transform: translateX(-50%);
  padding: 1rem 1.5rem;
  background: #e74c3c;
  color: white;
  border-radius: 8px;
  display: flex;
  align-items: center;
  gap: 1rem;
  z-index: 1000;
}

.error-toast .dismiss {
  background: none;
  border: none;
  color: white;
  cursor: pointer;
  font-weight: bold;
}

/* Court Selection Styles */
.corner-label {
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
  font-weight: 500;
  color: #888;
  transition: all 0.2s;
}

.corner-label.active {
  background: #4ecca3;
  color: #1a1a2e;
  font-weight: bold;
}

.court-selection-container {
  position: relative;
  width: 100%;
  aspect-ratio: 16/9;
  background: #0f0f1a;
  border-radius: 12px;
  overflow: hidden;
  margin-bottom: 1rem;
}

.court-preview-video {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.court-selection-canvas {
  position: absolute;
  inset: 0;
  cursor: crosshair;
}

.camera-placeholder {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.7);
  color: #888;
}

.corner-indicator {
  position: absolute;
  top: 1rem;
  left: 1rem;
  padding: 0.5rem 1rem;
  background: rgba(78, 204, 163, 0.9);
  color: #1a1a2e;
  border-radius: 6px;
  font-weight: bold;
  font-size: 0.9rem;
}

.court-actions {
  display: flex;
  gap: 1rem;
  margin-bottom: 1rem;
}

.btn-secondary {
  padding: 0.5rem 1rem;
  background: #16213e;
  border: 1px solid #3a3a5a;
  border-radius: 6px;
  color: #888;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-secondary:hover:not(:disabled) {
  border-color: #4ecca3;
  color: #4ecca3;
}

.btn-secondary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.court-status {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.5rem;
  margin-bottom: 1rem;
  padding: 1rem;
  background: #0f0f1a;
  border-radius: 8px;
}

.corner-status {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.corner-name {
  color: #888;
  font-size: 0.85rem;
}

.corner-coords {
  color: #4ecca3;
  font-family: monospace;
  font-size: 0.85rem;
}

.corner-pending {
  color: #555;
  font-size: 0.85rem;
  font-style: italic;
}

/* Stream Controls */
.stream-controls-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 1rem;
  background: #16213e;
  border-radius: 8px;
  margin-bottom: 1rem;
}

.session-info-bar {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.info-label {
  color: #888;
  font-size: 0.85rem;
}

.frames-label {
  color: #4ecca3;
  font-size: 0.85rem;
  font-family: monospace;
}

.controls-right {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.toggle-control {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
}

.toggle-control input {
  display: none;
}

.toggle-slider {
  width: 36px;
  height: 20px;
  background: #3a3a5a;
  border-radius: 20px;
  position: relative;
  transition: background 0.2s;
}

.toggle-slider::before {
  content: '';
  position: absolute;
  width: 16px;
  height: 16px;
  background: white;
  border-radius: 50%;
  top: 2px;
  left: 2px;
  transition: transform 0.2s;
}

.toggle-control input:checked + .toggle-slider {
  background: #4ecca3;
}

.toggle-control input:checked + .toggle-slider::before {
  transform: translateX(16px);
}

.toggle-text {
  color: #888;
  font-size: 0.85rem;
}

.recording-status {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
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
}

.recording-info {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 1rem;
  background: rgba(78, 204, 163, 0.1);
  border-radius: 8px;
  margin-top: 0.5rem;
}

.recording-info .info-icon {
  width: 20px;
  height: 20px;
  color: #4ecca3;
  flex-shrink: 0;
}

.recording-info span {
  color: #888;
  font-size: 0.85rem;
}

.btn-record .btn-icon {
  width: 18px;
  height: 18px;
  margin-right: 0.5rem;
}

.btn-record {
  display: flex;
  align-items: center;
  justify-content: center;
}

/* Loading and Resume Sections */
.loading-section .section-card,
.resume-section .section-card {
  text-align: center;
}

.active-session-info {
  background: #0f0f1a;
  padding: 1rem;
  border-radius: 8px;
  margin: 1rem 0;
  text-align: left;
}

.active-session-info p {
  margin: 0.5rem 0;
  color: #ccc;
}

.active-session-info strong {
  color: #4ecca3;
}

.resume-actions {
  display: flex;
  gap: 1rem;
  justify-content: center;
  margin-top: 1rem;
}

.btn-fullframe {
  background: #4ecca3 !important;
  color: #1a1a2e !important;
  border-color: #4ecca3 !important;
}

.btn-fullframe:hover {
  background: #3db892 !important;
}
</style>
