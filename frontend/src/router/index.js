import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { appMode, isBadmintonMode } from '../composables/useAppMode'

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
  // Blog (public, fitness only)
  {
    path: '/blog',
    name: 'Blog',
    component: () => import('../views/BlogView.vue'),
    meta: { appMode: 'fitness' }
  },
  {
    path: '/blog/:slug',
    name: 'BlogPost',
    component: () => import('../views/BlogPostView.vue'),
    meta: { appMode: 'fitness' }
  },
  // Fitness routes
  {
    path: '/hub',
    name: 'Home',
    component: () => import('../views/workout/WorkoutHomeView.vue'),
    meta: { requiresAuth: true, requiredFeature: 'workout', appMode: 'fitness' }
  },
  {
    path: '/explore',
    name: 'Explore',
    component: () => import('../views/FeatureHubView.vue'),
    meta: { requiresAuth: true, appMode: 'fitness' }
  },
  {
    path: '/features',
    name: 'FeatureCatalog',
    component: () => import('../views/FeatureRequestView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/profile',
    name: 'Profile',
    component: () => import('../views/ProfileView.vue'),
    meta: { requiresAuth: true }
  },
  // Badminton routes
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: () => import('../views/DashboardView.vue'),
    meta: { requiresAuth: true, requiredFeature: 'badminton', appMode: 'badminton' }
  },
  {
    path: '/upload',
    name: 'Upload',
    component: () => import('../views/UploadView.vue'),
    meta: { requiresAuth: true, requiredFeature: 'badminton', appMode: 'badminton' }
  },
  {
    path: '/court-setup/:jobId',
    name: 'CourtSetup',
    component: () => import('../views/CourtSetupView.vue'),
    meta: { requiresAuth: true, requiredFeature: 'badminton', appMode: 'badminton' }
  },
  {
    path: '/results/:jobId',
    name: 'Results',
    component: () => import('../views/ResultsView.vue'),
    meta: { requiresAuth: true, requiredFeature: 'badminton', appMode: 'badminton' }
  },
  {
    path: '/live',
    name: 'LiveStream',
    component: () => import('../views/LiveStreamView.vue'),
    meta: { requiresAuth: true, requiredFeature: 'badminton', appMode: 'badminton' }
  },
  {
    path: '/stream-results/:sessionId',
    name: 'StreamResults',
    component: () => import('../views/StreamResultsView.vue'),
    meta: { requiresAuth: true, requiredFeature: 'badminton', appMode: 'badminton' }
  },
  {
    path: '/stream/:sessionId/tuning',
    name: 'StreamTuning',
    component: () => import('../views/TuningView.vue'),
    meta: { requiresAuth: true, requiredFeature: 'tuning' },
    props: route => ({ streamSessionId: parseInt(route.params.sessionId) })
  },
  // Fitness: Challenges
  {
    path: '/challenges',
    name: 'ChallengeSelector',
    component: () => import('../views/ChallengeSelectorView.vue'),
    meta: { requiresAuth: true, appMode: 'fitness' }
  },
  {
    path: '/challenges/results/:sessionId',
    name: 'ChallengeResults',
    component: () => import('../views/ChallengeResultsView.vue'),
    meta: { requiresAuth: true, appMode: 'fitness' }
  },
  {
    path: '/challenges/:type/session',
    name: 'ChallengeSession',
    component: () => import('../views/ChallengeSessionView.vue'),
    meta: { requiresAuth: true, appMode: 'fitness' }
  },
  {
    path: '/challenges/:type',
    name: 'ChallengeHome',
    component: () => import('../views/ChallengeHomeView.vue'),
    meta: { requiresAuth: true, appMode: 'fitness' }
  },
  // Fitness: Mimic
  {
    path: '/mimic',
    name: 'MimicBrowse',
    component: () => import('../views/MimicBrowseView.vue'),
    meta: { requiresAuth: true, requiredFeature: 'mimic', appMode: 'fitness' }
  },
  {
    path: '/mimic/session/:challengeId',
    name: 'MimicSession',
    component: () => import('../views/MimicSessionView.vue'),
    meta: { requiresAuth: true, requiredFeature: 'mimic', appMode: 'fitness' }
  },
  {
    path: '/mimic/results/:sessionId',
    name: 'MimicResults',
    component: () => import('../views/MimicResultsView.vue'),
    meta: { requiresAuth: true, requiredFeature: 'mimic', appMode: 'fitness' }
  },
  // Fitness: Workout
  {
    path: '/workout',
    name: 'WorkoutPlan',
    component: () => import('../views/workout/WorkoutPlanView.vue'),
    meta: { requiresAuth: true, requiredFeature: 'workout', appMode: 'fitness' }
  },
  {
    path: '/workout/onboarding',
    name: 'WorkoutOnboarding',
    component: () => import('../views/workout/ConversationalOnboardingView.vue'),
    meta: { requiresAuth: true, requiredFeature: 'workout', appMode: 'fitness' }
  },
  {
    path: '/workout/onboarding/classic',
    name: 'WorkoutOnboardingClassic',
    component: () => import('../views/workout/WorkoutOnboardingView.vue'),
    meta: { requiresAuth: true, requiredFeature: 'workout', appMode: 'fitness' }
  },
  {
    path: '/workout/equipment',
    name: 'WorkoutEquipment',
    component: () => import('../views/workout/EquipmentView.vue'),
    meta: { requiresAuth: true, requiredFeature: 'workout', appMode: 'fitness' }
  },
  {
    path: '/workout/exercises',
    name: 'ExerciseLibrary',
    component: () => import('../views/workout/ExerciseLibraryView.vue'),
    meta: { requiresAuth: true, requiredFeature: 'workout', appMode: 'fitness' }
  },
  {
    path: '/workout/exercises/:slug',
    name: 'ExerciseDetail',
    component: () => import('../views/workout/ExerciseDetailView.vue'),
    meta: { requiresAuth: true, requiredFeature: 'workout', appMode: 'fitness' }
  },
  {
    path: '/workout/quick-start',
    name: 'QuickStart',
    component: () => import('../views/workout/QuickStartView.vue'),
    meta: { requiresAuth: true, requiredFeature: 'workout', appMode: 'fitness' }
  },
  {
    path: '/workout/session/:sessionId?',
    name: 'WorkoutSession',
    component: () => import('../views/workout/WorkoutSessionView.vue'),
    meta: { requiresAuth: true, requiredFeature: 'workout', appMode: 'fitness' }
  },
  {
    path: '/workout/results/:sessionId',
    name: 'WorkoutResults',
    component: () => import('../views/workout/WorkoutResultsView.vue'),
    meta: { requiresAuth: true, requiredFeature: 'workout', appMode: 'fitness' }
  },
  // Shared: Admin & Tuning
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
    meta: { requiresAuth: true, requiredFeature: 'tuning' }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

function getHomePath(authStore) {
  if (isBadmintonMode) {
    return '/dashboard'
  }
  // Fitness mode — land on home
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
  const home = isAuth ? getHomePath(authStore) : (isBadmintonMode ? '/dashboard' : '/hub')

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

  // 4. App mode guard — prevent cross-mode navigation
  if (to.meta.appMode && to.meta.appMode !== appMode) {
    next(home)
    return
  }

  // 5. Feature-gated routes (skip if requiredFeature matches current appMode — domain is the gate)
  if (to.meta.requiredFeature && to.meta.requiredFeature !== appMode && !authStore.hasFeature(to.meta.requiredFeature)) {
    next(home)
    return
  }

  // 6. Hub page requires workout feature (fitness mode)
  if (to.path === '/hub' && !isBadmintonMode && !authStore.hasFeature('workout')) {
    next(home)
    return
  }

  next()
})

export default router
