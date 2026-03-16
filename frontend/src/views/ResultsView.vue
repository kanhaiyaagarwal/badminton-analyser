<template>
  <div class="results-view">
    <div class="header">
      <router-link to="/dashboard" class="back-link">Back to Dashboard</router-link>
      <h1>Analysis Results</h1>
    </div>

    <div v-if="loading" class="loading">Loading results...</div>

    <div v-else-if="error" class="error">{{ error }}</div>

    <template v-else-if="report">
      <!-- Summary Cards -->
      <div class="summary-cards">
        <div class="card">
          <h3>Total Shots</h3>
          <div class="value">{{ report.summary?.total_shots || 0 }}</div>
        </div>
        <div class="card">
          <h3>Rallies</h3>
          <div class="value">{{ report.summary?.total_rallies || 0 }}</div>
        </div>
        <div class="card">
          <h3>Detection Rate</h3>
          <div class="value">{{ formatPercent(report.summary?.player_detection_rate) }}</div>
        </div>
        <div class="card">
          <h3>Avg Confidence</h3>
          <div class="value">{{ formatPercent(report.summary?.avg_confidence) }}</div>
        </div>
        <div v-if="shuttleAvailable" class="card">
          <h3>Shuttle Detection</h3>
          <div class="value">{{ formatPercent(report.shuttle_tracking?.summary?.detection_rate) }}</div>
          <div class="sub-value">{{ report.shuttle_tracking?.summary?.detected_frames || 0 }} / {{ report.shuttle_tracking?.summary?.total_frames || 0 }} frames</div>
        </div>
        <div v-if="shuttleAvailable" class="card">
          <h3>Shuttle Hits</h3>
          <div class="value">{{ report.summary?.shuttle_hits_detected || 0 }}</div>
        </div>
      </div>

      <!-- Shot Distribution Chart -->
      <div class="section">
        <h2>Shot Distribution</h2>
        <div class="chart-container">
          <Bar v-if="chartData" :data="chartData" :options="chartOptions" />
        </div>
      </div>

      <!-- Heatmap Gallery -->
      <div class="section">
        <h2>Movement Heatmap</h2>
        <HeatmapGallery :job-id="jobId" />
      </div>

      <!-- Shot Timeline with Shuttle Speed -->
      <div v-if="report.shot_timeline?.length" class="section">
        <h2>Shot Timeline</h2>
        <div class="timeline-list">
          <div v-for="(shot, idx) in report.shot_timeline" :key="idx" class="timeline-entry">
            <span class="timeline-time">{{ formatTime(shot.time) }}</span>
            <span :class="['timeline-shot', `shot-${shot.shot}`]">{{ shot.shot?.replace('_', ' ') }}</span>
            <span class="timeline-confidence">{{ (shot.confidence * 100).toFixed(0) }}%</span>
            <span v-if="shot.shuttle_speed_px_per_sec" class="timeline-speed">
              {{ Math.round(shot.shuttle_speed_px_per_sec) }} px/s
            </span>
            <span v-if="shot.shuttle_hit_matched" class="timeline-hit-badge">HIT</span>
          </div>
        </div>
      </div>

      <!-- Rally Timeline -->
      <div class="section">
        <h2>Rally Breakdown</h2>
        <RallyTimeline :rallies="report.rallies || []" />
      </div>

      <!-- Video Download -->
      <div class="section">
        <h2>Annotated Video</h2>
        <button @click="downloadVideo" class="btn-download" :disabled="downloading">
          {{ downloading ? 'Downloading...' : 'Download Annotated Video' }}
        </button>
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
import HeatmapGallery from '../components/HeatmapGallery.vue'
import RallyTimeline from '../components/RallyTimeline.vue'

ChartJS.register(Title, Tooltip, Legend, BarElement, CategoryScale, LinearScale)

const route = useRoute()
const jobId = parseInt(route.params.jobId)

const loading = ref(true)
const error = ref('')
const report = ref(null)
const downloading = ref(false)

const shuttleAvailable = computed(() => {
  return report.value?.shuttle_tracking?.available === true
})

