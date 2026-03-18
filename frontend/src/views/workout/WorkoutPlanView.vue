<template>
  <div class="workout-plan">
    <!-- Header -->
    <header class="plan-header">
      <h1 class="plan-title font-display">{{ todayWorkout?.day_label || 'Workout' }}</h1>
      <div class="plan-header-right">
        <span v-if="todayWorkout?.estimated_minutes" class="plan-duration">{{ todayWorkout.estimated_minutes }} min</span>
        <button v-if="todayWorkout?.has_plan" class="btn-edit-header" @click="handleEditWorkout" title="Edit workout">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M17 3a2.85 2.85 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z"/><path d="m15 5 4 4"/></svg>
        </button>
      </div>
    </header>

    <!-- Progress bar -->
    <div v-if="todayWorkout?.has_plan" class="progress-wrap">
      <div class="progress-bar">
        <div class="progress-fill" :style="{ width: '0%' }"></div>
      </div>
      <p class="progress-label">{{ exercises.length }} exercises</p>
    </div>

    <!-- No plan state -->
    <div v-if="!loading && !todayWorkout?.has_plan" class="empty-state">
      <div
        v-motion
        :initial="{ opacity: 0, y: 20 }"
        :enter="{ opacity: 1, y: 0, transition: { duration: 400 } }"
        class="empty-card glass"
      >
        <span class="empty-emoji">📋</span>
        <h2 class="empty-title font-display">No workout planned</h2>
        <p class="empty-desc">Start a quick workout or build your own plan.</p>
        <div class="empty-actions">
          <router-link to="/workout/quick-start" class="btn-primary">Build Your Own</router-link>
          <router-link to="/workout/exercises" class="btn-secondary glass">Browse Library</router-link>
        </div>
      </div>
    </div>

    <!-- Exercise list -->
    <section v-if="exercises.length > 0" class="exercise-list">
      <h2 class="section-label">Exercises</h2>
      <div class="exercise-cards">
        <div
          v-for="(ex, i) in exercises"
          :key="ex.slug || i"
          v-motion
          :initial="{ opacity: 0, x: -20 }"
          :enter="{ opacity: 1, x: 0, transition: { delay: i * 80 } }"
          class="exercise-row glass"
          @click="router.push(`/workout/exercises/${ex.slug}`)"
        >
          <div class="exercise-number">{{ i + 1 }}</div>
          <div class="exercise-info">
            <h3 class="exercise-name font-display">{{ ex.name }}</h3>
            <p class="exercise-meta">
              {{ ex.sets || 3 }} × {{ ex.reps || 10 }}
              <template v-if="ex.weight"> • {{ ex.weight }}kg</template>
            </p>
          </div>
          <div v-if="isTrackable(ex.slug)" class="tracking-badge">
            <span class="tracking-icon">📷</span>
          </div>
        </div>
      </div>
    </section>

    <!-- Coach message -->
    <section v-if="coachInsight" class="coach-section">
      <div
        v-motion
        :initial="{ opacity: 0, y: 10 }"
        :enter="{ opacity: 1, y: 0, transition: { delay: 400 } }"
        class="coach-bubble glass"
      >
        <div class="coach-inner">
          <div class="coach-avatar">
            <span class="coach-emoji">🦦</span>
          </div>
          <p class="coach-text">"{{ coachInsight }}"</p>
        </div>
      </div>
    </section>

    <!-- Start button -->
    <div v-if="todayWorkout?.has_plan" class="plan-actions">
      <button
        v-motion
        :initial="{ opacity: 0, y: 20 }"
        :enter="{ opacity: 1, y: 0, transition: { delay: 500 } }"
        class="btn-start"
        @click="handleStartWorkout"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="20" height="20">
          <polygon points="5 3 19 12 5 21 5 3"/>
        </svg>
        Start Workout
      </button>
    </div>

    <!-- Toast -->
    <div v-if="toast" class="toast" @click="toast = null">{{ toast }}</div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useWorkoutStore } from '../../stores/workout'

const router = useRouter()
const workoutStore = useWorkoutStore()

const loading = ref(true)
const todayWorkout = ref(null)
const toast = ref(null)

const TRACKABLE_SLUGS = [
  'push-up', 'bodyweight-squat', 'plank', 'squat-hold', 'jump-squat', 'burpee',
  'bicep-curl', 'lateral-raise', 'calf-raise',
]

function isTrackable(slug) {
  return TRACKABLE_SLUGS.includes(slug)
}

const exercises = computed(() => todayWorkout.value?.exercises || [])
const coachInsight = computed(() => todayWorkout.value?.insight || '')

async function handleStartWorkout() {
  try {
    const result = await workoutStore.startSession({})
    const sid = result.data?.session_id
    if (sid) {
      // Skip pre-workout chat — go straight to first exercise
      await workoutStore.sendAction(sid, 'begin_workout', {})
      router.push(`/workout/session/${sid}`)
    }
  } catch {
    toast.value = 'Failed to start workout'
    setTimeout(() => { toast.value = null }, 3000)
  }
}

