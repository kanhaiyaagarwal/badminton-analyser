<template>
  <div class="challenge-session">
    <!-- Placement guide overlay -->
    <div v-if="showPlacementGuide" class="placement-overlay" @click="dismissPlacementGuide">
      <div class="placement-card" @click.stop>
        <button class="placement-close" @click="dismissPlacementGuide">&times;</button>

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
          <img :src="positionGuideImg" alt="Position guide" class="placement-img" />
        </div>

        <div class="guide-steps">
          <div class="guide-step">
            <span class="step-number">3</span>
            <div class="step-content" v-if="isHoldType">
              <strong>Wait for the <span class="inline-circle red"></span> circle to turn <span class="inline-circle green"></span>, then hold your {{ challengeTitle }}</strong>
              <p>Get into position. The circle turns green once your form is detected and your full body is visible. You'll hear "Start" when the right posture is detected.</p>
            </div>
            <div class="step-content" v-else>
              <strong>Wait for the <span class="inline-circle red"></span> circle to turn <span class="inline-circle green"></span>, then begin {{ challengeTitle }}</strong>
              <p>The circle turns green once you're in the correct position and your entire body is visible. You'll hear "Start" when the right posture is detected.</p>
            </div>
          </div>
          <div class="guide-step">
            <span class="step-number">4</span>
            <div class="step-content" v-if="isHoldType">
              <strong>Timer only counts good form</strong>
              <p>The hold timer pauses if your form breaks. You get a few seconds to adjust — get back in position and the timer resumes.</p>
            </div>
            <div class="step-content" v-else>
              <strong>Challenge auto-ends</strong>
              <p>When you stand up or drop out of position, the session ends on its own. Want more reps? Start a new challenge!</p>
            </div>
          </div>
          <div class="guide-step">
            <span class="step-number">5</span>
            <div class="step-content">
              <strong>Sound &amp; Record</strong>
              <p v-if="isHoldType">Sound is on by default — you'll hear your hold time called out every 5 seconds. Tap Record to save a video.</p>
              <p v-else>Sound is on by default — you'll hear rep counts called out. Tap Record to save a video of your session.</p>
            </div>
          </div>
        </div>

        <button class="placement-btn" @click="dismissPlacementGuide">Got it, let's go!</button>
      </div>
    </div>

    <!-- Setup phase — fullscreen camera with overlay controls -->
    <div v-if="phase === 'setup'" class="setup-phase">
      <div class="camera-preview-wrap maximized" @click="(cameraReady || isWorkoutMode) && !starting && startSession()">
        <video ref="previewVideo" autoplay playsinline muted class="camera-preview"></video>
        <div v-if="!cameraReady" class="camera-placeholder">
          <p>{{ cameraError || (isWorkoutMode ? 'Tap to start set' : 'Initialising camera...') }}</p>
        </div>

        <!-- Top bar: back, title, info -->
        <div class="setup-top-bar" @click.stop>
          <router-link :to="isWorkoutMode ? `/workout/session/${workoutSessionId}` : `/challenges/${challengeType}`" class="setup-back-btn">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" width="20" height="20" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"/></svg>
          </router-link>
          <span class="setup-title">{{ isWorkoutMode ? `Set ${workoutSetNumber}/${workoutSetsTotal}` : challengeTitle }}</span>
          <button class="setup-info-btn" @click="showPlacementGuide = true">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="20" height="20" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>
          </button>
        </div>

        <!-- Toggle buttons overlaid on camera -->
        <div class="camera-overlay-toggles" @click.stop>
          <button :class="['cam-toggle', { active: recordOnStart }]" @click="toggleRecord" title="Record session">
            <svg viewBox="0 0 24 24" fill="currentColor" width="18" height="18"><circle cx="12" cy="12" r="7"/></svg>
          </button>
          <button :class="['cam-toggle', { active: enableSound }]" @click="toggleSound" title="Sound cues">
            <svg v-if="enableSound" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" width="18" height="18" stroke-linecap="round" stroke-linejoin="round"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14"/><path d="M15.54 8.46a5 5 0 0 1 0 7.07"/></svg>
            <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" width="18" height="18" stroke-linecap="round" stroke-linejoin="round"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><line x1="23" y1="9" x2="17" y2="15"/><line x1="17" y1="9" x2="23" y2="15"/></svg>
          </button>
          <select v-if="cameras.length > 1" v-model="selectedCamera" @change="switchCamera" class="cam-toggle-select" title="Switch camera">
            <option v-for="cam in cameras" :key="cam.deviceId" :value="cam.deviceId">
              {{ cam.label || 'Camera' }}
            </option>
          </select>
        </div>

        <!-- Toast notification -->
        <transition name="toast-fade">
          <div v-if="toastMessage" class="cam-toast">{{ toastMessage }}</div>
        </transition>

        <!-- Tap to start hint -->
        <div v-if="(cameraReady || isWorkoutMode) && !starting" class="tap-start-hint">
          Tap anywhere to start
        </div>
      </div>
    </div>

    <!-- Active phase -->
    <div v-else-if="phase === 'active'" class="active-phase">
      <div class="video-container maximized">
        <video ref="streamVideo" autoplay playsinline muted class="stream-video"></video>
        <canvas ref="overlayCanvas" class="overlay-canvas"></canvas>

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

        <!-- Toast notification -->
        <transition name="toast-fade">
          <div v-if="toastMessage" class="cam-toast">{{ toastMessage }}</div>
        </transition>
      </div>

      <!-- Bottom action bar -->
      <div class="session-bottom-bar">
        <button :class="['bar-btn', { active: enableSound }]" @click="toggleSound">
          <svg v-if="enableSound" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="20" height="20" stroke-linecap="round" stroke-linejoin="round"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14"/></svg>
          <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="20" height="20" stroke-linecap="round" stroke-linejoin="round"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><line x1="23" y1="9" x2="17" y2="15"/><line x1="17" y1="9" x2="23" y2="15"/></svg>
          <span>Sound</span>
        </button>
        <button
          @click="toggleRecording"
          :class="['bar-btn record-btn', { recording: isRecording }]"
        >
          <svg viewBox="0 0 24 24" fill="currentColor" width="22" height="22">
            <circle v-if="!isRecording" cx="12" cy="12" r="8"/>
            <rect v-else x="8" y="8" width="8" height="8" rx="1"/>
          </svg>
          <span>{{ isRecording ? 'Stop' : 'Record' }}</span>
        </button>
        <button @click="endSession" class="bar-btn end-btn">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="20" height="20" stroke-linecap="round" stroke-linejoin="round"><rect x="6" y="6" width="12" height="12" rx="2"/></svg>
          <span>End</span>
        </button>
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
import { useAnalytics } from '../composables/useAnalytics'
import api from '../api/client'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const challengesStore = useChallengesStore()
const analytics = useAnalytics()

