<template>
  <div class="cooldown-phase">
    <div class="cooldown-content">
      <h1 class="cooldown-title">Cool Down</h1>
      <p class="cooldown-desc">Take a moment to stretch. Your muscles will thank you.</p>

      <div v-if="stretches.length > 0" class="stretch-list">
        <div v-for="(s, i) in stretches" :key="i" class="stretch-item">
          <span class="stretch-num">{{ i + 1 }}</span>
          <span class="stretch-text">{{ s }}</span>
        </div>
      </div>

      <div v-if="coachSays" class="coach-bubble">
        <img src="/mascot/otter-mascot.png" alt="Coach" class="coach-avatar" />
        <div class="coach-text">{{ coachSays }}</div>
      </div>
    </div>

    <div class="cooldown-actions">
      <button class="btn-primary full-width" @click="$emit('action', 'end_workout')">
        Finish Workout
      </button>
      <button class="btn-outline full-width" @click="$emit('action', 'end_workout')">
        Skip Cool Down
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  data: { type: Object, required: true },
  coachSays: { type: String, default: '' },
})

defineEmits(['action'])

const stretches = computed(() => props.data.stretches || [])
</script>

<style scoped>
.cooldown-phase {
  min-height: 100vh;
  min-height: 100dvh;
  display: flex;
  flex-direction: column;
  padding-top: 3.5rem;
}

.cooldown-content {
  flex: 1;
  padding: 2rem 1.25rem;
}

.cooldown-title {
  font-size: 1.75rem;
  font-weight: 800;
  color: var(--text-primary);
  margin-bottom: 0.35rem;
}

.cooldown-desc {
  font-size: 0.9rem;
  color: var(--text-muted);
  margin-bottom: 1.5rem;
}

.stretch-list {
  margin-bottom: 1.5rem;
}

.stretch-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 0;
  border-bottom: 1px solid var(--border-color);
}

.stretch-num {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: var(--color-primary-light);
  color: var(--color-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.75rem;
  font-weight: 700;
  flex-shrink: 0;
}

.stretch-text {
  font-size: 0.9rem;
  color: var(--text-primary);
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

.cooldown-actions {
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
</style>
