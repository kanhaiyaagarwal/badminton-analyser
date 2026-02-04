import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const routes = [
  {
    path: '/',
    name: 'Landing',
    component: () => import('../views/LandingView.vue'),
    meta: { guest: true }
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/LoginView.vue'),
    meta: { guest: true }
  },
  {
    path: '/signup',
    name: 'Signup',
    component: () => import('../views/SignupView.vue'),
    meta: { guest: true }
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: () => import('../views/DashboardView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/upload',
    name: 'Upload',
    component: () => import('../views/UploadView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/court-setup/:jobId',
    name: 'CourtSetup',
    component: () => import('../views/CourtSetupView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/results/:jobId',
    name: 'Results',
    component: () => import('../views/ResultsView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/live',
    name: 'LiveStream',
    component: () => import('../views/LiveStreamView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/stream-results/:sessionId',
    name: 'StreamResults',
    component: () => import('../views/StreamResultsView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/admin',
    name: 'Admin',
    component: () => import('../views/AdminView.vue'),
    meta: { requiresAuth: true, requiresAdmin: true }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  const authStore = useAuthStore()

  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    next('/login')
  } else if (to.meta.guest && authStore.isAuthenticated && to.name !== 'Landing') {
    // Redirect authenticated users from login/signup to dashboard, but allow landing page
    next('/dashboard')
  } else if (to.meta.requiresAdmin && !authStore.user?.is_admin) {
    next('/dashboard')
  } else {
    next()
  }
})

export default router
