<template>
  <div class="live-annotation">
    <div class="annotation-header">
      <h3>Live Detection</h3>
      <div :class="['status-dot', { active: isActive }]"></div>
    </div>

    <!-- Current Shot Display -->
    <div class="current-shot-panel">
      <div v-if="currentShot" class="shot-display" :class="currentShot.type">
        <div class="shot-icon">
          <svg viewBox="0 0 24 24" fill="currentColor">
            <circle cx="12" cy="12" r="10"/>
          </svg>
        </div>
        <div class="shot-info">
          <div class="shot-name">{{ formatShotType(currentShot.type) }}</div>
          <div class="shot-confidence">{{ (currentShot.confidence * 100).toFixed(0) }}% confidence</div>
        </div>
        <div class="shot-time">{{ formatTime(currentShot.timestamp) }}</div>
      </div>
      <div v-else class="no-shot-display">
        <div class="pulse-ring"></div>
        <span>Analyzing...</span>
      </div>
    </div>

    <!-- Mini Court with Position (Single Court) -->
    <div class="mini-court-container">
      <div class="mini-court-label">Player Position</div>
      <div class="mini-court">
        <svg viewBox="0 0 200 260" class="court-svg">
          <!-- Court outline (single side) -->
          <rect x="10" y="10" width="180" height="240" fill="none" stroke="#3a5a3a" stroke-width="2"/>

          <!-- Short service line -->
          <line x1="10" y1="60" x2="190" y2="60" stroke="#3a5a3a" stroke-width="1"/>

          <!-- Center line (for service boxes) -->
          <line x1="100" y1="10" x2="100" y2="60" stroke="#3a5a3a" stroke-width="1"/>

          <!-- Doubles sidelines (inner) -->
          <line x1="30" y1="10" x2="30" y2="250" stroke="#3a5a3a" stroke-width="1" stroke-dasharray="4"/>
          <line x1="170" y1="10" x2="170" y2="250" stroke="#3a5a3a" stroke-width="1" stroke-dasharray="4"/>

          <!-- Net line at top -->
          <line x1="10" y1="10" x2="190" y2="10" stroke="#fff" stroke-width="3"/>
          <text x="100" y="7" text-anchor="middle" fill="#666" font-size="8">NET</text>

          <!-- Player position marker -->
          <circle
            v-if="playerPosition"
            :cx="playerPosition.x"
            :cy="playerPosition.y"
            r="10"
            fill="#4ecca3"
            class="player-marker"
          />
          <circle
            v-if="playerPosition"
            :cx="playerPosition.x"
            :cy="playerPosition.y"
            r="16"
            fill="none"
            stroke="#4ecca3"
            stroke-width="2"
            opacity="0.5"
            class="player-ring"
          />

          <!-- Position trail -->
          <polyline
            v-if="positionTrail.length > 1"
            :points="trailPoints"
            fill="none"
            stroke="#4ecca3"
            stroke-width="2"
            opacity="0.4"
          />
        </svg>
        <div v-if="!playerPosition" class="no-position">
          No player detected
        </div>
      </div>
    </div>

    <!-- Recent Shots Timeline -->
    <div class="shots-timeline">
      <div class="timeline-label">Recent Shots</div>
      <div class="timeline-container">
        <div
          v-for="(shot, index) in recentShots"
          :key="index"
          :class="['timeline-shot', shot.type]"
        >
          <div class="shot-dot"></div>
          <div class="shot-details">
            <span class="shot-type-name">{{ formatShotType(shot.type) }}</span>
            <span class="shot-ago">{{ getTimeAgo(shot.timestamp) }}</span>
          </div>
        </div>
        <div v-if="recentShots.length === 0" class="no-shots">
          No shots detected yet
        </div>
      </div>
    </div>

    <!-- Frame Counter -->
    <div class="frame-counter">
      <span class="counter-label">Frames:</span>
      <span class="counter-value">{{ framesProcessed }}</span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'

const props = defineProps({
  lastShot: {
    type: String,
    default: null
  },
  lastShotConfidence: {
    type: Number,
    default: 0
  },
  position: {
    type: Object,
    default: null
  },
  courtBoundary: {
    type: Object,
    default: null
  },
  framesProcessed: {
    type: Number,
    default: 0
  }
})

const currentShot = ref(null)
const recentShots = ref([])
const positionTrail = ref([])
const startTime = ref(Date.now())

const isActive = computed(() => props.framesProcessed > 0)

const playerPosition = computed(() => {
  if (!props.position || !props.courtBoundary) return null

  // Map real court coordinates to mini court (200x260 - single court)
  const court = props.courtBoundary
  const pos = props.position

  // Calculate relative position within court boundary
  const courtWidth = Math.abs(court.top_right[0] - court.top_left[0])
  const courtHeight = Math.abs(court.bottom_left[1] - court.top_left[1])

  if (courtWidth === 0 || courtHeight === 0) return null

  const relX = (pos.x - court.top_left[0]) / courtWidth
  const relY = (pos.y - court.top_left[1]) / courtHeight

  // Map to mini court coordinates (10-190 for x, 10-250 for y)
  // Net is at top (y=10), back of court at bottom (y=250)
  const miniX = 10 + relX * 180
  const miniY = 10 + relY * 240

  // Clamp to court bounds
  return {
    x: Math.max(10, Math.min(190, miniX)),
    y: Math.max(10, Math.min(250, miniY))
  }
})

const trailPoints = computed(() => {
  return positionTrail.value.map(p => `${p.x},${p.y}`).join(' ')
})

