<template>
  <div class="frame-viewer">
    <!-- Video Player -->
    <div class="video-container" v-if="videoUrl">
      <video
        ref="videoRef"
        :src="videoUrl"
        class="video-player"
        @loadedmetadata="handleVideoLoad"
        @timeupdate="handleTimeUpdate"
        @seeking="isSeeking = true"
        @seeked="isSeeking = false"
        @error="handleVideoError"
        muted
        playsinline
      ></video>
      <div v-if="videoError" class="video-error">{{ videoError }}</div>
      <div class="video-controls">
        <button @click="togglePlay" class="play-btn">
          {{ isPlaying ? '⏸' : '▶' }}
        </button>
        <span class="video-time">{{ formatTime(videoCurrentTime) }}</span>
      </div>
    </div>
    <div v-else class="no-video">
      <p>Video not available</p>
      <p class="hint">Frame data is displayed below</p>
    </div>

    <!-- Frame Navigation -->
    <div class="navigation">
      <button @click="goToStart" :disabled="currentFrame === 0" class="nav-btn">
        |&lt;
      </button>
      <button @click="prevFrame" :disabled="currentFrame === 0" class="nav-btn">
        &lt;
      </button>
      <div class="frame-slider">
        <div class="slider-with-markers">
          <!-- Time markers on timeline -->
          <div class="time-markers">
            <div
              v-for="tick in timeMarkerTicks"
              :key="'time-' + tick.time"
              class="time-tick"
              :style="{ left: tick.position + '%' }"
            >
              <span class="time-label">{{ formatTimeShort(tick.time) }}</span>
            </div>
          </div>
          <input
            type="range"
            :min="0"
            :max="frames.length - 1"
            :value="currentFrame"
            @input="handleSliderInput"
            class="slider"
          />
          <!-- Current position indicator (thin line) -->
          <div
            class="position-indicator"
            :style="{ left: getMarkerPosition(localFrame) + '%' }"
          ></div>
          <!-- Shot markers on timeline -->
          <div class="shot-markers">
            <!-- Rally end markers - vertical lines showing where player stopped moving -->
            <div
              v-for="rallyEnd in rallyEndFrames"
              :key="'rally-' + rallyEnd.index"
              class="rally-end-marker"
              :class="{ 'at-position': isNearCurrentFrame(rallyEnd.index) }"
              :style="{ left: getMarkerPosition(rallyEnd.index) + '%' }"
              :title="`Rally ${rallyEnd.rallyNumber} End @ ${formatTime(rallyEnd.timestamp)} (player stopped moving)`"
              @click="goToFrameIndex(rallyEnd.index)"
            >
              <span v-if="isNearCurrentFrame(rallyEnd.index)" class="rally-end-tooltip">Rally {{ rallyEnd.rallyNumber }} End</span>
            </div>
            <!-- Shot markers -->
            <div
              v-for="shot in shotFrames"
              :key="'shot-' + shot.index"
              class="shot-marker"
              :class="[getShotMarkerClass(shot.type), { 'at-position': isNearCurrentFrame(shot.index) }]"
              :style="{ left: getMarkerPosition(shot.index) + '%' }"
              :title="`${formatShotType(shot.type)} @ ${formatTime(shot.timestamp)} (${(shot.confidence * 100).toFixed(0)}%)`"
              @click="goToFrameIndex(shot.index)"
            >
              <span v-if="isNearCurrentFrame(shot.index)" class="shot-label">{{ formatShotType(shot.type) }}</span>
            </div>
          </div>
        </div>
      </div>
      <button @click="nextFrame" :disabled="currentFrame >= frames.length - 1" class="nav-btn">
        &gt;
      </button>
      <button @click="goToEnd" :disabled="currentFrame >= frames.length - 1" class="nav-btn">
        &gt;|
      </button>
    </div>

    <!-- Shot Summary & Legend -->
    <div class="shot-summary-section">
      <!-- Overall Shot Counts -->
      <div v-if="Object.keys(shotCounts).length > 0" class="shot-summary">
        <h4>Shot Summary</h4>
        <div class="shot-counts-grid">
          <div
            v-for="(count, type) in shotCounts"
            :key="type"
            class="shot-count-item"
            :class="getShotClass(type)"
          >
            <span class="shot-count-value">{{ count }}</span>
            <span class="shot-count-label">{{ formatShotType(type) }}</span>
          </div>
        </div>
        <div class="total-shots">
          Total: <strong>{{ shotFrames.length }}</strong> shots
        </div>
      </div>

      <!-- Timeline Legend -->
      <div v-if="shotFrames.length > 0 || rallyEndFrames.length > 0" class="shot-legend">
        <span class="legend-label">Timeline:</span>
        <span v-if="shotCounts.smash" class="legend-item"><span class="dot marker-smash"></span>Smash ({{ shotCounts.smash }})</span>
        <span v-if="shotCounts.clear" class="legend-item"><span class="dot marker-clear"></span>Clear ({{ shotCounts.clear }})</span>
        <span v-if="shotCounts.drop_shot" class="legend-item"><span class="dot marker-drop"></span>Drop ({{ shotCounts.drop_shot }})</span>
        <span v-if="shotCounts.net_shot" class="legend-item"><span class="dot marker-net"></span>Net ({{ shotCounts.net_shot }})</span>
        <span v-if="shotCounts.drive" class="legend-item"><span class="dot marker-drive"></span>Drive ({{ shotCounts.drive }})</span>
        <span v-if="shotCounts.lift" class="legend-item"><span class="dot marker-lift"></span>Lift ({{ shotCounts.lift }})</span>
        <span v-if="rallyEndFrames.length > 0" class="legend-item"><span class="dot marker-rally-end"></span>Rally End ({{ rallyEndFrames.length }})</span>
      </div>
    </div>

    <!-- Frame Info -->
    <div class="frame-info">
      <div class="info-row">
        <span class="label">Position:</span>
        <span class="value">{{ localFrame + 1 }}</span>
        <span class="total">/ {{ frames.length }}</span>
      </div>
      <div class="info-row">
        <span class="label">Time:</span>
        <span class="value">{{ formatTime(currentFrameData?.timestamp || 0) }}</span>
      </div>
      <div class="info-row">
        <span class="label">Video Frame:</span>
        <span class="value frame-num">{{ currentFrameData?.frame_number || 0 }}</span>
      </div>
    </div>

    <!-- Current Frame Data Panel -->
    <div class="data-panel">
      <div v-if="!currentFrameData?.player_detected" class="no-player">
        No player detected in this frame
      </div>

      <template v-else>
        <!-- Velocity Metrics -->
        <div class="metric-section">
          <h4>Velocity</h4>
          <div class="metric-row">
            <span class="metric-label">Wrist:</span>
            <div class="metric-bar-container">
              <div
                class="metric-bar"
                :style="{ width: getVelocityWidth(currentFrameData.wrist_velocity) + '%' }"
              ></div>
              <span class="metric-value">{{ formatVelocity(currentFrameData.wrist_velocity) }}</span>
            </div>
          </div>
          <div class="metric-row">
            <span class="metric-label">Body:</span>
            <div class="metric-bar-container">
              <div
                class="metric-bar body"
                :style="{ width: getVelocityWidth(currentFrameData.body_velocity) + '%' }"
              ></div>
              <span class="metric-value">{{ formatVelocity(currentFrameData.body_velocity) }}</span>
            </div>
          </div>
          <div class="metric-row">
            <span class="metric-label">Direction:</span>
            <span class="metric-value direction">{{ currentFrameData.wrist_direction || '-' }}</span>
          </div>
        </div>

        <!-- Classification -->
        <div class="metric-section">
          <h4>Classification</h4>
          <div class="classification-display">
            <div :class="['shot-badge', getShotClass(displayedShotType)]">
              {{ displayedShotType || 'Unknown' }}
            </div>
            <div class="confidence">
              {{ (displayedConfidence * 100).toFixed(0) }}%
            </div>
          </div>
          <div class="metric-row">
            <span class="metric-label">Swing:</span>
            <span class="metric-value">{{ currentFrameData.swing_type || '-' }}</span>
          </div>
          <div class="metric-row">
            <span class="metric-label">Cooldown:</span>
            <span :class="['metric-value', { active: currentFrameData.cooldown_active }]">
              {{ currentFrameData.cooldown_active ? 'Active' : 'Off' }}
            </span>
          </div>
        </div>

        <!-- Position Info -->
        <div class="metric-section">
          <h4>Position</h4>
          <div v-if="currentFrameData.wrist_y !== null" class="metric-row">
            <span class="metric-label">Wrist Y:</span>
            <span class="metric-value">{{ currentFrameData.wrist_y?.toFixed(3) }}</span>
          </div>
          <div v-if="currentFrameData.shoulder_y !== null" class="metric-row">
            <span class="metric-label">Shoulder Y:</span>
            <span class="metric-value">{{ currentFrameData.shoulder_y?.toFixed(3) }}</span>
          </div>
          <div v-if="currentFrameData.hip_y !== null" class="metric-row">
            <span class="metric-label">Hip Y:</span>
            <span class="metric-value">{{ currentFrameData.hip_y?.toFixed(3) }}</span>
          </div>
          <div v-if="currentFrameData.arm_extension !== null" class="metric-row">
            <span class="metric-label">Arm Ext:</span>
            <span class="metric-value">{{ currentFrameData.arm_extension?.toFixed(3) }}</span>
          </div>
        </div>

        <!-- Boolean Conditions -->
        <div v-if="currentFrameData.is_overhead !== null" class="metric-section">
          <h4>Conditions</h4>
          <div class="condition-badges">
            <span :class="['condition-badge', { active: currentFrameData.is_overhead }]">
              Overhead
            </span>
            <span :class="['condition-badge', { active: currentFrameData.is_low_position }]">
              Low
            </span>
            <span :class="['condition-badge', { active: currentFrameData.is_arm_extended }]">
              Extended
            </span>
            <span v-if="currentFrameData.is_wrist_between_shoulder_hip !== null" :class="['condition-badge', { active: currentFrameData.is_wrist_between_shoulder_hip }]">
              Mid-body
            </span>
          </div>
          <div v-if="currentFrameData.classification_reason" class="classification-reason">
            <span class="reason-text">{{ currentFrameData.classification_reason }}</span>
          </div>
        </div>

        <!-- Re-classification Results -->
        <div v-if="hasReclassifyResult" class="metric-section reclassify-section">
          <h4>Re-classification</h4>
          <div class="reclassify-comparison">
            <div class="original">
              <span class="label">Original:</span>
              <span :class="['shot-badge small', getShotClass(currentFrameData.shot_type)]">
                {{ currentFrameData.shot_type }}
              </span>
            </div>
            <span class="arrow">→</span>
            <div class="new">
              <span class="label">New:</span>
              <span :class="['shot-badge small', getShotClass(reclassifiedShotType)]">
                {{ reclassifiedShotType }}
              </span>
            </div>
          </div>
          <div v-if="wasChanged" class="changed-badge">Changed</div>
        </div>
      </template>
    </div>

    <!-- Keyboard Shortcuts Help -->
    <div class="shortcuts-help">
      <span>← / → : Navigate frames</span>
      <span>Home / End : Jump to start/end</span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  frames: {
    type: Array,
    required: true
  },
  videoInfo: {
    type: Object,
    default: null
  },
  currentFrame: {
    type: Number,
    default: 0
  },
  reclassifyResults: {
    type: Object,
    default: null
  },
  videoUrl: {
    type: String,
    default: null
  },
  jobId: {
    type: [Number, String],
    default: null
  },
  rallyThresholds: {
    type: Object,
    default: () => ({
      stillness_frames: 4,
      stillness_threshold: 0.02
    })
  }
})

