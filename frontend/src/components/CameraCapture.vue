<template>
  <div class="camera-capture">
    <!-- Camera Selection -->
    <div v-if="!streaming" class="camera-setup">
      <div class="camera-preview-container">
        <video ref="previewVideo" autoplay playsinline muted class="camera-preview"></video>
        <div v-if="!cameraReady" class="camera-placeholder">
          <svg class="camera-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"/>
          </svg>
          <p>{{ cameraError || 'Select a camera to start' }}</p>
        </div>
      </div>

      <div class="controls">
        <div class="control-group">
          <label>Camera</label>
          <select v-model="selectedCamera" @change="switchCamera" :disabled="cameras.length === 0">
            <option value="">Select camera...</option>
            <option v-for="camera in cameras" :key="camera.deviceId" :value="camera.deviceId">
              {{ camera.label || `Camera ${cameras.indexOf(camera) + 1}` }}
            </option>
          </select>
        </div>

        <div class="control-group">
          <label>Frame Rate</label>
          <div class="fps-options">
            <button
              v-for="option in fpsOptions"
              :key="option.fps"
              :class="['fps-btn', { active: selectedFps === option.fps }]"
              @click="selectedFps = option.fps"
            >
              {{ option.label }}
            </button>
          </div>
          <p class="fps-hint">{{ getFpsHint() }}</p>
        </div>

        <button
          @click="startStreaming"
          :disabled="!cameraReady"
          class="start-btn"
        >
          <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"/>
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
          </svg>
          Start Streaming
        </button>
      </div>
    </div>

    <!-- Active Streaming -->
    <div v-else class="streaming-active">
      <div class="video-container">
        <video ref="streamVideo" autoplay playsinline muted class="stream-video"></video>
        <canvas ref="overlayCanvas" class="overlay-canvas"></canvas>

        <div class="stream-badge">
          <span class="live-dot"></span>
          LIVE
        </div>

        <div class="fps-badge">{{ selectedFps }} FPS</div>
      </div>

      <div class="stream-controls">
        <button @click="stopStreaming" class="stop-btn">
          <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 10a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1v-4z"/>
          </svg>
          Stop Streaming
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, onBeforeUnmount } from 'vue'

const emit = defineEmits(['frame', 'stream-start', 'stream-stop', 'error'])

const props = defineProps({
  courtOverlay: {
    type: Object,
    default: null
  },
  poseData: {
    type: Object,
    default: null
  },
  showAnnotations: {
    type: Boolean,
    default: true
  },
  autoStart: {
    type: Boolean,
    default: false
  }
})

const previewVideo = ref(null)
const streamVideo = ref(null)
const overlayCanvas = ref(null)

const cameras = ref([])
const selectedCamera = ref('')
const cameraReady = ref(false)
const cameraError = ref('')
const streaming = ref(false)
const selectedFps = ref(10)

const fpsOptions = [
  { fps: 5, label: '5 FPS', quality: 0.6, desc: 'Low bandwidth' },
  { fps: 10, label: '10 FPS', quality: 0.7, desc: 'Recommended' },
  { fps: 15, label: '15 FPS', quality: 0.8, desc: 'Better accuracy' },
  { fps: 30, label: '30 FPS', quality: 0.85, desc: 'Best quality' }
]

let mediaStream = null
let captureInterval = null
let captureCanvas = null

onMounted(async () => {
  await loadCameras()
})

onUnmounted(() => {
  stopStreaming()
  if (mediaStream) {
    mediaStream.getTracks().forEach(track => track.stop())
  }
  if (animationFrame) {
    cancelAnimationFrame(animationFrame)
  }
})

