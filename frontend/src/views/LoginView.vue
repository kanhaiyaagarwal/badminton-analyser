<template>
  <div class="login-page">
    <!-- Logo -->
    <div class="brand-header">
      <div class="brand-logo">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="32" height="32" stroke-linecap="round" stroke-linejoin="round">
          <path d="M6.5 6.5a3.5 3.5 0 1 0-3.5 3.5h3.5V6.5z"/>
          <path d="M6.5 6.5a3.5 3.5 0 1 1 3.5 3.5H6.5V6.5z"/>
          <path d="M6.5 17.5a3.5 3.5 0 1 0 3.5-3.5H6.5v3.5z"/>
          <path d="M17.5 6.5a3.5 3.5 0 1 0-3.5 3.5h3.5V6.5z"/>
          <path d="M17.5 17.5a3.5 3.5 0 1 1-3.5-3.5h3.5v3.5z"/>
          <path d="M6.5 17.5a3.5 3.5 0 1 1-3.5-3.5h3.5v3.5z"/>
        </svg>
      </div>
      <span class="brand-name">PushUp Pro</span>
    </div>

    <!-- Hero image grid -->
    <section class="hero-grid">
      <div class="hero-col hero-col-left">
        <div class="grid-item grid-main">
          <img src="/hero-gym.jpg" alt="Outdoor pushup" class="grid-img" />
        </div>
        <div class="grid-item grid-stat">
          <div class="stat-card">
            <span class="stat-number">1000+</span>
            <span class="stat-text">Pushups completed this week</span>
          </div>
        </div>
      </div>
      <div class="hero-col hero-col-right">
        <div class="grid-item grid-half">
          <img src="/hero-runner.jpg" alt="Fitness training" class="grid-img" />
        </div>
        <div class="grid-item grid-half">
          <img src="/hero-pushup.jpg" alt="Fitness training" class="grid-img img-lower" />
        </div>
      </div>
    </section>

    <!-- Headline -->
    <section class="headline-section">
      <h1 class="headline">Challenge Yourself</h1>
      <p class="headline-sub">Track your pushup progress, compete with others, and achieve your fitness goals.</p>
    </section>

    <!-- Login form -->
    <section class="form-section">
      <div class="auth-card">
        <form @submit.prevent="handleLogin">
          <div class="form-group">
            <label for="email">Email</label>
            <input
              id="email"
              v-model="email"
              type="email"
              placeholder="Enter your email"
              required
            />
          </div>

          <div class="form-group">
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

          <div v-if="error" class="error-message">
            {{ error }}
            <router-link
              v-if="isLocked"
              :to="{ path: '/forgot-password', query: $route.query }"
              class="reset-link"
            >Reset Password</router-link>
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
    </section>

    <!-- Feature cards -->
    <section class="features-section">
      <h2 class="features-title">Why Choose PushUp Pro?</h2>
      <div class="features-grid">
        <div class="feature-card">
          <div class="feature-icon icon-blue">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="28" height="28">
              <polyline points="2 12 7 4 12 15 17 8 22 12" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </div>
          <h3>Real-time Tracking</h3>
          <p>Use your camera to track pushups in real-time with AI-powered form detection</p>
        </div>
        <div class="feature-card">
          <div class="feature-icon icon-purple">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="28" height="28">
              <path d="M6 9H4.5a2.5 2.5 0 010-5C7 4 7 7 7 7m11-2h1.5a2.5 2.5 0 000-5C17 0 17 3 17 3M8 9h8l1 12H7L8 9z" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </div>
          <h3>Compete & Win</h3>
          <p>Challenge yourself and compete with others on the global leaderboard</p>
        </div>
        <div class="feature-card">
          <div class="feature-icon icon-green">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="28" height="28">
              <polyline points="3 17 8 11 13 15 21 5" stroke-linecap="round" stroke-linejoin="round"/>
              <polyline points="17 5 21 5 21 9" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </div>
          <h3>Track Progress</h3>
          <p>Monitor your improvement over time with detailed statistics and insights</p>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const email = ref('')
const password = ref('')
const loading = ref(false)
const error = ref('')
const isLocked = ref(false)

