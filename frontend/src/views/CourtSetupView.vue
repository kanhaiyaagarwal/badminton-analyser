<template>
  <div class="court-setup">
    <div class="header">
      <h1>Setup Court Boundary</h1>
      <p class="subtitle" v-if="!useEntireFrame">Click to select the 4 corners of the court</p>
      <p class="subtitle" v-else>Entire video frame will be analyzed</p>
    </div>

    <div v-if="loading" class="loading">Loading video frame...</div>

    <div v-else-if="error" class="error">
      {{ error }}
      <button @click="loadFrame" class="btn-retry">Retry</button>
    </div>

    <div v-else class="setup-container">
      <div class="canvas-container">
        <div v-if="useEntireFrame && frameUrl" class="entire-frame-preview">
          <img :src="frameUrl" alt="Video frame" class="frame-image" />
          <div class="entire-frame-overlay">
            <span>Entire frame will be analyzed</span>
          </div>
        </div>
        <CourtSelector
          v-else-if="frameUrl"
          :image-url="frameUrl"
          :video-width="videoInfo?.width"
          :video-height="videoInfo?.height"
          @boundary-selected="handleBoundarySelected"
        />
      </div>

      <div class="controls-panel">
        <div class="frame-mode-toggle">
          <label class="toggle-label">
            <input
              type="checkbox"
              v-model="useEntireFrame"
              @change="handleFrameModeChange"
            />
            <span class="toggle-text">Analyze entire frame</span>
          </label>
          <p class="toggle-hint">Skip court boundary selection</p>
        </div>

        <div class="timestamp-control">
          <label>Frame timestamp (seconds)</label>
          <input
            v-model.number="timestamp"
            type="number"
            min="0"
            :max="videoInfo?.duration || 0"
            step="0.5"
          />
          <button @click="loadFrame" class="btn-secondary">Load Frame</button>
        </div>

        <div class="video-info" v-if="videoInfo">
          <p>Resolution: {{ videoInfo.width }} x {{ videoInfo.height }}</p>
          <p>Duration: {{ videoInfo.duration?.toFixed(1) }}s</p>
          <p>FPS: {{ videoInfo.fps?.toFixed(1) }}</p>
        </div>

        <div class="speed-preset">
          <label>Analysis Speed</label>
          <select v-model="speedPreset">
            <option value="turbo">Turbo (fastest, no video output)</option>
            <option value="fast">Fast (lower accuracy)</option>
            <option value="balanced">Balanced (recommended)</option>
            <option value="accurate">Accurate (slower)</option>
          </select>
          <p class="preset-hint" v-if="speedPreset === 'turbo'">
            No annotated video will be generated
          </p>
        </div>

        <div class="tuning-option">
          <label class="toggle-label">
            <input
              type="checkbox"
              v-model="saveFrameData"
            />
            <span class="toggle-text">Enable tuning data</span>
          </label>
          <p class="toggle-hint">Save per-frame data for threshold tuning (admin)</p>
        </div>

        <div v-if="boundary && !useEntireFrame" class="boundary-preview">
          <h3>Selected Boundary</h3>
          <div class="coords">
            <p>Top-Left: ({{ boundary.top_left.join(', ') }})</p>
            <p>Top-Right: ({{ boundary.top_right.join(', ') }})</p>
            <p>Bottom-Left: ({{ boundary.bottom_left.join(', ') }})</p>
            <p>Bottom-Right: ({{ boundary.bottom_right.join(', ') }})</p>
          </div>
        </div>

        <div v-if="useEntireFrame && videoInfo" class="boundary-preview entire-frame-info">
          <h3>Entire Frame Mode</h3>
          <p>Full video resolution: {{ videoInfo.width }} x {{ videoInfo.height }}</p>
        </div>

        <button
          @click="startAnalysis"
          class="btn-start"
          :disabled="(!boundary && !useEntireFrame) || starting"
        >
          {{ starting ? 'Starting...' : 'Start Analysis' }}
        </button>

        <router-link to="/dashboard" class="btn-cancel">Cancel</router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '../api/client'
import { useJobsStore } from '../stores/jobs'
import CourtSelector from '../components/CourtSelector.vue'

const route = useRoute()
const router = useRouter()
const jobsStore = useJobsStore()

const jobId = parseInt(route.params.jobId)

const loading = ref(true)
const error = ref('')
const frameUrl = ref(null)
const videoInfo = ref(null)
const timestamp = ref(0)
const boundary = ref(null)
const speedPreset = ref('balanced')
const starting = ref(false)
const useEntireFrame = ref(false)
const saveFrameData = ref(false)

onMounted(() => {
  loadVideoInfo()
  loadFrame()
})

async function loadVideoInfo() {
  try {
    const response = await api.get(`/api/v1/court/video-info/${jobId}`)
    videoInfo.value = response.data
  } catch (err) {
    console.error('Failed to load video info', err)
  }
}

async function loadFrame() {
  loading.value = true
  error.value = ''

  try {
    const response = await api.post(
      `/api/v1/court/extract-frame/${jobId}?timestamp=${timestamp.value}`,
      {},
      { responseType: 'blob' }
    )

    // Revoke previous URL if exists
    if (frameUrl.value) {
      URL.revokeObjectURL(frameUrl.value)
    }

    frameUrl.value = URL.createObjectURL(response.data)

    // Get video info from headers
    const width = parseInt(response.headers['x-video-width'])
    const height = parseInt(response.headers['x-video-height'])
    const duration = parseFloat(response.headers['x-video-duration'])
    const fps = parseFloat(response.headers['x-video-fps'])

    if (width && height) {
      videoInfo.value = { width, height, duration, fps }
    }
  } catch (err) {
    error.value = err.response?.data?.detail || 'Failed to load video frame'
  } finally {
    loading.value = false
  }
}

