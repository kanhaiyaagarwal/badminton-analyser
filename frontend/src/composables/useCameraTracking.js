/**
 * Composable for camera-based workout form tracking.
 *
 * REUSES the challenge WebSocket infrastructure (/ws/challenge/) which
 * already handles:
 *   - Hold-based frame dropping (plank, squat_hold)
 *   - Sequential processing (pushup, squat)
 *   - Pose overlay data, form feedback, auto-end detection
 *   - All analyzer types (PushupAnalyzer, SquatAnalyzer, PlankAnalyzer)
 *
 * Flow:
 *   1. POST /api/v1/workout/sessions/{id}/start-tracking → creates a challenge session
 *   2. Connect to /ws/challenge/{challengeSessionId} (existing, proven endpoint)
 *   3. On end: collect results, POST them back as camera-result
 */

import { ref, onUnmounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import api from '@/api/client'

const FRAME_INTERVAL_MS = 100 // 10fps
const JPEG_QUALITY = 0.7      // match challenge quality

export function useCameraTracking() {
  const authStore = useAuthStore()

  // Reactive state
  const isReady = ref(false)
  const isActive = ref(false)
  const reps = ref(0)
  const holdSeconds = ref(0)
  const formFeedback = ref('')
  const playerDetected = ref(false)
  const playerReady = ref(false)
  const poseData = ref(null)
  const autoEnded = ref(false)
  const error = ref(null)

  // Internal
  let videoEl = null
  let canvasEl = null
  let stream = null
  let ws = null
  let frameInterval = null
  let startTime = 0
  let challengeSessionId = null

  // Hold timer (local interpolation, same as ChallengeSessionView)
  let isInHold = false
  let holdBaseSeconds = 0
  let holdStartedAt = 0
  let holdTimerInterval = null

  /**
   * Initialize camera.
   */
  async function initCamera(video, canvas = null) {
    videoEl = video
    canvasEl = canvas
    error.value = null

    try {
      // Match ChallengeSessionView: 640x480, zoom 1x (widest FOV)
      stream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: 'user',
          width: { ideal: 640 },
          height: { ideal: 480 },
          zoom: { ideal: 1 },
          focusMode: { ideal: 'continuous' },
        },
        audio: false,
      })
      videoEl.srcObject = stream
      await videoEl.play()
      isReady.value = true
    } catch (e) {
      error.value = `Camera access denied: ${e.message}`
      isReady.value = false
    }
  }

  /**
   * Start tracking: create challenge session via workout API, then connect to /ws/challenge/.
   */
  async function start(workoutSessionId, exerciseSlug) {
    if (!isReady.value || !videoEl) return

    error.value = null
    reps.value = 0
    holdSeconds.value = 0
    formFeedback.value = ''
    playerDetected.value = false
    playerReady.value = false
    autoEnded.value = false
    isActive.value = true
    startTime = Date.now()

    try {
      // Create a challenge session via workout endpoint
      const { data: trackData } = await api.post(
        `/api/v1/workout/sessions/${workoutSessionId}/start-tracking`,
        { exercise_slug: exerciseSlug }
      )
      challengeSessionId = trackData.challenge_session_id
      const wsPath = trackData.ws_url

      // Connect to the EXISTING /ws/challenge/ endpoint
      await authStore.ensureValidToken()
      const token = authStore.accessToken
      const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:'
      const wsUrl = `${protocol}//${location.host}${wsPath}?token=${token}`

      ws = new WebSocket(wsUrl)

      ws.onopen = () => {
        _startFrameCapture()
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)

          if (data.type === 'challenge_update') {
            // Reps (for pushup, squat)
            reps.value = data.reps || 0

            // Hold timer (for plank, squat_hold) — local interpolation
            const serverHold = data.hold_seconds || 0
            if (serverHold > 0 && !isInHold) {
              isInHold = true
              holdBaseSeconds = serverHold
              holdStartedAt = Date.now()
              holdSeconds.value = serverHold
              _startHoldTimer()
            } else if (serverHold > 0 && isInHold) {
              // Re-anchor from server
              holdBaseSeconds = serverHold
              holdStartedAt = Date.now()
            } else if (serverHold === 0 && isInHold) {
              isInHold = false
              _stopHoldTimer()
              holdSeconds.value = 0
            }

            // Form feedback
            if (data.form_feedback) formFeedback.value = data.form_feedback
            playerDetected.value = !!data.player_detected
            playerReady.value = !!data.ready

            // Pose data for overlay
            if (data.pose) {
              poseData.value = data.pose
              if (canvasEl) _drawPoseOverlay(data.pose)
            }

            // Auto-end detection
            if (data.auto_end) {
              autoEnded.value = true
              _endChallengeSession()
            }
          } else if (data.type === 'session_ended') {
            _handleSessionEnded(data.report)
          }
        } catch (e) { /* ignore parse errors */ }
      }

      ws.onerror = () => {
        error.value = 'WebSocket connection error'
      }

      ws.onclose = () => {
        _stopFrameCapture()
      }

    } catch (e) {
      error.value = `Failed to start tracking: ${e.message}`
      isActive.value = false
    }
  }

  /**
   * Stop tracking — end the challenge session and return results.
   */
  function stop() {
    return new Promise((resolve) => {
      if (!ws || ws.readyState !== WebSocket.OPEN) {
        isActive.value = false
        _cleanup()
        resolve(_currentReport())
        return
      }

      // Wait for session_ended response
      const origOnMessage = ws.onmessage
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          if (data.type === 'session_ended') {
            const report = data.report || {}
            isActive.value = false
            _cleanup()
            resolve({
              reps: report.score || report.reps || reps.value,
              holdSeconds: report.hold_seconds || holdSeconds.value,
              formScore: report.form_score || 0,
              durationSeconds: report.duration_seconds || Math.round((Date.now() - startTime) / 1000),
            })
          } else if (origOnMessage) {
            origOnMessage(event)
          }
        } catch (e) {
          resolve(_currentReport())
        }
      }

      // Send end_session (same message type the challenge WS expects)
      ws.send(JSON.stringify({ type: 'end_session' }))

      // Also end via REST to persist results
      _endChallengeSession()

      // Timeout fallback
      setTimeout(() => {
        isActive.value = false
        _cleanup()
        resolve(_currentReport())
      }, 3000)
    })
  }

  /** Clean up all resources. */
  function destroy() {
    _cleanup()
    if (stream) {
      stream.getTracks().forEach(t => t.stop())
      stream = null
    }
    isReady.value = false
    isActive.value = false
  }

  // --- Internal: frame capture (same as ChallengeSessionView) ---

  function _startFrameCapture() {
    const canvas = document.createElement('canvas')

    frameInterval = setInterval(() => {
      if (!videoEl || !ws || ws.readyState !== WebSocket.OPEN) return

      canvas.width = videoEl.videoWidth || 640
      canvas.height = videoEl.videoHeight || 480
      const ctx = canvas.getContext('2d')
      ctx.drawImage(videoEl, 0, 0, canvas.width, canvas.height)

      canvas.toBlob((blob) => {
        if (!blob || !ws || ws.readyState !== WebSocket.OPEN) return
        const reader = new FileReader()
        reader.onloadend = () => {
          const base64 = reader.result.split(',')[1]
          ws.send(JSON.stringify({
            type: 'frame',
            data: base64,
            timestamp: (Date.now() - startTime) / 1000,
          }))
        }
        reader.readAsDataURL(blob)
      }, 'image/jpeg', JPEG_QUALITY)
    }, FRAME_INTERVAL_MS)
  }

  function _stopFrameCapture() {
    if (frameInterval) {
      clearInterval(frameInterval)
      frameInterval = null
    }
  }

  // --- Hold timer (local interpolation between server updates) ---

  function _startHoldTimer() {
    _stopHoldTimer()
    holdTimerInterval = setInterval(() => {
      if (isInHold) {
        holdSeconds.value = holdBaseSeconds + (Date.now() - holdStartedAt) / 1000
      }
    }, 100)
  }

  function _stopHoldTimer() {
    if (holdTimerInterval) {
      clearInterval(holdTimerInterval)
      holdTimerInterval = null
    }
  }

  // --- Pose overlay (same coordinate system as ChallengeSessionView) ---

  function _drawPoseOverlay(pose) {
    if (!canvasEl || !videoEl) return

    canvasEl.width = videoEl.videoWidth || 640
    canvasEl.height = videoEl.videoHeight || 480

    const ctx = canvasEl.getContext('2d')
    ctx.clearRect(0, 0, canvasEl.width, canvasEl.height)

    if (!pose || !pose.landmarks) return

    const landmarks = pose.landmarks
    const pw = pose.width || canvasEl.width
    const ph = pose.height || canvasEl.height

    // Scale from pose detection resolution to canvas
    const sx = canvasEl.width / pw
    const sy = canvasEl.height / ph

    const isUsable = (lm) =>
      lm && lm.visibility >= 0.5 &&
      lm.x >= 0 && lm.x <= pw &&
      lm.y >= 0 && lm.y <= ph

    ctx.globalAlpha = 0.75

    // Use server-provided connections or fallback
    const connections = pose.connections || [
      [11, 12], [11, 13], [13, 15], [12, 14], [14, 16],
      [11, 23], [12, 24], [23, 24], [23, 25], [24, 26],
      [25, 27], [26, 28],
    ]

    ctx.strokeStyle = 'rgba(93, 157, 118, 0.8)'
    ctx.lineWidth = 3

    for (const [a, b] of connections) {
      const la = landmarks[a]
      const lb = landmarks[b]
      if (!isUsable(la) || !isUsable(lb)) continue
      ctx.beginPath()
      ctx.moveTo(la.x * sx, la.y * sy)
      ctx.lineTo(lb.x * sx, lb.y * sy)
      ctx.stroke()
    }

    ctx.fillStyle = 'rgba(93, 157, 118, 1)'
    for (const lm of landmarks) {
      if (!isUsable(lm)) continue
      ctx.beginPath()
      ctx.arc(lm.x * sx, lm.y * sy, 5, 0, Math.PI * 2)
      ctx.fill()
    }

    ctx.globalAlpha = 1
  }

  // --- Helpers ---

  async function _endChallengeSession() {
    if (!challengeSessionId) return
    try {
      await api.post(`/api/v1/challenges/sessions/${challengeSessionId}/end`)
    } catch (e) { /* ignore — WS disconnect handler also ends it */ }
  }

  function _handleSessionEnded(report) {
    isActive.value = false
    if (report) {
      reps.value = report.score || report.reps || reps.value
    }
    _cleanup()
  }

  function _currentReport() {
    return {
      reps: reps.value,
      holdSeconds: holdSeconds.value,
      formScore: 0,
      durationSeconds: Math.round((Date.now() - startTime) / 1000),
    }
  }

  function _cleanup() {
    _stopFrameCapture()
    _stopHoldTimer()
    if (ws && ws.readyState === WebSocket.OPEN) {
      try { ws.close() } catch (e) { /* ignore */ }
    }
  }

  onUnmounted(() => {
    destroy()
  })

  function getChallengeSessionId() {
    return challengeSessionId
  }

  return {
    isReady,
    isActive,
    reps,
    holdSeconds,
    formFeedback,
    playerDetected,
    playerReady,
    poseData,
    autoEnded,
    error,
    getChallengeSessionId,
    initCamera,
    start,
    stop,
    destroy,
  }
}