async function handleEditWorkout() {
  try {
    const result = await workoutStore.startSession({})
    const sid = result.data?.session_id
    if (sid) {
      router.push(`/workout/session/${sid}?edit=1`)
    }
  } catch {
    toast.value = 'Failed to load workout'
    setTimeout(() => { toast.value = null }, 3000)
  }
}

onMounted(async () => {
  try {
    await workoutStore.fetchProfile()
    todayWorkout.value = await workoutStore.fetchTodayWorkout()
  } catch {
    // May fail for new users
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.workout-plan {
  padding-bottom: 2rem;
}

/* Header */
.plan-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  padding: 2.5rem 1.5rem 1rem;
}

.plan-title {
  font-size: 1.75rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: -0.02em;
  color: var(--text-primary);
}

.plan-header-right {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.plan-duration {
  font-size: 0.875rem;
  color: var(--text-muted);
  font-weight: 600;
}

.btn-edit-header {
  width: 32px;
  height: 32px;
  border: none;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.08);
  color: var(--text-muted);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s;
}

.btn-edit-header:hover {
  background: var(--color-primary-light);
  color: var(--color-primary);
}

/* Progress */
.progress-wrap {
  padding: 0 1.5rem;
  margin-bottom: 1.5rem;
}

.progress-bar {
  height: 6px;
  border-radius: 3px;
  background: var(--text-muted);
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: var(--color-primary);
  border-radius: 3px;
  transition: width 0.3s ease;
}

.progress-label {
  font-size: 0.75rem;
  color: var(--text-muted);
  margin-top: 0.5rem;
}

/* Empty state */
.empty-state {
  padding: 3rem 1.5rem;
}

.empty-card {
  padding: 2rem;
  border-radius: 1rem;
  text-align: center;
}

.empty-emoji {
  font-size: 2.5rem;
  display: block;
  margin-bottom: 1rem;
}

.empty-title {
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 0.5rem;
}

.empty-desc {
  font-size: 0.875rem;
  color: var(--text-muted);
  margin-bottom: 1.5rem;
}

.empty-actions {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

/* Section label */
.section-label {
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--text-muted);
  margin-bottom: 0.75rem;
}

/* Exercise list */
.exercise-list {
  padding: 0 1.5rem;
  margin-bottom: 1.5rem;
}

.exercise-cards {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.exercise-row {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1.25rem;
  border-radius: 1rem;
  cursor: pointer;
  transition: border-color 0.15s;
}

.exercise-row:hover {
  border-color: var(--color-primary);
}

.exercise-row:active {
  transform: scale(0.99);
}

.exercise-number {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: linear-gradient(135deg, rgba(242, 101, 34, 0.2), rgba(242, 101, 34, 0.05));
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 0.875rem;
  color: var(--color-primary);
  flex-shrink: 0;
}

.exercise-info {
  flex: 1;
  min-width: 0;
}

.exercise-name {
  font-size: 1rem;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 0.15rem;
}

.exercise-meta {
  font-size: 0.8rem;
  color: var(--text-muted);
}

.tracking-badge {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: rgba(20, 184, 166, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.tracking-icon {
  font-size: 0.85rem;
}

/* Coach */
.coach-section {
  padding: 0 1.5rem;
  margin-bottom: 1.5rem;
}

.coach-bubble {
  padding: 1rem;
  border-radius: 1rem;
}

.coach-inner {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
}

.coach-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: var(--gradient-secondary);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.coach-emoji {
  font-size: 1.15rem;
}

.coach-text {
  font-size: 0.875rem;
  color: var(--text-primary);
  opacity: 0.9;
  font-style: italic;
  line-height: 1.6;
  flex: 1;
}

/* Actions */
.plan-actions {
  padding: 1rem 1.5rem;
  padding-bottom: calc(1rem + env(safe-area-inset-bottom, 0px));
}

.btn-start {
  width: 100%;
  padding: 1rem;
  border: none;
  border-radius: 0.75rem;
  background: var(--gradient-primary);
  color: var(--text-on-primary);
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 1rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  box-shadow: var(--glow-primary);
  transition: transform 0.15s;
}

.btn-start:active {
  transform: scale(0.98);
}

.btn-primary {
  display: inline-block;
  padding: 0.75rem 1.5rem;
  background: var(--gradient-primary);
  color: var(--text-on-primary);
  border: none;
  border-radius: 0.75rem;
  font-weight: 700;
  font-size: 0.9rem;
  cursor: pointer;
  text-decoration: none;
  text-align: center;
  box-shadow: var(--glow-primary);
}

.btn-secondary {
  display: inline-block;
  padding: 0.75rem 1.5rem;
  border-radius: 0.75rem;
  font-weight: 700;
  font-size: 0.9rem;
  cursor: pointer;
  text-decoration: none;
  text-align: center;
  color: var(--text-primary);
}

/* Toast */
.toast {
  position: fixed;
  bottom: 5rem;
  left: 50%;
  transform: translateX(-50%);
  padding: 0.65rem 1.25rem;
  background: var(--bg-card);
  color: var(--text-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-full);
  font-size: 0.8rem;
  font-weight: 500;
  z-index: 100;
  max-width: 90%;
  text-align: center;
}
</style>