function handleBoundarySelected(selectedBoundary) {
  boundary.value = selectedBoundary
}

function handleFrameModeChange() {
  // Clear manual boundary when switching to entire frame mode
  if (useEntireFrame.value) {
    boundary.value = null
  }
}

function getFullFrameBoundary() {
  // Create boundary that covers the entire video frame
  const width = videoInfo.value?.width || 1920
  const height = videoInfo.value?.height || 1080
  return {
    top_left: [0, 0],
    top_right: [width, 0],
    bottom_left: [0, height],
    bottom_right: [width, height],
    court_color: 'green'
  }
}

async function startAnalysis() {
  // Use full frame boundary or manual selection
  const analysisBoundary = useEntireFrame.value ? getFullFrameBoundary() : boundary.value
  if (!analysisBoundary) return

  starting.value = true
  error.value = ''

  try {
    // Pass the current timestamp so the same frame is used for heatmap backgrounds
    await jobsStore.startAnalysis(jobId, analysisBoundary, speedPreset.value, timestamp.value, saveFrameData.value)
    router.push('/dashboard')
  } catch (err) {
    error.value = err.response?.data?.detail || 'Failed to start analysis'
    starting.value = false
  }
}
</script>

<style scoped>
.court-setup {
  max-width: 1200px;
  margin: 0 auto;
}

.header {
  margin-bottom: 2rem;
}

h1 {
  color: #4ecca3;
  margin-bottom: 0.5rem;
}

.subtitle {
  color: #888;
}

.loading {
  text-align: center;
  padding: 3rem;
  color: #888;
}

.error {
  background: rgba(231, 76, 60, 0.2);
  color: #e74c3c;
  padding: 1rem;
  border-radius: 8px;
  display: flex;
  align-items: center;
  gap: 1rem;
}

.btn-retry {
  background: #e74c3c;
  color: white;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 4px;
  cursor: pointer;
}

.setup-container {
  display: grid;
  grid-template-columns: 1fr 300px;
  gap: 2rem;
}

.canvas-container {
  background: #16213e;
  border-radius: 12px;
  padding: 1rem;
  overflow: hidden;
}

.controls-panel {
  background: #16213e;
  border-radius: 12px;
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.timestamp-control label,
.speed-preset label {
  display: block;
  color: #888;
  margin-bottom: 0.5rem;
}

.timestamp-control input,
.speed-preset select {
  width: 100%;
  padding: 0.5rem;
  border: 2px solid #2a2a4a;
  border-radius: 6px;
  background: #1a1a2e;
  color: #eee;
  margin-bottom: 0.5rem;
}

.btn-secondary {
  width: 100%;
  padding: 0.5rem;
  background: #3a3a5a;
  color: #eee;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-secondary:hover {
  background: #4a4a6a;
}

.preset-hint {
  font-size: 0.75rem;
  color: #f39c12;
  margin-top: 0.25rem;
}

.video-info {
  background: #1a1a2e;
  padding: 1rem;
  border-radius: 6px;
}

.video-info p {
  color: #888;
  font-size: 0.9rem;
  margin-bottom: 0.25rem;
}

.boundary-preview {
  background: #1a1a2e;
  padding: 1rem;
  border-radius: 6px;
}

.boundary-preview h3 {
  color: #4ecca3;
  font-size: 0.9rem;
  margin-bottom: 0.5rem;
}

.coords p {
  color: #888;
  font-size: 0.8rem;
  font-family: monospace;
  margin-bottom: 0.25rem;
}

.btn-start {
  width: 100%;
  padding: 1rem;
  background: #4ecca3;
  color: #1a1a2e;
  border: none;
  border-radius: 8px;
  font-size: 1rem;
  font-weight: bold;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-start:hover:not(:disabled) {
  background: #3db892;
}

.btn-start:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-cancel {
  display: block;
  text-align: center;
  color: #888;
  text-decoration: none;
  padding: 0.75rem;
  border: 1px solid #3a3a5a;
  border-radius: 8px;
  transition: all 0.2s;
}

.btn-cancel:hover {
  border-color: #e74c3c;
  color: #e74c3c;
}

.frame-mode-toggle {
  background: #1a1a2e;
  padding: 1rem;
  border-radius: 6px;
  border: 2px solid #3a3a5a;
}

.toggle-label {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  cursor: pointer;
}

.toggle-label input[type="checkbox"] {
  width: 18px;
  height: 18px;
  accent-color: #4ecca3;
  cursor: pointer;
}

.toggle-text {
  color: #eee;
  font-weight: 500;
}

.toggle-hint {
  color: #888;
  font-size: 0.75rem;
  margin-top: 0.5rem;
  margin-left: 1.75rem;
}

.entire-frame-preview {
  position: relative;
  width: 100%;
}

.frame-image {
  width: 100%;
  height: auto;
  border-radius: 8px;
}

.entire-frame-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(78, 204, 163, 0.15);
  border: 3px dashed #4ecca3;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.entire-frame-overlay span {
  background: rgba(26, 26, 46, 0.9);
  color: #4ecca3;
  padding: 0.75rem 1.5rem;
  border-radius: 6px;
  font-weight: 500;
}

.entire-frame-info {
  background: rgba(78, 204, 163, 0.1);
  border: 1px solid #4ecca3;
}

.entire-frame-info p {
  color: #4ecca3;
  font-size: 0.85rem;
}

.tuning-option {
  background: #1a1a2e;
  padding: 1rem;
  border-radius: 6px;
  border: 1px solid #3a3a5a;
}

@media (max-width: 900px) {
  .setup-container {
    grid-template-columns: 1fr;
  }
}
</style>
