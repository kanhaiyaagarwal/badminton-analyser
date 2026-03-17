<template>
  <div class="pre-workout">
    <!-- Exercise plan (top, scrollable) -->
    <div class="plan-section">
      <h2 class="plan-title">{{ data.day_label || "Today's Workout" }}</h2>
      <div class="exercise-list">
        <div
          v-for="(ex, i) in exercises"
          :key="ex.slug || i"
          class="exercise-item"
        >
          <span class="exercise-num">{{ i + 1 }}</span>
          <div class="exercise-info">
            <span class="exercise-name">{{ ex.name }}</span>
            <span class="exercise-detail">{{ ex.sets }}x{{ ex.reps }}{{ ex.weight_kg ? ` @ ${ex.weight_kg}kg` : '' }}</span>
          </div>
        </div>
      </div>
      <div class="plan-meta">
        <span>{{ exercises.length }} exercises</span>
        <span>~{{ data.estimated_minutes || 45 }} min</span>
      </div>
    </div>

    <!-- Chat area (bottom) -->
    <div class="chat-section">
      <CoachChat
        ref="chatRef"
        context="pre_workout"
        :session-id="sessionId"
        :initial-message="coachSays || null"
        compact
        @action="handleChatAction"
      />
    </div>

    <!-- Quick actions + Begin button -->
    <div class="pre-workout-actions">
      <div class="quick-buttons">
        <button class="quick-btn" @click="sendQuickAction('swap_exercise')">Swap exercise</button>
        <button class="quick-btn" @click="sendQuickAction('make_shorter')">Make it shorter</button>
      </div>
      <button class="btn-primary full-width begin-btn" @click="handleBegin">
        Begin Workout
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import CoachChat from '../../../components/workout/CoachChat.vue'
import { useCoachChat } from '../../../composables/useCoachChat'

const props = defineProps({
  data: { type: Object, required: true },
  coachSays: { type: String, default: '' },
  sessionId: { type: String, default: null },
})

const emit = defineEmits(['action'])

const exercises = computed(() => props.data.exercises || [])

const chatRef = ref(null)

function handleChatAction(type, params) {
  if (type === 'begin_workout') {
    handleBegin()
    return
  }
  // Forward other actions to parent (e.g., swap_exercise, adjust_next_set)
  emit('action', type, params)
}

function handleBegin() {
  emit('action', 'begin_workout')
}

function sendQuickAction(action) {
  // Route through chat — these are conversational requests, not session agent actions
  const messages = {
    swap_exercise: "I'd like to swap an exercise",
    make_shorter: "Can you make the workout shorter?",
  }
  const msg = messages[action] || action
  // Send via the chat component's exposed method
  if (chatRef.value) {
    chatRef.value.sendFromParent(msg)
  }
}
</script>

<style scoped>
.pre-workout {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  min-height: 100dvh;
  padding-top: 0.5rem;
}

/* Plan section */
.plan-section {
  padding: 1rem 1.25rem;
  flex-shrink: 0;
}

.plan-title {
  font-size: 1.2rem;
  font-weight: 800;
  color: var(--text-primary);
  margin-bottom: 0.75rem;
}

.exercise-list {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  margin-bottom: 0.5rem;
}

.exercise-item {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  padding: 0.6rem 0.75rem;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
}

.exercise-num {
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

.exercise-info {
  display: flex;
  flex-direction: column;
}

.exercise-name {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--text-primary);
}

.exercise-detail {
  font-size: 0.7rem;
  color: var(--text-muted);
}

.plan-meta {
  display: flex;
  justify-content: space-between;
  font-size: 0.75rem;
  color: var(--text-muted);
}

/* Chat section */
.chat-section {
  flex: 1;
  min-height: 200px;
  border-top: 1px solid var(--border-color);
}

/* Actions */
.pre-workout-actions {
  padding: 0.75rem 1.25rem;
  padding-bottom: calc(0.75rem + env(safe-area-inset-bottom, 0px));
  border-top: 1px solid var(--border-color);
  background: var(--bg-card);
}

.quick-buttons {
  display: flex;
  gap: 0.4rem;
  margin-bottom: 0.5rem;
}

.quick-btn {
  flex: 1;
  padding: 0.45rem 0.5rem;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-full);
  background: transparent;
  color: var(--text-secondary);
  font-size: 0.75rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.quick-btn:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.begin-btn {
  padding: 0.85rem;
}

.btn-primary {
  display: block;
  width: 100%;
  padding: 0.85rem 1.25rem;
  background: var(--gradient-primary);
  color: white;
  border: none;
  border-radius: var(--radius-md);
  font-weight: 600;
  font-size: 1rem;
  cursor: pointer;
  transition: opacity 0.2s;
}

.btn-primary:hover { opacity: 0.9; }
.full-width { width: 100%; }
</style>
