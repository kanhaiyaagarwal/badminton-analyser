<template>
  <div class="workout-home">
    <!-- Greeting -->
    <div class="greeting-section">
      <h1 class="greeting">{{ greeting }}<span v-if="authStore.user">, {{ authStore.user.username }}</span></h1>
      <div v-if="todayWorkout?.streak > 0" class="streak-badge">
        {{ todayWorkout.streak }} day streak
      </div>
    </div>

    <!-- Onboarding nudge (if not onboarded and no sessions) -->
    <div v-if="!workoutStore.isOnboarded && !loading" class="nudge-card">
      <img src="/mascot/otter-mascot.png" alt="Coach" class="nudge-mascot" />
      <div class="nudge-body">
        <h3>Ready to start your fitness journey?</h3>
        <p>Set up your personalized plan in 2 minutes.</p>
        <router-link to="/workout/onboarding" class="btn-primary">Set Up My Plan</router-link>
      </div>
    </div>

    <!-- Today's Workout Card -->
    <div v-if="todayWorkout?.has_plan" class="today-card">
      <div class="today-header">
        <h2 class="today-label">{{ todayWorkout.day_label }}</h2>
        <span class="today-duration">~{{ todayWorkout.estimated_minutes }} min</span>
      </div>

      <!-- Time picker pills -->
      <div v-if="todayWorkout.exercises?.length > 0" class="time-pills">
        <button
          v-for="t in timePills"
          :key="t"
          class="time-pill"
          :class="{ active: selectedTime === t }"
          @click="selectedTime = t"
        >
          {{ t === 0 ? 'Full Plan' : t + ' min' }}
        </button>
      </div>

      <div class="exercise-pills">
        <span v-for="ex in displayedExercises" :key="ex.slug" class="ex-pill">
          {{ ex.name }}
        </span>
      </div>

      <button class="btn-primary full-width start-btn" @click="handleStartWorkout">
        Start Workout
      </button>
    </div>

    <!-- Week strip -->
    <div v-if="weekView" class="week-strip">
      <div
        v-for="d in weekView.days"
        :key="d.day"
        class="week-dot-wrap"
      >
        <span
          class="week-dot"
          :class="d.status"
          :title="d.label || d.day"
        >
          <template v-if="d.status === 'completed'">&#10003;</template>
          <template v-else-if="d.status === 'today'">&bull;</template>
        </span>
        <span class="week-day-label">{{ d.day.charAt(0).toUpperCase() }}</span>
      </div>
    </div>

    <!-- Coach message -->
    <div v-if="todayWorkout?.coach_message" class="coach-bubble">
      <img src="/mascot/otter-mascot.png" alt="Coach" class="coach-avatar" />
      <div class="coach-text">{{ todayWorkout.coach_message }}</div>
    </div>

    <!-- Quick Start section (always visible) -->
    <div class="quick-start-section">
      <h3 class="section-title">Quick Start</h3>
      <p class="section-desc">Pick exercises and jump straight in.</p>
      <div class="quick-chips">
        <router-link to="/workout/quick-start" class="quick-chip">
          Build Your Own
        </router-link>
        <router-link to="/workout/exercises" class="quick-chip">
          Browse Library
        </router-link>
      </div>
    </div>

    <!-- Recent Wins (placeholder) -->
    <div v-if="progressStats && progressStats.total_workouts > 0" class="wins-section">
      <h3 class="section-title">Recent Wins</h3>
      <div class="win-cards">
        <div class="win-card">
          <span class="win-value">{{ progressStats.total_workouts }}</span>
          <span class="win-label">Workouts</span>
        </div>
        <div class="win-card">
          <span class="win-value">{{ progressStats.workouts_this_week }}</span>
          <span class="win-label">This Week</span>
        </div>
        <div v-if="progressStats.total_volume_kg > 0" class="win-card">
          <span class="win-value">{{ formatVolume(progressStats.total_volume_kg) }}</span>
          <span class="win-label">Total Volume</span>
        </div>
      </div>
    </div>

    <!-- Toast -->
    <div v-if="toast" class="toast" @click="toast = null">{{ toast }}</div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../../stores/auth'
