import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const routes = [
  {
    path: '/',
    redirect: '/login'
  },
  {
    path: '/landing-full',
    name: 'LandingFull',
    component: () => import('../views/LandingViewFull.vue'),
    meta: { requiresAuth: true, requiresAdmin: true }
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
    meta: { requiresAuth: true }
  },
  {
    path: '/profile',
    name: 'Profile',
    component: () => import('../views/ProfileView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: () => import('../views/DashboardView.vue'),
    meta: { requiresAuth: true, requiredFeature: 'badminton' }
  },
  {
    path: '/upload',
    name: 'Upload',
    component: () => import('../views/UploadView.vue'),
    meta: { requiresAuth: true, requiredFeature: 'badminton' }
  },
  {
    path: '/court-setup/:jobId',
    name: 'CourtSetup',
    component: () => import('../views/CourtSetupView.vue'),
    meta: { requiresAuth: true, requiredFeature: 'badminton' }
  },
  {
    path: '/results/:jobId',
    name: 'Results',
    component: () => import('../views/ResultsView.vue'),
    meta: { requiresAuth: true, requiredFeature: 'badminton' }
  },
  {
    path: '/live',
    name: 'LiveStream',
    component: () => import('../views/LiveStreamView.vue'),
    meta: { requiresAuth: true, requiredFeature: 'badminton' }
  },
  {
    path: '/stream-results/:sessionId',
    name: 'StreamResults',
    component: () => import('../views/StreamResultsView.vue'),
    meta: { requiresAuth: true, requiredFeature: 'badminton' }
  },
  {
    path: '/stream/:sessionId/tuning',
    name: 'StreamTuning',
    component: () => import('../views/TuningView.vue'),
    meta: { requiresAuth: true, requiredFeature: 'badminton' },
    props: route => ({ streamSessionId: parseInt(route.params.sessionId) })
  },
  {
    path: '/challenges',
    name: 'ChallengeSelector',
    component: () => import('../views/ChallengeSelectorView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/challenges/results/:sessionId',
    name: 'ChallengeResults',
    component: () => import('../views/ChallengeResultsView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/challenges/:type/session',
    name: 'ChallengeSession',
    component: () => import('../views/ChallengeSessionView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/challenges/:type',
    name: 'ChallengeHome',
    component: () => import('../views/ChallengeHomeView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/mimic',
    name: 'MimicBrowse',
    component: () => import('../views/MimicBrowseView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/mimic/session/:challengeId',
    name: 'MimicSession',
    component: () => import('../views/MimicSessionView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/mimic/results/:sessionId',
    name: 'MimicResults',
    component: () => import('../views/MimicResultsView.vue'),
    meta: { requiresAuth: true }
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

function getHomePath(authStore) {
  // If user has badminton access, show hub (multiple features)
  if (authStore.hasFeature('badminton')) return '/hub'
  // If user only has challenge features, go straight to challenges
  const challengeFeatures = ['pushup', 'squat', 'plank']
  if (challengeFeatures.some(f => authStore.hasFeature(f))) return '/challenges'
  // Fallback
  return '/hub'
}

router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore()
  const isAuth = authStore.isAuthenticated

  // Wait for user data to load on refresh before checking guards
  if (isAuth) {
    await authStore.initReady
  }

  const isAdmin = authStore.user?.is_admin
  const home = isAuth ? getHomePath(authStore) : '/hub'

  // 1. Auth required but not logged in
  if (to.meta.requiresAuth && !isAuth) {
    next({ path: '/login', query: { redirect: to.fullPath } })
    return
  }

  // 2. Guest-only pages — redirect if already authenticated
  if (to.meta.guest && isAuth) {
    next(home)
    return
  }

  // 3. Admin-only routes
  if (to.meta.requiresAdmin && !isAdmin) {
    next(home)
    return
  }

  // 4. Feature-gated routes
  if (to.meta.requiredFeature && !authStore.hasFeature(to.meta.requiredFeature)) {
    next(home)
    return
  }

  // 5. Hub page — skip if user only has challenges
  if (to.path === '/hub' && home !== '/hub') {
    next(home)
    return
  }

  next()
})

export default router
