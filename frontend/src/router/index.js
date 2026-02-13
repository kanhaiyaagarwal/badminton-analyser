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
    path: '/forgot-password',
    name: 'ForgotPassword',
    component: () => import('../views/ForgotPasswordView.vue'),
    meta: { guest: true }
  },
  {
    path: '/challenge',
    redirect: '/challenges',
    meta: { requiresAuth: true }
  },
  {
    path: '/hub',
    name: 'FeatureHub',
    component: () => import('../views/FeatureHubView.vue'),
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: () => import('../views/DashboardView.vue'),
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  {
    path: '/upload',
    name: 'Upload',
    component: () => import('../views/UploadView.vue'),
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  {
    path: '/court-setup/:jobId',
    name: 'CourtSetup',
    component: () => import('../views/CourtSetupView.vue'),
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  {
    path: '/results/:jobId',
    name: 'Results',
    component: () => import('../views/ResultsView.vue'),
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  {
    path: '/live',
    name: 'LiveStream',
    component: () => import('../views/LiveStreamView.vue'),
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  {
    path: '/stream-results/:sessionId',
    name: 'StreamResults',
    component: () => import('../views/StreamResultsView.vue'),
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  {
    path: '/stream/:sessionId/tuning',
    name: 'StreamTuning',
    component: () => import('../views/TuningView.vue'),
    meta: { requiresAuth: true, requiresAdmin: true },
    props: route => ({ streamSessionId: parseInt(route.params.sessionId) })
  },
  {
    path: '/challenges',
    name: 'ChallengeSelector',
    component: () => import('../views/ChallengeSelectorView.vue'),
    meta: { requiresAuth: true, challengeRoute: true }
  },
  {
    path: '/challenges/results/:sessionId',
    name: 'ChallengeResults',
    component: () => import('../views/ChallengeResultsView.vue'),
    meta: { requiresAuth: true, challengeRoute: true }
  },
  {
    path: '/challenges/:type/session',
    name: 'ChallengeSession',
    component: () => import('../views/ChallengeSessionView.vue'),
    meta: { requiresAuth: true, challengeRoute: true }
  },
  {
    path: '/challenges/:type',
    name: 'ChallengeHome',
    component: () => import('../views/ChallengeHomeView.vue'),
    meta: { requiresAuth: true, challengeRoute: true }
  },
  {
    path: '/workout',
    name: 'Workout',
    component: () => import('../views/WorkoutView.vue'),
    meta: { requiresAuth: true, requiresAdmin: true }
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
  const isAuth = authStore.isAuthenticated
  const isAdmin = authStore.user?.is_admin

  // 1. Auth required but not logged in → login with redirect
  if (to.meta.requiresAuth && !isAuth) {
    next({ path: '/login', query: { redirect: to.fullPath } })
    return
  }

  // 2. Guest-only pages (login/signup) — redirect if already authenticated
  if (to.meta.guest && isAuth && to.name !== 'Landing') {
    next(isAdmin ? '/hub' : '/challenges')
    return
  }

  // 3. Admin-only routes — redirect non-admin to challenges
  if (to.meta.requiresAdmin && !isAdmin) {
    next('/challenges')
    return
  }

  // 4. Non-admin authenticated users can only access challenge routes, guest routes, and Landing
  if (isAuth && !isAdmin && !to.meta.challengeRoute && !to.meta.guest && to.name !== 'Landing') {
    next('/challenges')
    return
  }

  next()
})

export default router
