<template>
  <div class="explore">
    <!-- Header -->
    <header class="explore-header">
      <h1 class="explore-title font-display">Explore</h1>

      <!-- Search bar -->
      <div class="search-bar glass">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="20" height="20" class="search-icon">
          <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
        </svg>
        <input
          v-model="searchQuery"
          type="text"
          placeholder="Search workouts, exercises..."
          class="search-input"
        />
      </div>
    </header>

    <!-- Categories -->
    <section class="explore-section">
      <h2 class="section-label">Categories</h2>
      <div class="category-grid">
        <router-link
          v-for="(cat, i) in filteredCategories"
          :key="cat.label"
          :to="cat.route"
          v-motion
          :initial="{ opacity: 0, y: 20 }"
          :enter="{ opacity: 1, y: 0, transition: { delay: i * 100 } }"
          class="category-card glass"
        >
          <div class="category-icon-circle">
            <span class="category-emoji">{{ cat.emoji }}</span>
          </div>
          <div>
            <h3 class="category-name">{{ cat.label }}</h3>
            <p class="category-count">{{ cat.count }}</p>
          </div>
        </router-link>
      </div>
    </section>

    <!-- Featured / Available Features -->
    <section class="explore-section">
      <h2 class="section-label">Featured</h2>
      <div class="featured-list">
        <router-link
          v-for="(feat, i) in filteredFeatures"
          :key="feat.title"
          :to="feat.route"
          v-motion
          :initial="{ opacity: 0, x: -20 }"
          :enter="{ opacity: 1, x: 0, transition: { delay: 300 + i * 100 } }"
          class="featured-card glass"
        >
          <div class="featured-icon-box">
            <span class="featured-emoji">{{ feat.emoji }}</span>
          </div>
          <div class="featured-info">
            <h3 class="featured-title font-display">{{ feat.title }}</h3>
            <div class="featured-meta">
              <span>{{ feat.subtitle }}</span>
              <span class="meta-dot">•</span>
              <span class="featured-badge" :class="feat.badgeClass">{{ feat.badge }}</span>
            </div>
          </div>
          <svg class="featured-chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="18" height="18">
            <polyline points="9 18 15 12 9 6"/>
          </svg>
        </router-link>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useAuthStore } from '../stores/auth'

const authStore = useAuthStore()
const searchQuery = ref('')

const allCategories = [
  { emoji: '🏋️', label: 'Strength', count: 'Exercises & Challenges', route: '/challenges', feature: ['pushup', 'squat', 'plank'] },
  { emoji: '💪', label: 'Coaching', count: 'AI-Powered Plans', route: '/hub', feature: ['workout'] },
  { emoji: '💃', label: 'MoveMatch', count: 'Dance & Mimic', route: '/mimic', feature: ['mimic'] },
]

const allFeatures = [
  { emoji: '💪', title: 'AI Fitness Coach', subtitle: 'Personalized plans', badge: 'AI-Powered', badgeClass: 'badge-primary', route: '/hub', feature: 'workout' },
  { emoji: '🔥', title: 'Fitness Challenges', subtitle: 'Pushup, squat, plank', badge: 'Camera Tracking', badgeClass: 'badge-secondary', route: '/challenges', feature: ['pushup', 'squat', 'plank'] },
  { emoji: '🎯', title: 'MoveMatch', subtitle: 'Mirror dance moves', badge: 'Fun', badgeClass: 'badge-primary', route: '/mimic', feature: 'mimic' },
]

function hasFeature(feature) {
  if (Array.isArray(feature)) return feature.some(f => authStore.hasFeature(f))
  return authStore.hasFeature(feature)
}

const filteredCategories = computed(() => {
  const cats = allCategories.filter(c => hasFeature(c.feature))
  if (!searchQuery.value) return cats
  const q = searchQuery.value.toLowerCase()
  return cats.filter(c => c.label.toLowerCase().includes(q))
})

const filteredFeatures = computed(() => {
  const feats = allFeatures.filter(f => hasFeature(f.feature))
  if (!searchQuery.value) return feats
  const q = searchQuery.value.toLowerCase()
  return feats.filter(f => f.title.toLowerCase().includes(q) || f.subtitle.toLowerCase().includes(q))
})
</script>

<style scoped>
.explore {
  padding-bottom: 2rem;
}

/* Header */
.explore-header {
  padding: 3rem 1.5rem 1.5rem;
}

.explore-title {
  font-size: 1.75rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: -0.02em;
  color: var(--text-primary);
  margin-bottom: 1rem;
}

/* Search */
.search-bar {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1rem;
  border-radius: 1rem;
}

.search-icon {
  color: var(--text-muted);
  flex-shrink: 0;
}

.search-input {
  flex: 1;
  background: transparent;
  border: none;
  outline: none;
  font-size: 0.875rem;
  color: var(--text-primary);
}

.search-input::placeholder {
  color: var(--text-muted);
}

/* Sections */
.explore-section {
  padding: 0 1.5rem;
  margin-bottom: 2rem;
}

.section-label {
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--text-muted);
  margin-bottom: 0.75rem;
}

/* Category grid */
.category-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.75rem;
}

.category-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  padding: 1rem 0.5rem;
  border-radius: 1rem;
  text-decoration: none;
  text-align: center;
  transition: transform 0.15s, border-color 0.2s;
}

.category-card:hover {
  border-color: var(--color-primary);
  transform: scale(1.03);
}

.category-card:active {
  transform: scale(0.95);
}

.category-icon-circle {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, rgba(242, 101, 34, 0.2) 0%, rgba(242, 101, 34, 0.05) 100%);
}

.category-emoji {
  font-size: 1.5rem;
}

.category-name {
  font-size: 0.85rem;
  font-weight: 700;
  color: var(--text-primary);
}

.category-count {
  font-size: 0.7rem;
  color: var(--text-muted);
  margin-top: 0.1rem;
}

/* Featured list */
.featured-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.featured-card {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1.25rem 1rem;
  border-radius: 1rem;
  text-decoration: none;
  transition: transform 0.15s, border-color 0.2s;
  cursor: pointer;
}

.featured-card:hover {
  border-color: var(--color-primary);
  transform: scale(1.01);
}

.featured-card:active {
  transform: scale(0.98);
}

.featured-icon-box {
  width: 56px;
  height: 56px;
  border-radius: 0.75rem;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, rgba(242, 101, 34, 0.2) 0%, rgba(242, 101, 34, 0.05) 100%);
  flex-shrink: 0;
}

.featured-emoji {
  font-size: 1.75rem;
}

.featured-info {
  flex: 1;
  min-width: 0;
}

.featured-title {
  font-size: 1rem;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 0.25rem;
}

.featured-meta {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.8rem;
  color: var(--text-muted);
}

.meta-dot {
  opacity: 0.5;
}

.featured-badge {
  font-size: 0.7rem;
  font-weight: 600;
  padding: 0.15rem 0.5rem;
  border-radius: 999px;
}

.badge-primary {
  background: rgba(242, 101, 34, 0.15);
  color: hsl(18 95% 55%);
}

.badge-secondary {
  background: rgba(20, 184, 166, 0.15);
  color: hsl(175 70% 45%);
}

.badge-accent {
  background: rgba(245, 158, 11, 0.15);
  color: hsl(45 85% 55%);
}

.featured-chevron {
  flex-shrink: 0;
  color: var(--text-muted);
  transition: transform 0.2s;
}

.featured-card:hover .featured-chevron {
  transform: translateX(3px);
  color: var(--color-primary);
}
</style>
