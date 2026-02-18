<template>
  <div class="hub-container">
    <div class="hub-header">
      <h1>Welcome back<span v-if="authStore.user">, {{ authStore.user.username }}</span></h1>
      <p class="hub-subtitle">Choose a feature to get started</p>
    </div>

    <div class="feature-grid">
      <router-link v-if="authStore.hasFeature('badminton')" to="/dashboard" class="feature-card">
        <div class="card-icon">&#127992;</div>
        <h2>Badminton Analysis</h2>
        <p>Upload videos or stream live for real-time shot detection, movement tracking, and coaching insights.</p>
        <span class="card-action">Open Dashboard &rarr;</span>
      </router-link>

      <router-link v-if="hasAnyChallengeFeature" to="/challenges" class="feature-card">
        <div class="card-icon">&#9889;</div>
        <h2>Challenges</h2>
        <p>Test your fitness with timed plank holds, max squat reps, and pushup challenges using live pose detection.</p>
        <span class="card-action">Start Challenge &rarr;</span>
      </router-link>

      <router-link to="/workout" class="feature-card coming-soon">
        <div class="card-icon">&#127947;</div>
        <h2>Workout with Me</h2>
        <p>Follow guided workout routines with real-time form feedback and rep counting.</p>
        <span class="card-badge">Coming Soon</span>
      </router-link>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useAuthStore } from '../stores/auth'

const authStore = useAuthStore()
const hasAnyChallengeFeature = computed(() =>
  authStore.hasFeature('pushup') || authStore.hasFeature('squat_hold') || authStore.hasFeature('squat_half') || authStore.hasFeature('squat_full') || authStore.hasFeature('plank')
)
</script>

<style scoped>
.hub-container {
  max-width: 1000px;
  margin: 0 auto;
  padding: 2rem 1rem;
}

.hub-header {
  text-align: center;
  margin-bottom: 3rem;
}

.hub-header h1 {
  color: var(--text-primary);
  font-size: 2rem;
  margin-bottom: 0.5rem;
}

.hub-subtitle {
  color: var(--text-muted);
  font-size: 1.1rem;
}

.feature-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 1.5rem;
}

.feature-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 2rem;
  text-decoration: none;
  transition: all 0.3s ease;
  display: flex;
  flex-direction: column;
  box-shadow: var(--shadow-md);
}

.feature-card:hover {
  border-color: var(--color-primary);
  transform: translateY(-4px);
  box-shadow: var(--shadow-lg);
}

.feature-card.coming-soon {
  opacity: 0.6;
  pointer-events: none;
}

.card-icon {
  font-size: 2.5rem;
  margin-bottom: 1rem;
}

.feature-card h2 {
  color: var(--color-primary);
  font-size: 1.3rem;
  margin-bottom: 0.75rem;
}

.feature-card p {
  color: var(--text-secondary);
  font-size: 0.95rem;
  line-height: 1.5;
  flex: 1;
}

.card-action {
  color: var(--color-primary);
  font-size: 0.9rem;
  margin-top: 1.25rem;
  font-weight: 500;
}

.card-badge {
  display: inline-block;
  background: var(--color-primary-light);
  color: var(--color-primary);
  padding: 0.25rem 0.75rem;
  border-radius: var(--radius-lg);
  font-size: 0.8rem;
  margin-top: 1.25rem;
  width: fit-content;
}
</style>
