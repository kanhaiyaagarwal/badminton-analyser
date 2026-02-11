<template>
  <div class="challenge-selector">
    <div class="selector-header">
      <router-link to="/hub" class="back-link">&larr; Back to Hub</router-link>
      <h1>Challenges</h1>
      <p class="subtitle">Pick a challenge and test your limits</p>
    </div>

    <div class="challenge-grid">
      <div
        v-for="challenge in challenges"
        :key="challenge.type"
        class="challenge-card"
        @click="startChallenge(challenge.type)"
      >
        <div class="card-icon">{{ challenge.icon }}</div>
        <h2>{{ challenge.name }}</h2>
        <p>{{ challenge.description }}</p>
        <div class="card-metric">
          <span class="metric-label">{{ challenge.metric }}</span>
          <span v-if="personalRecords[challenge.type]" class="metric-value">
            PB: {{ personalRecords[challenge.type] }} {{ challenge.unit }}
          </span>
        </div>
        <button class="start-btn">Start &rarr;</button>
      </div>
    </div>

    <!-- Recent Sessions -->
    <div class="sessions-section">
      <h2>Recent Sessions</h2>
      <div v-if="store.loading" class="sessions-loading">Loading sessions...</div>
      <div v-else-if="store.sessions.length === 0" class="sessions-empty">
        No sessions yet. Pick a challenge above to get started!
      </div>
      <div v-else class="sessions-list">
        <div v-for="session in store.sessions" :key="session.id" class="session-card">
          <div class="session-header">
            <div class="session-type">
              <span class="session-icon">{{ challengeIcon(session.challenge_type) }}</span>
              <span class="session-name">{{ challengeName(session.challenge_type) }}</span>
            </div>
            <span :class="['session-status', session.status]">{{ session.status }}</span>
          </div>
          <div class="session-stats">
            <div class="session-stat">
              <span class="session-stat-value">{{ session.score ?? '-' }}</span>
              <span class="session-stat-label">{{ session.challenge_type === 'plank' ? 'seconds' : 'reps' }}</span>
            </div>
            <div class="session-stat">
              <span class="session-stat-value">{{ formatDuration(session.duration_seconds) }}</span>
              <span class="session-stat-label">duration</span>
            </div>
            <div class="session-stat">
              <span class="session-stat-value">{{ formatDate(session.created_at) }}</span>
              <span class="session-stat-label">date</span>
            </div>
          </div>
          <div v-if="session.has_recording" class="session-actions">
            <button
              @click="downloadRecording(session.id)"
              class="download-btn"
              :disabled="downloadingId === session.id"
            >
              <svg class="dl-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/>
              </svg>
              {{ downloadingId === session.id ? 'Downloading...' : 'Download Recording' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useChallengesStore } from '../stores/challenges'
import api from '../api/client'

const router = useRouter()
const store = useChallengesStore()
const personalRecords = store.personalRecords
const downloadingId = ref(null)

const challenges = [
  {
    type: 'plank',
    name: 'Plank Hold',
    icon: '\u{1F9D8}',
    description: 'Hold a plank position as long as you can. The timer only counts when your form is correct.',
    metric: 'Hold Time',
    unit: 's',
  },
  {
    type: 'squat',
    name: 'Max Squats',
    icon: '\u{1F3CB}',
    description: 'Do as many squats as you can. Full range of motion required for each rep to count.',
    metric: 'Max Reps',
    unit: 'reps',
  },
  {
    type: 'pushup',
    name: 'Max Pushups',
    icon: '\u{1F4AA}',
    description: 'Crank out as many pushups as possible. Elbows must bend below 90 degrees each rep.',
    metric: 'Max Reps',
    unit: 'reps',
  },
]

const CHALLENGE_META = {
  plank: { name: 'Plank Hold', icon: '\u{1F9D8}' },
  squat: { name: 'Max Squats', icon: '\u{1F3CB}' },
  pushup: { name: 'Max Pushups', icon: '\u{1F4AA}' },
}

function challengeIcon(type) {
  return CHALLENGE_META[type]?.icon || ''
}

function challengeName(type) {
  return CHALLENGE_META[type]?.name || type
}

function formatDuration(seconds) {
  if (!seconds) return '0:00'
  const m = Math.floor(seconds / 60)
  const s = Math.round(seconds % 60)
  return `${m}:${String(s).padStart(2, '0')}`
}

function formatDate(dateString) {
  if (!dateString) return 'N/A'
  return new Date(dateString).toLocaleDateString()
}

function startChallenge(type) {
  router.push(`/challenges/${type}`)
}

async function downloadRecording(sessionId) {
  downloadingId.value = sessionId
  try {
    const response = await api.get(`/api/v1/challenges/sessions/${sessionId}/recording`, {
      responseType: 'blob'
    })
    const blob = new Blob([response.data], { type: 'video/mp4' })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `challenge_recording_${sessionId}.mp4`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
  } catch (err) {
    alert('Failed to download recording')
  } finally {
    downloadingId.value = null
  }
}

onMounted(() => {
  store.fetchRecords()
  store.fetchSessions()
})
</script>

<style scoped>
.challenge-selector {
  max-width: 1000px;
  margin: 0 auto;
  padding: 1rem;
}

.selector-header {
  margin-bottom: 2rem;
}

.back-link {
  color: #888;
  text-decoration: none;
  font-size: 0.9rem;
}

.back-link:hover {
  color: #4ecca3;
}

.selector-header h1 {
  color: #eee;
  margin: 0.5rem 0 0.25rem;
}

.subtitle {
  color: #888;
}

.challenge-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 1.5rem;
}

