<template>
  <div class="active-set">
    <!-- Phase 1: Active tracking (camera or manual timer) -->
    <template v-if="phase === 'tracking'">
      <!-- Camera Mode — fullscreen, matches ChallengeSessionView -->
      <template v-if="cameraActive">
        <div class="camera-fullscreen">
          <video ref="videoEl" class="camera-feed" autoplay playsinline muted></video>
          <canvas ref="overlayCanvas" class="pose-overlay"></canvas>

          <!-- HUD (top-left, matches challenge style) -->
          <div class="hud">
            <div class="hud-metric primary">
              <span class="metric-value">{{ displayCount }}</span>
              <span class="metric-label">{{ isHoldExercise ? 'Hold (s)' : 'Reps' }}</span>
            </div>
            <div class="hud-metric">
              <span class="metric-value">{{ setTimerFormatted }}</span>
              <span class="metric-label">Time</span>
            </div>
          </div>

          <!-- Exercise + set info (top-right) -->
          <div class="set-info-badge">
            {{ exercise.name }} — Set {{ data.set_number }}/{{ data.sets_total }}
          </div>

          <!-- Form feedback (bottom, color-coded) -->
          <div
            v-if="camera.formFeedback.value"
            class="form-feedback"
            :class="feedbackClass"
          >
            {{ camera.formFeedback.value }}
          </div>

          <!-- Rep pop animation -->
          <transition name="rep-pop">
            <div v-if="showRepPop" class="rep-pop-overlay" :key="repPopKey">
              <span class="rep-pop-number">{{ repPopValue }}</span>
            </div>
          </transition>

          <!-- Bottom bar: End Set -->
          <div class="session-bottom-bar">
            <button class="bar-btn end-btn" @click="endSet">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="20" height="20" stroke-linecap="round" stroke-linejoin="round"><rect x="6" y="6" width="12" height="12" rx="2"/></svg>
              <span>End Set</span>
            </button>
          </div>
        </div>
      </template>

      <!-- Manual Mode (non-trackable or camera off) -->
      <template v-else>
        <div class="set-content">
          <div class="set-header">
            <span class="set-label">Set {{ data.set_number }} of {{ data.sets_total }}</span>
            <span class="exercise-name">{{ exercise.name }}</span>
          </div>
          <div class="target-display">
            <template v-if="data.target_reps">
              <span class="target-number">{{ data.target_reps }}</span>
              <span class="target-unit">reps</span>
            </template>
            <template v-else>
              <span class="target-number">{{ setTimer }}</span>
              <span class="target-unit">seconds</span>
            </template>
          </div>
          <div class="set-timer">{{ setTimerFormatted }}</div>
          <div v-if="coachSays" class="coach-inline">{{ coachSays }}</div>
        </div>
        <div class="set-actions">
          <button class="btn-end full-width" @click="endSet">End Set</button>
        </div>
      </template>
    </template>

    <!-- Phase 2: Log form (after ending set) -->
    <template v-if="phase === 'logging'">
      <div class="set-content">
        <div class="set-header">
          <span class="set-label">Set {{ data.set_number }} of {{ data.sets_total }}</span>
          <span class="exercise-name">{{ exercise.name }}</span>
        </div>

        <div class="log-form">
          <h3 class="form-title">Log Set</h3>

          <div class="stepper-row">
            <span class="stepper-label">Reps</span>
            <div class="stepper">
              <button class="stepper-btn" @click="reps = Math.max(0, reps - 1)">-</button>
              <input type="number" v-model.number="reps" class="stepper-input" min="0" />
              <button class="stepper-btn" @click="reps++">+</button>
            </div>
          </div>

          <div class="stepper-row">
            <span class="stepper-label">Weight (kg)</span>
            <div class="stepper">
              <button class="stepper-btn" @click="weight = Math.max(0, weight - 2.5)">-</button>
              <input type="number" v-model.number="weight" class="stepper-input" min="0" step="2.5" />
              <button class="stepper-btn" @click="weight += 2.5">+</button>
            </div>
          </div>

          <div class="rpe-row">
            <span class="stepper-label">Effort</span>
            <div class="rpe-options">
              <button
                v-for="r in rpeOptions"
                :key="r.value"
                class="rpe-btn"
                :class="{ active: rpe === r.value }"
                @click="rpe = r.value"
                :title="r.label"
              >
                {{ r.emoji }}
              </button>
            </div>
          </div>

          <button class="btn-primary full-width" @click="saveSet">Save</button>
          <button class="btn-skip-exercise" @click="skipExercise">Skip Exercise</button>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { useCameraTracking } from '@/composables/useCameraTracking'

const props = defineProps({
  data: { type: Object, required: true },
  coachSays: { type: String, default: '' },
  progress: { type: Object, default: null },
  useCamera: { type: Boolean, default: true },
})

