import axios from 'axios'

const api = axios.create({
  baseURL: '',
  timeout: 60000
})

// Safe localStorage wrapper — Safari private mode throws on access
function safeGetItem(key) {
  try { return localStorage.getItem(key) } catch { return null }
}
function safeSetItem(key, value) {
  try { localStorage.setItem(key, value) } catch { /* Safari private mode */ }
}
function safeRemoveItem(key) {
  try { localStorage.removeItem(key) } catch { /* Safari private mode */ }
}

// Lazy reference to auth store — avoids circular import at module load time.
// Set by the auth store itself after it initializes.
let _authStore = null
export function _setAuthStoreRef(store) { _authStore = store }

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = safeGetItem('accessToken')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// Response interceptor for token refresh
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true

      const refreshToken = safeGetItem('refreshToken')
      if (refreshToken) {
        try {
          const response = await axios.post('/api/v1/auth/refresh', null, {
            params: { refresh_token: refreshToken }
          })

          const { access_token, refresh_token } = response.data
          safeSetItem('accessToken', access_token)
          safeSetItem('refreshToken', refresh_token)

          // Sync Pinia store so ensureValidToken / accessToken ref stay current
          if (_authStore) {
            _authStore.accessToken = access_token
            _authStore.refreshToken = refresh_token
          }

          originalRequest.headers.Authorization = `Bearer ${access_token}`
          return api(originalRequest)
        } catch (refreshError) {
          safeRemoveItem('accessToken')
          safeRemoveItem('refreshToken')
          window.location.href = '/login'
          return Promise.reject(refreshError)
        }
      }
    }

    if (window.DD_RUM) {
      window.DD_RUM.addError(error, {
        source: 'network',
        url: error.config?.url,
        status: error.response?.status,
      })
    }

    return Promise.reject(error)
  }
)

export default api

// WebSocket helper
export function createProgressWebSocket(jobId, onMessage, onError) {
  const token = safeGetItem('accessToken')
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = window.location.host
  const wsUrl = `${protocol}//${host}/ws/progress/${jobId}?token=${token}`

  const ws = new WebSocket(wsUrl)

  ws.onopen = () => {
    console.log('WebSocket connected for job', jobId)
  }

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      onMessage(data)
    } catch (e) {
      console.error('Failed to parse WebSocket message', e)
    }
  }

  ws.onerror = (event) => {
    console.error('WebSocket error', event)
    if (onError) onError(event)
  }

  ws.onclose = () => {
    console.log('WebSocket closed for job', jobId)
  }

  // Ping to keep alive
  const pingInterval = setInterval(() => {
    if (ws.readyState === WebSocket.OPEN) {
      ws.send('ping')
    }
  }, 30000)

  return {
    ws,
    close: () => {
      clearInterval(pingInterval)
      ws.close()
    }
  }
}
