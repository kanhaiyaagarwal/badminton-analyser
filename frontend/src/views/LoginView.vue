<template>
  <div class="auth-page">
    <div class="auth-container">

      <!-- Default: Google button first, then email/password form -->
      <template v-if="!googleNeedsInvite && !googleWaitlisted">
        <!-- Mascot + Brand -->
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
        >Welcome back</h1>
        <p
          v-motion
          :initial="{ opacity: 0, y: 16 }"
          :enter="{ opacity: 1, y: 0, transition: { delay: 200, duration: 400 } }"
          class="auth-subtitle"
        >Sign in to your account</p>

        <div
          v-motion
          :initial="{ opacity: 0, y: 16 }"
          :enter="{ opacity: 1, y: 0, transition: { delay: 300, duration: 400 } }"
          class="auth-form-area"
        >
          <div v-if="googleAvailable" ref="googleBtnContainer" class="google-btn-wrapper"></div>

          <div v-if="googleAvailable" class="divider">
            <span>or sign in with email</span>
          </div>

          <div v-if="error && !isLocked" class="msg-error">{{ error }}</div>
          <div v-if="error && isLocked" class="msg-error">
            {{ error }}
            <router-link
              :to="{ path: '/forgot-password', query: $route.query }"
              class="error-link"
            >Reset Password</router-link>
          </div>

          <form @submit.prevent="handleLogin">
            <div class="field-group">
              <label for="email">Email</label>
              <input
                id="email"
                v-model="email"
                type="email"
                placeholder="Enter your email"
                required
              />
            </div>

            <div class="field-group">
              <label for="password">Password</label>
              <input
                id="password"
                v-model="password"
                type="password"
                placeholder="Enter your password"
                required
              />
              <router-link
                :to="{ path: '/forgot-password', query: $route.query }"
                class="forgot-link"
              >Forgot password?</router-link>
            </div>

            <button type="submit" class="btn-primary" :disabled="loading">
              {{ loading ? 'Logging in...' : 'Login & Start' }}
            </button>
          </form>

          <p class="auth-switch">
            New user?
            <router-link :to="{ path: '/signup', query: $route.query }">Sign up</router-link>
          </p>
        </div>
      </template>

      <!-- Invite code step (new Google user without invite) -->
      <template v-else-if="googleNeedsInvite && !googleWaitlisted">
        <div class="auth-brand"><img src="/mascot/otter-mascot.png" alt="PushUp Pro" class="auth-logo" /></div>
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

          <button
            type="button"
            @click="handleGoogleWaitlist"
            :disabled="waitlistLoading"
            class="btn-outline"
          >
            {{ waitlistLoading ? 'Joining...' : 'Join the Waitlist' }}
          </button>

          <button type="button" @click="resetGoogleState" class="btn-link">Back to login</button>
        </div>
      </template>

      <!-- Waitlisted confirmation -->
      <template v-else>
        <div class="auth-brand"><img src="/mascot/otter-mascot.png" alt="PushUp Pro" class="auth-logo" /></div>
        <div class="auth-form-area">
          <div class="msg-success">You've been added to the waitlist! We'll notify you when access is available.</div>
          <button type="button" @click="resetGoogleState" class="btn-link">Back to login</button>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useGoogleAuth } from '../composables/useGoogleAuth'
import api from '../api/client'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const { isAvailable: googleAvailable, renderButton } = useGoogleAuth()

const email = ref('')
const password = ref('')
const loading = ref(false)
const error = ref('')
const isLocked = ref(false)

// Google OAuth state
const googleBtnContainer = ref(null)
const googleNeedsInvite = ref(false)
const googleWaitlisted = ref(false)
const googleInviteCode = ref('')
const storedCredential = ref('')
const storedGoogleEmail = ref('')
const storedGoogleName = ref('')
const waitlistLoading = ref(false)

onMounted(async () => {
  if (googleAvailable) {
    await nextTick()
    if (googleBtnContainer.value) {
      renderButton(googleBtnContainer.value, handleGoogleCallback)
    }
  }
})

async function handleLogin() {
  loading.value = true
  error.value = ''
  isLocked.value = false

  try {
    await authStore.login(email.value, password.value)
    const redirect = route.query.redirect
    if (redirect) {
      router.push(redirect)
    } else {
      router.push('/hub')
    }
  } catch (err) {
    const status = err.response?.status
    const detail = err.response?.data?.detail || ''
    if (status === 403 && detail.includes('Account locked')) {
      isLocked.value = true
      error.value = detail
    } else {
      error.value = detail || 'Login failed. Please try again.'
    }
  } finally {
    loading.value = false
  }
}

async function handleGoogleCallback(credential) {
  loading.value = true
  error.value = ''

  try {
    const inviteFromUrl = route.query.invite || ''
    const data = await authStore.loginWithGoogle(credential, inviteFromUrl)

    if (data.access_token) {
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
  waitlistLoading.value = true
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
    waitlistLoading.value = false
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

/* ---- Form area (full-width card on mobile, elevated on desktop) ---- */
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

/* ---- Forgot link ---- */
.forgot-link {
  display: block;
  text-align: right;
  margin-top: 0.5rem;
  font-size: 0.8rem;
  color: var(--text-muted);
  text-decoration: none;
}

.forgot-link:hover {
  color: var(--color-primary);
  text-decoration: underline;
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

.error-link {
  display: block;
  margin-top: 0.5rem;
  color: var(--color-primary);
  font-weight: 700;
  text-decoration: underline;
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

/* ---- Responsive: larger card on desktop ---- */
@media (min-width: 640px) {
  .auth-form-area {
    padding: 2.5rem 2rem;
  }
}
</style>
