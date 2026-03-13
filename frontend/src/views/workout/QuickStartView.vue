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

    <!-- Quick Combos -->
    <div v-if="!search && selectedMuscle === 'All'" class="combos-section">
      <h3 class="sub-title">Quick Combos</h3>
      <div class="combo-cards">
        <button
          v-for="combo in quickCombos"
          :key="combo.name"
          class="combo-card"
          :class="{ active: activeCombo === combo.name }"
          @click="applyCombo(combo)"
        >
          <span class="combo-name">{{ combo.name }}</span>
          <span class="combo-time">{{ combo.time }}</span>
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
          &middot; ~{{ selectedSlugs.size * 5 }} min
        </div>
      </div>
      <button class="btn-primary tray-btn" @click="startQuickWorkout" :disabled="workoutStore.loading">
        Start Workout
      </button>
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

const muscleGroups = ['All', 'Chest', 'Back', 'Legs', 'Shoulders', 'Arms', 'Core']

const quickCombos = [
  { name: 'HIIT Blast', time: '15 min', slugs: ['push-up', 'bodyweight-squat', 'mountain-climber'] },
  { name: 'Upper Body', time: '20 min', slugs: ['bench-press', 'shoulder-press', 'barbell-row', 'bicep-curl'] },
  { name: 'Leg Day', time: '20 min', slugs: ['barbell-squat', 'romanian-deadlift', 'lunges', 'calf-raise'] },
]

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

function applyCombo(combo) {
  selectedSlugs.clear()
  combo.slugs.forEach(s => selectedSlugs.add(s))
  activeCombo.value = combo.name
}

async function startQuickWorkout() {
  try {
    const result = await workoutStore.startSession({
      exercise_slugs: [...selectedSlugs],
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
  padding-bottom: 8rem;
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
  gap: 0.5rem;
}

.combo-card {
  flex: 1;
  padding: 0.65rem 0.5rem;
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

.combo-name {
  display: block;
  font-weight: 600;
  font-size: 0.8rem;
  color: var(--text-primary);
}

.combo-time {
  display: block;
  font-size: 0.7rem;
  color: var(--text-muted);
  margin-top: 0.15rem;
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

.tray-btn {
  width: 100%;
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
  background: var(--text-primary);
  color: white;
  border-radius: var(--radius-full);
  font-size: 0.8rem;
  z-index: 100;
  max-width: 90%;
  text-align: center;
}
</style>
