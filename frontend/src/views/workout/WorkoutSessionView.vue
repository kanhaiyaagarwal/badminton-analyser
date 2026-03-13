<template>
  <div class="workout-session">
    <!-- Loading -->
    <div v-if="loading && !activeSession" class="loading-screen">
      <div class="spinner"></div>
      <p>Loading workout...</p>
    </div>

    <!-- Brief Phase -->
    <BriefPhase
      v-else-if="view === 'brief'"
      :data="data"
      :coach-says="coachSays"
      @action="handleAction"
    />

    <!-- Exercise Intro -->
    <ExerciseIntro
      v-else-if="view === 'exercise_intro'"
      :data="data"
      :coach-says="coachSays"
      :progress="progress"
      @action="handleAction"
    />

    <!-- Active Set -->
    <ActiveSet
      v-else-if="view === 'active_set'"
      :data="data"
      :coach-says="coachSays"
      :progress="progress"
      @action="handleAction"
    />

    <!-- Rest Timer -->
    <RestTimer
      v-else-if="view === 'rest_timer'"
      :data="data"
      :coach-says="coachSays"
      :progress="progress"
      @action="handleAction"
    />

    <!-- Cooldown -->
    <CooldownPhase
      v-else-if="view === 'cooldown'"
      :data="data"
      :coach-says="coachSays"
      @action="handleAction"
    />

    <!-- Summary -->
    <SummaryPhase
      v-else-if="view === 'summary'"
      :data="data"
      :coach-says="coachSays"
      @action="handleAction"
      @done="handleDone"
    />

    <!-- Pause Overlay -->
    <div v-if="isPaused && view !== 'summary' && view !== 'brief'" class="pause-overlay" @click.self="isPaused = false">
      <div class="pause-card">
        <h2>Paused</h2>
        <p>{{ elapsedFormatted }}</p>
        <button class="btn-primary" @click="isPaused = false">Resume</button>
        <button class="btn-outline btn-danger" @click="handleEndWorkout">End Workout</button>
      </div>
    </div>

    <!-- Top bar (during workout) -->
    <div v-if="view && view !== 'brief' && view !== 'summary'" class="session-topbar">
      <button class="topbar-btn" @click="isPaused = true">
        <svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20"><rect x="6" y="4" width="4" height="16" rx="1"/><rect x="14" y="4" width="4" height="16" rx="1"/></svg>
      </button>
      <span class="topbar-timer">{{ elapsedFormatted }}</span>
      <div class="topbar-right">
        <button class="topbar-btn mute-btn" @click="voiceOutput.toggleMute()" :title="voiceOutput.muted.value ? 'Unmute' : 'Mute'">
          <svg v-if="!voiceOutput.muted.value" viewBox="0 0 24 24" fill="currentColor" width="18" height="18"><path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02z"/></svg>
          <svg v-else viewBox="0 0 24 24" fill="currentColor" width="18" height="18"><path d="M16.5 12c0-1.77-1.02-3.29-2.5-4.03v2.21l2.45 2.45c.03-.2.05-.41.05-.63zm2.5 0c0 .94-.2 1.82-.54 2.64l1.51 1.51C20.63 14.91 21 13.5 21 12c0-4.28-2.99-7.86-7-8.77v2.06c2.89.86 5 3.54 5 6.71zM4.27 3L3 4.27 7.73 9H3v6h4l5 5v-6.73l4.25 4.25c-.67.52-1.42.93-2.25 1.18v2.06c1.38-.31 2.63-.95 3.69-1.81L19.73 21 21 19.73l-9-9L4.27 3zM12 4L9.91 6.09 12 8.18V4z"/></svg>
        </button>
        <div class="topbar-progress" v-if="progress">
          {{ progress.exercise_index + 1 }}/{{ progress.exercise_total }}
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useWorkoutStore } from '../../stores/workout'
import { useVoiceOutput } from '../../composables/useVoiceOutput'
import BriefPhase from './session/BriefPhase.vue'
import ExerciseIntro from './session/ExerciseIntro.vue'
import ActiveSet from './session/ActiveSet.vue'
import RestTimer from './session/RestTimer.vue'
import CooldownPhase from './session/CooldownPhase.vue'
import SummaryPhase from './session/SummaryPhase.vue'

