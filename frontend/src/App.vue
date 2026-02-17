<template>
  <div id="app">
    <nav v-if="authStore.isAuthenticated && !isLandingPage" class="navbar">
      <div class="nav-brand">
        <router-link to="/hub">
          <img src="/pwa-192x192.png" alt="PushUp Pro" class="brand-icon" />
          PushUp Pro
        </router-link>
      </div>
      <div class="nav-links">
        <router-link to="/hub">Home</router-link>
        <router-link v-if="isAdmin" to="/admin" class="nav-admin">Admin</router-link>
        <div class="user-badge">
          <span class="user-avatar">{{ userInitial }}</span>
          <span class="user-name">{{ authStore.user?.username }}</span>
        </div>
        <button @click="logout" class="btn-logout">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18" stroke-linecap="round" stroke-linejoin="round">
            <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
            <polyline points="16 17 21 12 16 7"/>
            <line x1="21" y1="12" x2="9" y2="12"/>
          </svg>
          <span class="logout-text">Logout</span>
        </button>
      </div>
    </nav>
    <main :class="['main-content', { 'full-width': isLandingPage || isAuthPage }]">
      <router-view />
    </main>
    <footer v-if="!isLandingPage" class="app-footer">
      <a href="mailto:connect@neymo.ai">connect@neymo.ai</a>
    </footer>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useAuthStore } from './stores/auth'
import { useRouter, useRoute } from 'vue-router'

const authStore = useAuthStore()
const router = useRouter()
const route = useRoute()

const isAdmin = computed(() => authStore.user?.is_admin)
const isLandingPage = computed(() => route.name === 'Landing' || route.name === 'LandingFull')
const isAuthPage = computed(() => ['Login', 'Signup'].includes(route.name))
const userInitial = computed(() => (authStore.user?.username || authStore.user?.email || '?')[0].toUpperCase())

const logout = () => {
  authStore.logout()
  router.push('/')
}
</script>

<style>
#app {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--bg-page);
  position: relative;
}

.navbar {
  background: var(--bg-card);
  position: relative;
  z-index: 1;
  padding: 1rem 2rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  box-shadow: var(--shadow-sm);
  border-bottom: 1px solid var(--border-color);
}

.nav-brand a {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  background: var(--gradient-primary);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  text-decoration: none;
  font-size: 1.5rem;
  font-weight: 700;
}

.brand-icon {
  width: 32px;
  height: 32px;
  border-radius: 6px;
  flex-shrink: 0;
  -webkit-text-fill-color: initial;
}

.nav-links {
  display: flex;
  align-items: center;
  gap: 1.5rem;
}

.nav-links a {
  color: var(--text-secondary);
  text-decoration: none;
  padding: 0.5rem 1rem;
  border-radius: var(--radius-md);
  transition: background 0.2s, color 0.2s;
  font-weight: 500;
}

.nav-links a:hover,
.nav-links a.router-link-active {
  background: var(--color-primary-light);
  color: var(--color-primary);
}

.nav-admin {
  color: var(--color-secondary) !important;
  border: 1px solid var(--color-secondary);
}

.nav-admin:hover,
.nav-admin.router-link-active {
  background: var(--color-secondary-light) !important;
  color: var(--color-secondary) !important;
}

.user-badge {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.user-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: var(--gradient-primary);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 0.95rem;
}

.user-name {
  color: var(--text-primary);
  font-weight: 500;
  font-size: 0.95rem;
}

.btn-logout {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  background: transparent;
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
  padding: 0.5rem 1rem;
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all 0.2s;
  font-weight: 500;
  font-size: 0.95rem;
}

.btn-logout:hover {
  border-color: var(--text-muted);
  color: var(--text-primary);
}

.main-content {
  flex: 1;
  padding: 2rem;
  max-width: 1400px;
  margin: 0 auto;
  width: 100%;
  position: relative;
  z-index: 1;
}

.main-content.full-width {
  padding: 0;
  max-width: 100%;
}

@media (max-width: 640px) {
  .navbar {
    padding: 0.75rem 1rem;
  }

  .nav-brand a {
    font-size: 1.1rem;
  }

  .nav-links {
    gap: 0.5rem;
  }

  .nav-links a {
    padding: 0.35rem 0.5rem;
    font-size: 0.8rem;
  }

  .btn-logout {
    padding: 0.35rem 0.5rem;
    font-size: 0.8rem;
  }

  .btn-logout svg {
    width: 16px;
    height: 16px;
  }

  .logout-text {
    display: none;
  }

  .user-name {
    display: none;
  }

  .user-avatar {
    width: 30px;
    height: 30px;
    font-size: 0.8rem;
  }

  .main-content {
    padding: 1rem;
  }
}

.app-footer {
  text-align: center;
  padding: 1.5rem 1rem;
  color: var(--text-muted);
  font-size: 0.8rem;
}

.app-footer a {
  color: var(--text-muted);
  text-decoration: none;
  transition: color 0.2s;
}

.app-footer a:hover {
  color: var(--color-primary);
}
</style>
