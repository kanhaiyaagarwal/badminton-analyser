<template>
  <div class="rally-timeline">
    <div v-if="rallies.length === 0" class="empty">
      No rallies detected in this analysis.
    </div>

    <div v-else class="rallies-list">
      <div
        v-for="rally in rallies"
        :key="rally.rally_id"
        class="rally-item"
        :class="{ expanded: expandedRally === rally.rally_id }"
      >
        <div class="rally-header" @click="toggleRally(rally.rally_id)">
          <div class="rally-info">
            <span class="rally-id">Rally {{ rally.rally_id }}</span>
            <span class="rally-stats">
              {{ rally.hit_count ?? rally.shot_count }} hits | {{ (rally.rally_duration ?? rally.duration).toFixed(1) }}s
            </span>
          </div>
          <div class="rally-preview">
            <span
              v-for="(shot, index) in rally.shots.slice(0, 5)"
              :key="index"
              :class="['shot-chip', shot]"
            >
              {{ formatShot(shot) }}
            </span>
            <span v-if="rally.shots.length > 5" class="more">
              +{{ rally.shots.length - 5 }}
            </span>
          </div>
          <span class="expand-icon">{{ expandedRally === rally.rally_id ? '-' : '+' }}</span>
        </div>

        <div v-if="expandedRally === rally.rally_id" class="rally-details">
          <div class="shots-flow">
            <div
              v-for="(shot, index) in rally.shots"
              :key="index"
              class="shot-item"
            >
              <div :class="['shot-badge', shot]">
                {{ formatShot(shot) }}
              </div>
              <span v-if="index < rally.shots.length - 1" class="arrow">></span>
            </div>
          </div>

          <div class="shot-breakdown">
            <h4>Shot Breakdown</h4>
            <div class="breakdown-grid">
              <div
                v-for="(count, shotType) in getShotCounts(rally.shots)"
                :key="shotType"
                class="breakdown-item"
              >
                <span :class="['dot', shotType]"></span>
                <span class="type">{{ formatShot(shotType) }}</span>
                <span class="count">{{ count }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const props = defineProps({
  rallies: {
    type: Array,
    default: () => []
  }
})

const expandedRally = ref(null)

function toggleRally(rallyId) {
  expandedRally.value = expandedRally.value === rallyId ? null : rallyId
}

function formatShot(shot) {
  const shortNames = {
    smash: 'SM',
    clear: 'CL',
    drop_shot: 'DR',
    net_shot: 'NT',
    drive: 'DV',
    lift: 'LF'
  }
  return shortNames[shot] || shot.slice(0, 2).toUpperCase()
}

function getShotCounts(shots) {
  const counts = {}
  shots.forEach(shot => {
    counts[shot] = (counts[shot] || 0) + 1
  })
  return counts
}
</script>

<style scoped>
.rally-timeline {
  width: 100%;
}

.empty {
  text-align: center;
  padding: 2rem;
  color: var(--text-muted);
}

.rallies-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.rally-item {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  overflow: hidden;
  transition: all 0.2s;
}

.rally-item.expanded {
  background: var(--bg-card);
}

.rally-header {
  display: flex;
  align-items: center;
  padding: 1rem;
  cursor: pointer;
  transition: background 0.2s;
}

.rally-header:hover {
  background: var(--color-primary-light);
}

.rally-info {
  min-width: 150px;
}

.rally-id {
  display: block;
  color: var(--color-primary);
  font-weight: bold;
  font-size: 0.9rem;
}

.rally-stats {
  color: var(--text-muted);
  font-size: 0.8rem;
}

.rally-preview {
  flex: 1;
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem;
  margin: 0 1rem;
}

.shot-chip {
  padding: 0.15rem 0.4rem;
  border-radius: 4px;
  font-size: 0.7rem;
  font-weight: bold;
  background: var(--border-color);
  color: var(--text-primary);
}

.shot-chip.smash { background: var(--color-destructive-light); color: var(--color-destructive); }
.shot-chip.clear { background: var(--color-success-light); color: var(--color-success); }
.shot-chip.drop_shot { background: var(--color-warning-light); color: var(--color-warning); }
.shot-chip.net_shot { background: var(--color-info-light); color: var(--color-info); }
.shot-chip.drive { background: var(--color-secondary-light); color: var(--color-secondary); }
.shot-chip.lift { background: var(--color-primary-light); color: var(--color-primary); }

.more {
  color: var(--text-muted);
  font-size: 0.8rem;
  padding: 0.15rem 0.4rem;
}

.expand-icon {
  color: var(--color-primary);
  font-size: 1.2rem;
  font-weight: bold;
  width: 24px;
  text-align: center;
}

.rally-details {
  padding: 0 1rem 1rem;
  border-top: 1px solid var(--border-color);
}

.shots-flow {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
  padding: 1rem 0;
}

.shot-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.shot-badge {
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: bold;
}

.shot-badge.smash { background: var(--color-destructive); color: white; }
.shot-badge.clear { background: var(--color-success); color: white; }
.shot-badge.drop_shot { background: var(--color-warning); color: white; }
.shot-badge.net_shot { background: var(--color-info); color: white; }
.shot-badge.drive { background: var(--color-secondary); color: white; }
.shot-badge.lift { background: var(--color-primary); color: white; }

.arrow {
  color: #4a4a6a;
  font-size: 0.8rem;
}

.shot-breakdown {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 1rem;
  margin-top: 0.5rem;
}

.shot-breakdown h4 {
  color: var(--text-muted);
  font-size: 0.8rem;
  font-weight: normal;
  margin-bottom: 0.75rem;
}

.breakdown-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
  gap: 0.5rem;
}

.breakdown-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.85rem;
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.dot.smash { background: var(--color-destructive); }
.dot.clear { background: var(--color-success); }
.dot.drop_shot { background: var(--color-warning); }
.dot.net_shot { background: var(--color-info); }
.dot.drive { background: var(--color-secondary); }
.dot.lift { background: var(--color-primary); }

.type {
  color: var(--text-muted);
  flex: 1;
}

.count {
  color: var(--text-primary);
  font-weight: bold;
}
</style>
