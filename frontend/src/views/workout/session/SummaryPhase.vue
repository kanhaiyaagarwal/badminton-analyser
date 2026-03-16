<template>
  <div class="summary-phase">
    <div class="summary-content">
      <!-- Celebration header -->
      <div
        v-motion
        :initial="{ opacity: 0, scale: 0.9 }"
        :enter="{ opacity: 1, scale: 1, transition: { duration: 600 } }"
        class="celebration"
      >
        <div
          v-motion
          :initial="{ scale: 0 }"
          :enter="{ scale: 1, transition: { delay: 200, type: 'spring', stiffness: 200, damping: 12 } }"
          class="check-icon"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" width="32" height="32">
            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
            <polyline points="22 4 12 14.01 9 11.01"/>
          </svg>
        </div>
        <h1 class="done-title font-display">Workout Complete!</h1>
        <p class="done-subtitle">Amazing effort today 💪</p>
      </div>

      <!-- Stat cards -->
      <div class="stat-cards">
        <div
          v-for="(stat, i) in statCards"
          :key="stat.label"
          v-motion
          :initial="{ opacity: 0, scale: 0.9 }"
          :enter="{ opacity: 1, scale: 1, transition: { delay: 400 + i * 100 } }"
          class="stat-card glass"
        >
          <span class="stat-value" :class="stat.colorClass">{{ stat.value }}</span>
          <span class="stat-label">{{ stat.label }}</span>
        </div>
      </div>

      <!-- Highlights -->
      <div
        v-if="allHighlights.length > 0"
        v-motion
        :initial="{ opacity: 0, y: 20 }"
        :enter="{ opacity: 1, y: 0, transition: { delay: 500 } }"
      >
        <h2 class="section-label">Highlights</h2>
        <div class="highlights-card glass">
          <div v-for="(h, i) in allHighlights" :key="i" class="highlight-row">
            <span class="highlight-emoji">{{ h.icon }}</span>
            <p class="highlight-text">{{ h.text }}</p>
          </div>
        </div>
      </div>

      <!-- Streak badge -->
      <div
        v-if="data.streak > 0"
        v-motion
        :initial="{ opacity: 0, scale: 0.9 }"
        :enter="{ opacity: 1, scale: 1, transition: { delay: 600 } }"
        class="streak-card"
      >
        <div class="streak-icon-circle">
          <svg viewBox="0 0 24 24" fill="currentColor" width="24" height="24">
            <path d="M12 23c-3.6 0-7-2.5-7-7 0-3.2 2-5.5 3.8-7.5C10.5 6.5 12 4.6 12 2c0 4 4.5 6 6.2 9.2C19.7 13.8 20 16 20 16c0 4.5-3.9 7-8 7z"/>
          </svg>
        </div>
        <div class="streak-info">
          <h3 class="streak-title font-display">{{ data.streak }} day streak!</h3>
          <p class="streak-sub">Keep it going tomorrow</p>
        </div>
      </div>

      <!-- Coach summary -->
      <div
        v-if="coachSays"
        v-motion
        :initial="{ opacity: 0, y: 20 }"
        :enter="{ opacity: 1, y: 0, transition: { delay: 700 } }"
        class="coach-bubble glass"
      >
        <div class="coach-bubble-inner">
          <div class="coach-avatar-ring">
            <span class="coach-emoji">🦦</span>
          </div>
          <p class="coach-text">"{{ coachSays }}"</p>
        </div>
      </div>
    </div>

    <!-- Actions -->
    <div class="summary-actions">
      <button
        v-motion
        :initial="{ opacity: 0, y: 20 }"
        :enter="{ opacity: 1, y: 0, transition: { delay: 800 } }"
        class="btn-done"
        @click="$emit('done')"
      >
        Done →
      </button>
      <button
        v-if="canShare"
        v-motion
        :initial="{ opacity: 0, y: 20 }"
        :enter="{ opacity: 1, y: 0, transition: { delay: 900 } }"
        class="btn-share glass"
        @click="shareResults"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="16" height="16">
          <circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/>
          <line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/>
        </svg>
        Share Results
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

defineEmits(['action', 'done'])

const highlights = computed(() => props.data.highlights || [])
const prs = computed(() => props.data.prs || [])
const canShare = computed(() => !!navigator.share)

const statCards = computed(() => [
  { value: props.data.duration_minutes || 0, label: 'Minutes', colorClass: 'gradient-primary' },
  { value: props.data.exercises_completed || 0, label: 'Exercises', colorClass: 'gradient-secondary' },
  { value: props.data.total_sets || 0, label: 'Sets', colorClass: 'gradient-accent' },
])

