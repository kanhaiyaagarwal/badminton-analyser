<template>
  <div class="mimic-results">
    <router-link to="/mimic" class="back-link">&larr; Back to Challenges</router-link>

    <div v-if="loading" class="loading">Loading results...</div>

    <template v-else-if="session">
      <h1>Session Results</h1>
      <p v-if="session.challenge_title" class="challenge-title">{{ session.challenge_title }}</p>

      <!-- Overall score gauge -->
      <div class="gauge-section">
        <SimilarityGauge :score="session.overall_score" label="Overall Score" :size="220" />
      </div>

      <!-- Side-by-side comparison video -->
      <div v-if="comparisonVideoUrl" class="comparison-video-section">
        <h2>Side-by-Side Comparison</h2>
        <video
          ref="videoRef"
          :src="comparisonVideoUrl"
          controls
          playsinline
          class="comparison-video"
          @timeupdate="onTimeUpdate"
        ></video>
        <button @click="downloadVideo" class="download-btn" :disabled="downloading">
          {{ downloading ? 'Downloading...' : 'Download Video' }}
        </button>
      </div>

      <!-- Score breakdown -->
      <div class="breakdown-section">
        <h2>Score Breakdown</h2>
        <div class="breakdown-grid" v-if="session.score_breakdown">
          <div class="breakdown-card">
            <span class="bk-value">{{ session.score_breakdown.angle_score || 0 }}%</span>
            <span class="bk-label">Angle Match</span>
          </div>
          <div class="breakdown-card">
            <span class="bk-value">{{ session.score_breakdown.cosine_normalized || 0 }}%</span>
            <span class="bk-label">Pose Similarity</span>
          </div>
          <div class="breakdown-card">
            <span class="bk-value">{{ session.score_breakdown.upper_body || 0 }}%</span>
            <span class="bk-label">Upper Body</span>
          </div>
          <div class="breakdown-card">
            <span class="bk-value">{{ session.score_breakdown.lower_body || 0 }}%</span>
            <span class="bk-label">Lower Body</span>
          </div>
        </div>
      </div>

      <!-- Feedback section -->
      <div v-if="session.feedback && session.feedback.items?.length" class="feedback-section">
        <h2>Feedback</h2>
        <p v-if="session.feedback.summary" class="feedback-summary">{{ session.feedback.summary }}</p>
        <div class="feedback-cards">
          <div
            v-for="(item, idx) in session.feedback.items"
            :key="idx"
            class="feedback-card"
            :class="`feedback-${item.status}`"
          >
            <span class="feedback-icon">
              <template v-if="item.status === 'good'">&#10003;</template>
              <template v-else-if="item.status === 'fair'">~</template>
              <template v-else-if="item.status === 'poor'">!</template>
              <template v-else>i</template>
            </span>
            <span class="feedback-msg">{{ item.message }}</span>
          </div>
        </div>
      </div>

      <!-- Stats row -->
      <div class="stats-row">
        <div class="stat">
          <span class="stat-value">{{ formatDuration(session.duration_seconds) }}</span>
          <span class="stat-label">Duration</span>
        </div>
        <div class="stat">
          <span class="stat-value">{{ session.frames_compared || 0 }}</span>
          <span class="stat-label">Frames</span>
        </div>
        <div class="stat" v-if="session.personal_best != null">
          <span class="stat-value">{{ Math.round(session.personal_best) }}</span>
          <span class="stat-label">Personal Best</span>
        </div>
        <div class="stat" v-if="session.attempt_count">
          <span class="stat-value">{{ session.attempt_count }}</span>
          <span class="stat-label">Attempts</span>
        </div>
      </div>

      <!-- Score over time chart -->
      <div v-if="chartData" class="chart-section">
        <h2>Score Over Time</h2>
        <div class="chart-container">
          <Line :data="chartData" :options="chartOptions" />
        </div>
      </div>

      <!-- Actions -->
      <div class="actions">
        <button @click="tryAgain" class="action-btn primary">Try Again</button>
        <router-link to="/mimic" class="action-btn secondary">Browse Challenges</router-link>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Line } from 'vue-chartjs'
import {
  Chart as ChartJS,
  Title,
  Tooltip,
  Legend,
  LineElement,
  PointElement,
  CategoryScale,
  LinearScale,
  Filler,
} from 'chart.js'
import annotationPlugin from 'chartjs-plugin-annotation'
import { useAuthStore } from '../stores/auth'
import { useMimicStore } from '../stores/mimic'
import SimilarityGauge from '../components/SimilarityGauge.vue'

