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

        <!-- Squat group: per-variant stats table -->
        <div v-if="challenge.isGroup && variantRows(challenge).length" class="variant-table">
          <div class="variant-table-header">
            <span class="vt-col vt-name"></span>
            <span class="vt-col vt-num">Best</span>
            <span class="vt-col vt-num">This Week</span>
          </div>
          <div v-for="row in variantRows(challenge)" :key="row.type" class="variant-table-row">
            <span class="vt-col vt-name">{{ row.label }}</span>
            <span class="vt-col vt-num vt-best">{{ row.best }}</span>
            <span class="vt-col vt-num vt-week">{{ row.week }}</span>
          </div>
        </div>

        <!-- Stats row (non-group only) -->
        <div class="card-stats" v-if="!challenge.isGroup && hasStats(challenge.type)">
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

const SQUAT_SUBTYPES = ['squat_hold', 'squat_half', 'squat_full']

const visibleChallenges = computed(() => {
  if (isAdmin.value) return challenges
  return challenges.filter(c => {
    if (c.isGroup) {
      return c.subtypes.some(st => store.enabledTypes.includes(st))
    }
    return store.enabledTypes.includes(c.type)
  })
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
    name: 'Squats',
    icon: '\u{1F3CB}',
    isGroup: true,
    subtypes: SQUAT_SUBTYPES,
    description: 'Three squat challenges: hold, partial depth, and full depth.',
    metric: 'Reps / Hold',
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

const VARIANT_LABELS = {
  squat_hold: 'Hold',
  squat_half: 'Half',
  squat_full: 'Full',
}

function variantRows(challenge) {
  if (!challenge.isGroup) return []
  return challenge.subtypes
    .filter(st => {
      const s = store.stats[st]
      return s && (s.personal_best || s.weekly_total)
    })
    .map(st => ({
      type: st,
      label: VARIANT_LABELS[st] || st,
      best: store.stats[st]?.personal_best || 0,
      week: store.stats[st]?.weekly_total || 0,
    }))
}

function hasStats(type) {
  const challenge = challenges.find(c => c.type === type)
  if (challenge?.isGroup) {
    return challenge.subtypes.some(st => {
      const s = store.stats[st]
      return s && (s.personal_best || s.weekly_total || s.daily_best)
    })
  }
  const s = store.stats[type]
  return s && (s.personal_best || s.weekly_total || s.daily_best)
}

function getStat(type, key) {
  const challenge = challenges.find(c => c.type === type)
  if (challenge?.isGroup) {
    // Aggregate across subtypes: best = max, weekly = sum, daily = max
    let val = 0
    for (const st of challenge.subtypes) {
      const v = store.stats[st]?.[key] || 0
      if (key === 'weekly_total') val += v
      else val = Math.max(val, v)
    }
    return val
  }
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
  color: var(--text-muted);
  text-decoration: none;
  font-size: 0.9rem;
}

.back-link:hover {
  color: var(--color-primary);
}

.selector-header h1 {
  color: var(--text-primary);
  margin: 0.5rem 0 0.25rem;
}

.subtitle {
  color: var(--text-muted);
}

.challenge-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 1.5rem;
}

.challenge-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 2rem;
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  flex-direction: column;
}

.challenge-card:hover {
  border-color: var(--color-primary);
  transform: translateY(-4px);
  box-shadow: var(--shadow-lg);
}

.card-icon {
  font-size: 2.5rem;
  margin-bottom: 1rem;
}

.challenge-card h2 {
  color: var(--color-primary);
  font-size: 1.2rem;
  margin-bottom: 0.5rem;
}

.challenge-card p {
  color: var(--text-secondary);
  font-size: 0.9rem;
  line-height: 1.5;
  flex: 1;
}

.card-stats {
  display: flex;
  gap: 0;
  margin-top: 1rem;
  padding-top: 0.75rem;
  border-top: 1px solid var(--border-color);
}

.card-stat {
  flex: 1;
  text-align: center;
}

.card-stat + .card-stat {
  border-left: 1px solid var(--border-color);
}

.card-stat-value {
  display: block;
  font-size: 1.3rem;
  font-weight: 700;
  line-height: 1.2;
}

.card-stat-value.best { color: var(--color-primary); }
.card-stat-value.today { color: var(--color-warning); }
.card-stat-value.week { color: var(--color-info); }

.card-stat-label {
  display: block;
  color: var(--text-muted);
  font-size: 0.7rem;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin-top: 0.2rem;
}

/* Variant stats table (inside squat group card) */
.variant-table {
  margin-top: 1rem;
  padding-top: 0.75rem;
  border-top: 1px solid var(--border-color);
}

.variant-table-header {
  display: flex;
  padding: 0 0.25rem 0.4rem;
}

.variant-table-header .vt-col {
  color: var(--text-muted);
  font-size: 0.65rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.variant-table-row {
  display: flex;
  padding: 0.35rem 0.25rem;
  border-top: 1px solid var(--border-color);
}

.vt-col {
  font-size: 0.85rem;
}

.vt-name {
  flex: 1;
  color: var(--text-secondary);
  font-weight: 500;
}

.vt-num {
  width: 5rem;
  text-align: right;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}

.vt-best { color: var(--color-primary); }
.vt-week { color: var(--color-info); }

.start-btn {
  margin-top: 1rem;
  background: var(--color-primary-light);
  border: 1px solid var(--border-color);
  color: var(--color-primary);
  padding: 0.6rem 1rem;
  border-radius: var(--radius-md);
  cursor: pointer;
  font-size: 0.9rem;
  transition: all 0.2s;
}

.start-btn:hover {
  background: var(--color-primary-hover);
  color: var(--text-on-primary);
}

@media (max-width: 640px) {
  .challenge-grid {
    grid-template-columns: 1fr;
  }
}
</style>