async function loadCameras() {
  try {
    // Request permission first
    await navigator.mediaDevices.getUserMedia({ video: true })
      .then(stream => stream.getTracks().forEach(track => track.stop()))

    const devices = await navigator.mediaDevices.enumerateDevices()
    cameras.value = devices.filter(d => d.kind === 'videoinput')

    // Auto-select back camera on mobile, otherwise first camera
    if (cameras.value.length > 0) {
      // Try to find back camera (environment facing)
      const backCamera = cameras.value.find(cam =>
        cam.label.toLowerCase().includes('back') ||
        cam.label.toLowerCase().includes('rear') ||
        cam.label.toLowerCase().includes('environment')
      )

      // On mobile, prefer the last camera (usually back camera)
      const isMobile = /Android|iPhone|iPad|iPod/i.test(navigator.userAgent)
      if (backCamera) {
        selectedCamera.value = backCamera.deviceId
      } else if (isMobile && cameras.value.length > 1) {
        // On mobile with multiple cameras, last one is usually back camera
        selectedCamera.value = cameras.value[cameras.value.length - 1].deviceId
      } else {
        selectedCamera.value = cameras.value[0].deviceId
      }

      await switchCamera()

      // Auto-start if prop is set
      if (props.autoStart && cameraReady.value) {
        startStreaming()
      }
    }
  } catch (e) {
    cameraError.value = 'Camera access denied. Please allow camera access.'
    emit('error', cameraError.value)
  }
}

async function switchCamera() {
  if (!selectedCamera.value) return

  // Stop existing stream
  if (mediaStream) {
    mediaStream.getTracks().forEach(track => track.stop())
  }

  try {
    mediaStream = await navigator.mediaDevices.getUserMedia({
      video: {
        deviceId: { exact: selectedCamera.value },
        width: { ideal: 1280 },
        height: { ideal: 720 },
        facingMode: 'environment' // Prefer back camera on mobile
      }
    })

    const videoEl = streaming.value ? streamVideo.value : previewVideo.value
    if (videoEl) {
      videoEl.srcObject = mediaStream
    }

    cameraReady.value = true
    cameraError.value = ''
  } catch (e) {
    cameraError.value = 'Failed to access camera: ' + e.message
    cameraReady.value = false
    emit('error', cameraError.value)
  }
}

function startStreaming() {
  if (!cameraReady.value) {
    console.warn('CameraCapture: Cannot start streaming - camera not ready')
    return
  }

  console.log('CameraCapture: Starting streaming...')
  streaming.value = true

  // Wait for video element to be ready
  setTimeout(() => {
    if (streamVideo.value) {
      streamVideo.value.srcObject = mediaStream
      console.log('CameraCapture: Video element connected to media stream')
    } else {
      console.warn('CameraCapture: streamVideo ref is null')
    }

    // Setup capture canvas
    captureCanvas = document.createElement('canvas')

    // Start frame capture
    const fps = selectedFps.value
    const interval = 1000 / fps
    const quality = fpsOptions.find(o => o.fps === fps)?.quality || 0.7

    console.log(`CameraCapture: Starting frame capture at ${fps} FPS, quality ${quality}`)

    captureInterval = setInterval(() => {
      captureAndSendFrame(quality)
    }, interval)

    emit('stream-start', { fps, quality })
  }, 100)
}

let frameCount = 0

function captureAndSendFrame(quality) {
  const video = streamVideo.value
  if (!video || !captureCanvas) {
    if (frameCount === 0) console.warn('CameraCapture: video or canvas not ready')
    return
  }

  const width = video.videoWidth
  const height = video.videoHeight

  if (width === 0 || height === 0) {
    if (frameCount === 0) console.warn('CameraCapture: video dimensions are 0')
    return
  }

  captureCanvas.width = width
  captureCanvas.height = height

  const ctx = captureCanvas.getContext('2d')
  ctx.drawImage(video, 0, 0, width, height)

  // Convert to JPEG base64
  const dataUrl = captureCanvas.toDataURL('image/jpeg', quality)
  const base64Data = dataUrl.split(',')[1]

  frameCount++
  if (frameCount % 30 === 1) {
    console.log(`CameraCapture: Emitting frame #${frameCount}, ${width}x${height}, data size: ${base64Data?.length}`)
  }

  emit('frame', {
    data: base64Data,
    timestamp: Date.now() / 1000,
    width,
    height
  })
}

function stopStreaming() {
  if (captureInterval) {
    clearInterval(captureInterval)
    captureInterval = null
  }

  streaming.value = false
  emit('stream-stop')

  // Switch back to preview
  if (previewVideo.value && mediaStream) {
    previewVideo.value.srcObject = mediaStream
  }
}

function getFpsHint() {
  const option = fpsOptions.find(o => o.fps === selectedFps.value)
  return option?.desc || ''
}

// Animation frame for drawing
let animationFrame = null

