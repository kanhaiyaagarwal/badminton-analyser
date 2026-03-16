<template>
  <div class="rest-timer">
    <div class="rest-content">
      <!-- Feedback from last set -->
      <div v-if="data.feedback" class="feedback-badge">
        {{ data.feedback }}
      </div>

      <h2 class="rest-label">Rest</h2>

      <!-- Circular countdown -->
      <div class="countdown-wrap">
        <svg class="countdown-svg" viewBox="0 0 120 120">
          <circle class="countdown-bg" cx="60" cy="60" r="54" />
          <circle
            class="countdown-ring"
            cx="60" cy="60" r="54"
            :stroke-dasharray="circumference"
            :stroke-dashoffset="dashOffset"
          />
        </svg>
        <div class="countdown-text">
          <span class="countdown-number">{{ remaining }}</span>
          <span class="countdown-unit">sec</span>
        </div>
      </div>

      <!-- Next set preview -->
      <div v-if="nextSet" class="next-preview">
        <span class="next-label">Next Up</span>
        <span class="next-info">{{ nextSet.name }} — Set {{ nextSet.set_number }}/{{ nextSet.sets_total }}</span>
      </div>

      <!-- Post-set quick feedback -->
      <div class="feedback-cards">
        <button
          v-for="opt in feedbackOptions"
          :key="opt.value"
          class="feedback-card"
          :class="{ selected: selectedFeedback === opt.value }"
          @click="handleFeedback(opt)"
        >
          {{ opt.label }}
        </button>
      </div>

      <!-- Mini coach chat (for conversational rest) -->
      <div v-if="showChat" class="rest-chat">
        <CoachChat
          context="rest"
          :session-id="sessionId"
          compact
          @action="handleChatAction"
        />
      </div>

      <!-- Coach tip (fallback when chat not shown) -->
      <div v-else-if="coachSays" class="coach-bubble">
        <img src="/mascot/otter-mascot.png" alt="Coach" class="coach-avatar" />
        <div class="coach-text">{{ coachSays }}</div>
      </div>

      <!-- Voice listening indicator -->
      <div v-if="voiceInput.isListening.value" class="voice-indicator">
        <div class="voice-pulse"></div>
        <span class="voice-text">Listening...</span>
        <span v-if="voiceInput.transcript.value" class="voice-transcript">"{{ voiceInput.transcript.value }}"</span>
      </div>
    </div>

    <!-- Actions -->
    <div class="rest-actions">
      <button class="btn-primary full-width" @click="skipRest">
        Skip Rest
      </button>
      <button class="btn-outline full-width chat-toggle-btn" @click="showChat = !showChat">
        {{ showChat ? 'Hide Chat' : 'Talk to Coach' }}
      </button>
      <button class="btn-outline full-width mic-btn" @click="toggleVoice" v-if="voiceSupported && !showChat">
        {{ voiceInput.isListening.value ? 'Stop Listening' : 'Voice Command' }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useVoiceInput } from '@/composables/useVoiceInput'
import CoachChat from '../../../components/workout/CoachChat.vue'

const props = defineProps({
  data: { type: Object, required: true },
  coachSays: { type: String, default: '' },
  progress: { type: Object, default: null },
  sessionId: { type: String, default: null },
})

const emit = defineEmits(['action'])

// Voice input
const voiceInput = useVoiceInput()
const voiceSupported = ref(false)
const showChat = ref(false)
const selectedFeedback = ref(null)

const feedbackOptions = [
  { label: 'Felt easy', value: 'easy' },
  { label: 'Just right', value: 'just_right' },
  { label: 'Really hard', value: 'hard' },
]

function handleFeedback(opt) {
  selectedFeedback.value = opt.value
  emit('action', 'report_feedback', { feeling: opt.value })
}

function handleChatAction(type, params) {
  emit('action', type, params)
}

onMounted(() => {
  voiceSupported.value = !!(window.SpeechRecognition || window.webkitSpeechRecognition)
})

const totalSeconds = computed(() => props.data.rest_duration_sec || 90)
const remaining = ref(totalSeconds.value)
const nextSet = computed(() => props.data.next_set || null)

const circumference = 2 * Math.PI * 54
const dashOffset = computed(() => {
  const pct = remaining.value / totalSeconds.value
  return circumference * (1 - pct)
})

let interval = null

onMounted(() => {
  remaining.value = totalSeconds.value
  interval = setInterval(() => {
    remaining.value--
    if (remaining.value <= 0) {
      clearInterval(interval)
      interval = null
      // Vibrate if available
      if (navigator.vibrate) navigator.vibrate([200, 100, 200])
      // Auto-advance to next set
      skipRest()
    }
  }, 1000)
})