const route = useRoute()
const router = useRouter()
const workoutStore = useWorkoutStore()

const voiceOutput = useVoiceOutput()

const isPaused = ref(false)
const elapsedSeconds = ref(0)
let timerInterval = null

const loading = computed(() => workoutStore.loading)
const activeSession = computed(() => workoutStore.activeSession)
const view = computed(() => activeSession.value?.view)
const data = computed(() => activeSession.value?.data || {})
const coachSays = computed(() => activeSession.value?.coach_says || '')
const progress = computed(() => activeSession.value?.progress)
const sid = computed(() => workoutStore.sessionId || route.params.sessionId)

const elapsedFormatted = computed(() => {
  const m = Math.floor(elapsedSeconds.value / 60)
  const s = elapsedSeconds.value % 60
  return `${m}:${s.toString().padStart(2, '0')}`
})

function startTimer() {
  if (timerInterval) return
  timerInterval = setInterval(() => {
    if (!isPaused.value) {
      elapsedSeconds.value++
    }
  }, 1000)
}

function stopTimer() {
  if (timerInterval) {
    clearInterval(timerInterval)
    timerInterval = null
  }
}

// Start the elapsed timer when workout begins
watch(view, (v) => {
  if (v && v !== 'brief' && v !== 'summary') {
    startTimer()
  }
  if (v === 'summary') {
    stopTimer()
  }
})

// Auto-play coach audio on view changes — stop previous audio first
watch(activeSession, (session, oldSession) => {
  // Stop any playing audio from the previous view
  if (oldSession && oldSession.view !== session?.view) {
    voiceOutput.stop()
  }
  if (session?.coach_says) {
    voiceOutput.speak(session.coach_says, session.audio_url || null)
  }
})

async function handleAction(action, params = {}) {
  if (!sid.value) return
  try {
    await workoutStore.sendAction(sid.value, action, params)
  } catch (err) {
    console.error('Action failed:', err)
  }
}

async function handleEndWorkout() {
  isPaused.value = false
  await handleAction('end_workout')
}

function handleDone() {
  workoutStore.clearSession()
  router.push('/workout')
}

onMounted(async () => {
  // If we have an active session already (navigated from home), nothing to do.
  // Otherwise, load the session from the route param.
  if (!activeSession.value && route.params.sessionId) {
    // Try to start/resume the session
    try {
      await workoutStore.startSession({})
    } catch {
      router.push('/workout')
    }
  }
})

onUnmounted(() => {
  stopTimer()
})
</script>

<style scoped>
.workout-session {
  min-height: 100vh;
  min-height: 100dvh;
  background: var(--bg-page);
  position: relative;
}

.loading-screen {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  min-height: 100dvh;
  gap: 1rem;
  color: var(--text-muted);
}

.spinner {
  width: 32px;
  height: 32px;
  border: 3px solid var(--border-color);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Top bar */
.session-topbar {
  position: fixed;
  top: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 100%;
  max-width: 430px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.65rem 1rem;
  background: rgba(253, 252, 249, 0.92);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--border-color);
  z-index: 20;
}

.topbar-btn {
  background: none;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  padding: 0.25rem;
  display: flex;
  align-items: center;
}

.topbar-timer {
  font-size: 1rem;
  font-weight: 700;
  color: var(--text-primary);
  font-variant-numeric: tabular-nums;
}

.topbar-right {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.mute-btn {
  opacity: 0.7;
}

.topbar-progress {
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--text-muted);
}

/* Pause overlay */
.pause-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}

.pause-card {
  background: var(--bg-card);
  border-radius: var(--radius-lg);
  padding: 2rem 1.5rem;
  text-align: center;
  width: 280px;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.pause-card h2 {
  font-size: 1.25rem;
  font-weight: 800;
  color: var(--text-primary);
}

.pause-card p {
  font-size: 2rem;
  font-weight: 700;
  color: var(--color-primary);
  font-variant-numeric: tabular-nums;
}

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

.btn-outline {
  padding: 0.7rem 1.25rem;
  background: transparent;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  font-weight: 600;
  font-size: 0.9rem;
  cursor: pointer;
  color: var(--text-secondary);
}

.btn-danger {
  color: var(--color-destructive);
  border-color: var(--color-destructive);
}
</style>
