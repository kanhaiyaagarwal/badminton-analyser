<template>
  <div class="challenge-home">
    <router-link to="/challenges" class="back-link">&larr; All Challenges</router-link>

    <div class="home-header">
      <span class="header-icon">{{ meta.icon }}</span>
      <h1>{{ meta.name }}</h1>
    </div>

    <button class="start-challenge-btn" @click="startSession">
      Start Challenge &rarr;
    </button>

    <!-- Rank badge -->
    <div v-if="hasRank" class="rank-badge">
      <span class="rank-sparkle">&#10024;</span>
      Your Rank:
      <strong>{{ ordinal(daily?.user_rank) }}</strong> today
      <template v-if="weekly?.user_rank">
        &middot; <strong>{{ ordinal(weekly?.user_rank) }}</strong> this week
      </template>
      <span class="rank-sparkle">&#10024;</span>
    </div>

    <!-- Stats row -->
    <div class="stats-row" v-if="typeStats">
      <div class="stat-box">
        <span class="stat-val best">{{ typeStats.personal_best || 0 }}</span>
        <span class="stat-lbl">Personal Best</span>
      </div>
      <div class="stat-box">
        <span class="stat-val today">{{ typeStats.daily_best || 0 }}</span>
        <span class="stat-lbl">Today's Best</span>
      </div>
      <div class="stat-box">
        <span class="stat-val week">{{ typeStats.weekly_total || 0 }}</span>
        <span class="stat-lbl">This Week</span>
      </div>
    </div>

    <!-- Leaderboard -->
    <div class="leaderboard-section">
      <h2>Leaderboard</h2>
      <div class="leaderboard-grid">
        <!-- Daily -->
        <div class="lb-card">
          <h3>Today's Best</h3>
          <div v-if="!daily?.entries?.length" class="lb-empty">No scores yet. Be the first!</div>
          <div v-else class="lb-list">
            <div
              v-for="entry in daily.entries"
              :key="'d-' + entry.rank"
              :class="['lb-entry', { 'lb-self': entry.is_self }]"
            >
              <span class="lb-medal">{{ medalFor(entry.rank) }}</span>
              <span class="lb-email">{{ entry.email }}</span>
              <span class="lb-score">{{ entry.score }}</span>
            </div>
          </div>
        </div>

        <!-- Weekly -->
        <div class="lb-card">
          <h3>This Week's Best</h3>
          <div v-if="!weekly?.entries?.length" class="lb-empty">No scores yet. Be the first!</div>
          <div v-else class="lb-list">
            <div
              v-for="entry in weekly.entries"
              :key="'w-' + entry.rank"
              :class="['lb-entry', { 'lb-self': entry.is_self }]"
            >
              <span class="lb-medal">{{ medalFor(entry.rank) }}</span>
              <span class="lb-email">{{ entry.email }}</span>
              <span class="lb-score">{{ entry.score }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Session History -->
    <div class="history-section">
      <h2>Session History</h2>
      <div v-if="store.loading" class="history-empty">Loading sessions...</div>
      <div v-else-if="typeSessions.length === 0" class="history-empty">
        No sessions yet. Start your first challenge!
      </div>
      <div v-else class="history-list">
        <div
          v-for="session in typeSessions"
          :key="session.id"
          class="history-card"
          @click="viewResults(session.id)"
        >
          <div class="history-header">
            <span class="history-score">{{ session.score }} {{ scoreUnit }}</span>
            <span class="history-date">{{ formatDate(session.created_at) }}</span>
          </div>
          <div class="history-meta">
            <span>{{ formatDuration(session.duration_seconds) }}</span>
            <span v-if="session.personal_best" class="history-pb">PB {{ session.personal_best }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useChallengesStore } from '../stores/challenges'

const route = useRoute()
const router = useRouter()
const store = useChallengesStore()

const challengeType = computed(() => route.params.type)

const CHALLENGE_META = {
  plank: { name: 'Plank Hold', icon: '\u{1F9D8}', unit: 's' },
  squat: { name: 'Max Squats', icon: '\u{1F3CB}', unit: 'reps' },
  pushup: { name: 'Max Pushups', icon: '\u{1F4AA}', unit: 'reps' },
}

const meta = computed(() => CHALLENGE_META[challengeType.value] || CHALLENGE_META.pushup)
const scoreUnit = computed(() => meta.value.unit)
const typeStats = computed(() => store.stats[challengeType.value])

const daily = computed(() => store.leaderboard?.daily)
const weekly = computed(() => store.leaderboard?.weekly)
const hasRank = computed(() => daily.value?.user_rank || weekly.value?.user_rank)

const typeSessions = computed(() =>
  store.sessions.filter(s => s.challenge_type === challengeType.value)
)

function ordinal(n) {
  if (!n) return '-'
  const s = ['th', 'st', 'nd', 'rd']
  const v = n % 100
  return n + (s[(v - 20) % 10] || s[v] || s[0])
}

function medalFor(rank) {
  if (rank === 1) return '\u{1F947}'
  if (rank === 2) return '\u{1F948}'
  if (rank === 3) return '\u{1F949}'
  return `#${rank}`
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

function startSession() {
  router.push(`/challenges/${challengeType.value}/session`)
}

function viewResults(sessionId) {
  router.push(`/challenges/results/${sessionId}`)
}

onMounted(() => {
  store.fetchStats()
  store.fetchLeaderboard(challengeType.value)
  store.fetchSessions()
})
</script>

<style scoped>
.challenge-home {
  max-width: 800px;
  margin: 0 auto;
  padding: 1rem;
}

.back-link {
  color: #888;
  text-decoration: none;
  font-size: 0.9rem;
}
.back-link:hover { color: #4ecca3; }

.home-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin: 1rem 0 1.5rem;
}

.header-icon {
  font-size: 2.5rem;
}

.home-header h1 {
  color: #eee;
  margin: 0;
}

.start-challenge-btn {
  width: 100%;
  background: #4ecca3;
  color: #0a0a1a;
  border: none;
  padding: 1rem;
  border-radius: 12px;
  font-size: 1.2rem;
  font-weight: 700;
  cursor: pointer;
  transition: opacity 0.2s;
  margin-bottom: 1.5rem;
}
.start-challenge-btn:hover { opacity: 0.9; }

/* Rank badge */
.rank-badge {
  text-align: center;
  background: rgba(78, 204, 163, 0.08);
  border: 1px solid rgba(78, 204, 163, 0.2);
  border-radius: 24px;
  padding: 0.6rem 1.25rem;
  color: #ccc;
  font-size: 0.95rem;
  margin-bottom: 1.5rem;
  animation: badge-glow 3s ease-in-out infinite;
}

.rank-badge strong {
  color: #4ecca3;
}

.rank-sparkle {
  animation: sparkle-float 2s ease-in-out infinite;
  display: inline-block;
}

@keyframes badge-glow {
  0%, 100% { box-shadow: 0 0 8px rgba(78, 204, 163, 0.1); }
  50% { box-shadow: 0 0 16px rgba(78, 204, 163, 0.25); }
}

@keyframes sparkle-float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-3px); }
}

