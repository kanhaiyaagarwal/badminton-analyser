<template>
  <div class="auth-container">
    <!-- Step 1: Signup Form -->
    <div v-if="!showOtpStep" class="auth-card">
      <h1>Sign Up</h1>
      <p class="subtitle">Create your Badminton Analyzer account</p>

      <form @submit.prevent="handleSignup">
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

        <div class="form-group">
          <label for="password">Password</label>
          <input
            id="password"
            v-model="password"
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

        <div class="form-group">
          <label for="inviteCode">Invite Code</label>
          <input
            id="inviteCode"
            v-model="inviteCode"
            type="text"
            placeholder="Enter your invite code"
            required
          />
        </div>

        <div v-if="error" class="error-message">{{ error }}</div>
        <div v-if="success" class="success-message">{{ success }}</div>

        <button type="submit" class="btn-primary" :disabled="loading">
          {{ loading ? 'Creating account...' : 'Sign Up' }}
        </button>
      </form>

      <p class="auth-switch">
        Already have an account?
        <router-link :to="{ path: '/login', query: $route.query }">Login</router-link>
      </p>

      <div class="waitlist-section">
        <p class="waitlist-text">Don't have an invite code?</p>
        <button type="button" @click="showWaitlist = true" class="btn-waitlist">
          Join the Waitlist
        </button>
      </div>
    </div>

    <!-- Step 2: OTP Verification -->
    <div v-else class="auth-card">
      <h1>Verify Email</h1>
      <p class="subtitle">Enter the 6-digit code sent to {{ pendingEmail }}</p>

      <form @submit.prevent="handleVerifyOtp">
        <div class="form-group">
          <label for="otpCode">Verification Code</label>
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

        <div v-if="otpError" class="error-message">{{ otpError }}</div>
        <div v-if="otpSuccess" class="success-message">{{ otpSuccess }}</div>

        <button type="submit" class="btn-primary" :disabled="otpLoading || otpCode.length !== 6">
          {{ otpLoading ? 'Verifying...' : 'Verify Email' }}
        </button>
      </form>

      <div class="resend-section">
        <p v-if="resendCooldown > 0" class="cooldown-text">
          Resend code in {{ resendCooldown }}s
        </p>
        <button
          v-else
          type="button"
          @click="handleResendOtp"
          class="btn-link"
          :disabled="resendLoading"
        >
          {{ resendLoading ? 'Sending...' : "Didn't receive a code? Resend" }}
        </button>
      </div>

      <button type="button" @click="goBackToSignup" class="btn-secondary">
        Back to Sign Up
      </button>
    </div>

    <!-- Waitlist Modal -->
    <div v-if="showWaitlist" class="modal-overlay" @click="showWaitlist = false">
      <div class="modal-content" @click.stop>
        <h2>Join the Waitlist</h2>
        <p class="modal-desc">Enter your email and we'll notify you when access is available.</p>

        <form @submit.prevent="handleWaitlist">
          <div class="form-group">
            <label for="waitlistEmail">Email</label>
            <input
              id="waitlistEmail"
              v-model="waitlistEmail"
              type="email"
              placeholder="your@email.com"
              required
            />
          </div>

          <div class="form-group">
            <label for="waitlistName">Name (optional)</label>
            <input
              id="waitlistName"
              v-model="waitlistName"
              type="text"
              placeholder="Your name"
            />
          </div>

          <div v-if="waitlistError" class="error-message">{{ waitlistError }}</div>
          <div v-if="waitlistSuccess" class="success-message">{{ waitlistSuccess }}</div>

          <button type="submit" class="btn-primary" :disabled="waitlistLoading">
            {{ waitlistLoading ? 'Joining...' : 'Join Waitlist' }}
          </button>

          <button type="button" @click="showWaitlist = false" class="btn-secondary">
            Cancel
          </button>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import api from '../api/client'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

