<template>
  <div class="mimic-browse">
    <div class="browse-header">
      <router-link to="/hub" class="back-link">&larr; Back to Hub</router-link>
      <h1>Mimic Challenges</h1>
      <p class="subtitle">Watch a reference video, then mimic the movements to score points</p>
    </div>

    <!-- Upload section -->
    <div class="upload-section">
      <button class="upload-btn" @click="showUpload = !showUpload">
        {{ showUpload ? 'Cancel' : '+ Upload Challenge' }}
      </button>

      <div v-if="showUpload" class="upload-form">
        <input v-model="uploadTitle" type="text" placeholder="Challenge title" class="input" />
        <textarea v-model="uploadDescription" placeholder="Description (optional)" class="input textarea" rows="2"></textarea>
        <div class="file-picker">
          <input type="file" accept="video/*" ref="fileInput" @change="onFileSelected" class="file-input" />
          <span v-if="selectedFile" class="file-name">{{ selectedFile.name }}</span>
        </div>
        <button @click="handleUpload" :disabled="!uploadTitle || !selectedFile || uploading" class="submit-btn">
          {{ uploading ? 'Uploading...' : 'Upload' }}
        </button>
      </div>
    </div>

    <!-- Trending section -->
    <section v-if="mimicStore.trending.length > 0" class="section">
      <h2 class="section-title">Trending</h2>
      <div class="challenge-grid">
        <div
          v-for="ch in mimicStore.trending"
          :key="ch.id"
          class="challenge-card"
        >
          <div class="card-thumb" @click="goToChallenge(ch)">
            <img v-if="ch.has_thumbnail" :src="`/api/v1/mimic/challenges/${ch.id}/thumbnail`" alt="" />
            <div v-else class="thumb-placeholder">&#127916;</div>
          </div>
          <div class="card-info">
            <h3>{{ ch.title }}</h3>
            <div class="card-meta">
              <span v-if="ch.video_duration">{{ formatDuration(ch.video_duration) }}</span>
              <span>{{ ch.play_count }} plays</span>
            </div>
            <span v-if="ch.processing_status === 'ready'" class="status ready">Ready</span>
            <span v-else class="status processing">{{ ch.processing_status }}</span>
            <div v-if="ch.processing_status === 'ready'" class="card-actions">
              <button class="action-btn live-btn" @click="goToChallenge(ch)">Live</button>
              <button
                class="action-btn upload-compare-btn"
                @click="openCompareUpload(ch.id)"
                :disabled="comparingId === ch.id"
              >
                {{ comparingId === ch.id ? 'Processing...' : 'Upload Video' }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- All challenges -->
    <section class="section">
      <h2 class="section-title">All Challenges</h2>
      <div v-if="mimicStore.loading && !mimicStore.challenges.length" class="loading">Loading...</div>
      <div v-else-if="mimicStore.challenges.length === 0" class="empty">
        No challenges yet. Upload one to get started!
      </div>
      <div v-else class="challenge-grid">
        <div
          v-for="ch in mimicStore.challenges"
          :key="ch.id"
          class="challenge-card"
        >
          <div class="card-thumb" @click="goToChallenge(ch)">
            <img v-if="ch.has_thumbnail" :src="`/api/v1/mimic/challenges/${ch.id}/thumbnail`" alt="" />
            <div v-else class="thumb-placeholder">&#127916;</div>
          </div>
          <div class="card-info">
            <h3>{{ ch.title }}</h3>
            <p v-if="ch.description" class="card-desc">{{ ch.description }}</p>
            <div class="card-meta">
              <span v-if="ch.video_duration">{{ formatDuration(ch.video_duration) }}</span>
              <span>{{ ch.play_count }} plays</span>
            </div>
            <span v-if="ch.processing_status === 'ready'" class="status ready">Ready</span>
            <span v-else-if="ch.processing_status === 'pending' || ch.processing_status === 'processing'" class="status processing">Processing...</span>
            <span v-else class="status failed">Failed</span>
            <div v-if="ch.processing_status === 'ready'" class="card-actions">
              <button class="action-btn live-btn" @click="goToChallenge(ch)">Live</button>
              <button
                class="action-btn upload-compare-btn"
                @click="openCompareUpload(ch.id)"
                :disabled="comparingId === ch.id"
              >
                {{ comparingId === ch.id ? 'Processing...' : 'Upload Video' }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- Hidden file input for compare upload -->
    <input
      type="file"
      accept="video/*"
      ref="compareFileInput"
      style="display: none"
      @change="onCompareFileSelected"
    />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useMimicStore } from '../stores/mimic'

const router = useRouter()
const mimicStore = useMimicStore()

const showUpload = ref(false)
const uploadTitle = ref('')
const uploadDescription = ref('')
const selectedFile = ref(null)
const uploading = ref(false)
const fileInput = ref(null)

// Compare upload state
const compareFileInput = ref(null)
const comparingId = ref(null)
let pendingChallengeId = null

onMounted(() => {
  mimicStore.fetchChallenges()
  mimicStore.fetchTrending()
})

function onFileSelected(e) {
  selectedFile.value = e.target.files?.[0] || null
}

async function handleUpload() {
  if (!uploadTitle.value || !selectedFile.value) return
  uploading.value = true
  try {
    const formData = new FormData()
    formData.append('title', uploadTitle.value)
    if (uploadDescription.value) formData.append('description', uploadDescription.value)
    formData.append('video', selectedFile.value)
    await mimicStore.uploadChallenge(formData)
    // Reset form
    uploadTitle.value = ''
    uploadDescription.value = ''
    selectedFile.value = null
    showUpload.value = false
    // Refresh list
    mimicStore.fetchChallenges()
  } catch (err) {
    // error is in store
  } finally {
    uploading.value = false
  }
}

function goToChallenge(ch) {
  if (ch.processing_status === 'ready') {
    router.push(`/mimic/session/${ch.id}`)
  }
}

function openCompareUpload(challengeId) {
  pendingChallengeId = challengeId
  // Reset file input so the same file can be re-selected
  if (compareFileInput.value) compareFileInput.value.value = ''
  compareFileInput.value?.click()
}

async function onCompareFileSelected(e) {
  const file = e.target.files?.[0]
  if (!file || !pendingChallengeId) return

  const challengeId = pendingChallengeId
  comparingId.value = challengeId

  try {
    const formData = new FormData()
    formData.append('video', file)
    const result = await mimicStore.uploadComparison(challengeId, formData)
    const session = await mimicStore.pollSession(result.session_id)
    router.push(`/mimic/results/${session.id}`)
  } catch (err) {
    // error is in store
  } finally {
    comparingId.value = null
    pendingChallengeId = null
  }
}

function formatDuration(seconds) {
  if (!seconds) return ''
  const m = Math.floor(seconds / 60)
  const s = Math.round(seconds % 60)
  return m > 0 ? `${m}m ${s}s` : `${s}s`
}
</script>

<style scoped>
.mimic-browse {
  max-width: 900px;
  margin: 0 auto;
  padding: 1.5rem 1rem;
}

.browse-header {
  margin-bottom: 1.5rem;
}

.back-link {
  color: var(--text-muted);
  text-decoration: none;
  font-size: 0.9rem;
}

.browse-header h1 {
  color: var(--text-primary);
  font-size: 1.8rem;
  margin: 0.5rem 0 0.25rem;
}

.subtitle {
  color: var(--text-muted);
  font-size: 0.95rem;
}

.upload-section {
  margin-bottom: 2rem;
}

.upload-btn {
  background: var(--color-primary);
  color: white;
  border: none;
  padding: 0.6rem 1.2rem;
  border-radius: var(--radius-md, 8px);
  cursor: pointer;
  font-size: 0.9rem;
}

.upload-form {
  margin-top: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  max-width: 400px;
}

.input {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md, 8px);
  padding: 0.6rem 0.8rem;
  color: var(--text-primary);
  font-size: 0.9rem;
}

