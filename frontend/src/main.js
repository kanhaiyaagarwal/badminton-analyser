import { createApp } from 'vue'
import { createPinia } from 'pinia'
import './assets/theme.css'
import App from './App.vue'
import router from './router'

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

app.use(createPinia())
app.use(router)

// Catch unhandled Vue errors and forward to Datadog RUM
app.config.errorHandler = (err, instance, info) => {
  console.error(err)
  if (window.DD_RUM) {
    window.DD_RUM.addError(err, { source: 'vue', info })
  }
}

app.mount('#app')
