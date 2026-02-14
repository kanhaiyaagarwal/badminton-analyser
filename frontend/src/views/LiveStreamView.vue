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

        <!-- Mode Selector -->
        <div class="mode-selector">
          <label class="mode-label">Analysis Mode</label>
          <div class="mode-cards">
            <div
              class="mode-card"
              :class="{ active: streamMode === 'basic' }"
              @click="streamMode = 'basic'"
            >
              <div class="mode-card-header">
                <span class="mode-icon">&#9889;</span>
                <h4>Real-Time</h4>
              </div>
              <p>Instant skeleton overlay, shot detection, movement heatmap. Results per frame. Recording is optional.</p>
            </div>
            <div
              class="mode-card"
              :class="{ active: streamMode === 'advanced' }"
              @click="streamMode = 'advanced'"
            >
              <div class="mode-card-header">
                <span class="mode-icon">&#127919;</span>
                <h4>Advanced</h4>
              </div>
              <p>Shuttle tracking + accurate shot classification. Results update periodically. Always records.</p>
            </div>
          </div>
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

        <!-- Camera Controls -->
        <div class="camera-controls">
          <div class="camera-select-row">
            <label>Camera:</label>
            <select v-model="selectedCourtCamera" @change="switchCourtCamera" :disabled="availableCameras.length === 0">
              <option value="">Select camera...</option>
              <option v-for="cam in availableCameras" :key="cam.deviceId" :value="cam.deviceId">
                {{ cam.label || `Camera ${availableCameras.indexOf(cam) + 1}` }}
              </option>
            </select>
          </div>
          <div class="zoom-control-row" v-if="zoomSupported">
            <label>Zoom: {{ currentZoom.toFixed(1) }}x</label>
            <input
              type="range"
              :min="zoomRange.min"
              :max="zoomRange.max"
              :step="0.1"
              v-model.number="currentZoom"
              @input="applyZoom"
              class="zoom-slider"
            />
          </div>
        </div>

        <!-- Court Selection Video Preview -->
        <div
          class="court-selection-container"
          ref="courtSelectionContainer"
          @touchstart="handleTouchStart"
          @touchmove="handleTouchMove"
          @touchend="handleTouchEnd"
        >
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

    <!-- Step 3: Live Streaming (Basic Mode) -->
    <div v-else-if="step === 'streaming' && streamMode === 'basic'" class="streaming-section">
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

          <!-- Action Buttons -->
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

          <div v-if="hasRecording" class="recording-info">
            <svg class="info-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"/>
            </svg>
            <span>Recording saved - will be available for download when session ends</span>
          </div>

          <!-- Stream Controls Bar -->
          <div class="stream-controls-bar">
            <div class="session-info-bar">
              <span class="info-label">Session #{{ sessionId }}</span>
              <span class="frames-label">{{ liveStats.framesProcessed }} frames</span>
            </div>

            <div class="controls-right">
              <label class="toggle-control">
                <input type="checkbox" v-model="showAnnotations" />
                <span class="toggle-slider"></span>
                <span class="toggle-text">Skeleton</span>
              </label>

              <div v-if="isRecording" class="recording-status">
                <span class="recording-dot"></span>
                <span class="recording-time">{{ formatRecordingTime(recordingDuration) }}</span>
              </div>
            </div>
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

    <!-- Step 3: Live Streaming (Advanced Mode) -->
    <div v-else-if="step === 'streaming' && streamMode === 'advanced'" class="streaming-section">
      <div class="advanced-layout">
        <div class="advanced-main">
          <CameraCapture
            ref="streamCamera"
            :court-overlay="courtBoundary"
            :show-annotations="false"
            :auto-start="true"
            @frame="handleFrame"
            @stream-start="handleStreamStart"
            @stream-stop="handleStreamStop"
            @error="handleError"
          />

          <!-- Action Button -->
          <div class="stream-actions">
            <button @click="endSession" class="btn-end" :disabled="finalizingInProgress">
              {{ finalizingInProgress ? 'Finalizing...' : 'End Session' }}
            </button>
          </div>

          <!-- Advanced Controls Bar -->
          <div class="stream-controls-bar">
            <div class="session-info-bar">
              <span class="info-label">Session #{{ sessionId }}</span>
              <span class="mode-badge">ADVANCED</span>
              <span class="recording-dot"></span>
              <span class="recording-time">Recording</span>
            </div>
            <div class="controls-right">
              <span class="frames-label">{{ advancedStatus.framesBuffered }} frames buffered</span>
            </div>
          </div>

          <!-- Seek Bar -->
          <div class="seek-bar-container">
            <div class="seek-bar">
              <div class="seek-processed" :style="{ width: processedPct + '%' }"></div>
              <div class="seek-buffered" :style="{ width: bufferedPct + '%' }"></div>
            </div>
            <div class="seek-labels">
              <span>{{ formatTime(advancedStatus.secondsProcessed) }} processed</span>
              <span>{{ formatTime(advancedStatus.secondsBuffered) }} buffered</span>
            </div>
          </div>
        </div>

        <!-- Advanced Sidebar: accumulated results -->
        <div class="advanced-sidebar">
          <div class="advanced-results-card">
            <h3>Analysis Results</h3>
            <p v-if="!advancedResults.summary || !advancedResults.summary.total_shots" class="hint">
              Results will appear after the first processing cycle...
            </p>
            <div v-else class="advanced-stats">
              <div class="stat-row">
                <span class="stat-label">Shots</span>
                <span class="stat-value">{{ advancedResults.summary.total_shots || 0 }}</span>
              </div>
              <div class="stat-row">
                <span class="stat-label">Rallies</span>
                <span class="stat-value">{{ advancedResults.summary.total_rallies || 0 }}</span>
              </div>
              <div class="stat-row">
                <span class="stat-label">Shuttle Hits</span>
                <span class="stat-value">{{ advancedResults.summary.shuttle_hits || advancedResults.shuttle_hits?.length || 0 }}</span>
              </div>
            </div>

            <div v-if="advancedResults.shot_distribution && Object.keys(advancedResults.shot_distribution).length" class="shot-distribution">
              <h4>Shot Distribution</h4>
              <div v-for="(count, type) in advancedResults.shot_distribution" :key="type" class="dist-row">
                <span class="dist-type">{{ formatShotType(type) }}</span>
                <div class="dist-bar-bg">
                  <div class="dist-bar" :style="{ width: getDistPct(count) + '%' }"></div>
                </div>
                <span class="dist-count">{{ count }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Session Ended / Results -->
    <div v-else-if="step === 'ended'" class="results-section">
      <div class="section-card">
        <router-link to="/hub" class="back-home-link">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="15 18 9 12 15 6"/>
          </svg>
          Back to Home
        </router-link>
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

          <div class="shot-breakdown" v-if="finalReport.shot_distribution && Object.keys(finalReport.shot_distribution).length > 0">
            <h3>Shot Distribution</h3>
            <div v-for="(count, type) in finalReport.shot_distribution" :key="type" class="shot-row">
              <span class="shot-type">{{ formatShotType(type) }}</span>
              <span class="shot-count">{{ count }}</span>
            </div>
          </div>
          <p v-else class="no-shots-msg">No shots were detected during this session.</p>
        </div>

        <!-- Recording Download -->
        <div v-if="hasRecording" class="recording-download">
          <p class="recording-desc">Your session recording is ready for download.</p>
          <button @click="downloadRecording" class="btn-download" :disabled="downloading">
            <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/>
            </svg>
            {{ downloading ? 'Downloading...' : 'Download Recording' }}
          </button>
        </div>

        <div class="ended-actions">
          <router-link :to="`/stream-results/${sessionId}`" class="btn-primary">
            View Full Results
          </router-link>
          <button @click="startNewSession" class="btn-secondary">
            Start New Session
          </button>
        </div>
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

// Camera selection and zoom
const availableCameras = ref([])
const selectedCourtCamera = ref('')
const zoomSupported = ref(false)
const zoomRange = ref({ min: 1, max: 1 })
const currentZoom = ref(1)

// Pinch-to-zoom state
let initialPinchDistance = 0
let initialZoom = 1

const isRecording = ref(false)
const hasRecording = ref(false)
const recordingDuration = ref(0)
const downloading = ref(false)
const showAnnotations = ref(true)
const finalReport = ref(null)
let recordingTimer = null

// Session creation options
const streamMode = ref('basic')
const enableTuningData = ref(false)
const enableShuttleTracking = ref(false)

// Advanced mode state
const advancedStatus = ref({
  framesBuffered: 0,
  secondsBuffered: 0,
  framesProcessed: 0,
  secondsProcessed: 0,
  isProcessing: false,
})
const advancedResults = ref({
  shots: [],
  rallies: [],
  shot_distribution: {},
  shuttle_hits: [],
  summary: {},
})
const finalizingInProgress = ref(false)

// Post-analysis state
const analysisAvailable = ref(false)
const analysisStatus = ref('none')
const analysisProgress = ref(0)
const analysisRunning = ref(false)
const postAnalysisResults = ref(null)
const hasFrameData = ref(false)
let analysisPoller = null

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
  stopAnalysisPoller()
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
    // First, enumerate available cameras
    await enumerateCameras()

    // On mobile, explicitly request back camera
    const isMobile = /Android|iPhone|iPad|iPod/i.test(navigator.userAgent)
    const videoConstraints = {
      width: { ideal: 1920 },
      height: { ideal: 1080 }
    }

    // If a specific camera is selected, use it
    if (selectedCourtCamera.value) {
      videoConstraints.deviceId = { exact: selectedCourtCamera.value }
    } else if (isMobile) {
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
      console.log('Exact constraint failed, trying without:', e.message)
      courtMediaStream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 1920 },
          height: { ideal: 1080 },
          facingMode: 'environment'
        }
      })
    }

    if (courtPreviewVideo.value) {
      courtPreviewVideo.value.srcObject = courtMediaStream
      await courtPreviewVideo.value.play()
    }

    // Check zoom capabilities
    checkZoomCapabilities()

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

