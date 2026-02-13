<template>
  <div id="app">
    <nav v-if="authStore.isAuthenticated && !isLandingPage" class="navbar">
      <div class="nav-brand">
        <router-link :to="isAdmin ? '/hub' : '/challenges'">
          <svg v-if="!isAdmin" class="brand-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M6 9H4.5a2.5 2.5 0 0 1 0-5C7 4 7 7 7 7"/>
            <path d="M18 9h1.5a2.5 2.5 0 0 0 0-5C17 4 17 7 17 7"/>
            <path d="M4 22h16"/>
            <path d="M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 20 7 22"/>
            <path d="M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17 20 17 22"/>
            <path d="M18 2H6v7a6 6 0 0 0 12 0V2Z"/>
          </svg>
          {{ isAdmin ? '🏸 pushup.neymo.ai' : 'PushUp Pro' }}
        </router-link>
      </div>
      <div class="nav-links">
        <router-link v-if="isAdmin" to="/hub">Home</router-link>
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
          Logout
        </button>
      </div>
    </nav>
    <main :class="['main-content', { 'full-width': isLandingPage || isAuthPage }]">
      <router-view />
    </main>
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
  width: 28px;
  height: 28px;
  stroke: var(--color-primary);
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
    gap: 0.75rem;
  }

  .nav-links a {
    padding: 0.4rem 0.6rem;
  }

  .btn-logout {
    padding: 0.4rem 0.75rem;
  }

  .user-name {
    display: none;
  }

  .main-content {
    padding: 1rem;
  }
}
</style>