.challenge-card {
  background: rgba(22, 33, 62, 0.8);
  border: 1px solid rgba(78, 204, 163, 0.15);
  border-radius: 12px;
  padding: 2rem;
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  flex-direction: column;
}

.challenge-card:hover {
  border-color: #4ecca3;
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(78, 204, 163, 0.15);
}

.card-icon {
  font-size: 2.5rem;
  margin-bottom: 1rem;
}

.challenge-card h2 {
  color: #4ecca3;
  font-size: 1.2rem;
  margin-bottom: 0.5rem;
}

.challenge-card p {
  color: #aaa;
  font-size: 0.9rem;
  line-height: 1.5;
  flex: 1;
}

.card-metric {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 1rem;
  padding-top: 0.75rem;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
}

.metric-label {
  color: #888;
  font-size: 0.85rem;
}

.metric-value {
  color: #4ecca3;
  font-weight: 600;
  font-size: 0.9rem;
}

.start-btn {
  margin-top: 1rem;
  background: rgba(78, 204, 163, 0.15);
  border: 1px solid rgba(78, 204, 163, 0.3);
  color: #4ecca3;
  padding: 0.6rem 1rem;
  border-radius: 8px;
  cursor: pointer;
  font-size: 0.9rem;
  transition: all 0.2s;
}

.start-btn:hover {
  background: rgba(78, 204, 163, 0.25);
}

/* Recent Sessions */
.sessions-section {
  margin-top: 3rem;
  padding-top: 2rem;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
}

.sessions-section h2 {
  color: #eee;
  margin-bottom: 1rem;
  font-size: 1.2rem;
}

.sessions-loading,
.sessions-empty {
  color: #888;
  text-align: center;
  padding: 2rem;
}

.sessions-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.session-card {
  background: rgba(22, 33, 62, 0.8);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 10px;
  padding: 1.25rem;
}

.session-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.75rem;
}

.session-type {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.session-icon {
  font-size: 1.2rem;
}

.session-name {
  color: #eee;
  font-weight: 600;
}

.session-status {
  padding: 0.15rem 0.6rem;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
}

.session-status.ended,
.session-status.completed {
  background: rgba(78, 204, 163, 0.15);
  color: #4ecca3;
}

.session-status.active,
.session-status.streaming {
  background: rgba(231, 76, 60, 0.15);
  color: #e74c3c;
}

.session-stats {
  display: flex;
  gap: 2rem;
}

.session-stat-value {
  display: block;
  color: #ccc;
  font-size: 0.95rem;
  font-weight: 600;
}

.session-stat-label {
  display: block;
  color: #666;
  font-size: 0.75rem;
  margin-top: 0.15rem;
}

.session-actions {
  margin-top: 0.75rem;
  padding-top: 0.75rem;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
}

.download-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  background: transparent;
  border: 1px solid #4ecca3;
  color: #4ecca3;
  padding: 0.4rem 0.9rem;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.85rem;
  transition: all 0.2s;
}

.download-btn:hover:not(:disabled) {
  background: #4ecca3;
  color: #1a1a2e;
}

.download-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.download-btn .dl-icon {
  width: 14px;
  height: 14px;
}
</style>