const emit = defineEmits(['frameChange'])

// Video refs
const videoRef = ref(null)
const isPlaying = ref(false)
const isSeeking = ref(false)
const videoCurrentTime = ref(0)
const videoDuration = ref(0)
const syncingFromVideo = ref(false)
const syncingFromSlider = ref(false)
const videoError = ref('')

const localFrame = ref(props.currentFrame)

watch(() => props.currentFrame, (newVal) => {
  localFrame.value = newVal
})

const currentFrameData = computed(() => {
  return props.frames[localFrame.value] || null
})

const reclassifyResult = computed(() => {
  if (!props.reclassifyResults?.results || !currentFrameData.value) return null
  return props.reclassifyResults.results.find(
    r => r.frame_number === currentFrameData.value.frame_number
  )
})

const hasReclassifyResult = computed(() => {
  return reclassifyResult.value && reclassifyResult.value.player_detected
})

const reclassifiedShotType = computed(() => {
  return reclassifyResult.value?.new_shot_type || currentFrameData.value?.shot_type
})

// Compute frames that have actual shots detected
const ACTUAL_SHOTS = ['smash', 'clear', 'drop_shot', 'net_shot', 'drive', 'lift']
const shotFrames = computed(() => {
  const shots = props.frames
    .map((frame, index) => ({
      index,
      type: frame.shot_type,
      timestamp: frame.timestamp,
      confidence: frame.confidence || 0
    }))
    .filter(f => ACTUAL_SHOTS.includes(f.type))

  console.log('Shot frames found:', shots.length, shots.slice(0, 5))
  return shots
})