async function enumerateCameras() {
  try {
    // Request permission first to get camera labels
    await navigator.mediaDevices.getUserMedia({ video: true }).then(stream => {
      stream.getTracks().forEach(track => track.stop())
    })

    const devices = await navigator.mediaDevices.enumerateDevices()
    availableCameras.value = devices.filter(d => d.kind === 'videoinput')
    console.log('Available cameras:', availableCameras.value.map(c => c.label))

    // Auto-select back/environment camera if not already selected
    if (!selectedCourtCamera.value && availableCameras.value.length > 0) {
      // Look for back camera (various naming conventions)
      const backCamera = availableCameras.value.find(cam => {
        const label = cam.label.toLowerCase()
        return label.includes('back') ||
               label.includes('rear') ||
               label.includes('environment') ||
               label.includes('wide') ||
               label.includes('0, facing back')
      })

      if (backCamera) {
        selectedCourtCamera.value = backCamera.deviceId
      } else if (availableCameras.value.length > 1) {
        // On mobile, last camera is often the back camera
        selectedCourtCamera.value = availableCameras.value[availableCameras.value.length - 1].deviceId
      } else {
        selectedCourtCamera.value = availableCameras.value[0].deviceId
      }
    }
  } catch (e) {
    console.error('Failed to enumerate cameras:', e)
  }
}