ChartJS.register(Title, Tooltip, Legend, LineElement, PointElement, CategoryScale, LinearScale, Filler, annotationPlugin)

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const mimicStore = useMimicStore()

const sessionId = parseInt(route.params.sessionId)
const session = ref(null)
const loading = ref(true)
const videoRef = ref(null)
const currentVideoTime = ref(0)

const downloading = ref(false)

const comparisonVideoUrl = computed(() =>
  session.value?.has_comparison_video
    ? `/api/v1/mimic/sessions/${sessionId}/comparison-video?token=${authStore.accessToken}`
    : null
)

async function downloadVideo() {
  if (!comparisonVideoUrl.value || downloading.value) return
  downloading.value = true
  try {
    const resp = await fetch(comparisonVideoUrl.value)
    const blob = await resp.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `comparison_${sessionId}.mp4`
    a.click()
    URL.revokeObjectURL(url)
  } catch (e) {
    console.error('Download failed:', e)
  } finally {
    downloading.value = false
  }
}

onMounted(async () => {
  try {
    session.value = await mimicStore.fetchSession(sessionId)
  } catch (err) {
    // error handled by store
  } finally {
    loading.value = false
  }
})

function onTimeUpdate() {
  if (videoRef.value) {
    currentVideoTime.value = videoRef.value.currentTime
  }
}

// Downsample scores for chart, shared between chartData and chartOptions
const sampledScores = computed(() => {
  const scores = session.value?.frame_scores
  if (!scores || scores.length < 2) return null
  const step = Math.max(1, Math.floor(scores.length / 100))
  return scores.filter((_, i) => i % step === 0)
})

const seekbarIndex = computed(() => {
  const sampled = sampledScores.value
  if (!sampled || !sampled.length) return null

  const t = currentVideoTime.value
  // Find closest index by timestamp
  let best = 0
  let bestDiff = Math.abs(sampled[0].t - t)
  for (let i = 1; i < sampled.length; i++) {
    const diff = Math.abs(sampled[i].t - t)
    if (diff < bestDiff) {
      bestDiff = diff
      best = i
    }
  }
  return best
})

const chartData = computed(() => {
  const sampled = sampledScores.value
  if (!sampled) return null

  // Use smoothed keys when available, fall back to raw for backward compat
  const hasSmoothed = 'angle_score_smoothed' in sampled[0]

  return {
    labels: sampled.map(f => f.t.toFixed(1) + 's'),
    datasets: [
      {
        label: 'Overall',
        data: sampled.map(f => hasSmoothed ? f.angle_score_smoothed : f.angle_score),
        borderColor: '#2ecc71',
        backgroundColor: 'rgba(46, 204, 113, 0.1)',
        fill: true,
        tension: 0.3,
        pointRadius: 0,
        borderWidth: 2,
      },
      {
        label: 'Upper Body',
        data: sampled.map(f => hasSmoothed ? f.upper_body_smoothed : f.upper_body),
        borderColor: '#e67e22',
        backgroundColor: 'transparent',
        fill: false,
        tension: 0.3,
        pointRadius: 0,
        borderWidth: 1.5,
        borderDash: [6, 3],
      },
      {
        label: 'Lower Body',
        data: sampled.map(f => hasSmoothed ? f.lower_body_smoothed : f.lower_body),
        borderColor: '#9b59b6',
        backgroundColor: 'transparent',
        fill: false,
        tension: 0.3,
        pointRadius: 0,
        borderWidth: 1.5,
        borderDash: [6, 3],
      },
    ],
  }
})

const chartOptions = computed(() => {
  const idx = seekbarIndex.value
  const annotations = {}

  if (idx !== null) {
    annotations.seekbar = {
      type: 'line',
      xMin: idx,
      xMax: idx,
      borderColor: 'rgba(255, 255, 255, 0.8)',
      borderWidth: 1.5,
      borderDash: [4, 3],
    }
  }

  return {
    responsive: true,
    maintainAspectRatio: false,
    animation: { duration: 0 },
    plugins: {
      legend: { labels: { color: '#888' } },
      annotation: { annotations },
    },
    scales: {
      x: {
        ticks: { color: '#888', maxTicksLimit: 10 },
        grid: { color: 'rgba(255,255,255,0.05)' },
      },
      y: {
        min: 0,
        max: 100,
        ticks: { color: '#888' },
        grid: { color: 'rgba(255,255,255,0.05)' },
      },
    },
  }
})

