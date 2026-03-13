<template>
  <!-- Mobile-app shell: constrained width, centered, card-like on desktop -->
  <div class="app-shell" :class="{ 'shell-wide': isAdminPage }">
    <div class="app-frame" :class="{ 'frame-wide': isAdminPage }">

      <!-- Top Header (authenticated, non-landing/auth pages) -->
      <header v-if="authStore.isAuthenticated && !isLandingPage && !isAuthPage && !isFullscreenPage" class="app-header">
        <router-link to="/hub" class="header-brand">
          <img src="/mascot/otter-mascot.png" alt="PushUp Pro" class="header-logo" />
          <span class="header-name">PushUp Pro</span>
        </router-link>
        <div class="header-actions">
          <router-link v-if="isAdmin" to="/admin" class="admin-badge">Admin</router-link>
        </div>
      </header>

      <!-- Main Content -->
      <main class="app-main" :class="{ 'has-nav': authStore.isAuthenticated && !isLandingPage && !isAuthPage && !isAdminPage && !isFullscreenPage }">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </main>

      <!-- Bottom Navigation (authenticated, non-landing/auth/admin pages) -->
      <nav v-if="authStore.isAuthenticated && !isLandingPage && !isAuthPage && !isAdminPage && !isFullscreenPage" class="bottom-nav">
        <BottomNavItem to="/hub" label="Home" exact>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
            <polyline points="9 22 9 12 15 12 15 22"/>
          </svg>
        </BottomNavItem>
        <BottomNavItem to="/workout" label="Workout">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M6.5 6.5a3.5 3.5 0 1 0 0 7"/>
            <path d="M17.5 6.5a3.5 3.5 0 1 1 0 7"/>
            <path d="M6.5 10h11"/>
            <path d="M4 10H2"/>
            <path d="M22 10h-2"/>
          </svg>
        </BottomNavItem>
        <BottomNavItem to="/features" label="Explore">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="10"/>
            <polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76"/>
          </svg>
        </BottomNavItem>
        <BottomNavItem to="/profile" label="Profile">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
            <circle cx="12" cy="7" r="4"/>
          </svg>
        </BottomNavItem>
      </nav>

      <!-- Footer (landing/auth pages only) -->
      <footer v-if="isLandingPage || isAuthPage" class="app-footer">
        <a href="mailto:connect@neymo.ai">connect@neymo.ai</a>
      </footer>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useAuthStore } from './stores/auth'
import { useRoute } from 'vue-router'
import BottomNavItem from './components/BottomNavItem.vue'

const authStore = useAuthStore()
const route = useRoute()

const isAdmin = computed(() => authStore.user?.is_admin)
const isLandingPage = computed(() => route.name === 'Landing' || route.name === 'LandingFull')
const isAuthPage = computed(() => ['Login', 'Signup', 'ForgotPassword'].includes(route.name))
const isAdminPage = computed(() => ['Admin', 'Tuning', 'StreamTuning'].includes(route.name))
const isFullscreenPage = computed(() => ['ChallengeSession', 'WorkoutSession'].includes(route.name))

</script>

<style>
/* ---- Mobile-app shell ---- */
.app-shell {
  min-height: 100vh;
  min-height: 100dvh;
  background: var(--bg-page);
  display: flex;
  justify-content: center;
}

/* Phone-width frame: full on mobile, constrained + elevated on desktop */
.app-frame {
  width: 100%;
  max-width: 430px;
  min-height: 100vh;
  min-height: 100dvh;
  display: flex;
  flex-direction: column;
  background: var(--bg-page);
  position: relative;
}

@media (min-width: 480px) {
  .app-shell {
    background: #E8E4DC;
    padding: 1rem 0;
    align-items: flex-start;
  }
  .app-frame {
    min-height: calc(100vh - 2rem);
    min-height: calc(100dvh - 2rem);
    border-radius: 1.5rem;
    box-shadow: 0 8px 40px rgba(45, 42, 38, 0.12), 0 0 0 1px rgba(45, 42, 38, 0.06);
    overflow: hidden;
  }
}

/* ---- Wide mode (admin pages) ---- */
.shell-wide {
  background: var(--bg-page) !important;
  padding: 0 !important;
}

.frame-wide {
  max-width: 100% !important;
  border-radius: 0 !important;
  box-shadow: none !important;
  overflow: visible !important;
}

/* ---- Top header ---- */
.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 1.25rem;
  background: rgba(253, 252, 249, 0.92);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--border-color);
  position: sticky;
  top: 0;
  z-index: 30;
}

.header-brand {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  text-decoration: none;
}

.header-logo {
  width: 28px;
  height: 28px;
  border-radius: 7px;
}

.header-name {
  font-size: 1rem;
  font-weight: 700;
  color: var(--color-primary);
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.admin-badge {
  font-size: 0.7rem;
  font-weight: 600;
  padding: 0.2rem 0.6rem;
  border-radius: 9999px;
  background: var(--color-secondary-light);
  color: var(--color-secondary);
  text-decoration: none;
}


/* ---- Main content ---- */
.app-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  position: relative;
}

.app-main.has-nav {
  padding-bottom: 4.5rem; /* space for bottom nav */
}

/* ---- Bottom navigation ---- */
.bottom-nav {
  position: fixed;
  bottom: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 100%;
  max-width: 430px;
  display: flex;
  align-items: center;
  justify-content: space-around;
  padding: 0.5rem 0.5rem;
  padding-bottom: calc(0.5rem + env(safe-area-inset-bottom, 0px));
  background: rgba(253, 252, 249, 0.92);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-top: 1px solid var(--border-color);
  z-index: 40;
}

@media (min-width: 480px) {
  .bottom-nav {
    border-radius: 0 0 1.5rem 1.5rem;
  }
}

/* ---- Footer ---- */
.app-footer {
  text-align: center;
  padding: 1.25rem 1rem;
  font-size: 0.75rem;
  color: var(--text-muted);
}

.app-footer a {
  color: var(--text-muted);
  text-decoration: none;
  transition: color 0.2s;
}

.app-footer a:hover {
  color: var(--color-primary);
}

/* ---- Page transitions ---- */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.fade-enter-from {
  opacity: 0;
  transform: translateY(4px);
}

.fade-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
</style>
