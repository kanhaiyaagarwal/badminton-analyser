<template>
  <div class="challenge-results">
    <div class="results-header">
      <router-link :to="backLink" class="back-link">&larr; Back to Challenge</router-link>
      <h1>Challenge Complete</h1>
    </div>

    <div v-if="result" class="results-card" ref="shareCard">
      <div class="card-brand">PushUp Pro</div>

      <div class="result-type">{{ typeLabel }}</div>
      <div class="result-user">by {{ displayName }}</div>

      <div class="score-display">
        <span class="score-value">{{ result.score }}</span>
        <span class="score-unit">{{ scoreUnit }}</span>
      </div>

      <!-- Daily Rank Badge -->
      <div v-if="result.daily_rank === 1" class="rank-badge leader-badge">
        Today's Leader
      </div>
      <div v-else-if="result.daily_rank > 1" class="rank-badge rank-text">
        {{ ordinal(result.daily_rank) }} today
      </div>

      <div class="stats-grid">
        <div class="stat">
          <span class="stat-value">{{ formatDuration(result.duration_seconds) }}</span>
          <span class="stat-label">Duration</span>
        </div>
        <div class="stat" v-if="result.personal_best !== null && result.personal_best !== undefined">
          <span class="stat-value" :class="{ 'new-pb': isNewPB }">{{ result.personal_best }} {{ scoreUnit }}</span>
          <span class="stat-label">{{ isNewPB ? 'New PR!' : 'Personal Record' }}</span>
        </div>
      </div>

      <!-- Form Summary -->
      <div v-if="result.form_summary" class="form-summary">
        <div class="form-summary-header">
          <span class="form-summary-title">Form Quality</span>
          <div class="form-score-badge" :class="formScoreClass">
            {{ result.form_summary.form_score }}
          </div>
        </div>

        <!-- Pushup details -->
        <div v-if="result.challenge_type === 'pushup'" class="form-details">
          <div v-if="result.form_summary.total_attempts > 0" class="form-attempts">
            <div class="form-detail-line">
              {{ result.form_summary.total_attempts }} total attempt{{ result.form_summary.total_attempts !== 1 ? 's' : '' }}
            </div>
            <div class="form-detail-sub highlight">{{ result.form_summary.good_reps }} good rep{{ result.form_summary.good_reps !== 1 ? 's' : '' }}</div>
            <div v-if="result.form_summary.half_pushups > 0" class="form-detail-sub bad">{{ result.form_summary.half_pushups }} half pushup{{ result.form_summary.half_pushups !== 1 ? 's' : '' }}</div>
          </div>
          <div v-else class="form-detail-line muted">No reps completed</div>
        </div>

        <!-- Plank details -->
        <div v-if="result.challenge_type === 'plank'" class="form-details">
          <div class="form-detail-line">
            Good form {{ result.form_summary.good_form_pct }}% of session
          </div>
          <div v-if="result.form_summary.form_break_count > 0" class="form-detail-line muted">
            {{ result.form_summary.form_break_count }} form break{{ result.form_summary.form_break_count !== 1 ? 's' : '' }}
          </div>
          <div v-if="result.form_summary.sag_frames > 0 || result.form_summary.pike_frames > 0" class="form-issues">
            <span v-if="result.form_summary.sag_frames > 0" class="form-issue">hips sagging</span>
            <span v-if="result.form_summary.sag_frames > 0 && result.form_summary.pike_frames > 0" class="form-issue-sep">&middot;</span>
            <span v-if="result.form_summary.pike_frames > 0" class="form-issue">hips too high</span>
          </div>
        </div>
      </div>

      <!-- QR Code -->
      <div class="card-footer">
        <span class="card-cta">Think you can beat me?</span>
        <div v-if="qrDataUrl" class="qr-section">
          <img :src="qrDataUrl" alt="QR code" class="qr-code" />
          <span class="qr-label">Scan to join</span>
        </div>
      </div>

      <div class="verified-badge">Posture & form verified by neymo.ai</div>
    </div>
    <!-- end results-card -->

    <div v-if="result">
      <div class="actions">
        <button @click="retry" class="retry-btn">Try Again</button>
        <button @click="shareResult" class="share-btn" :disabled="sharing">
          <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z"/>
          </svg>
          {{ sharing ? 'Sharing...' : 'Share' }}
        </button>
        <button v-if="showInstall" @click="installApp" class="install-btn">
          <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/>
          </svg>
          Install App
        </button>
      </div>

      <!-- iOS install nudge -->
      <div v-if="isIOS && !isStandalone" class="ios-install-nudge" @click="dismissNudge" v-show="!nudgeDismissed">
        <span class="nudge-icon">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M4 12v8a2 2 0 002 2h12a2 2 0 002-2v-8"/><polyline points="16 6 12 2 8 6"/><line x1="12" y1="2" x2="12" y2="15"/>
          </svg>
        </span>
        <span class="nudge-text">
          Tap <strong>Share</strong> <span class="ios-share-icon">&#xFEFF;&#x2B06;&#xFE0E;</span> then <strong>"Add to Home Screen"</strong> to install the app
        </span>
      </div>

      <!-- Recording Download -->
      <div v-if="hasRecording" class="recording-download">
        <p class="recording-desc">Your annotated session recording is ready.</p>
        <button @click="downloadRecording" class="download-btn" :disabled="downloading">
          <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/>
          </svg>
          {{ downloading ? 'Downloading...' : 'Download Recording' }}
        </button>
      </div>
    </div>

    <div v-else class="loading">
      <p>Loading results...</p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { toPng } from 'html-to-image'