const challengeType = computed(() => route.params.type)

// Workout mode: when launched from a workout session to track a set
const workoutSessionId = computed(() => route.query.workout_session_id)
const workoutExerciseId = computed(() => route.query.exercise_id)
const workoutExerciseSlug = computed(() => route.query.exercise_slug)
const workoutExerciseName = computed(() => route.query.exercise_name)
const workoutSetNumber = computed(() => route.query.set_number)
const workoutSetsTotal = computed(() => route.query.sets_total)
const isWorkoutMode = computed(() => !!workoutSessionId.value)

const CHALLENGE_META = {
  plank: { title: 'Plank Hold', hint: 'Get into a plank position in view of the camera, then start.', scoreLabel: 'Hold (s)', unit: 's' },
  squat_hold: { title: 'Squat Hold', hint: 'Stand facing camera, full body visible. Lower into squat position.', scoreLabel: 'Hold (s)', unit: 's' },
  squat_half: { title: 'Half Squats', hint: 'Stand facing camera. Half-depth squats — bend to about 90\u00B0.', scoreLabel: 'Reps', unit: 'reps' },
  squat_full: { title: 'Full Squats', hint: 'Stand facing camera. Go all the way down past parallel.', scoreLabel: 'Reps', unit: 'reps' },
  pushup: { title: 'Max Pushups', hint: 'Position the camera to the side so your full body is visible.', scoreLabel: 'Reps', unit: 'reps' },
  arm_rep: { title: 'Arm Exercise', hint: 'Stand facing camera with full upper body visible.', scoreLabel: 'Reps', unit: 'reps' },
}

