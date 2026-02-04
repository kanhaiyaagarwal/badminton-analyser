<template>
  <div class="heatmap-gallery">
    <div v-if="loading" class="loading">Loading heatmaps...</div>

    <div v-else-if="heatmaps.length === 0" class="empty">
      No heatmaps available for this analysis.
    </div>

    <div v-else class="gallery">
      <div
        v-for="heatmap in heatmaps"
        :key="heatmap.type"
        class="heatmap-item"
        :class="{ selected: selectedType === heatmap.type }"
        @click="selectHeatmap(heatmap)"
      >
        <img v-if="heatmap.blobUrl" :src="heatmap.blobUrl" :alt="heatmap.type" />
        <div v-else class="img-loading">Loading...</div>
        <div class="heatmap-label">{{ formatType(heatmap.type) }}</div>
        <div class="heatmap-desc">{{ getDescription(heatmap.type) }}</div>
      </div>
    </div>

    <!-- Enlarged view -->
    <div v-if="selectedHeatmap" class="enlarged-view" @click="selectedHeatmap = null">
      <div class="enlarged-content" @click.stop>
        <button class="close-btn" @click="selectedHeatmap = null">X</button>
        <img v-if="selectedHeatmap.blobUrl" :src="selectedHeatmap.blobUrl" :alt="selectedHeatmap.type" />
        <div class="enlarged-label">{{ formatType(selectedHeatmap.type) }}</div>
        <button @click="downloadHeatmap(selectedHeatmap)" class="download-btn">
          Download
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import api from '../api/client'

const props = defineProps({
  jobId: {
    type: Number,
    required: true
  }
})

const loading = ref(true)
const heatmaps = ref([])
const selectedType = ref(null)
const selectedHeatmap = ref(null)

onMounted(async () => {
  await loadHeatmaps()
})

onUnmounted(() => {
  // Cleanup blob URLs
  heatmaps.value.forEach(h => {
    if (h.blobUrl) {
      URL.revokeObjectURL(h.blobUrl)
    }
  })
})

async function loadHeatmaps() {
  loading.value = true

  try {
    const response = await api.get(`/api/v1/results/${props.jobId}/heatmaps`)
    const heatmapList = response.data.heatmaps || []

    // Load each heatmap image via API (backend proxies S3)
    for (const heatmap of heatmapList) {
      heatmap.blobUrl = null
      loadHeatmapImage(heatmap)
    }

    heatmaps.value = heatmapList
  } catch (error) {
    console.error('Failed to load heatmaps:', error)
    heatmaps.value = []
  } finally {
    loading.value = false
  }
}

async function loadHeatmapImage(heatmap) {
  try {
    const response = await api.get(heatmap.url, {
      responseType: 'blob'
    })
    heatmap.blobUrl = URL.createObjectURL(response.data)
  } catch (error) {
    console.error(`Failed to load heatmap ${heatmap.type}:`, error)
  }
}

function formatType(type) {
  const labels = {
    'rally_heatmap': 'Rally Heatmap',
    'trajectory': 'Movement Trajectory',
    'time_gradient': 'Time Progression',
    'density_contour': 'Density Contours',
    'movement': 'Movement Heatmap'
  }
  return labels[type] || type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
}

function getDescription(type) {
  const descriptions = {
    'rally_heatmap': 'Each rally shown in a different color',
    'trajectory': 'Connected movement paths during play',
    'time_gradient': 'Color shows progression from start to end',
    'density_contour': 'Contour lines showing movement concentration',
    'movement': 'Overall movement heat distribution'
  }
  return descriptions[type] || ''
}

function selectHeatmap(heatmap) {
  selectedType.value = heatmap.type
  selectedHeatmap.value = heatmap
}

function downloadHeatmap(heatmap) {
  if (!heatmap.blobUrl) return

  const link = document.createElement('a')
  link.href = heatmap.blobUrl
  link.download = `${heatmap.type}_${props.jobId}.png`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}
</script>

<style scoped>
.heatmap-gallery {
  width: 100%;
}

.loading, .empty {
  text-align: center;
  padding: 2rem;
  color: #888;
}

.gallery {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 1rem;
}

.heatmap-item {
  background: #1a1a2e;
  border-radius: 8px;
  overflow: hidden;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
  border: 2px solid transparent;
}

.heatmap-item:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}

.heatmap-item.selected {
  border-color: #4ecca3;
}

.heatmap-item img {
  width: 100%;
  height: 150px;
  object-fit: cover;
}

.img-loading {
  width: 100%;
  height: 150px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #0a0a1a;
  color: #666;
  font-size: 0.8rem;
}

.heatmap-label {
  padding: 0.5rem 0.75rem 0;
  text-align: center;
  font-size: 0.9rem;
  font-weight: bold;
  color: #eee;
}

.heatmap-desc {
  padding: 0.25rem 0.75rem 0.75rem;
  text-align: center;
  font-size: 0.75rem;
  color: #888;
}

.enlarged-view {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.9);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 2rem;
}

.enlarged-content {
  position: relative;
  max-width: 90vw;
  max-height: 90vh;
  background: #16213e;
  border-radius: 12px;
  overflow: hidden;
}

.enlarged-content img {
  max-width: 100%;
  max-height: calc(90vh - 100px);
  display: block;
}

.close-btn {
  position: absolute;
  top: 1rem;
  right: 1rem;
  background: rgba(0, 0, 0, 0.5);
  color: white;
  border: none;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  cursor: pointer;
  font-size: 1rem;
  transition: background 0.2s;
}

.close-btn:hover {
  background: #e74c3c;
}

.enlarged-label {
  padding: 1rem;
  text-align: center;
  font-size: 1.1rem;
  color: #eee;
}

.download-btn {
  display: block;
  width: 100%;
  text-align: center;
  padding: 0.75rem;
  background: #4ecca3;
  color: #1a1a2e;
  border: none;
  font-weight: bold;
  font-size: 1rem;
  cursor: pointer;
  transition: background 0.2s;
}

.download-btn:hover {
  background: #3db892;
}
</style>
