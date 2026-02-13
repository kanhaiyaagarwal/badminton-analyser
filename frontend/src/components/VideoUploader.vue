<template>
  <div
    class="video-uploader"
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

    <div v-if="!file" class="upload-prompt">
      <svg class="upload-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"/>
      </svg>
      <p class="main-text">Drag & drop video here</p>
      <p class="sub-text">or click to browse</p>
      <p class="formats">MP4, AVI, MOV, MKV, WebM (max 500MB)</p>
    </div>

    <div v-else class="file-preview">
      <svg class="video-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"/>
      </svg>
      <div class="file-info">
        <p class="filename">{{ file.name }}</p>
        <p class="filesize">{{ formatSize(file.size) }}</p>
      </div>
      <button @click.stop="clearFile" class="clear-btn">X</button>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const emit = defineEmits(['file-selected', 'error'])

const fileInput = ref(null)
const file = ref(null)
const isDragover = ref(false)

const allowedTypes = ['video/mp4', 'video/avi', 'video/quicktime', 'video/x-matroska', 'video/webm']
const maxSize = 500 * 1024 * 1024 // 500MB

function triggerInput() {
  if (!file.value) {
    fileInput.value.click()
  }
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

  // Check type
  if (!f.type.startsWith('video/')) {
    emit('error', 'Please select a video file')
    return
  }

  // Check size
  if (f.size > maxSize) {
    emit('error', 'File size exceeds 500MB limit')
    return
  }

  file.value = f
  emit('file-selected', f)
}

function clearFile() {
  file.value = null
  fileInput.value.value = ''
  emit('file-selected', null)
}

function formatSize(bytes) {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}
</script>

<style scoped>
.video-uploader {
  border: 2px dashed var(--border-input);
  border-radius: var(--radius-lg);
  padding: 2rem;
  cursor: pointer;
  transition: all 0.2s;
  text-align: center;
}

.video-uploader:hover,
.video-uploader.dragover {
  border-color: var(--color-primary);
  background: var(--color-primary-light);
}

.hidden-input {
  display: none;
}

.upload-prompt {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
}

.upload-icon {
  width: 48px;
  height: 48px;
  color: var(--color-primary);
}

.main-text {
  color: var(--text-primary);
  font-size: 1.1rem;
}

.sub-text {
  color: var(--text-muted);
  font-size: 0.9rem;
}

.formats {
  color: var(--text-muted);
  font-size: 0.8rem;
  margin-top: 0.5rem;
}

.file-preview {
  display: flex;
  align-items: center;
  gap: 1rem;
  justify-content: center;
}

.video-icon {
  width: 40px;
  height: 40px;
  color: var(--color-primary);
}

.file-info {
  text-align: left;
}

.filename {
  color: var(--text-primary);
  font-weight: bold;
  word-break: break-word;
}

.filesize {
  color: var(--text-muted);
  font-size: 0.85rem;
}

.clear-btn {
  background: var(--color-destructive-light);
  color: var(--color-destructive);
  border: none;
  width: 28px;
  height: 28px;
  border-radius: var(--radius-full);
  cursor: pointer;
  font-weight: 600;
  transition: all 0.2s;
}

.clear-btn:hover {
  background: var(--color-destructive);
  color: white;
}
</style>
