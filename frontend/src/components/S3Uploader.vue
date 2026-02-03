<template>
  <div class="s3-uploader">
    <!-- File Selection -->
    <div
      v-if="!file && !uploading"
      class="drop-zone"
      :class="{ dragover: isDragover }"
      @dragover.prevent="isDragover = true"
      @dragleave.prevent="isDragover = false"
      @drop.prevent="handleDrop"
      @click="triggerInput"
    >
      <input
        ref="fileInput"
        type="file"
        accept="video/*"
        @change="handleFileSelect"
        class="hidden-input"
      />

      <svg class="upload-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"/>
      </svg>
      <p class="main-text">Drag & drop video here</p>
      <p class="sub-text">or click to browse</p>
      <p class="formats">MP4, AVI, MOV, MKV, WebM (max 500MB)</p>

      <div v-if="s3Enabled" class="s3-badge">
        <svg class="cloud-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 15a4 4 0 004 4h9a5 5 0 10-.1-9.999 5.002 5.002 0 10-9.78 2.096A4.001 4.001 0 003 15z"/>
        </svg>
        <span>Cloud Upload Enabled</span>
      </div>
    </div>

    <!-- File Selected (Ready to upload) -->
    <div v-else-if="file && !uploading" class="file-ready">
      <div class="file-preview">
        <svg class="video-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"/>
        </svg>
        <div class="file-info">
          <p class="filename">{{ file.name }}</p>
          <p class="filesize">{{ formatSize(file.size) }}</p>
        </div>
        <button @click="clearFile" class="clear-btn">X</button>
      </div>

      <button @click="startUpload" class="upload-btn">
        <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"/>
        </svg>
        Upload to {{ s3Enabled ? 'Cloud' : 'Server' }}
      </button>
    </div>

    <!-- Uploading Progress -->
    <div v-else-if="uploading" class="upload-progress">
      <div class="progress-header">
        <span class="status-text">{{ statusText }}</span>
        <span class="progress-percent">{{ progress.toFixed(0) }}%</span>
      </div>

      <div class="progress-bar-container">
        <div class="progress-bar" :style="{ width: `${progress}%` }"></div>
      </div>

      <div class="progress-details">
        <span v-if="uploadSpeed">{{ uploadSpeed }}</span>
        <span v-if="remainingTime">{{ remainingTime }} remaining</span>
      </div>

      <button v-if="!completed" @click="cancelUpload" class="cancel-btn">Cancel</button>
    </div>

    <!-- Error Message -->
    <div v-if="error" class="error-message">
      {{ error }}
      <button @click="error = ''" class="dismiss-btn">X</button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import axios from 'axios'
import api from '../api/client'

const emit = defineEmits(['upload-complete', 'upload-error', 'upload-progress'])

const fileInput = ref(null)
const file = ref(null)
const isDragover = ref(false)
const uploading = ref(false)
const progress = ref(0)
const completed = ref(false)
const error = ref('')
const statusText = ref('Preparing upload...')
const uploadSpeed = ref('')
const remainingTime = ref('')
const s3Enabled = ref(false)
const abortController = ref(null)

const maxSize = 500 * 1024 * 1024 // 500MB

onMounted(async () => {
  // Check if S3 upload is available
  try {
    const response = await api.get('/api/v1/upload/status')
    s3Enabled.value = response.data.s3_enabled
  } catch (e) {
    s3Enabled.value = false
  }
})

function triggerInput() {
  fileInput.value.click()
}

function handleFileSelect(event) {
  const selected = event.target.files[0]
  validateAndSetFile(selected)
}

function handleDrop(event) {
  isDragover.value = false
  const dropped = event.dataTransfer.files[0]
  validateAndSetFile(dropped)
}

function validateAndSetFile(f) {
  if (!f) return

  if (!f.type.startsWith('video/')) {
    error.value = 'Please select a video file'
    return
  }

  if (f.size > maxSize) {
    error.value = 'File size exceeds 500MB limit'
    return
  }

  file.value = f
  error.value = ''
}

function clearFile() {
  file.value = null
  fileInput.value.value = ''
  progress.value = 0
  completed.value = false
  error.value = ''
}

