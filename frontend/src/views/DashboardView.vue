<template>
  <div class="dashboard">
    <div class="dashboard-header">
      <h1>My Analysis</h1>
      <div class="header-actions">
        <router-link v-if="isAdmin" to="/admin" class="btn-admin">
          Admin
        </router-link>
        <router-link to="/live" class="btn-live">
          <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <circle cx="12" cy="12" r="10" stroke-width="2"/>
            <circle cx="12" cy="12" r="3" fill="currentColor"/>
          </svg>
          Live Analysis
        </router-link>
        <router-link to="/upload" class="btn-upload">
          + Upload Video
        </router-link>
      </div>
    </div>

    <div v-if="loading" class="loading">Loading analysis...</div>

    <div v-else-if="allAnalysis.length === 0" class="empty-state">
      <p>No analysis yet.</p>
      <div class="empty-actions">
        <router-link to="/upload" class="btn-primary">Upload a video</router-link>
        <span class="or-divider">or</span>
        <router-link to="/live" class="btn-live-alt">Start live analysis</router-link>
      </div>
    </div>

    <div v-else class="jobs-grid">
      <div v-for="item in allAnalysis" :key="`${item.type}-${item.id}`" class="job-card">
        <div class="job-header">
          <div class="job-title-row">
            <span :class="['type-badge', item.type]">
              {{ item.type === 'stream' ? 'LIVE' : 'VIDEO' }}
            </span>
            <span class="job-filename">
              {{ item.type === 'stream' ? (item.title || `Session #${item.id}`) : item.video_filename }}
            </span>
          </div>
          <span :class="['status-badge', item.status]">{{ formatStatus(item.status) }}</span>
        </div>

        <div class="job-info">
          <!-- Video job processing -->
          <div v-if="item.type === 'video' && item.status === 'processing'" class="progress-bar">
            <div class="progress-fill" :style="{ width: item.progress + '%' }"></div>
            <span class="progress-text">{{ Math.round(item.progress) }}%</span>
          </div>

          <p v-if="item.status_message" class="status-message">{{ item.status_message }}</p>
          <p v-if="item.error_message" class="error-message">{{ item.error_message }}</p>

          <!-- Show stats for completed stream sessions -->
          <div v-if="item.type === 'stream' && item.status === 'ended'" class="stream-stats">
            <span v-if="item.total_shots > 0" class="stat-item">
              <strong>{{ item.total_shots }}</strong> shots detected
            </span>
            <span v-if="item.has_recording" class="recording-badge">
              <svg class="badge-icon" viewBox="0 0 24 24" fill="currentColor">
                <path d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14V10zM5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"/>
              </svg>
              Recording
            </span>
          </div>

          <p class="job-date">
            Created: {{ formatDate(item.created_at) }}
          </p>
        </div>

        <div class="job-actions">
          <!-- Video job actions -->
          <template v-if="item.type === 'video'">
            <template v-if="item.status === 'pending'">
              <router-link
                :to="`/court-setup/${item.id}`"
                class="btn-action btn-primary"
              >
                Setup Court
              </router-link>
            </template>

            <template v-else-if="item.status === 'completed' || item.has_results">
              <router-link
                :to="`/results/${item.id}`"
                class="btn-action btn-success"
              >
                View Results
              </router-link>
            </template>

            <template v-else-if="item.status === 'processing'">
              <ProgressTracker :job-id="item.id" />
            </template>

            <button
              @click="handleDeleteJob(item.id)"
              class="btn-action btn-danger"
              :disabled="item.status === 'processing'"
            >
              Delete
            </button>
          </template>

          <!-- Stream session actions -->
          <template v-else-if="item.type === 'stream'">
            <template v-if="item.status === 'ended' && item.has_results">
              <router-link
                :to="`/stream-results/${item.id}`"
                class="btn-action btn-success"
              >
                View Results
              </router-link>
            </template>

            <template v-else-if="item.status === 'streaming'">
              <router-link
                :to="`/live?resume=${item.id}`"
                class="btn-action btn-primary"
              >
                Resume
              </router-link>
            </template>

            <template v-else-if="item.status === 'setup' || item.status === 'ready'">
              <router-link
                :to="`/live?resume=${item.id}`"
                class="btn-action btn-primary"
              >
                Continue Setup
              </router-link>
            </template>

            <button
              @click="handleDeleteSession(item.id)"
              class="btn-action btn-danger"
              :disabled="item.status === 'streaming'"
            >
              Delete
            </button>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, computed } from 'vue'
import { useJobsStore } from '../stores/jobs'
import { useAuthStore } from '../stores/auth'
import ProgressTracker from '../components/ProgressTracker.vue'

const jobsStore = useJobsStore()
const authStore = useAuthStore()

const isAdmin = computed(() => authStore.user?.is_admin)

const allAnalysis = computed(() => jobsStore.allAnalysis)
const loading = computed(() => jobsStore.loading)

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
</script>

<style scoped>
.dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
}

h1 {
  color: #4ecca3;
}

.header-actions {
  display: flex;
  gap: 1rem;
}

.btn-upload {
  background: #4ecca3;
  color: #1a1a2e;
  padding: 0.75rem 1.5rem;
  border-radius: 8px;
  text-decoration: none;
  font-weight: bold;
  transition: background 0.2s;
}

