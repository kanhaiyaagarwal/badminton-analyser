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

      <!-- Score breakdown -->
      <div class="breakdown-section">
        <h2>Score Breakdown</h2>
        <div class="breakdown-grid" v-if="session.score_breakdown">
          <div class="breakdown-card">
            <span class="bk-value">{{ session.score_breakdown.angle_score || 0 }}</span>
            <span class="bk-label">Angle Match</span>
          </div>
          <div class="breakdown-card">
            <span class="bk-value">{{ session.score_breakdown.cosine_normalized || 0 }}</span>
            <span class="bk-label">Pose Similarity</span>
          </div>
          <div class="breakdown-card">
            <span class="bk-value">{{ session.score_breakdown.upper_body || 0 }}</span>
            <span class="bk-label">Upper Body</span>
          </div>
          <div class="breakdown-card">
            <span class="bk-value">{{ session.score_breakdown.lower_body || 0 }}</span>
            <span class="bk-label">Lower Body</span>
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
import { useMimicStore } from '../stores/mimic'
import SimilarityGauge from '../components/SimilarityGauge.vue'

ChartJS.register(Title, Tooltip, Legend, LineElement, PointElement, CategoryScale, LinearScale, Filler)

const route = useRoute()
const router = useRouter()
const mimicStore = useMimicStore()

const sessionId = parseInt(route.params.sessionId)
const session = ref(null)
const loading = ref(true)

onMounted(async () => {
  try {
    session.value = await mimicStore.fetchSession(sessionId)
  } catch (err) {
    // error handled by store
  } finally {
    loading.value = false
  }
})

const chartData = computed(() => {
  const scores = session.value?.frame_scores
  if (!scores || scores.length < 2) return null

  // Downsample if too many points
  const step = Math.max(1, Math.floor(scores.length / 100))
  const sampled = scores.filter((_, i) => i % step === 0)

  return {
    labels: sampled.map(f => f.t.toFixed(1) + 's'),
    datasets: [
      {
        label: 'Angle Score',
        data: sampled.map(f => f.angle_score),
        borderColor: '#2ecc71',
        backgroundColor: 'rgba(46, 204, 113, 0.1)',
        fill: true,
        tension: 0.3,
        pointRadius: 0,
      },
      {
        label: 'Pose Similarity',
        data: sampled.map(f => f.cosine_normalized),
        borderColor: '#3498db',
        backgroundColor: 'rgba(52, 152, 219, 0.1)',
        fill: true,
        tension: 0.3,
        pointRadius: 0,
      },
    ],
  }
})

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { labels: { color: '#888' } },
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