import QRCode from 'qrcode'
import api from '../api/client'
import { useAuthStore } from '../stores/auth'

const INVITE_URL = 'https://pushup.neymo.ai/signup?invite=PUSHUP'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const sessionId = computed(() => route.params.sessionId)
const result = ref(null)
const hasRecording = ref(false)
const downloading = ref(false)
const sharing = ref(false)
const shareCard = ref(null)
const qrDataUrl = ref(null)
const isAdminView = ref(false)  // true when admin is viewing another user's session

// iOS detection
const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1)
const isStandalone = window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone === true
const nudgeDismissed = ref(false)

function dismissNudge() {
  nudgeDismissed.value = true
}

// PWA install prompt
const deferredPrompt = ref(null)
const showInstall = ref(false)

window.addEventListener('beforeinstallprompt', (e) => {
  e.preventDefault()
  deferredPrompt.value = e
  showInstall.value = true
})

async function installApp() {
  if (!deferredPrompt.value) return
  deferredPrompt.value.prompt()
  const { outcome } = await deferredPrompt.value.userChoice
  if (outcome === 'accepted') {
    showInstall.value = false
  }
  deferredPrompt.value = null
}

const TYPE_LABELS = {
  plank: 'Plank Hold',
  squat: 'Max Squats',
  pushup: 'Max Pushups',
}

const backLink = computed(() => result.value?.challenge_type ? `/challenges/${result.value.challenge_type}` : '/challenges')
const typeLabel = computed(() => TYPE_LABELS[result.value?.challenge_type] || 'Challenge')
const scoreUnit = computed(() => result.value?.challenge_type === 'plank' ? 's' : 'reps')
const isNewPB = computed(() => result.value && result.value.score === result.value.personal_best)
const displayName = computed(() => authStore.user?.username || 'You')
const formScoreClass = computed(() => {
  const score = result.value?.form_summary?.form_score ?? 0
  if (score >= 80) return 'score-green'
  if (score >= 50) return 'score-yellow'
  return 'score-red'
})

function ordinal(n) {
  const s = ['th', 'st', 'nd', 'rd']
  const v = n % 100
  return n + (s[(v - 20) % 10] || s[v] || s[0])
}

