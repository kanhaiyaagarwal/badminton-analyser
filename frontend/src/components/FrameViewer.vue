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
            <!-- Gap zone overlays -->
            <template v-if="showRallyMarkers">
              <div
                v-for="(gz, idx) in shuttleGapZones"
                :key="'gap-' + idx"
                class="gap-zone-overlay"
                :style="{
                  left: (getMarkerPosition(gz.startIdx) + 0.1 * (getMarkerPosition(gz.endIdx) - getMarkerPosition(gz.startIdx))) + '%',
                  width: (0.8 * (getMarkerPosition(gz.endIdx) - getMarkerPosition(gz.startIdx))) + '%'
                }"
                :title="`Gap zone: ${formatTime(frames[gz.startIdx]?.timestamp)} - ${formatTime(frames[gz.endIdx]?.timestamp)}`"
              ></div>
            </template>
            <!-- Rally end markers -->
            <template v-if="showRallyMarkers">
              <div
                v-for="rallyEnd in rallyEndFrames"
                :key="'rally-' + rallyEnd.index"
                class="rally-end-marker"
                :class="{ 'at-position': isNearCurrentFrame(rallyEnd.index) }"
                :style="{ left: getMarkerPosition(rallyEnd.index) + '%' }"
                :title="`Rally ${rallyEnd.rallyNumber} End @ ${formatTime(rallyEnd.timestamp)}`"
                @click="goToFrameIndex(rallyEnd.index)"
              >
                <span v-if="isNearCurrentFrame(rallyEnd.index)" class="rally-end-tooltip">Rally {{ rallyEnd.rallyNumber }} End</span>
              </div>
            </template>
            <!-- Shuttle hit markers -->
            <template v-if="showHitMarkers">
              <div
                v-for="hit in shuttleHitMarkers"
                :key="'hit-' + hit.index"
                class="hit-marker"
                :class="{ 'at-position': isNearCurrentFrame(hit.index) }"
                :style="{ left: getMarkerPosition(hit.index) + '%' }"
                :title="`Shuttle Hit @ ${formatTime(hit.timestamp)}`"
                @click="goToFrameIndex(hit.index)"
              >
                <span v-if="isNearCurrentFrame(hit.index)" class="hit-tooltip">Hit</span>
              </div>
            </template>
            <!-- Manual hit markers -->
            <template v-if="showManualHitMarkers">
              <div
                v-for="hit in manualHitMarkers"
                :key="'manual-hit-' + hit.index"
                class="manual-hit-marker"
                :class="{ 'at-position': isNearCurrentFrame(hit.index) }"
                :style="{ left: getMarkerPosition(hit.index) + '%' }"
                :title="`Manual Hit @ ${formatTime(hit.timestamp)} (click to remove)`"
                @click="removeManualHit(hit.index)"
              >
                <span v-if="isNearCurrentFrame(hit.index)" class="manual-hit-tooltip">Manual</span>
              </div>
            </template>
            <!-- Manual shot label markers -->
            <template v-if="manualShotLabelMarkers.length > 0">
              <div
                v-for="label in manualShotLabelMarkers"
                :key="'label-' + label.index"
                class="shot-label-marker"
                :class="[getShotMarkerClass(label.type), { 'at-position': isNearCurrentFrame(label.index) }]"
                :style="{ left: getMarkerPosition(label.index) + '%' }"
                :title="`Manual: ${formatShotType(label.type)} @ ${formatTime(label.timestamp)}`"
                @click="goToFrameIndex(label.index)"
              >
                <span v-if="isNearCurrentFrame(label.index)" class="shot-label">{{ formatShotType(label.type) }}</span>
              </div>
            </template>
            <!-- Shot markers (filtered) -->
            <div
              v-for="shot in filteredShotFrames"
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

          <!-- Shuttle visibility strip -->
          <div v-if="showShuttleStrip && hasShuttleData" class="shuttle-visibility-strip">
            <canvas ref="shuttleStripCanvas" class="shuttle-strip-canvas" @click="handleStripClick"></canvas>
          </div>
        </div>
      </div>
      <button @click="nextFrame" :disabled="currentFrame >= frames.length - 1" class="nav-btn">
        &gt;
      </button>
      <button @click="goToEnd" :disabled="currentFrame >= frames.length - 1" class="nav-btn">
        &gt;|
      </button>
      <div class="action-buttons">
        <button
          @click="toggleManualHit"
          :class="['action-btn', 'mark-hit-btn', { active: manualHitFrameIndices.has(localFrame) }]"
          :title="manualHitFrameIndices.has(localFrame) ? 'Remove manual hit (H)' : 'Mark as hit (H)'"
        >
          {{ manualHitFrameIndices.has(localFrame) ? 'Unmark Hit' : 'Mark Hit' }}
        </button>
        <!-- Shot type label dropdown (always visible) -->
        <select
          :value="manualShotLabels.get(localFrame) || ''"
          @change="setManualShotLabel(localFrame, $event.target.value)"
          class="shot-label-select"
          title="Label shot type (S)"
        >
          <option value="">-- Label --</option>
          <option value="smash">Smash</option>
          <option value="clear">Clear</option>
          <option value="drop_shot">Drop</option>
          <option value="net_shot">Net</option>
          <option value="drive">Drive</option>
          <option value="lift">Lift</option>
          <option value="opponent_hit">Opponent</option>
        </select>
        <button @click="downloadRawData" class="action-btn download-btn" title="Download all frame data as JSON">
          Download Data
        </button>
      </div>
    </div>

    <!-- Shot Filter & Summary -->
    <div class="shot-summary-section">
      <!-- Toggleable Shot Type Filters -->
      <div v-if="Object.keys(allShotCounts).length > 0" class="shot-filters">
        <div class="filter-header">
          <h4>Shot Filters</h4>
          <button class="filter-toggle-all" @click="toggleAllFilters">
            {{ allFiltersEnabled ? 'None' : 'All' }}
          </button>
        </div>
        <div class="shot-counts-grid">
          <div
            v-for="(count, type) in allShotCounts"
            :key="type"
            class="shot-count-item"
            :class="[getShotClass(type), { disabled: !shotTypeFilter[type] }]"
            @click="toggleShotFilter(type)"
          >
            <span class="shot-count-value">{{ count }}</span>
            <span class="shot-count-label">{{ formatShotType(type) }}</span>
          </div>
        </div>
        <div class="total-shots">
          Showing: <strong>{{ filteredShotFrames.length }}</strong> / {{ allShotFrames.length }} shots
        </div>
      </div>

      <!-- Overlay toggles -->
      <div class="overlay-toggles">
        <div
          v-if="hasShuttleData"
          class="overlay-toggle"
          :class="{ active: showShuttleStrip }"
          @click="showShuttleStrip = !showShuttleStrip"
        >
          <span class="toggle-dot shuttle-dot"></span>
          Shuttle ({{ shuttleStats.detected }}/{{ shuttleStats.total }} frames)
        </div>
        <div
          v-if="rallyEndFrames.length > 0"
          class="overlay-toggle"
          :class="{ active: showRallyMarkers }"
          @click="showRallyMarkers = !showRallyMarkers"
        >
          <span class="toggle-dot rally-dot"></span>
          Rally Breaks ({{ rallyEndFrames.length }})
        </div>
        <div
          v-if="hasShuttleData && shuttleHitCount > 0"
          class="overlay-toggle"
          :class="{ active: showHitMarkers }"
          @click="showHitMarkers = !showHitMarkers"
        >
          <span class="toggle-dot hit-dot"></span>
          Shuttle Hits ({{ shuttleHitCount }})
        </div>
        <div
          v-if="manualHitCount > 0"
          class="overlay-toggle"
          :class="{ active: showManualHitMarkers }"
          @click="showManualHitMarkers = !showManualHitMarkers"
        >
          <span class="toggle-dot manual-hit-dot"></span>
          Manual Hits ({{ manualHitCount }})
        </div>
        <div
          v-if="manualShotLabelMarkers.length > 0"
          class="overlay-toggle active"
        >
          <span class="toggle-dot" style="background: #4ecca3; border: 1px solid #fff;"></span>
          Shot Labels ({{ manualShotLabelMarkers.length }})
        </div>
      </div>

      <!-- Timeline Legend -->
      <div v-if="filteredShotFrames.length > 0 || rallyEndFrames.length > 0" class="shot-legend">
        <span class="legend-label">Timeline:</span>
        <span v-for="type in enabledShotTypes" :key="type" class="legend-item">
          <span :class="['dot', getShotMarkerClass(type)]"></span>{{ formatShotType(type) }} ({{ allShotCounts[type] }})
        </span>
      </div>
    </div>

    <!-- Current Frame Data Panel -->
    <div class="data-panel">
      <div v-if="!currentFrameData?.player_detected" class="no-player">
        No player detected in this frame
      </div>

      <template v-else>
        <div class="metrics-grid">
          <!-- Col 1: Frame Info + Velocity -->
          <div class="metrics-col">
            <div class="metric-section">
              <h4>Frame</h4>
              <div class="metric-row">
                <span class="metric-label">Position:</span>
                <span class="metric-value">{{ localFrame + 1 }} <span class="dim">/ {{ frames.length }}</span></span>
              </div>
              <div class="metric-row">
                <span class="metric-label">Time:</span>
                <span class="metric-value">{{ formatTime(currentFrameData?.timestamp || 0) }}</span>
              </div>
              <div class="metric-row">
                <span class="metric-label">Frame #:</span>
                <span class="metric-value dim">{{ currentFrameData?.frame_number || 0 }}</span>
              </div>
            </div>

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
                <span class="metric-label">Dir:</span>
                <span class="metric-value direction">{{ currentFrameData.wrist_direction || '-' }}</span>
              </div>
            </div>
          </div>

          <!-- Col 2: Position + Classification -->
          <div class="metrics-col">
            <div class="metric-section">
              <h4>Position</h4>
              <div v-if="currentFrameData.wrist_y !== null" class="metric-row">
                <span class="metric-label">Wrist Y:</span>
                <span class="metric-value">{{ currentFrameData.wrist_y?.toFixed(3) }}</span>
              </div>
              <div v-if="currentFrameData.shoulder_y !== null" class="metric-row">
                <span class="metric-label">Shoulder:</span>
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
          </div>

          <!-- Col 3: Conditions + Shuttle -->
          <div class="metrics-col">
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

            <div v-if="currentFrameData.shuttle_visible !== undefined" class="metric-section">
              <h4>Shuttle</h4>
              <div class="metric-row">
                <span class="metric-label">Detected:</span>
                <span :class="['metric-value', { active: currentFrameData.shuttle_visible }]">
                  {{ currentFrameData.shuttle_visible ? 'Yes' : 'No' }}
                </span>
              </div>
              <template v-if="currentFrameData.shuttle_visible">
                <div class="metric-row">
                  <span class="metric-label">Pos:</span>
                  <span class="metric-value mono">{{ currentFrameData.shuttle_x }}, {{ currentFrameData.shuttle_y }}</span>
                </div>
                <div v-if="currentFrameData.shuttle_confidence" class="metric-row">
                  <span class="metric-label">Conf:</span>
                  <span class="metric-value">{{ currentFrameData.shuttle_confidence?.toFixed(3) }}</span>
                </div>
                <div v-if="currentFrameData.shuttle_speed != null" class="metric-row">
                  <span class="metric-label">Speed:</span>
                  <span class="metric-value">{{ currentFrameData.shuttle_speed }} px/s</span>
                </div>
                <div v-if="currentFrameData.shuttle_direction" class="metric-row">
                  <span class="metric-label">Dir:</span>
                  <span class="metric-value direction">{{ currentFrameData.shuttle_direction }}</span>
                </div>
                <div v-if="currentFrameData.shuttle_dx != null" class="metric-row">
                  <span class="metric-label">Vel:</span>
                  <span class="metric-value mono">dx={{ currentFrameData.shuttle_dx }} dy={{ currentFrameData.shuttle_dy }}</span>
                </div>
                <div v-if="currentFrameData.shuttle_is_hit" class="shuttle-hit-badge">
                  HIT DETECTED
                </div>
              </template>
            </div>

            <!-- Shot label info (when on a hit frame) -->
            <div v-if="isCurrentFrameHit" class="metric-section">
              <h4>Hit Classification</h4>
              <div v-if="currentFrameData.shot_type && currentFrameData.shuttle_hit_matched" class="metric-row">
                <span class="metric-label">Auto:</span>
                <span :class="['shot-badge small', getShotClass(currentFrameData.shot_type)]">
                  {{ formatShotType(currentFrameData.shot_type) }}
                </span>
              </div>
              <div v-if="currentFrameData.swing_type" class="metric-row">
                <span class="metric-label">Swing:</span>
                <span class="metric-value">{{ currentFrameData.swing_type }}</span>
              </div>
              <div v-if="manualShotLabels.has(localFrame)" class="metric-row">
                <span class="metric-label">Label:</span>
                <span :class="['shot-badge small', getShotClass(manualShotLabels.get(localFrame))]">
                  {{ formatShotType(manualShotLabels.get(localFrame)) }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </template>
    </div>

    <!-- Keyboard Shortcuts Help -->
    <div class="shortcuts-help">
      <span>← / → : Navigate frames</span>
      <span>Home / End : Jump to start/end</span>
      <span>H : Mark/unmark hit</span>
      <span>S : Focus shot label</span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'

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
      shuttle_gap_frames: 90,
      shuttle_gap_miss_pct: 80
    })
  },
  hitThresholds: {
    type: Object,
    default: () => ({
      hit_disp_window: 30,
      hit_speed_window: 8,
      hit_break_window: 8,
      hit_threshold: 0.15,
      hit_cooldown: 25
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

// Shuttle & rally overlay toggles
const shuttleStripCanvas = ref(null)
const showShuttleStrip = ref(true)
const showRallyMarkers = ref(true)
const showHitMarkers = ref(true)
const manualHitFrameIndices = ref(new Set())
const showManualHitMarkers = ref(true)
const manualShotLabels = ref(new Map())  // frameIndex → shot_type string

const hasShuttleData = computed(() => {
  return props.frames.some(f => f.shuttle_visible !== undefined)
})

const shuttleStats = computed(() => {
  let detected = 0
  let total = 0
  for (const f of props.frames) {
    if (f.shuttle_visible !== undefined) {
      total++
      if (f.shuttle_visible) detected++
    }
  }
  return { detected, total }
})

// Client-side multi-signal shuttle hit detection
const shuttleHitFrameIndices = computed(() => {
  const n = props.frames.length
  if (n === 0) return new Set()

  const dispW = props.hitThresholds?.hit_disp_window ?? 30
  const spdW = props.hitThresholds?.hit_speed_window ?? 8
  const brkW = props.hitThresholds?.hit_break_window ?? 8
  const threshold = props.hitThresholds?.hit_threshold ?? 0.15
  const cooldown = props.hitThresholds?.hit_cooldown ?? 25

  // --- Step 0: Build clean position arrays ---
  // Extract raw positions (frame index → {x, y} or null)
  const rawX = new Float64Array(n)
  const rawY = new Float64Array(n)
  const hasPos = new Uint8Array(n)
  for (let i = 0; i < n; i++) {
    const f = props.frames[i]
    if (f.shuttle_visible && f.shuttle_x != null && f.shuttle_y != null) {
      rawX[i] = f.shuttle_x
      rawY[i] = f.shuttle_y
      hasPos[i] = 1
    }
  }

  // Interpolate gaps up to 5 frames
  const interpX = Float64Array.from(rawX)
  const interpY = Float64Array.from(rawY)
  const valid = Uint8Array.from(hasPos)
  const MAX_GAP = 5
  let gapStart = -1
  for (let i = 0; i < n; i++) {
    if (hasPos[i]) {
      if (gapStart >= 0 && gapStart > 0 && hasPos[gapStart - 1]) {
        const gapLen = i - gapStart
        if (gapLen <= MAX_GAP) {
          const prevI = gapStart - 1
          for (let g = gapStart; g < i; g++) {
            const t = (g - prevI) / (i - prevI)
            interpX[g] = rawX[prevI] + t * (rawX[i] - rawX[prevI])
            interpY[g] = rawY[prevI] + t * (rawY[i] - rawY[prevI])
            valid[g] = 1
          }
        }
      }
      gapStart = -1
    } else {
      if (gapStart < 0) gapStart = i
    }
  }

  // Median-smooth with window=3
  const smoothX = new Float64Array(n)
  const smoothY = new Float64Array(n)
  for (let i = 0; i < n; i++) {
    if (!valid[i]) continue
    // Collect up to 3 valid neighbors centered on i
    const xVals = [], yVals = []
    for (let d = -1; d <= 1; d++) {
      const j = i + d
      if (j >= 0 && j < n && valid[j]) {
        xVals.push(interpX[j])
        yVals.push(interpY[j])
      }
    }
    xVals.sort((a, b) => a - b)
    yVals.sort((a, b) => a - b)
    const mid = Math.floor(xVals.length / 2)
    smoothX[i] = xVals[mid]
    smoothY[i] = yVals[mid]
  }

  // Compute velocity from smoothed positions: vx[i] = (x[i] - x[i-2]) / 2
  const vx = new Float64Array(n)
  const vy = new Float64Array(n)
  const speed = new Float64Array(n)
  for (let i = 2; i < n; i++) {
    if (!valid[i] || !valid[i - 2]) continue
    vx[i] = (smoothX[i] - smoothX[i - 2]) / 2
    vy[i] = (smoothY[i] - smoothY[i - 2]) / 2
    speed[i] = Math.sqrt(vx[i] * vx[i] + vy[i] * vy[i])
  }

  // --- Step 1: Signal A — Large-window net displacement cosine ---
  const signalA = new Float64Array(n)
  for (let i = 0; i < n; i++) {
    // Find first/last valid in [i-dispW, i] (before window)
    let bFirst = -1, bLast = -1
    for (let j = Math.max(0, i - dispW); j <= i; j++) {
      if (valid[j]) {
        if (bFirst < 0) bFirst = j
        bLast = j
      }
    }
    // Find first/last valid in [i, i+dispW] (after window)
    let aFirst = -1, aLast = -1
    for (let j = i; j <= Math.min(n - 1, i + dispW); j++) {
      if (valid[j]) {
        if (aFirst < 0) aFirst = j
        aLast = j
      }
    }
    const minSpan = Math.max(1, Math.floor(dispW / 3))
    if (bFirst < 0 || bLast < 0 || aFirst < 0 || aLast < 0) continue
    if ((bLast - bFirst) < minSpan || (aLast - aFirst) < minSpan) continue

    const bDx = smoothX[bLast] - smoothX[bFirst]
    const bDy = smoothY[bLast] - smoothY[bFirst]
    const aDx = smoothX[aLast] - smoothX[aFirst]
    const aDy = smoothY[aLast] - smoothY[aFirst]

    const bMag = Math.sqrt(bDx * bDx + bDy * bDy)
    const aMag = Math.sqrt(aDx * aDx + aDy * aDy)
    if (bMag < 1e-6 || aMag < 1e-6) continue

    const cosSim = (bDx * aDx + bDy * aDy) / (bMag * aMag)
    signalA[i] = Math.max(0, -cosSim)
  }

  // --- Step 2: Signal B — Speed ratio ---
  const signalB = new Float64Array(n)
  for (let i = 0; i < n; i++) {
    let beforeSum = 0, beforeCnt = 0
    for (let j = Math.max(0, i - spdW); j <= i; j++) {
      if (speed[j] > 0) { beforeSum += speed[j]; beforeCnt++ }
    }
    let afterSum = 0, afterCnt = 0
    for (let j = i + 1; j <= Math.min(n - 1, i + spdW); j++) {
      if (speed[j] > 0) { afterSum += speed[j]; afterCnt++ }
    }
    if (beforeCnt === 0 || afterCnt === 0) continue
    const beforeAvg = beforeSum / beforeCnt
    const afterAvg = afterSum / afterCnt
    if (beforeAvg < 1e-6 || afterAvg < 1e-6) continue
    const ratio = afterAvg > beforeAvg ? afterAvg / beforeAvg : beforeAvg / afterAvg
    signalB[i] = ratio - 1
  }

  // --- Step 3: Signal C — Trajectory break / prediction error ---
  const signalC = new Float64Array(n)
  const K = 5 // prediction horizon
  for (let i = brkW; i < n - K; i++) {
    // Collect positions in [i-brkW, i]
    const ts = [], xs = [], ys = []
    for (let j = i - brkW; j <= i; j++) {
      if (valid[j]) {
        ts.push(j)
        xs.push(smoothX[j])
        ys.push(smoothY[j])
      }
    }
    if (ts.length < 3) continue

    // Fit linear x(t): x = a*t + b using least squares
    let sumT = 0, sumT2 = 0, sumX = 0, sumTX = 0
    for (let k = 0; k < ts.length; k++) {
      const t = ts[k]
      sumT += t; sumT2 += t * t; sumX += xs[k]; sumTX += t * xs[k]
    }
    const nPts = ts.length
    const detX = nPts * sumT2 - sumT * sumT
    if (Math.abs(detX) < 1e-12) continue
    const aX = (nPts * sumTX - sumT * sumX) / detX
    const bX = (sumX - aX * sumT) / nPts

    // Fit quadratic y(t): y = a*t^2 + b*t + c using least squares
    let sT = 0, sT2 = 0, sT3 = 0, sT4 = 0, sY = 0, sTY = 0, sT2Y = 0
    for (let k = 0; k < ts.length; k++) {
      const t = ts[k]
      const t2 = t * t
      sT += t; sT2 += t2; sT3 += t * t2; sT4 += t2 * t2
      sY += ys[k]; sTY += t * ys[k]; sT2Y += t2 * ys[k]
    }
    // Solve 3x3 system: [n sT sT2; sT sT2 sT3; sT2 sT3 sT4] * [c b a] = [sY sTY sT2Y]
    const M = [
      [nPts, sT, sT2],
      [sT, sT2, sT3],
      [sT2, sT3, sT4]
    ]
    const rhs = [sY, sTY, sT2Y]
    // Gaussian elimination
    const aug = M.map((row, ri) => [...row, rhs[ri]])
    let singular = false
    for (let col = 0; col < 3; col++) {
      // Partial pivoting
      let maxRow = col
      for (let row = col + 1; row < 3; row++) {
        if (Math.abs(aug[row][col]) > Math.abs(aug[maxRow][col])) maxRow = row
      }
      [aug[col], aug[maxRow]] = [aug[maxRow], aug[col]]
      if (Math.abs(aug[col][col]) < 1e-12) { singular = true; break }
      for (let row = col + 1; row < 3; row++) {
        const factor = aug[row][col] / aug[col][col]
        for (let c = col; c < 4; c++) aug[row][c] -= factor * aug[col][c]
      }
    }
    if (singular) continue
    // Back-substitute
    const sol = [0, 0, 0]
    for (let row = 2; row >= 0; row--) {
      let s = aug[row][3]
      for (let col = row + 1; col < 3; col++) s -= aug[row][col] * sol[col]
      sol[row] = s / aug[row][row]
    }
    const cY = sol[0], bY = sol[1], aY = sol[2]

    // Predict positions at [i+1 ... i+K] and compute avg error
    let errSum = 0, errCnt = 0
    for (let k = 1; k <= K; k++) {
      const t = i + k
      if (t >= n || !valid[t]) continue
      const predX = aX * t + bX
      const predY = aY * t * t + bY * t + cY
      const dx = smoothX[t] - predX
      const dy = smoothY[t] - predY
      errSum += Math.sqrt(dx * dx + dy * dy)
      errCnt++
    }
    if (errCnt > 0) signalC[i] = errSum / errCnt
  }

  // --- Step 4: Normalize and combine ---
  // 95th-percentile normalization
  function normalize95(arr) {
    const vals = []
    for (let i = 0; i < arr.length; i++) {
      if (arr[i] > 0) vals.push(arr[i])
    }
    if (vals.length === 0) return new Float64Array(arr.length)
    vals.sort((a, b) => a - b)
    const p95 = vals[Math.min(vals.length - 1, Math.floor(vals.length * 0.95))]
    if (p95 < 1e-12) return new Float64Array(arr.length)
    const out = new Float64Array(arr.length)
    for (let i = 0; i < arr.length; i++) {
      out[i] = Math.min(1, arr[i] / p95)
    }
    return out
  }

  const normA = normalize95(signalA)
  const normB = normalize95(signalB)
  const normC = normalize95(signalC)

  // Weighted sum: 0.45 * displacement + 0.30 * speed + 0.25 * break
  const combined = new Float64Array(n)
  for (let i = 0; i < n; i++) {
    combined[i] = 0.45 * normA[i] + 0.30 * normB[i] + 0.25 * normC[i]
  }

  // --- Step 5: Peak detection with NMS ---
  const gapSet = gapFrameIndices.value
  // Collect candidates above threshold
  const candidates = []
  for (let i = 0; i < n; i++) {
    if (combined[i] >= threshold && !gapSet.has(i)) {
      candidates.push({ idx: i, score: combined[i] })
    }
  }
  // Sort by score descending
  candidates.sort((a, b) => b.score - a.score)

  // NMS with cooldown
  const result = new Set()
  const suppressed = new Uint8Array(n)
  for (const c of candidates) {
    if (suppressed[c.idx]) continue
    result.add(c.idx)
    // Suppress neighbors within cooldown
    for (let j = Math.max(0, c.idx - cooldown); j <= Math.min(n - 1, c.idx + cooldown); j++) {
      suppressed[j] = 1
    }
  }

  return result
})

const shuttleHitMarkers = computed(() => {
  const gapSet = gapFrameIndices.value
  const result = []
  for (const idx of shuttleHitFrameIndices.value) {
    if (gapSet.has(idx)) continue
    const f = props.frames[idx]
    if (f) {
      result.push({ index: idx, timestamp: f.timestamp || 0 })
    }
  }
  result.sort((a, b) => a.index - b.index)
  return result
})

const shuttleHitCount = computed(() => shuttleHitMarkers.value.length)

const manualHitMarkers = computed(() => {
  return Array.from(manualHitFrameIndices.value)
    .filter(idx => props.frames[idx])
    .map(idx => ({ index: idx, timestamp: props.frames[idx].timestamp || 0 }))
    .sort((a, b) => a.index - b.index)
})
const manualHitCount = computed(() => manualHitMarkers.value.length)

// Whether current frame is a detected or manual hit
const isCurrentFrameHit = computed(() => {
  return shuttleHitFrameIndices.value.has(localFrame.value) ||
    manualHitFrameIndices.value.has(localFrame.value)
})

// Manual shot label markers for the seek bar timeline
const manualShotLabelMarkers = computed(() => {
  return Array.from(manualShotLabels.value.entries())
    .filter(([idx]) => props.frames[idx])
    .map(([idx, type]) => ({
      index: idx,
      type,
      timestamp: props.frames[idx].timestamp || 0
    }))
    .sort((a, b) => a.index - b.index)
})

function setManualShotLabel(frameIndex, shotType) {
  const newMap = new Map(manualShotLabels.value)
  if (shotType) {
    newMap.set(frameIndex, shotType)
  } else {
    newMap.delete(frameIndex)
  }
  manualShotLabels.value = newMap
}

// Draw shuttle visibility strip on canvas
function drawShuttleStrip() {
  const canvas = shuttleStripCanvas.value
  if (!canvas || !props.frames.length) return

  const parent = canvas.parentElement
  if (!parent) return

  const width = parent.clientWidth
  const height = 8
  canvas.width = width
  canvas.height = height

  const ctx = canvas.getContext('2d')
  ctx.clearRect(0, 0, width, height)

  const n = props.frames.length
  if (n === 0) return

  const gapSet = gapFrameIndices.value

  // Draw per-pixel: each pixel covers a range of frames
  for (let px = 0; px < width; px++) {
    const startFrame = Math.floor((px / width) * n)
    const endFrame = Math.min(Math.floor(((px + 1) / width) * n), n)

    let visible = 0
    let total = 0
    let inGap = false
    for (let i = startFrame; i < endFrame; i++) {
      if (gapSet.has(i)) inGap = true
      if (props.frames[i].shuttle_visible !== undefined) {
        total++
        if (props.frames[i].shuttle_visible) visible++
      }
    }

    if (inGap) {
      // Gap zone — muted red with stripe pattern
      ctx.fillStyle = 'rgba(231, 76, 60, 0.4)'
    } else if (total === 0) {
      ctx.fillStyle = '#1a1a2e'
    } else {
      const ratio = visible / total
      if (ratio > 0.5) {
        ctx.fillStyle = `rgba(78, 204, 163, ${0.3 + ratio * 0.7})`
      } else {
        ctx.fillStyle = `rgba(231, 76, 60, ${0.2 + (1 - ratio) * 0.3})`
      }
    }
    ctx.fillRect(px, 0, 1, height)
  }

  // Draw hit markers as small yellow triangles (skip gap zones)
  if (showHitMarkers.value) {
    const hitSet = shuttleHitFrameIndices.value
    if (hitSet.size > 0) {
      ctx.fillStyle = '#ffd700'
      ctx.strokeStyle = '#b8960f'
      ctx.lineWidth = 0.5
      for (const idx of hitSet) {
        if (gapSet.has(idx)) continue
        const px = Math.round((idx / n) * width)
        // Small downward-pointing triangle
        ctx.beginPath()
        ctx.moveTo(px - 3, 0)
        ctx.lineTo(px + 3, 0)
        ctx.lineTo(px, height)
        ctx.closePath()
        ctx.fill()
        ctx.stroke()
      }
    }
  }

  // Draw manual hit markers as cyan upward triangles
  if (showManualHitMarkers.value && manualHitFrameIndices.value.size > 0) {
    ctx.fillStyle = '#00e5ff'
    ctx.strokeStyle = '#0097a7'
    ctx.lineWidth = 0.5
    for (const idx of manualHitFrameIndices.value) {
      const px = Math.round((idx / n) * width)
      ctx.beginPath()
      ctx.moveTo(px - 3, height)
      ctx.lineTo(px + 3, height)
      ctx.lineTo(px, 0)
      ctx.closePath()
      ctx.fill()
      ctx.stroke()
    }
  }
}

function handleStripClick(event) {
  const canvas = shuttleStripCanvas.value
  if (!canvas) return
  const rect = canvas.getBoundingClientRect()
  const x = event.clientX - rect.left
  const ratio = x / rect.width
  const frameIndex = Math.round(ratio * (props.frames.length - 1))
  goToFrameIndex(frameIndex)
}

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

// Shot type filter state - all enabled by default
const shotTypeFilter = ref({})

// Initialize filters when frames change
watch(() => props.frames, () => {
  // Reset filters to all enabled when new data loads
  const newFilter = {}
  for (const type of ACTUAL_SHOTS) {
    newFilter[type] = shotTypeFilter.value[type] !== undefined ? shotTypeFilter.value[type] : true
  }
  shotTypeFilter.value = newFilter
}, { immediate: true })

// Shuttle gap zone detection — zone-based, not rolling window.
// Mark every frame as "in gap" if any window covering it has >= miss_pct% missing.
// This produces continuous gap zones with no duplicate break markers.
const shuttleGapZones = computed(() => {
  const gapFrames = props.rallyThresholds?.shuttle_gap_frames ?? 90
  const missPct = (props.rallyThresholds?.shuttle_gap_miss_pct ?? 80) / 100
  const window = Math.max(1, gapFrames)
  const n = props.frames.length

  if (n === 0) return []
  const hasShuttle = props.frames.some(f => f.shuttle_visible !== undefined)
  if (!hasShuttle) return []

  // Step 1: Build gap mask
  const inGap = new Uint8Array(n) // 0 = not gap, 1 = gap
  for (let i = 0; i < n; i++) {
    const end = Math.min(i + window, n)
    const actual = end - i
    if (actual <= 0) continue
    let miss = 0
    for (let j = i; j < end; j++) {
      if (!props.frames[j].shuttle_visible) miss++
    }
    if (miss / actual >= missPct) {
      for (let j = i; j < end; j++) {
        inGap[j] = 1
      }
    }
  }

  // Step 2: Extract continuous gap zones
  const zones = []
  let i = 0
  while (i < n) {
    if (inGap[i]) {
      const start = i
      while (i < n && inGap[i]) i++
      zones.push({ startIdx: start, endIdx: i - 1 })
    } else {
      i++
    }
  }
  return zones
})

// Set of frame indices inside gap zones (for fast lookup)
const gapFrameIndices = computed(() => {
  const s = new Set()
  for (const gz of shuttleGapZones.value) {
    for (let i = gz.startIdx; i <= gz.endIdx; i++) {
      s.add(i)
    }
  }
  return s
})

// Rally end markers — one per gap zone boundary
const rallyEndFrames = computed(() => {
  return shuttleGapZones.value.map((gz, idx) => ({
    index: gz.startIdx,
    timestamp: props.frames[gz.startIdx]?.timestamp || 0,
    rallyNumber: idx + 1,
    endIndex: gz.endIdx
  }))
})

// All shot frames (unfiltered) — excludes cooldown, low-confidence, and gap zone frames
const allShotFrames = computed(() => {
  return props.frames
    .map((frame, index) => ({
      index,
      type: frame.shot_type,
      timestamp: frame.timestamp,
      confidence: frame.confidence || 0,
      cooldown: frame.cooldown_active || false,
      isHit: frame.shuttle_is_hit || false
    }))
    .filter(f =>
      ACTUAL_SHOTS.includes(f.type) &&
      !f.cooldown &&
      !gapFrameIndices.value.has(f.index) &&
      // Hit-centric shots (at shuttle hit frames) bypass confidence gate
      // since shuttle hit NMS already prevents duplicates
      (f.isHit || f.confidence > 0.5)
    )
})

// Filtered shot frames (respects toggle state)
const filteredShotFrames = computed(() => {
  return allShotFrames.value.filter(f => shotTypeFilter.value[f.type])
})

// Count all shots by type (unfiltered, for showing totals)
const allShotCounts = computed(() => {
  const counts = {}
  for (const shot of allShotFrames.value) {
    counts[shot.type] = (counts[shot.type] || 0) + 1
  }
  return counts
})

// Which shot types are currently enabled
const enabledShotTypes = computed(() => {
  return ACTUAL_SHOTS.filter(t => shotTypeFilter.value[t] && allShotCounts.value[t])
})

const allFiltersEnabled = computed(() => {
  return ACTUAL_SHOTS.every(t => !allShotCounts.value[t] || shotTypeFilter.value[t])
})

function toggleShotFilter(type) {
  shotTypeFilter.value[type] = !shotTypeFilter.value[type]
}

function toggleAllFilters() {
  const newState = !allFiltersEnabled.value
  for (const type of ACTUAL_SHOTS) {
    shotTypeFilter.value[type] = newState
  }
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

function toggleManualHit() {
  const idx = localFrame.value
  const newSet = new Set(manualHitFrameIndices.value)
  if (newSet.has(idx)) newSet.delete(idx)
  else newSet.add(idx)
  manualHitFrameIndices.value = newSet
}

function removeManualHit(index) {
  const newSet = new Set(manualHitFrameIndices.value)
  newSet.delete(index)
  manualHitFrameIndices.value = newSet
}

function downloadRawData() {
  const exportData = {
    export_timestamp: new Date().toISOString(),
    job_id: props.jobId,
    video_info: props.videoInfo,
    total_frames: props.frames.length,
    auto_detected_hits: {
      frame_indices: Array.from(shuttleHitFrameIndices.value).sort((a, b) => a - b),
      count: shuttleHitFrameIndices.value.size
    },
    manual_hits: {
      frame_indices: Array.from(manualHitFrameIndices.value).sort((a, b) => a - b),
      count: manualHitFrameIndices.value.size
    },
    manual_shot_labels: Object.fromEntries(
      Array.from(manualShotLabels.value.entries())
        .sort(([a], [b]) => a - b)
        .map(([idx, type]) => [idx, {
          frame_index: idx,
          frame_number: props.frames[idx]?.frame_number,
          timestamp: props.frames[idx]?.timestamp,
          shot_type: type
        }])
    ),
    rally_end_frames: rallyEndFrames.value.map(r => ({
      frame_index: r.index, timestamp: r.timestamp, rally_number: r.rallyNumber
    })),
    shot_detections: allShotFrames.value.map(s => ({
      frame_index: s.index, type: s.type, timestamp: s.timestamp, confidence: s.confidence
    })),
    shuttle_detections: props.frames
      .map((f, i) => ({ ...f, _index: i }))
      .filter(f => f.shuttle_visible)
      .map(f => ({
        frame_index: f._index,
        timestamp: f.timestamp,
        x: f.shuttle_x,
        y: f.shuttle_y,
        confidence: f.shuttle_confidence,
        speed: f.shuttle_speed,
        dx: f.shuttle_dx,
        dy: f.shuttle_dy,
        direction: f.shuttle_direction,
        is_hit: f.shuttle_is_hit || false
      })),
    frames: props.frames
  }
  const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `frame_data_${props.jobId || 'export'}_${Date.now()}.json`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
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
  } else if (event.key === 'h' || event.key === 'H') {
    event.preventDefault()
    toggleManualHit()
  } else if (event.key === 's' || event.key === 'S') {
    // Focus the shot label dropdown if on a hit frame
    if (isCurrentFrameHit.value) {
      event.preventDefault()
      const select = document.querySelector('.shot-label-select')
      if (select) select.focus()
    }
  }
}

onMounted(() => {
  window.addEventListener('keydown', handleKeydown)
  nextTick(drawShuttleStrip)
})

// Redraw shuttle strip when frames or toggle change
watch(() => props.frames, () => nextTick(drawShuttleStrip), { deep: false })
watch(showShuttleStrip, (v) => { if (v) nextTick(drawShuttleStrip) })
watch(() => props.rallyThresholds, () => nextTick(drawShuttleStrip), { deep: true })
watch(() => props.hitThresholds, () => nextTick(drawShuttleStrip), { deep: true })
watch(showHitMarkers, () => nextTick(drawShuttleStrip))
watch(manualHitFrameIndices, () => nextTick(drawShuttleStrip))
watch(showManualHitMarkers, () => nextTick(drawShuttleStrip))

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

/* Gap zone overlays on seek bar */
.gap-zone-overlay {
  position: absolute;
  top: -6px;
  height: 20px;
  background: rgba(231, 76, 60, 0.15);
  border-radius: 2px;
  pointer-events: none;
  z-index: 1;
}

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

/* Shuttle hit markers on seek bar — gold diamonds */
.hit-marker {
  position: absolute;
  top: -2px;
  width: 8px;
  height: 8px;
  background: #ffd700;
  transform: translateX(-50%) rotate(45deg);
  cursor: pointer;
  pointer-events: auto;
  opacity: 0.85;
  z-index: 4;
  transition: transform 0.15s, opacity 0.15s, box-shadow 0.15s;
}

.hit-marker:hover {
  transform: translateX(-50%) rotate(45deg) scale(1.3);
  opacity: 1;
  z-index: 10;
  box-shadow: 0 0 6px #ffd700;
}

.hit-marker.at-position {
  transform: translateX(-50%) rotate(45deg) scale(1.5);
  opacity: 1;
  z-index: 15;
  box-shadow: 0 0 10px #ffd700;
}

.hit-tooltip {
  position: absolute;
  bottom: 100%;
  left: 50%;
  transform: translateX(-50%) rotate(-45deg);
  font-size: 9px;
  font-weight: bold;
  color: #1a1a2e;
  white-space: nowrap;
  background: #ffd700;
  padding: 2px 6px;
  border-radius: 3px;
  margin-bottom: 6px;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.3);
}

/* Shuttle visibility strip below timeline */
.shuttle-visibility-strip {
  margin-top: 2px;
  height: 8px;
  border-radius: 2px;
  overflow: hidden;
}

.shuttle-strip-canvas {
  width: 100%;
  height: 8px;
  display: block;
  cursor: pointer;
  border-radius: 2px;
}

/* Overlay toggles (shuttle strip, rally markers) */
.overlay-toggles {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
  margin-bottom: 0.5rem;
}

.overlay-toggle {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.25rem 0.6rem;
  background: rgba(100, 100, 100, 0.15);
  border-radius: 4px;
  font-size: 0.72rem;
  color: #666;
  cursor: pointer;
  user-select: none;
  transition: all 0.15s;
}

.overlay-toggle:hover {
  background: rgba(100, 100, 100, 0.25);
}

.overlay-toggle.active {
  color: #ccc;
  background: rgba(100, 100, 100, 0.3);
}

.toggle-dot {
  width: 8px;
  height: 8px;
  border-radius: 2px;
}

.toggle-dot.shuttle-dot {
  background: #4ecca3;
}

.toggle-dot.rally-dot {
  background: transparent;
  border: 1px dashed #fff;
  width: 2px;
  height: 10px;
  border-radius: 0;
}

.toggle-dot.hit-dot {
  background: #ffd700;
  clip-path: polygon(50% 100%, 0 0, 100% 0);
}

.shot-summary-section {
  background: #1a1a2e;
  border-radius: 8px;
  padding: 0.75rem;
}

.filter-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.75rem;
}

.filter-header h4 {
  margin: 0;
  color: #4ecca3;
  font-size: 0.9rem;
}

.filter-toggle-all {
  background: #2a2a4a;
  border: none;
  color: #888;
  padding: 0.2rem 0.6rem;
  border-radius: 4px;
  font-size: 0.7rem;
  cursor: pointer;
  text-transform: uppercase;
}

.filter-toggle-all:hover {
  background: #3a3a5a;
  color: #eee;
}

.shot-filters h4 {
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
  cursor: pointer;
  transition: opacity 0.2s, transform 0.1s;
  user-select: none;
}

.shot-count-item:hover {
  transform: scale(1.05);
}

.shot-count-item.disabled {
  opacity: 0.3;
  filter: grayscale(1);
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

.data-panel {
  background: #1a1a2e;
  border-radius: 8px;
  padding: 0.5rem;
}

.metrics-grid {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 0.5rem;
}

@media (max-width: 900px) {
  .metrics-grid {
    grid-template-columns: 1fr 1fr;
  }
}

@media (max-width: 500px) {
  .metrics-grid {
    grid-template-columns: 1fr;
  }
}

.metrics-col {
  display: flex;
  flex-direction: column;
}

.no-player {
  text-align: center;
  color: #888;
  padding: 1rem;
  font-size: 0.8rem;
}

.metric-section {
  margin-bottom: 0.4rem;
  padding-bottom: 0.4rem;
  border-bottom: 1px solid #232342;
}

.metric-section:last-child {
  margin-bottom: 0;
  padding-bottom: 0;
  border-bottom: none;
}

.metric-section h4 {
  margin: 0 0 0.3rem;
  color: #666;
  font-size: 0.65rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.metric-row {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  margin-bottom: 0.2rem;
}

.metric-label {
  color: #888;
  font-size: 0.72rem;
  min-width: 52px;
}

.metric-value {
  color: #eee;
  font-size: 0.75rem;
}

.metric-value.mono {
  font-family: monospace;
  font-size: 0.72rem;
}

.metric-value .dim {
  color: #666;
  font-size: 0.7rem;
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
  gap: 0.3rem;
}

.metric-bar-container .metric-value {
  min-width: 36px;
  text-align: right;
  font-size: 0.7rem;
}

.metric-bar {
  height: 5px;
  background: linear-gradient(90deg, #4ecca3 0%, #3db892 100%);
  border-radius: 3px;
  min-width: 2px;
  transition: width 0.2s;
}

.metric-bar.body {
  background: linear-gradient(90deg, #3498db 0%, #2980b9 100%);
}

.classification-display {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.3rem;
}

.shot-badge {
  padding: 0.25rem 0.6rem;
  border-radius: 12px;
  font-weight: bold;
  text-transform: capitalize;
  font-size: 0.75rem;
}

.shot-badge.small {
  padding: 0.15rem 0.5rem;
  font-size: 0.7rem;
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
  font-size: 1rem;
  font-weight: bold;
  color: #4ecca3;
}

.reclassify-section {
  background: rgba(78, 204, 163, 0.1);
  border-radius: 6px;
  padding: 0.4rem;
  margin-top: 0.25rem;
}

.reclassify-comparison {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  flex-wrap: wrap;
}

.reclassify-comparison .label {
  color: #888;
  font-size: 0.68rem;
  margin-right: 0.15rem;
}

.arrow {
  color: #4ecca3;
  font-size: 0.9rem;
}

.changed-badge {
  display: inline-block;
  margin-top: 0.25rem;
  padding: 0.15rem 0.35rem;
  background: rgba(241, 196, 15, 0.2);
  color: #f1c40f;
  border-radius: 3px;
  font-size: 0.65rem;
  font-weight: bold;
}

.shuttle-hit-badge {
  display: inline-block;
  margin-top: 0.2rem;
  padding: 0.15rem 0.4rem;
  background: rgba(231, 76, 60, 0.3);
  color: #e74c3c;
  border-radius: 3px;
  font-size: 0.65rem;
  font-weight: bold;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.condition-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 0.3rem;
  margin-bottom: 0.3rem;
}

.condition-badge {
  padding: 0.15rem 0.35rem;
  background: rgba(100, 100, 100, 0.2);
  color: #666;
  border-radius: 3px;
  font-size: 0.65rem;
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
  border-radius: 3px;
  padding: 0.25rem 0.35rem;
  margin-top: 0.25rem;
}

.reason-text {
  font-size: 0.6rem;
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

/* Manual hit markers on seek bar — cyan circles */
.manual-hit-marker {
  position: absolute;
  top: -1px;
  width: 10px;
  height: 10px;
  background: #00e5ff;
  border-radius: 50%;
  transform: translateX(-50%);
  cursor: pointer;
  pointer-events: auto;
  opacity: 0.85;
  z-index: 4;
  transition: transform 0.15s, opacity 0.15s, box-shadow 0.15s;
}

.manual-hit-marker:hover {
  transform: translateX(-50%) scale(1.3);
  opacity: 1;
  z-index: 10;
  box-shadow: 0 0 6px #00e5ff;
}

.manual-hit-marker.at-position {
  transform: translateX(-50%) scale(1.5);
  opacity: 1;
  z-index: 15;
  box-shadow: 0 0 10px #00e5ff;
}

.manual-hit-tooltip {
  position: absolute;
  bottom: 100%;
  left: 50%;
  transform: translateX(-50%);
  font-size: 9px;
  font-weight: bold;
  color: #1a1a2e;
  white-space: nowrap;
  background: #00e5ff;
  padding: 2px 6px;
  border-radius: 3px;
  margin-bottom: 6px;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.3);
}

.toggle-dot.manual-hit-dot {
  background: #00e5ff;
  border-radius: 50%;
}

/* Action buttons (Mark Hit / Download Data) */
.action-buttons {
  display: flex;
  gap: 0.4rem;
  margin-left: 0.5rem;
}

.action-btn {
  padding: 0.3rem 0.7rem;
  background: #2a2a4a;
  border: 1px solid #3a3a5a;
  border-radius: 6px;
  color: #ccc;
  font-size: 0.72rem;
  cursor: pointer;
  white-space: nowrap;
  transition: background 0.2s, border-color 0.2s;
}

.action-btn:hover {
  background: #3a3a5a;
  border-color: #4a4a6a;
}

.mark-hit-btn.active {
  background: rgba(0, 229, 255, 0.2);
  border-color: #00e5ff;
  color: #00e5ff;
}

.download-btn:hover {
  background: rgba(78, 204, 163, 0.2);
  border-color: #4ecca3;
  color: #4ecca3;
}

/* Shot label dropdown */
/* Manual shot label markers on seek bar — like shot markers but with white border */
.shot-label-marker {
  position: absolute;
  top: -5px;
  width: 8px;
  height: 18px;
  border-radius: 2px;
  transform: translateX(-50%);
  cursor: pointer;
  pointer-events: auto;
  opacity: 0.95;
  transition: transform 0.15s, opacity 0.15s, box-shadow 0.15s;
  z-index: 6;
  border: 1.5px solid rgba(255, 255, 255, 0.8);
}

.shot-label-marker:hover {
  transform: translateX(-50%) scaleY(1.2);
  opacity: 1;
  z-index: 10;
}

.shot-label-marker.at-position {
  transform: translateX(-50%) scaleY(1.4);
  opacity: 1;
  z-index: 15;
  box-shadow: 0 0 8px currentColor;
}

.shot-label-select {
  padding: 0.25rem 0.4rem;
  background: #2a2a4a;
  border: 1px solid #3a3a5a;
  border-radius: 6px;
  color: #ccc;
  font-size: 0.72rem;
  cursor: pointer;
  outline: none;
  transition: border-color 0.2s;
}

.shot-label-select:focus {
  border-color: #4ecca3;
}

.shot-label-select option {
  background: #1a1a2e;
  color: #ccc;
}

</style>