const emit = defineEmits(['action'])

const exercise = computed(() => props.data.exercise || {})
const phase = ref('tracking') // 'tracking' | 'logging'
const reps = ref(props.data.target_reps || 10)
const weight = ref(0)
const rpe = ref(null)
const cameraFormScore = ref(null)

const rpeOptions = [
  { value: 1, emoji: '1', label: 'Very Easy' },
  { value: 3, emoji: '3', label: 'Easy' },
  { value: 5, emoji: '5', label: 'Moderate' },
  { value: 7, emoji: '7', label: 'Hard' },
  { value: 9, emoji: '9', label: 'Very Hard' },
  { value: 10, emoji: '10', label: 'Max' },
]

// Set timer
const setSeconds = ref(0)
let setTimerInterval = null

const setTimer = computed(() => setSeconds.value)
const setTimerFormatted = computed(() => {
  const m = Math.floor(setSeconds.value / 60)
  const s = setSeconds.value % 60
  return `${m}:${s.toString().padStart(2, '0')}`
})

// --- Camera tracking ---
const TRACKABLE_SLUGS = [
  'push-up', 'diamond-push-up', 'wide-grip-push-up', 'burpee',
  'dips', 'tricep-dip-bench', 'pull-up', 'chin-up',
  'bench-press', 'incline-bench-press', 'decline-bench-press',
  'incline-dumbbell-press', 'close-grip-bench-press',
  'skull-crusher', 'dumbbell-fly', 'incline-dumbbell-fly',
  'bodyweight-squat', 'jump-squat', 'sumo-squat', 'front-squat', 'barbell-squat',
  'hack-squat', 'smith-machine-squat', 'bulgarian-split-squat', 'lunges', 'step-up',
  'box-jump', 'sissy-squat', 'deadlift', 'sumo-deadlift', 'kettlebell-swing',
  'barbell-thruster', 'hip-thrust', 'nordic-curl', 'leg-extension', 'cable-pull-through',
  'glute-bridge', 'donkey-kick', 'fire-hydrant', 'calf-raise', 'single-leg-calf-raise',
  'crunch', 'russian-twist', 'bicycle-crunch', 'hanging-leg-raise', 'v-up', 'dead-bug',
  'decline-sit-up', 'cable-crunch', 'ab-wheel-rollout', 'hyperextension', 'superman',
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
  'plank', 'side-plank', 'hollow-body-hold', 'squat-hold', 'wall-sit',
  'hip-flexor-stretch', 'pigeon-pose', 'childs-pose',
]
const isHoldExercise = computed(() => ['plank', 'squat-hold'].includes(exercise.value.slug))
const isTrackable = computed(() => TRACKABLE_SLUGS.includes(exercise.value.slug))
const cameraActive = ref(props.useCamera && isTrackable.value)

const videoEl = ref(null)
const overlayCanvas = ref(null)
const camera = useCameraTracking()

const displayCount = computed(() => {
  if (isHoldExercise.value) return Math.floor(camera.holdSeconds.value)
  return camera.reps.value
})

// Form feedback color class (matches challenge style)
const feedbackClass = computed(() => {
  const fb = (camera.formFeedback.value || '').toLowerCase()
  if (!fb) return ''
  // Positive keywords
  if (/good|great|perfect|nice|straight/.test(fb)) return 'positive'
  return 'corrective'
})

// Rep pop animation (matches challenge style)
const showRepPop = ref(false)
const repPopValue = ref(0)
const repPopKey = ref(0)
let repPopTimeout = null

watch(() => camera.reps.value, (newVal, oldVal) => {
  if (newVal > oldVal && newVal > 0 && !isHoldExercise.value) {
    repPopValue.value = newVal
    repPopKey.value++
    showRepPop.value = true
    if (repPopTimeout) clearTimeout(repPopTimeout)
    repPopTimeout = setTimeout(() => { showRepPop.value = false }, 800)
  }
})

const trackedChallengeSessionId = ref(null)

async function endSet() {
  if (cameraActive.value) {
    trackedChallengeSessionId.value = camera.getChallengeSessionId()
    const report = await camera.stop()
    const cameraReps = isHoldExercise.value
      ? Math.floor(report.holdSeconds || 0)
      : (report.reps || 0)
    reps.value = cameraReps
    cameraFormScore.value = report.formScore || null
    cameraActive.value = false
  }
  if (setTimerInterval) { clearInterval(setTimerInterval); setTimerInterval = null }
  phase.value = 'logging'
}

