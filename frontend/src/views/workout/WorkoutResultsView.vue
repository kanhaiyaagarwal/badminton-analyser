<template>
  <div class="results-page">
    <router-link to="/workout" class="back-link">&larr; Back</router-link>

    <div v-if="loading" class="loading">
      <div class="spinner"></div>
      <p>Loading results...</p>
    </div>

    <div v-else-if="error" class="error-msg">{{ error }}</div>

    <div v-else-if="summary" class="results-content">
      <!-- Check icon + title -->
      <div
        v-motion
        :initial="{ opacity: 0, scale: 0.8 }"
        :enter="{ opacity: 1, scale: 1, transition: { type: 'spring', stiffness: 200, damping: 15 } }"
        class="results-hero"
      >
        <div class="check-circle">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" width="32" height="32">
            <polyline points="20 6 9 17 4 12"/>
          </svg>
        </div>
        <h1 class="results-title">Great workout!</h1>
        <p class="results-date">{{ formattedDate }}</p>
      </div>

      <!-- Stat cards -->
      <div class="stat-cards">
        <div
          v-motion
          :initial="{ opacity: 0, y: 20 }"
          :enter="{ opacity: 1, y: 0, transition: { delay: 200 } }"
          class="stat-card glass"
        >
          <span class="stat-value">{{ summary.duration_minutes || 0 }}</span>
          <span class="stat-label">Minutes</span>
        </div>
        <div
          v-motion
          :initial="{ opacity: 0, y: 20 }"
          :enter="{ opacity: 1, y: 0, transition: { delay: 300 } }"
          class="stat-card glass"
        >
          <span class="stat-value accent">{{ summary.exercises_completed || 0 }}</span>
          <span class="stat-label">Exercises</span>
        </div>
        <div
          v-motion
          :initial="{ opacity: 0, y: 20 }"
          :enter="{ opacity: 1, y: 0, transition: { delay: 400 } }"
          class="stat-card glass"
        >
          <span class="stat-value">{{ summary.total_sets || 0 }}</span>
          <span class="stat-label">Sets</span>
        </div>
      </div>

      <div
        v-if="summary.total_volume_kg > 0"
        v-motion
        :initial="{ opacity: 0, y: 20 }"
        :enter="{ opacity: 1, y: 0, transition: { delay: 500 } }"
        class="volume-card glass"
      >
        <span class="volume-value">{{ summary.total_volume_kg }}kg</span>
        <span class="volume-label">Total Volume</span>
      </div>

      <!-- PRs -->
      <div
        v-if="summary.prs?.length > 0"
        v-motion
        :initial="{ opacity: 0, y: 20 }"
        :enter="{ opacity: 1, y: 0, transition: { delay: 600 } }"
        class="prs-section"
      >
        <h3 class="section-title">Personal Records</h3>
        <div v-for="(pr, i) in summary.prs" :key="i" class="pr-row">
          <span class="pr-badge">PR</span>
          <span class="pr-text">
            {{ pr.exercise }} — {{ pr.value }}{{ pr.type === 'weight' ? 'kg' : ' reps' }}
          </span>
        </div>
      </div>

      <!-- Coach summary -->
      <div
        v-if="summary.coach_summary"
        v-motion
        :initial="{ opacity: 0, y: 20 }"
        :enter="{ opacity: 1, y: 0, transition: { delay: 700 } }"
        class="coach-bubble"
      >
        <div class="coach-avatar-ring">
          <img src="/mascot/otter-mascot.png" alt="Coach" class="coach-avatar" />
        </div>
        <div class="coach-text glass">{{ summary.coach_summary }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import api from '../../api/client'

const route = useRoute()
const loading = ref(true)
const error = ref(null)
const summary = ref(null)
const sessionDate = ref(null)

const formattedDate = computed(() => {
  if (!sessionDate.value) return ''
  return new Date(sessionDate.value).toLocaleDateString('en-US', {
    weekday: 'long',
    month: 'short',
    day: 'numeric',
  })
})

onMounted(async () => {
  try {
    // Use the end_workout action to get summary for a completed session
    const sid = route.params.sessionId
    const res = await api.post(`/api/v1/workout/sessions/${sid}/action`, {
      action: 'end_workout',
      params: {},
    })
    if (res.data.view === 'summary') {
      summary.value = res.data.data
    }
  } catch (err) {
    error.value = err.response?.data?.detail || 'Failed to load results'
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.results-page {
  padding: 1.25rem;
}

.back-link {
  color: var(--text-muted);
  text-decoration: none;
  font-size: 0.85rem;
}

.loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 3rem 0;
  gap: 0.75rem;
  color: var(--text-muted);
}

.spinner {
  width: 28px;
  height: 28px;
  border: 3px solid var(--border-color);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

.error-msg {
  padding: 2rem;
  text-align: center;
  color: var(--color-destructive);
}

/* Hero */
.results-hero {
  text-align: center;
  margin-top: 1rem;
  margin-bottom: 1.5rem;
}

.check-circle {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: var(--color-success);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 0.75rem;
  box-shadow: var(--glow-secondary);
}

.results-title {
  font-family: var(--font-display);
  font-size: 1.5rem;
  font-weight: 800;
  color: var(--text-primary);
}

.results-date {
  font-size: 0.85rem;
  color: var(--text-muted);
  margin-top: 0.25rem;
}

.stat-cards {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.stat-card {
  flex: 1;
  padding: 0.85rem 0.5rem;
  border-radius: var(--radius-md);
  text-align: center;
}

.stat-value {
  display: block;
  font-family: var(--font-display);
  font-size: 1.35rem;
  font-weight: 800;
  color: var(--color-primary);
}

.stat-value.accent {
  color: var(--color-secondary);
}

.stat-label {
  font-size: 0.65rem;
  color: var(--text-muted);
  text-transform: uppercase;
}

.volume-card {
  text-align: center;
  padding: 0.85rem;
  border-radius: var(--radius-md);
  margin-bottom: 1.25rem;
}

.volume-value {
  display: block;
  font-family: var(--font-display);
  font-size: 1.25rem;
  font-weight: 800;
  color: var(--color-primary);
}

.volume-label {
  font-size: 0.65rem;
  color: var(--text-muted);
  text-transform: uppercase;
}

.section-title {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 0.5rem;
}

.prs-section {
  margin-bottom: 1.25rem;
}

.pr-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.4rem 0;
}

.pr-badge {
  padding: 0.15rem 0.45rem;
  border-radius: var(--radius-full);
  background: var(--color-warning);
  color: var(--text-on-primary);
  font-size: 0.65rem;
  font-weight: 700;
}

.pr-text {
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--text-primary);
}

.coach-bubble {
  display: flex;
  align-items: flex-start;
  gap: 0.65rem;
}

.coach-avatar-ring {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: var(--gradient-secondary);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  padding: 2px;
}

.coach-avatar {
  width: 100%;
  height: 100%;
  border-radius: 50%;
  object-fit: cover;
}

.coach-text {
  padding: 0.65rem 0.85rem;
  border-radius: 0 var(--radius-md) var(--radius-md) var(--radius-md);
  font-size: 0.85rem;
  color: var(--text-secondary);
  line-height: 1.4;
  font-style: italic;
}
</style>
