/**
 * Composable for TTS voice output — plays coach audio.
 *
 * Priority: pre-recorded clip (0ms latency) > dynamic TTS endpoint > browser speechSynthesis
 *
 * Returns: { speak, stop, muted, toggleMute }
 */

import { ref, watch } from 'vue'

const muted = ref(localStorage.getItem('coach_muted') === 'true')
const isSpeaking = ref(false)

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
   * Speak and wait until done. Returns a Promise that resolves when speech ends.
   * Useful for speak-then-listen sequencing.
   * @param {string} text
   * @param {string|null} audioUrl
   * @returns {Promise<void>}
   */
  function speakAndWait(text, audioUrl = null) {
    return new Promise((resolve) => {
      if (muted.value || !text) {
        resolve()
        return
      }
      audioQueue.push({ text, audioUrl, onDone: resolve })
      _processQueue()
    })
  }

  /**
   * Stop any currently playing audio and clear the queue.
   * Called on view transitions to prevent audio bleeding into next screen.
   */
  function stop() {
    // Resolve any pending speakAndWait promises
    for (const item of audioQueue) {
      if (item.onDone) item.onDone()
    }
    audioQueue = []
    isPlaying = false
    isSpeaking.value = false

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
    speakAndWait,
    stop,
    muted,
    isSpeaking,
    toggleMute,
  }
}

async function _processQueue() {
  if (isPlaying || audioQueue.length === 0) return

  isPlaying = true
  isSpeaking.value = true
  const { text, audioUrl, onDone } = audioQueue.shift()

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

  if (onDone) onDone()
  isPlaying = false
  currentAudio = null
  // Update isSpeaking based on remaining queue
  if (audioQueue.length > 0) {
    _processQueue()
  } else {
    isSpeaking.value = false
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