async function startUpload() {
  if (!file.value) return

  uploading.value = true
  progress.value = 0
  completed.value = false
  error.value = ''
  abortController.value = new AbortController()

  try {
    if (s3Enabled.value) {
      await uploadToS3()
    } else {
      await uploadToServer()
    }
  } catch (e) {
    if (e.name === 'CanceledError' || e.message === 'canceled') {
      statusText.value = 'Upload cancelled'
    } else {
      error.value = e.response?.data?.detail || e.message || 'Upload failed'
      emit('upload-error', error.value)
    }
    uploading.value = false
  }
}

async function uploadToS3() {
  const f = file.value

  // Step 1: Get pre-signed URL
  statusText.value = 'Getting upload URL...'

  const response = await api.post('/api/v1/upload/request', {
    filename: f.name,
    content_type: f.type || 'video/mp4',
    size: f.size
  })

  const { upload_url, job_id, use_multipart } = response.data

  if (use_multipart) {
    await uploadMultipart(f)
    return
  }

  // Step 2: Upload directly to S3
  statusText.value = 'Uploading to cloud...'
  const startTime = Date.now()
  let lastLoaded = 0

  await axios.put(upload_url, f, {
    headers: {
      'Content-Type': f.type || 'video/mp4'
    },
    signal: abortController.value.signal,
    onUploadProgress: (e) => {
      progress.value = (e.loaded / e.total) * 100
      emit('upload-progress', progress.value)

      // Calculate speed
      const elapsed = (Date.now() - startTime) / 1000
      if (elapsed > 0) {
        const bytesPerSec = e.loaded / elapsed
        uploadSpeed.value = formatSpeed(bytesPerSec)

        const remaining = (e.total - e.loaded) / bytesPerSec
        remainingTime.value = formatTime(remaining)
      }
    }
  })

  // Step 3: Confirm upload
  statusText.value = 'Confirming upload...'
  await api.post(`/api/v1/upload/confirm/${job_id}`)

  // Success
  statusText.value = 'Upload complete!'
  completed.value = true
  progress.value = 100

  emit('upload-complete', { job_id, type: 's3' })
}

async function uploadMultipart(f) {
  // Initiate multipart upload
  statusText.value = 'Initiating multipart upload...'

  const initResponse = await api.post('/api/v1/upload/multipart/init', {
    filename: f.name,
    content_type: f.type || 'video/mp4',
    size: f.size
  })

  const { upload_id, file_key, job_id, part_urls, part_size } = initResponse.data

  // Upload parts
  statusText.value = 'Uploading parts...'
  const parts = []
  const totalParts = part_urls.length
  let uploadedParts = 0

  for (const { part_number, upload_url } of part_urls) {
    const start = (part_number - 1) * part_size
    const end = Math.min(start + part_size, f.size)
    const chunk = f.slice(start, end)

    const response = await axios.put(upload_url, chunk, {
      signal: abortController.value.signal
    })

    parts.push({
      PartNumber: part_number,
      ETag: response.headers.etag
    })

    uploadedParts++
    progress.value = (uploadedParts / totalParts) * 100
    emit('upload-progress', progress.value)
  }

  // Complete multipart upload
  statusText.value = 'Completing upload...'
  await api.post('/api/v1/upload/multipart/complete', {
    file_key,
    upload_id,
    parts
  })

  // Confirm upload
  await api.post(`/api/v1/upload/confirm/${job_id}`)

  statusText.value = 'Upload complete!'
  completed.value = true
  progress.value = 100

  emit('upload-complete', { job_id, type: 's3-multipart' })
}

async function uploadToServer() {
  // Standard server upload (existing flow)
  const f = file.value
  const formData = new FormData()
  formData.append('file', f)

  statusText.value = 'Uploading to server...'
  const startTime = Date.now()

  const response = await api.post('/api/v1/analysis/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    },
    signal: abortController.value.signal,
    onUploadProgress: (e) => {
      progress.value = (e.loaded / e.total) * 100
      emit('upload-progress', progress.value)

      const elapsed = (Date.now() - startTime) / 1000
      if (elapsed > 0) {
        const bytesPerSec = e.loaded / elapsed
        uploadSpeed.value = formatSpeed(bytesPerSec)

        const remaining = (e.total - e.loaded) / bytesPerSec
        remainingTime.value = formatTime(remaining)
      }
    }
  })

  statusText.value = 'Upload complete!'
  completed.value = true
  progress.value = 100

  emit('upload-complete', { job_id: response.data.job_id, type: 'server' })
}

