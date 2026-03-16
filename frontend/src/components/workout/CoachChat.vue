<template>
  <div class="coach-chat" :class="{ compact }">
    <!-- Messages -->
    <div ref="messagesEl" class="chat-messages" @scroll="onScroll">
      <div
        v-for="(msg, i) in messages"
        :key="i"
        class="chat-msg"
        :class="msg.role"
      >
        <!-- Coach bubble -->
        <template v-if="msg.role === 'coach'">
          <div class="msg-avatar-ring">
            <span class="avatar-emoji">🦦</span>
          </div>
          <div class="msg-bubble coach-bubble glass">
            {{ msg.content }}
          </div>
        </template>

        <!-- User bubble -->
        <template v-else>
          <div class="msg-bubble user-bubble">
            {{ msg.content }}
          </div>
        </template>
      </div>

      <!-- Loading indicator -->
      <div v-if="loading" class="chat-msg coach">
        <div class="msg-avatar-ring">
          <span class="avatar-emoji">🦦</span>
        </div>
        <div class="msg-bubble coach-bubble glass typing-bubble">
          <span class="typing-dot" /><span class="typing-dot" /><span class="typing-dot" />
        </div>
      </div>
    </div>

    <!-- Option cards (from latest coach message) -->
    <div v-if="latestOptions.length > 0 && !loading" class="option-strip">
      <button
        v-for="(opt, i) in latestOptions"
        :key="opt.value"
        class="option-card glass"
        @click="handleOptionTap(opt)"
      >
        <span v-if="opt.emoji" class="option-emoji">{{ opt.emoji }}</span>
        {{ opt.label }}
      </button>
    </div>

    <!-- Voice error toast -->
    <div v-if="voiceError" class="voice-error" @click="voiceError = ''">
      {{ voiceError }}
    </div>

    <!-- Input area -->
    <div class="chat-input-area">
      <div class="chat-input-wrap glass">
        <input
          ref="inputEl"
          v-model="inputText"
          class="chat-input"
          :placeholder="compact ? 'Say something...' : 'Type or tap mic...'"
          @keydown.enter.prevent="handleSend"
          :disabled="loading"
        />
        <button
          class="mic-btn"
          :class="{ active: isListening, unsupported: !voiceSupported }"
          @click="toggleMic"
          :disabled="loading"
          :title="!voiceSupported ? 'Mic not supported' : isListening ? 'Stop listening' : 'Speak'"
        >
          <svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
            <template v-if="!voiceSupported">
              <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z" opacity="0.3"/>
              <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z" opacity="0.3"/>
              <line x1="3" y1="3" x2="21" y2="21" stroke="currentColor" stroke-width="2"/>
            </template>
            <template v-else>
              <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z"/>
              <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z"/>
            </template>
          </svg>
        </button>
      </div>
    </div>

    <!-- Voice listening overlay -->
    <div v-if="isListening" class="voice-overlay glass">
      <div class="voice-pulse-ring" />
      <span class="voice-label">Listening...</span>
      <span v-if="voiceTranscript" class="voice-transcript">"{{ voiceTranscript }}"</span>
      <button class="voice-cancel" @click="toggleMic">Cancel</button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, onMounted, watch } from 'vue'
import { useCoachChat } from '../../composables/useCoachChat'
import { useVoiceInput } from '../../composables/useVoiceInput'

const props = defineProps({
  context: { type: String, required: true },
  sessionId: { type: String, default: null },
  initialMessage: { type: String, default: null },
  compact: { type: Boolean, default: false },
})

const emit = defineEmits(['action', 'complete'])

const { messages, loading, sendMessage, sendOption, initChat, lastResponse } = useCoachChat(props.context, props.sessionId)
const voiceInput = useVoiceInput()

const inputEl = ref(null)
const messagesEl = ref(null)
const inputText = ref('')
const voiceSupported = ref(false)
const voiceError = ref('')

const isListening = computed(() => voiceInput.isListening.value)
const voiceTranscript = computed(() => voiceInput.transcript.value)

