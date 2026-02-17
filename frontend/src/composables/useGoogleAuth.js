import { ref } from 'vue'

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID || ''

const scriptLoaded = ref(false)
let scriptPromise = null

function loadGsiScript() {
  if (scriptPromise) return scriptPromise
  if (window.google?.accounts) {
    scriptLoaded.value = true
    return Promise.resolve()
  }

  scriptPromise = new Promise((resolve, reject) => {
    const script = document.createElement('script')
    script.src = 'https://accounts.google.com/gsi/client'
    script.async = true
    script.defer = true
    script.onload = () => {
      scriptLoaded.value = true
      resolve()
    }
    script.onerror = () => reject(new Error('Failed to load Google Identity Services'))
    document.head.appendChild(script)
  })
  return scriptPromise
}

function waitForLayout() {
  return new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)))
}

export function useGoogleAuth() {
  const isAvailable = !!GOOGLE_CLIENT_ID

  async function renderButton(containerEl, callback) {
    if (!isAvailable || !containerEl) return

    await loadGsiScript()
    await waitForLayout()

    window.google.accounts.id.initialize({
      client_id: GOOGLE_CLIENT_ID,
      callback: (response) => callback(response.credential),
      ux_mode: 'popup',
    })

    // Google button max is 400px; measure actual container width
    const width = Math.max(200, Math.min(containerEl.clientWidth || 300, 400))

    // Clear any previous render
    containerEl.innerHTML = ''

    window.google.accounts.id.renderButton(containerEl, {
      type: 'standard',
      shape: 'rectangular',
      theme: 'outline',
      size: 'large',
      text: 'signin_with',
      width,
    })
  }

  return { isAvailable, renderButton }
}
