import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '../api/client'

export const useChallengesStore = defineStore('challenges', () => {
  const sessions = ref([])
  const currentSession = ref(null)
  const personalRecords = ref({})
  const stats = ref({})
  const enabledTypes = ref([])
  const leaderboard = ref(null)
  const loading = ref(false)
  const error = ref(null)

  async function createSession(challengeType) {
    loading.value = true
    error.value = null
    try {
      const response = await api.post('/api/v1/challenges/sessions', {
        challenge_type: challengeType
      })
      currentSession.value = response.data
      return response.data
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to create session'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function endSession(sessionId) {
    loading.value = true
    error.value = null
    try {
      const response = await api.post(`/api/v1/challenges/sessions/${sessionId}/end`)
      currentSession.value = null
      return response.data
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to end session'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchSessions() {
    loading.value = true
    try {
      const response = await api.get('/api/v1/challenges/sessions')
      sessions.value = response.data
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to fetch sessions'
    } finally {
      loading.value = false
    }
  }

  async function fetchRecords() {
    try {
      const response = await api.get('/api/v1/challenges/records')
      personalRecords.value = response.data
    } catch (err) {
      // non-critical
    }
  }

  async function fetchStats() {
    try {
      const response = await api.get('/api/v1/challenges/stats')
      stats.value = response.data
    } catch (err) {
      // non-critical
    }
  }

  async function fetchEnabledChallenges() {
    try {
      const response = await api.get('/api/v1/challenges/enabled')
      enabledTypes.value = response.data
    } catch (err) {
      enabledTypes.value = ['pushup']
    }
  }

  async function fetchLeaderboard(challengeType = 'pushup') {
    try {
      const response = await api.get('/api/v1/challenges/leaderboard', {
        params: { challenge_type: challengeType }
      })
      leaderboard.value = response.data
    } catch (err) {
      // non-critical
    }
  }

  async function startRecording(sessionId) {
    const response = await api.post(`/api/v1/challenges/sessions/${sessionId}/recording/start`)
    return response.data
  }

  async function stopRecording(sessionId) {
    const response = await api.post(`/api/v1/challenges/sessions/${sessionId}/recording/stop`)
    return response.data
  }

  return {
    sessions,
    currentSession,
    personalRecords,
    stats,
    enabledTypes,
    leaderboard,
    loading,
    error,
    createSession,
    endSession,
    fetchSessions,
    fetchRecords,
    fetchStats,
    fetchEnabledChallenges,
    fetchLeaderboard,
    startRecording,
    stopRecording,
  }
})
