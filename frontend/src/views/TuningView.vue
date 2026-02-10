<template>
  <div class="tuning-view">
    <div class="header">
      <router-link to="/dashboard" class="back-link">Back to Dashboard</router-link>
      <h1>Tuning Dashboard</h1>
      <p class="subtitle">Fine-tune shot detection thresholds with real-time preview</p>
    </div>

    <div v-if="!isAdmin" class="not-admin">
      <p>Admin access required for tuning.</p>
    </div>

    <template v-else>
      <div class="tuning-layout">
        <!-- Row 1: Source Selection (full width) -->
        <div class="section source-section">
          <h2>Source</h2>
          <div class="source-row">
            <div class="source-tabs">
              <button
                :class="['tab', { active: sourceMode === 'video' }]"
                @click="sourceMode = 'video'"
              >
                Video
              </button>
              <button
                :class="['tab', { active: sourceMode === 'live' }]"
                @click="sourceMode = 'live'"
              >
                Live Stream
              </button>
            </div>

            <!-- Video Source -->
            <div v-if="sourceMode === 'video'" class="source-content">
              <div class="form-group-inline">
                <label>Job:</label>
                <select v-model="selectedJobId" @change="loadJobFrameData">
                  <option value="">-- Select a completed job --</option>
                  <option v-for="job in completedJobs" :key="job.id" :value="job.id">
                    {{ job.video_filename }} (Job #{{ job.id }})
                  </option>
                </select>
              </div>
              <div v-if="frameDataError" class="error-message">{{ frameDataError }}</div>
              <div v-if="loadingFrameData" class="loading">Loading video & frame data...</div>
            </div>

            <!-- Live Stream Source -->
            <div v-if="sourceMode === 'live'" class="source-content">
              <div v-if="loadingLiveSessions" class="loading">Loading active sessions...</div>
              <div v-else-if="liveSessions.length === 0" class="no-sessions">
                <p>No active streaming sessions.</p>
                <router-link to="/live" class="btn-secondary">Go to Live Stream</router-link>
              </div>
              <div v-else class="live-source-row">
                <div class="form-group-inline">
                  <label>Session:</label>
                  <select v-model="selectedLiveSessionId" @change="loadLiveSession">
                    <option value="">-- Select active session --</option>
                    <option v-for="session in liveSessions" :key="session.session_id" :value="session.session_id">
                      Session #{{ session.session_id }} ({{ session.total_shots }} shots, {{ session.frames_processed }} frames)
                    </option>
                  </select>
                </div>
                <div v-if="liveSessionStats" class="live-stats-inline">
                  <span>{{ liveSessionStats.frames_processed }} frames</span>
                  <span>{{ liveSessionStats.total_shots }} shots</span>
                  <span>{{ (liveSessionStats.player_detection_rate * 100).toFixed(0) }}% detect</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Row 2: Frame Viewer (full width) -->
        <div class="section viewer-section">
          <FrameViewer
            v-if="frameData && frameData.frames.length > 0"
            :frames="frameData.frames"
            :videoInfo="frameData.video_info"
            :currentFrame="currentFrameIndex"
            :reclassifyResults="reclassifyResults"
            :videoUrl="videoUrl"
            :jobId="selectedJobId"
            :rallyThresholds="rallyThresholds"
            :hitThresholds="hitThresholds"
            @frameChange="handleFrameChange"
          />
          <div v-else-if="!loadingFrameData" class="empty-viewer">
            <p>Select a job to view frame data</p>
          </div>
        </div>

        <!-- Row 3: Thresholds + Results side by side -->
        <div class="bottom-row">
          <!-- Threshold Controls -->
          <div class="section threshold-section">
            <div class="section-header">
              <h2>Thresholds</h2>
              <div class="preset-selector">
                <select v-model="selectedPresetId" @change="loadPreset">
                  <option value="">-- Custom --</option>
                  <option v-for="preset in presets" :key="preset.id" :value="preset.id">
                    {{ preset.name }} {{ preset.is_active ? '(Active)' : '' }}
                  </option>
                </select>
                <button @click="showSavePreset = true" class="btn-small" :disabled="!hasChanges">
                  Save As...
                </button>
              </div>
            </div>

            <div v-if="!thresholdSchema" class="loading-schema">
              <p>Loading threshold controls...</p>
              <p v-if="schemaError" class="error-text">{{ schemaError }}</p>
            </div>
            <template v-else>
              <ThresholdSliders
                :schema="thresholdSchema"
                :values="currentThresholds"
                @update="handleThresholdUpdate"
              />
            </template>

            <div v-if="hasChanges" class="apply-section">
              <button
                v-if="sourceMode === 'video'"
                @click="reclassify"
                class="btn-primary"
                :disabled="reclassifying || !selectedJobId"
              >
                {{ reclassifying ? 'Re-classifying...' : 'Apply & Re-classify' }}
              </button>
              <button
                v-else-if="sourceMode === 'live'"
                @click="updateLiveThresholds"
                class="btn-primary"
                :disabled="!selectedLiveSessionId"
              >
                Apply to Live Stream
              </button>
              <button @click="resetThresholds" class="btn-secondary">Reset</button>
            </div>
          </div>

          <!-- Results Comparison -->
          <div v-if="reclassifyResults" class="section results-section">
            <h2>Classification Changes</h2>
            <div class="results-summary">
              <div class="stat">
                <span class="value">{{ reclassifyResults.frames_changed }}</span>
                <span class="label">Frames Changed</span>
              </div>
              <div class="stat">
                <span class="value">{{ reclassifyResults.total_frames }}</span>
                <span class="label">Total Frames</span>
              </div>
            </div>

            <div class="distribution-comparison">
              <div class="distribution">
                <h4>Before</h4>
                <div v-for="(count, shot) in reclassifyResults.shot_distribution_before" :key="'before-'+shot" class="shot-count">
                  <span class="shot-type">{{ shot }}</span>
                  <span class="count">{{ count }}</span>
                </div>
              </div>
              <div class="distribution">
                <h4>After</h4>
                <div v-for="(count, shot) in reclassifyResults.shot_distribution_after" :key="'after-'+shot" class="shot-count">
                  <span class="shot-type">{{ shot }}</span>
                  <span class="count">{{ count }}</span>
                </div>
              </div>
            </div>

            <div v-if="reclassifyResults.comparison.length > 0" class="comparison-table">
              <h4>Changed Frames</h4>
              <table>
                <thead>
                  <tr>
                    <th>Frame</th>
                    <th>Time</th>
                    <th>Before</th>
                    <th>After</th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="change in reclassifyResults.comparison.slice(0, 20)"
                    :key="change.frame_number"
                    @click="goToFrame(change.frame_number)"
                    class="clickable"
                  >
                    <td>{{ change.frame_number }}</td>
                    <td>{{ formatTime(change.timestamp) }}</td>
                    <td>{{ change.before_shot }} ({{ (change.before_confidence * 100).toFixed(0) }}%)</td>
                    <td>{{ change.after_shot }} ({{ (change.after_confidence * 100).toFixed(0) }}%)</td>
                  </tr>
                </tbody>
              </table>
              <p v-if="reclassifyResults.comparison.length > 20" class="more-results">
                ...and {{ reclassifyResults.comparison.length - 20 }} more changes
              </p>
            </div>
          </div>
        </div>
      </div>

      <!-- Save Preset Modal -->
      <div v-if="showSavePreset" class="modal-overlay" @click="showSavePreset = false">
        <div class="modal-content" @click.stop>
          <h2>Save Preset</h2>
          <form @submit.prevent="savePreset">
            <div class="form-group">
              <label>Preset Name</label>
              <input v-model="newPresetName" type="text" placeholder="My Custom Preset" required />
            </div>
            <div class="form-group">
              <label>Description (optional)</label>
              <input v-model="newPresetDescription" type="text" placeholder="Description..." />
            </div>
            <div v-if="savePresetError" class="error-message">{{ savePresetError }}</div>
            <button type="submit" class="btn-primary" :disabled="savingPreset">
              {{ savingPreset ? 'Saving...' : 'Save Preset' }}
            </button>
            <button type="button" @click="showSavePreset = false" class="btn-secondary">
              Cancel
            </button>
          </form>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useAuthStore } from '../stores/auth'