import { useWorkoutStore } from '../../stores/workout'

const router = useRouter()
const authStore = useAuthStore()
const workoutStore = useWorkoutStore()

const loading = ref(true)
const todayWorkout = ref(null)
const weekView = ref(null)
const progressStats = ref(null)
const selectedTime = ref(0) // 0 = full plan
const toast = ref(null)

const timePills = [0, 20, 30, 45, 60]

const greeting = computed(() => {
  const hour = new Date().getHours()
  if (hour < 12) return 'Good morning'
  if (hour < 17) return 'Good afternoon'
  return 'Good evening'
})

const displayedExercises = computed(() => {
  const exercises = todayWorkout.value?.exercises || []
  if (selectedTime.value === 0) return exercises

  // Rough filter: ~5 min per exercise
  const maxExercises = Math.floor(selectedTime.value / 5)
  return exercises.slice(0, Math.max(1, maxExercises))
})

function formatVolume(kg) {
  if (kg >= 1000) return Math.round(kg / 100) / 10 + 't'
  return Math.round(kg) + 'kg'
}

async function handleStartWorkout() {
  try {
    const timeBudget = selectedTime.value > 0 ? selectedTime.value : undefined
    const result = await workoutStore.startSession({
      time_budget_minutes: timeBudget,
    })
    const sid = result.data?.session_id
    if (sid) {
      router.push(`/workout/session/${sid}`)
    }
  } catch {
    toast.value = 'Failed to start workout'
    setTimeout(() => { toast.value = null }, 3000)
  }
}

onMounted(async () => {
  try {
    await workoutStore.fetchProfile()

    const promises = [
      workoutStore.fetchTodayWorkout().then(r => { todayWorkout.value = r }),
      workoutStore.fetchWeekView().then(r => { weekView.value = r }),
      workoutStore.fetchProgressStats().then(r => { progressStats.value = r }),
    ]
    await Promise.allSettled(promises)
  } catch {
    // Profile fetch might fail for new users — that's ok
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.workout-home {
  padding: 1.25rem;
}

/* Greeting */
.greeting-section {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 1.25rem;
}

.greeting {
  font-size: 1.35rem;
  font-weight: 800;
  color: var(--text-primary);
  flex: 1;
}

.streak-badge {
  padding: 0.3rem 0.75rem;
  border-radius: var(--radius-full);
  background: var(--color-warning-light);
  color: var(--color-warning);
  font-size: 0.75rem;
  font-weight: 600;
  white-space: nowrap;
}

/* Nudge */
.nudge-card {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1.25rem;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  margin-bottom: 1.25rem;
}

.nudge-mascot {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  object-fit: cover;
  flex-shrink: 0;
}

.nudge-body h3 {
  font-size: 0.95rem;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 0.2rem;
}

.nudge-body p {
  font-size: 0.8rem;
  color: var(--text-secondary);
  margin-bottom: 0.6rem;
}

/* Today card */
.today-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 1.25rem;
  box-shadow: var(--shadow-sm);
  margin-bottom: 1rem;
}

.today-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.75rem;
}

.today-label {
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--text-primary);
}

.today-duration {
  font-size: 0.8rem;
  color: var(--text-muted);
}

.time-pills {
  display: flex;
  gap: 0.35rem;
  margin-bottom: 0.75rem;
  overflow-x: auto;
}

.time-pill {
  padding: 0.3rem 0.7rem;
  border-radius: var(--radius-full);
  border: 1px solid var(--border-color);
  background: var(--bg-input);
  font-size: 0.7rem;
  font-weight: 500;
  color: var(--text-secondary);
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.2s;
}

.time-pill.active {
  border-color: var(--color-primary);
  background: var(--color-primary);
  color: white;
}

