<template>
  <div class="active-set">
    <!-- Camera Mode -->
    <template v-if="cameraActive">
      <div class="camera-container">
        <video ref="videoEl" class="camera-feed" autoplay playsinline muted></video>
        <canvas ref="overlayCanvas" class="pose-overlay"></canvas>

        <!-- Ready indicator -->
        <div v-if="!camera.playerReady.value" class="camera-hud-center">
          <div class="ready-circle" :class="{ detected: camera.playerDetected.value }">
            <span v-if="camera.playerDetected.value">Get ready...</span>
            <span v-else>Position yourself</span>
          </div>
        </div>

        <!-- Rep counter (top-left) -->
        <div class="camera-hud-top">
          <div class="rep-counter">
            <span class="rep-number">{{ displayCount }}</span>
            <span class="rep-label">{{ isHoldExercise ? 'sec' : 'reps' }}</span>
          </div>
        </div>

        <!-- Form feedback toast (bottom) -->
        <div v-if="camera.formFeedback.value" class="camera-feedback-toast">
          {{ camera.formFeedback.value }}
        </div>

        <!-- Set info bar -->
        <div class="camera-info-bar">
          <span>Set {{ data.set_number }}/{{ data.sets_total }}</span>
          <button class="mode-switch-btn" @click="switchToManual">Manual</button>
          <span>{{ setTimerFormatted }}</span>
        </div>
      </div>

      <div class="set-actions">
        <button class="btn-primary full-width" @click="finishCameraSet">
          Done
        </button>
      </div>
    </template>

    <!-- Manual Mode -->
    <template v-else>
      <div class="set-content">
        <!-- Set info -->
        <div class="set-header">
          <span class="set-label">Set {{ data.set_number }} of {{ data.sets_total }}</span>
          <span class="exercise-name">{{ exercise.name }}</span>
          <button v-if="isTrackable" class="mode-switch-link" @click="switchToCamera">Switch to Camera</button>
        </div>

        <!-- Target display -->
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

        <!-- Progression hint -->
        <div v-if="data.progression" class="progression-hint">
          <span v-if="data.progression.weight_kg">Target: {{ data.progression.weight_kg }}kg</span>
          <span v-if="data.progression.reps"> x {{ data.progression.reps }}</span>
        </div>

        <!-- Set timer (counts up) -->
        <div class="set-timer">
          {{ setTimerFormatted }}
        </div>

        <!-- Coach says -->
        <div v-if="coachSays" class="coach-inline">{{ coachSays }}</div>
      </div>

      <!-- Complete Set Button -->
      <div class="set-actions">
        <button v-if="!showForm" class="btn-primary full-width complete-btn" @click="showForm = true">
          Complete Set
        </button>

        <!-- Inline form for logging -->
        <div v-if="showForm" class="log-form">
          <h3 class="form-title">Log Set</h3>

          <!-- Reps stepper -->
          <div class="stepper-row">
            <span class="stepper-label">Reps</span>
            <div class="stepper">
              <button class="stepper-btn" @click="reps = Math.max(0, reps - 1)">-</button>
              <input type="number" v-model.number="reps" class="stepper-input" min="0" />
              <button class="stepper-btn" @click="reps++">+</button>
            </div>
          </div>

          <!-- Weight stepper -->
          <div class="stepper-row">
            <span class="stepper-label">Weight (kg)</span>
            <div class="stepper">
              <button class="stepper-btn" @click="weight = Math.max(0, weight - 2.5)">-</button>
              <input type="number" v-model.number="weight" class="stepper-input" min="0" step="2.5" />
              <button class="stepper-btn" @click="weight += 2.5">+</button>
            </div>
          </div>

          <!-- RPE emoji selector -->
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
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useCameraTracking } from '@/composables/useCameraTracking'

const props = defineProps({
  data: { type: Object, required: true },
  coachSays: { type: String, default: '' },
  progress: { type: Object, default: null },
  useCamera: { type: Boolean, default: true },
})