onUnmounted(() => {
  if (interval) clearInterval(interval)
})

function skipRest() {
  if (interval) clearInterval(interval)
  voiceInput.stopListening()
  if (nextSet.value) {
    emit('action', 'skip_rest', {
      exercise_id: nextSet.value.exercise_id,
      set_number: nextSet.value.set_number,
    })
  }
}

function toggleVoice() {
  if (voiceInput.isListening.value) {
    voiceInput.stopListening()
  } else {
    voiceInput.startListening(handleVoiceCommand, { continuous: true })
  }
}

function handleVoiceCommand(text) {
  const lower = text.toLowerCase().trim()
  if (lower.includes('skip') || lower.includes('next') || lower.includes('go')) {
    skipRest()
  }
  // Other commands are handled by the parent via the action system
}
</script>

<style scoped>
.rest-timer {
  min-height: 100vh;
  min-height: 100dvh;
  display: flex;
  flex-direction: column;
  padding-top: 3.5rem;
}

.rest-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 1.5rem 1.25rem;
  text-align: center;
}

.feedback-badge {
  padding: 0.5rem 1rem;
  background: var(--color-primary-light);
  color: var(--color-primary);
  border-radius: var(--radius-full);
  font-size: 0.8rem;
  font-weight: 600;
  margin-bottom: 1rem;
  max-width: 300px;
  line-height: 1.3;
}

.rest-label {
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.1em;
  margin-bottom: 1rem;
}

.countdown-wrap {
  position: relative;
  width: 180px;
  height: 180px;
  margin-bottom: 1.5rem;
}

.countdown-svg {
  width: 100%;
  height: 100%;
  transform: rotate(-90deg);
}

.countdown-bg {
  fill: none;
  stroke: var(--border-color);
  stroke-width: 6;
}

.countdown-ring {
  fill: none;
  stroke: var(--color-primary);
  stroke-width: 6;
  stroke-linecap: round;
  transition: stroke-dashoffset 1s linear;
}

.countdown-text {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.countdown-number {
  font-size: 3rem;
  font-weight: 800;
  color: var(--text-primary);
  line-height: 1;
  font-variant-numeric: tabular-nums;
}

.countdown-unit {
  font-size: 0.8rem;
  color: var(--text-muted);
}

.next-preview {
  margin-bottom: 1rem;
}

.next-label {
  display: block;
  font-size: 0.7rem;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 0.15rem;
}

.next-info {
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--text-primary);
}

.coach-bubble {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  max-width: 300px;
}

.coach-avatar {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  object-fit: cover;
  flex-shrink: 0;
}

.coach-text {
  padding: 0.5rem 0.65rem;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 0 var(--radius-md) var(--radius-md) var(--radius-md);
  font-size: 0.75rem;
  color: var(--text-secondary);
  line-height: 1.4;
  text-align: left;
}

.rest-actions {
  padding: 1rem 1.25rem;
  padding-bottom: calc(1rem + env(safe-area-inset-bottom, 0px));
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

.full-width { width: 100%; }

/* Voice */
.voice-indicator {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.35rem;
  margin-top: 1rem;
}

.voice-pulse {
  width: 16px;
  height: 16px;
  background: var(--color-primary);
  border-radius: 50%;
  animation: pulse 1.5s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(1.3); }
}

.voice-text {
  font-size: 0.7rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.voice-transcript {
  font-size: 0.8rem;
  color: var(--text-primary);
  font-style: italic;
}

/* Feedback cards */
.feedback-cards {
  display: flex;
  gap: 0.4rem;
  margin-bottom: 1rem;
  flex-wrap: wrap;
  justify-content: center;
}

.feedback-card {
  padding: 0.5rem 1rem;
  border-radius: var(--radius-full);
  border: 1.5px solid var(--border-color);
  background: var(--bg-card);
  color: var(--text-secondary);
  font-size: 0.8rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.feedback-card:hover, .feedback-card:active {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.feedback-card.selected {
  border-color: var(--color-primary);
  background: var(--color-primary);
  color: white;
}

/* Rest chat */
.rest-chat {
  width: 100%;
  max-width: 350px;
  max-height: 200px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  overflow: hidden;
  margin-top: 0.5rem;
}

.chat-toggle-btn {
  margin-top: 0.5rem;
}

.mic-btn {
  margin-top: 0.5rem;
}

.btn-outline {
  padding: 0.65rem 1rem;
  background: transparent;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  font-weight: 600;
  font-size: 0.85rem;
  cursor: pointer;
  color: var(--text-secondary);
}
</style>
