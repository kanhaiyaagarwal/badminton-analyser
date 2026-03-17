<template>
  <div class="quick-start">
    <router-link to="/workout" class="back-link">&larr; Back</router-link>
    <h1 class="page-title">Quick Start</h1>
    <p class="page-desc">Pick your exercises and go.</p>

    <!-- Search -->
    <div class="search-wrap">
      <input
        v-model="search"
        type="text"
        class="search-input"
        placeholder="Search exercises..."
      />
    </div>

    <!-- Muscle group filter tabs -->
    <div class="filter-tabs">
      <button
        v-for="mg in muscleGroups"
        :key="mg"
        class="filter-tab"
        :class="{ active: selectedMuscle === mg }"
        @click="selectedMuscle = mg"
      >
        {{ mg }}
      </button>
    </div>

    <!-- Time slider -->
    <div class="time-slider-section">
      <div class="time-header">
        <span class="time-label">Time</span>
        <span class="time-value">{{ timeBudget === 0 ? 'Any' : timeBudget + ' min' }}</span>
      </div>
      <input
        type="range"
        v-model.number="timeBudget"
        min="0"
        max="60"
        step="5"
        class="time-slider"
      />
      <div class="time-marks">
        <span>Any</span>
        <span>15</span>
        <span>30</span>
        <span>45</span>
        <span>60</span>
      </div>
    </div>

    <!-- Saved Workouts -->
    <div v-if="!search && savedWorkouts.length > 0" class="combos-section">
      <h3 class="sub-title">Saved Workouts</h3>
      <div class="combo-cards">
        <button
          v-for="sw in savedWorkouts"
          :key="sw.id"
          class="combo-card saved-card"
          :class="{ active: activeCombo === sw.name }"
          @click="applySaved(sw)"
        >
          <button class="remove-saved" @click.stop="removeSaved(sw.id)">&times;</button>
          <span class="combo-name">{{ sw.name }}</span>
          <span class="combo-detail">{{ sw.slugs.length }} exercises · {{ sw.sets }} sets</span>
        </button>
      </div>
    </div>

    <!-- Quick Combos -->
    <div v-if="!search && activeCombos.length > 0" class="combos-section">
      <h3 class="sub-title">Quick Combos</h3>
      <div class="combo-cards">
        <button
          v-for="combo in activeCombos"
          :key="combo.name"
          class="combo-card"
          :class="{ active: activeCombo === combo.name }"
          @click="applyCombo(combo)"
        >
          <span class="combo-emoji">{{ combo.emoji || '' }}</span>
          <span class="combo-name">{{ combo.name }}</span>
          <span class="combo-detail">{{ combo.slugs.length }} exercises · {{ combo.sets }} sets · {{ combo.time }}</span>
        </button>
      </div>
    </div>

    <!-- Exercise grid -->
    <div class="exercise-grid">
      <button
        v-for="ex in filteredExercises"
        :key="ex.slug"
        class="exercise-item"
        :class="{ selected: selectedSlugs.has(ex.slug) }"
        @click="toggleExercise(ex.slug)"
      >
        <div class="ex-info">
          <span class="ex-name">{{ ex.name }}</span>
          <span class="ex-muscle">{{ ex.primary_muscle }}</span>
        </div>
        <div class="ex-badges">
          <span class="badge difficulty" :class="ex.difficulty">{{ ex.difficulty }}</span>
        </div>
      </button>
    </div>

    <!-- Selected tray -->
    <div v-if="selectedSlugs.size > 0" class="selected-tray">
      <div class="tray-content">
        <div class="tray-chips">
          <span v-for="slug in selectedSlugs" :key="slug" class="tray-chip" @click="toggleExercise(slug)">
            {{ exerciseNameMap[slug] || slug }} &times;
          </span>
        </div>
        <div class="tray-meta">
          {{ selectedSlugs.size }} exercise{{ selectedSlugs.size > 1 ? 's' : '' }}
          &middot; ~{{ selectedSlugs.size * 7 }} min
        </div>
      </div>
      <div class="tray-buttons">
        <button class="btn-save-combo" @click="saveCurrentWorkout" title="Save this combo">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/></svg>
        </button>
        <button class="btn-primary tray-btn" @click="startQuickWorkout" :disabled="workoutStore.loading">
          Start Workout
        </button>
      </div>
    </div>

    <!-- Toast -->
    <div v-if="toast" class="toast">{{ toast }}</div>
  </div>