const emit = defineEmits(['action'])

const exercise = computed(() => props.data.exercise || {})
const showForm = ref(false)
const reps = ref(props.data.target_reps || 10)
const weight = ref(0)
const rpe = ref(null)

const rpeOptions = [
  { value: 1, emoji: '1', label: 'Very Easy' },
  { value: 3, emoji: '3', label: 'Easy' },
  { value: 5, emoji: '5', label: 'Moderate' },
  { value: 7, emoji: '7', label: 'Hard' },
  { value: 9, emoji: '9', label: 'Very Hard' },
  { value: 10, emoji: '10', label: 'Max' },
]

// Set timer (counts up from 0)
const setSeconds = ref(0)
let setTimerInterval = null

const setTimer = computed(() => setSeconds.value)
const setTimerFormatted = computed(() => {
  const m = Math.floor(setSeconds.value / 60)
  const s = setSeconds.value % 60
  return `${m}:${s.toString().padStart(2, '0')}`
})

// --- Camera tracking (reuses challenge WebSocket infrastructure) ---
const TRACKABLE_SLUGS = [
  'push-up', 'bodyweight-squat', 'plank', 'squat-hold', 'jump-squat', 'burpee',
  'bicep-curl', 'lateral-raise', 'calf-raise',
]
const isHoldExercise = computed(() => ['plank', 'squat-hold'].includes(exercise.value.slug))
const isTrackable = computed(() => TRACKABLE_SLUGS.includes(exercise.value.slug))
const cameraMode = computed(() => props.useCamera && isTrackable.value)
const cameraActive = ref(cameraMode.value)

async function switchToManual() {
  const report = await camera.stop()
  cameraActive.value = false
  // Pre-fill reps from camera count
  reps.value = isHoldExercise.value
    ? Math.floor(report.holdSeconds || 0)
    : (report.reps || 0)
}

async function switchToCamera() {
  cameraActive.value = true
  await nextTick()
  if (videoEl.value) {
    await camera.initCamera(videoEl.value, overlayCanvas.value)
    if (camera.isReady.value) {
      camera.start(props.data.session_id, exercise.value.slug)
    }
  }
}

const videoEl = ref(null)
const overlayCanvas = ref(null)

const camera = useCameraTracking()

// Display: hold seconds for hold-based, reps for rep-based
const displayCount = computed(() => {
  if (isHoldExercise.value) {
    return Math.floor(camera.holdSeconds.value)
  }
  return camera.reps.value
})

onMounted(async () => {
  setTimerInterval = setInterval(() => {
    setSeconds.value++
  }, 1000)

  // Init camera if trackable and camera mode enabled
  if (cameraActive.value) {
    await nextTick()
    if (videoEl.value) {
      await camera.initCamera(videoEl.value, overlayCanvas.value)
      if (camera.isReady.value) {
        // Pass workout session ID — composable creates a challenge session under the hood
        camera.start(props.data.session_id, exercise.value.slug)
      }
    }
  }
})

onUnmounted(() => {
  if (setTimerInterval) clearInterval(setTimerInterval)
  camera.destroy()
})

async function finishCameraSet() {
  const report = await camera.stop()
  const finalReps = isHoldExercise.value
    ? Math.floor(report.holdSeconds || 0)
    : (report.reps || 0)
  emit('action', 'complete_set', {
    exercise_id: exercise.value.exercise_id,
    set_number: props.data.set_number,
    reps: finalReps,
    form_score: report.formScore || null,
    duration_seconds: setSeconds.value,
  })
}

function saveSet() {
  emit('action', 'complete_set', {
    exercise_id: exercise.value.exercise_id,
    set_number: props.data.set_number,
    reps: reps.value,
    weight_kg: weight.value || null,
    rpe: rpe.value,
    duration_seconds: setSeconds.value,
  })
}
</script>