// Count shots by type
const shotCounts = computed(() => {
  const counts = {}
  for (const shot of shotFrames.value) {
    counts[shot.type] = (counts[shot.type] || 0) + 1
  }
  return counts
})

// Detect rally ends by finding periods of stillness (player not moving)
// A rally ends when body coordinates don't change by more than threshold over several frames
// These values come from props.rallyThresholds (tunable in dashboard)

const rallyEndFrames = computed(() => {
  const stillnessFrames = props.rallyThresholds?.stillness_frames ?? 4
  const stillnessThreshold = props.rallyThresholds?.stillness_threshold ?? 0.02

  if (props.frames.length < stillnessFrames + 1) return []

  const rallyEnds = []
  let inStillPeriod = false
  let stillStartIndex = -1
  let hadShotBeforeStill = false
  let lastShotIndex = -1

  // Track when we last saw a shot
  const shotIndices = new Set(shotFrames.value.map(s => s.index))

  for (let i = 0; i < props.frames.length - stillnessFrames; i++) {
    // Track if we've had a shot before this point
    if (shotIndices.has(i)) {
      lastShotIndex = i
      hadShotBeforeStill = true
    }

    // Check if player is still for the next stillnessFrames frames
    const isStill = checkStillness(i, stillnessFrames, stillnessThreshold)

    if (isStill && !inStillPeriod) {
      // Entering a still period
      inStillPeriod = true
      stillStartIndex = i

      // If we had shots before this stillness, this is a rally end
      if (hadShotBeforeStill && lastShotIndex >= 0) {
        rallyEnds.push({
          index: stillStartIndex,
          timestamp: props.frames[stillStartIndex]?.timestamp || 0,
          rallyNumber: rallyEnds.length + 1,
          lastShotIndex: lastShotIndex
        })
        hadShotBeforeStill = false  // Reset for next rally
      }
    } else if (!isStill && inStillPeriod) {
      // Exiting still period - player started moving again (new rally starting)
      inStillPeriod = false
    }
  }

  return rallyEnds
})