function saveSet() {
  emit('action', 'complete_set', {
    exercise_id: exercise.value.exercise_id,
    set_number: props.data.set_number,
    reps: reps.value,
    weight_kg: weight.value || null,
    rpe: rpe.value,
    form_score: cameraFormScore.value,
    duration_seconds: setSeconds.value,
    challenge_session_id: trackedChallengeSessionId.value,
  })
}

function skipExercise() {
  emit('action', 'skip_exercise', { exercise_id: exercise.value.exercise_id })
}

onMounted(async () => {
  setTimerInterval = setInterval(() => { setSeconds.value++ }, 1000)

  if (cameraActive.value) {
    await nextTick()
    if (videoEl.value) {
      await camera.initCamera(videoEl.value, overlayCanvas.value)
      if (camera.isReady.value) {
        camera.start(props.data.session_id, exercise.value.slug)
      }
    }
  }
})

onUnmounted(() => {
  if (setTimerInterval) clearInterval(setTimerInterval)
  if (repPopTimeout) clearTimeout(repPopTimeout)
  camera.destroy()
})
</script>

<style scoped>
.active-set {
  min-height: 100vh;
  min-height: 100dvh;
  display: flex;
  flex-direction: column;
  padding-top: 3.5rem;
}

/* ========== Camera — fullscreen, matches ChallengeSessionView ========== */

.camera-fullscreen {
  position: fixed;
  inset: 0;
  z-index: 100;
  background: #000;
}

/* Portrait: contain shows full frame (black bars top/bottom on tall phones) */
.camera-feed {
  width: 100%;
  height: 100%;
  object-fit: contain;
  display: block;
  transform: scaleX(-1);
}

.pose-overlay {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  transform: scaleX(-1);
}

/* HUD — top-left metric boxes (same as challenge) */
.hud {
  position: absolute;
  top: 1rem;
  top: calc(1rem + env(safe-area-inset-top, 0px));
  left: 1rem;
  display: flex;
  gap: 1.5rem;
  z-index: 2;
}

.hud-metric {
  background: rgba(0, 0, 0, 0.7);
  padding: 0.5rem 1rem;
  border-radius: var(--radius-md, 8px);
  text-align: center;
}

