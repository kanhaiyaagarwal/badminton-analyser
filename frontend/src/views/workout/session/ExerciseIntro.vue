<template>
  <div class="exercise-intro">
    <!-- Progress bar -->
    <div class="progress-bar-wrap" v-if="progress">
      <div class="progress-bar" :style="{ width: progressPct + '%' }"></div>
    </div>

    <div class="intro-content">
      <!-- Exercise name -->
      <h1 class="exercise-name">{{ exercise.name }}</h1>
      <p class="exercise-target">{{ exercise.sets }} sets x {{ exercise.reps }}</p>

      <!-- Camera tracking badge -->
      <div v-if="isTrackable" class="tracking-badge">
        <span class="tracking-icon">*</span>
        Camera Tracking
      </div>

      <!-- Form cues -->
      <div v-if="formCues.length > 0" class="form-cues">
        <h3 class="cues-title">Form Cues</h3>
        <ul class="cues-list">
          <li v-for="(cue, i) in formCues" :key="i">{{ cue }}</li>
        </ul>
      </div>

      <!-- History -->
      <div v-if="history?.last_session" class="history-section">
        <div class="history-row">
          <span class="history-label">Last Session</span>
          <span class="history-value">
            {{ history.last_session.best_reps }} reps
            <template v-if="history.last_session.best_weight"> @ {{ history.last_session.best_weight }}kg</template>
          </span>
        </div>
        <div v-if="history.pr_reps" class="history-row">
          <span class="history-label">PR Reps</span>
          <span class="history-value highlight">{{ history.pr_reps }}</span>
        </div>
        <div v-if="history.pr_weight" class="history-row">
          <span class="history-label">PR Weight</span>
          <span class="history-value highlight">{{ history.pr_weight }}kg</span>
        </div>
      </div>

      <!-- Coach bubble -->
      <div v-if="coachSays" class="coach-bubble">
        <img src="/mascot/otter-mascot.png" alt="Coach" class="coach-avatar" />
        <div class="coach-text">{{ coachSays }}</div>
      </div>
    </div>

    <!-- Actions -->
    <div class="intro-actions">
      <button class="btn-primary full-width" @click="beginSet">Begin Set</button>
      <button class="btn-outline full-width" @click="skipExercise">Skip Exercise</button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  data: { type: Object, required: true },
  coachSays: { type: String, default: '' },
  progress: { type: Object, default: null },
})

const emit = defineEmits(['action'])

const exercise = computed(() => props.data.exercise || {})
const formCues = computed(() => props.data.form_cues || [])
const history = computed(() => props.data.history || null)

const TRACKABLE_SLUGS = ['push-up', 'bodyweight-squat', 'plank', 'squat-hold', 'jump-squat', 'burpee']
const isTrackable = computed(() => TRACKABLE_SLUGS.includes(exercise.value.slug))

const progressPct = computed(() => {
  if (!props.progress) return 0
  return Math.round((props.progress.exercise_index / Math.max(1, props.progress.exercise_total)) * 100)
})

function beginSet() {
  // Emit skip_rest to go to active_set view
  emit('action', 'skip_rest', {
    exercise_id: exercise.value.exercise_id,
    set_number: 1,
  })
}

function skipExercise() {
  emit('action', 'skip_exercise', {
    exercise_id: exercise.value.exercise_id,
  })
}
</script>

<style scoped>
.exercise-intro {
  min-height: 100vh;
  min-height: 100dvh;
  display: flex;
  flex-direction: column;
  padding-top: 3.5rem; /* space for topbar */
}

.progress-bar-wrap {
  height: 3px;
  background: var(--border-color);
  position: fixed;
  top: 3rem;
  left: 50%;
  transform: translateX(-50%);
  width: 100%;
  max-width: 430px;
  z-index: 21;
}

.progress-bar {
  height: 100%;
  background: var(--color-primary);
  transition: width 0.3s ease;
  border-radius: 2px;
}

.intro-content {
  flex: 1;
  padding: 1.5rem 1.25rem;
}

.exercise-name {
  font-size: 1.75rem;
  font-weight: 800;
  color: var(--text-primary);
  margin-bottom: 0.25rem;
}

.exercise-target {
  font-size: 1rem;
  color: var(--text-muted);
  margin-bottom: 1.5rem;
}

.form-cues {
  margin-bottom: 1.25rem;
}

.cues-title {
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 0.5rem;
}

.cues-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.cues-list li {
  padding: 0.35rem 0;
  font-size: 0.85rem;
  color: var(--text-primary);
  border-bottom: 1px solid var(--border-color);
}

.cues-list li::before {
  content: '\2713  ';
  color: var(--color-primary);
  font-weight: 700;
}

.history-section {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 0.85rem;
  margin-bottom: 1.25rem;
}

.history-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.3rem 0;
}

.history-label {
  font-size: 0.8rem;
  color: var(--text-muted);
}

.history-value {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--text-primary);
}

.history-value.highlight {
  color: var(--color-primary);
}

.coach-bubble {
  display: flex;
  align-items: flex-start;
  gap: 0.65rem;
  margin-top: 1rem;
}

.coach-avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  object-fit: cover;
  flex-shrink: 0;
}

.coach-text {
  padding: 0.5rem 0.75rem;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 0 var(--radius-md) var(--radius-md) var(--radius-md);
  font-size: 0.8rem;
  color: var(--text-secondary);
  line-height: 1.4;
}

.intro-actions {
  padding: 1rem 1.25rem;
  padding-bottom: calc(1rem + env(safe-area-inset-bottom, 0px));
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
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

.btn-outline {
  padding: 0.75rem 1.25rem;
  background: transparent;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  font-weight: 600;
  font-size: 0.9rem;
  cursor: pointer;
  color: var(--text-secondary);
}

.full-width { width: 100%; }

.tracking-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.3rem 0.65rem;
  background: var(--color-primary);
  color: white;
  border-radius: 999px;
  font-size: 0.7rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  margin-bottom: 1rem;
}

.tracking-icon {
  font-size: 0.9rem;
  line-height: 1;
}
</style>
