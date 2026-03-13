<template>
  <div class="brief-phase">
    <h1 class="day-label">{{ data.day_label || 'Workout' }}</h1>

    <!-- Coach bubble -->
    <div class="coach-bubble">
      <img src="/mascot/otter-mascot.png" alt="Coach" class="coach-avatar" />
      <div class="coach-text">{{ coachSays }}</div>
    </div>

    <!-- Time picker pills -->
    <div class="time-pills">
      <button
        v-for="t in timePills"
        :key="t"
        class="time-pill"
        :class="{ active: selectedTime === t }"
        @click="selectTime(t)"
      >
        {{ t === 0 ? 'Full Plan' : t + ' min' }}
      </button>
    </div>

    <!-- Exercise list -->
    <div class="exercise-list">
      <div v-for="(ex, i) in displayedExercises" :key="ex.exercise_id || i" class="exercise-row">
        <span class="ex-order">{{ i + 1 }}</span>
        <div class="ex-info">
          <span class="ex-name">{{ ex.name }}</span>
          <span class="ex-detail">{{ ex.sets }} x {{ ex.reps }}</span>
        </div>
      </div>
      <div v-if="trimmedCount > 0" class="trimmed-note">
        {{ trimmedCount }} exercise{{ trimmedCount > 1 ? 's' : '' }} trimmed to fit time
      </div>
    </div>

    <!-- Estimated time -->
    <div class="estimate">
      ~{{ data.estimated_minutes || 0 }} min estimated
    </div>

    <!-- Begin button -->
    <button class="btn-primary full-width" @click="$emit('action', 'begin_workout')">
      Begin Workout
    </button>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  data: { type: Object, required: true },
  coachSays: { type: String, default: '' },
})

const emit = defineEmits(['action'])

const timePills = [0, 20, 30, 45, 60]
const selectedTime = ref(props.data.time_budget_minutes || 0)

const allExercises = computed(() => props.data.exercises || [])

const displayedExercises = computed(() => {
  if (selectedTime.value === 0) return allExercises.value
  const max = Math.max(1, Math.floor(selectedTime.value / 5))
  return allExercises.value.slice(0, max)
})

const trimmedCount = computed(() => {
  return allExercises.value.length - displayedExercises.value.length
})

function selectTime(t) {
  selectedTime.value = t
  if (t > 0) {
    emit('action', 'adjust_time', { minutes: t })
  } else {
    // Reload full plan
    emit('action', 'adjust_time', { minutes: 0 })
  }
}
</script>

<style scoped>
.brief-phase {
  padding: 1.5rem 1.25rem;
  padding-bottom: 2rem;
}

.day-label {
  font-size: 1.5rem;
  font-weight: 800;
  color: var(--text-primary);
  margin-bottom: 1rem;
}

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

.time-pills {
  display: flex;
  gap: 0.35rem;
  margin-bottom: 1rem;
  overflow-x: auto;
}

.time-pill {
  padding: 0.35rem 0.75rem;
  border-radius: var(--radius-full);
  border: 1px solid var(--border-color);
  background: var(--bg-input);
  font-size: 0.75rem;
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

.exercise-list {
  margin-bottom: 1rem;
}

.exercise-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.65rem 0;
  border-bottom: 1px solid var(--border-color);
}

.ex-order {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: var(--color-primary-light);
  color: var(--color-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.7rem;
  font-weight: 700;
  flex-shrink: 0;
}

.ex-info {
  flex: 1;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.ex-name {
  font-weight: 600;
  font-size: 0.9rem;
  color: var(--text-primary);
}

.ex-detail {
  font-size: 0.8rem;
  color: var(--text-muted);
  white-space: nowrap;
}

.trimmed-note {
  padding: 0.5rem 0;
  font-size: 0.75rem;
  color: var(--text-muted);
  font-style: italic;
}

.estimate {
  font-size: 0.8rem;
  color: var(--text-muted);
  margin-bottom: 1rem;
  text-align: center;
}

.btn-primary {
  padding: 0.85rem 1.25rem;
  background: var(--gradient-primary);
  color: white;
  border: none;
  border-radius: var(--radius-md);
  font-weight: 600;
  font-size: 1rem;
  cursor: pointer;
}

.btn-primary:hover { opacity: 0.9; }
.full-width { width: 100%; display: block; }
</style>
