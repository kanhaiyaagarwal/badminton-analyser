import { computed } from 'vue'

const BADDY_HOSTS = ['baddy.neymo.ai', 'baddy.localhost']

function detectBadmintonMode() {
  if (BADDY_HOSTS.includes(window.location.hostname)) return true
  const params = new URLSearchParams(window.location.search)
  const modeParam = params.get('mode')
  if (modeParam === 'badminton') {
    sessionStorage.setItem('appMode', 'badminton')
    return true
  }
  if (modeParam === 'fitness') {
    sessionStorage.removeItem('appMode')
    return false
  }
  return sessionStorage.getItem('appMode') === 'badminton'
}

const _isBadminton = detectBadmintonMode()

export function useAppMode() {
  const isBadminton = computed(() => _isBadminton)
  const isFitness = computed(() => !_isBadminton)
  const mode = computed(() => _isBadminton ? 'badminton' : 'fitness')
  const appName = computed(() => _isBadminton ? 'Baddy' : 'PushUp Pro')
  return { mode, isBadminton, isFitness, appName }
}

// Non-reactive exports for use in router guards (outside component context)
export const appMode = _isBadminton ? 'badminton' : 'fitness'
export const isBadmintonMode = _isBadminton
