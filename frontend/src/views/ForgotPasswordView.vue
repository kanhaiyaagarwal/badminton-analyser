<template>
  <div class="auth-page">
    <div class="auth-container">

      <!-- Step 1: Email input -->
      <template v-if="!showResetStep">
        <div
          v-motion
          :initial="{ opacity: 0, scale: 0.85 }"
          :enter="{ opacity: 1, scale: 1, transition: { duration: 400 } }"
          class="auth-brand"
        ><img src="/mascot/otter-mascot.png" alt="PushUp Pro" class="auth-logo" /></div>

        <h1
          v-motion
          :initial="{ opacity: 0, y: 16 }"
          :enter="{ opacity: 1, y: 0, transition: { delay: 100, duration: 400 } }"
          class="auth-title"
        >Forgot Password</h1>
        <p
          v-motion
          :initial="{ opacity: 0, y: 16 }"
          :enter="{ opacity: 1, y: 0, transition: { delay: 200, duration: 400 } }"
          class="auth-subtitle"
        >Enter your email to receive a reset code</p>

        <div
          v-motion
          :initial="{ opacity: 0, y: 16 }"
          :enter="{ opacity: 1, y: 0, transition: { delay: 300, duration: 400 } }"
          class="auth-form-area"
        >
          <form @submit.prevent="handleForgotPassword">
            <div class="field-group">
              <label for="email">Email</label>
              <input
                id="email"
                v-model="email"
                type="email"
                placeholder="your@email.com"
                required
              />
            </div>

            <div v-if="error" class="msg-error">{{ error }}</div>
            <div v-if="success" class="msg-success">{{ success }}</div>

            <button type="submit" class="btn-primary" :disabled="loading">
              {{ loading ? 'Sending...' : 'Send Reset Code' }}
            </button>
          </form>

          <p class="auth-switch">
            Remember your password?
            <router-link :to="{ path: '/login', query: $route.query }">Login</router-link>
          </p>
        </div>
      </template>

      <!-- Step 2: OTP + New Password -->
      <template v-else>
        <div class="auth-brand"><img src="/mascot/otter-mascot.png" alt="PushUp Pro" class="auth-logo" /></div>
        <h1 class="auth-title">Reset Password</h1>
        <p class="auth-subtitle">Enter the code sent to {{ email }} and your new password</p>

        <div class="auth-form-area">
          <form @submit.prevent="handleResetPassword">
            <div class="field-group">
              <label for="otpCode">Reset Code</label>
              <input
                id="otpCode"
                v-model="otpCode"
                type="text"
                inputmode="numeric"
                pattern="[0-9]{6}"
                maxlength="6"
                placeholder="000000"
                required
                autocomplete="one-time-code"
                class="otp-input"
              />
            </div>

            <div class="field-group">
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

            <div class="field-group">
              <label for="confirmPassword">Confirm Password</label>
              <input
                id="confirmPassword"
                v-model="confirmPassword"
                type="password"
                placeholder="Confirm your password"
                required
              />
            </div>

            <div v-if="resetError" class="msg-error">{{ resetError }}</div>
            <div v-if="resetSuccess" class="msg-success">{{ resetSuccess }}</div>

            <button
              type="submit"
              class="btn-primary"
              :disabled="resetLoading || otpCode.length !== 6"
            >
              {{ resetLoading ? 'Resetting...' : 'Reset Password' }}
            </button>
          </form>

          <div class="resend-section">
            <p v-if="resendCooldown > 0" class="resend-text">
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
      </template>
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
/* ---- Full-page mobile-first auth layout ---- */
.auth-page {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-page);
  padding: 2rem 1.5rem 3rem;
}

.auth-container {
  width: 100%;
  max-width: 400px;
  display: flex;
  flex-direction: column;
  align-items: center;
}

/* ---- Brand logo ---- */
.auth-brand {
  margin-bottom: 1.25rem;
}

.auth-logo {
  width: 56px;
  height: 56px;
  border-radius: 0.875rem;
  box-shadow: var(--shadow-md);
}

