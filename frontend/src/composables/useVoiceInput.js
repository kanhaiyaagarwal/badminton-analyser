/**
 * Composable for STT voice input — microphone capture + speech recognition.
 *
 * Uses Web Speech API (SpeechRecognition) when available, with fallback
 * to sending audio over WebSocket to server-side Vosk.
 *
 * Returns: { startListening, stopListening, isListening, transcript, error }
 */

import { ref, onUnmounted } from 'vue'

export function useVoiceInput() {
  const isListening = ref(false)
  const transcript = ref('')
  const error = ref(null)

  let recognition = null
  let onCommandCallback = null

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

    // Use Web Speech API if available
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
    if (!SpeechRecognition) {
      error.value = 'Speech recognition not supported in this browser'
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
      if (event.error === 'no-speech') {
        // Silence — not an error
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
    }
  }

  /**
   * Stop listening.
   */
  function stopListening() {
    if (recognition) {
      try {
        recognition.stop()
      } catch (e) {
        // ignore
      }
      recognition = null
    }
    isListening.value = false
    onCommandCallback = null
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