async function switchCourtCamera() {
  if (!selectedCourtCamera.value) return

  // Stop current stream
  if (courtMediaStream) {
    courtMediaStream.getTracks().forEach(track => track.stop())
  }

  courtCameraReady.value = false
  zoomSupported.value = false
  currentZoom.value = 1

  try {
    courtMediaStream = await navigator.mediaDevices.getUserMedia({
      video: {
        deviceId: { exact: selectedCourtCamera.value },
        width: { ideal: 1920 },
        height: { ideal: 1080 }
      }
    })

    if (courtPreviewVideo.value) {
      courtPreviewVideo.value.srcObject = courtMediaStream
      await courtPreviewVideo.value.play()
    }

    checkZoomCapabilities()
    courtCameraReady.value = true

    setTimeout(() => drawCourtOverlay(), 100)
  } catch (e) {
    console.error('Failed to switch camera:', e)
    courtCameraError.value = 'Failed to switch camera: ' + e.message
  }
}

function checkZoomCapabilities() {
  if (!courtMediaStream) return

  const videoTrack = courtMediaStream.getVideoTracks()[0]
  if (!videoTrack) return

  try {
    const capabilities = videoTrack.getCapabilities()
    if (capabilities.zoom) {
      zoomSupported.value = true
      zoomRange.value = {
        min: capabilities.zoom.min,
        max: capabilities.zoom.max
      }
      // Get current zoom level
      const settings = videoTrack.getSettings()
      currentZoom.value = settings.zoom || 1
      console.log('Zoom supported:', zoomRange.value, 'current:', currentZoom.value)
    } else {
      zoomSupported.value = false
      console.log('Zoom not supported by this camera')
    }
  } catch (e) {
    console.log('Failed to check zoom capabilities:', e)
    zoomSupported.value = false
  }
}

async function applyZoom() {
  if (!courtMediaStream || !zoomSupported.value) return

  const videoTrack = courtMediaStream.getVideoTracks()[0]
  if (!videoTrack) return

  try {
    await videoTrack.applyConstraints({
      advanced: [{ zoom: currentZoom.value }]
    })
  } catch (e) {
    console.error('Failed to apply zoom:', e)
  }
}

// Pinch-to-zoom handlers
function handleTouchStart(event) {
  if (event.touches.length === 2) {
    initialPinchDistance = getPinchDistance(event.touches)
    initialZoom = currentZoom.value
  }
}

function handleTouchMove(event) {
  if (event.touches.length === 2 && zoomSupported.value) {
    event.preventDefault()
    const currentDistance = getPinchDistance(event.touches)
    const scale = currentDistance / initialPinchDistance

    // Calculate new zoom level
    let newZoom = initialZoom * scale
    newZoom = Math.max(zoomRange.value.min, Math.min(zoomRange.value.max, newZoom))
    currentZoom.value = newZoom
    applyZoom()
  }
}

function handleTouchEnd(event) {
  initialPinchDistance = 0
}

