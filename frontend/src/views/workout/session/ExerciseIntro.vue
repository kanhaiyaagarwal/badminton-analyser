<template>
  <div class="exercise-intro">
    <!-- Progress bar -->
    <div class="progress-bar-wrap" v-if="progress">
      <div class="progress-bar" :style="{ width: progressPct + '%' }"></div>
    </div>
    <p v-if="progress" class="progress-label">Exercise {{ progress.exercise_index + 1 }} of {{ progress.exercise_total }}</p>

    <div class="intro-content">
      <!-- Exercise card -->
      <div
        v-motion
        :initial="{ opacity: 0, y: 20 }"
        :enter="{ opacity: 1, y: 0, transition: { duration: 400 } }"
        class="exercise-card glass"
      >
        <!-- Camera tracking badge -->
        <div v-if="isTrackable" class="tracking-row">
          <div class="tracking-badge">
            <span class="tracking-emoji">📷</span>
            Camera Tracking
          </div>
          <button class="toggle-btn" :class="{ on: useCamera }" @click="useCamera = !useCamera">
            <span class="toggle-knob"></span>
          </button>
        </div>

        <!-- Exercise name -->
        <h2 class="exercise-name font-display">{{ exercise.name }}</h2>
        <p v-if="!editingTarget" class="exercise-target" @click="startEditing">
          {{ editSets }} sets × {{ editReps }} reps
        </p>

        <!-- Target editor -->
        <div v-if="editingTarget" class="target-editor">
          <div class="stepper-row">
            <span class="stepper-label">Sets</span>
            <div class="stepper">
              <button class="stepper-btn" @click="editSets = Math.max(1, editSets - 1)">-</button>
              <input type="number" v-model.number="editSets" class="stepper-input" min="1" max="10" />
              <button class="stepper-btn" @click="editSets = Math.min(10, editSets + 1)">+</button>
            </div>
          </div>
          <div class="stepper-row">
            <span class="stepper-label">Reps</span>
            <div class="stepper">
              <button class="stepper-btn" @click="editReps = Math.max(1, editReps - 1)">-</button>
              <input type="number" v-model.number="editReps" class="stepper-input" min="1" max="50" />
              <button class="stepper-btn" @click="editReps = Math.min(50, editReps + 1)">+</button>
            </div>
          </div>
          <div class="editor-actions">
            <button class="btn-sm btn-save" @click="saveTargets">Save</button>
            <button class="btn-sm btn-cancel" @click="cancelEditing">Cancel</button>
          </div>
        </div>

        <!-- Demo video -->
        <div v-if="videoId" class="demo-video">
          <div class="video-wrap" @click="showVideo = !showVideo">
            <template v-if="showVideo">
              <iframe
                :src="`https://www.youtube.com/embed/${videoId}?autoplay=1&loop=1&mute=1&playsinline=1&rel=0&modestbranding=1&fs=0&iv_load_policy=3&disablekb=0&playlist=${videoId}`"
                frameborder="0"
                allow="autoplay; encrypted-media"
                sandbox="allow-scripts allow-same-origin allow-presentation"
                class="video-iframe"
              ></iframe>
            </template>
            <template v-else>
              <img :src="`https://img.youtube.com/vi/${videoId}/0.jpg`" alt="Demo" class="video-thumb" />
              <div class="play-overlay">
                <svg viewBox="0 0 24 24" fill="white" width="32" height="32"><polygon points="5 3 19 12 5 21 5 3"/></svg>
              </div>
            </template>
          </div>
          <p class="demo-label">Tap to {{ showVideo ? 'hide' : 'watch' }} demo</p>
        </div>

        <!-- Form cues -->
        <div v-if="formCues.length > 0" class="form-cues">
          <h3 class="cues-title">Form Cues</h3>
          <ul class="cues-list">
            <li v-for="(cue, i) in formCues" :key="i">• {{ cue }}</li>
          </ul>
        </div>

        <!-- History -->
        <div v-if="history?.last_session" class="history-section">
          <h3 class="cues-title">Last Session</h3>
          <p class="history-line">
            Best: {{ history.last_session.best_reps }} reps
            <template v-if="history.last_session.best_weight"> @ {{ history.last_session.best_weight }}kg</template>
          </p>
          <p v-if="history.pr_weight" class="history-line">🏆 PR: {{ history.pr_weight }}kg</p>
        </div>
      </div>

      <!-- Coach bubble -->
      <div
        v-if="coachSays"
        v-motion
        :initial="{ opacity: 0 }"
        :enter="{ opacity: 1, transition: { delay: 200 } }"
        class="coach-bubble glass"
      >
        <div class="coach-bubble-inner">
          <div class="coach-avatar-ring">
            <span class="coach-emoji">🦦</span>
          </div>
          <p class="coach-text">"{{ coachSays }}"</p>
        </div>
      </div>
    </div>

    <!-- Actions -->
    <div class="intro-actions">
      <button class="btn-begin" @click="beginSet">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="20" height="20">
          <polygon points="5 3 19 12 5 21 5 3"/>
        </svg>
        Begin Set
      </button>
      <button class="btn-skip glass" @click="skipExercise">
        Skip Exercise
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  data: { type: Object, required: true },
  coachSays: { type: String, default: '' },
  progress: { type: Object, default: null },
})