.hud-metric.primary {
  border: 1px solid var(--color-primary, #f26522);
}

.metric-value {
  display: block;
  color: var(--color-primary, #f26522);
  font-size: 1.8rem;
  font-weight: 700;
  line-height: 1;
  font-variant-numeric: tabular-nums;
}

.metric-label {
  display: block;
  color: #ccc;
  font-size: 0.75rem;
  font-weight: 500;
  margin-top: 0.25rem;
}

/* Exercise + set badge (top-right) */
.set-info-badge {
  position: absolute;
  top: 1rem;
  top: calc(1rem + env(safe-area-inset-top, 0px));
  right: 1rem;
  background: rgba(0, 0, 0, 0.7);
  color: #fff;
  padding: 0.4rem 0.75rem;
  border-radius: var(--radius-md, 8px);
  font-size: 0.75rem;
  font-weight: 600;
  z-index: 2;
}

/* Form feedback — color-coded (same as challenge) */
.form-feedback {
  position: absolute;
  bottom: 5rem;
  left: 50%;
  transform: translateX(-50%);
  padding: 0.5rem 1.25rem;
  border-radius: 9999px;
  font-size: 0.9rem;
  font-weight: 500;
  white-space: nowrap;
  z-index: 2;
  transition: background 0.3s ease, color 0.3s ease;
}

.form-feedback.positive {
  background: rgba(78, 204, 163, 0.2);
  color: #4ecca3;
  border: 1px solid rgba(78, 204, 163, 0.4);
}

.form-feedback.corrective {
  background: rgba(231, 76, 60, 0.2);
  color: #e74c3c;
  border: 1px solid rgba(231, 76, 60, 0.4);
}

/* Rep pop animation (same as challenge) */
.rep-pop-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  pointer-events: none;
  z-index: 10;
}

.rep-pop-number {
  font-size: 8rem;
  font-weight: 900;
  color: #4ecca3;
  text-shadow: 0 0 40px rgba(78, 204, 163, 0.6), 0 4px 20px rgba(0, 0, 0, 0.8);
  line-height: 1;
}

.rep-pop-enter-active {
  transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.rep-pop-leave-active {
  transition: all 0.5s ease-out;
}
.rep-pop-enter-from {
  opacity: 0;
  transform: scale(0.3);
}
.rep-pop-enter-to {
  opacity: 1;
  transform: scale(1);
}
.rep-pop-leave-from {
  opacity: 1;
  transform: scale(1);
}
.rep-pop-leave-to {
  opacity: 0;
  transform: scale(1.5);
}

/* Bottom bar (same style as challenge session-bottom-bar) */
.session-bottom-bar {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0.5rem 1rem;
  padding-bottom: calc(0.5rem + env(safe-area-inset-bottom, 0px));
  background: rgba(0, 0, 0, 0.85);
  backdrop-filter: blur(12px);
  z-index: 110;
}

.bar-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.2rem;
  background: transparent;
  border: none;
  color: rgba(255, 255, 255, 0.7);
  cursor: pointer;
  padding: 0.4rem 1.5rem;
  border-radius: var(--radius-md, 8px);
  transition: all 0.2s;
  font-family: inherit;
}

.bar-btn span {
  font-size: 0.65rem;
  font-weight: 500;
}

.bar-btn.end-btn:hover {
  color: var(--color-destructive, #dc2626);
}

/* ========== Manual mode ========== */

.set-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 1.5rem 1.25rem;
  text-align: center;
}

.set-header { margin-bottom: 1rem; }

.set-label {
  display: block;
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.exercise-name {
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--text-primary);
}

.target-display { margin-bottom: 0.5rem; }

.target-number {
  font-size: 4rem;
  font-weight: 800;
  color: var(--color-primary);
  line-height: 1;
}

.target-unit {
  display: block;
  font-size: 0.9rem;
  color: var(--text-muted);
  margin-top: 0.25rem;
}

.set-timer {
  font-size: 1.5rem;
  font-weight: 600;
  color: var(--text-secondary);
  font-variant-numeric: tabular-nums;
  margin-bottom: 1rem;
}

.coach-inline {
  font-size: 0.85rem;
  color: var(--text-secondary);
  max-width: 300px;
  line-height: 1.4;
}

.set-actions {
  padding: 1rem 1.25rem;
  padding-bottom: calc(1rem + env(safe-area-inset-bottom, 0px));
}

.btn-end {
  padding: 0.85rem 1.25rem;
  background: var(--color-destructive, #dc2626);
  color: white;
  border: none;
  border-radius: var(--radius-md, 8px);
  font-weight: 700;
  font-size: 1rem;
  cursor: pointer;
  transition: opacity 0.15s;
}

.btn-end:hover { opacity: 0.9; }

/* ========== Log form ========== */

.log-form {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg, 12px);
  padding: 1rem;
  width: 100%;
  max-width: 360px;
}

.form-title {
  font-size: 0.9rem;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 0.75rem;
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
  border-radius: var(--radius-md, 8px);
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
  border-radius: var(--radius-md, 8px);
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

.rpe-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.85rem;
}

.rpe-options {
  display: flex;
  gap: 0.3rem;
}

.rpe-btn {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  border: 1px solid var(--border-color);
  background: var(--bg-input);
  font-size: 0.8rem;
  font-weight: 600;
  cursor: pointer;
  color: var(--text-secondary);
  transition: all 0.2s;
}

.rpe-btn.active {
  border-color: var(--color-primary);
  background: var(--color-primary);
  color: white;
}

.btn-primary {
  padding: 0.75rem 1.25rem;
  background: var(--gradient-primary);
  color: white;
  border: none;
  border-radius: var(--radius-md, 8px);
  font-weight: 600;
  font-size: 0.9rem;
  cursor: pointer;
}

.btn-skip-exercise {
  width: 100%;
  margin-top: 0.5rem;
  padding: 0.6rem;
  background: transparent;
  border: none;
  color: var(--text-muted);
  font-size: 0.8rem;
  font-weight: 600;
  cursor: pointer;
  text-decoration: underline;
  text-underline-offset: 2px;
}

.btn-skip-exercise:hover {
  color: var(--text-secondary);
}

.full-width { width: 100%; }

/* ========== Mobile small screen ========== */
@media (max-width: 640px) {
  .hud { gap: 0.75rem; }
  .metric-value { font-size: 1.3rem; }
  .form-feedback { font-size: 0.8rem; padding: 0.4rem 1rem; }
  .rep-pop-number { font-size: 5rem; }
}

/* ========== Landscape — camera fills screen, controls compact ========== */
@media (orientation: landscape) and (max-height: 500px) {
  .active-set { padding-top: 0; }

  /* Fill screen edge-to-edge in landscape */
  .camera-feed { object-fit: cover; }

  .hud {
    top: 0.5rem;
    left: 0.5rem;
    gap: 0.75rem;
  }

  .hud-metric { padding: 0.3rem 0.75rem; }
  .metric-value { font-size: 1.3rem; }
  .metric-label { font-size: 0.65rem; }

  .set-info-badge {
    top: 0.5rem;
    right: 0.5rem;
    font-size: 0.65rem;
    padding: 0.3rem 0.5rem;
  }

  .session-bottom-bar { padding: 0.3rem 0.75rem; }

  .form-feedback {
    bottom: 3rem;
    font-size: 0.8rem;
  }

  .rep-pop-number { font-size: 5rem; }
}
</style>