watch(() => voiceInput.error.value, (err) => {
  if (!err) return
  const silentErrors = ['no-speech', 'aborted']
  if (silentErrors.includes(err)) return
  const errorMessages = {
    'not-allowed': 'Mic permission denied. Check browser settings.',
    'audio-capture': 'No microphone found.',
  }
  const msg = errorMessages[err] ?? `Mic error: ${err}`
  voiceError.value = msg
  setTimeout(() => { voiceError.value = '' }, 4000)
})

const latestOptions = computed(() => {
  for (let i = messages.value.length - 1; i >= 0; i--) {
    if (messages.value[i].role === 'coach' && messages.value[i].options?.length > 0) {
      return messages.value[i].options
    }
  }
  return []
})

watch(() => messages.value.length, async () => {
  await nextTick()
  scrollToBottom()
})

watch(lastResponse, (resp) => {
  if (!resp) return
  if (resp.actions?.length > 0) {
    for (const action of resp.actions) {
      emit('action', action.type, action.params || {})
    }
  }
  if (resp.onboarding_complete) {
    emit('complete', resp.data_collected || {})
  }
})

function scrollToBottom() {
  if (messagesEl.value) {
    messagesEl.value.scrollTop = messagesEl.value.scrollHeight
  }
}

function onScroll() {}

async function handleSend() {
  const text = inputText.value.trim()
  if (!text || loading.value) return
  inputText.value = ''
  await sendMessage(text)
}

async function handleOptionTap(opt) {
  if (loading.value) return
  await sendOption(opt.value, opt.label)
}

function toggleMic() {
  voiceError.value = ''
  if (isListening.value) { voiceInput.stopListening(); return }
  if (loading.value) return
  voiceInput.startListening((text) => {
    if (text) { inputText.value = text; handleSend() }
  }, { continuous: false })
}

async function sendFromParent(text) {
  if (!text || loading.value) return
  inputText.value = text
  await handleSend()
}

defineExpose({ sendFromParent })

onMounted(() => {
  voiceSupported.value = !!(window.SpeechRecognition || window.webkitSpeechRecognition || window.MediaRecorder)
  if (props.initialMessage) {
    messages.value.push({ role: 'coach', content: props.initialMessage, options: [], timestamp: Date.now() })
  } else {
    initChat()
  }
})
</script>

<style scoped>
.coach-chat {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  position: relative;
}

.coach-chat.compact {
  max-height: 280px;
}

/* Messages */
.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 1rem 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.compact .chat-messages {
  padding: 0.5rem;
  gap: 0.5rem;
}

.chat-msg {
  display: flex;
  align-items: flex-start;
  gap: 0.65rem;
  max-width: 85%;
  animation: msgIn 0.3s ease;
}

@keyframes msgIn {
  from { opacity: 0; transform: translateY(6px); }
  to { opacity: 1; transform: translateY(0); }
}

.chat-msg.coach { align-self: flex-start; }
.chat-msg.user { align-self: flex-end; }