const emit = defineEmits(['action'])

const exercise = computed(() => props.data.exercise || {})
const formCues = computed(() => props.data.form_cues || [])
const history = computed(() => props.data.history || null)
const showVideo = ref(false)

const videoId = computed(() => {
  const url = exercise.value.demo_video_url
  if (!url) return null
  // Extract YouTube video ID from shorts or regular URL
  const match = url.match(/(?:shorts\/|v=|youtu\.be\/)([a-zA-Z0-9_-]{11})/)
  return match ? match[1] : null
})

// All exercises that support camera-based rep/hold counting
// Keep in sync with WorkoutSessionView TRACKABLE_SLUG_TO_CHALLENGE
const TRACKABLE_SLUGS = [
  // Pushup analyzer
  'push-up', 'diamond-push-up', 'wide-grip-push-up', 'burpee',
  'dips', 'tricep-dip-bench', 'pull-up', 'chin-up',
  'bench-press', 'incline-bench-press', 'decline-bench-press',
  'incline-dumbbell-press', 'close-grip-bench-press',
  'skull-crusher', 'dumbbell-fly', 'incline-dumbbell-fly',
  // Squat analyzer
  'bodyweight-squat', 'jump-squat', 'sumo-squat', 'front-squat', 'barbell-squat',
  'hack-squat', 'smith-machine-squat', 'bulgarian-split-squat', 'lunges', 'step-up',
  'box-jump', 'sissy-squat', 'deadlift', 'sumo-deadlift', 'kettlebell-swing',
  'barbell-thruster', 'hip-thrust', 'nordic-curl', 'leg-extension', 'cable-pull-through',
  'glute-bridge', 'donkey-kick', 'fire-hydrant', 'calf-raise', 'single-leg-calf-raise',
  'crunch', 'russian-twist', 'bicycle-crunch', 'hanging-leg-raise', 'v-up', 'dead-bug',
  'decline-sit-up', 'cable-crunch', 'ab-wheel-rollout', 'hyperextension', 'superman',
  // Arm rep analyzer
  'bicep-curl', 'hammer-curl', 'preacher-curl', 'incline-dumbbell-curl',
  'concentration-curl', 'cable-curl', 'reverse-curl',
  'overhead-tricep-extension', 'tricep-pushdown', 'dumbbell-tricep-kickback',
  'lateral-raise', 'cable-lateral-raise', 'front-raise', 'reverse-fly',
  'shoulder-press', 'arnold-press',
  'barbell-shrug', 'dumbbell-shrug',
  'upright-row', 'barbell-row', 'single-arm-dumbbell-row', 't-bar-row',
  'seated-cable-row', 'chest-supported-row', 'pendlay-row',
  'good-morning', 'romanian-deadlift', 'stiff-leg-deadlift',
  'face-pull', 'glute-kickback',
  // Holds
  'plank', 'side-plank', 'hollow-body-hold', 'squat-hold', 'wall-sit',
  'hip-flexor-stretch', 'pigeon-pose', 'childs-pose',
]
const isTrackable = computed(() => TRACKABLE_SLUGS.includes(exercise.value.slug))
const useCamera = ref(true)

const editingTarget = ref(false)
const editSets = ref(exercise.value.sets || 3)
const editReps = ref(exercise.value.reps || 10)

function startEditing() {
  editSets.value = exercise.value.sets || 3
  editReps.value = exercise.value.reps || 10
  editingTarget.value = true
}

function cancelEditing() { editingTarget.value = false }

function saveTargets() {
  editingTarget.value = false
  emit('action', 'modify_exercise', {
    exercise_id: exercise.value.exercise_id,
    sets: editSets.value,
    reps: editReps.value,
  })
}

const progressPct = computed(() => {
  if (!props.progress) return 0
  return Math.round((props.progress.exercise_index / Math.max(1, props.progress.exercise_total)) * 100)
})

function beginSet() {
  emit('action', 'skip_rest', {
    exercise_id: exercise.value.exercise_id,
    set_number: 1,
    use_camera: isTrackable.value ? useCamera.value : false,
  })
}

function skipExercise() {
  emit('action', 'skip_exercise', { exercise_id: exercise.value.exercise_id })
}
</script>

<style scoped>
.exercise-intro {
  min-height: 100vh;
  min-height: 100dvh;
  display: flex;
  flex-direction: column;
  padding-top: 3.5rem;
}