</template>

<script setup>
import { ref, computed, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useWorkoutStore } from '../../stores/workout'

const router = useRouter()
const workoutStore = useWorkoutStore()

const search = ref('')
const selectedMuscle = ref('All')
const selectedSlugs = reactive(new Set())
const activeCombo = ref(null)
const toast = ref(null)
const timeBudget = ref(0) // 0 = any

const muscleGroups = ['All', 'Chest', 'Back', 'Legs', 'Shoulders', 'Arms', 'Core']

// Combo templates: priority-ordered exercise pools (compounds first, then isolation/accessories)
// The builder picks from the pool until the time budget is filled.
const comboTemplates = {
  'All': [
    { name: 'HIIT Blast', emoji: '🔥', pool: ['push-up', 'bodyweight-squat', 'mountain-climber', 'burpee', 'jump-squat', 'high-knees', 'jumping-jacks', 'plank', 'russian-twist', 'bear-crawl'] },
    { name: 'Upper Body', emoji: '💪', pool: ['bench-press', 'shoulder-press', 'barbell-row', 'pull-up', 'incline-dumbbell-press', 'lateral-raise', 'bicep-curl', 'tricep-pushdown', 'face-pull', 'dips', 'hammer-curl', 'dumbbell-fly'] },
    { name: 'Leg Day', emoji: '🦵', pool: ['barbell-squat', 'romanian-deadlift', 'lunges', 'leg-press', 'hip-thrust', 'leg-extension', 'leg-curl', 'calf-raise', 'bulgarian-split-squat', 'glute-bridge', 'step-up', 'sumo-squat'] },
    { name: 'Full Body', emoji: '🏋️', pool: ['bench-press', 'barbell-squat', 'barbell-row', 'shoulder-press', 'deadlift', 'pull-up', 'lunges', 'bicep-curl', 'plank', 'lateral-raise', 'tricep-pushdown', 'calf-raise'] },
    { name: 'Core Burner', emoji: '🎯', pool: ['plank', 'crunch', 'russian-twist', 'hanging-leg-raise', 'mountain-climber', 'bicycle-crunch', 'v-up', 'dead-bug', 'side-plank', 'hollow-body-hold', 'ab-wheel-rollout', 'cable-crunch'] },
  ],
  'Chest': [
    { name: 'Chest Builder', emoji: '🏋️', pool: ['bench-press', 'incline-dumbbell-press', 'dumbbell-fly', 'push-up', 'incline-bench-press', 'cable-fly', 'decline-bench-press', 'pec-deck', 'incline-dumbbell-fly', 'diamond-push-up', 'cable-crossover', 'wide-grip-push-up'] },
    { name: 'Chest & Tris', emoji: '💪', pool: ['bench-press', 'incline-bench-press', 'dips', 'tricep-pushdown', 'cable-fly', 'skull-crusher', 'close-grip-bench-press', 'dumbbell-fly', 'overhead-tricep-extension', 'diamond-push-up', 'dumbbell-tricep-kickback', 'push-up'] },
    { name: 'Bodyweight Chest', emoji: '🔥', pool: ['push-up', 'diamond-push-up', 'wide-grip-push-up', 'dips', 'tricep-dip-bench', 'plank', 'burpee', 'mountain-climber'] },
  ],
  'Back': [
    { name: 'Back Thickness', emoji: '🏋️', pool: ['barbell-row', 'seated-cable-row', 'lat-pulldown', 'face-pull', 'single-arm-dumbbell-row', 't-bar-row', 'chest-supported-row', 'pendlay-row', 'reverse-fly', 'hyperextension', 'superman', 'seated-row-machine'] },
    { name: 'Pull Day', emoji: '💪', pool: ['deadlift', 'pull-up', 'barbell-row', 'bicep-curl', 'lat-pulldown', 'hammer-curl', 'chin-up', 'face-pull', 'seated-cable-row', 'reverse-curl', 'concentration-curl', 'preacher-curl'] },
    { name: 'Bodyweight Back', emoji: '🔥', pool: ['pull-up', 'chin-up', 'superman', 'hyperextension', 'hanging-leg-raise', 'plank', 'bear-crawl', 'burpee'] },
  ],
  'Legs': [
    { name: 'Quad Focused', emoji: '🦵', pool: ['barbell-squat', 'leg-press', 'lunges', 'leg-extension', 'front-squat', 'hack-squat', 'bulgarian-split-squat', 'step-up', 'smith-machine-squat', 'jump-squat', 'sissy-squat', 'wall-sit'] },
    { name: 'Posterior Chain', emoji: '🔥', pool: ['romanian-deadlift', 'hip-thrust', 'leg-curl', 'glute-bridge', 'stiff-leg-deadlift', 'good-morning', 'sumo-deadlift', 'seated-leg-curl', 'nordic-curl', 'donkey-kick', 'fire-hydrant', 'cable-pull-through'] },
    { name: 'Leg Blast', emoji: '💪', pool: ['barbell-squat', 'romanian-deadlift', 'lunges', 'leg-press', 'hip-thrust', 'calf-raise', 'leg-curl', 'leg-extension', 'bulgarian-split-squat', 'step-up', 'sumo-squat', 'glute-bridge'] },
    { name: 'Bodyweight Legs', emoji: '🏃', pool: ['bodyweight-squat', 'jump-squat', 'lunges', 'glute-bridge', 'wall-sit', 'box-jump', 'donkey-kick', 'fire-hydrant', 'single-leg-calf-raise', 'sumo-squat', 'nordic-curl', 'step-up'] },
  ],
  'Shoulders': [
    { name: 'Boulder Shoulders', emoji: '🏋️', pool: ['shoulder-press', 'lateral-raise', 'front-raise', 'face-pull', 'reverse-fly', 'arnold-press', 'upright-row', 'cable-lateral-raise', 'dumbbell-shrug', 'barbell-shrug', 'dumbbell-fly', 'band-shoulder-dislocates'] },
    { name: 'Press & Raise', emoji: '💪', pool: ['arnold-press', 'lateral-raise', 'upright-row', 'shoulder-press', 'front-raise', 'cable-lateral-raise', 'reverse-fly', 'face-pull', 'barbell-shrug', 'dumbbell-shrug'] },
  ],
  'Arms': [
    { name: 'Arm Day', emoji: '💪', pool: ['bicep-curl', 'tricep-pushdown', 'hammer-curl', 'skull-crusher', 'concentration-curl', 'dips', 'preacher-curl', 'overhead-tricep-extension', 'cable-curl', 'dumbbell-tricep-kickback', 'reverse-curl', 'incline-dumbbell-curl'] },
    { name: 'Bicep Blast', emoji: '🔥', pool: ['bicep-curl', 'hammer-curl', 'incline-dumbbell-curl', 'preacher-curl', 'concentration-curl', 'cable-curl', 'reverse-curl', 'chin-up'] },
    { name: 'Tricep Blast', emoji: '🎯', pool: ['tricep-pushdown', 'skull-crusher', 'overhead-tricep-extension', 'dips', 'close-grip-bench-press', 'dumbbell-tricep-kickback', 'tricep-dip-bench', 'diamond-push-up'] },
  ],
  'Core': [
    { name: 'Core Burner', emoji: '🔥', pool: ['plank', 'crunch', 'russian-twist', 'hanging-leg-raise', 'mountain-climber', 'bicycle-crunch', 'v-up', 'dead-bug', 'side-plank', 'hollow-body-hold', 'ab-wheel-rollout', 'cable-crunch'] },
    { name: 'Abs Focus', emoji: '🎯', pool: ['crunch', 'bicycle-crunch', 'v-up', 'dead-bug', 'hollow-body-hold', 'decline-sit-up', 'cable-crunch', 'russian-twist', 'hanging-leg-raise', 'plank'] },
    { name: 'Core Strength', emoji: '💪', pool: ['plank', 'side-plank', 'ab-wheel-rollout', 'hanging-leg-raise', 'cable-crunch', 'dead-bug', 'hollow-body-hold', 'superman', 'mountain-climber', 'v-up'] },
  ],
}