function cancelUpload() {
  if (abortController.value) {
    abortController.value.abort()
  }
  uploading.value = false
  progress.value = 0
}

function formatSize(bytes) {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

function formatSpeed(bytesPerSec) {
  if (bytesPerSec < 1024) return bytesPerSec.toFixed(0) + ' B/s'
  if (bytesPerSec < 1024 * 1024) return (bytesPerSec / 1024).toFixed(1) + ' KB/s'
  return (bytesPerSec / (1024 * 1024)).toFixed(1) + ' MB/s'
}

function formatTime(seconds) {
  if (seconds < 60) return Math.ceil(seconds) + 's'
  const mins = Math.floor(seconds / 60)
  const secs = Math.ceil(seconds % 60)
  return `${mins}m ${secs}s`
}
</script>

<style scoped>
.s3-uploader {
  width: 100%;
}

.drop-zone {
  border: 2px dashed #3a3a5a;
  border-radius: 12px;
  padding: 2rem;
  cursor: pointer;
  transition: all 0.2s;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
}

.drop-zone:hover,
.drop-zone.dragover {
  border-color: #4ecca3;
  background: rgba(78, 204, 163, 0.1);
}

.hidden-input {
  display: none;
}

.upload-icon {
  width: 48px;
  height: 48px;
  color: #4ecca3;
}

.main-text {
  color: #eee;
  font-size: 1.1rem;
  margin: 0;
}

.sub-text {
  color: #888;
  font-size: 0.9rem;
  margin: 0;
}

.formats {
  color: #666;
  font-size: 0.8rem;
  margin-top: 0.5rem;
}

.s3-badge {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-top: 1rem;
  padding: 0.5rem 1rem;
  background: rgba(78, 204, 163, 0.1);
  border-radius: 20px;
  color: #4ecca3;
  font-size: 0.85rem;
}

.cloud-icon {
  width: 18px;
  height: 18px;
}

.file-ready {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.file-preview {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem;
  background: #16213e;
  border-radius: 8px;
}

.video-icon {
  width: 40px;
  height: 40px;
  color: #4ecca3;
}

.file-info {
  flex: 1;
  text-align: left;
}

.filename {
  color: #eee;
  font-weight: bold;
  word-break: break-word;
  margin: 0;
}

.filesize {
  color: #888;
  font-size: 0.85rem;
  margin: 0;
}

.clear-btn {
  background: rgba(231, 76, 60, 0.2);
  color: #e74c3c;
  border: none;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  cursor: pointer;
  font-weight: bold;
}

.clear-btn:hover {
  background: #e74c3c;
  color: white;
}

.upload-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  background: #4ecca3;
  color: #1a1a2e;
  border: none;
  padding: 0.75rem 1.5rem;
  border-radius: 8px;
  font-weight: bold;
  cursor: pointer;
  transition: background 0.2s;
}

.upload-btn:hover {
  background: #3db892;
}

.btn-icon {
  width: 20px;
  height: 20px;
}

.upload-progress {
  padding: 1.5rem;
  background: #16213e;
  border-radius: 12px;
}

.progress-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 0.75rem;
}

.status-text {
  color: #eee;
}

.progress-percent {
  color: #4ecca3;
  font-weight: bold;
}

.progress-bar-container {
  height: 8px;
  background: #0f0f1a;
  border-radius: 4px;
  overflow: hidden;
}

.progress-bar {
  height: 100%;
  background: linear-gradient(90deg, #4ecca3, #3db892);
  transition: width 0.3s ease;
}

.progress-details {
  display: flex;
  justify-content: space-between;
  margin-top: 0.5rem;
  font-size: 0.85rem;
  color: #888;
}

.cancel-btn {
  margin-top: 1rem;
  background: rgba(231, 76, 60, 0.2);
  color: #e74c3c;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
}

.cancel-btn:hover {
  background: #e74c3c;
  color: white;
}

.error-message {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 1rem;
  padding: 0.75rem 1rem;
  background: rgba(231, 76, 60, 0.1);
  border: 1px solid rgba(231, 76, 60, 0.3);
  border-radius: 8px;
  color: #e74c3c;
}

.dismiss-btn {
  background: none;
  border: none;
  color: #e74c3c;
  cursor: pointer;
  font-weight: bold;
}
</style>
