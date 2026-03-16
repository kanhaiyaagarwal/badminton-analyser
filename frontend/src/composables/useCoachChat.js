/**
 * Composable for coach chat — manages conversation state, API calls, and voice sequencing.
 *
 * Usage:
 *   const { messages, sendMessage, sendOption, loading, conversationId } = useCoachChat('onboarding')
 *
 * Integrates with useVoiceOutput for auto-playing coach responses.
 */

import { ref } from 'vue'
import api from '../api/client'
import { useVoiceOutput } from './useVoiceOutput'

export function useCoachChat(context, sessionId = null) {
  const messages = ref([])  // [{role: 'coach'|'user', content, options?, timestamp}]
  const loading = ref(false)
  const conversationId = ref(null)
  const lastResponse = ref(null)  // Full ChatResponse from server

  const voiceOutput = useVoiceOutput()

  /**
   * Send a text message to the coach chat endpoint.
   * Adds user message to chat, calls API, adds coach response.
   */
  async function sendMessage(text) {
    if (loading.value) return

    // Add user message to chat (skip empty opening messages)
    if (text) {
      messages.value.push({
        role: 'user',
        content: text,
        timestamp: Date.now(),
      })
    }

    loading.value = true
    try {
      const res = await api.post('/api/v1/workout/chat', {
        message: text,
        context,
        session_id: sessionId,
        conversation_id: conversationId.value,
      })

      const data = res.data
      lastResponse.value = data

      // Track conversation ID
      if (data.conversation_id) {
        conversationId.value = data.conversation_id
      }

      // Add coach response to chat
      if (data.response) {
        messages.value.push({
          role: 'coach',
          content: data.response,
          options: data.suggested_options || [],
          actions: data.actions || [],
          timestamp: Date.now(),
        })

        // Auto-play coach response via TTS
        voiceOutput.speak(data.response, data.audio_url || null)
      }

      return data
    } catch (err) {
      // Add error message as coach bubble
      messages.value.push({
        role: 'coach',
        content: 'Sorry, I had trouble understanding that. Could you try again?',
        options: [],
        timestamp: Date.now(),
      })
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * Send a structured option selection (user tapped a card).
   * Shows the label as the user's message, sends the value to the API.
   */
  async function sendOption(value, label) {
    if (loading.value) return

    // Show the label as user's message
    messages.value.push({
      role: 'user',
      content: label || value,
      timestamp: Date.now(),
    })

    loading.value = true
    try {
      const res = await api.post('/api/v1/workout/chat', {
        message: value,
        context,
        session_id: sessionId,
        conversation_id: conversationId.value,
      })

      const data = res.data
      lastResponse.value = data

      if (data.conversation_id) {
        conversationId.value = data.conversation_id
      }

      if (data.response) {
        messages.value.push({
          role: 'coach',
          content: data.response,
          options: data.suggested_options || [],
          actions: data.actions || [],
          timestamp: Date.now(),
        })
        voiceOutput.speak(data.response, data.audio_url || null)
      }

      return data
    } catch (err) {
      messages.value.push({
        role: 'coach',
        content: 'Something went wrong. Let me try that again.',
        options: [],
        timestamp: Date.now(),
      })
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * Initialize the chat with an opening message from the coach.
   * Sends empty message to get the greeting.
   */
  async function initChat() {
    return sendMessage('')
  }

  return {
    messages,
    loading,
    conversationId,
    lastResponse,
    sendMessage,
    sendOption,
    initChat,
  }
}
