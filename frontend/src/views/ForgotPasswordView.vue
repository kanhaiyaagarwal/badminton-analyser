<template>
  <div class="auth-container">
    <!-- Step 1: Email input -->
    <div v-if="!showResetStep" class="auth-card">
      <h1>Forgot Password</h1>
      <p class="subtitle">Enter your email to receive a reset code</p>

      <form @submit.prevent="handleForgotPassword">
        <div class="form-group">
          <label for="email">Email</label>
          <input
            id="email"
            v-model="email"
            type="email"
            placeholder="your@email.com"
            required
          />
        </div>

        <div v-if="error" class="error-message">{{ error }}</div>
        <div v-if="success" class="success-message">{{ success }}</div>

        <button type="submit" class="btn-primary" :disabled="loading">
          {{ loading ? 'Sending...' : 'Send Reset Code' }}
        </button>
      </form>

      <p class="auth-switch">
        Remember your password?
        <router-link :to="{ path: '/login', query: $route.query }">Login</router-link>
      </p>
    </div>

    <!-- Step 2: OTP + New Password -->
    <div v-else class="auth-card">
      <h1>Reset Password</h1>
      <p class="subtitle">Enter the code sent to {{ email }} and your new password</p>

      <form @submit.prevent="handleResetPassword">
        <div class="form-group">
          <label for="otpCode">Reset Code</label>
          <input
            id="otpCode"
            v-model="otpCode"
            type="text"
            inputmode="numeric"
            pattern="[0-9]{6}"
            maxlength="6"
            placeholder="000000"
            class="otp-input"
            required
            autocomplete="one-time-code"
          />
        </div>

        <div class="form-group">
          <label for="newPassword">New Password</label>
          <input
            id="newPassword"
            v-model="newPassword"
            type="password"
            placeholder="Min 8 characters"
            minlength="8"
            required
          />
        </div>

        <div class="form-group">
          <label for="confirmPassword">Confirm Password</label>
          <input
            id="confirmPassword"
            v-model="confirmPassword"
            type="password"
            placeholder="Confirm your password"
            required
          />
        </div>

        <div v-if="resetError" class="error-message">{{ resetError }}</div>
        <div v-if="resetSuccess" class="success-message">{{ resetSuccess }}</div>

        <button
          type="submit"
          class="btn-primary"
          :disabled="resetLoading || otpCode.length !== 6"
        >
          {{ resetLoading ? 'Resetting...' : 'Reset Password' }}
        </button>
      </form>

      <div class="resend-section">
        <p v-if="resendCooldown > 0" class="cooldown-text">
          Resend code in {{ resendCooldown }}s
        </p>
        <button
          v-else
          type="button"
          @click="handleResendCode"
          class="btn-link"
          :disabled="resendLoading"
        >
          {{ resendLoading ? 'Sending...' : "Didn't receive a code? Resend" }}
        </button>
      </div>

      <button type="button" @click="goBack" class="btn-secondary">
        Back
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

// Step 1
const email = ref('')
const loading = ref(false)
const error = ref('')
const success = ref('')

// Step 2
const showResetStep = ref(false)
const otpCode = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const resetLoading = ref(false)
const resetError = ref('')
const resetSuccess = ref('')
const resendCooldown = ref(0)
const resendLoading = ref(false)

let cooldownTimer = null

onUnmounted(() => {
  if (cooldownTimer) {
    clearInterval(cooldownTimer)
  }
})

function startCooldownTimer(seconds) {
  resendCooldown.value = seconds
  if (cooldownTimer) {
    clearInterval(cooldownTimer)
  }
  cooldownTimer = setInterval(() => {
    resendCooldown.value--
    if (resendCooldown.value <= 0) {
      clearInterval(cooldownTimer)
      cooldownTimer = null
    }
  }, 1000)
}

async function handleForgotPassword() {
  error.value = ''
  success.value = ''
  loading.value = true

  try {
    const response = await authStore.forgotPassword(email.value)
    if (response.success) {
      success.value = response.message
      showResetStep.value = true
      startCooldownTimer(60)
    } else {
      error.value = response.message
    }
  } catch (err) {
    error.value = err.response?.data?.detail || 'Failed to send reset code.'
  } finally {
    loading.value = false
  }
}