const isHoldType = computed(() => ['plank', 'squat_hold'].includes(challengeType.value))
const meta = computed(() => CHALLENGE_META[challengeType.value] || CHALLENGE_META.squat_full)

const POSITION_GUIDE_IMAGES = {
  plank: '/position-guide-plank.png',
  pushup: '/position-guide-pushup.png',
  squat_hold: '/position-guide-squat.png',
  squat_half: '/position-guide-squat.png',
  squat_full: '/position-guide-squat.png',
  arm_rep: '/position-guide-squat.png',
}
const positionGuideImg = computed(() => POSITION_GUIDE_IMAGES[challengeType.value] || '/position-guide-pushup.png')
const challengeTitle = computed(() => {
  // In workout mode, show the actual exercise name (e.g., "Shoulder Press" instead of "Arm Exercise")
  if (isWorkoutMode.value && workoutExerciseName.value) {
    const setInfo = workoutSetNumber.value ? ` — Set ${workoutSetNumber.value}/${workoutSetsTotal.value}` : ''
    return `${workoutExerciseName.value}${setInfo}`
  }
  return meta.value.title
})
const challengeHint = computed(() => meta.value.hint)
const scoreLabel = computed(() => meta.value.scoreLabel)

// Annotations toggle
const showAnnotations = ref(true)


// Placement guide — show once per challenge type, then only via info button
const showPlacementGuide = ref(false)

function checkPlacementGuide() {
  const key = `guide_seen_${challengeType.value}`
  if (!localStorage.getItem(key)) {
    showPlacementGuide.value = true
  }
}

function dismissPlacementGuide() {
  showPlacementGuide.value = false
  const key = `guide_seen_${challengeType.value}`
  localStorage.setItem(key, '1')
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
let prevHoldSeconds = 0
let frameInterval = null
let startTime = null
let elapsedTimer = null
let readyTime = null

// Local hold timer — ticks independently of server responses
let holdTimerInterval = null
let holdStartedAt = null        // wall-clock ms when hold started
let holdBaseSeconds = 0         // server-confirmed hold_seconds at that point
let isInHold = false            // whether the server says the player is actively holding

// Real-time data from backend
const reps = ref(0)
const holdSeconds = ref(0)
const formFeedback = ref('')
const elapsed = ref(0)
const playerDetected = ref(false)
const playerReady = ref(false)
const legsStraight = ref(true)
const timeRemaining = ref(0)

// Feedback stabilization: only update displayed feedback after
// the same message appears for STABILIZE_FRAMES consecutive frames.
// Prevents flickering when pose hovers near a threshold boundary.
const STABILIZE_FRAMES = 3
let _pendingFeedback = ''
let _pendingCount = 0

function stabilizeFeedback(incoming) {
  if (incoming === formFeedback.value) {
    // Already displaying this — reset pending
    _pendingFeedback = incoming
    _pendingCount = STABILIZE_FRAMES
    return
  }
  if (incoming === _pendingFeedback) {
    _pendingCount++
    if (_pendingCount >= STABILIZE_FRAMES) {
      formFeedback.value = incoming
    }
  } else {
    _pendingFeedback = incoming
    _pendingCount = 1
  }
}

// Sound cues
const enableSound = ref(true)

function speak(text) {
  if (!enableSound.value || !window.speechSynthesis) return
  const u = new SpeechSynthesisUtterance(text)
  u.rate = 1.2
  u.volume = 1
  window.speechSynthesis.speak(u)
}

// Recording state
const recordOnStart = ref(false)
const isRecording = ref(false)
const hasRecording = ref(false)
const recordingDuration = ref(0)
let recordingTimer = null

// Toggle toast
const toastMessage = ref('')
let toastTimer = null

function showToast(msg) {
  toastMessage.value = msg
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => { toastMessage.value = '' }, 1200)
}

