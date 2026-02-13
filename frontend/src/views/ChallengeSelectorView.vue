<template>
  <div class="challenge-selector">
    <div class="selector-header">
      <router-link v-if="isAdmin" to="/hub" class="back-link">&larr; Back to Hub</router-link>
      <h1>Challenges</h1>
      <p class="subtitle">Pick a challenge and test your limits</p>
    </div>

    <div class="challenge-grid">
      <div
        v-for="challenge in visibleChallenges"
        :key="challenge.type"
        class="challenge-card"
        @click="startChallenge(challenge.type)"
      >
        <div class="card-icon">{{ challenge.icon }}</div>
        <h2>{{ challenge.name }}</h2>
        <p>{{ challenge.description }}</p>

        <!-- Stats row -->
        <div class="card-stats" v-if="hasStats(challenge.type)">
          <div class="card-stat">
            <span class="card-stat-value best">{{ getStat(challenge.type, 'personal_best') }}</span>
            <span class="card-stat-label">Best</span>
          </div>
          <div class="card-stat">
            <span class="card-stat-value today">{{ getStat(challenge.type, 'daily_best') }}</span>
            <span class="card-stat-label">Today</span>
          </div>
          <div class="card-stat">
            <span class="card-stat-value week">{{ getStat(challenge.type, 'weekly_total') }}</span>
            <span class="card-stat-label">This Week</span>
          </div>
        </div>

        <button class="start-btn">Start &rarr;</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useChallengesStore } from '../stores/challenges'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const store = useChallengesStore()
const authStore = useAuthStore()
const isAdmin = computed(() => authStore.user?.is_admin)

const visibleChallenges = computed(() => {
  if (isAdmin.value) return challenges
  return challenges.filter(c => store.enabledTypes.includes(c.type))
})

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

function hasStats(type) {
  const s = store.stats[type]
  return s && (s.personal_best || s.weekly_total || s.daily_best)
}

function getStat(type, key) {
  return store.stats[type]?.[key] || 0
}

function startChallenge(type) {
  router.push(`/challenges/${type}`)
}

onMounted(async () => {
  await store.fetchEnabledChallenges()
  await store.fetchSessions()

  // First-time non-admin user with single enabled type and no past sessions → go straight to challenge home
  if (!isAdmin.value && store.enabledTypes.length === 1 && store.sessions.length === 0) {
    router.replace(`/challenges/${store.enabledTypes[0]}`)
    return
  }

  store.fetchStats()
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

.card-stats {
  display: flex;
  gap: 0;
  margin-top: 1rem;
  padding-top: 0.75rem;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
}

.card-stat {
  flex: 1;
  text-align: center;
}

.card-stat + .card-stat {
  border-left: 1px solid rgba(255, 255, 255, 0.05);
}

.card-stat-value {
  display: block;
  font-size: 1.3rem;
  font-weight: 700;
  line-height: 1.2;
}

.card-stat-value.best { color: #4ecca3; }
.card-stat-value.today { color: #f9ca24; }
.card-stat-value.week { color: #42a5f5; }

.card-stat-label {
  display: block;
  color: #666;
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin-top: 0.2rem;
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

@media (max-width: 640px) {
  .challenge-grid {
    grid-template-columns: 1fr;
  }
}
</style>
