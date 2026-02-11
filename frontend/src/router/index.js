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
    path: '/hub',
    name: 'FeatureHub',
    component: () => import('../views/FeatureHubView.vue'),
    meta: { requiresAuth: true }
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
    path: '/stream/:sessionId/tuning',
    name: 'StreamTuning',
    component: () => import('../views/TuningView.vue'),
    meta: { requiresAuth: true },
    props: route => ({ streamSessionId: parseInt(route.params.sessionId) })
  },
  {
    path: '/challenges',
    name: 'ChallengeSelector',
    component: () => import('../views/ChallengeSelectorView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/challenges/:type',
    name: 'ChallengeSession',
    component: () => import('../views/ChallengeSessionView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/challenges/results/:sessionId',
    name: 'ChallengeResults',
    component: () => import('../views/ChallengeResultsView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/workout',
    name: 'Workout',
    component: () => import('../views/WorkoutView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/admin',
    name: 'Admin',
    component: () => import('../views/AdminView.vue'),
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  {
    path: '/tuning',
    name: 'Tuning',
    component: () => import('../views/TuningView.vue'),
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
    // Redirect authenticated users from login/signup to hub
    next('/hub')
  } else if (to.meta.requiresAdmin && !authStore.user?.is_admin) {
    next('/hub')
  } else {
    next()
  }
})

export default router