// Step 1: Signup form
const email = ref('')
const password = ref('')
const confirmPassword = ref('')
const inviteCode = ref('')
const loading = ref(false)
const error = ref('')
const success = ref('')

// Step 2: OTP verification
const showOtpStep = ref(false)
const pendingUserId = ref(null)
const pendingEmail = ref('')
const otpCode = ref('')
const otpLoading = ref(false)
const otpError = ref('')
const otpSuccess = ref('')
const resendCooldown = ref(0)
const resendLoading = ref(false)

let cooldownTimer = null

// Waitlist
const showWaitlist = ref(false)
const waitlistEmail = ref('')
const waitlistName = ref('')
const waitlistLoading = ref(false)
const waitlistError = ref('')
const waitlistSuccess = ref('')

// Check if returning to page with pending verification
onMounted(() => {
  if (authStore.pendingVerification) {
    pendingUserId.value = authStore.pendingVerification.userId
    pendingEmail.value = authStore.pendingVerification.email
    showOtpStep.value = true
  }
})

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

async function handleSignup() {
  error.value = ''
  success.value = ''

  if (password.value !== confirmPassword.value) {
    error.value = 'Passwords do not match'
    return
  }

  loading.value = true

  try {
    const username = email.value.split('@')[0]
    const response = await authStore.signup(email.value, username, password.value, inviteCode.value)

    if (response.requires_verification) {
      // Show OTP verification step
      pendingUserId.value = response.user_id
      pendingEmail.value = response.email
      showOtpStep.value = true
      startCooldownTimer(60) // Start initial cooldown
    } else {
      // Email verification disabled - redirect to login
      success.value = response.message || 'Account created! Redirecting to login...'
      const loginQuery = route.query.redirect ? { redirect: route.query.redirect } : {}
      setTimeout(() => router.push({ path: '/login', query: loginQuery }), 1500)
    }
  } catch (err) {
    error.value = err.response?.data?.detail || 'Signup failed. Please try again.'
  } finally {
    loading.value = false
  }
}

async function handleVerifyOtp() {
  otpError.value = ''
  otpSuccess.value = ''
  otpLoading.value = true

  try {
    const response = await authStore.verifyEmail(pendingUserId.value, otpCode.value)
    if (response.success) {
      otpSuccess.value = 'Email verified! Redirecting to login...'
      const loginQuery = route.query.redirect ? { redirect: route.query.redirect } : { new: '1' }
      setTimeout(() => router.push({ path: '/login', query: loginQuery }), 1500)
    } else {
      otpError.value = response.message
    }
  } catch (err) {
    otpError.value = err.response?.data?.detail || 'Verification failed. Please try again.'
  } finally {
    otpLoading.value = false
  }
}

async function handleResendOtp() {
  otpError.value = ''
  otpSuccess.value = ''
  resendLoading.value = true

  try {
    const response = await authStore.resendOTP(pendingUserId.value)
    if (response.success) {
      otpSuccess.value = response.message
      otpCode.value = '' // Clear old code
      startCooldownTimer(60)
    } else {
      otpError.value = response.message
      if (response.cooldown_seconds > 0) {
        startCooldownTimer(response.cooldown_seconds)
      }
    }
  } catch (err) {
    otpError.value = err.response?.data?.detail || 'Failed to resend code.'
  } finally {
    resendLoading.value = false
  }
}

function goBackToSignup() {
  authStore.clearPendingVerification()
  showOtpStep.value = false
  pendingUserId.value = null
  pendingEmail.value = ''
  otpCode.value = ''
  otpError.value = ''
  otpSuccess.value = ''
  resendCooldown.value = 0
  if (cooldownTimer) {
    clearInterval(cooldownTimer)
    cooldownTimer = null
  }
}

