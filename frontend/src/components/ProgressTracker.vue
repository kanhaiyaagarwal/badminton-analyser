<template>
  <div class="progress-tracker">
    <div class="status-indicator" :class="{ connected: isConnected }">
      <span class="dot"></span>
      {{ isConnected ? 'Live' : 'Connecting...' }}
    </div>

    <div class="progress-info">
      <div class="progress-bar">
        <div class="progress-fill" :style="{ width: progress + '%' }"></div>
      </div>
      <div class="progress-details">
        <span class="percentage">{{ Math.round(progress) }}%</span>
        <span class="message">{{ message }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { createProgressWebSocket } from '../api/client'
import { useJobsStore } from '../stores/jobs'

const props = defineProps({
  jobId: {
    type: Number,
    required: true
  }
})

const jobsStore = useJobsStore()

const progress = ref(0)
const message = ref('Connecting...')
const isConnected = ref(false)
let wsConnection = null
let pollInterval = null

onMounted(() => {
  connectWebSocket()
  // Start polling as fallback for progress updates
  startPolling()
})

onUnmounted(() => {
  if (wsConnection) {
    wsConnection.close()
  }
  if (pollInterval) {
    clearInterval(pollInterval)
  }
})

function startPolling() {
  // Poll every 5 seconds as fallback
  pollInterval = setInterval(async () => {
    try {
      const status = await jobsStore.getJobStatus(props.jobId)
      if (status.progress > progress.value) {
        progress.value = status.progress
        message.value = status.status_message || message.value
      }
      if (status.status === 'completed') {
        progress.value = 100
        message.value = 'Analysis complete!'
        jobsStore.updateJobStatus(props.jobId, 'completed', true)
        clearInterval(pollInterval)
        // Refresh jobs list to get full updated data
        await jobsStore.fetchJobs()
      } else if (status.status === 'failed') {
        message.value = status.error_message || 'Analysis failed'
        jobsStore.updateJobStatus(props.jobId, 'failed')
        clearInterval(pollInterval)
      }
    } catch (e) {
      console.error('Polling error:', e)
    }
  }, 5000)
}

function connectWebSocket() {
  wsConnection = createProgressWebSocket(
    props.jobId,
    handleMessage,
    handleError
  )

  wsConnection.ws.onopen = () => {
    isConnected.value = true
    message.value = 'Processing...'
  }

  wsConnection.ws.onclose = () => {
    isConnected.value = false
  }
}

function handleMessage(data) {
  if (data.type === 'progress') {
    progress.value = data.progress
    message.value = data.message
    jobsStore.updateJobProgress(props.jobId, data.progress, data.message)
  } else if (data.type === 'complete') {
    progress.value = 100
    message.value = data.message
    jobsStore.updateJobStatus(props.jobId, 'completed', true)
    if (pollInterval) clearInterval(pollInterval)
    // Refresh jobs to get updated data
    jobsStore.fetchJobs()
  } else if (data.type === 'error') {
    message.value = data.message
    jobsStore.updateJobStatus(props.jobId, 'failed')
    if (pollInterval) clearInterval(pollInterval)
  }
}

function handleError(error) {
  console.error('WebSocket error:', error)
  isConnected.value = false
  message.value = 'Processing... (polling for updates)'
}
</script>

<style scoped>
.progress-tracker {
  width: 100%;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.75rem;
  color: #888;
  margin-bottom: 0.5rem;
}

.status-indicator.connected {
  color: #4ecca3;
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #888;
}

.status-indicator.connected .dot {
  background: #4ecca3;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.progress-info {
  width: 100%;
}

.progress-bar {
  background: #2a2a4a;
  border-radius: 10px;
  height: 8px;
  overflow: hidden;
  margin-bottom: 0.25rem;
}

.progress-fill {
  background: linear-gradient(90deg, #4ecca3, #3498db);
  height: 100%;
  transition: width 0.3s;
}

.progress-details {
  display: flex;
  justify-content: space-between;
  font-size: 0.75rem;
}

.percentage {
  color: #4ecca3;
  font-weight: bold;
}

.message {
  color: #888;
  text-overflow: ellipsis;
  overflow: hidden;
  white-space: nowrap;
  max-width: 150px;
}
</style>
