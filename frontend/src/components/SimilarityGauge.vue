<template>
  <div class="gauge-wrap">
    <svg :width="size" :height="size * 0.6" viewBox="0 0 200 120">
      <!-- Background arc -->
      <path
        :d="bgArc"
        fill="none"
        stroke="var(--border-color, #333)"
        stroke-width="14"
        stroke-linecap="round"
      />
      <!-- Score arc -->
      <path
        :d="scoreArc"
        fill="none"
        :stroke="arcColor"
        stroke-width="14"
        stroke-linecap="round"
      />
      <!-- Score text -->
      <text x="100" y="95" text-anchor="middle" :fill="arcColor" font-size="32" font-weight="700">
        {{ Math.round(score) }}
      </text>
      <text x="100" y="112" text-anchor="middle" fill="var(--text-muted, #888)" font-size="11">
        {{ label }}
      </text>
    </svg>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  score: { type: Number, default: 0 },
  label: { type: String, default: 'Score' },
  size: { type: Number, default: 200 },
})

const arcColor = computed(() => {
  const s = props.score
  if (s >= 80) return '#2ecc71'
  if (s >= 50) return '#f1c40f'
  return '#e74c3c'
})

// SVG arc helpers
function polarToCartesian(cx, cy, r, angleDeg) {
  const rad = (angleDeg - 90) * Math.PI / 180
  return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) }
}

function describeArc(cx, cy, r, startAngle, endAngle) {
  const start = polarToCartesian(cx, cy, r, endAngle)
  const end = polarToCartesian(cx, cy, r, startAngle)
  const large = endAngle - startAngle > 180 ? 1 : 0
  return `M ${start.x} ${start.y} A ${r} ${r} 0 ${large} 0 ${end.x} ${end.y}`
}

const bgArc = computed(() => describeArc(100, 80, 60, -90, 90))
const scoreArc = computed(() => {
  const angle = -90 + (Math.min(100, Math.max(0, props.score)) / 100) * 180
  if (props.score <= 0) return ''
  return describeArc(100, 80, 60, -90, angle)
})
</script>

<style scoped>
.gauge-wrap {
  display: flex;
  justify-content: center;
}
</style>