async function handleWaitlist() {
  waitlistError.value = ''
  waitlistSuccess.value = ''
  waitlistLoading.value = true

  try {
    const response = await api.post('/api/v1/admin/join-waitlist', {
      email: waitlistEmail.value,
      name: waitlistName.value || null
    })
    waitlistSuccess.value = response.data.message
    setTimeout(() => {
      showWaitlist.value = false
      waitlistEmail.value = ''
      waitlistName.value = ''
      waitlistSuccess.value = ''
    }, 3000)
  } catch (err) {
    waitlistError.value = err.response?.data?.detail || 'Failed to join waitlist.'
  } finally {
    waitlistLoading.value = false
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
  background: #16213e;
  padding: 3rem;
  border-radius: 12px;
  width: 100%;
  max-width: 400px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
}

h1 {
  color: #4ecca3;
  margin-bottom: 0.5rem;
  text-align: center;
}

.subtitle {
  color: #888;
  text-align: center;
  margin-bottom: 2rem;
}

.form-group {
  margin-bottom: 1.25rem;
}

label {
  display: block;
  margin-bottom: 0.5rem;
  color: #ccc;
}

input {
  width: 100%;
  padding: 0.75rem 1rem;
  border: 2px solid #2a2a4a;
  border-radius: 8px;
  background: #1a1a2e;
  color: #eee;
  font-size: 1rem;
  transition: border-color 0.2s;
}

input:focus {
  outline: none;
  border-color: #4ecca3;
}

.btn-primary {
  width: 100%;
  padding: 1rem;
  background: #4ecca3;
  color: #1a1a2e;
  border: none;
  border-radius: 8px;
  font-size: 1rem;
  font-weight: bold;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-primary:hover:not(:disabled) {
  background: #3db892;
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.error-message {
  background: rgba(231, 76, 60, 0.2);
  color: #e74c3c;
  padding: 0.75rem 1rem;
  border-radius: 8px;
  margin-bottom: 1rem;
  font-size: 0.9rem;
}

.success-message {
  background: rgba(78, 204, 163, 0.2);
  color: #4ecca3;
  padding: 0.75rem 1rem;
  border-radius: 8px;
  margin-bottom: 1rem;
  font-size: 0.9rem;
}

.auth-switch {
  text-align: center;
  margin-top: 1.5rem;
  color: #888;
}

.auth-switch a {
  color: #4ecca3;
  text-decoration: none;
}

.auth-switch a:hover {
  text-decoration: underline;
}

.waitlist-section {
  margin-top: 1.5rem;
  padding-top: 1.5rem;
  border-top: 1px solid #2a2a4a;
  text-align: center;
}

.waitlist-text {
  color: #888;
  margin-bottom: 0.75rem;
}

.btn-waitlist {
  background: transparent;
  border: 1px solid #4ecca3;
  color: #4ecca3;
  padding: 0.75rem 1.5rem;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-waitlist:hover {
  background: rgba(78, 204, 163, 0.1);
}

.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 1rem;
}

.modal-content {
  background: #16213e;
  padding: 2rem;
  border-radius: 12px;
  width: 100%;
  max-width: 400px;
}

.modal-content h2 {
  color: #4ecca3;
  margin-bottom: 0.5rem;
}

.modal-desc {
  color: #888;
  margin-bottom: 1.5rem;
}

.btn-secondary {
  width: 100%;
  padding: 0.75rem;
  background: transparent;
  border: 1px solid #3a3a5a;
  color: #888;
  border-radius: 8px;
  margin-top: 0.75rem;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-secondary:hover {
  border-color: #888;
  color: #eee;
}

/* OTP Step Styles */
.otp-input {
  text-align: center;
  font-size: 1.5rem;
  letter-spacing: 0.5rem;
  font-family: monospace;
}

.resend-section {
  text-align: center;
  margin: 1.5rem 0;
}

.cooldown-text {
  color: #888;
  font-size: 0.9rem;
}

.btn-link {
  background: none;
  border: none;
  color: #4ecca3;
  cursor: pointer;
  font-size: 0.9rem;
  text-decoration: underline;
  padding: 0;
}

.btn-link:hover:not(:disabled) {
  color: #3db892;
}

.btn-link:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