import api from '../api/client'
import ThresholdSliders from '../components/ThresholdSliders.vue'
import FrameViewer from '../components/FrameViewer.vue'

const authStore = useAuthStore()
const isAdmin = computed(() => authStore.user?.is_admin)

// Source selection
const sourceMode = ref('video')
const selectedJobId = ref('')
const completedJobs = ref([])

// Live stream
const liveSessions = ref([])
const loadingLiveSessions = ref(false)
const selectedLiveSessionId = ref('')
const liveSessionStats = ref(null)

// Frame data
const frameData = ref(null)
const loadingFrameData = ref(false)
const frameDataError = ref('')
const currentFrameIndex = ref(0)
const videoUrl = ref(null)

// Presets
const presets = ref([])
const selectedPresetId = ref('')
const thresholdSchema = ref(null)
const schemaError = ref('')

// Current thresholds (editable)
const currentThresholds = ref({})
const originalThresholds = ref({})

// Re-classification
const reclassifying = ref(false)
const reclassifyResults = ref(null)

// Save preset modal
const showSavePreset = ref(false)
const newPresetName = ref('')
const newPresetDescription = ref('')
const savingPreset = ref(false)
const savePresetError = ref('')

// Computed
const hasChanges = computed(() => {
  return JSON.stringify(currentThresholds.value) !== JSON.stringify(originalThresholds.value)
})