/* Progress bar */
.progress-bar-wrap {
  height: 6px;
  border-radius: 3px;
  background: var(--text-muted);
  margin: 0 1.5rem;
  overflow: hidden;
}

.progress-bar {
  height: 100%;
  background: var(--color-primary);
  transition: width 0.3s ease;
  border-radius: 3px;
}

.progress-label {
  font-size: 0.75rem;
  color: var(--text-muted);
  margin: 0.5rem 1.5rem 0;
}

/* Content */
.intro-content {
  padding: 1rem 1.5rem;
}

/* Exercise card */
.exercise-card {
  padding: 1rem 1.25rem;
  border-radius: 1rem;
  margin-bottom: 0.75rem;
}

.tracking-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.75rem;
}

.tracking-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.3rem 0.75rem;
  background: rgba(20, 184, 166, 0.2);
  color: var(--color-secondary);
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 700;
}

.tracking-emoji {
  font-size: 0.85rem;
}

.toggle-btn {
  position: relative;
  width: 44px;
  height: 24px;
  border-radius: 12px;
  border: none;
  background: var(--text-muted);
  cursor: pointer;
  transition: background 0.2s;
  padding: 0;
  flex-shrink: 0;
}

.toggle-btn.on {
  background: var(--color-primary);
}

.toggle-knob {
  position: absolute;
  top: 2px;
  left: 2px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: white;
  transition: transform 0.2s;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.15);
}

.toggle-btn.on .toggle-knob {
  transform: translateX(20px);
}

.exercise-name {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 0.25rem;
}

.exercise-target {
  font-size: 0.95rem;
  color: var(--text-muted);
  margin-bottom: 1rem;
  cursor: pointer;
}

/* Demo video */
.demo-video {
  margin-bottom: 0.5rem;
}

.video-wrap {
  position: relative;
  width: 100%;
  aspect-ratio: 9/16;
  max-height: 280px;
  border-radius: 0.75rem;
  overflow: hidden;
  background: #000;
  cursor: pointer;
}

.video-iframe {
  width: 100%;
  height: 100%;
  border: none;
}

.video-thumb {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.play-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.35);
}

.demo-label {
  text-align: center;
  font-size: 0.7rem;
  color: var(--text-muted);
  margin-top: 0.35rem;
}

/* Form cues */
.form-cues {
  margin-bottom: 0.5rem;
}

.cues-title {
  font-size: 0.7rem;
  font-weight: 700;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin-bottom: 0.5rem;
}

.cues-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.cues-list li {
  padding: 0.2rem 0;
  font-size: 0.875rem;
  color: var(--text-primary);
}

/* History */
.history-section {
  margin-top: 0.5rem;
}

.history-line {
  font-size: 0.875rem;
  color: var(--text-primary);
  padding: 0.1rem 0;
}

/* Coach bubble */
.coach-bubble {
  padding: 0.75rem;
  border-radius: 0.75rem;
  margin-bottom: 0.5rem;
}

.coach-bubble-inner {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
}

.coach-avatar-ring {
  width: 32px;
  height: 32px;
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

/* Target editor */
.target-editor {
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 0.85rem;
  margin-bottom: 1rem;
}

.stepper-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.65rem;
}

.stepper-label {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--text-secondary);
}

.stepper {
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.stepper-btn {
  width: 36px;
  height: 36px;
  border-radius: var(--radius-md);
  border: 1px solid var(--border-color);
  background: var(--bg-input);
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--text-primary);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}

.stepper-input {
  width: 60px;
  text-align: center;
  padding: 0.4rem;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  background: var(--bg-input);
  font-size: 1rem;
  font-weight: 700;
  color: var(--text-primary);
  -moz-appearance: textfield;
}

.stepper-input::-webkit-outer-spin-button,
.stepper-input::-webkit-inner-spin-button {
  -webkit-appearance: none;
  margin: 0;
}

.editor-actions {
  display: flex;
  gap: 0.5rem;
  margin-top: 0.5rem;
}

.btn-sm {
  padding: 0.4rem 0.85rem;
  border-radius: var(--radius-md);
  font-size: 0.8rem;
  font-weight: 600;
  cursor: pointer;
  border: none;
}

.btn-save {
  background: var(--color-primary);
  color: var(--text-on-primary);
}

.btn-cancel {
  background: transparent;
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
}

/* Actions */
.intro-actions {
  padding: 1rem 1.5rem;
  padding-bottom: calc(1rem + env(safe-area-inset-bottom, 0px));
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.btn-begin {
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

.btn-begin:active {
  transform: scale(0.98);
}

.btn-skip {
  width: 100%;
  padding: 1rem;
  border-radius: 0.75rem;
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 1rem;
  cursor: pointer;
  color: var(--text-primary);
  transition: transform 0.15s;
}

.btn-skip:active {
  transform: scale(0.98);
}
</style>
