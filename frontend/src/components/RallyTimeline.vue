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
              {{ rally.shot_count }} shots | {{ rally.duration.toFixed(1) }}s
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
  color: #888;
}

.rallies-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.rally-item {
  background: #1a1a2e;
  border-radius: 8px;
  overflow: hidden;
  transition: all 0.2s;
}

.rally-item.expanded {
  background: #1e1e3a;
}

.rally-header {
  display: flex;
  align-items: center;
  padding: 1rem;
  cursor: pointer;
  transition: background 0.2s;
}

.rally-header:hover {
  background: rgba(78, 204, 163, 0.1);
}

.rally-info {
  min-width: 150px;
}

.rally-id {
  display: block;
  color: #4ecca3;
  font-weight: bold;
  font-size: 0.9rem;
}

.rally-stats {
  color: #888;
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
  background: #2a2a4a;
  color: #eee;
}

.shot-chip.smash { background: rgba(231, 76, 60, 0.3); color: #e74c3c; }
.shot-chip.clear { background: rgba(46, 204, 113, 0.3); color: #2ecc71; }
.shot-chip.drop_shot { background: rgba(243, 156, 18, 0.3); color: #f39c12; }
.shot-chip.net_shot { background: rgba(52, 152, 219, 0.3); color: #3498db; }
.shot-chip.drive { background: rgba(155, 89, 182, 0.3); color: #9b59b6; }
.shot-chip.lift { background: rgba(26, 188, 156, 0.3); color: #1abc9c; }

.more {
  color: #888;
  font-size: 0.8rem;
  padding: 0.15rem 0.4rem;
}

.expand-icon {
  color: #4ecca3;
  font-size: 1.2rem;
  font-weight: bold;
  width: 24px;
  text-align: center;
}

.rally-details {
  padding: 0 1rem 1rem;
  border-top: 1px solid #2a2a4a;
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

.shot-badge.smash { background: #e74c3c; color: white; }
.shot-badge.clear { background: #2ecc71; color: white; }
.shot-badge.drop_shot { background: #f39c12; color: white; }
.shot-badge.net_shot { background: #3498db; color: white; }
.shot-badge.drive { background: #9b59b6; color: white; }
.shot-badge.lift { background: #1abc9c; color: white; }

.arrow {
  color: #4a4a6a;
  font-size: 0.8rem;
}

.shot-breakdown {
  background: #16213e;
  border-radius: 6px;
  padding: 1rem;
  margin-top: 0.5rem;
}

.shot-breakdown h4 {
  color: #888;
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

.dot.smash { background: #e74c3c; }
.dot.clear { background: #2ecc71; }
.dot.drop_shot { background: #f39c12; }
.dot.net_shot { background: #3498db; }
.dot.drive { background: #9b59b6; }
.dot.lift { background: #1abc9c; }

.type {
  color: #888;
  flex: 1;
}

.count {
  color: #eee;
  font-weight: bold;
}
</style>
