import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '../api/client'

export const useWorkoutStore = defineStore('workout', () => {
  // State
  const profile = ref(null)
  const todayWorkout = ref(null)
  const weekView = ref(null)
  const progressStats = ref(null)
  const exercises = ref([])
  const exercisesTotal = ref(0)
  const currentExercise = ref(null)
  const onboardingData = ref({})
  const loading = ref(false)
  const error = ref(null)

  // M1: Session state
  const activeSession = ref(null)      // Current AgentResponse { view, data, coach_says, available_actions, progress }
  const sessionId = ref(null)
  const sessionSummary = ref(null)

  // Chat state (for coach companion)
  const chatConversationId = ref(null)
  const chatContext = ref(null)  // current chat context: onboarding | pre_workout | rest | post_workout

  // Computed
  const isOnboarded = computed(() => profile.value?.onboarding_completed === true)

  // Actions
  async function fetchProfile() {
    try {
      const res = await api.get('/api/v1/workout/profile')
      profile.value = res.data
      return res.data
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to fetch profile'
      throw err
    }
  }

  async function submitOnboarding(data) {
    loading.value = true
    error.value = null
    try {
      const res = await api.post('/api/v1/workout/onboarding', data)
      // Refresh profile after onboarding
      await fetchProfile()
      return res.data
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to save onboarding'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchTodayWorkout() {
    try {
      const res = await api.get('/api/v1/workout/today')
      todayWorkout.value = res.data
      return res.data
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to fetch today workout'
      throw err
    }
  }

  async function fetchWeekView() {
    try {
      const res = await api.get('/api/v1/workout/week')
      weekView.value = res.data
      return res.data
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to fetch week view'
      throw err
    }
  }

  async function fetchProgressStats() {
    try {
      const res = await api.get('/api/v1/workout/progress/stats')
      progressStats.value = res.data
      return res.data
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to fetch progress'
      throw err
    }
  }

  async function fetchWorkoutHistory(params = {}) {
    try {
      const res = await api.get('/api/v1/workout/history', { params })
      return res.data
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to fetch history'
      throw err
    }
  }

  async function updateMeasurements(data) {
    try {
      const res = await api.put('/api/v1/workout/profile/measurements', data)
      // Update profile cache
      if (profile.value) {
        Object.assign(profile.value, res.data)
      }
      return res.data
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to update measurements'
      throw err
    }
  }

  async function fetchGoals() {
    try {
      const res = await api.get('/api/v1/workout/goals')
      return res.data
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to fetch goals'
      throw err
    }
  }

  async function fetchEquipment() {
    try {
      const res = await api.get('/api/v1/workout/equipment')
      return res.data
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to fetch equipment'
      throw err
    }
  }

  async function updateEquipment(equipment, trainLocation) {
    try {
      const res = await api.put('/api/v1/workout/equipment', {
        equipment,
        train_location: trainLocation,
      })
      return res.data
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to update equipment'
      throw err
    }
  }

  async function fetchExercises(params = {}) {
    try {
      const res = await api.get('/api/v1/workout/exercises', { params })
      exercises.value = res.data
      exercisesTotal.value = res.data.length
      return res.data
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to fetch exercises'
      throw err
    }
  }

  async function fetchExercise(slug) {
    try {
      const res = await api.get(`/api/v1/workout/exercises/${slug}`)
      currentExercise.value = res.data
      return res.data
    } catch (err) {
      error.value = err.response?.data?.detail || 'Exercise not found'
      throw err
    }
  }

  async function createQuickStart(exerciseSlugs) {
    loading.value = true
    try {
      const res = await api.post('/api/v1/workout/quick-start', {
        exercise_slugs: exerciseSlugs
      })
      return res.data
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to create session'
      throw err
    } finally {
      loading.value = false
    }
  }

  // M1: Session actions

  async function startSession(params = {}) {
    loading.value = true
    error.value = null
    try {
      const res = await api.post('/api/v1/workout/sessions/start', params)
      activeSession.value = res.data
      sessionId.value = res.data.data?.session_id
      return res.data
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to start session'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function sendAction(sid, action, params = {}) {
    loading.value = true
    error.value = null
    try {
      const res = await api.post(`/api/v1/workout/sessions/${sid}/action`, { action, params })
      activeSession.value = res.data
      if (res.data.view === 'summary') {
        sessionSummary.value = res.data.data
      }
      // Update sessionId from data if present
      if (res.data.data?.session_id) {
        sessionId.value = res.data.data.session_id
      }
      return res.data
    } catch (err) {
      error.value = err.response?.data?.detail || 'Action failed'
      throw err
    } finally {
      loading.value = false
    }
  }

  function clearSession() {
    activeSession.value = null
    sessionId.value = null
    sessionSummary.value = null
    chatConversationId.value = null
    chatContext.value = null
  }

  async function sendChatMessage(message, context, sid = null) {
    try {
      const res = await api.post('/api/v1/workout/chat', {
        message,
        context,
        session_id: sid || sessionId.value,
        conversation_id: chatConversationId.value,
      })
      if (res.data.conversation_id) {
        chatConversationId.value = res.data.conversation_id
      }
      chatContext.value = context
      return res.data
    } catch (err) {
      error.value = err.response?.data?.detail || 'Chat failed'
      throw err
    }
  }

  return {
    profile,
    todayWorkout,
    weekView,
    progressStats,
    exercises,
    exercisesTotal,
    currentExercise,
    onboardingData,
    loading,
    error,
    isOnboarded,
    activeSession,
    sessionId,
    sessionSummary,
    chatConversationId,
    chatContext,
    fetchProfile,
    submitOnboarding,
    fetchTodayWorkout,
    fetchWeekView,
    fetchProgressStats,
    fetchWorkoutHistory,
    updateMeasurements,
    fetchGoals,
    fetchEquipment,
    updateEquipment,
    fetchExercises,
    fetchExercise,
    createQuickStart,
    startSession,
    sendAction,
    clearSession,
    sendChatMessage,
  }
})
