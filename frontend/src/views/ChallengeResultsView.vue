<template>
  <div class="challenge-results">
    <div class="results-header">
      <router-link :to="backLink" class="back-link">&larr; Back to Challenge</router-link>
      <h1>Challenge Complete</h1>
    </div>

    <div v-if="result" class="results-card">
      <div class="result-type">{{ typeLabel }}</div>

      <div class="score-display">
        <span class="score-value">{{ result.score }}</span>
        <span class="score-unit">{{ scoreUnit }}</span>
      </div>

      <div class="stats-grid">
        <div class="stat">
          <span class="stat-value">{{ formatDuration(result.duration_seconds) }}</span>
          <span class="stat-label">Duration</span>
        </div>
        <div class="stat" v-if="result.personal_best !== null && result.personal_best !== undefined">
          <span class="stat-value" :class="{ 'new-pb': isNewPB }">{{ result.personal_best }} {{ scoreUnit }}</span>
          <span class="stat-label">{{ isNewPB ? 'New PB!' : 'Personal Best' }}</span>
        </div>
      </div>

      <!-- Recording Download -->
      <div v-if="hasRecording" class="recording-download">
        <p class="recording-desc">Your annotated session recording is ready.</p>
        <button @click="downloadRecording" class="download-btn" :disabled="downloading">
          <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/>
          </svg>
          {{ downloading ? 'Downloading...' : 'Download Recording' }}
        </button>
      </div>

      <div class="actions">
        <button @click="retry" class="retry-btn">Try Again</button>
        <router-link to="/challenges" class="home-btn">All Challenges</router-link>
      </div>
    </div>

    <div v-else class="loading">
      <p>Loading results...</p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '../api/client'

const route = useRoute()
const router = useRouter()
const sessionId = computed(() => route.params.sessionId)
const result = ref(null)
const hasRecording = ref(false)
const downloading = ref(false)

const TYPE_LABELS = {
  plank: 'Plank Hold',
  squat: 'Max Squats',
  pushup: 'Max Pushups',
}

const backLink = computed(() => result.value?.challenge_type ? `/challenges/${result.value.challenge_type}` : '/challenges')
const typeLabel = computed(() => TYPE_LABELS[result.value?.challenge_type] || 'Challenge')
const scoreUnit = computed(() => result.value?.challenge_type === 'plank' ? 's' : 'reps')
const isNewPB = computed(() => result.value && result.value.score === result.value.personal_best)

function formatDuration(seconds) {
  if (!seconds) return '0:00'
  const m = Math.floor(seconds / 60)
  const s = Math.round(seconds % 60)
  return `${m}:${String(s).padStart(2, '0')}`
}

function retry() {
  if (result.value?.challenge_type) {
    router.push(`/challenges/${result.value.challenge_type}`)
  } else {
    router.push('/challenges')
  }
}

async function downloadRecording() {
  downloading.value = true
  try {
    const response = await api.get(`/api/v1/challenges/sessions/${sessionId.value}/recording`, {
      responseType: 'blob'
    })
    const blob = new Blob([response.data], { type: 'video/mp4' })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `challenge_recording_${sessionId.value}.mp4`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
  } catch (err) {
    console.error('Failed to download recording:', err)
  } finally {
    downloading.value = false
  }
}

onMounted(async () => {
  // Try loading from sessionStorage (set by ChallengeSessionView after live session)
  const stored = sessionStorage.getItem(`challenge_result_${sessionId.value}`)
  if (stored) {
    const data = JSON.parse(stored)
    result.value = data
    hasRecording.value = !!data.has_recording
    sessionStorage.removeItem(`challenge_result_${sessionId.value}`)
    return
  }

  // Fallback: fetch from API (for history navigation)
  try {
    const response = await api.get('/api/v1/challenges/sessions')
    const session = response.data.find(s => s.id === Number(sessionId.value))
    if (session) {
      result.value = session
      hasRecording.value = !!session.has_recording
    }
  } catch (err) {
    console.error('Failed to load session results:', err)
  }
})
</script>

<style scoped>
.challenge-results {
  max-width: 600px;
  margin: 0 auto;
  padding: 1rem;
}

.results-header {
  margin-bottom: 2rem;
}

.back-link {
  color: #888;
  text-decoration: none;
  font-size: 0.9rem;
}
.back-link:hover { color: #4ecca3; }

.results-header h1 {
  color: #eee;
  margin-top: 0.5rem;
}

.results-card {
  background: rgba(22, 33, 62, 0.8);
  border: 1px solid rgba(78, 204, 163, 0.15);
  border-radius: 12px;
  padding: 2.5rem;
  text-align: center;
}

.result-type {
  color: #888;
  font-size: 1rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 1rem;
}

.score-display {
  margin-bottom: 2rem;
}

.score-value {
  font-size: 4rem;
  font-weight: 700;
  color: #4ecca3;
  line-height: 1;
}

.score-unit {
  font-size: 1.2rem;
  color: #888;
  margin-left: 0.5rem;
}

.stats-grid {
  display: flex;
  justify-content: center;
  gap: 3rem;
  margin-bottom: 2rem;
  padding-top: 1.5rem;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
}

.stat {
  text-align: center;
}

.stat-value {
  display: block;
  color: #eee;
  font-size: 1.3rem;
  font-weight: 600;
}

.stat-value.new-pb {
  color: #f1c40f;
}

.stat-label {
  display: block;
  color: #888;
  font-size: 0.8rem;
  margin-top: 0.25rem;
}

.recording-download {
  margin: 1.5rem 0;
  padding: 1.5rem;
  background: #0f0f1a;
  border-radius: 8px;
  text-align: center;
}

.recording-desc {
  color: #888;
  margin-bottom: 1rem;
}

.download-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  background: #4ecca3;
  color: #1a1a2e;
  padding: 0.75rem 1.5rem;
  border-radius: 8px;
  font-weight: 600;
  border: none;
  cursor: pointer;
  font-size: 1rem;
  transition: background 0.2s;
}
.download-btn:hover:not(:disabled) { background: #3db892; }
.download-btn:disabled { background: #888; cursor: not-allowed; }
.download-btn .btn-icon {
  width: 18px;
  height: 18px;
}

.actions {
  display: flex;
  gap: 1rem;
  justify-content: center;
  margin-top: 1rem;
}

.retry-btn {
  background: #4ecca3;
  color: #0a0a1a;
  border: none;
  padding: 0.75rem 2rem;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.2s;
}
.retry-btn:hover { opacity: 0.9; }

.home-btn {
  background: transparent;
  border: 1px solid rgba(78, 204, 163, 0.3);
  color: #4ecca3;
  padding: 0.75rem 2rem;
  border-radius: 8px;
  text-decoration: none;
  transition: all 0.2s;
}
.home-btn:hover { background: rgba(78, 204, 163, 0.1); }

.loading {
  text-align: center;
  color: #888;
  padding: 3rem;
}
</style>