// Realistic time budgets: ~7 min per exercise with 3 sets, ~9 min with 4 sets
// (45s work + 90s rest per set + transitions)
function planForTime(minutes) {
  if (minutes === 0) return { exercises: 4, sets: 3 } // "Any" default
  if (minutes <= 15) return { exercises: 2, sets: 3 }
  if (minutes <= 20) return { exercises: 3, sets: 3 }
  if (minutes <= 25) return { exercises: 3, sets: 3 }
  if (minutes <= 30) return { exercises: 4, sets: 3 }
  if (minutes <= 40) return { exercises: 4, sets: 4 }
  if (minutes <= 45) return { exercises: 5, sets: 3 }
  if (minutes <= 50) return { exercises: 5, sets: 4 }
  if (minutes <= 55) return { exercises: 6, sets: 3 }
  return { exercises: 6, sets: 4 }
}

const activeCombos = computed(() => {
  const templates = comboTemplates[selectedMuscle.value] || comboTemplates['All']
  const { exercises: count, sets } = planForTime(timeBudget.value)
  const estTime = timeBudget.value === 0 ? count * 7 : timeBudget.value

  return templates.map(t => ({
    name: t.name,
    emoji: t.emoji,
    slugs: t.pool.slice(0, count),
    sets,
    time: `~${estTime} min`,
  }))
})

