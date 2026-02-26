import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '../api/client'

export const useMimicStore = defineStore('mimic', () => {
  const challenges = ref([])
  const challengesTotal = ref(0)
  const trending = ref([])
  const sessions = ref([])
  const sessionsTotal = ref(0)
  const records = ref([])
  const currentSession = ref(null)
  const loading = ref(false)
  const error = ref(null)

  async function fetchChallenges({ limit = 50, offset = 0 } = {}) {
    loading.value = true
    error.value = null
    try {
      const response = await api.get('/api/v1/mimic/challenges', {
        params: { limit, offset }
      })
      challenges.value = response.data.challenges
      challengesTotal.value = response.data.total
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to fetch challenges'
    } finally {
      loading.value = false
    }
  }

  async function fetchTrending() {
    try {
      const response = await api.get('/api/v1/mimic/challenges/trending')
      trending.value = response.data
    } catch (err) {
      // non-critical
    }
  }

  async function fetchChallenge(challengeId) {
    loading.value = true
    error.value = null
    try {
      const response = await api.get(`/api/v1/mimic/challenges/${challengeId}`)
      return response.data
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to fetch challenge'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function uploadChallenge(formData) {
    loading.value = true
    error.value = null
    try {
      const response = await api.post('/api/v1/mimic/challenges', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      return response.data
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to upload challenge'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function createSession(challengeId) {
    loading.value = true
    error.value = null
    try {
      const response = await api.post('/api/v1/mimic/sessions', {
        challenge_id: challengeId
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
      const response = await api.post(`/api/v1/mimic/sessions/${sessionId}/end`)
      currentSession.value = null
      return response.data
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to end session'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchSessions({ challengeId, limit = 50, offset = 0 } = {}) {
    try {
      const params = { limit, offset }
      if (challengeId) params.challenge_id = challengeId
      const response = await api.get('/api/v1/mimic/sessions', { params })
      sessions.value = response.data.sessions
      sessionsTotal.value = response.data.total
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to fetch sessions'
    }
  }

  async function fetchSession(sessionId) {
    try {
      const response = await api.get(`/api/v1/mimic/sessions/${sessionId}`)
      return response.data
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to fetch session'
      throw err
    }
  }

  async function uploadComparison(challengeId, formData) {
    loading.value = true
    error.value = null
    try {
      const response = await api.post(
        `/api/v1/mimic/challenges/${challengeId}/compare`,
        formData,
        { headers: { 'Content-Type': 'multipart/form-data' } }
      )
      return response.data
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to upload comparison'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function pollSession(sessionId, { interval = 2000, timeout = 300000 } = {}) {
    const start = Date.now()
    while (Date.now() - start < timeout) {
      const session = await fetchSession(sessionId)
      if (session.status === 'ended') return session
      await new Promise(r => setTimeout(r, interval))
    }
    throw new Error('Polling timed out')
  }

  async function fetchRecords() {
    try {
      const response = await api.get('/api/v1/mimic/records')
      records.value = response.data
    } catch (err) {
      // non-critical
    }
  }

  return {
    challenges,
    challengesTotal,
    trending,
    sessions,
    sessionsTotal,
    records,
    currentSession,
    loading,
    error,
    fetchChallenges,
    fetchTrending,
    fetchChallenge,
    uploadChallenge,
    createSession,
    endSession,
    fetchSessions,
    fetchSession,
    uploadComparison,
    pollSession,
    fetchRecords,
  }
})
