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
    <div v-if="todayWorkout?.has_plan && !showCustomize" class="plan-actions">
      <button class="btn-start" @click="handleStartWorkout">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="20" height="20">
          <polygon points="5 3 19 12 5 21 5 3"/>
        </svg>
        Start Workout
      </button>
      <button class="btn-customize" @click="openCustomize">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3v18M3 12h18"/></svg>
        Customize Weekly Plan
      </button>
    </div>

    <!-- Weekly Plan Customizer -->
    <div v-if="showCustomize" class="customize-section">
      <div class="customize-header">
        <h2 class="section-label">Customize Weekly Plan</h2>
        <button class="btn-cancel" @click="showCustomize = false">Cancel</button>
      </div>

      <div class="customize-days">
        <div
          v-for="(cd, di) in customDays"
          :key="cd.day"
          class="customize-day glass"
        >
          <div class="customize-day-header">
            <span class="customize-day-name">{{ fullDayName(cd.day) }}</span>
            <div class="customize-day-right">
              <span v-if="cd.muscles.length" class="customize-day-count">{{ cd.muscles.length }} groups</span>
              <button class="btn-remove-day" @click="removeDay(di)" title="Remove day">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
              </button>
            </div>
          </div>
          <div class="muscle-pills">
            <button
              v-for="mg in sortedMuscleGroups(cd.day)"
              :key="mg"
              class="muscle-pill"
              :class="{
                'muscle-selected': cd.muscles.includes(mg),
                'muscle-used': !cd.muscles.includes(mg) && usedMuscles(cd.day).has(mg),
              }"
              @click="toggleMuscle(di, mg)"
            >
              {{ mg }}
            </button>
          </div>
        </div>

        <!-- Add day pills -->
        <div v-if="availableDays.length > 0" class="add-day-pills">
          <button
            v-for="d in availableDays"
            :key="d"
            class="add-day-pill"
            @click="addDayDirect(d)"
          >
            {{ shortDayName(d) }}
          </button>
          <span class="add-day-hint">add</span>
        </div>
      </div>

      <button class="btn-start" @click="saveCustomPlan" :disabled="savingCustom">
        {{ savingCustom ? 'Saving...' : 'Save Plan' }}
      </button>
    </div>

    <!-- Toast -->
    <div v-if="toast" class="toast" @click="toast = null">{{ toast }}</div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useWorkoutStore } from '../../stores/workout'
import api from '../../api/client'

const router = useRouter()
const route = useRoute()
const workoutStore = useWorkoutStore()

const loading = ref(true)
const todayWorkout = ref(null)
const toast = ref(null)

// Weekly plan customizer
const showCustomize = ref(false)
const savingCustom = ref(false)
const customDays = ref([])

const ALL_MUSCLE_GROUPS = [
  'chest', 'back', 'shoulders', 'biceps', 'triceps',
  'quads', 'hamstrings', 'glutes', 'calves', 'core',
]

const DAY_NAMES_FULL = {
  mon: 'Monday', tue: 'Tuesday', wed: 'Wednesday',
  thu: 'Thursday', fri: 'Friday', sat: 'Saturday', sun: 'Sunday',
}

function fullDayName(abbr) {
  return DAY_NAMES_FULL[abbr] || abbr
}

function openCustomize() {
  // Initialize from current plan days
  const weekData = todayWorkout.value
  if (!weekData) return

  // Fetch the week view to get all days
  workoutStore.fetchWeekView(0).then(wv => {
    customDays.value = (wv.days || [])
      .filter(d => d.exercises?.length > 0 || d.status === 'today' || d.status === 'planned')
      .map(d => ({
        day: d.day,
        muscles: guessMusclesFromLabel(d.label),
      }))
    // If no planned days found, use existing plan days
    if (customDays.value.length === 0 && weekData.exercises?.length) {
      customDays.value = [{ day: 'mon', muscles: [] }, { day: 'wed', muscles: [] }, { day: 'fri', muscles: [] }]
    }
    showCustomize.value = true
  })
}

function guessMusclesFromLabel(label) {
  // Extract muscle groups from day label like "Upper — Chest & Back"
  if (!label) return []
  const lower = label.toLowerCase()
  return ALL_MUSCLE_GROUPS.filter(m => lower.includes(m))
}

function usedMuscles(currentDay) {
  // Collect muscles selected on OTHER days
  const used = new Set()
  for (const cd of customDays.value) {
    if (cd.day === currentDay) continue
    for (const m of cd.muscles) {
      used.add(m)
    }
  }
  return used
}

function sortedMuscleGroups(currentDay) {
  const used = usedMuscles(currentDay)
  const selected = new Set(customDays.value.find(d => d.day === currentDay)?.muscles || [])
  // Selected first, then available, then used (greyed) at the end
  return [...ALL_MUSCLE_GROUPS].sort((a, b) => {
    const aSelected = selected.has(a) ? 0 : 1
    const bSelected = selected.has(b) ? 0 : 1
    if (aSelected !== bSelected) return aSelected - bSelected
    const aUsed = used.has(a) && !selected.has(a) ? 1 : 0
    const bUsed = used.has(b) && !selected.has(b) ? 1 : 0
    return aUsed - bUsed
  })
}