const chartData = computed(() => {
  if (!report.value?.shot_distribution) return null

  const distribution = report.value.shot_distribution
  const labels = Object.keys(distribution)
  const values = Object.values(distribution)

  return {
    labels: labels.map(l => l.replace('_', ' ')),
    datasets: [{
      label: 'Shots',
      data: values,
      backgroundColor: [
        '#e74c3c', // smash - red
        '#2ecc71', // clear - green
        '#f39c12', // drop_shot - orange
        '#3498db', // net_shot - blue
        '#9b59b6', // drive - purple
        '#1abc9c'  // lift - teal
      ]
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
        color: '#888'
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

onMounted(async () => {
  await loadResults()
})

async function loadResults() {
  loading.value = true
  error.value = ''

  try {
    const response = await api.get(`/api/v1/results/${jobId}`)
    report.value = response.data
  } catch (err) {
    error.value = err.response?.data?.detail || 'Failed to load results'
  } finally {
    loading.value = false
  }
}

function formatPercent(value) {
  if (value === undefined || value === null) return '-'
  return (value * 100).toFixed(1) + '%'
}

function formatTime(seconds) {
  if (seconds === undefined || seconds === null) return '-'
  const m = Math.floor(seconds / 60)
  const s = (seconds % 60).toFixed(1)
  return `${m}:${s.padStart(4, '0')}`
}

async function downloadVideo() {
  downloading.value = true
  try {
    // Get presigned URL for direct S3 download (avoids proxying large video through backend)
    const urlResponse = await api.get(`/api/v1/results/${jobId}/video/url`)
    const { url: videoUrl } = urlResponse.data

    const link = document.createElement('a')
    link.href = videoUrl
    link.download = `analyzed_video_${jobId}.mp4`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  } catch (err) {
    error.value = err.response?.data?.detail || 'Failed to download video'
  } finally {
    downloading.value = false
  }
}
</script>

<style scoped>
.results-view {
  max-width: 1000px;
  margin: 0 auto;
  padding: 1rem;
}

.header {
  margin-bottom: 1rem;
}

.back-link {
  color: var(--text-muted);
  text-decoration: none;
  font-size: 0.9rem;
  display: inline-block;
  margin-bottom: 1rem;
}

.back-link:hover {
  color: var(--color-primary);
}

h1 {
  color: var(--color-primary);
  font-size: 1.3rem;
}

.loading, .error {
  text-align: center;
  padding: 3rem;
  color: var(--text-muted);
}

.error {
  color: var(--color-destructive);
}

.summary-cards {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0.75rem;
  margin-bottom: 1.5rem;
}

.card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 1rem;
  text-align: center;
  box-shadow: var(--shadow-md);
}

.card h3 {
  color: var(--text-muted);
  font-size: 0.8rem;
  font-weight: normal;
  margin-bottom: 0.35rem;
}

.card .value {
  color: var(--color-primary);
  font-size: 1.5rem;
  font-weight: bold;
}

.card .sub-value {
  color: var(--text-muted);
  font-size: 0.75rem;
  margin-top: 0.25rem;
}

.section {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 1rem;
  margin-bottom: 1rem;
  box-shadow: var(--shadow-md);
}

.section h2 {
  color: var(--text-primary);
  font-size: 1.05rem;
  margin-bottom: 0.75rem;
}

.chart-container {
  height: 220px;
}

/* Shot Timeline */
.timeline-list {
  max-height: 400px;
  overflow-y: auto;
}

.timeline-entry {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.5rem 0;
  border-bottom: 1px solid var(--border-color);
  flex-wrap: wrap;
}

.timeline-time {
  color: var(--text-muted);
  font-size: 0.8rem;
  min-width: 50px;
  font-family: monospace;
}

.timeline-shot {
  font-weight: bold;
  font-size: 0.8rem;
  text-transform: capitalize;
  min-width: 65px;
}

.shot-smash { color: var(--color-destructive); }
.shot-clear { color: var(--color-success); }
.shot-drop_shot { color: var(--color-warning); }
.shot-net_shot { color: var(--color-info); }
.shot-drive { color: var(--color-secondary); }
.shot-lift { color: var(--color-primary); }

.timeline-confidence {
  color: var(--text-muted);
  font-size: 0.75rem;
}

.timeline-speed {
  color: var(--color-warning);
  font-size: 0.75rem;
  font-family: monospace;
}

.timeline-hit-badge {
  background: var(--color-destructive);
  color: #fff;
  font-size: 0.65rem;
  font-weight: 600;
  padding: 0.15rem 0.4rem;
  border-radius: var(--radius-sm);
}

.btn-download {
  display: block;
  width: 100%;
  text-align: center;
  background: var(--color-primary);
  color: var(--text-on-primary);
  padding: 0.75rem 1.5rem;
  border-radius: var(--radius-md);
  text-decoration: none;
  font-weight: 600;
  transition: background 0.2s;
  border: none;
  cursor: pointer;
  font-size: 0.9rem;
}

.btn-download:hover:not(:disabled) {
  background: var(--color-primary-hover);
}

.btn-download:disabled {
  background: var(--text-muted);
  cursor: not-allowed;
}

</style>