// Check if player is still (not moving) for N consecutive frames starting at frameIndex
function checkStillness(frameIndex, numFrames, threshold) {
  const baseFrame = props.frames[frameIndex]
  if (!baseFrame?.player_detected) return false

  // Get base positions (use wrist and hip as key indicators)
  const baseWristX = baseFrame.wrist_x
  const baseWristY = baseFrame.wrist_y
  const baseHipX = baseFrame.hip_x
  const baseHipY = baseFrame.hip_y

  // Need valid base positions
  if (baseWristX == null || baseWristY == null) return false

  for (let i = 1; i <= numFrames; i++) {
    const frame = props.frames[frameIndex + i]
    if (!frame?.player_detected) return false

    const wristX = frame.wrist_x
    const wristY = frame.wrist_y
    const hipX = frame.hip_x
    const hipY = frame.hip_y

    if (wristX == null || wristY == null) return false

    // Check if wrist moved too much
    const wristDx = Math.abs(wristX - baseWristX)
    const wristDy = Math.abs(wristY - baseWristY)
    if (wristDx > threshold || wristDy > threshold) return false

    // Check hip movement if available
    if (baseHipX != null && hipX != null) {
      const hipDx = Math.abs(hipX - baseHipX)
      const hipDy = Math.abs(hipY - baseHipY)
      if (hipDx > threshold || hipDy > threshold) return false
    }
  }

  return true  // Player was still for all frames
}

// Time marker ticks for timeline (every 10 seconds for short videos, 30s for longer)
const timeMarkerTicks = computed(() => {
  if (props.frames.length < 2) return []

  const duration = props.frames[props.frames.length - 1]?.timestamp || 0
  if (duration <= 0) return []

  // Choose tick interval based on duration
  let interval = 10 // Default: every 10 seconds
  if (duration > 300) interval = 60 // Over 5 minutes: every minute
  else if (duration > 120) interval = 30 // Over 2 minutes: every 30 seconds
  else if (duration < 30) interval = 5 // Under 30 seconds: every 5 seconds

  const ticks = []
  for (let time = 0; time <= duration; time += interval) {
    // Find the closest frame to this time
    let closestIdx = 0
    let closestDiff = Infinity
    for (let i = 0; i < props.frames.length; i++) {
      const diff = Math.abs(props.frames[i].timestamp - time)
      if (diff < closestDiff) {
        closestDiff = diff
        closestIdx = i
      }
    }
    ticks.push({
      time: time,
      position: (closestIdx / (props.frames.length - 1)) * 100
    })
  }
  return ticks
})

// Check if a shot marker is near the current frame position
function isNearCurrentFrame(shotIndex) {
  const threshold = Math.max(3, Math.floor(props.frames.length * 0.01)) // 1% of video or at least 3 frames
  return Math.abs(shotIndex - localFrame.value) <= threshold
}