/* Stats row */
.stats-row {
  display: flex;
  gap: 1rem;
  margin-bottom: 2rem;
}

.stat-box {
  flex: 1;
  text-align: center;
  background: rgba(22, 33, 62, 0.8);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 10px;
  padding: 1rem 0.5rem;
}

.stat-val {
  display: block;
  font-size: 1.5rem;
  font-weight: 700;
  line-height: 1.2;
}
.stat-val.best { color: #4ecca3; }
.stat-val.today { color: #f9ca24; }
.stat-val.week { color: #42a5f5; }

.stat-lbl {
  display: block;
  color: #666;
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin-top: 0.3rem;
}

/* Leaderboard */
.leaderboard-section {
  margin-bottom: 2rem;
}

.leaderboard-section h2 {
  color: #eee;
  font-size: 1.2rem;
  margin-bottom: 1rem;
}

.leaderboard-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.lb-card {
  background: rgba(22, 33, 62, 0.8);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 12px;
  padding: 1.25rem;
  animation: shimmer 3s ease-in-out infinite;
}

@keyframes shimmer {
  0%, 100% { border-color: rgba(255, 255, 255, 0.05); }
  50% { border-color: rgba(78, 204, 163, 0.15); }
}

.lb-card h3 {
  color: #aaa;
  font-size: 0.85rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin: 0 0 1rem;
}

.lb-empty {
  color: #666;
  text-align: center;
  padding: 1.5rem 0;
  font-size: 0.9rem;
}

.lb-list {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}

.lb-entry {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.6rem 0.75rem;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.02);
}

.lb-entry.lb-self {
  background: rgba(78, 204, 163, 0.08);
  box-shadow: 0 0 12px rgba(78, 204, 163, 0.15);
}

.lb-medal {
  font-size: 1.3rem;
  min-width: 2rem;
  text-align: center;
}

.lb-email {
  flex: 1;
  color: #ccc;
  font-size: 0.9rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.lb-score {
  color: #4ecca3;
  font-weight: 700;
  font-size: 1.1rem;
}

/* History */
.history-section h2 {
  color: #eee;
  font-size: 1.2rem;
  margin-bottom: 1rem;
}

.history-empty {
  color: #888;
  text-align: center;
  padding: 2rem;
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}

.history-card {
  background: rgba(22, 33, 62, 0.8);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 10px;
  padding: 1rem 1.25rem;
  cursor: pointer;
  transition: all 0.2s;
}
.history-card:hover {
  border-color: rgba(78, 204, 163, 0.3);
}

.history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.35rem;
}

.history-score {
  color: #4ecca3;
  font-weight: 700;
  font-size: 1.05rem;
}

.history-date {
  color: #666;
  font-size: 0.85rem;
}

.history-meta {
  display: flex;
  gap: 1.5rem;
  color: #888;
  font-size: 0.85rem;
}

.history-pb {
  color: #f1c40f;
  font-weight: 600;
}

/* Mobile */
@media (max-width: 640px) {
  .leaderboard-grid {
    grid-template-columns: 1fr;
  }

  .rank-badge {
    font-size: 0.85rem;
    padding: 0.5rem 1rem;
  }

  .stats-row {
    flex-wrap: wrap;
  }

  .stat-box {
    min-width: calc(50% - 0.5rem);
  }

  .history-card {
    padding: 0.75rem 1rem;
  }
}
</style>
