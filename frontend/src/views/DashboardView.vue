<template>
  <div class="dashboard">
    <router-link to="/hub" class="back-link">&larr; Back to Hub</router-link>

    <div class="home-header">
      <span class="header-icon">&#127992;</span>
      <h1>Badminton Analysis</h1>
    </div>

    <!-- CTA card -->
    <div class="cta-card" @click="$router.push('/live')">
      <div class="cta-circle cta-circle-tr"></div>
      <div class="cta-circle cta-circle-bl"></div>
      <div class="cta-content">
        <h2 class="cta-title">Start Live Analysis</h2>
        <p class="cta-sub">Real-time shot detection and movement tracking from your camera</p>
        <button class="cta-btn">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="20" height="20">
            <circle cx="12" cy="12" r="10"/>
            <circle cx="12" cy="12" r="3" fill="currentColor"/>
          </svg>
          Go Live
        </button>
      </div>
    </div>

    <!-- Upload action -->
    <router-link to="/upload" class="upload-card">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="24" height="24">
        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
        <polyline points="17 8 12 3 7 8"/>
        <line x1="12" y1="3" x2="12" y2="15"/>
      </svg>
      <div class="upload-text">
        <span class="upload-title">Upload Video</span>
        <span class="upload-sub">Analyze a recorded badminton video</span>
      </div>
      <span class="upload-arrow">&rarr;</span>
    </router-link>

    <!-- Loading -->
    <div v-if="loading" class="loading">Loading analysis...</div>

    <!-- Empty state -->
    <div v-else-if="allAnalysis.length === 0" class="empty-state">
      <p>No analysis yet. Start a live session or upload a video to begin.</p>
    </div>

    <!-- Session History -->
    <div v-else class="history-section">
      <h2>Session History</h2>
      <div class="history-list">
        <div v-for="item in allAnalysis" :key="`${item.type}-${item.id}`" class="history-card">
          <div class="history-header">
            <div class="history-title-row">
              <span :class="['type-badge', item.type]">
                {{ item.type === 'stream' ? 'LIVE' : 'VIDEO' }}
              </span>
              <span class="history-name">
                {{ item.type === 'stream' ? (item.title || `Session #${item.id}`) : item.video_filename }}
              </span>
            </div>
            <span :class="['status-badge', item.status]">{{ formatStatus(item.status) }}</span>
          </div>

          <div class="history-info">
            <p v-if="item.status !== 'processing' && item.status_message" class="status-message">{{ item.status_message }}</p>
            <p v-if="item.error_message" class="error-message">{{ item.error_message }}</p>

            <div v-if="item.type === 'stream' && item.status === 'ended'" class="stream-stats">
              <span v-if="item.total_shots > 0" class="stat-item">
                <strong>{{ item.total_shots }}</strong> shots
              </span>
              <span v-if="item.has_recording" class="recording-badge">
                <svg viewBox="0 0 24 24" fill="currentColor" width="14" height="14">
                  <path d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14V10zM5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"/>
                </svg>
                Recorded
              </span>
            </div>

            <span class="history-date">{{ formatDate(item.created_at) }}</span>
          </div>

          <div class="history-actions">
            <!-- Video job actions -->
            <template v-if="item.type === 'video'">
              <template v-if="item.status === 'pending'">
                <router-link :to="`/court-setup/${item.id}`" class="btn-action btn-primary">Setup Court</router-link>
              </template>
              <template v-else-if="item.status === 'completed' || item.has_results">
                <router-link :to="`/results/${item.id}`" class="btn-action btn-success">View Results</router-link>
                <button @click="handleDownloadVideo(item.id)" class="btn-action btn-outline" :disabled="downloadingId === `video-${item.id}`">
                  {{ downloadingId === `video-${item.id}` ? 'Downloading...' : 'Download' }}
                </button>
              </template>
              <template v-else-if="item.status === 'processing'">
                <ProgressTracker :job-id="item.id" />
                <button @click="handleCancelJob(item.id)" class="btn-action btn-outline-warn">Cancel</button>
              </template>
              <button v-if="item.status !== 'processing'" @click="handleDeleteJob(item.id)" class="btn-action btn-danger">Delete</button>
            </template>

            <!-- Stream session actions -->
            <template v-else-if="item.type === 'stream'">
              <template v-if="item.status === 'ended'">
                <router-link v-if="item.has_results" :to="`/stream-results/${item.id}`" class="btn-action btn-success">View Results</router-link>
                <button v-if="item.has_recording" @click="handleDownloadRecording(item.id)" class="btn-action btn-outline" :disabled="downloadingId === `stream-${item.id}`">
                  {{ downloadingId === `stream-${item.id}` ? 'Downloading...' : 'Download' }}
                </button>
              </template>
              <template v-else-if="item.status === 'streaming'">
                <router-link :to="`/live?resume=${item.id}`" class="btn-action btn-primary">Resume</router-link>
              </template>
              <template v-else-if="item.status === 'setup' || item.status === 'ready'">
                <router-link :to="`/live?resume=${item.id}`" class="btn-action btn-primary">Continue Setup</router-link>
              </template>
              <button @click="handleDeleteSession(item.id)" class="btn-action btn-danger" :disabled="item.status === 'streaming'">Delete</button>
            </template>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useJobsStore } from '../stores/jobs'
