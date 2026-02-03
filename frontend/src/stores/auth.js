import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '../api/client'

// Helper to decode JWT and get expiration
function getTokenExpiration(token) {
  if (!token) return null
  try {
    const payload = JSON.parse(atob(token.split('.')[1]))
    return payload.exp ? payload.exp * 1000 : null // Convert to milliseconds
  } catch {
    return null
  }
}

export const useAuthStore = defineStore('auth', () => {
  const user = ref(null)
  const accessToken = ref(localStorage.getItem('accessToken'))
  const refreshToken = ref(localStorage.getItem('refreshToken'))

  const isAuthenticated = computed(() => !!accessToken.value)

  // Check if token is expired or about to expire (within 2 minutes)
  const isTokenExpiringSoon = computed(() => {
    const exp = getTokenExpiration(accessToken.value)
    if (!exp) return true
    return Date.now() > exp - 120000 // 2 minutes buffer
  })

  async function login(email, password) {
    const formData = new URLSearchParams()
    formData.append('username', email)
    formData.append('password', password)

    const response = await api.post('/api/v1/auth/login', formData, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
    })

    setTokens(response.data.access_token, response.data.refresh_token)
    await fetchUser()

    return response.data
  }

  async function signup(email, username, password) {
    const response = await api.post('/api/v1/auth/signup', {
      email,
      username,
      password
    })
    return response.data
  }

  async function fetchUser() {
    if (!accessToken.value) return null

    try {
      const response = await api.get('/api/v1/auth/me')
      user.value = response.data
      return user.value
    } catch (error) {
      if (error.response?.status === 401) {
        logout()
      }
      throw error
    }
  }

  async function refreshAccessToken() {
    if (!refreshToken.value) {
      logout()
      return false
    }

    try {
      const response = await api.post('/api/v1/auth/refresh', null, {
        params: { refresh_token: refreshToken.value }
      })

      setTokens(response.data.access_token, response.data.refresh_token)
      return true
    } catch (error) {
      logout()
      return false
    }
  }

  // Ensure we have a valid token, refreshing if needed
  // Use this before WebSocket connections
  async function ensureValidToken() {
    if (!accessToken.value) return false

    if (isTokenExpiringSoon.value) {
      console.log('Token expiring soon, refreshing...')
      return await refreshAccessToken()
    }
    return true
  }

  function setTokens(access, refresh) {
    accessToken.value = access
    refreshToken.value = refresh

    if (access) {
      localStorage.setItem('accessToken', access)
    } else {
      localStorage.removeItem('accessToken')
    }

    if (refresh) {
      localStorage.setItem('refreshToken', refresh)
    } else {
      localStorage.removeItem('refreshToken')
    }
  }

  function logout() {
    user.value = null
    setTokens(null, null)
  }

  // Initialize user on store creation
  if (accessToken.value) {
    fetchUser().catch(() => {})
  }

  return {
    user,
    accessToken,
    refreshToken,
    isAuthenticated,
    isTokenExpiringSoon,
    login,
    signup,
    fetchUser,
    refreshAccessToken,
    ensureValidToken,
    logout
  }
})