function getPinchDistance(touches) {
  const dx = touches[0].clientX - touches[1].clientX
  const dy = touches[0].clientY - touches[1].clientY
  return Math.sqrt(dx * dx + dy * dy)
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
    const isAdvanced = streamMode.value === 'advanced'
    const response = await api.post('/api/v1/stream/create', {
      title: sessionTitle.value || (isAdvanced ? 'Advanced Session' : 'Live Session'),
      frame_rate: 30,
      quality: 'medium',
      stream_mode: streamMode.value,
      enable_tuning_data: isAdvanced ? true : false,
      enable_shuttle_tracking: isAdvanced
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
  } else if (data.type === 'frame_buffered') {
    // Advanced mode: update buffer/processing status
    advancedStatus.value.framesBuffered = data.frames_buffered || 0
    advancedStatus.value.secondsBuffered = data.seconds_buffered || 0
    advancedStatus.value.framesProcessed = data.frames_processed || 0
    advancedStatus.value.secondsProcessed = data.seconds_processed || 0
    advancedStatus.value.isProcessing = data.is_processing || false
  } else if (data.type === 'chunk_results') {
    // Advanced mode: updated classification results
    advancedStatus.value.secondsProcessed = data.seconds_processed || 0
    advancedStatus.value.secondsBuffered = data.seconds_buffered || 0
    advancedStatus.value.framesProcessed = data.frames_processed || 0
    advancedResults.value = {
      shots: data.shots || [],
      rallies: data.rallies || [],
      shot_distribution: data.shot_distribution || {},
      shuttle_hits: data.shuttle_hits || [],
      summary: data.summary || {},
    }
  } else if (data.type === 'finalizing') {
    finalizingInProgress.value = true
    if (data.report) {
      finalReport.value = data.report
    }
  } else if (data.type === 'stream_ended') {
    finalizingInProgress.value = false
    finalReport.value = data.report
    analysisAvailable.value = !!data.analysis_available
    if (data.analysis_status) {
      // Advanced mode sends explicit status (complete/failed)
      analysisStatus.value = data.analysis_status
      if (data.analysis_status === 'complete' && data.report) {
        postAnalysisResults.value = {
          shots: data.report.total_shots,
          distribution: data.report.shot_distribution,
          rallies: data.report.total_rallies,
          shuttle_hits: data.report.shuttle_hits,
        }
        hasFrameData.value = !!data.report.frame_data_path
      }
    } else if (data.analysis_available) {
      // Basic mode: analysis data available but not yet run
      analysisStatus.value = 'pending'
    }
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
    if (streamMode.value === 'advanced') {
      // Advanced mode: only send WebSocket message.
      // The WebSocket handler runs finalize and sends stream_ended when done.
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'end_stream' }))
      }
      // Don't close WS or navigate — wait for 'finalizing' and 'stream_ended' messages
      return
    }

    // Basic mode: send WS message + call REST API
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'end_stream' }))
    }

    const response = await api.post(`/api/v1/stream/${sessionId.value}/end`)
    finalReport.value = response.data.report
    if (response.data.analysis_available) {
      analysisAvailable.value = true
      analysisStatus.value = 'pending'
    }

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
  analysisAvailable.value = false
  analysisStatus.value = 'none'
  analysisProgress.value = 0
  analysisRunning.value = false
  postAnalysisResults.value = null
  hasFrameData.value = false
  finalizingInProgress.value = false
  advancedStatus.value = { framesBuffered: 0, secondsBuffered: 0, framesProcessed: 0, secondsProcessed: 0, isProcessing: false }
  advancedResults.value = { shots: [], rallies: [], shot_distribution: {}, shuttle_hits: [], summary: {} }
  stopRecordingTimer()
  stopAnalysisPoller()
  step.value = 'setup'
}

// Advanced mode computed
const processedPct = computed(() => {
  const buffered = advancedStatus.value.secondsBuffered
  if (buffered <= 0) return 0
  return Math.min(100, (advancedStatus.value.secondsProcessed / buffered) * 100)
})

const bufferedPct = computed(() => 100) // Buffered is always the full bar

function formatTime(seconds) {
  if (!seconds || seconds <= 0) return '0:00'
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  return `${m}:${s.toString().padStart(2, '0')}`
}

