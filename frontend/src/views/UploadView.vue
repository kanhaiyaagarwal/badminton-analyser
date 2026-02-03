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

  // 500MB limit
  if (file.size > 500 * 1024 * 1024) {
    error.value = 'File too large. Maximum size is 500MB.'
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
  color: #4ecca3;
  margin-bottom: 0.5rem;
}

.subtitle {
  color: #888;
  margin-bottom: 2rem;
}

.upload-area {
  background: #16213e;
  border-radius: 12px;
  padding: 1rem;
  transition: all 0.2s;
}

.upload-area.dragover {
  border-color: #4ecca3;
  background: rgba(78, 204, 163, 0.1);
}

.file-input {
  display: none;
}

.drop-zone {
  border: 2px dashed #3a3a5a;
  border-radius: 8px;
  padding: 3rem;
  cursor: pointer;
  transition: all 0.2s;
}

.drop-zone:hover {
  border-color: #4ecca3;
}

.drop-content {
  text-align: center;
}

.upload-icon {
  width: 64px;
  height: 64px;
  color: #4ecca3;
  margin-bottom: 1rem;
}

.drop-content p {
  color: #888;
  margin-bottom: 0.5rem;
}

.or {
  font-size: 0.9rem;
}

.btn-browse {
  display: inline-block;
  background: #4ecca3;
  color: #1a1a2e;
  padding: 0.5rem 1.5rem;
  border-radius: 6px;
  font-weight: bold;
  margin: 0.5rem 0;
}

.formats {
  font-size: 0.8rem;
  color: #666;
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
  color: #4ecca3;
}

.file-info {
  flex: 1;
}

.filename {
  color: #eee;
  font-weight: bold;
  word-break: break-word;
}

.filesize {
  color: #888;
  font-size: 0.9rem;
}

.btn-clear {
  background: transparent;
  border: 1px solid #e74c3c;
  color: #e74c3c;
  padding: 0.5rem 1rem;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-clear:hover {
  background: #e74c3c;
  color: white;
}

.error-message {
  background: rgba(231, 76, 60, 0.2);
  color: #e74c3c;
  padding: 1rem;
  border-radius: 8px;
  margin-top: 1rem;
}

.upload-progress {
  margin-top: 1.5rem;
  text-align: center;
}

.upload-progress p {
  color: #888;
  margin-bottom: 0.5rem;
}

.progress-bar {
  background: #2a2a4a;
  border-radius: 10px;
  height: 10px;
  overflow: hidden;
}

.progress-fill {
  background: linear-gradient(90deg, #4ecca3, #3498db);
  height: 100%;
  transition: width 0.3s;
}

.btn-upload {
  display: block;
  width: 100%;
  margin-top: 1.5rem;
  padding: 1rem;
  background: #4ecca3;
  color: #1a1a2e;
  border: none;
  border-radius: 8px;
  font-size: 1rem;
  font-weight: bold;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-upload:hover {
  background: #3db892;
}
</style>