// Draw pose skeleton on canvas
let drawCount = 0
function drawAnnotations() {
  drawCount++

  if (!overlayCanvas.value || !streaming.value) {
    if (drawCount <= 3) console.log('drawAnnotations early exit: canvas=', !!overlayCanvas.value, 'streaming=', streaming.value)
    return
  }

  const canvas = overlayCanvas.value
  const video = streamVideo.value
  if (!video || !video.srcObject) {
    if (drawCount <= 3) console.log('drawAnnotations: video not ready, srcObject=', !!video?.srcObject)
    if (streaming.value) {
      animationFrame = requestAnimationFrame(drawAnnotations)
    }
    return
  }

  if (video.videoWidth === 0 || video.videoHeight === 0) {
    if (drawCount <= 3) console.log('drawAnnotations: video dimensions 0')
    if (streaming.value) {
      animationFrame = requestAnimationFrame(drawAnnotations)
    }
    return
  }

  // Log once when we start drawing
  if (drawCount === 1 || (drawCount <= 10 && drawCount % 5 === 0)) {
    console.log('drawAnnotations drawing! canvas:', canvas.width, 'x', canvas.height, 'video:', video.videoWidth, 'x', video.videoHeight)
  }

  // Calculate actual video display area (accounting for object-fit: contain)
  const containerRect = video.parentElement.getBoundingClientRect()
  const videoAspect = video.videoWidth / video.videoHeight
  const containerAspect = containerRect.width / containerRect.height

  let displayWidth, displayHeight, offsetX, offsetY

  if (videoAspect > containerAspect) {
    // Video is wider - letterboxing top/bottom
    displayWidth = containerRect.width
    displayHeight = containerRect.width / videoAspect
    offsetX = 0
    offsetY = (containerRect.height - displayHeight) / 2
  } else {
    // Video is taller - letterboxing left/right
    displayHeight = containerRect.height
    displayWidth = containerRect.height * videoAspect
    offsetX = (containerRect.width - displayWidth) / 2
    offsetY = 0
  }

  // Set canvas internal size to match video native dimensions
  if (canvas.width !== video.videoWidth || canvas.height !== video.videoHeight) {
    canvas.width = video.videoWidth
    canvas.height = video.videoHeight
    console.log('Canvas resized to:', canvas.width, 'x', canvas.height)
  }

  // Position and size canvas to match actual video display area
  canvas.style.left = offsetX + 'px'
  canvas.style.top = offsetY + 'px'
  canvas.style.width = displayWidth + 'px'
  canvas.style.height = displayHeight + 'px'

  const ctx = canvas.getContext('2d')
  ctx.clearRect(0, 0, canvas.width, canvas.height)

  // Skip drawing if annotations are disabled
  if (!props.showAnnotations) {
    if (streaming.value) {
      animationFrame = requestAnimationFrame(drawAnnotations)
    }
    return
  }

  // Debug indicator - small green square in top-left to show canvas is rendering
  ctx.fillStyle = '#00ff00'
  ctx.fillRect(10, 10, 15, 15)

  // Draw court boundary
  const overlay = props.courtOverlay
  if (overlay && overlay.top_left) {
    ctx.strokeStyle = 'rgba(78, 204, 163, 0.7)'
    ctx.lineWidth = 2
    ctx.setLineDash([8, 4])
    ctx.beginPath()
    ctx.moveTo(overlay.top_left[0], overlay.top_left[1])
    ctx.lineTo(overlay.top_right[0], overlay.top_right[1])
    ctx.lineTo(overlay.bottom_right[0], overlay.bottom_right[1])
    ctx.lineTo(overlay.bottom_left[0], overlay.bottom_left[1])
    ctx.closePath()
    ctx.stroke()
    ctx.setLineDash([])
  }

  // Draw pose skeleton
  const pose = props.poseData
  if (pose && pose.landmarks && pose.landmarks.length > 0) {
    // Debug: log once when we first get pose data
    if (!window._poseLoggedOnce) {
      console.log('Drawing pose skeleton:', pose.landmarks.length, 'landmarks, canvas:', canvas.width, 'x', canvas.height, 'frame:', pose.width, 'x', pose.height)
      window._poseLoggedOnce = true
    }
    // Scale from original frame size to canvas display size
    const scaleX = canvas.width / pose.width
    const scaleY = canvas.height / pose.height

    // Define colors for different body parts (matching video upload style)
    const bodyPartColors = {
      // Connection colors by type
      connections: {
        torso: '#00ff00',      // Green - shoulders, hips
        leftArm: '#00ffff',    // Cyan - left arm
        rightArm: '#ffff00',   // Yellow - right arm
        leftLeg: '#ff00ff',    // Magenta - left leg
        rightLeg: '#ff66ff',   // Pink - right leg
      },
      // Landmark colors by index
      landmarks: {
        0: '#ffffff',   // Nose - white
        11: '#00ff96',  // Left shoulder - light green
        12: '#00ff96',  // Right shoulder - light green
        13: '#00ccff',  // Left elbow - light blue
        14: '#ffc800',  // Right elbow - orange
        15: '#00ffff',  // Left wrist - cyan
        16: '#ffff00',  // Right wrist - yellow
        23: '#00ff00',  // Left hip - green
        24: '#64ff00',  // Right hip - light green
        25: '#ff00ff',  // Left knee - magenta
        26: '#ff66ff',  // Right knee - pink
        27: '#8000ff',  // Left ankle - purple
        28: '#cc80ff',  // Right ankle - light purple
      }
    }

    // Categorize connections by body part
    const getConnectionColor = (i, j) => {
      // Torso connections
      if ((i === 11 && j === 12) || (i === 23 && j === 24) ||
          (i === 11 && j === 23) || (i === 12 && j === 24)) {
        return bodyPartColors.connections.torso
      }
      // Left arm
      if ((i === 11 && j === 13) || (i === 13 && j === 15)) {
        return bodyPartColors.connections.leftArm
      }
      // Right arm
      if ((i === 12 && j === 14) || (i === 14 && j === 16)) {
        return bodyPartColors.connections.rightArm
      }
      // Left leg
      if ((i === 23 && j === 25) || (i === 25 && j === 27)) {
        return bodyPartColors.connections.leftLeg
      }
      // Right leg
      if ((i === 24 && j === 26) || (i === 26 && j === 28)) {
        return bodyPartColors.connections.rightLeg
      }
      return '#00ff00' // Default green
    }

    // Draw connections (skeleton lines) with body-part specific colors
    ctx.lineWidth = 3
    ctx.lineCap = 'round'

    for (const [i, j] of pose.connections) {
      const p1 = pose.landmarks[i]
      const p2 = pose.landmarks[j]

      if (p1 && p2 && p1.visibility > 0.5 && p2.visibility > 0.5) {
        const color = getConnectionColor(i, j)
        ctx.strokeStyle = color
        ctx.shadowColor = color
        ctx.shadowBlur = 5
        ctx.beginPath()
        ctx.moveTo(p1.x * scaleX, p1.y * scaleY)
        ctx.lineTo(p2.x * scaleX, p2.y * scaleY)
        ctx.stroke()
      }
    }

    ctx.shadowBlur = 0

    // Draw landmarks (joints) with body-part specific colors
    pose.landmarks.forEach((lm, index) => {
      if (lm.visibility > 0.5) {
        const x = lm.x * scaleX
        const y = lm.y * scaleY
        const color = bodyPartColors.landmarks[index] || '#00ff00'

        // Outer glow
        ctx.beginPath()
        ctx.arc(x, y, 8, 0, Math.PI * 2)
        ctx.fillStyle = color.replace('#', 'rgba(') + ', 0.3)'.replace('rgba(', 'rgba(' +
          parseInt(color.slice(1, 3), 16) + ',' +
          parseInt(color.slice(3, 5), 16) + ',' +
          parseInt(color.slice(5, 7), 16) + ',')
        // Simpler approach for glow
        ctx.globalAlpha = 0.3
        ctx.fillStyle = color
        ctx.fill()
        ctx.globalAlpha = 1.0

        // Main circle
        ctx.beginPath()
        ctx.arc(x, y, 5, 0, Math.PI * 2)
        ctx.fillStyle = color
        ctx.fill()

        // White outline for visibility
        ctx.beginPath()
        ctx.arc(x, y, 6, 0, Math.PI * 2)
        ctx.strokeStyle = '#ffffff'
        ctx.lineWidth = 1
        ctx.stroke()

        // Inner dot
        ctx.beginPath()
        ctx.arc(x, y, 2, 0, Math.PI * 2)
        ctx.fillStyle = 'white'
        ctx.fill()
      }
    })
  }

  // Continue animation loop
  if (streaming.value) {
    animationFrame = requestAnimationFrame(drawAnnotations)
  }
}

