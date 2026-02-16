<template>
  <div class="upload-view">
    <h1>Upload Video</h1>
    <p class="subtitle">Upload a badminton video for analysis</p>

    <div class="upload-area" :class="{ dragover: isDragover }">
      <input
        ref="fileInput"
        type="file"
        accept="video/*"
        @change="handleFileSelect"
        class="file-input"
      />

      <div
        class="drop-zone"
        @click="triggerFileInput"
        @dragover.prevent="isDragover = true"
        @dragleave.prevent="isDragover = false"
        @drop.prevent="handleDrop"
      >
        <div v-if="!selectedFile" class="drop-content">
          <svg class="upload-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"/>
          </svg>
          <p>Drag and drop video here</p>
          <p class="or">or</p>
          <span class="btn-browse">Browse Files</span>
          <p class="formats">Supported: MP4, AVI, MOV, MKV, WebM</p>
        </div>

        <div v-else class="selected-file">
          <svg class="file-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"/>
          </svg>
          <div class="file-info">
            <p class="filename">{{ selectedFile.name }}</p>
            <p class="filesize">{{ formatFileSize(selectedFile.size) }}</p>
          </div>
          <button @click.stop="clearFile" class="btn-clear">Clear</button>
        </div>
      </div>
    </div>

    <div v-if="error" class="error-message">{{ error }}</div>

    <div v-if="uploading" class="upload-progress">
      <p>Uploading...</p>
      <div class="progress-bar">
        <div class="progress-fill" :style="{ width: uploadProgress + '%' }"></div>
      </div>
    </div>

    <button
      v-if="selectedFile && !uploading"
      @click="uploadFile"
      class="btn-upload"
    >
      Upload and Continue
    </button>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useJobsStore } from '../stores/jobs'

const router = useRouter()
const jobsStore = useJobsStore()

const fileInput = ref(null)
const selectedFile = ref(null)
const isDragover = ref(false)
const uploading = ref(false)
const uploadProgress = ref(0)
const error = ref('')

const allowedExtensions = ['.mp4', '.avi', '.mov', '.mkv', '.webm']

function triggerFileInput() {
  fileInput.value.click()
}

function handleFileSelect(event) {
  const file = event.target.files[0]
  validateAndSetFile(file)
}

function handleDrop(event) {
  isDragover.value = false
  const file = event.dataTransfer.files[0]
  validateAndSetFile(file)
}

function validateAndSetFile(file) {
  error.value = ''

  if (!file) return

  const ext = '.' + file.name.split('.').pop().toLowerCase()
  if (!allowedExtensions.includes(ext)) {
    error.value = `Invalid file type. Allowed: ${allowedExtensions.join(', ')}`
    return
  }

  // 100MB limit
  if (file.size > 100 * 1024 * 1024) {
    error.value = 'File too large. Maximum size is 100MB.'
    return
  }

  selectedFile.value = file
}

function clearFile() {
  selectedFile.value = null
  fileInput.value.value = ''
  error.value = ''
}

function formatFileSize(bytes) {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

async function uploadFile() {
  if (!selectedFile.value) return

  uploading.value = true
  uploadProgress.value = 0
  error.value = ''

  try {
    const job = await jobsStore.uploadVideo(selectedFile.value)
    router.push(`/court-setup/${job.id}`)
  } catch (err) {
    error.value = err.response?.data?.detail || 'Upload failed. Please try again.'
  } finally {
    uploading.value = false
  }
}
</script>

<style scoped>
.upload-view {
  max-width: 600px;
  margin: 0 auto;
}

h1 {
  color: var(--color-primary);
  margin-bottom: 0.5rem;
}

.subtitle {
  color: var(--text-muted);
  margin-bottom: 2rem;
}

.upload-area {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 1rem;
  transition: all 0.2s;
  box-shadow: var(--shadow-md);
}

.upload-area.dragover {
  border-color: var(--color-primary);
  background: var(--color-primary-light);
}

.file-input {
  display: none;
}

.drop-zone {
  border: 2px dashed var(--border-input);
  border-radius: var(--radius-md);
  padding: 3rem;
  cursor: pointer;
  transition: all 0.2s;
}

.drop-zone:hover {
  border-color: var(--color-primary);
}

.drop-content {
  text-align: center;
}

.upload-icon {
  width: 64px;
  height: 64px;
  color: var(--color-primary);
  margin-bottom: 1rem;
}

.drop-content p {
  color: var(--text-muted);
  margin-bottom: 0.5rem;
}

.or {
  font-size: 0.9rem;
}

.btn-browse {
  display: inline-block;
  background: var(--color-primary);
  color: var(--text-on-primary);
  padding: 0.5rem 1.5rem;
  border-radius: var(--radius-sm);
  font-weight: bold;
  margin: 0.5rem 0;
}

.formats {
  font-size: 0.8rem;
  color: var(--text-muted);
  margin-top: 1rem;
}

.selected-file {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.file-icon {
  width: 48px;
  height: 48px;
  color: var(--color-primary);
}

.file-info {
  flex: 1;
}

.filename {
  color: var(--text-primary);
  font-weight: bold;
  word-break: break-word;
}

.filesize {
  color: var(--text-muted);
  font-size: 0.9rem;
}

.btn-clear {
  background: transparent;
  border: 1px solid var(--color-destructive);
  color: var(--color-destructive);
  padding: 0.5rem 1rem;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all 0.2s;
}

.btn-clear:hover {
  background: var(--color-destructive);
  color: white;
}

.error-message {
  background: var(--color-destructive-light);
  color: var(--color-destructive);
  padding: 1rem;
  border-radius: var(--radius-md);
  margin-top: 1rem;
}

.upload-progress {
  margin-top: 1.5rem;
  text-align: center;
}

.upload-progress p {
  color: var(--text-muted);
  margin-bottom: 0.5rem;
}

.progress-bar {
  background: var(--border-color);
  border-radius: var(--radius-full);
  height: 10px;
  overflow: hidden;
}

.progress-fill {
  background: var(--gradient-primary);
  height: 100%;
  transition: width 0.3s;
}

.btn-upload {
  display: block;
  width: 100%;
  margin-top: 1.5rem;
  padding: 1rem;
  background: var(--gradient-primary);
  color: var(--text-on-primary);
  border: none;
  border-radius: var(--radius-md);
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-upload:hover {
  background: var(--color-primary-hover);
}
</style>