// Rally detection thresholds for FrameViewer
const rallyThresholds = computed(() => ({
  shuttle_gap_frames: currentThresholds.value.shuttle_gap_frames ?? 90,
  shuttle_gap_miss_pct: currentThresholds.value.shuttle_gap_miss_pct ?? 80
}))

// Hit detection thresholds for FrameViewer
const hitThresholds = computed(() => ({
  hit_disp_window: currentThresholds.value.hit_disp_window ?? 30,
  hit_speed_window: currentThresholds.value.hit_speed_window ?? 8,
  hit_break_window: currentThresholds.value.hit_break_window ?? 8,
  hit_threshold: currentThresholds.value.hit_threshold ?? 0.15,
  hit_cooldown: currentThresholds.value.hit_cooldown ?? 25
}))

onMounted(async () => {
  if (isAdmin.value) {
    await Promise.all([
      loadJobs(),
      loadPresets(),
      loadSchema()
    ])
  }
})

// Watch for source mode changes
watch(sourceMode, async (newMode) => {
  if (newMode === 'live') {
    await loadLiveSessions()
  }
})

async function loadJobs() {
  try {
    const response = await api.get('/api/v1/analysis/jobs')
    // API returns { jobs: [...] } not just [...]
    const jobs = response.data.jobs || response.data || []
    completedJobs.value = jobs.filter(j => j.status === 'completed')
  } catch (err) {
    console.error('Failed to load jobs:', err)
  }
}

async function loadLiveSessions() {
  loadingLiveSessions.value = true
  try {
    const response = await api.get('/api/v1/tuning/live/sessions')
    liveSessions.value = response.data.active_sessions || []
  } catch (err) {
    console.error('Failed to load live sessions:', err)
    liveSessions.value = []
  } finally {
    loadingLiveSessions.value = false
  }
}

async function loadLiveSession() {
  if (!selectedLiveSessionId.value) {
    liveSessionStats.value = null
    return
  }

  try {
    const response = await api.get(`/api/v1/tuning/live/${selectedLiveSessionId.value}/thresholds`)
    liveSessionStats.value = response.data.stats

    // Load thresholds from the live session
    const sessionThresholds = response.data.thresholds
    if (sessionThresholds?.velocity_thresholds) {
      currentThresholds.value = {
        ...sessionThresholds.velocity_thresholds,
        shot_cooldown_seconds: sessionThresholds.shot_cooldown_seconds || 0.4
      }
      originalThresholds.value = { ...currentThresholds.value }
    }
  } catch (err) {
    console.error('Failed to load live session:', err)
    liveSessionStats.value = null
  }
}

