<template>
  <div class="heatmap-gallery">
    <div v-if="loading" class="loading">Generating heatmaps...</div>

    <div v-else-if="error" class="error">{{ error }}</div>

    <div v-else-if="heatmaps.length === 0" class="empty">
      No heatmaps available. Need more position data.
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
  sessionId: {
    type: Number,
    required: true
  }
})

const loading = ref(true)
const error = ref('')
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
  error.value = ''

  try {
    const response = await api.get(`/api/v1/stream/${props.sessionId}/heatmaps`)
    const heatmapList = response.data.heatmaps || []

    if (heatmapList.length === 0 && response.data.message) {
      error.value = response.data.message
      loading.value = false
      return
    }

    // Load each heatmap image with auth
    for (const heatmap of heatmapList) {
      heatmap.blobUrl = null
      loadHeatmapImage(heatmap)
    }

    heatmaps.value = heatmapList
  } catch (err) {
    console.error('Failed to load heatmaps:', err)
    error.value = err.response?.data?.detail || 'Failed to generate heatmaps'
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
  } catch (err) {
    console.error(`Failed to load heatmap ${heatmap.type}:`, err)
  }
}

function formatType(type) {
  const labels = {
    'rally_heatmap': 'Rally Heatmap',
    'trajectory': 'Movement Trajectory',
    'time_gradient': 'Time Progression',
    'density_contour': 'Density Contours',
    'rally_comparison': 'Rally Comparison'
  }
  return labels[type] || type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
}

function getDescription(type) {
  const descriptions = {
    'rally_heatmap': 'Each rally shown in a different color',
    'trajectory': 'Connected movement paths during play',
    'time_gradient': 'Color shows progression from start to end',
    'density_contour': 'Contour lines showing movement concentration',
    'rally_comparison': 'Side-by-side comparison of rallies'
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
  link.download = `${heatmap.type}_stream_${props.sessionId}.png`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}
</script>

<style scoped>
.heatmap-gallery {
  width: 100%;
}

.loading, .empty, .error {
  text-align: center;
  padding: 2rem;
  color: var(--text-muted);
}

.error {
  color: var(--color-destructive);
}

.gallery {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 1rem;
}

.heatmap-item {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  overflow: hidden;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
}

.heatmap-item:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

.heatmap-item.selected {
  border-color: var(--color-primary);
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
  background: var(--bg-input);
  color: var(--text-muted);
  font-size: 0.8rem;
}

.heatmap-label {
  padding: 0.5rem 0.75rem 0;
  text-align: center;
  font-size: 0.9rem;
  font-weight: bold;
  color: var(--text-primary);
}

.heatmap-desc {
  padding: 0.25rem 0.75rem 0.75rem;
  text-align: center;
  font-size: 0.75rem;
  color: var(--text-muted);
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
  background: var(--bg-card);
  border-radius: var(--radius-lg);
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
  font-weight: 600;
  transition: background 0.2s;
}

.close-btn:hover {
  background: var(--color-destructive);
}

.enlarged-label {
  padding: 1rem;
  text-align: center;
  font-size: 1.1rem;
  color: var(--text-primary);
}

.download-btn {
  display: block;
  width: 100%;
  text-align: center;
  padding: 0.75rem;
  background: var(--color-primary);
  color: var(--text-on-primary);
  border: none;
  font-weight: 600;
  font-size: 1rem;
  cursor: pointer;
  transition: background 0.2s;
}

.download-btn:hover {
  background: var(--color-primary-hover);
}
</style>
