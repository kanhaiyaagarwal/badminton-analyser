<template>
  <div class="conv-onboarding">
    <!-- Top bar with skip -->
    <div class="top-bar">
      <div class="top-spacer"></div>
      <button class="skip-btn" @click="handleSkip">Skip →</button>
    </div>

    <!-- Mascot & Title -->
    <div
      v-motion
      :initial="{ opacity: 0, scale: 0.9 }"
      :enter="{ opacity: 1, scale: 1, transition: { duration: 500 } }"
      class="mascot-section"
    >
      <div class="mascot-icon">
        <span class="mascot-emoji">🦦</span>
      </div>
      <h1 class="mascot-title font-display">AI Fitness Coach</h1>
    </div>

    <!-- Chat area -->
    <div class="chat-container">
      <CoachChat
        context="onboarding"
        @complete="handleComplete"
        @action="handleAction"
      />
    </div>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { useWorkoutStore } from '../../stores/workout'
import CoachChat from '../../components/workout/CoachChat.vue'

const router = useRouter()
const workoutStore = useWorkoutStore()

async function handleComplete(collectedData) {
  // Submit the collected onboarding data
  try {
    await workoutStore.submitOnboarding(collectedData)
  } catch {
    // Even if submission fails, navigate forward
  }
  router.push('/hub')
}

function handleAction(type, params) {
  // Handle any actions from the chat (e.g., begin_workout)
  if (type === 'begin_workout') {
    router.push('/hub')
  }
}

function handleSkip() {
  router.push('/hub')
}
</script>

<style scoped>
.conv-onboarding {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

/* Top bar */
.top-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 1.5rem;
  flex-shrink: 0;
}

.top-spacer {
  flex: 1;
}

.skip-btn {
  padding: 0.3rem 0.75rem;
  background: transparent;
  border: none;
  color: var(--text-muted);
  font-size: 0.85rem;
  font-weight: 500;
  cursor: pointer;
  transition: color 0.2s;
}

.skip-btn:hover {
  color: var(--text-primary);
}

/* Mascot */
.mascot-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 0 1.5rem 1.25rem;
  flex-shrink: 0;
}

.mascot-icon {
  width: 80px;
  height: 80px;
  border-radius: 1rem;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 0.75rem;
  background: linear-gradient(135deg, hsl(175 70% 45%), hsl(175 70% 55%));
  box-shadow: 0 0 30px -5px rgba(20, 184, 166, 0.3);
}

.mascot-emoji {
  font-size: 2.5rem;
}

.mascot-title {
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--color-secondary);
}

/* Chat container */
.chat-container {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}
</style>