.textarea {
  resize: vertical;
}

.file-picker {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.file-input {
  font-size: 0.85rem;
}

.file-name {
  color: var(--text-secondary);
  font-size: 0.85rem;
}

.submit-btn {
  background: var(--color-primary);
  color: white;
  border: none;
  padding: 0.6rem 1.2rem;
  border-radius: var(--radius-md, 8px);
  cursor: pointer;
  font-size: 0.9rem;
  width: fit-content;
}

.submit-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.section {
  margin-bottom: 2rem;
}

.section-title {
  color: var(--text-primary);
  font-size: 1.2rem;
  margin-bottom: 1rem;
}

.challenge-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 1rem;
}

.challenge-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg, 12px);
  overflow: hidden;
  transition: all 0.2s ease;
  box-shadow: var(--shadow-sm);
}

.challenge-card:hover {
  border-color: var(--color-primary);
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

.card-thumb {
  aspect-ratio: 16/9;
  background: var(--bg-secondary, #1a1a2e);
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.card-thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.thumb-placeholder {
  font-size: 2rem;
  opacity: 0.4;
}

.card-info {
  padding: 0.75rem 1rem;
}

.card-info h3 {
  color: var(--text-primary);
  font-size: 1rem;
  margin: 0 0 0.25rem;
}

.card-desc {
  color: var(--text-muted);
  font-size: 0.8rem;
  margin: 0 0 0.5rem;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.card-meta {
  display: flex;
  gap: 0.75rem;
  color: var(--text-muted);
  font-size: 0.8rem;
  margin-bottom: 0.4rem;
}

.status {
  font-size: 0.75rem;
  padding: 0.15rem 0.5rem;
  border-radius: 4px;
  display: inline-block;
}

.status.ready {
  background: rgba(46, 204, 113, 0.15);
  color: #2ecc71;
}

.status.processing {
  background: rgba(241, 196, 15, 0.15);
  color: #f1c40f;
}

.status.failed {
  background: rgba(231, 76, 60, 0.15);
  color: #e74c3c;
}

.card-actions {
  display: flex;
  gap: 0.5rem;
  margin-top: 0.5rem;
}

.action-btn {
  border: none;
  padding: 0.35rem 0.75rem;
  border-radius: var(--radius-md, 8px);
  cursor: pointer;
  font-size: 0.8rem;
  font-weight: 500;
}

.action-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.live-btn {
  background: var(--color-primary);
  color: white;
}

.upload-compare-btn {
  background: var(--bg-secondary, #2a2a3e);
  color: var(--text-primary);
  border: 1px solid var(--border-color);
}

.card-thumb {
  cursor: pointer;
}

.loading, .empty {
  color: var(--text-muted);
  text-align: center;
  padding: 2rem;
}
</style>
