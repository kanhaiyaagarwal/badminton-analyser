import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api, { _setAuthStoreRef } from '../api/client'

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

  // Pending verification state (for signup flow)
  const pendingVerification = ref(null) // { userId, email }

  const isAuthenticated = computed(() => !!accessToken.value)
  const enabledFeatures = computed(() => user.value?.enabled_features || [])

  function hasFeature(feature) {
    if (user.value?.is_admin) return true
    return enabledFeatures.value.includes(feature)
  }

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

  async function signup(email, username, password, inviteCode) {
    const response = await api.post('/api/v1/auth/signup', {
      email,
      username,
      password,
      invite_code: inviteCode
    })
    // If user was waitlisted (no invite code), don't set pending verification
    if (response.data.status === 'waitlisted') {
      return response.data
    }
    // Store pending verification info for OTP step
    pendingVerification.value = {
      userId: response.data.user_id,
      email: response.data.email
    }
    return response.data
  }

  async function verifyEmail(userId, code) {
    const response = await api.post('/api/v1/auth/verify-email', {
      user_id: userId,
      code
    })
    if (response.data.success) {
      pendingVerification.value = null
      // Auto-login: backend returns tokens on successful verification
      if (response.data.access_token) {
        setTokens(response.data.access_token, response.data.refresh_token)
        await fetchUser()
      }
    }
    return response.data
  }

  async function resendOTP(userId) {
    const response = await api.post('/api/v1/auth/resend-otp', {
      user_id: userId
    })
    return response.data
  }

  function clearPendingVerification() {
    pendingVerification.value = null
  }

  async function loginWithGoogle(credential, inviteCode = '') {
    const response = await api.post('/api/v1/auth/google', {
      credential,
      invite_code: inviteCode
    })
    if (response.data.access_token) {
      setTokens(response.data.access_token, response.data.refresh_token)
      await fetchUser()
    }
    return response.data
  }

  async function updateProfile(data) {
    const response = await api.patch('/api/v1/auth/me', data)
    user.value = response.data
    return response.data
  }

  async function forgotPassword(email) {
    const response = await api.post('/api/v1/auth/forgot-password', { email })
    return response.data
  }

  async function resetPassword(email, code, newPassword) {
    const response = await api.post('/api/v1/auth/reset-password', {
      email,
      code,
      new_password: newPassword
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

  // Initialize user on store creation — expose promise so router can await it
  let _initResolve
  const initReady = new Promise(resolve => { _initResolve = resolve })

  if (accessToken.value) {
    fetchUser().catch(() => {}).finally(() => _initResolve())
  } else {
    _initResolve()
  }

  // Let the axios interceptor sync tokens back into this store
  _setAuthStoreRef({ accessToken, refreshToken })

  return {
    initReady,
    user,
    accessToken,
    refreshToken,
    isAuthenticated,
    isTokenExpiringSoon,
    enabledFeatures,
    hasFeature,
    pendingVerification,
    login,
    loginWithGoogle,
    signup,
    updateProfile,
    verifyEmail,
    resendOTP,
    clearPendingVerification,
    forgotPassword,
    resetPassword,
    fetchUser,
    refreshAccessToken,
    ensureValidToken,
    logout
  }
})
