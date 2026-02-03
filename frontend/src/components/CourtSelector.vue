<template>
  <div class="court-selector">
    <div class="instructions">
      <span v-if="points.length < 4">
        Click to select {{ pointLabels[points.length] }} ({{ points.length + 1 }}/4)
      </span>
      <span v-else class="complete">
        All points selected! Drag to adjust.
      </span>
      <button v-if="points.length > 0" @click="resetPoints" class="btn-reset">Reset</button>
    </div>

    <div class="canvas-wrapper" ref="canvasWrapper">
      <canvas
        ref="canvas"
        @click="handleClick"
        @mousemove="handleMouseMove"
        @mousedown="handleMouseDown"
        @mouseup="handleMouseUp"
      />
    </div>

    <div class="coordinates" v-if="points.length > 0">
      <div v-for="(point, index) in points" :key="index" class="coord-item">
        <span class="label" :style="{ color: colors[index] }">{{ pointLabels[index] }}:</span>
        <span class="value">({{ point.x }}, {{ point.y }})</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue'

const props = defineProps({
  imageUrl: {
    type: String,
    required: true
  },
  videoWidth: {
    type: Number,
    default: 0
  },
  videoHeight: {
    type: Number,
    default: 0
  }
})

const emit = defineEmits(['boundary-selected'])

const canvas = ref(null)
const canvasWrapper = ref(null)
const ctx = ref(null)
const image = ref(null)
const points = ref([])
const draggingIndex = ref(-1)
const mousePos = ref({ x: 0, y: 0 })
const scale = ref(1)
const offset = ref({ x: 0, y: 0 })

const pointLabels = ['Top-Left', 'Top-Right', 'Bottom-Right', 'Bottom-Left']
const colors = ['#2ecc71', '#f1c40f', '#e74c3c', '#3498db']

onMounted(() => {
  loadImage()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
})

watch(() => props.imageUrl, () => {
  loadImage()
})

function loadImage() {
  image.value = new Image()
  image.value.onload = () => {
    nextTick(() => {
      setupCanvas()
      draw()
    })
  }
  image.value.src = props.imageUrl
}

function setupCanvas() {
  if (!canvas.value || !canvasWrapper.value || !image.value) return

  const wrapper = canvasWrapper.value
  const maxWidth = wrapper.clientWidth
  const maxHeight = window.innerHeight * 0.6

  // Calculate scale to fit image in container
  const imgWidth = props.videoWidth || image.value.width
  const imgHeight = props.videoHeight || image.value.height

  const scaleX = maxWidth / imgWidth
  const scaleY = maxHeight / imgHeight
  scale.value = Math.min(scaleX, scaleY, 1)

  const displayWidth = imgWidth * scale.value
  const displayHeight = imgHeight * scale.value

  canvas.value.width = displayWidth
  canvas.value.height = displayHeight
  ctx.value = canvas.value.getContext('2d')

  // Center offset
  offset.value = {
    x: (maxWidth - displayWidth) / 2,
    y: 0
  }
}

function handleResize() {
  setupCanvas()
  draw()
}

function draw() {
  if (!ctx.value || !image.value) return

  const c = ctx.value
  const w = canvas.value.width
  const h = canvas.value.height

  // Clear
  c.clearRect(0, 0, w, h)

  // Draw image
  c.drawImage(image.value, 0, 0, w, h)

  // Draw crosshair at mouse position
  if (points.value.length < 4) {
    c.strokeStyle = 'rgba(255, 255, 255, 0.5)'
    c.lineWidth = 1
    c.setLineDash([5, 5])

    // Vertical line
    c.beginPath()
    c.moveTo(mousePos.value.x, 0)
    c.lineTo(mousePos.value.x, h)
    c.stroke()

    // Horizontal line
    c.beginPath()
    c.moveTo(0, mousePos.value.y)
    c.lineTo(w, mousePos.value.y)
    c.stroke()

    c.setLineDash([])
  }

  // Draw polygon
  if (points.value.length >= 2) {
    c.strokeStyle = '#4ecca3'
    c.lineWidth = 2
    c.beginPath()
    c.moveTo(points.value[0].x * scale.value, points.value[0].y * scale.value)

    for (let i = 1; i < points.value.length; i++) {
      c.lineTo(points.value[i].x * scale.value, points.value[i].y * scale.value)
    }

    if (points.value.length === 4) {
      c.closePath()

      // Fill with semi-transparent color
      c.fillStyle = 'rgba(78, 204, 163, 0.2)'
      c.fill()
    }

    c.stroke()
  }

  // Draw points
  points.value.forEach((point, index) => {
    const x = point.x * scale.value
    const y = point.y * scale.value

    // Outer circle
    c.beginPath()
    c.arc(x, y, 10, 0, Math.PI * 2)
    c.fillStyle = colors[index]
    c.fill()

    // Inner circle
    c.beginPath()
    c.arc(x, y, 6, 0, Math.PI * 2)
    c.fillStyle = '#fff'
    c.fill()

    // Label
    c.fillStyle = colors[index]
    c.font = 'bold 12px sans-serif'
    c.fillText(pointLabels[index], x + 15, y - 5)
  })

  // Show coordinates at cursor
  if (points.value.length < 4) {
    const realX = Math.round(mousePos.value.x / scale.value)
    const realY = Math.round(mousePos.value.y / scale.value)

    c.fillStyle = 'rgba(0, 0, 0, 0.7)'
    c.fillRect(mousePos.value.x + 10, mousePos.value.y - 25, 80, 20)
    c.fillStyle = '#fff'
    c.font = '12px monospace'
    c.fillText(`(${realX}, ${realY})`, mousePos.value.x + 15, mousePos.value.y - 10)
  }
}