function getDistPct(count) {
  const dist = advancedResults.value.shot_distribution || {}
  const max = Math.max(1, ...Object.values(dist))
  return (count / max) * 100
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

async function triggerPostAnalysis() {
  analysisRunning.value = true
  try {
    await api.post(`/api/v1/stream/${sessionId.value}/analyze`)
    analysisStatus.value = 'running'
    analysisProgress.value = 0
    startAnalysisPoller()
  } catch (e) {
    error.value = e.response?.data?.detail || 'Failed to start analysis'
    analysisRunning.value = false
  }
}

function startAnalysisPoller() {
  stopAnalysisPoller()
  analysisPoller = setInterval(async () => {
    try {
      const response = await api.get(`/api/v1/stream/${sessionId.value}/analysis-status`)
      const data = response.data
      analysisStatus.value = data.analysis_status
      analysisProgress.value = data.analysis_progress || 0

      if (data.analysis_status === 'complete') {
        postAnalysisResults.value = data.post_analysis
        hasFrameData.value = data.has_frame_data
        analysisRunning.value = false
        stopAnalysisPoller()
      } else if (data.analysis_status === 'failed') {
        analysisRunning.value = false
        stopAnalysisPoller()
      }
    } catch (e) {
      console.error('Failed to poll analysis status:', e)
    }
  }, 2000)
}

function stopAnalysisPoller() {
  if (analysisPoller) {
    clearInterval(analysisPoller)
    analysisPoller = null
  }
}

async function retryPostAnalysis() {
  analysisStatus.value = 'pending'
  await triggerPostAnalysis()
}

async function downloadAnnotatedVideo() {
  downloading.value = true
  try {
    const response = await api.get(`/api/v1/stream/${sessionId.value}/annotated-video`, {
      responseType: 'blob'
    })
    const blob = new Blob([response.data], { type: 'video/mp4' })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `annotated_stream_${sessionId.value}.mp4`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
  } catch (err) {
    error.value = err.response?.data?.detail || 'Failed to download annotated video'
  } finally {
    downloading.value = false
  }
}

async function downloadRecording() {
  downloading.value = true
  try {
    const response = await api.get(`/api/v1/stream/${sessionId.value}/recording`, {
      responseType: 'blob'
    })
    const blob = new Blob([response.data], { type: 'video/mp4' })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `stream_recording_${sessionId.value}.mp4`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
  } catch (err) {
    error.value = err.response?.data?.detail || 'Failed to download recording'
  } finally {
    downloading.value = false
  }
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
  color: var(--text-muted);
  text-decoration: none;
  font-size: 0.9rem;
}

.back-link:hover {
  color: var(--color-primary);
}

h1 {
  color: var(--color-primary);
  margin: 0.5rem 0 0 0;
}

.section-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 1.5rem;
  box-shadow: var(--shadow-md);
}

.section-card h2 {
  color: var(--text-primary);
  margin: 0 0 1rem 0;
}

.hint {
  color: var(--text-muted);
  margin-bottom: 1rem;
}

.form-group {
  margin-bottom: 1rem;
}

.form-group label {
  display: block;
  color: var(--text-muted);
  margin-bottom: 0.5rem;
}

.form-group input {
  width: 100%;
  padding: 0.75rem;
  background: var(--bg-input);
  border: 1px solid var(--border-input);
  border-radius: var(--radius-md);
  color: var(--text-primary);
  font-size: 1rem;
}

