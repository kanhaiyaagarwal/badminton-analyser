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
  background: #16213e;
  border-radius: 12px;
  padding: 1.5rem;
}

.stats-header {
  margin-bottom: 1rem;
}

.stats-header h3 {
  margin: 0;
  color: #eee;
  font-size: 1.1rem;
}

/* Last Shot Section - Fixed Height */
.last-shot-section {
  background: #0f0f1a;
  border-radius: 8px;
  padding: 1rem;
  margin-bottom: 1rem;
  min-height: 70px;
}

.section-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: #888;
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
  font-weight: bold;
  padding: 0.5rem 1rem;
  border-radius: 6px;
  font-size: 1.1rem;
}

.shot-type-badge.smash { color: #e74c3c; background: rgba(231, 76, 60, 0.2); }
.shot-type-badge.clear { color: #2ecc71; background: rgba(46, 204, 113, 0.2); }
.shot-type-badge.drop_shot { color: #f39c12; background: rgba(243, 156, 18, 0.2); }
.shot-type-badge.net_shot { color: #3498db; background: rgba(52, 152, 219, 0.2); }
.shot-type-badge.drive { color: #9b59b6; background: rgba(155, 89, 182, 0.2); }
.shot-type-badge.lift { color: #1abc9c; background: rgba(26, 188, 156, 0.2); }
.shot-type-badge.serve { color: #e67e22; background: rgba(230, 126, 34, 0.2); }

.confidence-badge {
  color: #4ecca3;
  font-size: 0.9rem;
  padding: 0.25rem 0.5rem;
  background: rgba(78, 204, 163, 0.1);
  border-radius: 4px;
}

.no-shot {
  display: flex;
  align-items: center;
  min-height: 36px;
}

.waiting-text {
  color: #555;
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
  background: #0f0f1a;
  border-radius: 8px;
}

.stat-value {
  font-size: 1.5rem;
  font-weight: bold;
  color: #4ecca3;
}

.stat-label {
  font-size: 0.75rem;
  color: #888;
  margin-top: 0.25rem;
}

.shot-distribution {
  margin-bottom: 1rem;
}

.shot-distribution h4 {
  margin: 0 0 0.75rem 0;
  color: #888;
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
  color: #555;
  font-style: italic;
  font-size: 0.85rem;
  background: #0f0f1a;
  border-radius: 8px;
}

.shot-bar {
  display: grid;
  grid-template-columns: 80px 1fr 40px;
  align-items: center;
  gap: 0.5rem;
}

.bar-label {
  color: #888;
  font-size: 0.8rem;
  text-align: right;
}

.bar-container {
  height: 16px;
  background: #0f0f1a;
  border-radius: 8px;
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  border-radius: 8px;
  transition: width 0.3s ease;
}

.bar-fill.smash { background: #e74c3c; }
.bar-fill.clear { background: #2ecc71; }
.bar-fill.drop_shot { background: #f39c12; }
.bar-fill.net_shot { background: #3498db; }
.bar-fill.drive { background: #9b59b6; }
.bar-fill.lift { background: #1abc9c; }
.bar-fill.serve { background: #e67e22; }

.bar-count {
  color: #eee;
  font-size: 0.85rem;
  font-weight: bold;
}

/* Coaching Section - Fixed Height */
.coaching-section {
  background: #0f0f1a;
  border-radius: 8px;
  padding: 1rem;
  min-height: 80px;
  border-left: 3px solid #4ecca3;
}

.coaching-section .section-label {
  color: #4ecca3;
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
  color: #eee;
  font-size: 0.9rem;
  line-height: 1.4;
}

.no-tip {
  color: #555;
  font-style: italic;
  font-size: 0.85rem;
}
</style>
