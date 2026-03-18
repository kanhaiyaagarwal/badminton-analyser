<template>
  <div class="exercise-detail">
    <button class="back-link" @click="$router.back()">&larr; Back</button>

    <div v-if="loading" class="loading-state">
      <div class="spinner" />
    </div>

    <div v-else-if="exercise">
      <!-- Demo video -->
      <div class="demo-area">
        <div v-if="videoId" class="video-wrap" @click="showVideo = !showVideo">
          <template v-if="showVideo">
            <iframe
              :src="`https://www.youtube.com/embed/${videoId}?autoplay=1&loop=1&mute=1&playsinline=1&rel=0&modestbranding=1&fs=0&iv_load_policy=3&disablekb=0&playlist=${videoId}`"
              frameborder="0"
              allow="autoplay; encrypted-media"
              sandbox="allow-scripts allow-same-origin allow-presentation"
              class="video-iframe"
            ></iframe>
          </template>
          <template v-else>
            <img :src="`https://img.youtube.com/vi/${videoId}/0.jpg`" alt="Demo" class="video-thumb" />
            <div class="play-overlay">
              <svg viewBox="0 0 24 24" fill="white" width="40" height="40"><polygon points="5 3 19 12 5 21 5 3"/></svg>
            </div>
          </template>
        </div>
        <div v-else class="demo-placeholder">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="5" r="2"/>
            <path d="M12 7v6"/>
            <path d="M8 21l2-6h4l2 6"/>
            <path d="M6 12h12"/>
          </svg>
          <span>Demo coming soon</span>
        </div>
        <p v-if="videoId" class="demo-label">Tap to {{ showVideo ? 'hide' : 'watch' }} demo</p>
      </div>

      <!-- Exercise info -->
      <h1 class="ex-name">{{ exercise.name }}</h1>
      <div class="ex-meta-row">
        <span class="badge category">{{ exercise.category }}</span>
        <span class="badge difficulty" :class="exercise.difficulty">{{ exercise.difficulty }}</span>
        <span class="badge mode">{{ trackingLabel }}</span>
      </div>

      <p v-if="exercise.description" class="ex-description">{{ exercise.description }}</p>

      <!-- Form Cues -->
      <div v-if="exercise.form_cues?.length" class="section">
        <h3 class="section-title">Form Cues</h3>
        <ul class="cue-list">
          <li v-for="(cue, i) in exercise.form_cues" :key="i" class="cue-item good">
            <span class="cue-icon">&#10003;</span>
            {{ cue }}
          </li>
        </ul>
      </div>

      <!-- Common Mistakes -->
      <div v-if="exercise.common_mistakes?.length" class="section">
        <h3 class="section-title">Common Mistakes</h3>
        <ul class="cue-list">
          <li v-for="(mistake, i) in exercise.common_mistakes" :key="i" class="cue-item bad">
            <span class="cue-icon">&#9888;</span>
            {{ mistake }}
          </li>
        </ul>
      </div>

      <!-- Equipment & Muscles -->
      <div class="section">
        <h3 class="section-title">Details</h3>
        <div class="chip-group">
          <span class="detail-label">Equipment:</span>
          <span v-for="eq in exercise.equipment" :key="eq" class="chip">
            {{ eq === 'none' ? 'Bodyweight' : eq }}
          </span>
        </div>
        <div class="chip-group">
          <span class="detail-label">Muscles:</span>
          <span v-for="mg in exercise.muscle_groups" :key="mg" class="chip muscle">
            {{ mg }}
          </span>
        </div>
      </div>

      <!-- History placeholder -->
      <div class="section">
        <h3 class="section-title">History</h3>
        <p class="empty-hint">No history yet. Complete a workout to see your progress here.</p>
      </div>

      <!-- Add to Quick Start -->
      <button class="btn-primary full-width" @click="addToQuickStart">
        Add to Quick Start
      </button>
    </div>

    <div v-else class="empty-state">
      <p>Exercise not found.</p>
    </div>

    <!-- Toast -->
    <div v-if="toast" class="toast">{{ toast }}</div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useWorkoutStore } from '../../stores/workout'

const route = useRoute()
const router = useRouter()
const workoutStore = useWorkoutStore()

const loading = ref(true)
const exercise = ref(null)
const toast = ref(null)
const showVideo = ref(false)

const videoId = computed(() => {
  const url = exercise.value?.demo_video_url
  if (!url) return null
  const match = url.match(/(?:shorts\/|v=|youtu\.be\/)([a-zA-Z0-9_-]{11})/)
  return match ? match[1] : null
})

const trackingLabel = computed(() => {
  const mode = exercise.value?.tracking_mode
  if (mode === 'reps') return 'Reps'
  if (mode === 'hold') return 'Hold'
  if (mode === 'timed') return 'Timed'
  return mode || ''
})

function addToQuickStart() {
  router.push(`/workout/quick-start?add=${exercise.value.slug}`)
}