async function handleResetPassword() {
  resetError.value = ''
  resetSuccess.value = ''

  if (newPassword.value !== confirmPassword.value) {
    resetError.value = 'Passwords do not match'
    return
  }

  resetLoading.value = true

  try {
    const response = await authStore.resetPassword(email.value, otpCode.value, newPassword.value)
    if (response.success) {
      resetSuccess.value = 'Password reset! Redirecting to login...'
      const loginQuery = route.query.redirect ? { redirect: route.query.redirect } : {}
      setTimeout(() => router.push({ path: '/login', query: loginQuery }), 1500)
    } else {
      resetError.value = response.message
    }
  } catch (err) {
    resetError.value = err.response?.data?.detail || 'Failed to reset password.'
  } finally {
    resetLoading.value = false
  }
}

async function handleResendCode() {
  resetError.value = ''
  resetSuccess.value = ''
  resendLoading.value = true

  try {
    const response = await authStore.forgotPassword(email.value)
    if (response.success) {
      resetSuccess.value = 'A new reset code has been sent.'
      otpCode.value = ''
      startCooldownTimer(60)
    } else {
      resetError.value = response.message
    }
  } catch (err) {
    resetError.value = err.response?.data?.detail || 'Failed to resend code.'
  } finally {
    resendLoading.value = false
  }
}

function goBack() {
  showResetStep.value = false
  otpCode.value = ''
  newPassword.value = ''
  confirmPassword.value = ''
  resetError.value = ''
  resetSuccess.value = ''
  resendCooldown.value = 0
  if (cooldownTimer) {
    clearInterval(cooldownTimer)
    cooldownTimer = null
  }
}
</script>

<style scoped>
.auth-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 80vh;
}

.auth-card {
  background: var(--bg-card);
  padding: 3rem;
  border-radius: var(--radius-lg);
  width: 100%;
  max-width: 400px;
  box-shadow: var(--shadow-lg);
  border: 1px solid var(--border-color);
}

h1 {
  color: var(--color-primary);
  margin-bottom: 0.5rem;
  text-align: center;
}

.subtitle {
  color: var(--text-muted);
  text-align: center;
  margin-bottom: 2rem;
}

.form-group {
  margin-bottom: 1.25rem;
}

label {
  display: block;
  margin-bottom: 0.5rem;
  color: var(--text-secondary);
  font-weight: 500;
}

input {
  width: 100%;
  padding: 0.75rem 1rem;
  border: 2px solid var(--border-input);
  border-radius: var(--radius-md);
  background: var(--bg-input);
  color: var(--text-primary);
  font-size: 1rem;
  transition: border-color 0.2s;
}

input:focus {
  outline: none;
  border-color: var(--color-primary);
}

.otp-input {
  text-align: center;
  font-size: 1.5rem;
  letter-spacing: 0.5rem;
  font-family: monospace;
}

.btn-primary {
  width: 100%;
  padding: 1rem;
  background: var(--gradient-primary);
  color: var(--text-on-primary);
  border: none;
  border-radius: var(--radius-md);
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-primary:hover:not(:disabled) {
  background: var(--gradient-primary-hover);
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.error-message {
  background: var(--color-destructive-light);
  color: var(--color-destructive);
  padding: 0.75rem 1rem;
  border-radius: var(--radius-md);
  margin-bottom: 1rem;
  font-size: 0.9rem;
}

.success-message {
  background: var(--color-success-light);
  color: var(--color-success);
  padding: 0.75rem 1rem;
  border-radius: var(--radius-md);
  margin-bottom: 1rem;
  font-size: 0.9rem;
}

.auth-switch {
  text-align: center;
  margin-top: 1.5rem;
  color: var(--text-muted);
}

.auth-switch a {
  color: var(--color-primary);
  text-decoration: none;
}

.auth-switch a:hover {
  text-decoration: underline;
}

.resend-section {
  text-align: center;
  margin: 1.5rem 0;
}

.cooldown-text {
  color: var(--text-muted);
  font-size: 0.9rem;
}

.btn-link {
  background: none;
  border: none;
  color: var(--color-primary);
  cursor: pointer;
  font-size: 0.9rem;
  text-decoration: underline;
  padding: 0;
}

.btn-link:hover:not(:disabled) {
  color: var(--gradient-primary-hover);
}

.btn-link:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-secondary {
  width: 100%;
  padding: 0.75rem;
  background: transparent;
  border: 1px solid var(--border-input);
  color: var(--text-muted);
  border-radius: var(--radius-md);
  margin-top: 0.75rem;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-secondary:hover {
  border-color: var(--text-muted);
  color: var(--text-primary);
}
</style>
