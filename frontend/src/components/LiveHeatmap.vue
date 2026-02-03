<template>
  <div class="live-heatmap">
    <h4>Movement Heatmap</h4>
    <div class="heatmap-container">
      <canvas ref="heatmapCanvas" class="heatmap-canvas"></canvas>

      <div v-if="positions.length === 0" class="no-data">
        <p>Waiting for position data...</p>
      </div>
    </div>

    <div class="heatmap-legend">
      <div class="legend-bar"></div>
      <div class="legend-labels">
        <span>Low</span>
        <span>High</span>
      </div>
    </div>

    <div class="heatmap-stats">
      <span>{{ positions.length }} positions recorded</span>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  positions: {
    type: Array,
    default: () => []
  },
  courtBoundary: {
    type: Object,
    default: null
  },
  width: {
    type: Number,
    default: 300
  },
  height: {
    type: Number,
    default: 200
  }
})

const heatmapCanvas = ref(null)
let updateTimer = null

onMounted(() => {
  drawHeatmap()

  // Update periodically
  updateTimer = setInterval(() => {
    drawHeatmap()
  }, 1000)
})

onUnmounted(() => {
  if (updateTimer) {
    clearInterval(updateTimer)
  }
})

watch(() => props.positions.length, () => {
  // Redraw on new positions (debounced via timer)
})

function drawHeatmap() {
  const canvas = heatmapCanvas.value
  if (!canvas) return

  const ctx = canvas.getContext('2d')
  const w = props.width
  const h = props.height

  canvas.width = w
  canvas.height = h

  // Clear canvas
  ctx.fillStyle = '#0f0f1a'
  ctx.fillRect(0, 0, w, h)

  if (!props.courtBoundary || props.positions.length === 0) {
    return
  }

  // Calculate transform from court coordinates to canvas coordinates
  const court = props.courtBoundary
  const courtMinX = Math.min(court.top_left[0], court.bottom_left[0])
  const courtMaxX = Math.max(court.top_right[0], court.bottom_right[0])
  const courtMinY = Math.min(court.top_left[1], court.top_right[1])
  const courtMaxY = Math.max(court.bottom_left[1], court.bottom_right[1])

  const courtW = courtMaxX - courtMinX
  const courtH = courtMaxY - courtMinY

  // Create heatmap grid
  const gridSize = 20
  const grid = new Array(gridSize).fill(0).map(() => new Array(gridSize).fill(0))

  // Accumulate positions into grid
  for (const pos of props.positions) {
    // Normalize position to 0-1
    const normX = (pos.x - courtMinX) / courtW
    const normY = (pos.y - courtMinY) / courtH

    // Map to grid cell
    const gridX = Math.floor(normX * gridSize)
    const gridY = Math.floor(normY * gridSize)

    if (gridX >= 0 && gridX < gridSize && gridY >= 0 && gridY < gridSize) {
      grid[gridY][gridX]++
    }
  }

  // Find max value for normalization
  let maxVal = 0
  for (let y = 0; y < gridSize; y++) {
    for (let x = 0; x < gridSize; x++) {
      maxVal = Math.max(maxVal, grid[y][x])
    }
  }

  if (maxVal === 0) return

  // Draw heatmap cells
  const cellW = w / gridSize
  const cellH = h / gridSize

  for (let y = 0; y < gridSize; y++) {
    for (let x = 0; x < gridSize; x++) {
      const value = grid[y][x] / maxVal
      if (value > 0) {
        ctx.fillStyle = getHeatColor(value)
        ctx.fillRect(x * cellW, y * cellH, cellW, cellH)
      }
    }
  }

  // Apply blur for smoother look
  ctx.filter = 'blur(4px)'
  ctx.drawImage(canvas, 0, 0)
  ctx.filter = 'none'

  // Draw court lines
  drawCourtLines(ctx, w, h)
}

function getHeatColor(value) {
  // Blue -> Cyan -> Green -> Yellow -> Red
  const r = Math.floor(255 * Math.min(1, value * 2))
  const g = Math.floor(255 * Math.min(1, (1 - value) * 2))
  const b = Math.floor(255 * Math.max(0, 0.5 - value))
  const a = 0.3 + value * 0.5

  return `rgba(${r}, ${g}, ${b}, ${a})`
}

function drawCourtLines(ctx, w, h) {
  ctx.strokeStyle = 'rgba(255, 255, 255, 0.5)'
  ctx.lineWidth = 1

  // Outer boundary
  ctx.strokeRect(5, 5, w - 10, h - 10)

  // Center line
  ctx.beginPath()
  ctx.moveTo(5, h / 2)
  ctx.lineTo(w - 5, h / 2)
  ctx.stroke()

  // Service line
  ctx.beginPath()
  ctx.moveTo(5, h / 3)
  ctx.lineTo(w - 5, h / 3)
  ctx.stroke()

  // Center vertical
  ctx.beginPath()
  ctx.moveTo(w / 2, 5)
  ctx.lineTo(w / 2, h - 5)
  ctx.stroke()
}
</script>

<style scoped>
.live-heatmap {
  background: #16213e;
  border-radius: 12px;
  padding: 1rem;
}

.live-heatmap h4 {
  margin: 0 0 0.75rem 0;
  color: #888;
  font-size: 0.9rem;
  font-weight: normal;
}

.heatmap-container {
  position: relative;
  width: 100%;
  aspect-ratio: 3/2;
  background: #0f0f1a;
  border-radius: 8px;
  overflow: hidden;
}

.heatmap-canvas {
  width: 100%;
  height: 100%;
}

.no-data {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #666;
  font-size: 0.9rem;
}

.heatmap-legend {
  margin-top: 0.75rem;
}

.legend-bar {
  height: 8px;
  background: linear-gradient(90deg, #0077ff, #00ffff, #00ff00, #ffff00, #ff0000);
  border-radius: 4px;
}

.legend-labels {
  display: flex;
  justify-content: space-between;
  margin-top: 0.25rem;
  font-size: 0.75rem;
  color: #888;
}

.heatmap-stats {
  margin-top: 0.5rem;
  text-align: center;
  font-size: 0.8rem;
  color: #666;
}
</style>