function handleClick(event) {
  if (points.value.length >= 4) return

  const rect = canvas.value.getBoundingClientRect()
  const x = event.clientX - rect.left
  const y = event.clientY - rect.top

  // Convert to actual image coordinates
  const realX = Math.round(x / scale.value)
  const realY = Math.round(y / scale.value)

  points.value.push({ x: realX, y: realY })
  draw()

  if (points.value.length === 4) {
    emitBoundary()
  }
}

function handleMouseMove(event) {
  const rect = canvas.value.getBoundingClientRect()
  const x = event.clientX - rect.left
  const y = event.clientY - rect.top

  mousePos.value = { x, y }

  if (draggingIndex.value >= 0) {
    const realX = Math.round(x / scale.value)
    const realY = Math.round(y / scale.value)
    points.value[draggingIndex.value] = { x: realX, y: realY }
    emitBoundary()
  }

  draw()
}

function handleMouseDown(event) {
  if (points.value.length < 4) return

  const rect = canvas.value.getBoundingClientRect()
  const x = event.clientX - rect.left
  const y = event.clientY - rect.top

  // Check if clicking near a point
  for (let i = 0; i < points.value.length; i++) {
    const px = points.value[i].x * scale.value
    const py = points.value[i].y * scale.value
    const dist = Math.sqrt((x - px) ** 2 + (y - py) ** 2)

    if (dist < 15) {
      draggingIndex.value = i
      canvas.value.style.cursor = 'grabbing'
      break
    }
  }
}

function handleMouseUp() {
  draggingIndex.value = -1
  canvas.value.style.cursor = 'crosshair'
}

function resetPoints() {
  points.value = []
  emit('boundary-selected', null)
  draw()
}

function emitBoundary() {
  if (points.value.length !== 4) return

  const boundary = {
    top_left: [points.value[0].x, points.value[0].y],
    top_right: [points.value[1].x, points.value[1].y],
    bottom_right: [points.value[2].x, points.value[2].y],
    bottom_left: [points.value[3].x, points.value[3].y],
    court_color: 'green'
  }

  emit('boundary-selected', boundary)
}
</script>

<style scoped>
.court-selector {
  width: 100%;
}

.instructions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 1rem;
  background: #1a1a2e;
  border-radius: 8px;
  margin-bottom: 1rem;
  color: #888;
}

.instructions .complete {
  color: #4ecca3;
}

.btn-reset {
  background: transparent;
  border: 1px solid #e74c3c;
  color: #e74c3c;
  padding: 0.25rem 0.75rem;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.85rem;
  transition: all 0.2s;
}

.btn-reset:hover {
  background: #e74c3c;
  color: white;
}

.canvas-wrapper {
  display: flex;
  justify-content: center;
  background: #0a0a1a;
  border-radius: 8px;
  padding: 1rem;
  overflow: hidden;
}

canvas {
  cursor: crosshair;
  border-radius: 4px;
}

.coordinates {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0.5rem;
  margin-top: 1rem;
  padding: 1rem;
  background: #1a1a2e;
  border-radius: 8px;
}

.coord-item {
  display: flex;
  gap: 0.5rem;
  font-size: 0.85rem;
  font-family: monospace;
}

.coord-item .label {
  font-weight: bold;
}

.coord-item .value {
  color: #888;
}
</style>
