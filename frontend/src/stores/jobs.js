import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '../api/client'

export const useJobsStore = defineStore('jobs', () => {
  const jobs = ref([])
  const streamSessions = ref([])
  const allAnalysis = ref([])  // Combined jobs + sessions
  const currentJob = ref(null)
  const loading = ref(false)
  const error = ref(null)

  async function fetchJobs(statusFilter = null) {
    loading.value = true
    error.value = null

    try {
      const params = statusFilter ? { status_filter: statusFilter } : {}
      const response = await api.get('/api/v1/analysis/jobs', { params })
      jobs.value = response.data.jobs.map(j => ({ ...j, type: 'video' }))
      combineAnalysis()
      return jobs.value
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to fetch jobs'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchStreamSessions(statusFilter = null) {
    try {
      const params = statusFilter ? { status_filter: statusFilter } : {}
      const response = await api.get('/api/v1/stream/sessions', { params })
      streamSessions.value = response.data.sessions
      combineAnalysis()
      return streamSessions.value
    } catch (err) {
      console.error('Failed to fetch stream sessions:', err)
      return []
    }
  }

  async function fetchAll(statusFilter = null) {
    loading.value = true
    error.value = null

    try {
      await Promise.all([
        fetchJobs(statusFilter),
        fetchStreamSessions(statusFilter === 'ended' ? 'ended' : null)
      ])
      return allAnalysis.value
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to fetch analysis'
      throw err
    } finally {
      loading.value = false
    }
  }

  function combineAnalysis() {
    // Combine jobs and stream sessions, sort by created_at descending
    const combined = [
      ...jobs.value,
      ...streamSessions.value
    ]
    combined.sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
    allAnalysis.value = combined
  }

  async function uploadVideo(file) {
    loading.value = true
    error.value = null

    try {
      const formData = new FormData()
      formData.append('file', file)

      const response = await api.post('/api/v1/analysis/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })

      const job = response.data
      jobs.value.unshift(job)
      return job
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to upload video'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function getJobStatus(jobId) {
    try {
      const response = await api.get(`/api/v1/analysis/status/${jobId}`)
      return response.data
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to get job status'
      throw err
    }
  }

  async function startAnalysis(jobId, courtBoundary, speedPreset = 'balanced', frameTimestamp = 0.0) {
    loading.value = true
    error.value = null

    try {
      const response = await api.post(`/api/v1/analysis/start/${jobId}`, {
        court_boundary: courtBoundary,
        speed_preset: speedPreset,
        frame_timestamp: frameTimestamp
      })

      // Update job in list
      const index = jobs.value.findIndex(j => j.id === jobId)
      if (index !== -1) {
        jobs.value[index] = { ...jobs.value[index], ...response.data }
      }

      return response.data
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to start analysis'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function cancelJob(jobId) {
    loading.value = true
    error.value = null

    try {
      await api.post(`/api/v1/analysis/${jobId}/cancel`)
      // Update job status in list
      const index = jobs.value.findIndex(j => j.id === jobId)
      if (index !== -1) {
        jobs.value[index] = { ...jobs.value[index], status: 'cancelled', status_message: 'Cancelled by user' }
      }
      combineAnalysis()
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to cancel job'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function deleteJob(jobId) {
    loading.value = true
    error.value = null

    try {
      await api.delete(`/api/v1/analysis/${jobId}`)
      jobs.value = jobs.value.filter(j => j.id !== jobId)
      combineAnalysis()
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to delete job'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function deleteSession(sessionId) {
    loading.value = true
    error.value = null

    try {
      await api.delete(`/api/v1/stream/${sessionId}`)
      streamSessions.value = streamSessions.value.filter(s => s.id !== sessionId)
      combineAnalysis()
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to delete session'
      throw err
    } finally {
      loading.value = false
    }
  }

  function updateJobProgress(jobId, progress, message) {
    const index = jobs.value.findIndex(j => j.id === jobId)
    if (index !== -1) {
      // Use splice to ensure Vue reactivity
      const updatedJob = {
        ...jobs.value[index],
        progress,
        status_message: message
      }
      jobs.value.splice(index, 1, updatedJob)
    }
  }

  function updateJobStatus(jobId, status, hasResults = false) {
    const index = jobs.value.findIndex(j => j.id === jobId)
    if (index !== -1) {
      // Use splice to ensure Vue reactivity
      const updatedJob = {
        ...jobs.value[index],
        status,
        has_results: hasResults || status === 'completed'
      }
      jobs.value.splice(index, 1, updatedJob)
    }
  }

  return {
    jobs,
    streamSessions,
    allAnalysis,
    currentJob,
    loading,
    error,
    fetchJobs,
    fetchStreamSessions,
    fetchAll,
    uploadVideo,
    getJobStatus,
    startAnalysis,
    cancelJob,
    deleteJob,
    deleteSession,
    updateJobProgress,
    updateJobStatus
  }
})