// Build name map from exercises
const exerciseNameMap = computed(() => {
  const map = {}
  for (const ex of workoutStore.exercises) {
    map[ex.slug] = ex.name
  }
  return map
})

const filteredExercises = computed(() => {
  let list = workoutStore.exercises

  if (search.value) {
    const q = search.value.toLowerCase()
    list = list.filter(e => e.name.toLowerCase().includes(q))
  }

  if (selectedMuscle.value !== 'All') {
    const mg = selectedMuscle.value.toLowerCase()
    list = list.filter(e =>
      (e.muscle_groups || []).some(m => m.toLowerCase().includes(mg)) ||
      e.primary_muscle.toLowerCase().includes(mg)
    )
  }

  return list
})

function toggleExercise(slug) {
  if (selectedSlugs.has(slug)) {
    selectedSlugs.delete(slug)
  } else {
    selectedSlugs.add(slug)
  }
  activeCombo.value = null
}

const activeSets = ref(3) // track selected combo's sets

function applyCombo(combo) {
  selectedSlugs.clear()
  combo.slugs.forEach(s => selectedSlugs.add(s))
  activeSets.value = combo.sets || 3
  activeCombo.value = combo.name
}

// --- Saved workouts (localStorage) ---
const SAVED_KEY = 'saved_workouts'
const savedWorkouts = ref(JSON.parse(localStorage.getItem(SAVED_KEY) || '[]'))

function saveCurrentWorkout() {
  if (selectedSlugs.size === 0) return
  const name = activeCombo.value || `${selectedSlugs.size}-exercise workout`
  const entry = {
    id: Date.now(),
    name,
    slugs: [...selectedSlugs],
    sets: activeSets.value,
    muscle: selectedMuscle.value,
    createdAt: new Date().toISOString(),
  }
  const list = [...savedWorkouts.value, entry]
  savedWorkouts.value = list
  localStorage.setItem(SAVED_KEY, JSON.stringify(list))
  toast.value = `"${name}" saved!`
  setTimeout(() => { toast.value = null }, 2500)
}

