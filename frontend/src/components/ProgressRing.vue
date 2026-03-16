<template>
  <div class="progress-ring" :style="{ width: size + 'px', height: size + 'px' }">
    <svg :width="size" :height="size" :viewBox="`0 0 ${size} ${size}`">
      <!-- Background ring -->
      <circle
        :cx="center"
        :cy="center"
        :r="radius"
        fill="none"
        :stroke="trackColor"
        :stroke-width="strokeWidth"
      />
      <!-- Progress ring -->
      <circle
        :cx="center"
        :cy="center"
        :r="radius"
        fill="none"
        :stroke="ringColor"
        :stroke-width="strokeWidth"
        :stroke-dasharray="circumference"
        :stroke-dashoffset="offset"
        stroke-linecap="round"
        class="progress-circle"
        :style="{ '--target-offset': offset + 'px' }"
      />
    </svg>
    <div class="ring-content">
      <span class="ring-value" :style="{ color: ringColor }">{{ value }}</span>
      <span v-if="label" class="ring-label">{{ label }}</span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  progress: { type: Number, default: 0 },
  value: { type: [String, Number], default: '' },
  label: { type: String, default: '' },
  color: { type: String, default: 'primary' },
  size: { type: Number, default: 80 },
  strokeWidth: { type: Number, default: 6 },
})

const center = computed(() => props.size / 2)
const radius = computed(() => (props.size - props.strokeWidth) / 2)
const circumference = computed(() => 2 * Math.PI * radius.value)
const offset = computed(() => circumference.value * (1 - Math.min(props.progress, 1)))

const ringColor = computed(() => {
  const colors = {
    primary: 'hsl(18 95% 55%)',
    secondary: 'hsl(175 70% 45%)',
    accent: 'hsl(175 70% 45%)',
    success: 'hsl(160 60% 45%)',
    warning: 'hsl(45 85% 55%)',
  }
  return colors[props.color] || props.color
})

const trackColor = computed(() => 'rgba(255, 255, 255, 0.08)')
</script>

<style scoped>
.progress-ring {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.progress-ring svg {
  transform: rotate(-90deg);
}

.progress-circle {
  transition: stroke-dashoffset 1s ease-out;
}

.ring-content {
  position: absolute;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.ring-value {
  font-size: 1.1rem;
  font-weight: 800;
  line-height: 1;
  font-family: var(--font-display);
}

.ring-label {
  font-size: 0.55rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin-top: 0.15rem;
}
</style>
