<template>
  <div class="live-stats">
    <div class="stats-header">
      <h3>Live Statistics</h3>
    </div>

    <!-- Last Shot Detected - Fixed Section -->
    <div class="last-shot-section">
      <div class="section-label">Last Shot Detected</div>
      <div v-if="stats.lastShotType" class="shot-detected">
        <span :class="['shot-type-badge', stats.lastShotType]">
          {{ formatShotType(stats.lastShotType) }}
        </span>
        <span class="confidence-badge">
          {{ (stats.lastShotConfidence * 100).toFixed(0) }}% confidence
        </span>
      </div>
      <div v-else class="no-shot">
        <span class="waiting-text">Waiting for shot detection...</span>
      </div>
    </div>

    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-value">{{ stats.totalShots }}</div>
        <div class="stat-label">Total Shots</div>
      </div>

      <div class="stat-card">
        <div class="stat-value">{{ stats.currentRally }}</div>
        <div class="stat-label">Current Rally</div>
      </div>

      <div class="stat-card">
        <div class="stat-value">{{ (stats.detectionRate * 100).toFixed(0) }}%</div>
        <div class="stat-label">Detection Rate</div>
      </div>

      <div class="stat-card">
        <div class="stat-value">{{ stats.framesProcessed }}</div>
        <div class="stat-label">Frames</div>
      </div>
    </div>

    <div class="shot-distribution">
      <h4>Shot Distribution</h4>
      <div v-if="hasShots" class="distribution-bars">
        <div
          v-for="(count, shotType) in stats.shotDistribution"
          :key="shotType"
          class="shot-bar"
        >
          <div class="bar-label">{{ formatShotType(shotType) }}</div>
          <div class="bar-container">
            <div
              :class="['bar-fill', shotType]"
              :style="{ width: getBarWidth(count) + '%' }"
            ></div>
          </div>
          <div class="bar-count">{{ count }}</div>
        </div>
      </div>
      <div v-else class="no-distribution">
        <span>No shots recorded yet</span>
      </div>
    </div>

    <!-- Coaching Tip - Fixed Section -->
    <div class="coaching-section">
      <div class="section-label">
        <svg class="tip-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"/>
        </svg>
        Coaching Tip
      </div>
      <div class="coaching-content">
        <span v-if="stats.coachingTip" class="tip-text">{{ stats.coachingTip }}</span>
        <span v-else class="no-tip">Tips will appear based on your shots</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  stats: {
    type: Object,
    default: () => ({
      totalShots: 0,
      currentRally: 0,
      shotDistribution: {},
      lastShotType: null,
      lastShotConfidence: 0,
      framesProcessed: 0,
      detectionRate: 0,
      coachingTip: ''
    })
  }
})

const maxShots = computed(() => {
  const values = Object.values(props.stats.shotDistribution || {})
  return Math.max(...values, 1)
})

const hasShots = computed(() => {
  return Object.keys(props.stats.shotDistribution || {}).length > 0
})

function getBarWidth(count) {
  return (count / maxShots.value) * 100
}

function formatShotType(type) {
  if (!type) return ''
  return type.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}
</script>

<style scoped>
.live-stats {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 1.5rem;
}

.stats-header {
  margin-bottom: 1rem;
}

.stats-header h3 {
  margin: 0;
  color: var(--text-primary);
  font-size: 1.1rem;
}

/* Last Shot Section - Fixed Height */
.last-shot-section {
  background: var(--bg-input);
  border-radius: var(--radius-md);
  padding: 1rem;
  margin-bottom: 1rem;
  min-height: 70px;
}

.section-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: var(--text-muted);
  font-size: 0.8rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 0.5rem;
}

.shot-detected {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.shot-type-badge {
  font-weight: 600;
  padding: 0.5rem 1rem;
  border-radius: var(--radius-sm);
  font-size: 1.1rem;
}

.shot-type-badge.smash { color: var(--color-destructive); background: var(--color-destructive-light); }
.shot-type-badge.clear { color: var(--color-success); background: rgba(46, 204, 113, 0.2); }
.shot-type-badge.drop_shot { color: var(--color-warning); background: rgba(243, 156, 18, 0.2); }
.shot-type-badge.net_shot { color: var(--color-info); background: rgba(52, 152, 219, 0.2); }
.shot-type-badge.drive { color: var(--color-secondary); background: rgba(155, 89, 182, 0.2); }
.shot-type-badge.lift { color: #1abc9c; background: rgba(26, 188, 156, 0.2); }
.shot-type-badge.serve { color: #e67e22; background: rgba(230, 126, 34, 0.2); }

.confidence-badge {
  color: var(--color-primary);
  font-size: 0.9rem;
  padding: 0.25rem 0.5rem;
  background: var(--color-primary-light);
  border-radius: 4px;
}

.no-shot {
  display: flex;
  align-items: center;
  min-height: 36px;
}

.waiting-text {
  color: var(--text-muted);
  font-style: italic;
  font-size: 0.9rem;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 0.75rem;
  margin-bottom: 1.5rem;
}

.stat-card {
  text-align: center;
  padding: 0.75rem;
  background: var(--bg-input);
  border-radius: var(--radius-md);
}

.stat-value {
  font-size: 1.5rem;
  font-weight: bold;
  color: var(--color-primary);
}

.stat-label {
  font-size: 0.75rem;
  color: var(--text-muted);
  margin-top: 0.25rem;
}

.shot-distribution {
  margin-bottom: 1rem;
}

.shot-distribution h4 {
  margin: 0 0 0.75rem 0;
  color: var(--text-muted);
  font-size: 0.9rem;
  font-weight: normal;
}

.distribution-bars {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.no-distribution {
  padding: 1rem;
  text-align: center;
  color: var(--text-muted);
  font-style: italic;
  font-size: 0.85rem;
  background: var(--bg-input);
  border-radius: var(--radius-md);
}

.shot-bar {
  display: grid;
  grid-template-columns: 80px 1fr 40px;
  align-items: center;
  gap: 0.5rem;
}

.bar-label {
  color: var(--text-muted);
  font-size: 0.8rem;
  text-align: right;
}

.bar-container {
  height: 16px;
  background: var(--bg-input);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  border-radius: var(--radius-md);
  transition: width 0.3s ease;
}

.bar-fill.smash { background: var(--color-destructive); }
.bar-fill.clear { background: var(--color-success); }
.bar-fill.drop_shot { background: var(--color-warning); }
.bar-fill.net_shot { background: var(--color-info); }
.bar-fill.drive { background: var(--color-secondary); }
.bar-fill.lift { background: #1abc9c; }
.bar-fill.serve { background: #e67e22; }

.bar-count {
  color: var(--text-primary);
  font-size: 0.85rem;
  font-weight: bold;
}

/* Coaching Section - Fixed Height */
.coaching-section {
  background: var(--bg-input);
  border-radius: var(--radius-md);
  padding: 1rem;
  min-height: 80px;
  border-left: 3px solid var(--color-primary);
}

.coaching-section .section-label {
  color: var(--color-primary);
}

.tip-icon {
  width: 16px;
  height: 16px;
}

.coaching-content {
  min-height: 24px;
  display: flex;
  align-items: center;
}

.tip-text {
  color: var(--text-primary);
  font-size: 0.9rem;
  line-height: 1.4;
}

.no-tip {
  color: var(--text-muted);
  font-style: italic;
  font-size: 0.85rem;
}
</style>