function applySaved(sw) {
  selectedSlugs.clear()
  sw.slugs.forEach(s => selectedSlugs.add(s))
  activeSets.value = sw.sets || 3
  activeCombo.value = sw.name
}

function removeSaved(id) {
  const list = savedWorkouts.value.filter(s => s.id !== id)
  savedWorkouts.value = list
  localStorage.setItem(SAVED_KEY, JSON.stringify(list))
}

async function startQuickWorkout() {
  try {
    const result = await workoutStore.startSession({
      exercise_slugs: [...selectedSlugs],
      time_budget_minutes: timeBudget.value || undefined,
    })
    const sid = result.data?.session_id
    if (sid) {
      router.push(`/workout/session/${sid}`)
    }
  } catch {
    toast.value = 'Failed to create session'
    setTimeout(() => { toast.value = null }, 3000)
  }
}

onMounted(() => {
  workoutStore.fetchExercises()
})
</script>

<style scoped>
.quick-start {
  padding: 1.25rem;
  padding-bottom: 14rem; /* space for bottom nav + selected tray */
}

.back-link {
  color: var(--text-muted);
  text-decoration: none;
  font-size: 0.85rem;
}
.back-link:hover { color: var(--color-primary); }

.page-title {
  font-size: 1.35rem;
  font-weight: 800;
  color: var(--text-primary);
  margin-top: 0.5rem;
  margin-bottom: 0.15rem;
}

.page-desc {
  font-size: 0.85rem;
  color: var(--text-muted);
  margin-bottom: 1rem;
}

/* Search */
.search-wrap {
  margin-bottom: 0.75rem;
}

.search-input {
  width: 100%;
  padding: 0.65rem 0.85rem;
  border: 1px solid var(--border-input);
  border-radius: var(--radius-md);
  background: var(--bg-input);
  font-size: 0.9rem;
  color: var(--text-primary);
  outline: none;
  box-sizing: border-box;
}

.search-input:focus {
  border-color: var(--border-input-focus);
}

/* Filter tabs */
.filter-tabs {
  display: flex;
  gap: 0.35rem;
  overflow-x: auto;
  margin-bottom: 1rem;
  -webkit-overflow-scrolling: touch;
}

.filter-tab {
  padding: 0.4rem 0.85rem;
  border-radius: var(--radius-full);
  border: 1px solid var(--border-color);
  background: var(--bg-card);
  font-size: 0.8rem;
  font-weight: 500;
  color: var(--text-secondary);
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.2s;
}

.filter-tab.active {
  border-color: var(--color-primary);
  background: var(--color-primary);
  color: white;
}

/* Combos */
/* Time slider */
.time-slider-section {
  margin-bottom: 1rem;
  padding: 0.75rem;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
}

.time-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.4rem;
}

.time-label {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.time-value {
  font-size: 0.85rem;
  font-weight: 700;
  color: var(--color-primary);
}

.time-slider {
  width: 100%;
  -webkit-appearance: none;
  appearance: none;
  height: 6px;
  background: var(--border-input);
  border-radius: 3px;
  outline: none;
}

.time-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 22px;
  height: 22px;
  background: var(--color-primary);
  border-radius: 50%;
  cursor: pointer;
  box-shadow: 0 1px 4px rgba(0,0,0,0.2);
}

.time-slider::-moz-range-thumb {
  width: 22px;
  height: 22px;
  background: var(--color-primary);
  border-radius: 50%;
  cursor: pointer;
  border: none;
}

.time-marks {
  display: flex;
  justify-content: space-between;
  margin-top: 0.3rem;
  font-size: 0.6rem;
  color: var(--text-muted);
}

.combos-section {
  margin-bottom: 1rem;
}

.sub-title {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 0.5rem;
}

