<template>
  <div class="library">
    <router-link to="/workout" class="back-link">&larr; Back</router-link>
    <h1 class="page-title">Exercise Library</h1>

    <!-- Search -->
    <div class="search-wrap">
      <input
        v-model="search"
        type="text"
        class="search-input"
        placeholder="Search exercises..."
        @input="debouncedFetch"
      />
    </div>

    <!-- Muscle group filter tabs -->
    <div class="filter-tabs">
      <button
        v-for="mg in muscleGroups"
        :key="mg.value"
        class="filter-tab"
        :class="{ active: selectedMuscle === mg.value }"
        @click="selectMuscle(mg.value)"
      >
        {{ mg.label }}
      </button>
    </div>

    <!-- Exercise list -->
    <div class="exercise-list">
      <router-link
        v-for="ex in workoutStore.exercises"
        :key="ex.slug"
        :to="`/workout/exercises/${ex.slug}`"
        class="exercise-row"
      >
        <div class="ex-info">
          <span class="ex-name">{{ ex.name }}</span>
          <div class="ex-meta">
            <span class="badge muscle">{{ ex.primary_muscle }}</span>
            <span class="badge difficulty" :class="ex.difficulty">{{ ex.difficulty }}</span>
            <span v-if="ex.tracking_mode === 'hold'" class="badge mode">Hold</span>
            <span v-if="ex.tracking_mode === 'timed'" class="badge mode">Timed</span>
          </div>
        </div>
        <div class="ex-equipment">
          <span v-for="eq in (ex.equipment || [])" :key="eq" class="eq-tag">
            {{ eq === 'none' ? 'Bodyweight' : eq }}
          </span>
        </div>
        <svg class="arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg>
      </router-link>

      <div v-if="workoutStore.exercises.length === 0" class="empty-state">
        <p>No exercises found.</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useWorkoutStore } from '../../stores/workout'

const workoutStore = useWorkoutStore()
const search = ref('')
const selectedMuscle = ref('')

const muscleGroups = [
  { value: '', label: 'All' },
  { value: 'chest', label: 'Chest' },
  { value: 'back', label: 'Back' },
  { value: 'quads', label: 'Legs' },
  { value: 'shoulders', label: 'Shoulders' },
  { value: 'biceps', label: 'Arms' },
  { value: 'core', label: 'Core' },
]

let debounceTimer = null

function debouncedFetch() {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(fetchExercises, 300)
}

function selectMuscle(mg) {
  selectedMuscle.value = mg
  fetchExercises()
}

function fetchExercises() {
  const params = {}
  if (search.value) params.search = search.value
  if (selectedMuscle.value) params.muscle_group = selectedMuscle.value
  workoutStore.fetchExercises(params)
}

onMounted(() => {
  fetchExercises()
})
</script>

<style scoped>
.library {
  padding: 1.25rem;
  padding-bottom: 6rem; /* space for bottom nav */
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

.search-input:focus { border-color: var(--border-input-focus); }

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

/* Exercise list */
.exercise-list {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.exercise-row {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  padding: 0.85rem;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  text-decoration: none;
  transition: all 0.2s;
}

.exercise-row:hover {
  box-shadow: var(--shadow-sm);
  transform: translateY(-1px);
}

.ex-info {
  flex: 1;
  min-width: 0;
}

.ex-name {
  display: block;
  font-weight: 600;
  font-size: 0.9rem;
  color: var(--text-primary);
  margin-bottom: 0.25rem;
}

.ex-meta {
  display: flex;
  gap: 0.25rem;
  flex-wrap: wrap;
}

.badge {
  padding: 0.15rem 0.45rem;
  border-radius: var(--radius-full);
  font-size: 0.6rem;
  font-weight: 500;
}

.badge.muscle {
  background: var(--color-info-light);
  color: var(--color-info);
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

.badge.mode {
  background: var(--color-secondary-light);
  color: var(--color-secondary);
}

.ex-equipment {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 0.15rem;
}

.eq-tag {
  font-size: 0.6rem;
  color: var(--text-muted);
  white-space: nowrap;
}

.arrow {
  width: 16px;
  height: 16px;
  color: var(--text-muted);
  flex-shrink: 0;
}

.empty-state {
  text-align: center;
  padding: 2rem;
  color: var(--text-muted);
}
</style>
