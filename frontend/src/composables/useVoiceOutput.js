/**
 * Composable for TTS voice output — plays coach audio.
 *
 * Priority: pre-recorded clip (0ms latency) > dynamic TTS endpoint > browser speechSynthesis
 *
 * Returns: { speak, stop, muted, toggleMute }
 */

import { ref, watch } from 'vue'

const muted = ref(localStorage.getItem('coach_muted') === 'true')

// Audio queue to prevent overlapping
let audioQueue = []
let isPlaying = false
let currentAudio = null  // Track current Audio element so we can stop it

export function useVoiceOutput() {
  // Persist mute setting
  watch(muted, (val) => {
    localStorage.setItem('coach_muted', val ? 'true' : 'false')
  })

  /**
   * Speak a coach message.
   * @param {string} text - The text to speak (fallback for browser TTS)
   * @param {string|null} audioUrl - URL to pre-recorded or dynamic TTS audio
   */
  function speak(text, audioUrl = null) {
    if (muted.value || !text) return

    audioQueue.push({ text, audioUrl })
    _processQueue()
  }

  /**
   * Stop any currently playing audio and clear the queue.
   * Called on view transitions to prevent audio bleeding into next screen.
   */
  function stop() {
    audioQueue = []
    isPlaying = false

    // Stop HTML5 Audio
    if (currentAudio) {
      currentAudio.pause()
      currentAudio.currentTime = 0
      currentAudio = null
    }

    // Stop browser speechSynthesis
    if (window.speechSynthesis) {
      window.speechSynthesis.cancel()
    }
  }

  function toggleMute() {
    muted.value = !muted.value
    if (muted.value) {
      stop()
    }
  }

  return {
    speak,
    stop,
    muted,
    toggleMute,
  }
}

async function _processQueue() {
  if (isPlaying || audioQueue.length === 0) return

  isPlaying = true
  const { text, audioUrl } = audioQueue.shift()

  try {
    if (audioUrl) {
      await _playAudioUrl(audioUrl)
    } else {
      await _browserSpeak(text)
    }
  } catch (e) {
    // Fallback to browser TTS if audio URL fails
    try {
      await _browserSpeak(text)
    } catch (e2) {
      // Silent fail
    }
  }

  isPlaying = false
  currentAudio = null
  // Process next in queue
  if (audioQueue.length > 0) {
    _processQueue()
  }
}

function _playAudioUrl(url) {
  return new Promise((resolve, reject) => {
    const audio = new Audio(url)
    currentAudio = audio  // Store reference so stop() can kill it
    audio.onended = resolve
    audio.onerror = reject
    audio.play().catch(reject)

    // Timeout safety
    setTimeout(() => {
      if (currentAudio === audio) {
        audio.pause()
        currentAudio = null
      }
      resolve()
    }, 10000)
  })
}

function _browserSpeak(text) {
  return new Promise((resolve) => {
    if (!window.speechSynthesis) {
      resolve()
      return
    }

    const utterance = new SpeechSynthesisUtterance(text)
    utterance.rate = 1.0
    utterance.pitch = 1.0
    utterance.volume = 0.8
    utterance.onend = resolve
    utterance.onerror = resolve

    window.speechSynthesis.speak(utterance)

    // Timeout safety
    setTimeout(() => {
      window.speechSynthesis.cancel()
      resolve()
    }, 8000)
  })
}