.exercise-pills {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
  margin-bottom: 1rem;
}

.ex-pill {
  padding: 0.3rem 0.65rem;
  border-radius: var(--radius-full);
  background: var(--color-primary-light);
  color: var(--color-primary);
  font-size: 0.75rem;
  font-weight: 500;
}

.start-btn {
  margin-top: 0.25rem;
}

/* Week strip */
.week-strip {
  display: flex;
  justify-content: space-between;
  padding: 0.75rem 0;
  margin-bottom: 1rem;
}

.week-dot-wrap {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.25rem;
}

.week-dot {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.7rem;
  font-weight: 600;
  border: 2px solid var(--border-color);
  background: var(--bg-card);
  color: var(--text-muted);
}

.week-dot.completed {
  border-color: var(--color-success);
  background: var(--color-success);
  color: white;
}

.week-dot.today {
  border-color: var(--color-primary);
  color: var(--color-primary);
  font-size: 1.25rem;
}

.week-dot.planned {
  border-color: var(--color-primary);
  border-style: dashed;
}

.week-dot.rest {
  border-color: var(--border-color);
  background: var(--bg-input);
}

.week-day-label {
  font-size: 0.65rem;
  color: var(--text-muted);
  font-weight: 500;
}

/* Coach bubble */
.coach-bubble {
  display: flex;
  align-items: flex-start;
  gap: 0.65rem;
  margin-bottom: 1.25rem;
}

.coach-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  object-fit: cover;
  flex-shrink: 0;
}

.coach-text {
  padding: 0.65rem 0.85rem;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 0 var(--radius-md) var(--radius-md) var(--radius-md);
  font-size: 0.85rem;
  color: var(--text-secondary);
  line-height: 1.45;
}

/* Quick Start */
.quick-start-section {
  margin-bottom: 1.25rem;
}

.section-title {
  font-size: 1rem;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 0.2rem;
}

.section-desc {
  font-size: 0.8rem;
  color: var(--text-muted);
  margin-bottom: 0.75rem;
}

.quick-chips {
  display: flex;
  gap: 0.5rem;
}

.quick-chip {
  flex: 1;
  padding: 0.75rem;
  text-align: center;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--color-primary);
  text-decoration: none;
  transition: all 0.2s;
}

.quick-chip:hover {
  border-color: var(--color-primary);
  box-shadow: var(--shadow-sm);
}

/* Wins */
.wins-section {
  margin-bottom: 1rem;
}

.win-cards {
  display: flex;
  gap: 0.5rem;
}

.win-card {
  flex: 1;
  padding: 0.85rem 0.5rem;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  text-align: center;
}

.win-value {
  display: block;
  font-size: 1.25rem;
  font-weight: 800;
  color: var(--color-primary);
}

.win-label {
  font-size: 0.65rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

/* Buttons */
.btn-primary {
  display: inline-block;
  padding: 0.65rem 1.25rem;
  background: var(--gradient-primary);
  color: white;
  border: none;
  border-radius: var(--radius-md);
  font-weight: 600;
  font-size: 0.9rem;
  cursor: pointer;
  text-decoration: none;
  text-align: center;
  transition: opacity 0.2s;
}

.btn-primary:hover { opacity: 0.9; }
.btn-primary.full-width { width: 100%; display: block; }

/* Toast */
.toast {
  position: fixed;
  bottom: 5rem;
  left: 50%;
  transform: translateX(-50%);
  padding: 0.65rem 1.25rem;
  background: var(--text-primary);
  color: white;
  border-radius: var(--radius-full);
  font-size: 0.8rem;
  font-weight: 500;
  z-index: 100;
  animation: toastIn 0.3s ease;
  max-width: 90%;
  text-align: center;
}

@keyframes toastIn {
  from { opacity: 0; transform: translateX(-50%) translateY(8px); }
  to { opacity: 1; transform: translateX(-50%) translateY(0); }
}
</style>