async function updateLiveThresholds() {
  if (!selectedLiveSessionId.value) return

  try {
    const velocityThresholds = {}
    const velocityKeys = ['static', 'movement', 'power_overhead', 'gentle_overhead', 'drive', 'net_min', 'net_max', 'lift', 'smash_vs_clear']
    for (const key of velocityKeys) {
      if (currentThresholds.value[key] !== undefined) {
        velocityThresholds[key] = currentThresholds.value[key]
      }
    }

    // Extract position thresholds
    const positionThresholds = {}
    const positionKeys = ['overhead_offset', 'low_position_offset', 'arm_extension_min']
    for (const key of positionKeys) {
      if (currentThresholds.value[key] !== undefined) {
        positionThresholds[key] = currentThresholds.value[key]
      }
    }

    await api.post(`/api/v1/tuning/live/${selectedLiveSessionId.value}/update-thresholds`, {
      velocity_thresholds: velocityThresholds,
      position_thresholds: Object.keys(positionThresholds).length > 0 ? positionThresholds : null,
      shot_cooldown_seconds: currentThresholds.value.shot_cooldown_seconds || 0.4
    })

    // Update original to mark as saved
    originalThresholds.value = { ...currentThresholds.value }

    // Refresh stats
    await loadLiveSession()
  } catch (err) {
    console.error('Failed to update live thresholds:', err)
  }
}

async function loadPresets() {
  try {
    const response = await api.get('/api/v1/tuning/presets')
    presets.value = response.data.presets || []

    // If there's an active preset, select it
    if (response.data.active_preset_id) {
      selectedPresetId.value = response.data.active_preset_id
      await loadPreset()
    }
  } catch (err) {
    console.error('Failed to load presets:', err)
  }
}

async function loadSchema() {
  schemaError.value = ''
  try {
    const response = await api.get('/api/v1/tuning/schemas/badminton')
    // The API returns the schema object directly with categories array
    // Handle both {categories: [...]} and {schema: {categories: [...]}} structures
    const schemaData = response.data
    if (schemaData.categories) {
      thresholdSchema.value = schemaData
    } else if (schemaData.schema?.categories) {
      thresholdSchema.value = schemaData.schema
    } else {
      console.warn('Unexpected schema structure:', schemaData)
      thresholdSchema.value = schemaData
    }
    console.log('Loaded schema:', thresholdSchema.value)
    console.log('Schema categories:', thresholdSchema.value?.categories?.length || 0)

    // Load default thresholds
    const defaults = await api.get('/api/v1/tuning/presets/defaults')
    currentThresholds.value = extractFlatThresholds(defaults.data)
    originalThresholds.value = { ...currentThresholds.value }
    console.log('Loaded defaults:', currentThresholds.value)
  } catch (err) {
    console.error('Failed to load schema:', err)
    schemaError.value = err.response?.data?.detail || 'Failed to load threshold schema'
  }
}

async function loadPreset() {
  if (!selectedPresetId.value) {
    // Reset to defaults
    const defaults = await api.get('/api/v1/tuning/presets/defaults')
    currentThresholds.value = extractFlatThresholds(defaults.data)
    originalThresholds.value = { ...currentThresholds.value }
    return
  }

  try {
    const response = await api.get(`/api/v1/tuning/presets/${selectedPresetId.value}`)
    currentThresholds.value = extractFlatThresholds(response.data.thresholds)
    originalThresholds.value = { ...currentThresholds.value }
  } catch (err) {
    console.error('Failed to load preset:', err)
  }
}

async function loadJobFrameData() {
  if (!selectedJobId.value) {
    frameData.value = null
    videoUrl.value = null
    return
  }

  loadingFrameData.value = true
  frameDataError.value = ''

  // Revoke previous blob URL if exists
  if (videoUrl.value && videoUrl.value.startsWith('blob:')) {
    URL.revokeObjectURL(videoUrl.value)
    videoUrl.value = null
  }

  try {
    // Load frame data (no limit = get all frames)
    const response = await api.get(`/api/v1/tuning/jobs/${selectedJobId.value}/frame-data`)
    frameData.value = response.data
    currentFrameIndex.value = 0
    reclassifyResults.value = null

    // Load annotated video (with pose overlay) - backend re-encodes to H.264 if needed
    try {
      const videoResponse = await api.get(`/api/v1/tuning/jobs/${selectedJobId.value}/annotated-video`, {
        responseType: 'blob'
      })
      videoUrl.value = URL.createObjectURL(videoResponse.data)
      console.log('Loaded annotated video')
    } catch (videoErr) {
      console.warn('Failed to load annotated video:', videoErr)
      videoUrl.value = null
      // Don't fail the whole load - frame data is still useful without video
    }
  } catch (err) {
    console.error('Failed to load frame data:', err)
    frameDataError.value = err.response?.data?.detail || 'Failed to load frame data. The job may need to be re-run with frame data export enabled.'
    frameData.value = null
    videoUrl.value = null
  } finally {
    loadingFrameData.value = false
  }
}