function formatDuration(seconds) {
  if (!seconds) return '0:00'
  const m = Math.floor(seconds / 60)
  const s = Math.round(seconds % 60)
  return `${m}:${String(s).padStart(2, '0')}`
}

function retry() {
  if (result.value?.challenge_type) {
    router.push(`/challenges/${result.value.challenge_type}`)
  } else {
    router.push('/challenges')
  }
}

async function downloadRecording() {
  downloading.value = true
  try {
    const endpoint = isAdminView.value
      ? `/api/v1/challenges/admin/sessions/${sessionId.value}/recording`
      : `/api/v1/challenges/sessions/${sessionId.value}/recording`
    const response = await api.get(endpoint, { responseType: 'blob' })
    const blob = new Blob([response.data], { type: 'video/mp4' })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `challenge_recording_${sessionId.value}.mp4`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
  } catch (err) {
    console.error('Failed to download recording:', err)
  } finally {
    downloading.value = false
  }
}

async function shareResult() {
  if (!shareCard.value) return
  sharing.value = true
  try {
    const dataUrl = await toPng(shareCard.value, { pixelRatio: 2 })
    const res = await fetch(dataUrl)
    const blob = await res.blob()
    const file = new File([blob], 'achievement.png', { type: 'image/png' })

    const scoreText = result.value.challenge_type === 'plank'
      ? `a ${result.value.score}s plank hold`
      : `${result.value.score} ${result.value.challenge_type}s`
    const shareText = `I just did ${scoreText}! Join the challenge and beat me: ${INVITE_URL}`

    if (navigator.canShare?.({ files: [file] })) {
      await navigator.share({
        files: [file],
        title: 'My Challenge Result',
        text: shareText,
      })
    } else {
      // Fallback: download the PNG
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = 'achievement.png'
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(url)
    }
  } catch (err) {
    if (err.name !== 'AbortError') {
      console.error('Failed to share:', err)
    }
  } finally {
    sharing.value = false
  }
}

onMounted(async () => {
  // Generate QR code
  try {
    qrDataUrl.value = await QRCode.toDataURL(INVITE_URL, { width: 80, margin: 1 })
  } catch (err) {
    console.error('Failed to generate QR code:', err)
  }

  // Try loading from sessionStorage (set by ChallengeSessionView after live session)
  const stored = sessionStorage.getItem(`challenge_result_${sessionId.value}`)
  if (stored) {
    const data = JSON.parse(stored)
    result.value = data
    hasRecording.value = !!data.has_recording
    sessionStorage.removeItem(`challenge_result_${sessionId.value}`)
    return
  }

  // Fallback: fetch from API (for history navigation)
  try {
    const response = await api.get('/api/v1/challenges/sessions')
    const session = response.data.find(s => s.id === Number(sessionId.value))
    if (session) {
      result.value = session
      hasRecording.value = !!session.has_recording
      return
    }
  } catch (err) {
    console.error('Failed to load session results:', err)
  }

  // Admin fallback: if user doesn't own the session, try admin endpoint
  if (authStore.user?.is_admin) {
    try {
      const response = await api.get(`/api/v1/challenges/admin/sessions/${sessionId.value}/detail`)
      result.value = response.data
      hasRecording.value = !!response.data.has_recording
      isAdminView.value = true
    } catch (err) {
      console.error('Failed to load session via admin:', err)
    }
  }
})
</script>

<style scoped>
.challenge-results {
  max-width: 600px;
  margin: 0 auto;
  padding: 1rem;
}

.results-header {
  margin-bottom: 2rem;
}

.back-link {
  color: var(--text-muted);
  text-decoration: none;
  font-size: 0.9rem;
}
.back-link:hover { color: var(--color-primary); }

.results-header h1 {
  color: var(--text-primary);
  margin-top: 0.5rem;
}

