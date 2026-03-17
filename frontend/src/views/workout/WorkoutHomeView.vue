<template>
  <div class="workout-home">
    <!-- Header with greeting and streak -->
    <header
      v-motion
      :initial="{ opacity: 0, y: -10 }"
      :enter="{ opacity: 1, y: 0, transition: { duration: 600 } }"
      class="home-header"
    >
      <h1 class="greeting font-display">{{ dynamicGreeting }} 👋</h1>
      <div v-if="todayWorkout?.streak > 0" class="streak-row">
        <svg class="streak-icon" viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
          <path d="M12 23c-3.6 0-7-2.5-7-7 0-3.2 2-5.5 3.8-7.5C10.5 6.5 12 4.6 12 2c0 4 4.5 6 6.2 9.2C19.7 13.8 20 16 20 16c0 4.5-3.9 7-8 7z"/>
        </svg>
        <span class="streak-text">{{ todayWorkout.streak }} day streak</span>
      </div>
    </header>

    <!-- Stats Section - 3 Progress Rings -->
    <section v-if="progressStats" class="stats-section">
      <div
        v-motion
        :initial="{ opacity: 0 }"
        :enter="{ opacity: 1, transition: { delay: 300, duration: 400 } }"
        class="stats-grid glass"
      >
        <ProgressRing
          :progress="workoutsProgress"
          :value="workoutsValue"
          label="Workouts"
          color="primary"
          :size="100"
          :stroke-width="6"
        />
        <ProgressRing
          :progress="volumeProgress"
          :value="formatVolume(progressStats.total_volume_kg || 0)"
          label="Volume"
          color="secondary"
          :size="100"
          :stroke-width="6"
        />
        <ProgressRing
          :progress="streakProgress"
          :value="(todayWorkout?.streak || 0) + 'd'"
          label="Streak"
          color="accent"
          :size="100"
          :stroke-width="6"
        />
      </div>
    </section>

    <!-- Coach insight bubble -->
    <section v-if="coachInsight" class="coach-section">
      <div
        v-motion
        :initial="{ opacity: 0, y: 10 }"
        :enter="{ opacity: 1, y: 0, transition: { delay: 400, duration: 300 } }"
        class="coach-preview glass"
      >
        <div class="coach-preview-inner">
          <div class="coach-avatar-ring">
            <span class="coach-emoji">✨</span>
          </div>
          <p class="coach-message">"{{ coachInsight }}"</p>
        </div>
      </div>
    </section>

    <!-- Onboarding nudge (if not onboarded and no sessions) -->
    <div v-if="!workoutStore.isOnboarded && !loading" class="nudge-card glass">
      <div class="nudge-avatar-ring">
        <img src="/mascot/otter-mascot.png" alt="Coach" class="nudge-mascot" />
      </div>
      <div class="nudge-body">
        <h3>Ready to start your fitness journey?</h3>
        <p>Let's chat and build your personalized plan.</p>
        <router-link to="/workout/onboarding" class="btn-primary">Talk to Coach</router-link>
      </div>
    </div>

    <!-- Today's Workout Card -->
    <section v-if="todayWorkout?.has_plan" class="today-section">
      <h2
        v-motion
        :initial="{ opacity: 0 }"
        :enter="{ opacity: 1, transition: { delay: 500 } }"
        class="section-label"
      >Today's Plan</h2>
      <div
        v-motion
        :initial="{ opacity: 0, y: 20 }"
        :enter="{ opacity: 1, y: 0, transition: { delay: 550, duration: 400 } }"
        class="workout-card glass"
      >
        <!-- Orange gradient header -->
        <div class="workout-card-header">
          <h3 class="workout-card-title font-display">{{ todayWorkout.day_label }}</h3>
          <span class="workout-card-duration">{{ todayWorkout.estimated_minutes }}m</span>
        </div>

        <div class="workout-card-body">
          <!-- Exercise pills -->
          <div class="exercise-pills">
            <span
              v-for="(ex, i) in displayedExercises"
              :key="ex.slug"
              v-motion
              :initial="{ opacity: 0, scale: 0.9 }"
              :enter="{ opacity: 1, scale: 1, transition: { delay: 600 + i * 100, duration: 300 } }"
              class="ex-pill"
            >
              {{ ex.name }}
            </span>
          </div>

          <!-- Start button -->
          <button class="btn-start" @click="handleStartWorkout">
            Start Workout
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg>
          </button>
        </div>
      </div>
    </section>

    <!-- Week strip -->
    <section v-if="weekView" class="week-section">
      <h2
        v-motion
        :initial="{ opacity: 0 }"
        :enter="{ opacity: 1, transition: { delay: 600 } }"
        class="section-label"
      >This Week</h2>
      <div class="week-strip glass">
        <div
          v-for="(d, index) in weekView.days"
          :key="d.day"
          class="week-dot-wrap"
        >
          <span
            class="week-dot"
            :class="d.status"
          >
            <template v-if="d.status === 'completed'">&#10003;</template>
            <template v-else-if="d.status === 'today'">&bull;</template>
            <template v-else-if="d.status === 'planned'">&#9675;</template>
          </span>
          <span class="week-day-label">{{ d.day.charAt(0).toUpperCase() }}</span>
        </div>
      </div>
    </section>

    <!-- Quick Start -->
    <section class="quick-section">
      <div class="quick-grid">
        <router-link
          to="/workout/quick-start"
          v-motion
          :initial="{ opacity: 0, y: 20 }"
          :enter="{ opacity: 1, y: 0, transition: { delay: 700 } }"
          class="quick-card glass"
        >
          <span class="quick-emoji">🏋️</span>
          <h3 class="quick-title font-display">Build Your Own</h3>
          <p class="quick-desc">Custom workout</p>
        </router-link>
        <router-link
          to="/workout/exercises"
          v-motion
          :initial="{ opacity: 0, y: 20 }"
          :enter="{ opacity: 1, y: 0, transition: { delay: 800 } }"
          class="quick-card glass"
        >
          <span class="quick-emoji">📚</span>
          <h3 class="quick-title font-display">Browse Library</h3>
          <p class="quick-desc">Exercise guides</p>
        </router-link>
      </div>
    </section>

    <!-- Toast -->
    <div v-if="toast" class="toast" @click="toast = null">{{ toast }}</div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../../stores/auth'
