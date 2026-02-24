/**
 * Thin wrapper around gtag() for custom GA4 events.
 * Safe to call even if GA4 isn't loaded (e.g. local dev).
 */
function track(eventName, params = {}) {
  if (typeof window.gtag === 'function') {
    window.gtag('event', eventName, params)
  }
}

export function useAnalytics() {
  return {
    challengeStarted(challengeType) {
      track('challenge_started', { challenge_type: challengeType })
    },
    challengeCompleted(challengeType, score, durationSeconds, isPersonalBest) {
      track('challenge_completed', {
        challenge_type: challengeType,
        score,
        duration_seconds: durationSeconds,
        is_personal_best: isPersonalBest,
      })
    },
    signupCompleted(method) {
      track('sign_up', { method })
    },
    leaderboardViewed(challengeType) {
      track('leaderboard_viewed', { challenge_type: challengeType })
    },
    shareClicked(challengeType, score) {
      track('share', { challenge_type: challengeType, score })
    },
  }
}