async function handleLogin() {
  loading.value = true
  error.value = ''
  isLocked.value = false

  try {
    await authStore.login(email.value, password.value)
    const redirect = route.query.redirect
    if (redirect) {
      router.push(redirect)
    } else if (authStore.user?.is_admin) {
      router.push('/hub')
    } else if (route.query.new === '1') {
      router.push('/challenges/pushup/session')
    } else {
      router.push('/challenges/pushup')
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
</script>

<style scoped>
.login-page {
  max-width: 900px;
  margin: 0 auto;
  padding: 2rem 1.5rem 4rem;
}

/* ---- Brand header ---- */
.brand-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 2rem;
}

.brand-logo {
  width: 44px;
  height: 44px;
  background: var(--gradient-primary);
  border-radius: var(--radius-lg);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
}

.brand-logo svg {
  width: 24px;
  height: 24px;
}

.brand-name {
  font-size: 1.4rem;
  font-weight: 500;
  letter-spacing: -0.01em;
  background: var(--gradient-primary);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

/* ---- Hero image grid ---- */
.hero-grid {
  display: flex;
  gap: 1.25rem;
  height: 612px;
  margin-bottom: 3rem;
}

.hero-col {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.hero-col-left {
  flex: 1.2;
}

.hero-col-right {
  flex: 1;
}

.grid-item {
  border-radius: 1.25rem;
  overflow: hidden;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
  transition: transform 0.35s ease, box-shadow 0.35s ease;
}

.grid-item:hover {
  transform: scale(1.05);
  box-shadow: 0 14px 36px rgba(0, 0, 0, 0.16);
}

.grid-main {
  flex: 4;
}

.grid-half {
  flex: 1;
}

.grid-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  border-radius: 1.25rem;
}

.img-lower {
  object-position: center 0%;
}

.grid-stat {
  flex: 1;
}

.stat-card {
  width: 100%;
  height: 100%;
  background: var(--gradient-primary);
  border-radius: 1.25rem;
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.stat-number {
  font-size: 2.5rem;
  font-weight: 800;
  color: #fff;
  line-height: 1;
  margin-bottom: 0.25rem;
}

.stat-text {
  color: rgba(255, 255, 255, 0.85);
  font-size: 0.9rem;
  font-weight: 500;
}

/* ---- Headline ---- */
.headline-section {
  margin-bottom: 2rem;
}

.headline {
  font-size: 2.8rem;
  font-weight: 800;
  background: linear-gradient(135deg, #3b82f6, #a855f7, #3b82f6);
  background-size: 200% 100%;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  animation: gradient-shift 4s ease infinite;
  line-height: 1.1;
  margin-bottom: 0.75rem;
}

.headline-sub {
  color: var(--text-secondary);
  font-size: 1.1rem;
  line-height: 1.5;
}

@keyframes gradient-shift {
  0% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
  100% { background-position: 0% 50%; }
}

/* ---- Form section ---- */
.form-section {
  margin-bottom: 3.5rem;
}

.auth-card {
  background: var(--bg-card);
  padding: 2.5rem;
  border-radius: var(--radius-xl, 1rem);
  box-shadow: var(--shadow-lg);
  border: 1px solid var(--border-color);
}

.form-group {
  margin-bottom: 1.5rem;
}

label {
  display: block;
  margin-bottom: 0.5rem;
  color: var(--text-primary);
  font-weight: 600;
  font-size: 0.95rem;
}

input {
  width: 100%;
  padding: 0.9rem 1rem;
  border: none;
  border-radius: var(--radius-md);
  background: var(--bg-input);
  color: var(--text-primary);
  font-size: 1rem;
  transition: box-shadow 0.2s;
}

input:focus {
  outline: none;
  box-shadow: 0 0 0 2px var(--border-input-focus);
}

input::placeholder {
  color: var(--text-muted);
}

.forgot-link {
  display: block;
  text-align: right;
  margin-top: 0.5rem;
  color: var(--text-muted);
  font-size: 0.85rem;
  text-decoration: none;
}

.forgot-link:hover {
  color: var(--color-primary);
}

.btn-primary {
  width: 100%;
  padding: 1rem;
  background: var(--gradient-primary);
  color: var(--text-on-primary);
  border: none;
  border-radius: var(--radius-md);
  font-size: 1.05rem;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.2s;
  margin-top: 0.5rem;
}

.btn-primary:hover:not(:disabled) {
  opacity: 0.9;
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

.reset-link {
  display: block;
  margin-top: 0.5rem;
  color: var(--color-primary);
  font-weight: bold;
  text-decoration: underline;
}

.auth-switch {
  text-align: center;
  margin-top: 1.5rem;
  color: var(--text-muted);
}

.auth-switch a {
  color: var(--color-primary);
  text-decoration: none;
  font-weight: 600;
}

.auth-switch a:hover {
  text-decoration: underline;
}

/* ---- Features section ---- */
.features-section {
  text-align: center;
}

.features-title {
  font-size: 1.8rem;
  font-weight: 800;
  color: var(--text-primary);
  margin-bottom: 2rem;
}

.features-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1.5rem;
}

.feature-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 2rem 1.5rem;
  text-align: center;
  box-shadow: var(--shadow-md);
}

.feature-icon {
  width: 56px;
  height: 56px;
  border-radius: var(--radius-full);
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 1rem;
}

.icon-blue {
  background: rgba(59, 130, 246, 0.12);
  color: #3b82f6;
}

.icon-purple {
  background: rgba(124, 58, 237, 0.12);
  color: #7c3aed;
}

.icon-green {
  background: rgba(22, 163, 74, 0.12);
  color: #16a34a;
}

.feature-card h3 {
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 0.5rem;
}

.feature-card p {
  color: var(--text-secondary);
  font-size: 0.9rem;
  line-height: 1.5;
}

/* ---- Responsive ---- */
@media (max-width: 640px) {
  .login-page {
    padding: 1rem 1rem 3rem;
  }

  .hero-grid {
    height: 466px;
    gap: 0.75rem;
    margin-bottom: 2rem;
  }

  .hero-col {
    gap: 0.75rem;
  }

  .stat-number {
    font-size: 1.8rem;
  }

  .headline {
    font-size: 2rem;
  }

  .headline-sub {
    font-size: 0.95rem;
  }

  .auth-card {
    padding: 1.5rem;
  }

  .features-grid {
    grid-template-columns: 1fr;
    gap: 1rem;
  }

  .features-title {
    font-size: 1.4rem;
  }
}
</style>
