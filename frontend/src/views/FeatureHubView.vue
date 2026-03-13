<template>
  <div class="hub">
    <!-- Welcome greeting -->
    <div
      v-motion
      :initial="{ opacity: 0, y: 12 }"
      :enter="{ opacity: 1, y: 0, transition: { duration: 400 } }"
      class="hub-header"
    >
      <h1 class="hub-greeting">
        Welcome back<span v-if="authStore.user">, {{ authStore.user.username }}</span>
      </h1>
      <p class="hub-subtitle">Choose a feature to get started</p>
    </div>

    <!-- Feature cards -->
    <div class="hub-cards">
      <router-link
        v-if="authStore.hasFeature('badminton')"
        to="/dashboard"
        v-motion
        :initial="{ opacity: 0, x: -12 }"
        :enter="{ opacity: 1, x: 0, transition: { delay: 100, duration: 400 } }"
        class="hub-card"
      >
        <span class="card-icon">&#127992;</span><!-- shuttlecock emoji, will be replaced with SVG icon later -->
        <div class="card-body">
          <h2 class="card-title">Badminton Analysis</h2>
          <p class="card-desc">Upload videos or stream live for real-time shot detection and coaching.</p>
        </div>
        <svg class="card-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="9 18 15 12 9 6"/>
        </svg>
      </router-link>

      <router-link
        v-if="hasAnyChallengeFeature"
        to="/challenges"
        v-motion
        :initial="{ opacity: 0, x: -12 }"
        :enter="{ opacity: 1, x: 0, transition: { delay: 200, duration: 400 } }"
        class="hub-card"
      >
        <img src="/mascot/otter-pushup-icon.png" alt="Challenges" class="card-icon-img" />
        <div class="card-body">
          <h2 class="card-title">Challenges</h2>
          <p class="card-desc">Plank holds, squat reps, and pushup challenges with live pose detection.</p>
        </div>
        <svg class="card-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="9 18 15 12 9 6"/>
        </svg>
      </router-link>

      <router-link
        v-if="authStore.hasFeature('workout')"
        to="/workout"
        v-motion
        :initial="{ opacity: 0, x: -12 }"
        :enter="{ opacity: 1, x: 0, transition: { delay: 250, duration: 400 } }"
        class="hub-card"
      >
        <span class="card-icon">&#127947;</span>
        <div class="card-body">
          <h2 class="card-title">AI Fitness Coach</h2>
          <p class="card-desc">Personalized workout plans, exercise library, and AI coaching.</p>
        </div>
        <svg class="card-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="9 18 15 12 9 6"/>
        </svg>
      </router-link>

      <router-link
        v-if="authStore.hasFeature('mimic')"
        to="/mimic"
        v-motion
        :initial="{ opacity: 0, x: -12 }"
        :enter="{ opacity: 1, x: 0, transition: { delay: 300, duration: 400 } }"
        class="hub-card"
      >
        <span class="card-icon">&#128378;</span><!-- mirror ball emoji, will be replaced with SVG icon later -->
        <div class="card-body">
          <h2 class="card-title">MoveMatch</h2>
          <p class="card-desc">Mirror dance moves from reels in real-time and score your accuracy.</p>
        </div>
        <svg class="card-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="9 18 15 12 9 6"/>
        </svg>
      </router-link>
    </div>

    <!-- Explore link -->
    <div
      v-motion
      :initial="{ opacity: 0 }"
      :enter="{ opacity: 1, transition: { delay: 420, duration: 400 } }"
      class="explore-wrapper"
    >
      <router-link to="/features" class="explore-link">
        Explore more features
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="9 18 15 12 9 6"/>
        </svg>
      </router-link>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useAuthStore } from '../stores/auth'

const authStore = useAuthStore()
const hasAnyChallengeFeature = computed(() =>
  authStore.hasFeature('pushup') || authStore.hasFeature('squat') || authStore.hasFeature('plank')
)
</script>

<style scoped>
.hub {
  padding: 1.25rem 1.25rem 1rem;
}

.hub-header {
  margin-bottom: 1.5rem;
}

.hub-greeting {
  font-size: 1.5rem;
  font-weight: 800;
  color: var(--text-primary);
}

.hub-subtitle {
  font-size: 0.875rem;
  color: var(--text-muted);
  margin-top: 0.25rem;
}

/* ---- Cards ---- */
.hub-cards {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.hub-card {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1.15rem 1.25rem;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 1rem;
  box-shadow: var(--shadow-sm);
  text-decoration: none;
  transition: box-shadow 0.2s, transform 0.15s;
}

.hub-card:hover {
  box-shadow: var(--shadow-md);
  transform: translateY(-1px);
}

.card-icon {
  font-size: 1.75rem;
  flex-shrink: 0;
}

.card-icon-img {
  width: 40px;
  height: 40px;
  object-fit: contain;
  flex-shrink: 0;
}

.card-body {
  flex: 1;
  min-width: 0;
}

.card-title {
  font-size: 0.95rem;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 0.15rem;
}

.card-desc {
  font-size: 0.8rem;
  color: var(--text-secondary);
  line-height: 1.4;
}

.card-arrow {
  width: 18px;
  height: 18px;
  flex-shrink: 0;
  color: var(--text-muted);
  transition: transform 0.2s;
}

.hub-card:hover .card-arrow {
  transform: translateX(3px);
}

/* ---- Explore ---- */
.explore-wrapper {
  text-align: center;
  margin-top: 1.5rem;
}

.explore-link {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.6rem 1.25rem;
  border: 1px solid var(--color-primary);
  border-radius: 1rem;
  color: var(--color-primary);
  font-size: 0.875rem;
  font-weight: 600;
  text-decoration: none;
  transition: background 0.2s, color 0.2s;
}

.explore-link:hover {
  background: var(--color-primary);
  color: #fff;
}
</style>