.combo-cards {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.combo-card {
  flex: 1 1 calc(50% - 0.25rem);
  min-width: 0;
  padding: 0.6rem 0.5rem;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  text-align: center;
  cursor: pointer;
  transition: all 0.2s;
}

.combo-card.active {
  border-color: var(--color-primary);
  background: var(--color-primary-light);
}

.combo-emoji {
  display: block;
  font-size: 1.1rem;
  margin-bottom: 0.2rem;
}

.combo-name {
  display: block;
  font-weight: 600;
  font-size: 0.75rem;
  color: var(--text-primary);
}

.combo-detail {
  display: block;
  font-size: 0.6rem;
  color: var(--text-muted);
  margin-top: 0.1rem;
}

/* Exercise grid */
.exercise-grid {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.exercise-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 0.85rem;
  background: var(--bg-card);
  border: 2px solid var(--border-color);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all 0.2s;
  text-align: left;
}

.exercise-item.selected {
  border-color: var(--color-primary);
  background: var(--color-primary-light);
}

.ex-info {
  display: flex;
  flex-direction: column;
}

.ex-name {
  font-weight: 600;
  font-size: 0.9rem;
  color: var(--text-primary);
}

.ex-muscle {
  font-size: 0.75rem;
  color: var(--text-muted);
}

.ex-badges {
  display: flex;
  gap: 0.35rem;
}

.badge {
  padding: 0.2rem 0.5rem;
  border-radius: var(--radius-full);
  font-size: 0.65rem;
  font-weight: 500;
}

.badge.difficulty.beginner {
  background: var(--color-success-light);
  color: var(--color-success);
}

.badge.difficulty.intermediate {
  background: var(--color-warning-light);
  color: var(--color-warning);
}

.badge.difficulty.advanced {
  background: var(--color-destructive-light);
  color: var(--color-destructive);
}

/* Selected tray */
.selected-tray {
  position: fixed;
  bottom: 4.5rem;
  left: 50%;
  transform: translateX(-50%);
  width: calc(100% - 2rem);
  max-width: 400px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  padding: 0.85rem;
  z-index: 50;
  animation: slideUp 0.3s ease;
}

@keyframes slideUp {
  from { opacity: 0; transform: translateX(-50%) translateY(12px); }
  to { opacity: 1; transform: translateX(-50%) translateY(0); }
}

.tray-content {
  margin-bottom: 0.65rem;
}

.tray-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.3rem;
  margin-bottom: 0.35rem;
}

.tray-chip {
  padding: 0.25rem 0.55rem;
  border-radius: var(--radius-full);
  background: var(--color-primary-light);
  color: var(--color-primary);
  font-size: 0.7rem;
  font-weight: 500;
  cursor: pointer;
}

.tray-meta {
  font-size: 0.75rem;
  color: var(--text-muted);
}

.tray-buttons {
  display: flex;
  gap: 0.5rem;
}

.btn-save-combo {
  padding: 0.7rem;
  background: var(--bg-input);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  cursor: pointer;
  color: var(--text-secondary);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.btn-save-combo:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.tray-btn {
  flex: 1;
}

/* Saved workouts */
.saved-card {
  position: relative;
  border-color: var(--color-secondary);
  border-style: dashed;
}

.remove-saved {
  position: absolute;
  top: 2px;
  right: 4px;
  background: none;
  border: none;
  color: var(--text-muted);
  font-size: 0.9rem;
  cursor: pointer;
  padding: 0 4px;
  line-height: 1;
}

.remove-saved:hover {
  color: var(--color-destructive);
}

/* Buttons */
.btn-primary {
  padding: 0.7rem 1.25rem;
  background: var(--gradient-primary);
  color: white;
  border: none;
  border-radius: var(--radius-md);
  font-weight: 600;
  font-size: 0.9rem;
  cursor: pointer;
}

.btn-primary:hover { opacity: 0.9; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }

/* Toast */
.toast {
  position: fixed;
  bottom: 10rem;
  left: 50%;
  transform: translateX(-50%);
  padding: 0.65rem 1.25rem;
  background: var(--color-primary);
  color: #fff;
  font-weight: 600;
  border-radius: var(--radius-full);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
  font-size: 0.8rem;
  z-index: 100;
  max-width: 90%;
  text-align: center;
}
</style>