// Start/stop animation loop with streaming
watch(streaming, (isStreaming) => {
  console.log('Streaming state changed:', isStreaming)
  if (isStreaming) {
    console.log('Starting annotation loop, canvas ref:', overlayCanvas.value)
    // Small delay to ensure video element is ready
    setTimeout(() => {
      console.log('Starting drawAnnotations, streamVideo:', streamVideo.value?.videoWidth, 'x', streamVideo.value?.videoHeight)
      drawAnnotations()
    }, 500)
  } else if (animationFrame) {
    cancelAnimationFrame(animationFrame)
    animationFrame = null
  }
})

// Redraw when pose data changes
watch(() => props.poseData, () => {
  // The animation loop will pick up the new pose data
}, { deep: true })
</script>

<style scoped>
.camera-capture {
  width: 100%;
}

.camera-setup {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.camera-preview-container {
  position: relative;
  width: 100%;
  aspect-ratio: 16/9;
  background: #0f0f1a;
  border-radius: 12px;
  overflow: hidden;
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
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #888;
  gap: 1rem;
}

.camera-icon {
  width: 48px;
  height: 48px;
}

.controls {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.control-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.control-group label {
  color: #888;
  font-size: 0.9rem;
}

.control-group select {
  padding: 0.75rem;
  background: #16213e;
  border: 1px solid #3a3a5a;
  border-radius: 8px;
  color: #eee;
  font-size: 1rem;
}

.fps-options {
  display: flex;
  gap: 0.5rem;
}

.fps-btn {
  flex: 1;
  padding: 0.5rem;
  background: #16213e;
  border: 1px solid #3a3a5a;
  border-radius: 6px;
  color: #888;
  cursor: pointer;
  transition: all 0.2s;
}

.fps-btn:hover {
  border-color: #4ecca3;
}

.fps-btn.active {
  background: rgba(78, 204, 163, 0.2);
  border-color: #4ecca3;
  color: #4ecca3;
}

.fps-hint {
  color: #666;
  font-size: 0.8rem;
  margin: 0;
}

.start-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 1rem;
  background: #4ecca3;
  color: #1a1a2e;
  border: none;
  border-radius: 8px;
  font-weight: bold;
  font-size: 1rem;
  cursor: pointer;
  transition: background 0.2s;
}

.start-btn:hover:not(:disabled) {
  background: #3db892;
}

.start-btn:disabled {
  background: #888;
  cursor: not-allowed;
}

.btn-icon {
  width: 24px;
  height: 24px;
}

.streaming-active {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.video-container {
  position: relative;
  width: 100%;
  aspect-ratio: 16/9;
  background: #0f0f1a;
  border-radius: 12px;
  overflow: hidden;
}

.stream-video {
  width: 100%;
  height: 100%;
  object-fit: contain;
  background: #0f0f1a;
}

.overlay-canvas {
  position: absolute;
  pointer-events: none;
  /* Positioned dynamically via JS to match video's object-fit: contain */
}

.stream-badge {
  position: absolute;
  top: 1rem;
  left: 1rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  background: rgba(231, 76, 60, 0.9);
  border-radius: 4px;
  color: white;
  font-weight: bold;
  font-size: 0.85rem;
}

.live-dot {
  width: 8px;
  height: 8px;
  background: white;
  border-radius: 50%;
  animation: pulse 1s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.fps-badge {
  position: absolute;
  top: 1rem;
  right: 1rem;
  padding: 0.5rem 1rem;
  background: rgba(0, 0, 0, 0.7);
  border-radius: 4px;
  color: #4ecca3;
  font-size: 0.85rem;
}

.stream-controls {
  display: flex;
  gap: 1rem;
}

.stop-btn {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 1rem;
  background: #e74c3c;
  color: white;
  border: none;
  border-radius: 8px;
  font-weight: bold;
  cursor: pointer;
  transition: background 0.2s;
}

.stop-btn:hover {
  background: #c0392b;
}
</style>