onMounted(async () => {
  try {
    const data = await workoutStore.fetchExercise(route.params.slug)
    exercise.value = data
  } catch {
    exercise.value = null
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.exercise-detail {
  padding: 1.25rem;
  padding-bottom: 6rem;
}

.back-link {
  color: var(--text-muted);
  text-decoration: none;
  font-size: 0.85rem;
  background: none;
  border: none;
  cursor: pointer;
  padding: 0;
  font-family: inherit;
}
.back-link:hover { color: var(--color-primary); }

/* Demo */
.demo-area {
  margin: 1rem 0;
}

.video-wrap {
  position: relative;
  width: 100%;
  aspect-ratio: 9/16;
  max-height: 360px;
  border-radius: var(--radius-lg);
  overflow: hidden;
  background: #000;
  cursor: pointer;
}

.video-iframe {
  width: 100%;
  height: 100%;
  border: none;
}

.video-thumb {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.play-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.35);
}

.demo-label {
  text-align: center;
  font-size: 0.7rem;
  color: var(--text-muted);
  margin-top: 0.4rem;
}

.demo-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 2.5rem 1rem;
  background: var(--bg-input);
  border: 1px dashed var(--border-color);
  border-radius: var(--radius-lg);
  color: var(--text-muted);
  font-size: 0.8rem;
}

/* Name & meta */
.ex-name {
  font-size: 1.4rem;
  font-weight: 800;
  color: var(--text-primary);
  margin-bottom: 0.5rem;
}

.ex-meta-row {
  display: flex;
  gap: 0.35rem;
  margin-bottom: 0.75rem;
}

.badge {
  padding: 0.2rem 0.6rem;
  border-radius: var(--radius-full);
  font-size: 0.7rem;
  font-weight: 500;
}

.badge.category {
  background: var(--color-info-light);
  color: var(--color-info);
  text-transform: capitalize;
}

.badge.difficulty.beginner {
  background: var(--color-success-light);
  color: var(--color-success);
}

.badge.difficulty.intermediate {
  background: var(--color-warning-light);
  color: var(--color-warning);
}

.badge.difficulty.advanced {
  background: var(--color-destructive-light);
  color: var(--color-destructive);
}

.badge.mode {
  background: var(--color-secondary-light);
  color: var(--color-secondary);
}

.ex-description {
  font-size: 0.9rem;
  color: var(--text-secondary);
  line-height: 1.5;
  margin-bottom: 1.25rem;
}

/* Sections */
.section {
  margin-bottom: 1.25rem;
}

.section-title {
  font-size: 0.85rem;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 0.5rem;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

/* Form cues */
.cue-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.cue-item {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  padding: 0.5rem 0.65rem;
  border-radius: var(--radius-sm);
  font-size: 0.85rem;
  line-height: 1.4;
}

.cue-item.good {
  background: var(--color-success-light);
  color: var(--text-secondary);
}

.cue-item.bad {
  background: var(--color-warning-light);
  color: var(--text-secondary);
}

.cue-icon {
  flex-shrink: 0;
  font-size: 0.75rem;
}

/* Details */
.chip-group {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  flex-wrap: wrap;
  margin-bottom: 0.5rem;
}

.detail-label {
  font-size: 0.75rem;
  color: var(--text-muted);
  font-weight: 500;
}

.chip {
  padding: 0.2rem 0.55rem;
  border-radius: var(--radius-full);
  background: var(--bg-input);
  border: 1px solid var(--border-color);
  font-size: 0.7rem;
  color: var(--text-secondary);
  text-transform: capitalize;
}

.chip.muscle {
  background: var(--color-primary-light);
  border-color: transparent;
  color: var(--color-primary);
}

.empty-hint {
  font-size: 0.8rem;
  color: var(--text-muted);
  font-style: italic;
}

/* Buttons */
.btn-primary {
  padding: 0.75rem 1.25rem;
  background: var(--gradient-primary);
  color: white;
  border: none;
  border-radius: var(--radius-md);
  font-weight: 600;
  font-size: 0.9rem;
  cursor: pointer;
  transition: opacity 0.2s;
}

.btn-primary:hover { opacity: 0.9; }
.btn-primary.full-width { width: 100%; }

/* Loading */
.loading-state {
  text-align: center;
  padding: 3rem 0;
}

.spinner {
  width: 32px;
  height: 32px;
  border: 3px solid var(--border-color);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin: 0 auto;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.empty-state {
  text-align: center;
  padding: 3rem;
  color: var(--text-muted);
}

/* Toast */
.toast {
  position: fixed;
  bottom: 5rem;
  left: 50%;
  transform: translateX(-50%);
  padding: 0.65rem 1.25rem;
  background: var(--text-primary);
  color: white;
  border-radius: var(--radius-full);
  font-size: 0.8rem;
  z-index: 100;
  max-width: 90%;
  text-align: center;
}
</style>