.btn-primary {
  display: inline-block;
  padding: 0.75rem 1.5rem;
  background: var(--gradient-primary);
  color: var(--text-on-primary);
  border: none;
  border-radius: var(--radius-md);
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-primary:hover:not(:disabled) {
  background: var(--color-primary-hover);
}

.btn-primary:disabled {
  background: var(--text-muted);
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
  color: var(--text-muted);
  font-size: 0.85rem;
}

.coord-input input {
  padding: 0.5rem;
  background: var(--bg-input);
  border: 1px solid var(--border-input);
  border-radius: var(--radius-sm);
  color: var(--text-primary);
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
  background: var(--bg-card);
  border: 2px solid var(--color-destructive);
  border-radius: var(--radius-md);
  color: var(--color-destructive);
  font-weight: bold;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-record:hover {
  background: var(--color-destructive-light);
}

.btn-record.recording {
  background: var(--color-destructive);
  color: white;
  animation: pulse-record 1s infinite;
}

@keyframes pulse-record {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.8; }
}

.btn-end {
  padding: 0.75rem 1.5rem;
  background: var(--color-destructive-light);
  border: none;
  border-radius: var(--radius-md);
  color: var(--color-destructive);
  font-weight: bold;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-end:hover {
  background: var(--color-destructive);
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
  color: var(--color-primary);
}

.stat .label {
  color: var(--text-muted);
  font-size: 0.9rem;
}

.shot-breakdown {
  text-align: left;
  max-width: 300px;
  margin: 0 auto;
}

.shot-breakdown h3 {
  color: var(--text-primary);
  font-size: 1rem;
  margin-bottom: 0.75rem;
}

.shot-row {
  display: flex;
  justify-content: space-between;
  padding: 0.5rem 0;
  border-bottom: 1px solid var(--border-input);
}

.shot-type {
  color: var(--text-muted);
}

.shot-count {
  color: var(--color-primary);
  font-weight: bold;
}

.error-toast {
  position: fixed;
  bottom: 2rem;
  left: 50%;
  transform: translateX(-50%);
  padding: 1rem 1.5rem;
  background: var(--color-destructive);
  color: white;
  border-radius: var(--radius-md);
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
  color: var(--text-muted);
  transition: all 0.2s;
}

.corner-label.active {
  background: var(--color-primary);
  color: var(--text-on-primary);
  font-weight: bold;
}

.camera-controls {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  margin-bottom: 1rem;
  padding: 1rem;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
}

.camera-select-row,
.zoom-control-row {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.camera-select-row label,
.zoom-control-row label {
  min-width: 80px;
  color: var(--text-secondary);
  font-size: 0.9rem;
}

.camera-select-row select {
  flex: 1;
  padding: 0.5rem;
  background: var(--bg-input);
  border: 1px solid var(--border-input);
  border-radius: var(--radius-sm);
  color: var(--text-primary);
  font-size: 0.9rem;
}

.camera-select-row select:focus {
  outline: none;
  border-color: var(--color-primary);
}

.zoom-slider {
  flex: 1;
  -webkit-appearance: none;
  appearance: none;
  height: 6px;
  background: var(--border-input);
  border-radius: 3px;
  outline: none;
}

.zoom-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 20px;
  height: 20px;
  background: var(--color-primary);
  border-radius: 50%;
  cursor: pointer;
}

.zoom-slider::-moz-range-thumb {
  width: 20px;
  height: 20px;
  background: var(--color-primary);
  border-radius: 50%;
  cursor: pointer;
  border: none;
}

.court-selection-container {
  position: relative;
  width: 100%;
  aspect-ratio: 16/9;
  background: #0f0f1a;
  border-radius: var(--radius-lg);
  overflow: hidden;
  margin-bottom: 1rem;
  touch-action: none; /* Enable custom touch handling for pinch-to-zoom */
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
  color: var(--text-muted);
}

.corner-indicator {
  position: absolute;
  top: 1rem;
  left: 1rem;
  padding: 0.5rem 1rem;
  background: var(--color-primary);
  color: var(--text-on-primary);
  border-radius: var(--radius-sm);
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
  background: var(--bg-card);
  border: 1px solid var(--border-input);
  border-radius: var(--radius-sm);
  color: var(--text-muted);
  cursor: pointer;
  transition: all 0.2s;
}

.btn-secondary:hover:not(:disabled) {
  border-color: var(--color-primary);
  color: var(--color-primary);
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
  background: var(--bg-input);
  border-radius: var(--radius-md);
}

.corner-status {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.corner-name {
  color: var(--text-muted);
  font-size: 0.85rem;
}

.corner-coords {
  color: var(--color-primary);
  font-family: monospace;
  font-size: 0.85rem;
}

.corner-pending {
  color: var(--text-muted);
  font-size: 0.85rem;
  font-style: italic;
}

/* Stream Controls */
.stream-controls-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 1rem;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  margin-bottom: 1rem;
  box-shadow: var(--shadow-md);
}

.session-info-bar {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.info-label {
  color: var(--text-muted);
  font-size: 0.85rem;
}

.frames-label {
  color: var(--color-primary);
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
  background: var(--border-input);
  border-radius: var(--radius-full);
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
  background: var(--color-primary);
}

.toggle-control input:checked + .toggle-slider::before {
  transform: translateX(16px);
}

.toggle-text {
  color: var(--text-muted);
  font-size: 0.85rem;
}

.recording-status {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  background: var(--color-destructive-light);
  border-radius: var(--radius-sm);
}

.recording-dot {
  width: 10px;
  height: 10px;
  background: var(--color-destructive);
  border-radius: 50%;
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
}

.recording-info {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 1rem;
  background: var(--color-primary-light);
  border-radius: var(--radius-md);
  margin-top: 0.5rem;
}

.recording-info .info-icon {
  width: 20px;
  height: 20px;
  color: var(--color-primary);
  flex-shrink: 0;
}

.recording-info span {
  color: var(--text-muted);
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

/* Back Home Link */
.back-home-link {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  color: var(--text-muted);
  text-decoration: none;
  font-size: 0.9rem;
  margin-bottom: 1rem;
  transition: color 0.2s;
}

.back-home-link:hover {
  color: var(--color-primary);
}

/* Loading and Resume Sections */
.loading-section .section-card,
.resume-section .section-card {
  text-align: center;
}

.active-session-info {
  background: var(--bg-input);
  padding: 1rem;
  border-radius: var(--radius-md);
  margin: 1rem 0;
  text-align: left;
}

.active-session-info p {
  margin: 0.5rem 0;
  color: var(--text-secondary);
}

.active-session-info strong {
  color: var(--color-primary);
}

.resume-actions {
  display: flex;
  gap: 1rem;
  justify-content: center;
  margin-top: 1rem;
}

.btn-fullframe {
  background: var(--color-primary) !important;
  color: var(--text-on-primary) !important;
  border-color: var(--color-primary) !important;
}

.btn-fullframe:hover {
  background: var(--color-primary-hover) !important;
}

/* Ended screen styles */
.no-shots-msg {
  color: var(--text-muted);
  text-align: center;
  padding: 1rem 0;
}

.recording-download {
  margin: 1.5rem 0;
  padding: 1.5rem;
  background: var(--bg-input);
  border-radius: var(--radius-md);
  text-align: center;
}

.recording-download .recording-desc {
  color: var(--text-muted);
  margin-bottom: 1rem;
}

.btn-download {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  background: var(--gradient-primary);
  color: var(--text-on-primary);
  padding: 0.75rem 1.5rem;
  border-radius: var(--radius-md);
  font-weight: 600;
  border: none;
  cursor: pointer;
  font-size: 1rem;
  transition: background 0.2s;
}

.btn-download:hover:not(:disabled) {
  background: var(--color-primary-hover);
}

.btn-download:disabled {
  background: var(--text-muted);
  cursor: not-allowed;
}

.btn-download .btn-icon {
  width: 20px;
  height: 20px;
}

.ended-actions {
  display: flex;
  gap: 1rem;
  justify-content: center;
  margin-top: 1.5rem;
}

.ended-actions .btn-primary {
  text-decoration: none;
}

/* Toggle options for session creation */
.toggle-options {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  margin-bottom: 1.5rem;
  padding: 1rem;
  background: var(--bg-input);
  border-radius: var(--radius-md);
}

.toggle-option {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  cursor: pointer;
}

.toggle-option input {
  display: none;
}

.toggle-slider-sm {
  width: 36px;
  height: 20px;
  background: var(--border-input);
  border-radius: var(--radius-full);
  position: relative;
  transition: background 0.2s;
  flex-shrink: 0;
}

.toggle-slider-sm::before {
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

.toggle-option input:checked + .toggle-slider-sm {
  background: var(--color-primary);
}

.toggle-option input:checked + .toggle-slider-sm::before {
  transform: translateX(16px);
}

.toggle-option-text {
  display: flex;
  flex-direction: column;
}

.toggle-option-label {
  color: var(--text-primary);
  font-size: 0.9rem;
  font-weight: 500;
}

.toggle-option-desc {
  color: var(--text-muted);
  font-size: 0.8rem;
}

/* Post-analysis styles */
.post-analysis-section {
  margin: 1.5rem 0;
  padding: 1.5rem;
  background: var(--bg-input);
  border-radius: var(--radius-md);
  text-align: center;
}

.post-analysis-section h3 {
  color: var(--color-primary);
  margin: 0 0 1rem 0;
  font-size: 1.1rem;
}

.analysis-desc {
  color: var(--text-muted);
  margin-bottom: 1rem;
  font-size: 0.9rem;
}

.analysis-desc.error-text {
  color: var(--color-destructive);
}

.progress-bar-container {
  width: 100%;
  height: 8px;
  background: var(--border-input);
  border-radius: 4px;
  margin: 1rem 0 0.5rem;
  overflow: hidden;
}

.progress-bar {
  height: 100%;
  background: var(--color-primary);
  border-radius: 4px;
  transition: width 0.3s ease;
}

.progress-text {
  color: var(--color-primary);
  font-family: monospace;
  font-size: 0.85rem;
}

.post-analysis-stats {
  display: flex;
  justify-content: center;
  gap: 2rem;
  margin-bottom: 1rem;
}

.analysis-actions {
  display: flex;
  gap: 1rem;
  justify-content: center;
  margin-top: 1rem;
}

.analysis-actions .btn-secondary {
  text-decoration: none;
  display: inline-flex;
  align-items: center;
}

/* Mode Selector */
.mode-selector {
  margin-bottom: 1.5rem;
}

.mode-label {
  display: block;
  color: var(--text-muted);
  margin-bottom: 0.75rem;
  font-size: 0.9rem;
}

.mode-cards {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.75rem;
}

.mode-card {
  background: var(--bg-input);
  border: 2px solid var(--border-input);
  border-radius: var(--radius-md);
  padding: 1rem;
  cursor: pointer;
  transition: border-color 0.2s, background 0.2s;
}

.mode-card:hover {
  border-color: var(--color-primary);
}

.mode-card.active {
  border-color: var(--color-primary);
  background: var(--color-primary-light);
}

.mode-card-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.mode-card-header h4 {
  margin: 0;
  color: var(--text-primary);
  font-size: 1rem;
}

.mode-icon {
  font-size: 1.2rem;
}

.mode-card p {
  color: var(--text-muted);
  font-size: 0.8rem;
  margin: 0;
  line-height: 1.4;
}

/* Advanced Layout */
.advanced-layout {
  display: grid;
  grid-template-columns: 1fr 320px;
  gap: 1rem;
}

@media (max-width: 900px) {
  .advanced-layout {
    grid-template-columns: 1fr;
  }
}

.advanced-main {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.mode-badge {
  background: var(--color-primary);
  color: var(--text-on-primary);
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 0.7rem;
  font-weight: bold;
  letter-spacing: 0.05em;
}

/* Seek Bar */
.seek-bar-container {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 0.75rem 1rem;
  box-shadow: var(--shadow-md);
}

.seek-bar {
  position: relative;
  height: 10px;
  background: var(--border-input);
  border-radius: 5px;
  overflow: hidden;
}

.seek-buffered {
  position: absolute;
  top: 0;
  left: 0;
  height: 100%;
  background: var(--border-color);
  border-radius: 5px;
}

.seek-processed {
  position: absolute;
  top: 0;
  left: 0;
  height: 100%;
  background: var(--color-primary);
  border-radius: 5px;
  z-index: 1;
  transition: width 0.5s ease;
}

.seek-labels {
  display: flex;
  justify-content: space-between;
  margin-top: 0.5rem;
  font-size: 0.8rem;
  color: var(--text-muted);
}

.seek-labels span:first-child {
  color: var(--color-primary);
}

/* Advanced Sidebar */
.advanced-sidebar {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.advanced-results-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 1.25rem;
  box-shadow: var(--shadow-md);
}

.advanced-results-card h3 {
  color: var(--color-primary);
  margin: 0 0 1rem 0;
  font-size: 1rem;
}

.advanced-stats {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.stat-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem 0;
  border-bottom: 1px solid var(--border-color);
}

.stat-label {
  color: var(--text-muted);
  font-size: 0.9rem;
}

.stat-value {
  color: var(--text-primary);
  font-size: 1.1rem;
  font-weight: bold;
  font-family: monospace;
}

.shot-distribution {
  margin-top: 0.5rem;
}

.shot-distribution h4 {
  color: var(--text-secondary);
  margin: 0 0 0.5rem 0;
  font-size: 0.85rem;
}

.dist-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.4rem;
}

.dist-type {
  color: var(--text-secondary);
  font-size: 0.8rem;
  width: 70px;
  flex-shrink: 0;
}

.dist-bar-bg {
  flex: 1;
  height: 6px;
  background: var(--border-input);
  border-radius: 3px;
  overflow: hidden;
}

.dist-bar {
  height: 100%;
  background: var(--color-primary);
  border-radius: 3px;
  transition: width 0.3s ease;
}

.dist-count {
  color: var(--text-secondary);
  font-size: 0.8rem;
  font-family: monospace;
  width: 24px;
  text-align: right;
}

/* ---- Mobile Responsive ---- */
@media (max-width: 640px) {
  .live-stream-view {
    padding: 0.75rem;
  }

  .header {
    margin-bottom: 1rem;
  }

  h1 {
    font-size: 1.3rem;
  }

  .section-card {
    padding: 1rem;
  }

  /* Mode selector */
  .mode-cards {
    grid-template-columns: 1fr;
  }

  .mode-card {
    padding: 0.75rem;
  }

  /* Court section */
  .camera-controls {
    padding: 0.75rem;
  }

  .camera-select-row,
  .zoom-control-row {
    flex-direction: column;
    align-items: stretch;
    gap: 0.5rem;
  }

  .camera-select-row label,
  .zoom-control-row label {
    min-width: unset;
  }

  .court-actions {
    flex-wrap: wrap;
  }

  .court-actions .btn-secondary,
  .court-actions .btn-fullframe {
    flex: 1;
    min-width: 0;
    text-align: center;
    font-size: 0.85rem;
    padding: 0.5rem 0.75rem;
  }

  .court-status {
    grid-template-columns: 1fr;
    padding: 0.75rem;
  }

  .corner-label {
    font-size: 0.8rem;
    padding: 0.15rem 0.4rem;
  }

  .hint {
    font-size: 0.85rem;
    line-height: 1.6;
  }

  /* Stream controls bar */
  .stream-controls-bar {
    flex-direction: column;
    gap: 0.5rem;
    padding: 0.5rem 0.75rem;
  }

  .session-info-bar {
    width: 100%;
    justify-content: space-between;
  }

  .controls-right {
    width: 100%;
    justify-content: space-between;
  }

  /* Stream actions */
  .stream-actions {
    flex-direction: column;
  }

  .btn-record,
  .btn-end {
    width: 100%;
    text-align: center;
    justify-content: center;
  }

  .recording-info {
    font-size: 0.8rem;
  }

  .recording-info span {
    font-size: 0.8rem;
  }

  /* Seek bar */
  .seek-bar-container {
    padding: 0.5rem 0.75rem;
  }

  .seek-labels {
    font-size: 0.75rem;
  }

  /* Summary / ended section */
  .summary-stats {
    flex-direction: column;
    gap: 1rem;
    align-items: center;
  }

  .stat .value {
    font-size: 1.5rem;
  }

  .shot-breakdown {
    max-width: 100%;
    padding: 0 0.5rem;
  }

  .post-analysis-section {
    padding: 1rem;
  }

  .post-analysis-stats {
    flex-direction: column;
    gap: 1rem;
    align-items: center;
  }

  .analysis-actions {
    flex-direction: column;
    gap: 0.75rem;
  }

  .analysis-actions .btn-secondary,
  .analysis-actions .btn-primary {
    width: 100%;
    text-align: center;
    justify-content: center;
  }

  .ended-actions {
    flex-direction: column;
  }

  .ended-actions .btn-primary,
  .ended-actions .btn-secondary {
    width: 100%;
    text-align: center;
    padding: 0.75rem;
  }

  .recording-download {
    padding: 1rem;
  }

  .btn-download {
    width: 100%;
    justify-content: center;
  }

  /* Resume section */
  .resume-actions {
    flex-direction: column;
  }

  .resume-actions .btn-primary,
  .resume-actions .btn-secondary {
    width: 100%;
    text-align: center;
    padding: 0.75rem;
  }

  /* Advanced sidebar */
  .advanced-results-card {
    padding: 1rem;
  }
}
</style>