import api from '../api/client'
import ProgressTracker from '../components/ProgressTracker.vue'

const jobsStore = useJobsStore()

const allAnalysis = computed(() => jobsStore.allAnalysis)
const loading = computed(() => jobsStore.loading)
const downloadingId = ref(null)

onMounted(() => {
  jobsStore.fetchAll()
})

function formatDate(dateString) {
  if (!dateString) return 'N/A'
  return new Date(dateString).toLocaleString()
}

function formatStatus(status) {
  const statusMap = {
    'pending': 'Pending',
    'processing': 'Processing',
    'completed': 'Completed',
    'failed': 'Failed',
    'cancelled': 'Cancelled',
    'setup': 'Setup',
    'ready': 'Ready',
    'streaming': 'Live',
    'paused': 'Paused',
    'ended': 'Completed'
  }
  return statusMap[status] || status
}

async function handleCancelJob(jobId) {
  if (confirm('Are you sure you want to cancel this analysis?')) {
    try {
      await jobsStore.cancelJob(jobId)
    } catch (err) {
      alert('Failed to cancel job: ' + (err.response?.data?.detail || err.message))
    }
  }
}

async function handleDeleteJob(jobId) {
  if (confirm('Are you sure you want to delete this video analysis?')) {
    await jobsStore.deleteJob(jobId)
  }
}

async function handleDeleteSession(sessionId) {
  if (confirm('Are you sure you want to delete this live session?')) {
    await jobsStore.deleteSession(sessionId)
  }
}

async function handleDownloadVideo(jobId) {
  downloadingId.value = `video-${jobId}`
  try {
    const response = await api.get(`/api/v1/results/${jobId}/video`, {
      responseType: 'blob'
    })
    triggerDownload(response.data, 'video/mp4', `analyzed_video_${jobId}.mp4`)
  } catch (err) {
    alert(err.response?.data?.detail || 'Failed to download video')
  } finally {
    downloadingId.value = null
  }
}

async function handleDownloadRecording(sessionId) {
  downloadingId.value = `stream-${sessionId}`
  try {
    const response = await api.get(`/api/v1/stream/${sessionId}/recording`, {
      responseType: 'blob'
    })
    triggerDownload(response.data, 'video/mp4', `stream_recording_${sessionId}.mp4`)
  } catch (err) {
    alert(err.response?.data?.detail || 'Failed to download recording')
  } finally {
    downloadingId.value = null
  }
}

function triggerDownload(data, mimeType, filename) {
  const blob = new Blob([data], { type: mimeType })
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(url)
}
</script>

<style scoped>
.dashboard {
  max-width: 800px;
  margin: 0 auto;
  padding: 1rem;
}

.back-link {
  color: var(--text-muted);
  text-decoration: none;
  font-size: 0.9rem;
}
.back-link:hover { color: var(--color-primary); }

.home-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin: 1rem 0 1.5rem;
}

.header-icon {
  font-size: 2.5rem;
}

.home-header h1 {
  color: var(--text-primary);
  margin: 0;
}

/* CTA Card */
.cta-card {
  position: relative;
  background: var(--gradient-primary);
  border-radius: var(--radius-lg);
  padding: 2rem;
  margin-bottom: 1rem;
  overflow: hidden;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
}

.cta-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-lg);
}

.cta-circle {
  position: absolute;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.1);
}

.cta-circle-tr {
  width: 16rem;
  height: 16rem;
  top: 0;
  right: 0;
  transform: translate(8rem, -8rem);
}

.cta-circle-bl {
  width: 12rem;
  height: 12rem;
  bottom: 0;
  left: 0;
  transform: translate(-6rem, 6rem);
}

.cta-content {
  position: relative;
  z-index: 1;
}

.cta-title {
  font-size: 1.75rem;
  font-weight: 700;
  color: #fff;
  margin: 0 0 0.5rem;
}

.cta-sub {
  color: rgba(191, 219, 254, 0.9);
  font-size: 1.05rem;
  margin: 0 0 1.5rem;
}

.cta-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  background: #fff;
  color: var(--color-primary);
  border: none;
  border-radius: var(--radius-md);
  padding: 0.85rem 1.5rem;
  font-size: 1.05rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
}

.cta-btn:hover {
  background: #eff6ff;
}

/* Upload card */
.upload-card {
  display: flex;
  align-items: center;
  gap: 1rem;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 1.25rem 1.5rem;
  margin-bottom: 2rem;
  text-decoration: none;
  color: var(--text-secondary);
  transition: all 0.2s;
  box-shadow: var(--shadow-md);
}