import { useWorkoutStore } from '../../stores/workout'
import { useVoiceOutput } from '../../composables/useVoiceOutput'
import ProgressRing from '../../components/ProgressRing.vue'

const router = useRouter()
const authStore = useAuthStore()
const workoutStore = useWorkoutStore()
const voiceOutput = useVoiceOutput()

const loading = ref(true)
const todayWorkout = ref(null)
const weekView = ref(null)
const progressStats = ref(null)
const selectedTime = ref(0)
const toast = ref(null)
const coachInsight = ref('')
const insightType = ref('')

const fallbackGreeting = computed(() => {
  const hour = new Date().getHours()
  const name = authStore.user?.username || ''
  const timeGreet = hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening'
  return name ? `${timeGreet}, ${name}` : timeGreet
})

const dynamicGreeting = computed(() => {
  return todayWorkout.value?.greeting || fallbackGreeting.value
})

const displayedExercises = computed(() => {
  const exercises = todayWorkout.value?.exercises || []
  if (selectedTime.value === 0) return exercises
  const maxExercises = Math.floor(selectedTime.value / 5)
  return exercises.slice(0, Math.max(1, maxExercises))
})

// Progress computations
const workoutsProgress = computed(() => {
  if (!progressStats.value) return 0
  const target = 4 // weekly target
  return Math.min((progressStats.value.workouts_this_week || 0) / target, 1)
})
const workoutsValue = computed(() => {
  if (!progressStats.value) return '0'
  return `${progressStats.value.workouts_this_week || 0}/4`
})
const volumeProgress = computed(() => {
  if (!progressStats.value?.total_volume_kg) return 0
  return Math.min(progressStats.value.total_volume_kg / 20000, 1)
})
const streakProgress = computed(() => {
  return Math.min((todayWorkout.value?.streak || 0) / 7, 1)
})

