<template>
  <div class="results-view">
    <div class="header">
      <div class="back-links">
        <router-link to="/hub" class="back-link">Home</router-link>
        <span class="back-sep">/</span>
        <router-link to="/dashboard" class="back-link">Dashboard</router-link>
      </div>
      <h1>Live Session Results</h1>
      <p v-if="report?.title" class="session-title">{{ report.title }}</p>
    </div>

    <div v-if="loading" class="loading">Loading results...</div>

    <div v-else-if="error" class="error">{{ error }}</div>

    <template v-else-if="report">
      <!-- Session Info -->
      <div class="session-info-cards">
        <div class="info-card" v-if="report.started_at">
          <div class="info-card-label">Started</div>
          <div class="info-card-value">{{ formatDate(report.started_at) }}</div>
        </div>
        <div class="info-card" v-if="report.ended_at">
          <div class="info-card-label">Ended</div>
          <div class="info-card-value">{{ formatDate(report.ended_at) }}</div>
        </div>
        <div class="info-card" v-if="report.summary?.session_duration">
          <div class="info-card-label">Duration</div>
          <div class="info-card-value info-card-highlight">{{ formatDuration(report.summary.session_duration) }}</div>
        </div>
      </div>

      <!-- Summary Cards -->
      <div class="summary-cards">
        <div class="card">
          <h3>Total Shots</h3>
          <div class="value">{{ report.summary?.total_shots || 0 }}</div>
        </div>
        <div class="card" v-if="report.post_analysis?.rallies">
          <h3>Rallies</h3>
          <div class="value">{{ report.post_analysis.rallies }}</div>
        </div>
        <div class="card" v-if="report.post_analysis?.shuttle_hits">
          <h3>Shuttle Hits</h3>
          <div class="value">{{ report.post_analysis.shuttle_hits }}</div>
        </div>
        <div class="card">
          <h3>Duration</h3>
          <div class="value">{{ formatDuration(report.summary?.session_duration) }}</div>
        </div>
      </div>

      <!-- Shot Distribution Chart -->
      <div class="section" v-if="hasShots">
        <h2>Shot Distribution</h2>
        <div class="chart-container">
          <Bar v-if="chartData" :data="chartData" :options="chartOptions" />
        </div>
      </div>

      <div class="section" v-else>
        <h2>Shot Distribution</h2>
        <p class="no-data">No shots were detected during this session.</p>
      </div>

      <!-- Shot List -->
      <div class="section" v-if="hasShots">
        <h2>Shot Breakdown</h2>
        <div class="shot-list">
          <div
            v-for="(count, shotType) in report.shot_distribution"
            :key="shotType"
            class="shot-item"
          >
            <span class="shot-type">{{ formatShotType(shotType) }}</span>
            <div class="shot-bar">
              <div
                class="shot-fill"
                :style="{ width: (count / maxShots * 100) + '%', backgroundColor: getShotColor(shotType) }"
              ></div>
            </div>
            <span class="shot-count">{{ count }}</span>
          </div>
        </div>
      </div>

      <!-- Heatmap Visualization -->
      <div class="section" v-if="hasPositions">
        <h2>Movement Heatmaps</h2>
        <StreamHeatmapGallery :session-id="sessionId" :admin="isAdminView" />
      </div>

      <!-- Shot Timeline / Trajectory -->
      <div class="section" v-if="hasTimeline">
        <h2>Shot Timeline</h2>
        <p class="section-desc">Shots detected over time</p>
        <div class="timeline-container">
          <div class="timeline">
            <div
              v-for="(shot, index) in normalizedTimeline"
              :key="index"
              class="timeline-item"
              :style="{ left: getTimelinePosition(shot.relativeTime) + '%' }"
            >
              <div class="timeline-dot" :style="{ backgroundColor: getShotColor(shot.shot) }"></div>
              <div class="timeline-tooltip">
                <span class="shot-name">{{ formatShotType(shot.shot) }}</span>
                <span class="shot-time">{{ formatTime(shot.relativeTime) }}</span>
                <span class="shot-conf">{{ Math.round(shot.confidence * 100) }}%</span>
              </div>
            </div>
          </div>
          <div class="timeline-axis">
            <span>0:00</span>
            <span>{{ formatTime(timelineDuration / 2) }}</span>
            <span>{{ formatTime(timelineDuration) }}</span>
          </div>
        </div>

        <!-- Shot Timeline List -->
        <div class="timeline-list">
          <div
            v-for="(shot, index) in normalizedTimeline"
            :key="'list-' + index"
            class="timeline-list-item"
          >
            <span class="list-time">{{ formatTime(shot.relativeTime) }}</span>
            <span class="list-shot" :style="{ color: getShotColor(shot.shot) }">
              {{ formatShotType(shot.shot) }}
            </span>
            <span class="list-conf">{{ Math.round(shot.confidence * 100) }}%</span>
          </div>
        </div>
      </div>

      <!-- Post-Analysis Results -->
      <div class="section" v-if="report.post_analysis">
        <h2>Detailed Analysis</h2>
        <div class="post-analysis-stats">
          <div class="pa-stat">
            <span class="pa-value">{{ report.post_analysis.shots || 0 }}</span>
            <span class="pa-label">Shots (Accurate)</span>
          </div>
          <div class="pa-stat">
            <span class="pa-value">{{ report.post_analysis.rallies || 0 }}</span>
            <span class="pa-label">Rallies</span>
          </div>
          <div class="pa-stat">
            <span class="pa-value">{{ report.post_analysis.shuttle_hits || 0 }}</span>
            <span class="pa-label">Shuttle Hits</span>
          </div>
        </div>
      </div>

      <!-- Rally Breakdown -->
      <div class="section" v-if="rallyData && rallyData.length > 0">
        <h2>Rally Breakdown</h2>
        <div class="rally-list">
          <div v-for="rally in rallyData" :key="rally.rally_id" class="rally-card">
            <div class="rally-header">
              <span class="rally-id">Rally {{ rally.rally_id }}</span>
              <span class="rally-duration">{{ formatDuration(rally.rally_duration || rally.duration) }}</span>
            </div>
            <div class="rally-details">
              <span class="rally-stat">{{ rally.shot_count || rally.shots?.length || 0 }} shots</span>
              <span class="rally-stat" v-if="rally.hit_count">{{ rally.hit_count }} hits</span>
              <span class="rally-time">{{ formatTime(rally.start_time) }} - {{ formatTime(rally.end_time) }}</span>
            </div>
            <div class="rally-shots" v-if="rally.shots && rally.shots.length > 0">
              <span
                v-for="(shot, i) in rally.shots"
                :key="i"
                class="rally-shot-tag"
                :style="{ backgroundColor: getShotColor(shot) + '33', color: getShotColor(shot), borderColor: getShotColor(shot) }"
              >{{ formatShotType(shot) }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Downloads -->
      <div class="section" v-if="report.has_recording || report.has_annotated_video">
        <h2>Downloads</h2>
        <div class="download-actions">
          <button v-if="report.has_annotated_video" @click="downloadAnnotatedVideo" class="btn-download" :disabled="downloading">
            {{ downloading ? 'Downloading...' : 'Download Annotated Video' }}
          </button>
          <button v-if="report.has_recording" @click="downloadRecording" class="btn-download btn-download-secondary" :disabled="downloading">
            {{ downloading ? 'Downloading...' : 'Download Raw Recording' }}
          </button>
          <router-link
            v-if="report.has_frame_data"
            :to="`/stream/${sessionId}/tuning`"
            class="btn-download btn-download-secondary"
          >
            Open in Frame Viewer
          </router-link>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { Bar } from 'vue-chartjs'
import {
  Chart as ChartJS,
  Title,
  Tooltip,
  Legend,
  BarElement,
  CategoryScale,
  LinearScale
} from 'chart.js'
import api from '../api/client'
import { useAuthStore } from '../stores/auth'
import StreamHeatmapGallery from '../components/StreamHeatmapGallery.vue'

ChartJS.register(Title, Tooltip, Legend, BarElement, CategoryScale, LinearScale)

const route = useRoute()
const authStore = useAuthStore()
const sessionId = parseInt(route.params.sessionId)

const loading = ref(true)
const error = ref('')
const report = ref(null)
const downloading = ref(false)
const isAdminView = ref(false)

const hasShots = computed(() => {
  return report.value?.shot_distribution && Object.keys(report.value.shot_distribution).length > 0
})

const hasPositions = computed(() => {
  return report.value?.foot_positions && report.value.foot_positions.length > 0
})

const hasTimeline = computed(() => {
  return report.value?.shot_timeline && report.value.shot_timeline.length > 0
})

const rallyData = computed(() => {
  return report.value?.post_analysis?.rally_data || []
})

// Convert absolute timestamps to relative times
const normalizedTimeline = computed(() => {
  if (!report.value?.shot_timeline?.length) return []

  const timeline = report.value.shot_timeline
  const firstTime = timeline[0].time

  return timeline.map(shot => ({
    ...shot,
    relativeTime: shot.time - firstTime
  }))
})

const timelineDuration = computed(() => {
  if (!normalizedTimeline.value.length) return 1
  const times = normalizedTimeline.value.map(s => s.relativeTime)
  return Math.max(...times) || 1
})

const maxShots = computed(() => {
  if (!report.value?.shot_distribution) return 1
  return Math.max(...Object.values(report.value.shot_distribution), 1)
})

const chartData = computed(() => {
  if (!report.value?.shot_distribution) return null

  const distribution = report.value.shot_distribution
  const labels = Object.keys(distribution)
  const values = Object.values(distribution)

  if (labels.length === 0) return null

  return {
    labels: labels.map(l => formatShotType(l)),
    datasets: [{
      label: 'Shots',
      data: values,
      backgroundColor: labels.map(l => getShotColor(l))
    }]
  }
})

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      display: false
    }
  },
  scales: {
    y: {
      beginAtZero: true,
      ticks: {
        color: '#888',
        stepSize: 1
      },
      grid: {
        color: '#2a2a4a'
      }
    },
    x: {
      ticks: {
        color: '#888'
      },
      grid: {
        display: false
      }
    }
  }
}