<style scoped>
.active-set {
  min-height: 100vh;
  min-height: 100dvh;
  display: flex;
  flex-direction: column;
  padding-top: 3.5rem;
}

/* Camera mode */
.camera-container {
  flex: 1;
  position: relative;
  background: #000;
  overflow: hidden;
}

.camera-feed {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transform: scaleX(-1); /* mirror */
}

.pose-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  transform: scaleX(-1);
}

.camera-hud-center {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 5;
}

.ready-circle {
  width: 120px;
  height: 120px;
  border-radius: 50%;
  background: rgba(200, 60, 60, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 0.8rem;
  font-weight: 600;
  text-align: center;
  transition: background 0.3s;
}

.ready-circle.detected {
  background: rgba(93, 157, 118, 0.7);
}

.camera-hud-top {
  position: absolute;
  top: 0.75rem;
  left: 0.75rem;
  right: 0.75rem;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.rep-counter {
  background: rgba(0, 0, 0, 0.6);
  border-radius: var(--radius-lg);
  padding: 0.5rem 0.85rem;
  text-align: center;
}

.rep-number {
  font-size: 2.5rem;
  font-weight: 800;
  color: #fff;
  line-height: 1;
  display: block;
  font-variant-numeric: tabular-nums;
}

.rep-label {
  font-size: 0.7rem;
  color: rgba(255, 255, 255, 0.7);
  text-transform: uppercase;
}

.form-badge {
  font-size: 1.1rem;
  font-weight: 700;
  padding: 0.4rem 0.75rem;
  border-radius: var(--radius-lg);
  color: #fff;
}

.form-good { background: rgba(93, 157, 118, 0.85); }
.form-ok { background: rgba(212, 175, 55, 0.85); }
.form-low { background: rgba(200, 80, 80, 0.85); }

.camera-feedback-toast {
  position: absolute;
  bottom: 4rem;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(0, 0, 0, 0.7);
  color: #fff;
  padding: 0.5rem 1rem;
  border-radius: var(--radius-md);
  font-size: 0.85rem;
  font-weight: 600;
  max-width: 80%;
  text-align: center;
  animation: fadeInUp 0.3s ease;
}

.camera-info-bar {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  background: rgba(0, 0, 0, 0.5);
  color: #fff;
  padding: 0.5rem 1rem;
  display: flex;
  justify-content: space-between;
  font-size: 0.8rem;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

@keyframes fadeInUp {
  from { opacity: 0; transform: translateX(-50%) translateY(8px); }
  to { opacity: 1; transform: translateX(-50%) translateY(0); }
}

/* Manual mode */
.set-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 1.5rem 1.25rem;
  text-align: center;
}

.set-header {
  margin-bottom: 1rem;
}

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

.target-display {
  margin-bottom: 0.5rem;
}

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

.progression-hint {
  font-size: 0.8rem;
  color: var(--color-primary);
  font-weight: 600;
  margin-bottom: 0.5rem;
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

.complete-btn {
  font-size: 1.1rem;
  padding: 1rem;
}

/* Log form */
.log-form {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 1rem;
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
  border: 1px solid var(--border-input);
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
  border-radius: var(--radius-md);
  font-weight: 600;
  font-size: 0.9rem;
  cursor: pointer;
}

.full-width { width: 100%; }

.mode-switch-btn {
  background: rgba(255, 255, 255, 0.2);
  border: 1px solid rgba(255, 255, 255, 0.3);
  color: #fff;
  padding: 0.2rem 0.5rem;
  border-radius: var(--radius-md);
  font-size: 0.7rem;
  font-weight: 600;
  cursor: pointer;
}

.mode-switch-link {
  display: block;
  margin-top: 0.35rem;
  background: none;
  border: none;
  color: var(--color-primary);
  font-size: 0.75rem;
  font-weight: 600;
  cursor: pointer;
  text-decoration: underline;
}
</style>
