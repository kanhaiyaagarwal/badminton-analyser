/**
 * Composable for STT voice input — microphone capture + speech recognition.
 *
 * Uses Web Speech API (SpeechRecognition) when available, with fallback
 * to MediaRecorder + server-side Whisper transcription.
 *
 * Returns: { startListening, stopListening, isListening, transcript, error }
 */

import { ref, onUnmounted } from 'vue'
import api from '../api/client'

export function useVoiceInput() {
  const isListening = ref(false)
  const transcript = ref('')
  const error = ref(null)

  let recognition = null
  let onCommandCallback = null
  let useWhisperFallback = false  // Set to true after Web Speech API fails with 'network'

  // MediaRecorder state for Whisper fallback
  let mediaRecorder = null
  let audioChunks = []
  let mediaStream = null

  /**
   * Start listening for voice commands.
   * @param {Function} onCommand - Callback receiving (text: string)
   * @param {Object} options - { continuous: bool, lang: string }
   */
  function startListening(onCommand, options = {}) {
    const { continuous = false, lang = 'en-US' } = options
    onCommandCallback = onCommand
    error.value = null
    transcript.value = ''

    if (useWhisperFallback) {
      _startWhisperRecording(onCommand)
      return
    }

    // Use Web Speech API if available
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
    if (!SpeechRecognition) {
      // No Web Speech API — go straight to Whisper
      useWhisperFallback = true
      _startWhisperRecording(onCommand)
      return
    }

    recognition = new SpeechRecognition()
    recognition.continuous = continuous
    recognition.interimResults = true
    recognition.lang = lang
    recognition.maxAlternatives = 1

    recognition.onstart = () => {
      isListening.value = true
    }

    recognition.onresult = (event) => {
      const result = event.results[event.results.length - 1]
      const text = result[0].transcript.trim()
      // Show interim transcription for visual feedback
      transcript.value = text
      // Only dispatch command on final result
      if (result.isFinal && onCommandCallback && text) {
        onCommandCallback(text)
      }
    }

    recognition.onerror = (event) => {
      if (event.error === 'no-speech' || event.error === 'aborted') {
        return
      }

      // Network error = Google's speech service unreachable (Arc, Brave, etc.)
      // Fall back to Whisper for this and all future calls
      if (event.error === 'network') {
        console.log('Web Speech API network error — switching to Whisper fallback')
        useWhisperFallback = true
        recognition = null
        isListening.value = false
        _startWhisperRecording(onCommand)
        return
      }

      error.value = event.error
      isListening.value = false
    }

    recognition.onend = () => {
      isListening.value = false
      // Auto-restart if continuous mode and not explicitly stopped
      if (continuous && !error.value && recognition && onCommandCallback) {
        try {
          recognition.start()
          isListening.value = true
        } catch (e) {
          // Already started or other error
        }
      }
    }

    try {
      recognition.start()
    } catch (e) {
      error.value = e.message
      // Try Whisper fallback
      useWhisperFallback = true
      _startWhisperRecording(onCommand)
    }
  }

  /**
   * Start recording via MediaRecorder for Whisper transcription.
   */
  async function _startWhisperRecording(onCommand) {
    onCommandCallback = onCommand
    error.value = null
    transcript.value = ''
    audioChunks = []

    try {
      mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true })
    } catch (e) {
      if (e.name === 'NotAllowedError') {
        error.value = 'not-allowed'
      } else if (e.name === 'NotFoundError') {
        error.value = 'audio-capture'
      } else {
        error.value = e.message
      }
      return
    }

    // Pick a supported MIME type
    const mimeType = ['audio/webm;codecs=opus', 'audio/webm', 'audio/ogg;codecs=opus', 'audio/mp4']
      .find(t => MediaRecorder.isTypeSupported(t)) || ''

    try {
      mediaRecorder = new MediaRecorder(mediaStream, mimeType ? { mimeType } : {})
    } catch (e) {
      error.value = e.message
      _stopMediaStream()
      return
    }

    mediaRecorder.ondataavailable = (event) => {
      if (event.data.size > 0) {
        audioChunks.push(event.data)
      }
    }

    mediaRecorder.onstop = async () => {
      _stopMediaStream()

      if (audioChunks.length === 0) {
        isListening.value = false
        return
      }

      const blob = new Blob(audioChunks, { type: mediaRecorder.mimeType || 'audio/webm' })
      audioChunks = []

      // Show "processing" state
      transcript.value = 'Transcribing...'

      try {
        const formData = new FormData()
        formData.append('audio', blob, `recording.${_getExtension(blob.type)}`)
        const res = await api.post('/api/v1/workout/stt', formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
          timeout: 15000,
        })

        const text = res.data?.text?.trim()
        if (text) {
          transcript.value = text
          if (onCommandCallback) {
            onCommandCallback(text)
          }
        } else {
          transcript.value = ''
          error.value = 'no-speech'
        }
      } catch (e) {
        transcript.value = ''
        if (e.response?.status === 503) {
          error.value = 'STT service unavailable'
        } else {
          error.value = e.response?.data?.detail || 'Transcription failed'
        }
      } finally {
        isListening.value = false
      }
    }

    mediaRecorder.onerror = () => {
      error.value = 'Recording failed'
      isListening.value = false
      _stopMediaStream()
    }

    mediaRecorder.start()
    isListening.value = true
  }

  function _getExtension(mimeType) {
    if (mimeType.includes('webm')) return 'webm'
    if (mimeType.includes('ogg')) return 'ogg'
    if (mimeType.includes('mp4')) return 'm4a'
    return 'webm'
  }

  function _stopMediaStream() {
    if (mediaStream) {
      mediaStream.getTracks().forEach(t => t.stop())
      mediaStream = null
    }
  }

  /**
   * Stop listening.
   */
  function stopListening() {
    // Stop Web Speech API
    if (recognition) {
      try {
        recognition.stop()
      } catch (e) {
        // ignore
      }
      recognition = null
    }

    // Stop MediaRecorder (triggers onstop → Whisper transcription)
    if (mediaRecorder && mediaRecorder.state === 'recording') {
      mediaRecorder.stop()
      // isListening stays true until transcription completes
      return
    }

    isListening.value = false
    onCommandCallback = null
    _stopMediaStream()
  }

  onUnmounted(() => {
    stopListening()
  })

  return {
    isListening,
    transcript,
    error,
    startListening,
    stopListening,
  }
}
