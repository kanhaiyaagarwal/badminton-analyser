<template>
  <div class="auth-container">
    <!-- Step 1: Signup Form -->
    <div v-if="!showOtpStep" class="auth-card">
      <!-- Default signup: Google first, then invite code, then manual form -->
      <template v-if="!googleNeedsInvite && !googleWaitlisted">
        <h1>Sign Up</h1>
        <p class="subtitle">Create your PushUp Pro account</p>

        <div v-if="googleAvailable" ref="googleBtnContainer" class="google-btn-wrapper"></div>

        <div v-if="googleAvailable" class="divider">
          <span>or sign up with email</span>
        </div>

        <div v-if="error" class="error-message">{{ error }}</div>
        <div v-if="success" class="success-message">{{ success }}</div>

        <form @submit.prevent="handleSignup">
          <div class="form-group">
            <label for="inviteCode">Invite Code <span class="optional">(optional)</span></label>
            <input
              id="inviteCode"
              v-model="inviteCode"
              type="text"
              placeholder="Enter your invite code (or leave blank to join waitlist)"
            />
          </div>

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
      </template>

      <!-- Google invite code step -->
      <template v-else-if="googleNeedsInvite && !googleWaitlisted">
        <h1>Almost there!</h1>
        <p class="subtitle">Enter an invite code to complete sign-up, or join the waitlist.</p>

        <form @submit.prevent="handleGoogleInviteSubmit">
          <div class="form-group">
            <label for="googleInviteCode">Invite Code</label>
            <input
              id="googleInviteCode"
              v-model="googleInviteCode"
              type="text"
              placeholder="Enter your invite code"
              required
            />
          </div>

          <div v-if="error" class="error-message">{{ error }}</div>

          <button type="submit" class="btn-primary" :disabled="loading">
            {{ loading ? 'Signing in...' : 'Continue' }}
          </button>
        </form>

        <button type="button" class="btn-waitlist" @click="handleGoogleWaitlist" :disabled="gwLoading" style="margin-top: 0.75rem;">
          {{ gwLoading ? 'Joining...' : 'Join the Waitlist' }}
        </button>

        <button type="button" class="btn-link" @click="resetGoogleState">Back to sign up</button>
      </template>

      <!-- Waitlisted confirmation -->
      <template v-else>
        <div class="success-message">You've been added to the waitlist! We'll notify you when access is available.</div>
        <button type="button" class="btn-link" @click="resetGoogleState">Back to sign up</button>
      </template>
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
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useGoogleAuth } from '../composables/useGoogleAuth'
import { useAnalytics } from '../composables/useAnalytics'
import api from '../api/client'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const analytics = useAnalytics()
const { isAvailable: googleAvailable, renderButton } = useGoogleAuth()

// Step 1: Signup form
const email = ref('')
const password = ref('')
const confirmPassword = ref('')
const inviteCode = ref(route.query.invite || '')
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

// Google OAuth state
const googleBtnContainer = ref(null)
const googleNeedsInvite = ref(false)
const googleWaitlisted = ref(false)
const googleInviteCode = ref('')
const storedCredential = ref('')
const storedGoogleEmail = ref('')
const storedGoogleName = ref('')
const gwLoading = ref(false)