.msg-avatar-ring {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: var(--gradient-secondary);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.avatar-emoji {
  font-size: 0.85rem;
}

.compact .msg-avatar-ring {
  width: 22px;
  height: 22px;
}

.compact .avatar-emoji {
  font-size: 0.7rem;
}

.msg-bubble {
  padding: 0.85rem 1rem;
  border-radius: 1rem;
  font-size: 0.875rem;
  line-height: 1.5;
  word-break: break-word;
}

.compact .msg-bubble {
  padding: 0.4rem 0.65rem;
  font-size: 0.8rem;
}

.coach-bubble {
  border-radius: 0 1rem 1rem 1rem;
  color: var(--text-primary);
}

.user-bubble {
  background: var(--color-primary);
  color: var(--text-on-primary);
  border-radius: 1rem 0 1rem 1rem;
}

/* Typing */
.typing-bubble {
  display: flex;
  gap: 0.25rem;
  padding: 0.75rem 1rem;
}

.typing-dot {
  width: 6px;
  height: 6px;
  background: var(--text-muted);
  border-radius: 50%;
  animation: typingBounce 1.4s infinite ease-in-out;
}

.typing-dot:nth-child(2) { animation-delay: 0.2s; }
.typing-dot:nth-child(3) { animation-delay: 0.4s; }

@keyframes typingBounce {
  0%, 80%, 100% { transform: scale(0.7); opacity: 0.4; }
  40% { transform: scale(1); opacity: 1; }
}

/* Option strip */
.option-strip {
  display: flex;
  gap: 0.5rem;
  padding: 0.5rem 1.5rem;
  overflow-x: auto;
  flex-shrink: 0;
  scroll-snap-type: x mandatory;
}

.compact .option-strip {
  padding: 0.3rem 0.5rem;
}

.option-card {
  min-width: 100px;
  padding: 1.25rem 1rem;
  border-radius: 1rem;
  font-size: 0.875rem;
  font-weight: 700;
  cursor: pointer;
  white-space: nowrap;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  color: var(--text-primary);
  scroll-snap-align: start;
  transition: border-color 0.2s, transform 0.15s;
  -webkit-tap-highlight-color: transparent;
}

.option-card:hover {
  border-color: var(--color-primary);
}

.option-card:active {
  transform: scale(0.95);
}

.option-emoji {
  font-size: 1.75rem;
}

.compact .option-card {
  padding: 0.6rem 0.8rem;
  font-size: 0.75rem;
  min-width: 80px;
}

/* Voice error */
.voice-error {
  padding: 0.4rem 0.75rem;
  margin: 0 1.5rem;
  background: var(--color-destructive-light);
  color: var(--color-destructive);
  font-size: 0.78rem;
  border-radius: var(--radius-md);
  text-align: center;
  flex-shrink: 0;
  cursor: pointer;
  animation: msgIn 0.2s ease;
}

/* Input area */
.chat-input-area {
  padding: 0.75rem 1.5rem;
  padding-bottom: calc(0.75rem + env(safe-area-inset-bottom, 0px));
  flex-shrink: 0;
}

.chat-input-wrap {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  border-radius: 1.5rem;
}

.compact .chat-input-area {
  padding: 0.35rem 0.5rem;
}

.chat-input {
  flex: 1;
  background: transparent;
  border: none;
  font-size: 0.875rem;
  color: var(--text-primary);
  outline: none;
}

.chat-input::placeholder {
  color: var(--text-muted);
}

.compact .chat-input {
  font-size: 0.8rem;
}

.mic-btn {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  flex-shrink: 0;
  transition: all 0.2s;
  background: var(--gradient-primary);
  color: var(--text-on-primary);
  box-shadow: 0 0 20px -5px rgba(242, 101, 34, 0.4);
}

.mic-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.mic-btn.unsupported { opacity: 0.3; }

.mic-btn.active {
  background: var(--color-destructive);
  animation: pulse 1.5s infinite;
}

@keyframes pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(220, 38, 38, 0.4); }
  50% { box-shadow: 0 0 0 8px rgba(220, 38, 38, 0); }
}

.compact .mic-btn {
  width: 36px;
  height: 36px;
}

/* Voice overlay */
.voice-overlay {
  position: absolute;
  bottom: 80px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.35rem;
  padding: 0.75rem 1.5rem;
  border-radius: 1rem;
  z-index: 10;
}

.voice-pulse-ring {
  width: 12px;
  height: 12px;
  background: var(--color-primary);
  border-radius: 50%;
  animation: pulse 1.5s infinite;
}

.voice-label {
  font-size: 0.7rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.voice-transcript {
  font-size: 0.8rem;
  color: var(--text-primary);
  font-style: italic;
  max-width: 200px;
  text-align: center;
}

.voice-cancel {
  margin-top: 0.25rem;
  padding: 0.2rem 0.6rem;
  background: transparent;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-full);
  color: var(--text-muted);
  font-size: 0.7rem;
  cursor: pointer;
}
</style>