const ALL_DAYS = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']
const SHORT_DAY_NAMES = { mon: 'Mon', tue: 'Tue', wed: 'Wed', thu: 'Thu', fri: 'Fri', sat: 'Sat', sun: 'Sun' }

const availableDays = computed(() => {
  const used = new Set(customDays.value.map(d => d.day))
  return ALL_DAYS.filter(d => !used.has(d))
})

function shortDayName(abbr) { return SHORT_DAY_NAMES[abbr] || abbr }

function addDayDirect(day) {
  const dayIdx = ALL_DAYS.indexOf(day)
  let insertAt = customDays.value.length
  for (let i = 0; i < customDays.value.length; i++) {
    if (ALL_DAYS.indexOf(customDays.value[i].day) > dayIdx) {
      insertAt = i
      break
    }
  }
  customDays.value.splice(insertAt, 0, { day, muscles: [] })
}

function removeDay(index) {
  customDays.value.splice(index, 1)
}

const repeatWarningShown = ref(false)

function toggleMuscle(dayIndex, muscle) {
  const day = customDays.value[dayIndex]
  const idx = day.muscles.indexOf(muscle)
  if (idx >= 0) {
    day.muscles.splice(idx, 1)
  } else {
    // Show one-time warning if this muscle is used on another day
    if (!repeatWarningShown.value && usedMuscles(day.day).has(muscle)) {
      repeatWarningShown.value = true
      toast.value = 'This muscle group is already on another day — exercises will vary'
      setTimeout(() => { toast.value = null }, 3000)
    }
    day.muscles.push(muscle)
  }
}

async function saveCustomPlan() {
  const days = customDays.value.filter(d => d.muscles.length > 0)
  if (days.length === 0) {
    toast.value = 'Select at least one muscle group per day'
    setTimeout(() => { toast.value = null }, 3000)
    return
  }
  savingCustom.value = true
  try {
    await api.put('/api/v1/workout/plan/customize', { days })
    todayWorkout.value = await workoutStore.fetchTodayWorkout()
    workoutStore.fetchWeekView(0)  // refresh week view for home page
    showCustomize.value = false
    toast.value = 'Plan updated!'
    setTimeout(() => { toast.value = null }, 2000)
  } catch (err) {
    toast.value = 'Failed to save plan'
    setTimeout(() => { toast.value = null }, 3000)
  } finally {
    savingCustom.value = false
  }
}

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
    // Auto-open customizer if ?customize=1
    if (route.query.customize === '1' && todayWorkout.value?.has_plan) {
      openCustomize()
    }
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

/* Customize button */
.btn-customize {
  width: 100%;
  margin-top: 0.5rem;
  padding: 0.6rem;
  border: 1px solid var(--border-color);
  border-radius: 0.75rem;
  background: transparent;
  color: var(--text-secondary);
  font-size: 0.8rem;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.35rem;
  transition: all 0.15s;
}

.btn-customize:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

/* Customizer */
.customize-section {
  padding: 0 1.5rem 2rem;
}

.customize-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.75rem;
}

.btn-cancel {
  padding: 0.3rem 0.7rem;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-full);
  background: transparent;
  color: var(--text-muted);
  font-size: 0.75rem;
  font-weight: 600;
  cursor: pointer;
}

.customize-days {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  margin-bottom: 1rem;
}

.customize-day {
  padding: 0.75rem 1rem;
  border-radius: 0.75rem;
}

.customize-day-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.customize-day-name {
  font-size: 0.85rem;
  font-weight: 700;
  color: var(--text-primary);
}

.customize-day-right {
  display: flex;
  align-items: center;
  gap: 0.4rem;
}

.customize-day-count {
  font-size: 0.7rem;
  color: var(--text-muted);
}

.btn-remove-day {
  width: 24px;
  height: 24px;
  border: none;
  border-radius: 50%;
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s;
}

.btn-remove-day:hover {
  color: var(--color-destructive, #dc2626);
  background: rgba(220, 38, 38, 0.1);
}

.muscle-pills {
  display: flex;
  flex-wrap: wrap;
  gap: 0.3rem;
}

.muscle-pill {
  padding: 0.3rem 0.6rem;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-full);
  background: transparent;
  color: var(--text-secondary);
  font-size: 0.7rem;
  font-weight: 600;
  cursor: pointer;
  text-transform: capitalize;
  transition: all 0.15s;
}

.muscle-pill:hover:not(:disabled) {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.muscle-selected {
  background: var(--color-primary) !important;
  color: var(--text-on-primary) !important;
  border-color: var(--color-primary) !important;
}

.muscle-used {
  opacity: 0.35;
}

/* Add day pills */
.add-day-pills {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.35rem;
  padding: 0.5rem 0;
}

.add-day-pill {
  padding: 0.35rem 0.65rem;
  border: 1px dashed var(--border-color);
  border-radius: var(--radius-full);
  background: transparent;
  color: var(--text-muted);
  font-size: 0.75rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
}

.add-day-pill:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
  border-style: solid;
}

.add-day-hint {
  font-size: 0.65rem;
  color: var(--text-muted);
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.05em;
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