/* ---- Typography ---- */
.auth-title {
  font-size: 1.75rem;
  font-weight: 800;
  color: var(--text-primary);
  text-align: center;
  margin-bottom: 0.35rem;
}

.auth-subtitle {
  font-size: 0.95rem;
  color: var(--text-muted);
  text-align: center;
  margin-bottom: 2rem;
}

/* ---- Form area ---- */
.auth-form-area {
  width: 100%;
  background: var(--bg-card);
  border-radius: 1.25rem;
  padding: 2rem 1.75rem;
  box-shadow: var(--shadow-md);
  border: 1px solid var(--border-color);
}

/* ---- Form fields ---- */
.field-group {
  margin-bottom: 1.25rem;
}

.field-group label {
  display: block;
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 0.5rem;
}

.field-group input {
  width: 100%;
  height: 52px;
  padding: 0 1rem;
  border: 2px solid var(--border-input);
  border-radius: 1rem;
  background: var(--bg-input);
  color: var(--text-primary);
  font-size: 1rem;
  font-family: inherit;
  outline: none;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.field-group input:focus {
  border-color: var(--border-input-focus);
  box-shadow: 0 0 0 3px rgba(124, 139, 111, 0.12);
}

.field-group input::placeholder {
  color: var(--text-muted);
}

.otp-input {
  text-align: center;
  font-size: 1.5rem;
  letter-spacing: 0.5rem;
  font-family: 'JetBrains Mono', monospace;
}

/* ---- Buttons ---- */
.btn-primary {
  width: 100%;
  height: 52px;
  background: var(--gradient-primary);
  color: #fff;
  border: none;
  border-radius: 1rem;
  font-size: 1.05rem;
  font-weight: 700;
  font-family: inherit;
  cursor: pointer;
  transition: opacity 0.2s, transform 0.15s;
  margin-top: 0.5rem;
}

.btn-primary:hover:not(:disabled) {
  opacity: 0.92;
  transform: translateY(-1px);
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-secondary {
  width: 100%;
  height: 44px;
  background: transparent;
  border: 1px solid var(--border-input);
  color: var(--text-muted);
  border-radius: 1rem;
  font-size: 0.875rem;
  font-family: inherit;
  cursor: pointer;
  margin-top: 0.75rem;
  transition: border-color 0.2s, color 0.2s;
}

.btn-secondary:hover {
  border-color: var(--text-muted);
  color: var(--text-primary);
}

.btn-link {
  display: block;
  width: 100%;
  text-align: center;
  background: none;
  border: none;
  font-size: 0.875rem;
  color: var(--color-primary);
  text-decoration: underline;
  cursor: pointer;
  font-family: inherit;
  padding: 0;
}

.btn-link:hover:not(:disabled) {
  color: var(--color-primary-hover);
}

.btn-link:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* ---- Auth switch ---- */
.auth-switch {
  text-align: center;
  margin-top: 1.5rem;
  font-size: 0.9rem;
  color: var(--text-muted);
}

.auth-switch a {
  color: var(--color-primary);
  text-decoration: none;
  font-weight: 700;
}

.auth-switch a:hover {
  text-decoration: underline;
}

/* ---- Resend section ---- */
.resend-section {
  text-align: center;
  margin: 1.5rem 0;
}

.resend-text {
  color: var(--text-muted);
  font-size: 0.875rem;
}

/* ---- Messages ---- */
.msg-error {
  background: var(--color-destructive-light);
  color: var(--color-destructive);
  padding: 0.85rem 1rem;
  border-radius: 0.75rem;
  margin-bottom: 1rem;
  font-size: 0.875rem;
  line-height: 1.4;
}

.msg-success {
  background: var(--color-success-light);
  color: var(--color-success);
  padding: 0.85rem 1rem;
  border-radius: 0.75rem;
  margin-bottom: 1rem;
  font-size: 0.875rem;
  text-align: center;
  line-height: 1.4;
}

/* ---- Responsive ---- */
@media (min-width: 640px) {
  .auth-form-area {
    padding: 2.5rem 2rem;
  }
}
</style>