const allHighlights = computed(() => {
  const items = []
  for (const pr of prs.value) {
    items.push({ icon: '🏆', text: `New PR: ${pr.exercise} ${pr.value}${pr.type === 'weight' ? 'kg' : ' reps'}` })
  }
  for (const h of highlights.value) {
    // Try to pick a relevant emoji
    if (h.toLowerCase().includes('complete')) items.push({ icon: '✓', text: h })
    else if (h.toLowerCase().includes('volume')) items.push({ icon: '💪', text: h })
    else items.push({ icon: '⭐', text: h })
  }
  if (items.length === 0 && (props.data.total_volume_kg > 0)) {
    items.push({ icon: '💪', text: `Total volume: ${props.data.total_volume_kg}kg` })
  }
  return items
})

async function shareResults() {
  if (!navigator.share) return
  try {
    await navigator.share({
      title: 'Workout Complete!',
      text: `Just finished a ${props.data.duration_minutes || 0} minute workout! ${props.data.exercises_completed || 0} exercises, ${props.data.total_sets || 0} sets. ${prs.value.length > 0 ? prs.value.length + ' new PR(s)!' : ''}`,
    })
  } catch {
    // User cancelled
  }
}
</script>

<style scoped>
.summary-phase {
  min-height: 100vh;
  min-height: 100dvh;
  display: flex;
  flex-direction: column;
}

.summary-content {
  flex: 1;
  padding: 3rem 1.5rem 1rem;
}

/* Celebration */
.celebration {
  text-align: center;
  margin-bottom: 2rem;
}

.check-icon {
  width: 64px;
  height: 64px;
  margin: 0 auto 1rem;
  color: var(--color-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  filter: drop-shadow(0 0 30px rgba(242, 101, 34, 0.3));
}

.done-title {
  font-size: 1.75rem;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 0.35rem;
}

.done-subtitle {
  color: var(--text-muted);
  font-size: 0.9rem;
}

/* Stat cards */
.stat-cards {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.75rem;
  margin-bottom: 1.5rem;
}

.stat-card {
  padding: 1rem 0.5rem;
  border-radius: 1rem;
  text-align: center;
}

.stat-value {
  display: block;
  font-family: var(--font-display);
  font-size: 1.75rem;
  font-weight: 900;
  margin-bottom: 0.15rem;
  background-clip: text;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.stat-value.gradient-primary {
  background-image: linear-gradient(135deg, hsl(18 95% 55%), hsl(18 95% 65%));
}

.stat-value.gradient-secondary {
  background-image: linear-gradient(135deg, hsl(175 70% 45%), hsl(175 70% 55%));
}

.stat-value.gradient-accent {
  background-image: linear-gradient(135deg, hsl(175 70% 45%), hsl(175 70% 55%));
}

.stat-label {
  font-size: 0.65rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

/* Section label */
.section-label {
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--text-muted);
  margin-bottom: 0.75rem;
}

/* Highlights */
.highlights-card {
  padding: 1.25rem;
  border-radius: 1rem;
  margin-bottom: 1.5rem;
}

.highlight-row {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  padding: 0.35rem 0;
}

.highlight-row + .highlight-row {
  margin-top: 0.35rem;
}

.highlight-emoji {
  font-size: 1.15rem;
  flex-shrink: 0;
}

.highlight-text {
  font-size: 0.875rem;
  color: var(--text-primary);
  line-height: 1.4;
}

/* Streak card */
.streak-card {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1.25rem;
  border-radius: 1rem;
  margin-bottom: 1.5rem;
  background: linear-gradient(135deg, rgba(242, 101, 34, 0.1), rgba(242, 101, 34, 0.03));
  border: 1px solid rgba(242, 101, 34, 0.3);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
}

.streak-icon-circle {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: var(--gradient-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-on-primary);
  flex-shrink: 0;
}

.streak-title {
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--text-primary);
}

.streak-sub {
  font-size: 0.8rem;
  color: var(--text-muted);
  margin-top: 0.1rem;
}

/* Coach bubble */
.coach-bubble {
  padding: 1rem;
  border-radius: 1rem;
  margin-bottom: 1.5rem;
}

.coach-bubble-inner {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
}

.coach-avatar-ring {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: var(--gradient-secondary);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.coach-emoji {
  font-size: 1.15rem;
}

.coach-text {
  font-size: 0.875rem;
  color: var(--text-primary);
  opacity: 0.9;
  font-style: italic;
  line-height: 1.6;
  flex: 1;
}

/* Actions */
.summary-actions {
  padding: 1rem 1.5rem;
  padding-bottom: calc(1.5rem + env(safe-area-inset-bottom, 0px));
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.btn-done {
  width: 100%;
  padding: 1rem;
  border: none;
  border-radius: 0.75rem;
  background: var(--gradient-primary);
  color: var(--text-on-primary);
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 1rem;
  cursor: pointer;
  box-shadow: var(--glow-primary);
  transition: transform 0.15s;
}

.btn-done:active {
  transform: scale(0.98);
}

.btn-share {
  width: 100%;
  padding: 1rem;
  border-radius: 0.75rem;
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 1rem;
  cursor: pointer;
  color: var(--text-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  transition: transform 0.15s;
}

.btn-share:active {
  transform: scale(0.98);
}
</style>
