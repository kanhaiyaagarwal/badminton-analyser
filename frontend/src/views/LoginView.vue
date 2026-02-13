<template>
  <div class="auth-container">
    <div class="auth-card">
      <h1>Login</h1>
      <p class="subtitle">Welcome back to Badminton Analyzer</p>

      <form @submit.prevent="handleLogin">
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
            placeholder="Your password"
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
          {{ loading ? 'Logging in...' : 'Login' }}
        </button>
      </form>

      <p class="auth-switch">
        Don't have an account?
        <router-link :to="{ path: '/signup', query: $route.query }">Sign up</router-link>
      </p>
    </div>
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
  margin-bottom: 1.5rem;
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

.forgot-link {
  display: block;
  text-align: right;
  margin-top: 0.5rem;
  color: #888;
  font-size: 0.85rem;
  text-decoration: none;
}

.forgot-link:hover {
  color: #4ecca3;
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

.reset-link {
  display: block;
  margin-top: 0.5rem;
  color: #4ecca3;
  font-weight: bold;
  text-decoration: underline;
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
</style>
