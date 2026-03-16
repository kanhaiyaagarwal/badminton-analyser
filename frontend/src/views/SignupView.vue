<template>
  <div class="auth-page">
    <div class="auth-container">

      <!-- Step 1: Signup Form -->
      <template v-if="!showOtpStep">
        <template v-if="!googleNeedsInvite && !googleWaitlisted">
          <div
            v-motion
            :initial="{ opacity: 0, scale: 0.85 }"
            :enter="{ opacity: 1, scale: 1, transition: { duration: 400 } }"
            class="auth-brand"
          ><img v-if="!isBadminton" src="/mascot/otter-mascot.png" :alt="appName" class="auth-logo" /><span v-else class="auth-logo-text">{{ appName }}</span></div>

          <h1
            v-motion
            :initial="{ opacity: 0, y: 16 }"
            :enter="{ opacity: 1, y: 0, transition: { delay: 100, duration: 400 } }"
            class="auth-title"
          >Sign Up</h1>
          <p
            v-motion
            :initial="{ opacity: 0, y: 16 }"
            :enter="{ opacity: 1, y: 0, transition: { delay: 200, duration: 400 } }"
            class="auth-subtitle"
          >Create your {{ appName }} account</p>

          <div
            v-motion
            :initial="{ opacity: 0, y: 16 }"
            :enter="{ opacity: 1, y: 0, transition: { delay: 300, duration: 400 } }"
            class="auth-form-area"
          >
            <div v-if="googleAvailable" ref="googleBtnContainer" class="google-btn-wrapper"></div>

            <div v-if="googleAvailable" class="divider">
              <span>or sign up with email</span>
            </div>

            <div v-if="error" class="msg-error">{{ error }}</div>
            <div v-if="success" class="msg-success">{{ success }}</div>

            <form @submit.prevent="handleSignup">
              <div class="field-group">
                <label for="inviteCode">Invite Code <span class="label-optional">(optional)</span></label>
                <input
                  id="inviteCode"
                  v-model="inviteCode"
                  type="text"
                  placeholder="Enter invite code or leave blank"
                />
              </div>

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

              <div class="field-group">
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

              <button type="submit" class="btn-primary" :disabled="loading">
                {{ loading ? 'Creating account...' : 'Sign Up' }}
              </button>
            </form>

            <p class="auth-switch">
              Already have an account?
              <router-link :to="{ path: '/login', query: $route.query }">Login</router-link>
            </p>

            <div class="waitlist-divider">
              <p class="waitlist-text">Don't have an invite code?</p>
              <button type="button" @click="showWaitlist = true" class="btn-outline-sm">
                Join the Waitlist
              </button>
            </div>
          </div>
        </template>

        <!-- Google invite code step -->
        <template v-else-if="googleNeedsInvite && !googleWaitlisted">
          <div class="auth-brand"><img v-if="!isBadminton" src="/mascot/otter-mascot.png" :alt="appName" class="auth-logo" /><span v-else class="auth-logo-text">{{ appName }}</span></div>
          <h1 class="auth-title" style="color: var(--color-primary)">Almost there!</h1>
          <p class="auth-subtitle">Enter an invite code to complete sign-up, or join the waitlist.</p>

          <div class="auth-form-area">
            <form @submit.prevent="handleGoogleInviteSubmit">
              <div class="field-group">
                <label for="googleInviteCode">Invite Code</label>
                <input
                  id="googleInviteCode"
                  v-model="googleInviteCode"
                  type="text"
                  placeholder="Enter your invite code"
                  required
                />
              </div>

              <div v-if="error" class="msg-error">{{ error }}</div>

              <button type="submit" class="btn-primary" :disabled="loading">
                {{ loading ? 'Signing in...' : 'Continue' }}
              </button>
            </form>

            <button type="button" @click="handleGoogleWaitlist" :disabled="gwLoading" class="btn-outline">
              {{ gwLoading ? 'Joining...' : 'Join the Waitlist' }}
            </button>

            <button type="button" @click="resetGoogleState" class="btn-link">Back to sign up</button>
          </div>
        </template>

        <!-- Waitlisted confirmation -->
        <template v-else>
          <div class="auth-brand"><img v-if="!isBadminton" src="/mascot/otter-mascot.png" :alt="appName" class="auth-logo" /><span v-else class="auth-logo-text">{{ appName }}</span></div>
          <div class="auth-form-area">
            <div class="msg-success">You've been added to the waitlist! We'll notify you when access is available.</div>
            <button type="button" @click="resetGoogleState" class="btn-link">Back to sign up</button>
          </div>
        </template>
      </template>

      <!-- Step 2: OTP Verification -->
      <template v-else>
        <div
          v-motion
          :initial="{ opacity: 0, scale: 0.85 }"
          :enter="{ opacity: 1, scale: 1, transition: { duration: 400 } }"
          class="auth-brand"
        ><img v-if="!isBadminton" src="/mascot/otter-mascot.png" :alt="appName" class="auth-logo" /><span v-else class="auth-logo-text">{{ appName }}</span></div>

        <h1 class="auth-title">Verify Email</h1>
        <p class="auth-subtitle">Enter the 6-digit code sent to {{ pendingEmail }}</p>

        <div class="auth-form-area">
          <form @submit.prevent="handleVerifyOtp">
            <div class="field-group">
              <label for="otpCode">Verification Code</label>
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

            <div v-if="otpError" class="msg-error">{{ otpError }}</div>
            <div v-if="otpSuccess" class="msg-success">{{ otpSuccess }}</div>

            <button type="submit" class="btn-primary" :disabled="otpLoading || otpCode.length !== 6">
              {{ otpLoading ? 'Verifying...' : 'Verify Email' }}
            </button>
          </form>

          <div class="resend-section">
            <p v-if="resendCooldown > 0" class="resend-text">
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
      </template>
    </div>

    <!-- Waitlist Modal -->
    <div v-if="showWaitlist" class="modal-overlay" @click="showWaitlist = false">
      <div class="modal-card" @click.stop>
        <h2 class="modal-title">Join the Waitlist</h2>
        <p class="modal-desc">Enter your email and we'll notify you when access is available.</p>

        <form @submit.prevent="handleWaitlist">
          <div class="field-group">
            <label for="waitlistEmail">Email</label>
            <input id="waitlistEmail" v-model="waitlistEmail" type="email" placeholder="your@email.com" required />
          </div>

          <div class="field-group">
            <label for="waitlistName">Name (optional)</label>
            <input id="waitlistName" v-model="waitlistName" type="text" placeholder="Your name" />
          </div>

          <div v-if="waitlistError" class="msg-error">{{ waitlistError }}</div>
          <div v-if="waitlistSuccess" class="msg-success">{{ waitlistSuccess }}</div>

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
import { useAppMode } from '../composables/useAppMode'
import api from '../api/client'