.upload-card:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.upload-text {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.upload-title {
  font-weight: 600;
  font-size: 1rem;
  color: var(--text-primary);
}

.upload-sub {
  font-size: 0.85rem;
  color: var(--text-muted);
  margin-top: 0.15rem;
}

.upload-arrow {
  font-size: 1.2rem;
  color: var(--text-muted);
}

.upload-card:hover .upload-arrow {
  color: var(--color-primary);
}

/* Loading / empty */
.loading, .empty-state {
  text-align: center;
  padding: 3rem 1rem;
  color: var(--text-muted);
}

/* History */
.history-section h2 {
  color: var(--text-primary);
  font-size: 1.2rem;
  margin-bottom: 1rem;
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.history-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 10px;
  padding: 1.25rem;
  box-shadow: var(--shadow-md);
  transition: border-color 0.2s;
}

.history-card:hover {
  border-color: var(--color-primary);
}

.history-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 0.75rem;
  margin-bottom: 0.75rem;
}

.history-title-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex: 1;
  min-width: 0;
}

.history-name {
  font-weight: 600;
  color: var(--text-primary);
  word-break: break-word;
  font-size: 0.95rem;
}

.type-badge {
  padding: 0.15rem 0.5rem;
  border-radius: 4px;
  font-size: 0.7rem;
  font-weight: bold;
  text-transform: uppercase;
  flex-shrink: 0;
}

.type-badge.video {
  background: var(--color-info-light);
  color: var(--color-info);
}

.type-badge.stream {
  background: var(--color-destructive-light);
  color: var(--color-destructive);
}

.status-badge {
  padding: 0.2rem 0.6rem;
  border-radius: var(--radius-full);
  font-size: 0.75rem;
  font-weight: bold;
  text-transform: uppercase;
  flex-shrink: 0;
}

.status-badge.pending { background: var(--color-warning-light); color: var(--color-warning); }
.status-badge.processing { background: var(--color-info-light); color: var(--color-info); }
.status-badge.completed, .status-badge.ended { background: var(--color-primary-light); color: var(--color-primary); }
.status-badge.failed { background: var(--color-destructive-light); color: var(--color-destructive); }
.status-badge.cancelled { background: rgba(148, 163, 184, 0.1); color: var(--text-muted); }
.status-badge.setup, .status-badge.ready { background: var(--color-secondary-light); color: var(--color-secondary); }
.status-badge.streaming { background: var(--color-destructive-light); color: var(--color-destructive); animation: pulse-status 1.5s infinite; }

@keyframes pulse-status {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}

.history-info {
  margin-bottom: 0.75rem;
}

.status-message {
  color: var(--text-secondary);
  font-size: 0.85rem;
  margin-bottom: 0.35rem;
}

.error-message {
  color: var(--color-destructive);
  font-size: 0.85rem;
  margin-bottom: 0.35rem;
}

.stream-stats {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  align-items: center;
  margin-bottom: 0.35rem;
}

.stat-item {
  color: var(--text-secondary);
  font-size: 0.85rem;
}

.stat-item strong {
  color: var(--color-primary);
}

.recording-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.15rem 0.5rem;
  background: var(--color-destructive-light);
  color: var(--color-destructive);
  border-radius: 4px;
  font-size: 0.75rem;
}

.history-date {
  color: var(--text-muted);
  font-size: 0.8rem;
}

.history-actions {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.btn-action {
  padding: 0.5rem 1rem;
  border-radius: var(--radius-sm);
  text-decoration: none;
  font-size: 0.85rem;
  font-weight: 600;
  cursor: pointer;
  border: none;
  transition: all 0.2s;
}

.btn-action.btn-primary { background: var(--color-primary); color: var(--text-on-primary); }
.btn-action.btn-primary:hover { background: var(--color-primary-hover); }

.btn-action.btn-success { background: var(--color-success); color: white; }

.btn-action.btn-outline {
  background: transparent;
  border: 1px solid var(--color-primary);
  color: var(--color-primary);
}
.btn-action.btn-outline:hover:not(:disabled) { background: var(--color-primary); color: var(--text-on-primary); }

.btn-action.btn-outline-warn {
  background: transparent;
  border: 1px solid var(--color-warning);
  color: var(--color-warning);
}
.btn-action.btn-outline-warn:hover { background: var(--color-warning); color: var(--text-on-primary); }

.btn-action.btn-danger {
  background: transparent;
  border: 1px solid var(--color-destructive);
  color: var(--color-destructive);
}
.btn-action.btn-danger:hover:not(:disabled) { background: var(--color-destructive); color: white; }

.btn-action:disabled { opacity: 0.5; cursor: not-allowed; }

/* Mobile */
@media (max-width: 640px) {
  .cta-title {
    font-size: 1.3rem;
  }

  .cta-sub {
    font-size: 0.9rem;
    margin-bottom: 1rem;
  }

  .cta-card {
    padding: 1.5rem;
  }

  .upload-card {
    padding: 1rem;
  }

  .history-card {
    padding: 1rem;
  }

  .history-actions {
    gap: 0.4rem;
  }

  .btn-action {
    padding: 0.4rem 0.75rem;
    font-size: 0.8rem;
  }
}
</style>
