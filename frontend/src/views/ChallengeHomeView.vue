<template>
  <div class="challenge-home">
    <router-link v-if="isAdmin || store.enabledTypes.length > 1" to="/challenges" class="back-link">&larr; All Challenges</router-link>

    <div class="home-header">
      <span class="header-icon">{{ meta.icon }}</span>
      <h1>{{ meta.name }}</h1>
    </div>

    <div class="challenge-cta" @click="startSession">
      <div class="cta-circle cta-circle-tr"></div>
      <div class="cta-circle cta-circle-bl"></div>
      <div class="cta-content">
        <h2 class="cta-title">Ready for Your Next Challenge?</h2>
        <p class="cta-sub">Push your limits and beat your personal record!</p>
        <button class="cta-btn">
          <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="6 3 20 12 6 21 6 3"></polygon></svg>
          Start Challenge Now
        </button>
      </div>
    </div>

    <!-- Rank badge -->
    <div v-if="hasRank" class="rank-badge">
      <span class="rank-sparkle">&#10024;</span>
      Your Rank:
      <template v-if="daily?.user_rank">
        <strong>{{ ordinal(daily?.user_rank) }}</strong> today
      </template>
      <template v-if="daily?.user_rank && weekly?.user_rank">
        &middot;
      </template>
      <template v-if="weekly?.user_rank">
        <strong>{{ ordinal(weekly?.user_rank) }}</strong> this week
      </template>
      <span class="rank-sparkle">&#10024;</span>
    </div>

    <!-- Stats row -->
    <div class="stats-row" v-if="typeStats">
      <div class="stat-box">
        <div class="stat-icon icon-blue">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
        </div>
        <div class="stat-info">
          <span class="stat-val">{{ typeStats.personal_best || 0 }}</span>
          <span class="stat-lbl">Personal Best</span>
        </div>
      </div>
      <div v-if="typeStats.daily_best" class="stat-box">
        <div class="stat-icon icon-orange">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 9H4.5a2.5 2.5 0 0 1 0-5C7 4 7 7 7 7"/><path d="M18 9h1.5a2.5 2.5 0 0 0 0-5C17 4 17 7 17 7"/><path d="M4 22h16"/><path d="M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 20 7 22"/><path d="M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17 20 17 22"/><path d="M18 2H6v7a6 6 0 0 0 12 0V2Z"/></svg>
        </div>
        <div class="stat-info">
          <span class="stat-val">{{ typeStats.daily_best }}</span>
          <span class="stat-lbl">Today's Best</span>
        </div>
      </div>
      <div class="stat-box">
        <div class="stat-icon icon-green">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
        </div>
        <div class="stat-info">
          <span class="stat-val">{{ typeStats.weekly_total || 0 }}</span>
          <span class="stat-lbl">This Week</span>
        </div>
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
              <span class="lb-name">{{ entry.username || entry.email }}</span>
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
              <span class="lb-name">{{ entry.username || entry.email }}</span>
              <span class="lb-score">{{ entry.score }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Session History -->
    <div class="history-section">
      <h2>Session History <span v-if="store.sessionsTotal > 0" class="history-count">({{ store.sessionsTotal }})</span></h2>
      <div v-if="store.sessionsLoading && store.sessions.length === 0" class="history-empty">Loading sessions...</div>
      <div v-else-if="store.sessions.length === 0" class="history-empty">
        No sessions yet. Start your first challenge!
      </div>
      <div v-else class="history-list">
        <div
          v-for="session in store.sessions"
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
        <div v-if="hasMoreSessions" ref="scrollSentinel" class="history-sentinel">
          <span v-if="store.sessionsLoading" class="loading-more">Loading more...</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useChallengesStore } from '../stores/challenges'
import { useAuthStore } from '../stores/auth'

const route = useRoute()
const router = useRouter()
const store = useChallengesStore()
const authStore = useAuthStore()
const isAdmin = computed(() => authStore.user?.is_admin)

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
const hasDailyRank = computed(() => !!daily.value?.user_rank)
const hasRank = computed(() => hasDailyRank.value || !!weekly.value?.user_rank)

const PAGE_SIZE = 10
const hasMoreSessions = computed(() => store.sessions.length < store.sessionsTotal)
const scrollSentinel = ref(null)
let observer = null

function loadSessions() {
  store.fetchSessions({ challengeType: challengeType.value, minScore: 1, limit: PAGE_SIZE, offset: 0 })
}

function loadMoreSessions() {
  if (store.sessionsLoading || !hasMoreSessions.value) return
  store.fetchSessions({
    challengeType: challengeType.value,
    minScore: 1,
    limit: PAGE_SIZE,
    offset: store.sessions.length,
    append: true,
  })
}

function setupObserver() {
  if (observer) observer.disconnect()
  observer = new IntersectionObserver((entries) => {
    if (entries[0]?.isIntersecting) loadMoreSessions()
  }, { rootMargin: '200px' })
}

watch(scrollSentinel, (el) => {
  if (el && observer) observer.observe(el)
})

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
  const d = new Date(dateString)
  return d.toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' }) +
    ', ' + d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })
}

function startSession() {
  router.push(`/challenges/${challengeType.value}/session`)
}

function viewResults(sessionId) {
  router.push(`/challenges/results/${sessionId}`)
}

onMounted(() => {
  store.fetchEnabledChallenges()
  store.fetchStats()
  store.fetchLeaderboard(challengeType.value)
  loadSessions()
  setupObserver()
})

