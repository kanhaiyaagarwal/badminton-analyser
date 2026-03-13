<template>
  <div class="summary-phase">
    <div class="summary-content">
      <!-- Celebration -->
      <div class="celebration">
        <div class="check-circle">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="20 6 9 17 4 12"/>
          </svg>
        </div>
        <h1 class="done-title">Workout Complete!</h1>
      </div>

      <!-- Stat cards -->
      <div class="stat-cards">
        <div class="stat-card">
          <span class="stat-value">{{ data.duration_minutes || 0 }}</span>
          <span class="stat-label">Minutes</span>
        </div>
        <div class="stat-card">
          <span class="stat-value">{{ data.exercises_completed || 0 }}</span>
          <span class="stat-label">Exercises</span>
        </div>
        <div class="stat-card">
          <span class="stat-value">{{ data.total_sets || 0 }}</span>
          <span class="stat-label">Sets</span>
        </div>
      </div>

      <!-- Highlights -->
      <div v-if="highlights.length > 0" class="highlights">
        <h3 class="section-title">Highlights</h3>
        <div v-for="(h, i) in highlights" :key="i" class="highlight-row">
          <span class="highlight-icon">*</span>
          <span class="highlight-text">{{ h }}</span>
        </div>
      </div>

      <!-- PRs -->
      <div v-if="prs.length > 0" class="prs-section">
        <h3 class="section-title">Personal Records</h3>
        <div v-for="(pr, i) in prs" :key="i" class="pr-row">
          <span class="pr-badge">PR</span>
          <span class="pr-text">
            {{ pr.exercise }} — {{ pr.value }}{{ pr.type === 'weight' ? 'kg' : ' reps' }}
          </span>
        </div>
      </div>

      <!-- Coach summary -->
      <div v-if="coachSays" class="coach-bubble">
        <img src="/mascot/otter-mascot.png" alt="Coach" class="coach-avatar" />
        <div class="coach-text">{{ coachSays }}</div>
      </div>

      <!-- Streak -->
      <div v-if="data.streak > 0" class="streak-badge">
        {{ data.streak }} day streak
      </div>
    </div>

    <!-- Actions -->
    <div class="summary-actions">
      <button v-if="canShare" class="btn-outline full-width" @click="shareResults">
        Share Results
      </button>
      <button class="btn-primary full-width" @click="$emit('done')">
        Done
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

async function shareResults() {
  if (!navigator.share) return
  try {
    await navigator.share({
      title: 'Workout Complete!',
      text: `Just finished a ${props.data.duration_minutes || 0} minute workout! ${props.data.exercises_completed || 0} exercises, ${props.data.total_sets || 0} sets. ${prs.value.length > 0 ? prs.value.length + ' new PR(s)!' : ''}`,
    })
  } catch {
    // User cancelled share
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
  padding: 2rem 1.25rem;
}

.celebration {
  text-align: center;
  margin-bottom: 1.5rem;
}

.check-circle {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: var(--color-success);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 0.75rem;
}

.check-circle svg {
  width: 32px;
  height: 32px;
}

.done-title {
  font-size: 1.5rem;
  font-weight: 800;
  color: var(--text-primary);
}

.stat-cards {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1.5rem;
}

.stat-card {
  flex: 1;
  padding: 1rem 0.5rem;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  text-align: center;
}

.stat-value {
  display: block;
  font-size: 1.5rem;
  font-weight: 800;
  color: var(--color-primary);
}

.stat-label {
  font-size: 0.65rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.section-title {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 0.5rem;
}

.highlights {
  margin-bottom: 1.25rem;
}

.highlight-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.35rem 0;
}

.highlight-icon {
  color: var(--color-primary);
  font-weight: 700;
}

.highlight-text {
  font-size: 0.9rem;
  color: var(--text-primary);
}

.prs-section {
  margin-bottom: 1.25rem;
}

.pr-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.4rem 0;
}

.pr-badge {
  padding: 0.15rem 0.45rem;
  border-radius: var(--radius-full);
  background: var(--color-warning);
  color: white;
  font-size: 0.65rem;
  font-weight: 700;
}

.pr-text {
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--text-primary);
}

.coach-bubble {
  display: flex;
  align-items: flex-start;
  gap: 0.65rem;
  margin-bottom: 1rem;
}

.coach-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  object-fit: cover;
  flex-shrink: 0;
}

.coach-text {
  padding: 0.65rem 0.85rem;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 0 var(--radius-md) var(--radius-md) var(--radius-md);
  font-size: 0.85rem;
  color: var(--text-secondary);
  line-height: 1.4;
}

.streak-badge {
  text-align: center;
  padding: 0.4rem 1rem;
  border-radius: var(--radius-full);
  background: var(--color-warning-light);
  color: var(--color-warning);
  font-size: 0.85rem;
  font-weight: 600;
  display: inline-block;
}

.summary-actions {
  padding: 1rem 1.25rem;
  padding-bottom: calc(1.5rem + env(safe-area-inset-bottom, 0px));
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
