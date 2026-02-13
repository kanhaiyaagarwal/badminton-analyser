<template>
  <div id="app">
    <nav v-if="authStore.isAuthenticated && !isLandingPage" class="navbar">
      <div class="nav-brand">
        <router-link :to="isAdmin ? '/hub' : '/challenges'">
          {{ isAdmin ? '🏸 vision.neymo.ai' : 'Challenges' }}
        </router-link>
      </div>
      <div class="nav-links">
        <router-link v-if="isAdmin" to="/hub">Home</router-link>
        <router-link v-if="isAdmin" to="/admin" class="nav-admin">Admin</router-link>
        <span class="user-info">{{ authStore.user?.username }}</span>
        <button @click="logout" class="btn-logout">Logout</button>
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
  background-image: url('@/assets/images/pattern-bg.jpg');
  background-size: cover;
  background-position: center;
  background-attachment: fixed;
  position: relative;
}

#app::before {
  content: '';
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(10, 10, 26, 0.8);
  z-index: 0;
  pointer-events: none;
}

.navbar {
  background: rgba(22, 33, 62, 0.95);
  position: relative;
  z-index: 1;
  padding: 1rem 2rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.3);
}

.nav-brand a {
  color: #4ecca3;
  text-decoration: none;
  font-size: 1.5rem;
  font-weight: bold;
}

.nav-links {
  display: flex;
  align-items: center;
  gap: 1.5rem;
}

.nav-links a {
  color: #eee;
  text-decoration: none;
  padding: 0.5rem 1rem;
  border-radius: 4px;
  transition: background 0.2s;
}

.nav-links a:hover,
.nav-links a.router-link-active {
  background: rgba(78, 204, 163, 0.2);
  color: #4ecca3;
}

.nav-admin {
  color: #9b59b6 !important;
  border: 1px solid #9b59b6;
}

.nav-admin:hover,
.nav-admin.router-link-active {
  background: rgba(155, 89, 182, 0.2) !important;
  color: #9b59b6 !important;
}

.user-info {
  color: #888;
  padding: 0 1rem;
}

.btn-logout {
  background: transparent;
  border: 1px solid #e74c3c;
  color: #e74c3c;
  padding: 0.5rem 1rem;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-logout:hover {
  background: #e74c3c;
  color: white;
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

  .user-info {
    display: none;
  }

  .main-content {
    padding: 1rem;
  }
}
</style>