// Short time format for tick labels
function formatTimeShort(seconds) {
  if (!seconds && seconds !== 0) return '0:00'
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

function formatShotType(type) {
  const names = {
    smash: 'Smash',
    clear: 'Clear',
    drop_shot: 'Drop',
    net_shot: 'Net',
    drive: 'Drive',
    lift: 'Lift'
  }
  return names[type] || type
}

const wasChanged = computed(() => {
  return reclassifyResult.value?.changed || false
})

const displayedShotType = computed(() => {
  if (hasReclassifyResult.value) {
    return reclassifyResult.value.new_shot_type
  }
  return currentFrameData.value?.shot_type
})

const displayedConfidence = computed(() => {
  if (hasReclassifyResult.value) {
    return reclassifyResult.value.new_confidence || 0
  }
  return currentFrameData.value?.confidence || 0
})

function handleSliderInput(event) {
  const newFrame = parseInt(event.target.value)
  localFrame.value = newFrame
  emit('frameChange', newFrame)
  syncVideoToFrame()
}

// Video control methods
function handleVideoLoad() {
  if (videoRef.value) {
    videoDuration.value = videoRef.value.duration
    videoError.value = ''
    console.log('Video loaded, duration:', videoDuration.value)
  }
}

function handleVideoError(event) {
  const video = event.target
  const error = video.error
  console.error('Video error:', error)
  if (error) {
    switch (error.code) {
      case 1:
        videoError.value = 'Video loading aborted'
        break
      case 2:
        videoError.value = 'Network error loading video'
        break
      case 3:
        videoError.value = 'Video decode error'
        break
      case 4:
        videoError.value = 'Video format not supported or CORS issue'
        break
      default:
        videoError.value = 'Unknown video error'
    }
  }
}

function handleTimeUpdate() {
  if (!videoRef.value || syncingFromSlider.value) return
  videoCurrentTime.value = videoRef.value.currentTime

  // Find the closest frame to the current video time
  if (!isSeeking.value && !syncingFromVideo.value) {
    syncingFromVideo.value = true
    const closestIndex = findClosestFrameIndex(videoCurrentTime.value)
    if (closestIndex !== localFrame.value) {
      localFrame.value = closestIndex
      emit('frameChange', closestIndex)
    }
    syncingFromVideo.value = false
  }
}

function findClosestFrameIndex(time) {
  let closestIndex = 0
  let closestDiff = Infinity

  for (let i = 0; i < props.frames.length; i++) {
    const frameTIme = props.frames[i].timestamp
    const diff = Math.abs(frameTIme - time)
    if (diff < closestDiff) {
      closestDiff = diff
      closestIndex = i
    }
  }
  return closestIndex
}

function syncVideoToFrame() {
  if (!videoRef.value || !currentFrameData.value) return
  syncingFromSlider.value = true
  videoRef.value.currentTime = currentFrameData.value.timestamp || 0
  setTimeout(() => {
    syncingFromSlider.value = false
  }, 100)
}

async function togglePlay() {
  if (!videoRef.value) return
  try {
    if (isPlaying.value) {
      videoRef.value.pause()
      isPlaying.value = false
    } else {
      await videoRef.value.play()
      isPlaying.value = true
    }
  } catch (err) {
    console.error('Video playback error:', err)
    console.error('Video URL:', props.videoUrl)
    videoError.value = 'Cannot play video: ' + err.message
  }
}

// Override navigation to sync video
function prevFrame() {
  if (localFrame.value > 0) {
    localFrame.value--
    emit('frameChange', localFrame.value)
    syncVideoToFrame()
  }
}

function nextFrame() {
  if (localFrame.value < props.frames.length - 1) {
    localFrame.value++
    emit('frameChange', localFrame.value)
    syncVideoToFrame()
  }
}

function goToStart() {
  localFrame.value = 0
  emit('frameChange', 0)
  syncVideoToFrame()
}

function goToEnd() {
  localFrame.value = props.frames.length - 1
  emit('frameChange', localFrame.value)
  syncVideoToFrame()
}

function goToFrameIndex(index) {
  localFrame.value = index
  emit('frameChange', index)
  syncVideoToFrame()
}

function getMarkerPosition(index) {
  if (props.frames.length <= 1) return 0
  return (index / (props.frames.length - 1)) * 100
}

function getShotMarkerClass(shotType) {
  const classes = {
    smash: 'marker-smash',
    clear: 'marker-clear',
    drop_shot: 'marker-drop',
    net_shot: 'marker-net',
    drive: 'marker-drive',
    lift: 'marker-lift'
  }
  return classes[shotType] || 'marker-default'
}

function handleKeydown(event) {
  if (event.key === 'ArrowLeft') {
    event.preventDefault()
    prevFrame()
  } else if (event.key === 'ArrowRight') {
    event.preventDefault()
    nextFrame()
  } else if (event.key === 'Home') {
    event.preventDefault()
    goToStart()
  } else if (event.key === 'End') {
    event.preventDefault()
    goToEnd()
  }
}

onMounted(() => {
  window.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown)
})