function extractFlatThresholds(thresholds) {
  const flat = {}

  // Extract velocity thresholds
  const velocity = thresholds.velocity || {}
  for (const [key, val] of Object.entries(velocity)) {
    flat[key] = typeof val === 'object' ? val.value : val
  }

  // Extract cooldown
  const cooldown = thresholds.cooldown || {}
  for (const [key, val] of Object.entries(cooldown)) {
    flat[key] = typeof val === 'object' ? val.value : val
  }

  // Extract position
  const position = thresholds.position || {}
  for (const [key, val] of Object.entries(position)) {
    flat[key] = typeof val === 'object' ? val.value : val
  }

  // Extract rally
  const rally = thresholds.rally || {}
  for (const [key, val] of Object.entries(rally)) {
    flat[key] = typeof val === 'object' ? val.value : val
  }

  // Extract shuttle_hit
  const shuttleHit = thresholds.shuttle_hit || {}
  for (const [key, val] of Object.entries(shuttleHit)) {
    flat[key] = typeof val === 'object' ? val.value : val
  }

  return flat
}

function handleThresholdUpdate(key, value) {
  currentThresholds.value = {
    ...currentThresholds.value,
    [key]: value
  }
}

function resetThresholds() {
  currentThresholds.value = { ...originalThresholds.value }
  reclassifyResults.value = null
}

async function reclassify() {
  if (!selectedJobId.value) return

  reclassifying.value = true

  try {
    // Extract velocity thresholds
    const velocityThresholds = {}
    const velocityKeys = ['static', 'movement', 'power_overhead', 'gentle_overhead', 'drive', 'net_min', 'net_max', 'lift', 'smash_vs_clear']
    for (const key of velocityKeys) {
      if (currentThresholds.value[key] !== undefined) {
        velocityThresholds[key] = currentThresholds.value[key]
      }
    }

    // Extract position thresholds
    const positionThresholds = {}
    const positionKeys = ['overhead_offset', 'low_position_offset', 'arm_extension_min']
    for (const key of positionKeys) {
      if (currentThresholds.value[key] !== undefined) {
        positionThresholds[key] = currentThresholds.value[key]
      }
    }

    const response = await api.post(`/api/v1/tuning/jobs/${selectedJobId.value}/reclassify`, {
      velocity_thresholds: velocityThresholds,
      position_thresholds: Object.keys(positionThresholds).length > 0 ? positionThresholds : null,
      shot_cooldown_seconds: currentThresholds.value.shot_cooldown_seconds || 0.4
    })

    reclassifyResults.value = response.data

    // Update frame data with new classifications
    if (frameData.value && response.data.results) {
      const resultsMap = new Map()
      for (const result of response.data.results) {
        resultsMap.set(result.frame_number, result)
      }

      // Update each frame with new classification
      frameData.value.frames = frameData.value.frames.map(frame => {
        const result = resultsMap.get(frame.frame_number)
        if (result && result.player_detected) {
          return {
            ...frame,
            shot_type: result.new_shot_type,
            confidence: result.new_confidence,
            cooldown_active: result.cooldown_active || false
          }
        }
        return frame
      })

      console.log(`Updated ${response.data.frames_changed} frame classifications`)
    }
  } catch (err) {
    console.error('Failed to reclassify:', err)
  } finally {
    reclassifying.value = false
  }
}