// Watch for new shots
watch(() => props.lastShot, (newShot) => {
  if (newShot) {
    const shotData = {
      type: newShot,
      confidence: props.lastShotConfidence,
      timestamp: Date.now()
    }
    currentShot.value = shotData
    recentShots.value.unshift(shotData)

    // Keep only last 5 shots
    if (recentShots.value.length > 5) {
      recentShots.value = recentShots.value.slice(0, 5)
    }
  }
})

// Watch for position updates
watch(playerPosition, (newPos) => {
  if (newPos) {
    positionTrail.value.push({ ...newPos })

    // Keep only last 20 positions for trail
    if (positionTrail.value.length > 20) {
      positionTrail.value = positionTrail.value.slice(-20)
    }
  }
})

function formatShotType(type) {
  if (!type) return ''
  return type.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

function formatTime(timestamp) {
  const elapsed = Math.floor((timestamp - startTime.value) / 1000)
  const mins = Math.floor(elapsed / 60)
  const secs = elapsed % 60
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

function getTimeAgo(timestamp) {
  const seconds = Math.floor((Date.now() - timestamp) / 1000)
  if (seconds < 5) return 'just now'
  if (seconds < 60) return `${seconds}s ago`
  const mins = Math.floor(seconds / 60)
  return `${mins}m ago`
}
</script>

<style scoped>
.live-annotation {
  background: #16213e;
  border-radius: 12px;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.annotation-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.annotation-header h3 {
  margin: 0;
  color: #eee;
  font-size: 1rem;
}

.status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #555;
}

.status-dot.active {
  background: #4ecca3;
  animation: pulse-dot 1.5s infinite;
}

@keyframes pulse-dot {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.7; transform: scale(1.2); }
}

/* Current Shot Panel */
.current-shot-panel {
  background: #0f0f1a;
  border-radius: 8px;
  padding: 1rem;
  min-height: 60px;
}

.shot-display {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.shot-icon {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.shot-icon svg {
  width: 24px;
  height: 24px;
}

.shot-display.smash .shot-icon { background: rgba(231, 76, 60, 0.2); color: #e74c3c; }
.shot-display.clear .shot-icon { background: rgba(46, 204, 113, 0.2); color: #2ecc71; }
.shot-display.drop_shot .shot-icon { background: rgba(243, 156, 18, 0.2); color: #f39c12; }
.shot-display.net_shot .shot-icon { background: rgba(52, 152, 219, 0.2); color: #3498db; }
.shot-display.drive .shot-icon { background: rgba(155, 89, 182, 0.2); color: #9b59b6; }
.shot-display.lift .shot-icon { background: rgba(26, 188, 156, 0.2); color: #1abc9c; }
.shot-display.serve .shot-icon { background: rgba(230, 126, 34, 0.2); color: #e67e22; }

.shot-info {
  flex: 1;
}

.shot-name {
  font-weight: bold;
  color: #eee;
  font-size: 1.1rem;
}

.shot-confidence {
  color: #4ecca3;
  font-size: 0.8rem;
}

.shot-time {
  color: #666;
  font-size: 0.8rem;
  font-family: monospace;
}

.no-shot-display {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  color: #555;
  font-style: italic;
}

.pulse-ring {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  border: 2px solid #4ecca3;
  animation: pulse-ring 1.5s infinite;
}

@keyframes pulse-ring {
  0% { transform: scale(0.8); opacity: 1; }
  100% { transform: scale(1.4); opacity: 0; }
}

/* Mini Court */
.mini-court-container {
  background: #0f0f1a;
  border-radius: 8px;
  padding: 0.75rem;
}

.mini-court-label {
  color: #888;
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 0.5rem;
}

.mini-court {
  position: relative;
  width: 100%;
  max-width: 150px;
  margin: 0 auto;
}

.court-svg {
  width: 100%;
  height: auto;
  background: #1a2a1a;
  border-radius: 4px;
}

.player-marker {
  filter: drop-shadow(0 0 4px #4ecca3);
}

.player-ring {
  animation: ring-pulse 1s infinite;
}

@keyframes ring-pulse {
  0%, 100% { opacity: 0.5; }
  50% { opacity: 0.2; }
}

.no-position {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #555;
  font-size: 0.75rem;
  font-style: italic;
}

/* Shots Timeline */
.shots-timeline {
  background: #0f0f1a;
  border-radius: 8px;
  padding: 0.75rem;
}

.timeline-label {
  color: #888;
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 0.5rem;
}

.timeline-container {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  max-height: 150px;
  overflow-y: auto;
}

.timeline-shot {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.25rem 0;
}

.shot-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.timeline-shot.smash .shot-dot { background: #e74c3c; }
.timeline-shot.clear .shot-dot { background: #2ecc71; }
.timeline-shot.drop_shot .shot-dot { background: #f39c12; }
.timeline-shot.net_shot .shot-dot { background: #3498db; }
.timeline-shot.drive .shot-dot { background: #9b59b6; }
.timeline-shot.lift .shot-dot { background: #1abc9c; }
.timeline-shot.serve .shot-dot { background: #e67e22; }

.shot-details {
  display: flex;
  justify-content: space-between;
  flex: 1;
  font-size: 0.8rem;
}

.shot-type-name {
  color: #ccc;
}

.shot-ago {
  color: #666;
}

.no-shots {
  color: #555;
  font-size: 0.8rem;
  font-style: italic;
  text-align: center;
  padding: 0.5rem;
}

/* Frame Counter */
.frame-counter {
  display: flex;
  justify-content: space-between;
  padding: 0.5rem;
  background: #0f0f1a;
  border-radius: 6px;
  font-size: 0.8rem;
}

.counter-label {
  color: #888;
}

.counter-value {
  color: #4ecca3;
  font-family: monospace;
}
</style>