.btn-upload:hover {
  background: #3db892;
}

.btn-admin {
  background: transparent;
  color: #9b59b6;
  padding: 0.75rem 1.5rem;
  border-radius: 8px;
  border: 2px solid #9b59b6;
  text-decoration: none;
  font-weight: bold;
  transition: all 0.2s;
}

.btn-admin:hover {
  background: #9b59b6;
  color: white;
}

.btn-live {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  background: transparent;
  color: #e74c3c;
  padding: 0.75rem 1.5rem;
  border-radius: 8px;
  border: 2px solid #e74c3c;
  text-decoration: none;
  font-weight: bold;
  transition: all 0.2s;
}

.btn-live:hover {
  background: #e74c3c;
  color: white;
}

.btn-live .btn-icon {
  width: 18px;
  height: 18px;
}

.loading, .empty-state {
  text-align: center;
  padding: 3rem;
  color: #888;
}

.empty-state .btn-primary {
  display: inline-block;
  margin-top: 1rem;
  background: #4ecca3;
  color: #1a1a2e;
  padding: 0.75rem 1.5rem;
  border-radius: 8px;
  text-decoration: none;
  font-weight: bold;
}

.jobs-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 1.5rem;
}

.job-card {
  background: #16213e;
  border-radius: 12px;
  padding: 1.5rem;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
}

.job-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1rem;
}

.job-filename {
  font-weight: bold;
  color: #eee;
  word-break: break-word;
  flex: 1;
  margin-right: 1rem;
}

.status-badge {
  padding: 0.25rem 0.75rem;
  border-radius: 20px;
  font-size: 0.8rem;
  font-weight: bold;
  text-transform: uppercase;
}

.status-badge.pending {
  background: rgba(241, 196, 15, 0.2);
  color: #f1c40f;
}

.status-badge.processing {
  background: rgba(52, 152, 219, 0.2);
  color: #3498db;
}

.status-badge.completed {
  background: rgba(78, 204, 163, 0.2);
  color: #4ecca3;
}

.status-badge.failed {
  background: rgba(231, 76, 60, 0.2);
  color: #e74c3c;
}

.status-badge.cancelled {
  background: rgba(149, 165, 166, 0.2);
  color: #95a5a6;
}

.job-info {
  margin-bottom: 1rem;
}

.progress-bar {
  background: #2a2a4a;
  border-radius: 10px;
  height: 20px;
  position: relative;
  overflow: hidden;
  margin-bottom: 0.5rem;
}

.progress-fill {
  background: linear-gradient(90deg, #4ecca3, #3498db);
  height: 100%;
  transition: width 0.3s;
}

.progress-text {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  font-size: 0.75rem;
  font-weight: bold;
  color: white;
}

.status-message {
  color: #888;
  font-size: 0.9rem;
  margin-bottom: 0.5rem;
}

.error-message {
  color: #e74c3c;
  font-size: 0.9rem;
  margin-bottom: 0.5rem;
}

.job-date {
  color: #666;
  font-size: 0.8rem;
}

.job-actions {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.btn-action {
  padding: 0.5rem 1rem;
  border-radius: 6px;
  text-decoration: none;
  font-size: 0.9rem;
  cursor: pointer;
  border: none;
  transition: all 0.2s;
}

.btn-action.btn-primary {
  background: #4ecca3;
  color: #1a1a2e;
}

.btn-action.btn-success {
  background: #27ae60;
  color: white;
}

.btn-action.btn-danger {
  background: transparent;
  border: 1px solid #e74c3c;
  color: #e74c3c;
}

.btn-action.btn-danger:hover:not(:disabled) {
  background: #e74c3c;
  color: white;
}

.btn-action:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.empty-actions {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  margin-top: 1rem;
}

.or-divider {
  color: #666;
}

.btn-live-alt {
  background: transparent;
  color: #e74c3c;
  padding: 0.75rem 1.5rem;
  border-radius: 8px;
  border: 2px solid #e74c3c;
  text-decoration: none;
  font-weight: bold;
  transition: all 0.2s;
}

.btn-live-alt:hover {
  background: #e74c3c;
  color: white;
}

.job-title-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex: 1;
  min-width: 0;
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
  background: rgba(52, 152, 219, 0.2);
  color: #3498db;
}

.type-badge.stream {
  background: rgba(231, 76, 60, 0.2);
  color: #e74c3c;
}

.stream-stats {
  margin-bottom: 0.5rem;
}

.stat-item {
  color: #888;
  font-size: 0.9rem;
}

.stat-item strong {
  color: #4ecca3;
}

.stream-stats {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  align-items: center;
}

.recording-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.2rem 0.5rem;
  background: rgba(231, 76, 60, 0.15);
  color: #e74c3c;
  border-radius: 4px;
  font-size: 0.8rem;
}

.recording-badge .badge-icon {
  width: 14px;
  height: 14px;
}

.status-badge.setup,
.status-badge.ready {
  background: rgba(155, 89, 182, 0.2);
  color: #9b59b6;
}

.status-badge.streaming {
  background: rgba(231, 76, 60, 0.2);
  color: #e74c3c;
  animation: pulse-status 1.5s infinite;
}

.status-badge.ended {
  background: rgba(78, 204, 163, 0.2);
  color: #4ecca3;
}

@keyframes pulse-status {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}
</style>