async function savePreset() {
  if (!newPresetName.value.trim()) return

  savingPreset.value = true
  savePresetError.value = ''

  try {
    // Build nested threshold structure
    const thresholds = {
      velocity: {},
      cooldown: {},
      position: {}
    }

    const velocityKeys = ['static', 'movement', 'power_overhead', 'gentle_overhead', 'drive', 'net_min', 'net_max', 'lift', 'smash_vs_clear']
    for (const key of velocityKeys) {
      if (currentThresholds.value[key] !== undefined) {
        thresholds.velocity[key] = { value: currentThresholds.value[key] }
      }
    }

    if (currentThresholds.value.shot_cooldown_seconds !== undefined) {
      thresholds.cooldown.shot_cooldown_seconds = { value: currentThresholds.value.shot_cooldown_seconds }
    }

    // Position thresholds
    const positionKeys = ['overhead_offset', 'low_position_offset', 'arm_extension_min']
    for (const key of positionKeys) {
      if (currentThresholds.value[key] !== undefined) {
        thresholds.position[key] = { value: currentThresholds.value[key] }
      }
    }

    await api.post('/api/v1/tuning/presets', {
      name: newPresetName.value,
      description: newPresetDescription.value || null,
      activity_type: 'badminton',
      thresholds
    })

    showSavePreset.value = false
    newPresetName.value = ''
    newPresetDescription.value = ''
    await loadPresets()
  } catch (err) {
    savePresetError.value = err.response?.data?.detail || 'Failed to save preset'
  } finally {
    savingPreset.value = false
  }
}

function handleFrameChange(index) {
  currentFrameIndex.value = index
}

function goToFrame(frameNumber) {
  if (!frameData.value) return
  const index = frameData.value.frames.findIndex(f => f.frame_number === frameNumber)
  if (index >= 0) {
    currentFrameIndex.value = index
  }
}

function formatTime(seconds) {
  const mins = Math.floor(seconds / 60)
  const secs = (seconds % 60).toFixed(1)
  return `${mins}:${secs.padStart(4, '0')}`
}
</script>