.results-card {
  background: linear-gradient(145deg, #1a1033 0%, #2d1b69 40%, #4c1d95 100%);
  border: none;
  border-radius: 1.25rem;
  padding: 2rem 2rem 1.5rem;
  text-align: center;
  position: relative;
  overflow: hidden;
}

/* Subtle decorative glow */
.results-card::before {
  content: '';
  position: absolute;
  top: -40%;
  right: -20%;
  width: 60%;
  height: 80%;
  background: radial-gradient(circle, rgba(139, 92, 246, 0.3) 0%, transparent 70%);
  pointer-events: none;
}

.card-brand {
  font-size: 0.75rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.15em;
  color: rgba(255, 255, 255, 0.4);
  margin-bottom: 1.25rem;
}

.result-type {
  color: rgba(255, 255, 255, 0.7);
  font-size: 0.9rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  margin-bottom: 0.2rem;
}

.result-user {
  color: rgba(255, 255, 255, 0.4);
  font-size: 0.8rem;
  font-weight: 500;
  margin-bottom: 0.75rem;
}

.score-display {
  margin-bottom: 1rem;
}

.score-value {
  font-size: 5rem;
  font-weight: 800;
  color: #ffffff;
  line-height: 1;
  text-shadow: 0 0 40px rgba(139, 92, 246, 0.5);
}

.score-unit {
  font-size: 1.3rem;
  color: rgba(255, 255, 255, 0.5);
  margin-left: 0.4rem;
  font-weight: 500;
}

/* Daily Rank Badges */
.rank-badge {
  display: inline-block;
  padding: 0.35rem 1.25rem;
  border-radius: 999px;
  font-weight: 700;
  font-size: 0.8rem;
  margin-bottom: 1.25rem;
  letter-spacing: 0.02em;
}

.leader-badge {
  background: linear-gradient(135deg, #f59e0b, #f97316);
  color: #1a1a1a;
  box-shadow: 0 2px 12px rgba(245, 158, 11, 0.4);
}

.rank-text {
  background: rgba(255, 255, 255, 0.1);
  color: rgba(255, 255, 255, 0.6);
  font-weight: 600;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.stats-grid {
  display: flex;
  justify-content: center;
  gap: 3rem;
  margin-bottom: 1.5rem;
  padding-top: 1.25rem;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}

.stat {
  text-align: center;
}

.stat-value {
  display: block;
  color: #ffffff;
  font-size: 1.3rem;
  font-weight: 700;
}

.stat-value.new-pb {
  color: #fbbf24;
}

.stat-label {
  display: block;
  color: rgba(255, 255, 255, 0.45);
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-top: 0.25rem;
}

/* Verified badge */
.verified-badge {
  font-size: 0.7rem;
  color: rgba(255, 255, 255, 0.4);
  font-weight: 500;
  letter-spacing: 0.02em;
  margin-top: 1rem;
}

/* Footer with CTA + QR */
.card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 1.25rem;
  padding-top: 1rem;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}

.card-cta {
  font-size: 0.8rem;
  color: rgba(255, 255, 255, 0.5);
  font-weight: 500;
  font-style: italic;
}

.qr-section {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.qr-code {
  width: 64px;
  height: 64px;
  border-radius: 6px;
  padding: 4px;
  background: #ffffff;
}

.qr-label {
  font-size: 0.55rem;
  color: rgba(255, 255, 255, 0.35);
  margin-top: 3px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.recording-download {
  margin: 1.5rem 0;
  padding: 1.5rem;
  background: var(--bg-input);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  text-align: center;
}

.recording-desc {
  color: var(--text-muted);
  margin-bottom: 1rem;
}

.download-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  background: var(--gradient-primary);
  color: var(--text-on-primary);
  padding: 0.75rem 1.5rem;
  border-radius: var(--radius-md);
  font-weight: 600;
  border: none;
  cursor: pointer;
  font-size: 1rem;
  transition: background 0.2s;
}
.download-btn:hover:not(:disabled) { opacity: 0.9; }
.download-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.download-btn .btn-icon {
  width: 18px;
  height: 18px;
}

.actions {
  display: flex;
  gap: 1rem;
  justify-content: center;
  margin-top: 1rem;
}

.retry-btn {
  background: var(--gradient-primary);
  color: var(--text-on-primary);
  border: none;
  padding: 0.75rem 2rem;
  border-radius: var(--radius-md);
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.2s;
}
.retry-btn:hover { opacity: 0.9; }

.share-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  background: transparent;
  border: 1px solid var(--border-color);
  color: var(--color-primary);
  padding: 0.75rem 1.5rem;
  border-radius: var(--radius-md);
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}
.share-btn:hover:not(:disabled) { background: var(--color-primary-light); }
.share-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.share-btn .btn-icon {
  width: 18px;
  height: 18px;
}

.install-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  background: linear-gradient(135deg, #1a6b8a, #2dd4bf);
  color: #fff;
  border: none;
  padding: 0.75rem 1.5rem;
  border-radius: var(--radius-md);
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.2s;
}
.install-btn:hover { opacity: 0.9; }
.install-btn .btn-icon {
  width: 18px;
  height: 18px;
}

.ios-install-nudge {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-top: 1rem;
  padding: 0.85rem 1rem;
  background: linear-gradient(135deg, #eef6fb, #e8f4f8);
  border: 1px solid #b8dce8;
  border-radius: var(--radius-md);
  cursor: pointer;
}

.nudge-icon {
  flex-shrink: 0;
  color: #1a6b8a;
}

.nudge-text {
  font-size: 0.85rem;
  color: var(--text-secondary);
  line-height: 1.4;
}

.ios-share-icon {
  display: inline-block;
  font-size: 1rem;
  vertical-align: middle;
  color: #007aff;
}

/* Form Summary */
.form-summary {
  margin-top: 1.25rem;
  padding-top: 1rem;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}

.form-summary-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.75rem;
}

.form-summary-title {
  font-size: 0.8rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: rgba(255, 255, 255, 0.5);
}

.form-score-badge {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.9rem;
  font-weight: 800;
  color: #fff;
}

.form-score-badge.score-green {
  background: linear-gradient(135deg, #22c55e, #16a34a);
  box-shadow: 0 2px 10px rgba(34, 197, 94, 0.4);
}

.form-score-badge.score-yellow {
  background: linear-gradient(135deg, #eab308, #ca8a04);
  box-shadow: 0 2px 10px rgba(234, 179, 8, 0.4);
}

.form-score-badge.score-red {
  background: linear-gradient(135deg, #ef4444, #dc2626);
  box-shadow: 0 2px 10px rgba(239, 68, 68, 0.4);
}

.form-details {
  text-align: left;
}

.form-detail-line {
  font-size: 0.95rem;
  color: rgba(255, 255, 255, 0.7);
  margin-bottom: 0.15rem;
}

.form-detail-line.muted {
  color: rgba(255, 255, 255, 0.4);
  font-size: 0.85rem;
}

.form-detail-sub {
  font-size: 0.9rem;
  padding-left: 1rem;
  margin-bottom: 0.1rem;
  position: relative;
}

.form-detail-sub::before {
  content: '';
  position: absolute;
  left: 0.3rem;
  top: 0.55em;
  width: 5px;
  height: 5px;
  border-radius: 50%;
}

.form-detail-sub.highlight {
  color: #f59e0b;
  font-weight: 700;
}

.form-detail-sub.highlight::before {
  background: #f59e0b;
}

.form-detail-sub.bad {
  color: #f87171;
}

.form-detail-sub.bad::before {
  background: #f87171;
}

.form-issues {
  font-size: 0.8rem;
  color: rgba(255, 255, 255, 0.35);
  margin-top: 0.15rem;
}

.form-issue-sep {
  margin: 0 0.3rem;
}

.loading {
  text-align: center;
  color: var(--text-muted);
  padding: 3rem;
}
</style>