function tryAgain() {
  if (session.value?.challenge_id) {
    router.push(`/mimic/session/${session.value.challenge_id}`)
  } else {
    router.push('/mimic')
  }
}

function formatDuration(seconds) {
  if (!seconds) return '0s'
  const m = Math.floor(seconds / 60)
  const s = Math.round(seconds % 60)
  return m > 0 ? `${m}m ${s}s` : `${s}s`
}
</script>

<style scoped>
.mimic-results {
  max-width: 700px;
  margin: 0 auto;
  padding: 1.5rem 1rem;
}

.back-link {
  color: var(--text-muted);
  text-decoration: none;
  font-size: 0.9rem;
}

h1 {
  color: var(--text-primary);
  font-size: 1.5rem;
  margin: 0.75rem 0 0.25rem;
}

.challenge-title {
  color: var(--text-secondary);
  font-size: 1rem;
  margin-bottom: 1rem;
}

.comparison-video-section {
  margin: 1.5rem 0;
}

.comparison-video-section h2 {
  color: var(--text-primary);
  font-size: 1.1rem;
  margin-bottom: 0.75rem;
}

.comparison-video {
  width: 100%;
  border-radius: var(--radius-md, 8px);
  background: #000;
}

.download-btn {
  display: inline-block;
  margin-top: 0.5rem;
  padding: 0.4rem 1rem;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md, 8px);
  color: var(--text-secondary);
  text-decoration: none;
  font-size: 0.85rem;
  cursor: pointer;
}

.gauge-section {
  margin: 1.5rem 0;
}

.breakdown-section {
  margin: 1.5rem 0;
}

.breakdown-section h2,
.chart-section h2 {
  color: var(--text-primary);
  font-size: 1.1rem;
  margin-bottom: 0.75rem;
}

.breakdown-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
  gap: 0.75rem;
}

.breakdown-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md, 8px);
  padding: 1rem;
  text-align: center;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.bk-value {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--text-primary);
}

.bk-label {
  font-size: 0.75rem;
  color: var(--text-muted);
}

/* Feedback section */
.feedback-section {
  margin: 1.5rem 0;
}

.feedback-section h2 {
  color: var(--text-primary);
  font-size: 1.1rem;
  margin-bottom: 0.5rem;
}

.feedback-summary {
  color: var(--text-secondary);
  font-size: 0.9rem;
  margin-bottom: 0.75rem;
}

.feedback-cards {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.feedback-card {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0.6rem 0.8rem;
  border-radius: var(--radius-md, 8px);
  border-left: 3px solid;
  font-size: 0.85rem;
}

.feedback-good {
  border-left-color: #2ecc71;
  background: rgba(46, 204, 113, 0.08);
  color: #2ecc71;
}

.feedback-fair {
  border-left-color: #f1c40f;
  background: rgba(241, 196, 15, 0.08);
  color: #f1c40f;
}

.feedback-poor {
  border-left-color: #e74c3c;
  background: rgba(231, 76, 60, 0.08);
  color: #e74c3c;
}

.feedback-tip {
  border-left-color: #3498db;
  background: rgba(52, 152, 219, 0.08);
  color: #3498db;
}

.feedback-icon {
  font-weight: 700;
  font-size: 0.95rem;
  min-width: 1.2em;
  text-align: center;
}

.feedback-msg {
  flex: 1;
}

.stats-row {
  display: flex;
  gap: 1.5rem;
  flex-wrap: wrap;
  margin: 1.5rem 0;
  justify-content: center;
}

.stat {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.stat-value {
  font-size: 1.3rem;
  font-weight: 600;
  color: var(--text-primary);
}

.stat-label {
  font-size: 0.75rem;
  color: var(--text-muted);
}

.chart-section {
  margin: 1.5rem 0;
}

.chart-container {
  height: 250px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md, 8px);
  padding: 0.75rem;
}

.actions {
  display: flex;
  gap: 0.75rem;
  justify-content: center;
  margin-top: 2rem;
}

.action-btn {
  padding: 0.6rem 1.5rem;
  border-radius: var(--radius-md, 8px);
  font-size: 0.95rem;
  font-weight: 500;
  cursor: pointer;
  text-decoration: none;
  text-align: center;
  border: none;
}

.action-btn.primary {
  background: var(--color-primary);
  color: white;
}

.action-btn.secondary {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
}

.loading {
  text-align: center;
  padding: 3rem;
  color: var(--text-muted);
}
</style>