function toggleRecord() {
  recordOnStart.value = !recordOnStart.value
  showToast(recordOnStart.value ? 'Recording On' : 'Recording Off')
}

function toggleSound() {
  enableSound.value = !enableSound.value
  showToast(enableSound.value ? 'Sound On' : 'Sound Off')
}

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
    speak('Start')
    showGoFlash.value = true
    if (goFlashTimeout) clearTimeout(goFlashTimeout)
    goFlashTimeout = setTimeout(() => {
      showGoFlash.value = false
    }, 1500)
  }
})

const displayScore = computed(() => {
  if (isHoldType.value) return holdSeconds.value
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

// Start elapsed timer when player becomes ready (green dot)
watch(playerReady, (ready) => {
  if (ready && !readyTime) {
    readyTime = Date.now()
    elapsed.value = 0
    elapsedTimer = setInterval(() => {
      elapsed.value = Math.floor((Date.now() - readyTime) / 1000)
    }, 1000)
  }
})

// Local hold timer — ticks every 100ms for smooth plank counter
function startHoldTimer() {
  stopHoldTimer()
  holdTimerInterval = setInterval(() => {
    if (!isInHold || !holdStartedAt) return
    holdSeconds.value = Math.round((holdBaseSeconds + (Date.now() - holdStartedAt) / 1000) * 10) / 10
  }, 100)
}

function stopHoldTimer() {
  if (holdTimerInterval) {
    clearInterval(holdTimerInterval)
    holdTimerInterval = null
  }
}

const feedbackClass = computed(() => {
  const fb = formFeedback.value.toLowerCase()
  const isNegative = fb.includes('don\'t') || fb.includes('over') || fb.includes('lost') ||
      fb.includes('break') || fb.includes('get back')
  if (isNegative) return 'corrective'
  if (fb.includes('good') || fb.includes('great') || fb.includes('rep') ||
      fb.includes('ready') || fb.includes('hold') || fb.includes('detected')) return 'positive'
  return 'corrective'
})

function triggerRepPop(count) {
  speak(String(count))
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
  const cameraInitStart = performance.now()
  try {
    // Need to request permission first
    const tempStream = await navigator.mediaDevices.getUserMedia({ video: true })
    tempStream.getTracks().forEach(t => t.stop())
    const devices = await navigator.mediaDevices.enumerateDevices()
    cameras.value = devices.filter(d => d.kind === 'videoinput')
    if (cameras.value.length > 0 && !selectedCamera.value) {
      // Prefer front camera by default
      const front = cameras.value.find(c => /front|user|facetime/i.test(c.label))
      selectedCamera.value = front ? front.deviceId : cameras.value[0].deviceId
      await switchCamera()
    }
    if (window.DD_RUM) {
      window.DD_RUM.addTiming('camera_init_ms', Math.round(performance.now() - cameraInitStart))
    }
  } catch (err) {
    cameraError.value = 'Camera access denied'
    if (window.DD_RUM) {
      window.DD_RUM.addError(new Error('Camera access denied'), {
        source: 'custom', challenge: challengeType.value, action: 'camera'
      })
    }
  }
}

async function switchCamera() {
  if (mediaStream) {
    mediaStream.getTracks().forEach(t => t.stop())
  }
  if (!selectedCamera.value) return

  try {
    mediaStream = await navigator.mediaDevices.getUserMedia({
      video: {
        deviceId: { exact: selectedCamera.value },
        width: { ideal: 640 }, height: { ideal: 480 },
        zoom: { ideal: 1 },           // widest field of view
        focusMode: { ideal: 'continuous' }
      }
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
    if (window.DD_RUM) {
      window.DD_RUM.addError(new Error('Failed to start camera'), {
        source: 'custom', challenge: challengeType.value, action: 'camera'
      })
    }
  }
}

// ---------- Session lifecycle ----------

let _wsConnectStart = 0
let _firstFrameSent = false

async function startSession() {
  starting.value = true
  try {
    // In workout mode, camera init was deferred — do it now
    if (isWorkoutMode.value && !cameraReady.value) {
      await enumerateCameras()
      if (!cameraReady.value) {
        cameraError.value = 'Camera access denied'
        starting.value = false
        return
      }
    }

    const sessionCreateStart = performance.now()
    let sid
    if (isWorkoutMode.value) {
      // Workout mode: create challenge session via workout start-tracking endpoint
      // Use exercise_slug from query param (passed by WorkoutSessionView) for accurate mapping
      const slug = workoutExerciseSlug.value || _workoutSlugFromChallengeType(challengeType.value)
      const resp = await api.post(`/api/v1/workout/sessions/${workoutSessionId.value}/start-tracking`, {
        exercise_slug: slug,
      })
      sid = resp.data.challenge_session_id
    } else {
      const data = await challengesStore.createSession(challengeType.value)
      sid = data.session_id
    }
    if (window.DD_RUM) {
      window.DD_RUM.addTiming('session_create_ms', Math.round(performance.now() - sessionCreateStart))
    }
    sessionId.value = sid
    analytics.challengeStarted(challengeType.value)
    phase.value = 'connecting'
    _wsConnectStart = performance.now()
    _firstFrameSent = false
    await connectWebSocket(sid)
  } catch (err) {
    if (window.DD_RUM) {
      window.DD_RUM.addError(err, { source: 'custom', challenge: challengeType.value, action: 'start_session' })
    }
    starting.value = false
  }
}

function _workoutSlugFromChallengeType(type) {
  const map = {
    pushup: 'push-up', squat_full: 'bodyweight-squat', plank: 'plank',
    squat_hold: 'squat-hold', squat_half: 'bodyweight-squat',
    bicep_curl: 'bicep-curl', lateral_raise: 'lateral-raise', calf_raise: 'calf-raise',
  }
  return map[type] || type
}

async function connectWebSocket(sid) {
  await authStore.ensureValidToken()
  const token = authStore.accessToken
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = window.location.host
  const wsUrl = `${protocol}//${host}/ws/challenge/${sid}?token=${token}`

  ws = new WebSocket(wsUrl)

  ws.onopen = async () => {
    if (window.DD_RUM && _wsConnectStart) {
      window.DD_RUM.addTiming('ws_connect_ms', Math.round(performance.now() - _wsConnectStart))
    }
    phase.value = 'active'
    starting.value = false

    startTime = Date.now()
    elapsed.value = 0

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
        if (newReps > reps.value && !isHoldType.value) {
          triggerRepPop(newReps)
        }
        reps.value = newReps

        // --- Local hold timer (plank) ---
        const serverHold = data.hold_seconds || 0
        if (isHoldType.value) {
          if (serverHold > 0 && !isInHold) {
            // Hold just started — begin local ticking
            isInHold = true
            holdBaseSeconds = serverHold
            holdStartedAt = Date.now()
            holdSeconds.value = serverHold
            startHoldTimer()
          } else if (serverHold > 0 && isInHold) {
            // Correct from server (authoritative) — re-anchor local timer
            holdBaseSeconds = serverHold
            holdStartedAt = Date.now()
          } else if (serverHold === 0 && isInHold) {
            // Player broke hold
            isInHold = false
            stopHoldTimer()
            holdSeconds.value = 0
          }
        } else {
          holdSeconds.value = serverHold
        }

        // Speak hold time every 5 seconds for hold-based types
        if (isHoldType.value && holdSeconds.value) {
          const prev5 = Math.floor(prevHoldSeconds / 5)
          const curr5 = Math.floor(holdSeconds.value / 5)
          if (curr5 > prev5 && curr5 > 0) {
            speak(String(curr5 * 5))
          }
        }
        prevHoldSeconds = holdSeconds.value
        stabilizeFeedback(data.form_feedback || '')
        playerDetected.value = !!data.player_detected
        playerReady.value = !!data.ready
        timeRemaining.value = data.time_remaining ?? 0
        if (data.exercise) {
          legsStraight.value = data.exercise.legs_straight !== false
        }
        drawPose(data.pose)

        // Auto-end: backend says session is over
        if (data.auto_end) {
          autoEnded = true
          endSession()
          return
        }
      } else if (data.type === 'session_ended') {
        handleSessionEnded(data.report)
      }
    } catch (e) { /* ignore parse errors */ }
  }

  ws.onerror = () => {
    if (window.DD_RUM) {
      window.DD_RUM.addError(new Error('WebSocket connection failed'), {
        source: 'custom', challenge: challengeType.value, action: 'websocket'
      })
    }
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
        if (!_firstFrameSent && window.DD_RUM && _wsConnectStart) {
          _firstFrameSent = true
          window.DD_RUM.addTiming('time_to_first_frame_ms', Math.round(performance.now() - _wsConnectStart))
        }
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
  stopHoldTimer()
  isInHold = false
}

let endingSession = false
let autoEnded = false

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
    if (autoEnded) speak('Session ended')
    if (isWorkoutMode.value) {
      submitWorkoutResults(null)
      return
    }
    try {
      const result = await challengesStore.endSession(sessionId.value)
      navigateToResults(sessionId.value, result)
    } catch (e) {
      router.push(`/challenges/${challengeType.value}`)
    }
  }
}

function handleSessionEnded(report) {
  if (autoEnded) speak('Session ended')
  if (window.DD_RUM) {
    window.DD_RUM.addAction('challenge_session_completed', {
      challenge_type: challengeType.value,
      score: report?.score ?? 0,
      duration_seconds: report?.duration_seconds ?? 0,
      end_reason: autoEnded ? 'auto_end' : 'normal',
      frames_processed: report?.frames_processed ?? 0,
    })
  }
  cleanup()

  if (isWorkoutMode.value) {
    submitWorkoutResults(report)
    return
  }

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

// ---------- Workout Mode: submit results back to workout session ----------

async function submitWorkoutResults(report) {
  const reps = isHoldType.value
    ? Math.floor(report?.hold_seconds || holdSeconds.value || 0)
    : (report?.score || report?.reps || 0)
  const duration = report?.duration_seconds || Math.floor((Date.now() - (startTime || Date.now())) / 1000)
  const formScore = report?.form_score || null

  try {
    const resp = await api.post(
      `/api/v1/workout/sessions/${workoutSessionId.value}/sets/${workoutSetNumber.value}/camera-result`,
      {
        exercise_id: Number(workoutExerciseId.value),
        set_number: Number(workoutSetNumber.value),
        reps,
        form_score: formScore,
        duration_seconds: duration,
      }
    )
    // Update the workout store with the next state (rest_timer, exercise_intro, etc.)
    // so WorkoutSessionView renders the correct view on return
    const { useWorkoutStore } = await import('../stores/workout')
    const workoutStore = useWorkoutStore()
    workoutStore.activeSession = resp.data
    if (resp.data.data?.session_id) {
      workoutStore.sessionId = resp.data.data.session_id
    }
  } catch { /* best-effort */ }

  // Navigate back to the workout session
  router.replace(`/workout/session/${workoutSessionId.value}`)
}

// ---------- Recording ----------

async function toggleRecording() {
  try {
    if (isRecording.value) {
      await api.post(`/api/v1/challenges/sessions/${sessionId.value}/recording/stop`)
      isRecording.value = false
      hasRecording.value = true
      stopRecordingTimer()
      showToast('Recording Off')
    } else {
      await api.post(`/api/v1/challenges/sessions/${sessionId.value}/recording/start`)
      isRecording.value = true
      recordingDuration.value = 0
      startRecordingTimer()
      showToast('Recording On')
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
  if (!canvas) return

  const video = streamVideo.value
  if (!video) return

  canvas.width = video.videoWidth || 640
  canvas.height = video.videoHeight || 480
  const ctx = canvas.getContext('2d')
  ctx.clearRect(0, 0, canvas.width, canvas.height)

  if (!poseData || !showAnnotations.value) return

  const landmarks = poseData.landmarks
  if (!landmarks) return

  const pw = poseData.width
  const ph = poseData.height

  // Scale from pose detection resolution to canvas
  const sx = canvas.width / pw
  const sy = canvas.height / ph

  // Helper: landmark is visible AND within the camera frame
  const isUsable = (lm) =>
      lm && lm.visibility >= 0.5 &&
      lm.x >= 0 && lm.x <= pw &&
      lm.y >= 0 && lm.y <= ph

  ctx.globalAlpha = 0.75

  // Draw connections with body-part colors
  ctx.lineWidth = 3
  for (const [a, b] of poseData.connections) {
    const la = landmarks[a]
    const lb = landmarks[b]
    if (!isUsable(la) || !isUsable(lb)) continue
    ctx.strokeStyle = connectionColor(a, b)
    ctx.beginPath()
    ctx.moveTo(la.x * sx, la.y * sy)
    ctx.lineTo(lb.x * sx, lb.y * sy)
    ctx.stroke()
  }

  // Draw joints with body-part colors
  for (let i = 0; i < landmarks.length; i++) {
    const lm = landmarks[i]
    if (!isUsable(lm)) continue
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
  readyTime = null
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
  }
  // Always clean up camera stream, even during setup phase
  cleanup()
  next()
})

onMounted(() => {
  checkPlacementGuide()
  // In workout mode, defer camera init until user clicks "Start" —
  // camera should only turn on when the user actively begins a set.
  if (!isWorkoutMode.value) {
    enumerateCameras()
  }
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
  overflow-x: hidden;
}

.setup-phase {
  flex: 1;
}

.camera-preview-wrap {
  position: relative;
  background: #000;
  overflow: hidden;
}

.camera-preview, .stream-video {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  transform: scaleX(-1);
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


/* Setup top bar (over fullscreen camera) */
.setup-top-bar {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem;
  padding-top: calc(0.75rem + env(safe-area-inset-top, 0px));
  background: linear-gradient(to bottom, rgba(0,0,0,0.6) 0%, transparent 100%);
  z-index: 12;
}

.setup-back-btn {
  width: 38px;
  height: 38px;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.6);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  text-decoration: none;
  flex-shrink: 0;
}

.setup-title {
  flex: 1;
  color: #fff;
  font-size: 1rem;
  font-weight: 600;
  text-shadow: 0 1px 4px rgba(0,0,0,0.5);
}

.setup-info-btn {
  width: 38px;
  height: 38px;
  border-radius: 50%;
  border: none;
  background: rgba(0, 0, 0, 0.6);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  flex-shrink: 0;
}

/* Camera overlay toggle buttons — bottom row */
.camera-overlay-toggles {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  padding: 0.75rem;
  padding-bottom: calc(0.75rem + env(safe-area-inset-bottom, 0px));
  background: linear-gradient(to top, rgba(0,0,0,0.6) 0%, transparent 100%);
  z-index: 12;
}

.cam-toggle {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  border: 2px solid transparent;
  background: rgba(0, 0, 0, 0.7);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s;
}

.cam-toggle:hover {
  background: rgba(0, 0, 0, 0.85);
}

.cam-toggle.active {
  background: rgba(255, 255, 255, 0.25);
  color: #fff;
}

/* Record button: subtle red ring */
.cam-toggle:first-child {
  border-color: rgba(231, 76, 60, 0.4);
}

.cam-toggle.active:first-child {
  background: rgba(231, 76, 60, 0.8);
  border-color: rgba(231, 76, 60, 0.8);
  color: #fff;
}

.cam-toggle-select {
  height: 44px;
  width: 44px;
  padding: 0;
  border-radius: 50%;
  border: 2px solid transparent;
  background: rgba(0, 0, 0, 0.7);
  color: #fff;
  font-size: 0;
  cursor: pointer;
  text-indent: -9999px;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 24 24' fill='none' stroke='white' stroke-width='2' stroke-linecap='round' stroke-linejoin='round' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z'/%3E%3Ccircle cx='12' cy='13' r='4'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: center;
  background-size: 18px;
  appearance: none;
  -webkit-appearance: none;
}

.cam-toggle-select option {
  background: #222;
  color: #fff;
  font-size: 0.85rem;
  text-indent: 0;
}

/* Toast notification */
.cam-toast {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  background: rgba(0, 0, 0, 0.8);
  color: #fff;
  padding: 0.5rem 1.25rem;
  border-radius: var(--radius-full, 9999px);
  font-size: 0.85rem;
  font-weight: 600;
  white-space: nowrap;
  z-index: 20;
  pointer-events: none;
}

.toast-fade-enter-active {
  transition: opacity 0.15s ease;
}
.toast-fade-leave-active {
  transition: opacity 0.4s ease;
}
.toast-fade-enter-from,
.toast-fade-leave-to {
  opacity: 0;
}

/* Tap to start hint */
.tap-start-hint {
  position: absolute;
  bottom: 4.5rem;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(0, 0, 0, 0.6);
  color: #fff;
  padding: 0.5rem 1.25rem;
  border-radius: var(--radius-full, 9999px);
  font-size: 0.9rem;
  font-weight: 500;
  white-space: nowrap;
  pointer-events: none;
  animation: tap-pulse 2.5s ease-in-out infinite;
  z-index: 11;
}

@keyframes tap-pulse {
  0%, 100% { opacity: 0.6; }
  50% { opacity: 1; }
}

/* Bottom action bar during active challenge */
.session-bottom-bar {
  position: fixed;
  bottom: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 100%;
  max-width: 430px;
  display: flex;
  align-items: center;
  justify-content: space-around;
  padding: 0.5rem 1rem;
  padding-bottom: calc(0.5rem + env(safe-area-inset-bottom, 0px));
  background: rgba(0, 0, 0, 0.85);
  backdrop-filter: blur(12px);
  z-index: 110;
}

.bar-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.2rem;
  background: transparent;
  border: none;
  color: rgba(255, 255, 255, 0.7);
  cursor: pointer;
  padding: 0.4rem 0.75rem;
  border-radius: var(--radius-md);
  transition: all 0.2s;
  font-family: inherit;
}

.bar-btn span {
  font-size: 0.65rem;
  font-weight: 500;
}

.bar-btn:hover, .bar-btn.active {
  color: #fff;
}

.bar-btn.record-btn {
  color: var(--color-destructive);
}

.bar-btn.record-btn.recording {
  color: #fff;
  animation: pulse-record 1s infinite;
}

.bar-btn.end-btn {
  color: rgba(255, 255, 255, 0.7);
}

.bar-btn.end-btn:hover {
  color: var(--color-destructive);
}


/* Active phase */
.video-container {
  position: relative;
  background: #000;
  border-radius: var(--radius-md);
  overflow: hidden;
  aspect-ratio: 4/3;
  width: 100%;
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
  transition: background 0.3s ease, color 0.3s ease, border-color 0.3s ease;
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

@keyframes pulse-record {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.8; }
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
  z-index: 200;
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
  padding: 1rem;
}

.placement-card {
  position: relative;
  background: var(--bg-card);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-xl);
  padding: 2rem;
  max-width: 420px;
  width: 100%;
  text-align: center;
  margin: 1rem auto;
}

.placement-close {
  position: absolute;
  top: 0.75rem;
  right: 0.75rem;
  width: 44px;
  height: 44px;
  border: none;
  background: var(--bg-card);
  color: var(--text-secondary);
  font-size: 1.75rem;
  line-height: 1;
  border-radius: 50%;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 210;
  box-shadow: var(--shadow-md);
}

.placement-close:hover {
  background: var(--color-destructive-light);
  color: var(--color-destructive);
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

/* Fullscreen mode */
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

@media (max-width: 640px) {
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

/* Landscape orientation — camera fills screen, controls compact */
@media (orientation: landscape) and (max-height: 500px) {
  .challenge-session {
    padding: 0;
  }

  /* Fill screen edge-to-edge in landscape */
  .camera-preview-wrap.maximized .camera-preview,
  .video-container.maximized .stream-video {
    object-fit: cover;
  }

  .session-bottom-bar {
    padding: 0.3rem 0.75rem;
  }

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

}
</style>