// Check if returning to page with pending verification
onMounted(async () => {
  if (authStore.pendingVerification) {
    pendingUserId.value = authStore.pendingVerification.userId
    pendingEmail.value = authStore.pendingVerification.email
    showOtpStep.value = true
  }
  if (googleAvailable && !showOtpStep.value) {
    await nextTick()
    if (googleBtnContainer.value) {
      renderButton(googleBtnContainer.value, handleGoogleCallback)
    }
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

    if (response.status === 'waitlisted') {
      // User was auto-added to waitlist (no invite code)
      success.value = response.message
    } else if (response.requires_verification) {
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
      analytics.signupCompleted('email')
      otpSuccess.value = 'Email verified! Signing you in...'
      const redirect = route.query.redirect
      setTimeout(() => {
        if (redirect) {
          router.push(redirect)
        } else {
          router.push('/challenges/pushup/session')
        }
      }, 1000)
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

async function handleGoogleCallback(credential) {
  loading.value = true
  error.value = ''

  try {
    const inviteFromUrl = route.query.invite || ''
    const data = await authStore.loginWithGoogle(credential, inviteFromUrl)

    if (data.access_token) {
      analytics.signupCompleted('google')
      router.push(route.query.redirect || '/hub')
    } else if (data.status === 'needs_invite') {
      storedCredential.value = credential
      storedGoogleEmail.value = data.email
      storedGoogleName.value = data.name
      googleNeedsInvite.value = true
    }
  } catch (err) {
    error.value = err.response?.data?.detail || 'Google sign-in failed.'
  } finally {
    loading.value = false
  }
}

async function handleGoogleInviteSubmit() {
  loading.value = true
  error.value = ''

  try {
    const data = await authStore.loginWithGoogle(storedCredential.value, googleInviteCode.value)
    if (data.access_token) {
      router.push(route.query.redirect || '/hub')
    }
  } catch (err) {
    error.value = err.response?.data?.detail || 'Invalid invite code.'
  } finally {
    loading.value = false
  }
}

async function handleGoogleWaitlist() {
  gwLoading.value = true
  error.value = ''

  try {
    await api.post('/api/v1/admin/join-waitlist', {
      email: storedGoogleEmail.value,
      name: storedGoogleName.value || null
    })
    googleWaitlisted.value = true
  } catch (err) {
    error.value = err.response?.data?.detail || 'Failed to join waitlist.'
  } finally {
    gwLoading.value = false
  }
}

function resetGoogleState() {
  googleNeedsInvite.value = false
  googleWaitlisted.value = false
  googleInviteCode.value = ''
  storedCredential.value = ''
  error.value = ''
  nextTick(() => {
    if (googleAvailable && googleBtnContainer.value) {
      renderButton(googleBtnContainer.value, handleGoogleCallback)
    }
  })
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

.optional {
  color: var(--text-muted);
  font-weight: 400;
  font-size: 0.85rem;
}

.divider {
  display: flex;
  align-items: center;
  margin: 1.5rem 0;
  color: var(--text-muted);
  font-size: 0.85rem;
}

.divider::before,
.divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: var(--border-color);
}

.divider span {
  padding: 0 1rem;
}

.google-btn-wrapper {
  display: flex;
  justify-content: center;
  align-items: center;
  margin-bottom: 0.5rem;
  width: 100%;
}

.google-btn-wrapper :deep(div),
.google-btn-wrapper :deep(iframe) {
  margin-left: auto !important;
  margin-right: auto !important;
}

.waitlist-section {
  margin-top: 1.5rem;
  padding-top: 1.5rem;
  border-top: 1px solid var(--border-color);
  text-align: center;
}

.waitlist-text {
  color: var(--text-muted);
  margin-bottom: 0.75rem;
}

.btn-waitlist {
  background: transparent;
  border: 1px solid var(--color-primary);
  color: var(--color-primary);
  padding: 0.75rem 1.5rem;
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all 0.2s;
}

.btn-waitlist:hover {
  background: var(--color-primary-light);
}

.modal-overlay {
  position: fixed;
  inset: 0;
  background: var(--bg-overlay);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 1rem;
}

.modal-content {
  background: var(--bg-card);
  padding: 2rem;
  border-radius: var(--radius-lg);
  width: 100%;
  max-width: 400px;
  box-shadow: var(--shadow-lg);
  border: 1px solid var(--border-color);
}

.modal-content h2 {
  color: var(--color-primary);
  margin-bottom: 0.5rem;
}

.modal-desc {
  color: var(--text-muted);
  margin-bottom: 1.5rem;
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
  color: var(--color-primary-hover);
}

.btn-link:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