function formatTime(seconds) {
  if (!seconds && seconds !== 0) return '0:00.0'
  const mins = Math.floor(seconds / 60)
  const secs = (seconds % 60).toFixed(1)
  return `${mins}:${secs.padStart(4, '0')}`
}

function formatVelocity(vel) {
  if (!vel && vel !== 0) return '0.00'
  return vel.toFixed(2)
}

function getVelocityWidth(vel) {
  if (!vel) return 0
  // Normalize to 0-100%, assuming max velocity of ~5
  return Math.min(100, (vel / 5) * 100)
}

function getShotClass(shotType) {
  const classes = {
    smash: 'shot-smash',
    clear: 'shot-clear',
    drop_shot: 'shot-drop',
    net_shot: 'shot-net',
    drive: 'shot-drive',
    lift: 'shot-lift',
    preparation: 'shot-prep',
    ready_position: 'shot-ready',
    static: 'shot-static',
    follow_through: 'shot-follow'
  }
  return classes[shotType] || 'shot-unknown'
}
</script>

<style scoped>
.frame-viewer {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.video-container {
  position: relative;
  background: #0a0a14;
  border-radius: 8px;
  overflow: hidden;
}

.video-player {
  width: 100%;
  max-height: 400px;
  display: block;
  background: #000;
}

.video-controls {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 0.75rem;
  background: linear-gradient(transparent, rgba(0, 0, 0, 0.8));
  display: flex;
  align-items: center;
  gap: 1rem;
}

.play-btn {
  width: 40px;
  height: 40px;
  background: rgba(78, 204, 163, 0.9);
  border: none;
  border-radius: 50%;
  color: #1a1a2e;
  font-size: 1rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.2s;
}

.play-btn:hover {
  background: #4ecca3;
}

.video-time {
  color: #eee;
  font-size: 0.9rem;
  font-family: monospace;
}

.no-video {
  background: #1a1a2e;
  border-radius: 8px;
  padding: 2rem;
  text-align: center;
  color: #888;
}

.no-video .hint {
  font-size: 0.85rem;
  color: #666;
  margin-top: 0.5rem;
}

.video-error {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  background: rgba(231, 76, 60, 0.9);
  color: white;
  padding: 0.75rem 1.5rem;
  border-radius: 8px;
  font-size: 0.9rem;
}

.navigation {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.nav-btn {
  width: 36px;
  height: 36px;
  background: #2a2a4a;
  border: none;
  border-radius: 6px;
  color: #eee;
  cursor: pointer;
  font-weight: bold;
  transition: background 0.2s;
}

.nav-btn:hover:not(:disabled) {
  background: #3a3a5a;
}

.nav-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.frame-slider {
  flex: 1;
}

.slider-with-markers {
  position: relative;
  width: 100%;
  padding-top: 18px; /* Space for time labels */
}

/* Time markers along the timeline */
.time-markers {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 18px;
  pointer-events: none;
}

.time-tick {
  position: absolute;
  transform: translateX(-50%);
}

.time-tick::after {
  content: '';
  position: absolute;
  left: 50%;
  top: 14px;
  width: 1px;
  height: 6px;
  background: rgba(255, 255, 255, 0.3);
  transform: translateX(-50%);
}

.time-label {
  font-size: 9px;
  color: #666;
  white-space: nowrap;
}

/* Current position indicator - thin line */
.position-indicator {
  position: absolute;
  top: 14px;
  width: 2px;
  height: 20px;
  background: #4ecca3;
  transform: translateX(-50%);
  pointer-events: none;
  z-index: 5;
  box-shadow: 0 0 4px rgba(78, 204, 163, 0.6);
}

.shot-markers {
  position: absolute;
  top: 14px;
  left: 0;
  right: 0;
  height: 20px;
  pointer-events: none;
}

.shot-marker {
  position: absolute;
  top: -4px;
  width: 6px;
  height: 16px;
  border-radius: 2px;
  transform: translateX(-50%);
  cursor: pointer;
  pointer-events: auto;
  opacity: 0.85;
  transition: transform 0.15s, opacity 0.15s, box-shadow 0.15s;
  z-index: 2;
}

.shot-marker:hover {
  transform: translateX(-50%) scaleY(1.2);
  opacity: 1;
  z-index: 10;
}

/* When shot marker is at/near current position */
.shot-marker.at-position {
  transform: translateX(-50%) scaleY(1.4);
  opacity: 1;
  z-index: 15;
  box-shadow: 0 0 8px currentColor;
}

.shot-label {
  position: absolute;
  bottom: 100%;
  left: 50%;
  transform: translateX(-50%);
  font-size: 9px;
  font-weight: bold;
  color: inherit;
  white-space: nowrap;
  padding: 2px 4px;
  background: rgba(0, 0, 0, 0.8);
  border-radius: 3px;
  margin-bottom: 2px;
}

.marker-smash { background: #e74c3c; color: #e74c3c; }
.marker-clear { background: #2ecc71; color: #2ecc71; }
.marker-drop { background: #f1c40f; color: #f1c40f; }
.marker-net { background: #3498db; color: #3498db; }
.marker-drive { background: #9b59b6; color: #9b59b6; }
.marker-lift { background: #e67e22; color: #e67e22; }
.marker-default { background: #888; color: #888; }
.marker-rally-end { background: #fff; color: #fff; }

/* Rally end markers - simple vertical dashed lines */
.rally-end-marker {
  position: absolute;
  top: -10px;
  width: 0;
  height: 28px;
  border-left: 2px dashed rgba(255, 255, 255, 0.6);
  transform: translateX(-50%);
  cursor: pointer;
  pointer-events: auto;
  z-index: 3;
}

.rally-end-marker:hover {
  border-left-color: #fff;
  border-left-style: solid;
}

.rally-end-marker.at-position {
  border-left-color: #fff;
  border-left-style: solid;
  border-left-width: 3px;
  z-index: 12;
}

.rally-end-tooltip {
  position: absolute;
  bottom: 100%;
  left: 50%;
  transform: translateX(-50%);
  font-size: 10px;
  font-weight: bold;
  color: #1a1a2e;
  white-space: nowrap;
  background: #fff;
  padding: 3px 8px;
  border-radius: 4px;
  margin-bottom: 4px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
}

.shot-summary-section {
  background: #1a1a2e;
  border-radius: 8px;
  padding: 0.75rem;
}

.shot-summary h4 {
  margin: 0 0 0.75rem;
  color: #4ecca3;
  font-size: 0.9rem;
}

.shot-counts-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(80px, 1fr));
  gap: 0.5rem;
  margin-bottom: 0.75rem;
}

.shot-count-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 0.5rem;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.05);
}

.shot-count-value {
  font-size: 1.5rem;
  font-weight: bold;
}

.shot-count-label {
  font-size: 0.7rem;
  text-transform: uppercase;
  opacity: 0.8;
}

.shot-count-item.shot-smash { background: rgba(231, 76, 60, 0.2); color: #e74c3c; }
.shot-count-item.shot-clear { background: rgba(46, 204, 113, 0.2); color: #2ecc71; }
.shot-count-item.shot-drop { background: rgba(241, 196, 15, 0.2); color: #f1c40f; }
.shot-count-item.shot-net { background: rgba(52, 152, 219, 0.2); color: #3498db; }
.shot-count-item.shot-drive { background: rgba(155, 89, 182, 0.2); color: #9b59b6; }
.shot-count-item.shot-lift { background: rgba(230, 126, 34, 0.2); color: #e67e22; }

.total-shots {
  text-align: center;
  color: #888;
  font-size: 0.85rem;
  padding-top: 0.5rem;
  border-top: 1px solid #2a2a4a;
}

.total-shots strong {
  color: #4ecca3;
}

.shot-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  align-items: center;
  padding: 0.5rem 0;
  font-size: 0.75rem;
  margin-top: 0.5rem;
  border-top: 1px solid #2a2a4a;
}

.legend-label {
  color: #888;
  margin-right: 0.25rem;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  color: #aaa;
}

.legend-item .dot {
  width: 8px;
  height: 8px;
  border-radius: 2px;
}

.legend-item .dot.marker-smash { background: #e74c3c; }
.legend-item .dot.marker-clear { background: #2ecc71; }
.legend-item .dot.marker-drop { background: #f1c40f; }
.legend-item .dot.marker-net { background: #3498db; }
.legend-item .dot.marker-drive { background: #9b59b6; }
.legend-item .dot.marker-lift { background: #e67e22; }
.legend-item .dot.marker-rally-end {
  background: transparent;
  border: 1px dashed #fff;
  width: 2px;
  height: 10px;
  border-radius: 0;
}

.slider {
  width: 100%;
  -webkit-appearance: none;
  appearance: none;
  height: 6px;
  background: #2a2a4a;
  border-radius: 3px;
  outline: none;
  cursor: pointer;
}

.slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 4px;
  height: 14px;
  background: transparent;
  border-radius: 2px;
  cursor: pointer;
}

.slider::-moz-range-thumb {
  width: 4px;
  height: 14px;
  background: transparent;
  border: none;
  border-radius: 2px;
  cursor: pointer;
}

.frame-info {
  display: flex;
  gap: 2rem;
  padding: 0.75rem;
  background: #1a1a2e;
  border-radius: 8px;
}

.info-row {
  display: flex;
  align-items: baseline;
  gap: 0.5rem;
}

.info-row .label {
  color: #888;
  font-size: 0.85rem;
}

.info-row .value {
  color: #4ecca3;
  font-size: 1.1rem;
  font-weight: bold;
}

.info-row .total {
  color: #666;
  font-size: 0.85rem;
}

.info-row .frame-num {
  color: #888;
  font-size: 0.9rem;
}

.data-panel {
  background: #1a1a2e;
  border-radius: 8px;
  padding: 1rem;
}

.no-player {
  text-align: center;
  color: #888;
  padding: 2rem;
}

.metric-section {
  margin-bottom: 1rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid #2a2a4a;
}

.metric-section:last-child {
  margin-bottom: 0;
  padding-bottom: 0;
  border-bottom: none;
}

.metric-section h4 {
  margin: 0 0 0.75rem;
  color: #888;
  font-size: 0.8rem;
  text-transform: uppercase;
}

.metric-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 0.5rem;
}

.metric-label {
  color: #888;
  font-size: 0.85rem;
  min-width: 70px;
}

.metric-value {
  color: #eee;
  font-size: 0.9rem;
}

.metric-value.direction {
  text-transform: capitalize;
  color: #4ecca3;
}

.metric-value.active {
  color: #f1c40f;
}

.metric-bar-container {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.metric-bar-container .metric-value {
  min-width: 50px;
  text-align: right;
}

.metric-bar {
  height: 8px;
  background: linear-gradient(90deg, #4ecca3 0%, #3db892 100%);
  border-radius: 4px;
  min-width: 2px;
  transition: width 0.2s;
}

.metric-bar.body {
  background: linear-gradient(90deg, #3498db 0%, #2980b9 100%);
}

.classification-display {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 0.75rem;
}

.shot-badge {
  padding: 0.5rem 1rem;
  border-radius: 20px;
  font-weight: bold;
  text-transform: capitalize;
  font-size: 1rem;
}

.shot-badge.small {
  padding: 0.25rem 0.75rem;
  font-size: 0.85rem;
}

.shot-smash { background: rgba(231, 76, 60, 0.3); color: #e74c3c; }
.shot-clear { background: rgba(46, 204, 113, 0.3); color: #2ecc71; }
.shot-drop { background: rgba(241, 196, 15, 0.3); color: #f1c40f; }
.shot-net { background: rgba(52, 152, 219, 0.3); color: #3498db; }
.shot-drive { background: rgba(155, 89, 182, 0.3); color: #9b59b6; }
.shot-lift { background: rgba(230, 126, 34, 0.3); color: #e67e22; }
.shot-prep { background: rgba(149, 165, 166, 0.3); color: #95a5a6; }
.shot-ready { background: rgba(127, 140, 141, 0.3); color: #7f8c8d; }
.shot-static { background: rgba(99, 110, 114, 0.3); color: #636e72; }
.shot-follow { background: rgba(116, 185, 255, 0.3); color: #74b9ff; }
.shot-unknown { background: rgba(99, 110, 114, 0.3); color: #636e72; }

.confidence {
  font-size: 1.5rem;
  font-weight: bold;
  color: #4ecca3;
}

.reclassify-section {
  background: rgba(78, 204, 163, 0.1);
  border-radius: 8px;
  padding: 0.75rem;
  margin-top: 0.5rem;
}

.reclassify-comparison {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.reclassify-comparison .label {
  color: #888;
  font-size: 0.8rem;
  margin-right: 0.25rem;
}

.arrow {
  color: #4ecca3;
  font-size: 1.2rem;
}

.changed-badge {
  display: inline-block;
  margin-top: 0.5rem;
  padding: 0.25rem 0.5rem;
  background: rgba(241, 196, 15, 0.2);
  color: #f1c40f;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: bold;
}

.condition-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.condition-badge {
  padding: 0.25rem 0.5rem;
  background: rgba(100, 100, 100, 0.2);
  color: #666;
  border-radius: 4px;
  font-size: 0.7rem;
  text-transform: uppercase;
  transition: all 0.2s;
}

.condition-badge.active {
  background: rgba(78, 204, 163, 0.3);
  color: #4ecca3;
  font-weight: bold;
}

.classification-reason {
  background: #1a1a2e;
  border-radius: 4px;
  padding: 0.5rem;
  margin-top: 0.5rem;
}

.reason-text {
  font-size: 0.7rem;
  color: #888;
  font-family: monospace;
  word-break: break-all;
}

.shortcuts-help {
  display: flex;
  gap: 2rem;
  justify-content: center;
  color: #666;
  font-size: 0.75rem;
}
</style>