function formatVolume(kg) {
  if (kg >= 1000) return Math.round(kg / 100) / 10 + 'k'
  return Math.round(kg) + ''
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
      workoutStore.fetchTodayWorkout().then(r => {
        todayWorkout.value = r
        if (r?.insight) {
          coachInsight.value = r.insight
          insightType.value = r.insight_type || ''
        }
        const todayKey = `coach_greeted_${new Date().toDateString()}`
        if (!sessionStorage.getItem(todayKey) && r?.greeting) {
          const spokenText = r.greeting + (r.insight ? '. ' + r.insight : '')
          voiceOutput.speak(spokenText)
          sessionStorage.setItem(todayKey, '1')
        }
      }),
      workoutStore.fetchWeekView().then(r => { weekView.value = r }),
      workoutStore.fetchProgressStats().then(r => { progressStats.value = r }),
    ]
    await Promise.allSettled(promises)
  } catch {
    // Profile fetch might fail for new users
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.workout-home {
  padding-bottom: 2rem;
}

/* Header */
.home-header {
  padding: 1.5rem 1.5rem 0.75rem;
}

.greeting {
  font-size: 1.2rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: -0.02em;
  color: var(--text-primary);
  margin-bottom: 0.5rem;
}

.streak-row {
  display: flex;
  align-items: center;
  gap: 0.4rem;
}

.streak-icon {
  color: var(--color-primary);
  width: 20px;
  height: 20px;
}

.streak-text {
  font-size: 0.8rem;
  font-weight: 500;
  color: var(--text-muted);
}

/* Stats */
.stats-section {
  padding: 0 1.5rem;
  margin-bottom: 1.5rem;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1rem;
  padding: 1.5rem;
  border-radius: 1rem;
}

/* Coach preview */
.coach-section {
  padding: 0 1.5rem;
  margin-bottom: 1.5rem;
}

.coach-preview {
  padding: 1rem;
  border-radius: 1rem;
  cursor: pointer;
  transition: border-color 0.2s;
}

.coach-preview:hover {
  border-color: var(--color-secondary);
}

.coach-preview-inner {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
}

.coach-avatar-ring {
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

.coach-message {
  font-size: 0.8rem;
  color: var(--text-primary);
  opacity: 0.9;
  font-style: italic;
  line-height: 1.5;
  flex: 1;
}

/* Nudge */
.nudge-card {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1.25rem;
  margin: 0 1.5rem 1.5rem;
  border-radius: 1rem;
}

.nudge-avatar-ring {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: var(--gradient-secondary);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  padding: 3px;
}

.nudge-mascot {
  width: 100%;
  height: 100%;
  border-radius: 50%;
  object-fit: cover;
}

.nudge-body h3 {
  font-family: var(--font-display);
  font-size: 0.85rem;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 0.2rem;
}

.nudge-body p {
  font-size: 0.8rem;
  color: var(--text-secondary);
  margin-bottom: 0.6rem;
}

/* Section label */
.section-label {
  font-size: 0.65rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--text-muted);
  margin-bottom: 0.6rem;
}

/* Today card */
.today-section {
  padding: 0 1.5rem;
  margin-bottom: 1.5rem;
}

.workout-card {
  border-radius: 1rem;
  overflow: hidden;
}

.workout-card-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  padding: 1.5rem 1rem 1rem;
  background: var(--gradient-primary);
  min-height: 5rem;
}

.workout-card-title {
  font-size: 1.05rem;
  font-weight: 700;
  color: var(--text-on-primary);
}

.workout-card-duration {
  font-size: 0.875rem;
  color: var(--text-on-primary);
  opacity: 0.8;
}

.workout-card-body {
  padding: 1rem;
}

.exercise-pills {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  margin-bottom: 1rem;
}

.ex-pill {
  padding: 0.35rem 0.75rem;
  border-radius: var(--radius-full);
  background: var(--color-primary-light);
  color: var(--text-primary);
  font-size: 0.8rem;
  font-weight: 500;
}

.btn-start {
  width: 100%;
  padding: 0.85rem;
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
  gap: 0.4rem;
  box-shadow: var(--glow-primary);
  transition: transform 0.15s;
}

.btn-start:active {
  transform: scale(0.98);
}

/* Week strip */
.week-section {
  padding: 0 1.5rem;
  margin-bottom: 1.5rem;
}

.week-strip {
  display: flex;
  align-items: center;
  justify-content: space-around;
  padding: 1rem;
  border-radius: 1rem;
}

.week-dot-wrap {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.4rem;
}

.week-dot {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.8rem;
  font-weight: 700;
  transition: all 0.2s;
}

.week-dot.completed {
  background: var(--color-primary);
  color: var(--text-on-primary);
}

.week-dot.today {
  border: 2px solid var(--color-primary);
  color: var(--color-primary);
  font-size: 1.5rem;
}

.week-dot.planned {
  border: 2px dashed var(--text-muted);
  color: var(--text-muted);
}

.week-dot.rest {
  color: var(--text-muted);
}

.week-day-label {
  font-size: 0.7rem;
  color: var(--text-muted);
}

/* Quick start */
.quick-section {
  padding: 0 1.5rem;
}

.quick-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.quick-card {
  padding: 1rem;
  border-radius: 1rem;
  text-decoration: none;
  text-align: left;
  transition: border-color 0.2s, transform 0.15s;
}

.quick-card:hover {
  border-color: var(--color-secondary);
}

.quick-card:active {
  transform: scale(0.98);
}

.quick-emoji {
  font-size: 1.5rem;
  display: block;
  margin-bottom: 0.4rem;
}

.quick-title {
  font-weight: 700;
  font-size: 0.8rem;
  color: var(--text-primary);
  margin-bottom: 0.15rem;
}

.quick-desc {
  font-size: 0.75rem;
  color: var(--text-muted);
}

/* Buttons */
.btn-primary {
  display: inline-block;
  padding: 0.65rem 1.25rem;
  background: var(--gradient-primary);
  color: var(--text-on-primary);
  border: none;
  border-radius: var(--radius-md);
  font-weight: 600;
  font-size: 0.9rem;
  cursor: pointer;
  text-decoration: none;
  text-align: center;
  box-shadow: var(--glow-primary);
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
  animation: toastIn 0.3s ease;
  max-width: 90%;
  text-align: center;
}

@keyframes toastIn {
  from { opacity: 0; transform: translateX(-50%) translateY(8px); }
  to { opacity: 1; transform: translateX(-50%) translateY(0); }
}
</style>
