import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { createHead } from '@unhead/vue/client'
import { MotionPlugin } from '@vueuse/motion'
import './assets/tailwind.css'
import './assets/theme.css'
import App from './App.vue'
import router from './router'
import { useHead } from '@unhead/vue'
import { isBadmintonMode } from './composables/useAppMode'

document.title = isBadmintonMode ? 'Baddy' : 'PushUp Pro'

// Set default OG/meta tags based on app mode — overrides static index.html values.
// This runs before any page-specific useHead() calls; page-level tags take precedence.
const defaultMeta = isBadmintonMode
  ? {
      title: 'Baddy — AI Badminton Analytics',
      url: 'https://baddy.neymo.ai',
      description: 'Upload match footage and get shuttle trajectory tracking, shot classification, player heatmaps, and rally breakdowns powered by AI.',
      image: 'https://baddy.neymo.ai/og-baddy.png',
      siteName: 'Baddy',
    }
  : {
      title: 'PushUp Pro — AI Fitness Coach',
      url: 'https://pushup.neymo.ai',
      description: 'AI-powered fitness coaching with real-time camera form tracking. Pushups, squats, planks — tracked live from your phone.',
      image: 'https://pushup.neymo.ai/og-pushup-v2.png',
      siteName: 'PushUp Pro',
    }

// Inject as low-priority defaults (page-specific useHead calls override these)
useHead({
  title: defaultMeta.title,
  meta: [
    { name: 'description', content: defaultMeta.description },
    { property: 'og:url', content: defaultMeta.url },
    { property: 'og:title', content: defaultMeta.title },
    { property: 'og:description', content: defaultMeta.description },
    { property: 'og:image', content: defaultMeta.image },
    { property: 'og:site_name', content: defaultMeta.siteName },
    { name: 'twitter:title', content: defaultMeta.title },
    { name: 'twitter:description', content: defaultMeta.description },
    { name: 'twitter:image', content: defaultMeta.image },
  ],
})

// Initialize Datadog RUM (CDN script loaded in index.html)
if (window.DD_RUM && import.meta.env.VITE_DD_RUM_CLIENT_TOKEN) {
  window.DD_RUM.init({
    clientToken: import.meta.env.VITE_DD_RUM_CLIENT_TOKEN,
    applicationId: import.meta.env.VITE_DD_RUM_APPLICATION_ID,
    site: 'us5.datadoghq.com',
    service: 'badminton-analyzer-frontend',
    env: 'prod',
    sessionSampleRate: 100,
    sessionReplaySampleRate: 0,
    trackUserInteractions: true,
    trackResources: true,
    trackLongTasks: true,
    defaultPrivacyLevel: 'mask-user-input',
  })
}

const app = createApp(App)
const head = createHead()

app.use(createPinia())
app.use(head)
app.use(router)
app.use(MotionPlugin)

// Catch unhandled Vue errors and forward to Datadog RUM
app.config.errorHandler = (err, instance, info) => {
  console.error(err)
  if (window.DD_RUM) {
    window.DD_RUM.addError(err, { source: 'vue', info })
  }
}

app.mount('#app')