<style scoped>
.tuning-view {
  max-width: 1600px;
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

h1 {
  color: #4ecca3;
  margin: 0.5rem 0 0.25rem;
}

.subtitle {
  color: #888;
  margin: 0;
}

.not-admin {
  text-align: center;
  padding: 3rem;
  color: #888;
}

.tuning-layout {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.bottom-row {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.section {
  background: #16213e;
  border-radius: 12px;
  padding: 1rem;
}

.section h2 {
  color: #eee;
  margin: 0 0 0.75rem;
  font-size: 1rem;
}

.threshold-section {
  padding: 0.75rem;
}

.threshold-section h2 {
  margin-bottom: 0.5rem;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.section-header h2 {
  margin: 0;
}

.source-row {
  display: flex;
  align-items: center;
  gap: 1rem;
  flex-wrap: wrap;
}

.source-tabs {
  display: flex;
  gap: 0.5rem;
}

.tab {
  flex: 1;
  padding: 0.75rem;
  background: #1a1a2e;
  border: 1px solid #2a2a4a;
  color: #888;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.tab:hover {
  border-color: #4ecca3;
  color: #eee;
}

.tab.active {
  background: rgba(78, 204, 163, 0.1);
  border-color: #4ecca3;
  color: #4ecca3;
}

.form-group {
  margin-bottom: 1rem;
}

.form-group label {
  display: block;
  color: #888;
  margin-bottom: 0.5rem;
  font-size: 0.9rem;
}

.form-group select,
.form-group input {
  width: 100%;
  padding: 0.75rem;
  background: #1a1a2e;
  border: 1px solid #2a2a4a;
  border-radius: 8px;
  color: #eee;
}

.form-group-inline {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.form-group-inline label {
  color: #888;
  font-size: 0.9rem;
  white-space: nowrap;
}

.form-group-inline select {
  padding: 0.5rem 0.75rem;
  background: #1a1a2e;
  border: 1px solid #2a2a4a;
  border-radius: 8px;
  color: #eee;
  min-width: 250px;
}

.live-source-row {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.live-stats-inline {
  display: flex;
  gap: 1rem;
  font-size: 0.85rem;
  color: #888;
}

.live-stats-inline span {
  color: #4ecca3;
}

.preset-selector {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.preset-selector select {
  flex: 1;
  padding: 0.5rem;
  background: #1a1a2e;
  border: 1px solid #2a2a4a;
  border-radius: 6px;
  color: #eee;
  max-width: 200px;
}

.btn-small {
  padding: 0.5rem 1rem;
  background: #2a2a4a;
  border: none;
  color: #eee;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.85rem;
  white-space: nowrap;
}

.btn-small:hover:not(:disabled) {
  background: #3a3a5a;
}

.btn-small:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.apply-section {
  display: flex;
  gap: 0.75rem;
  margin-top: 1.5rem;
  padding-top: 1rem;
  border-top: 1px solid #2a2a4a;
}

.btn-primary {
  flex: 1;
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
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-secondary {
  padding: 0.75rem 1rem;
  background: transparent;
  border: 1px solid #3a3a5a;
  color: #888;
  border-radius: 8px;
  cursor: pointer;
}

.btn-secondary:hover {
  border-color: #4ecca3;
  color: #eee;
}

.empty-viewer {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 300px;
  background: #1a1a2e;
  border-radius: 8px;
  color: #888;
}

.results-summary {
  display: flex;
  gap: 2rem;
  margin-bottom: 1.5rem;
}

.stat {
  display: flex;
  flex-direction: column;
}

.stat .value {
  font-size: 2rem;
  font-weight: bold;
  color: #4ecca3;
}

.stat .label {
  color: #888;
  font-size: 0.85rem;
}

.distribution-comparison {
  display: flex;
  gap: 2rem;
  margin-bottom: 1.5rem;
}

.distribution {
  flex: 1;
}

.distribution h4 {
  color: #888;
  margin: 0 0 0.5rem;
  font-size: 0.85rem;
  text-transform: uppercase;
}

.shot-count {
  display: flex;
  justify-content: space-between;
  padding: 0.25rem 0;
  border-bottom: 1px solid #2a2a4a;
}

.shot-type {
  color: #eee;
  text-transform: capitalize;
}

.count {
  color: #4ecca3;
  font-weight: bold;
}

.comparison-table {
  margin-top: 1rem;
}

.comparison-table h4 {
  color: #888;
  margin: 0 0 0.75rem;
  font-size: 0.85rem;
  text-transform: uppercase;
}

.comparison-table table {
  width: 100%;
  border-collapse: collapse;
}

.comparison-table th,
.comparison-table td {
  padding: 0.5rem;
  text-align: left;
  border-bottom: 1px solid #2a2a4a;
}

.comparison-table th {
  color: #888;
  font-weight: normal;
  font-size: 0.8rem;
}

.comparison-table td {
  color: #eee;
  font-size: 0.9rem;
}

.comparison-table tr.clickable {
  cursor: pointer;
}

.comparison-table tr.clickable:hover {
  background: rgba(78, 204, 163, 0.1);
}

.more-results {
  color: #888;
  font-size: 0.85rem;
  text-align: center;
  margin-top: 0.5rem;
}

.error-message {
  background: rgba(231, 76, 60, 0.2);
  color: #e74c3c;
  padding: 0.75rem;
  border-radius: 8px;
  margin-bottom: 1rem;
  font-size: 0.9rem;
}

.loading {
  text-align: center;
  color: #888;
  padding: 1rem;
}

.no-sessions {
  text-align: center;
  padding: 1.5rem;
}

.no-sessions p {
  color: #888;
  margin-bottom: 0.5rem;
}

.no-sessions .hint {
  font-size: 0.85rem;
  color: #666;
  margin-bottom: 1rem;
}

.live-stats {
  background: #1a1a2e;
  border-radius: 8px;
  padding: 1rem;
  margin-top: 1rem;
}

.stat-row {
  display: flex;
  justify-content: space-between;
  padding: 0.25rem 0;
}

.stat-row .label {
  color: #888;
}

.stat-row .value {
  color: #4ecca3;
  font-weight: bold;
}

.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: #16213e;
  padding: 2rem;
  border-radius: 12px;
  width: 100%;
  max-width: 400px;
}

.modal-content h2 {
  color: #4ecca3;
  margin-bottom: 1.5rem;
}

.modal-content .btn-secondary {
  width: 100%;
  margin-top: 0.75rem;
}

.loading-schema {
  padding: 1.5rem;
  text-align: center;
  color: #888;
}

.loading-schema .error-text {
  color: #e74c3c;
  margin-top: 0.5rem;
}
</style>