onUnmounted(() => {
  if (observer) observer.disconnect()
})
</script>

<style scoped>
.challenge-home {
  max-width: 800px;
  margin: 0 auto;
  padding: 1rem;
}

.back-link {
  color: var(--text-muted);
  text-decoration: none;
  font-size: 0.9rem;
}
.back-link:hover { color: var(--color-primary); }

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
  color: var(--text-primary);
  margin: 0;
}

/* CTA Card */
.challenge-cta {
  position: relative;
  background: var(--gradient-primary);
  border-radius: var(--radius-lg);
  padding: 2rem;
  margin-bottom: 1.5rem;
  overflow: hidden;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
}

.challenge-cta:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-lg);
}

.cta-circle {
  position: absolute;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.1);
}

.cta-circle-tr {
  width: 16rem;
  height: 16rem;
  top: 0;
  right: 0;
  transform: translate(8rem, -8rem);
}

.cta-circle-bl {
  width: 12rem;
  height: 12rem;
  bottom: 0;
  left: 0;
  transform: translate(-6rem, 6rem);
}

.cta-content {
  position: relative;
  z-index: 1;
}

.cta-title {
  font-size: 1.75rem;
  font-weight: 700;
  color: #fff;
  margin: 0 0 0.5rem;
}

.cta-sub {
  color: rgba(191, 219, 254, 0.9);
  font-size: 1.05rem;
  margin: 0 0 1.5rem;
}

.cta-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  background: #fff;
  color: var(--color-primary);
  border: none;
  border-radius: var(--radius-md);
  padding: 0.85rem 1.5rem;
  font-size: 1.05rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
}

.cta-btn:hover {
  background: #eff6ff;
}

.cta-btn svg {
  width: 20px;
  height: 20px;
}

/* Rank badge */
.rank-badge {
  text-align: center;
  background: var(--color-primary-light);
  border: 1px solid var(--border-color);
  border-radius: 24px;
  padding: 0.6rem 1.25rem;
  color: var(--text-secondary);
  font-size: 0.95rem;
  margin-bottom: 1.5rem;
  animation: badge-glow 3s ease-in-out infinite;
}

.rank-badge strong {
  color: var(--color-primary);
}

.rank-sparkle {
  animation: sparkle-float 2s ease-in-out infinite;
  display: inline-block;
}

@keyframes badge-glow {
  0%, 100% { box-shadow: var(--shadow-md); }
  50% { box-shadow: var(--shadow-lg); }
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
  display: flex;
  align-items: center;
  gap: 0.75rem;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 1.25rem 1rem;
  box-shadow: var(--shadow-md);
}

.stat-icon {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.stat-icon svg {
  width: 22px;
  height: 22px;
}

.icon-blue {
  background: rgba(59, 130, 246, 0.12);
  color: #3b82f6;
}

.icon-orange {
  background: rgba(249, 115, 22, 0.12);
  color: #f97316;
}

.icon-green {
  background: rgba(22, 163, 74, 0.12);
  color: #16a34a;
}

.stat-info {
  display: flex;
  flex-direction: column;
}

.stat-val {
  font-size: 1.5rem;
  font-weight: 700;
  line-height: 1.2;
  color: var(--text-primary);
}

.stat-lbl {
  display: block;
  color: var(--text-muted);
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
  color: var(--text-primary);
  font-size: 1.2rem;
  margin-bottom: 1rem;
}

.leaderboard-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.lb-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 1.25rem;
  box-shadow: var(--shadow-md);
  animation: shimmer 3s ease-in-out infinite;
}

@keyframes shimmer {
  0%, 100% { border-color: var(--border-color); }
  50% { border-color: var(--color-primary); }
}

.lb-card h3 {
  color: #aaa;
  font-size: 0.85rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin: 0 0 1rem;
}

.lb-empty {
  color: var(--text-muted);
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
  border-radius: var(--radius-md);
  background: var(--color-primary-light);
}

.lb-entry.lb-self {
  background: var(--color-primary-light);
  box-shadow: var(--shadow-md);
}

.lb-medal {
  font-size: 1.3rem;
  min-width: 2rem;
  text-align: center;
}

.lb-name {
  flex: 1;
  color: var(--text-secondary);
  font-size: 0.9rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.lb-score {
  color: var(--color-primary);
  font-weight: 700;
  font-size: 1.1rem;
}

/* History */
.history-section h2 {
  color: var(--text-primary);
  font-size: 1.2rem;
  margin-bottom: 1rem;
}

.history-count {
  color: var(--text-muted);
  font-weight: 400;
  font-size: 0.9rem;
}

.history-sentinel {
  text-align: center;
  padding: 1rem 0;
  min-height: 1px;
}

.loading-more {
  color: var(--text-muted);
  font-size: 0.85rem;
}

.history-empty {
  color: var(--text-muted);
  text-align: center;
  padding: 2rem;
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}

.history-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 10px;
  padding: 1rem 1.25rem;
  cursor: pointer;
  transition: all 0.2s;
  box-shadow: var(--shadow-md);
}
.history-card:hover {
  border-color: var(--color-primary);
}

.history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.35rem;
}

.history-score {
  color: var(--color-primary);
  font-weight: 700;
  font-size: 1.05rem;
}

.history-date {
  color: var(--text-muted);
  font-size: 0.85rem;
}

.history-meta {
  display: flex;
  gap: 1.5rem;
  color: var(--text-muted);
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