const shotColors = {
  smash: '#e74c3c',
  clear: '#2ecc71',
  drop_shot: '#f39c12',
  net_shot: '#3498db',
  drive: '#9b59b6',
  lift: '#1abc9c',
  serve: '#e67e22',
  unknown: '#95a5a6'
}

onMounted(async () => {
  await loadResults()
})

async function loadResults() {
  loading.value = true
  error.value = ''

  try {
    const response = await api.get(`/api/v1/stream/${sessionId}/results`)
    report.value = response.data
  } catch (err) {
    // Admin fallback: if user doesn't own the session, try admin endpoint
    if (err.response?.status === 404 && authStore.user?.is_admin) {
      try {
        const adminResp = await api.get(`/api/v1/admin/stream-sessions/${sessionId}/results`)
        report.value = adminResp.data
        isAdminView.value = true
        return
      } catch (adminErr) {
        error.value = adminErr.response?.data?.detail || 'Failed to load results'
        return
      }
    }
    error.value = err.response?.data?.detail || 'Failed to load results'
  } finally {
    loading.value = false
  }
}

function getTimelinePosition(relativeTime) {
  const duration = timelineDuration.value || 1
  return Math.min((relativeTime / duration) * 100, 100)
}

function formatTime(seconds) {
  if (!seconds && seconds !== 0) return '0:00'
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

function formatDate(dateString) {
  if (!dateString) return 'N/A'
  return new Date(dateString).toLocaleString()
}

function formatDuration(seconds) {
  if (!seconds) return 'N/A'
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  if (mins > 0) {
    return `${mins}m ${secs}s`
  }
  return `${secs}s`
}

function formatQuality(quality) {
  const map = {
    low: 'Low',
    medium: 'Medium',
    high: 'High',
    max: 'Maximum'
  }
  return map[quality] || quality || 'Medium'
}

function formatShotType(type) {
  if (!type) return ''
  return type.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

function getShotColor(shotType) {
  return shotColors[shotType] || shotColors.unknown
}

async function downloadRecording() {
  downloading.value = true
  try {
    const endpoint = isAdminView.value
      ? `/api/v1/admin/stream-sessions/${sessionId}/recording`
      : `/api/v1/stream/${sessionId}/recording`
    const response = await api.get(endpoint, { responseType: 'blob' })

    const blob = new Blob([response.data], { type: 'video/mp4' })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `stream_recording_${sessionId}.mp4`
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

async function downloadAnnotatedVideo() {
  downloading.value = true
  try {
    const endpoint = isAdminView.value
      ? `/api/v1/admin/stream-sessions/${sessionId}/annotated-video`
      : `/api/v1/stream/${sessionId}/annotated-video`
    const response = await api.get(endpoint, { responseType: 'blob' })

    const blob = new Blob([response.data], { type: 'video/mp4' })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `annotated_stream_${sessionId}.mp4`
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
</script>

<style scoped>
.results-view {
  max-width: 1000px;
  margin: 0 auto;
}

.header {
  margin-bottom: 2rem;
}

.back-links {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  margin-bottom: 0.75rem;
}

.back-link {
  color: var(--text-muted);
  text-decoration: none;
  font-size: 0.9rem;
}

.back-link:hover {
  color: var(--color-primary);
}

.back-sep {
  color: var(--text-muted);
  font-size: 0.85rem;
}

h1 {
  color: var(--color-primary);
  margin-bottom: 0.25rem;
}

.session-title {
  color: var(--text-muted);
  font-size: 1.1rem;
}

.loading, .error {
  text-align: center;
  padding: 3rem;
  color: var(--text-muted);
}

.error {
  color: var(--color-destructive);
}

.session-info-cards {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.info-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 1rem 1.25rem;
  box-shadow: var(--shadow-md);
}

.info-card-label {
  color: var(--text-muted);
  font-size: 0.8rem;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  margin-bottom: 0.35rem;
}

.info-card-value {
  color: var(--text-primary);
  font-size: 0.95rem;
  font-weight: 600;
}

.info-card-highlight {
  color: var(--color-primary);
  font-size: 1.1rem;
}

.summary-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 1rem;
  margin-bottom: 2rem;
}

.card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 1.5rem;
  text-align: center;
  box-shadow: var(--shadow-md);
}

.card h3 {
  color: var(--text-muted);
  font-size: 0.9rem;
  font-weight: normal;
  margin-bottom: 0.5rem;
}

.card .value {
  color: var(--color-primary);
  font-size: 2rem;
  font-weight: bold;
}

.card .value.quality {
  font-size: 1.5rem;
  text-transform: capitalize;
}

.section {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 1.5rem;
  margin-bottom: 1.5rem;
  box-shadow: var(--shadow-md);
}

.section h2 {
  color: var(--text-primary);
  font-size: 1.2rem;
  margin-bottom: 1rem;
}

.chart-container {
  height: 300px;
}

.no-data {
  color: var(--text-muted);
  text-align: center;
  padding: 2rem;
}

.shot-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.shot-item {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.shot-type {
  width: 100px;
  color: var(--text-muted);
  font-size: 0.9rem;
}

.shot-bar {
  flex: 1;
  height: 24px;
  background: var(--border-color);
  border-radius: 4px;
  overflow: hidden;
}

.shot-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.3s ease;
}

.shot-count {
  width: 40px;
  text-align: right;
  color: var(--color-primary);
  font-weight: bold;
}

.post-analysis-stats {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.pa-stat {
  display: flex;
  flex-direction: column;
  align-items: center;
  background: var(--bg-input);
  border-radius: var(--radius-md);
  padding: 1rem;
}

.pa-value {
  color: var(--color-primary);
  font-size: 1.4rem;
  font-weight: bold;
}

.pa-label {
  color: var(--text-muted);
  font-size: 0.8rem;
  text-align: center;
}

.download-actions {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
}

.btn-download-secondary {
  background: var(--border-color) !important;
  color: var(--text-primary) !important;
}

.btn-download-secondary:hover:not(:disabled) {
  background: var(--border-input) !important;
}

.recording-desc {
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
  text-decoration: none;
  font-weight: 600;
  transition: background 0.2s;
  border: none;
  cursor: pointer;
  font-size: 1rem;
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

/* Timeline Styles */
.timeline-container {
  padding: 1rem;
  background: var(--bg-input);
  border-radius: var(--radius-md);
  margin-bottom: 1rem;
}

.timeline {
  position: relative;
  height: 60px;
  background: var(--border-color);
  border-radius: 4px;
  margin-bottom: 0.5rem;
}

.timeline-item {
  position: absolute;
  top: 50%;
  transform: translate(-50%, -50%);
  cursor: pointer;
}

.timeline-dot {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  border: 2px solid white;
  transition: transform 0.2s;
}

.timeline-item:hover .timeline-dot {
  transform: scale(1.3);
}

.timeline-tooltip {
  position: absolute;
  bottom: 100%;
  left: 50%;
  transform: translateX(-50%);
  background: var(--bg-card);
  border: 1px solid var(--border-input);
  border-radius: var(--radius-sm);
  padding: 0.5rem;
  white-space: nowrap;
  opacity: 0;
  visibility: hidden;
  transition: all 0.2s;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  z-index: 10;
  margin-bottom: 0.5rem;
  box-shadow: var(--shadow-md);
}

.timeline-item:hover .timeline-tooltip {
  opacity: 1;
  visibility: visible;
}

.timeline-tooltip .shot-name {
  color: var(--color-primary);
  font-weight: bold;
  font-size: 0.85rem;
}

.timeline-tooltip .shot-time {
  color: var(--text-muted);
  font-size: 0.8rem;
}

.timeline-tooltip .shot-conf {
  color: var(--text-muted);
  font-size: 0.75rem;
}

.timeline-axis {
  display: flex;
  justify-content: space-between;
  color: var(--text-muted);
  font-size: 0.8rem;
}

.timeline-list {
  max-height: 200px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.timeline-list-item {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0.5rem;
  background: var(--bg-input);
  border-radius: 4px;
}

.list-time {
  color: var(--text-muted);
  font-family: monospace;
  font-size: 0.85rem;
  width: 50px;
}

.list-shot {
  flex: 1;
  font-weight: 500;
}

.list-conf {
  color: var(--text-muted);
  font-size: 0.85rem;
}

/* Rally Breakdown */
.rally-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.rally-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 1rem;
  border-left: 3px solid var(--color-primary);
  box-shadow: var(--shadow-md);
}

.rally-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.rally-id {
  color: var(--color-primary);
  font-weight: bold;
  font-size: 1rem;
}

.rally-duration {
  color: var(--text-muted);
  font-size: 0.9rem;
}

.rally-details {
  display: flex;
  gap: 1.5rem;
  margin-bottom: 0.5rem;
  font-size: 0.85rem;
}

.rally-stat {
  color: var(--text-secondary);
}

.rally-time {
  color: var(--text-muted);
  font-family: monospace;
}

.rally-shots {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
}

.rally-shot-tag {
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 500;
  border: 1px solid;
}

/* ---- Mobile Responsive ---- */
@media (max-width: 640px) {
  .results-view {
    padding: 0.75rem;
  }

  .header {
    margin-bottom: 1rem;
  }

  h1 {
    font-size: 1.3rem;
  }

  .session-info-cards {
    grid-template-columns: 1fr;
    gap: 0.75rem;
  }

  .info-card {
    padding: 0.75rem 1rem;
  }

  .info-card-value {
    font-size: 0.9rem;
  }

  .summary-cards {
    grid-template-columns: repeat(2, 1fr);
    gap: 0.75rem;
  }

  .card {
    padding: 1rem;
  }

  .card .value {
    font-size: 1.5rem;
  }

  .section {
    padding: 1rem;
    margin-bottom: 1rem;
  }

  .section h2 {
    font-size: 1.05rem;
  }

  .chart-container {
    height: 220px;
  }

  /* Shot list */
  .shot-item {
    gap: 0.5rem;
  }

  .shot-type {
    width: 70px;
    font-size: 0.8rem;
  }

  .shot-count {
    width: 30px;
    font-size: 0.85rem;
  }

  /* Post-analysis */
  .pa-stat {
    padding: 0.75rem;
  }

  .pa-value {
    font-size: 1.2rem;
  }

  .pa-label {
    font-size: 0.7rem;
  }

  /* Timeline */
  .timeline {
    height: 50px;
  }

  .timeline-dot {
    width: 12px;
    height: 12px;
  }

  .timeline-list-item {
    gap: 0.5rem;
    padding: 0.4rem;
    font-size: 0.85rem;
  }

  .list-time {
    width: 40px;
    font-size: 0.8rem;
  }

  /* Rally breakdown */
  .rally-card {
    padding: 0.75rem;
  }

  .rally-details {
    flex-wrap: wrap;
    gap: 0.75rem;
    font-size: 0.8rem;
  }

  .rally-time {
    font-size: 0.75rem;
  }

  /* Downloads */
  .download-actions {
    flex-direction: column;
  }

  .btn-download {
    width: 100%;
    justify-content: center;
    text-align: center;
  }

  .section-desc {
    font-size: 0.85rem;
  }
}
</style>