const { isBadminton, appName } = useAppMode()
const defaultHome = isBadminton.value ? '/dashboard' : '/challenges'

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
      success.value = response.message
    } else if (response.requires_verification) {
      pendingUserId.value = response.user_id
      pendingEmail.value = response.email
      showOtpStep.value = true
      startCooldownTimer(60)
    } else {
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
          router.push(defaultHome)
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
      otpCode.value = ''
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
      router.push(route.query.redirect || defaultHome)
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
      router.push(route.query.redirect || defaultHome)
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

.label-optional {
  font-weight: 400;
  font-size: 0.8rem;
  color: var(--text-muted);
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

.btn-outline {
  width: 100%;
  height: 48px;
  background: transparent;
  border: 2px solid var(--color-primary);
  color: var(--color-primary);
  border-radius: 1rem;
  font-size: 0.95rem;
  font-weight: 600;
  font-family: inherit;
  cursor: pointer;
  margin-top: 0.75rem;
  transition: background 0.2s;
}

.btn-outline:hover:not(:disabled) {
  background: var(--color-primary-light);
}

.btn-outline:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-outline-sm {
  background: transparent;
  border: 2px solid var(--color-primary);
  color: var(--color-primary);
  border-radius: 1rem;
  padding: 0.6rem 1.5rem;
  font-size: 0.875rem;
  font-weight: 600;
  font-family: inherit;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-outline-sm:hover {
  background: var(--color-primary-light);
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
  margin-top: 1rem;
  background: none;
  border: none;
  font-size: 0.875rem;
  color: var(--text-muted);
  text-decoration: underline;
  cursor: pointer;
  font-family: inherit;
}

.btn-link:hover {
  color: var(--color-primary);
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

/* ---- Waitlist section ---- */
.waitlist-divider {
  margin-top: 1.5rem;
  padding-top: 1.5rem;
  border-top: 1px solid var(--border-color);
  text-align: center;
}

.waitlist-text {
  color: var(--text-muted);
  font-size: 0.875rem;
  margin-bottom: 0.75rem;
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

/* ---- Divider ---- */
.divider {
  display: flex;
  align-items: center;
  margin: 1.25rem 0;
  color: var(--text-muted);
  font-size: 0.8rem;
}

.divider::before,
.divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: var(--border-color);
}

.divider span {
  padding: 0 0.75rem;
}

/* ---- Google ---- */
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

/* ---- Modal ---- */
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

.modal-card {
  background: var(--bg-card);
  padding: 2rem 1.75rem;
  border-radius: 1.25rem;
  width: 100%;
  max-width: 400px;
  box-shadow: var(--shadow-xl);
  border: 1px solid var(--border-color);
}

.modal-title {
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--color-primary);
  margin-bottom: 0.35rem;
}

.modal-desc {
  font-size: 0.9rem;
  color: var(--text-muted);
  margin-bottom: 1.5rem;
}

.auth-logo-text {
  font-size: 2rem;
  font-weight: 800;
  color: var(--color-primary);
}

/* ---- Responsive ---- */
@media (min-width: 640px) {
  .auth-form-area,
  .modal-card {
    padding: 2.5rem 2rem;
  }
}
</style>
