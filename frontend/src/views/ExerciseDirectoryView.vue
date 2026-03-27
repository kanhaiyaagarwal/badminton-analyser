<template>
  <div class="exercise-dir">
    <header class="dir-header">
      <h1 class="dir-title font-display">Exercise Library</h1>
      <p class="dir-subtitle">Form guides, video demos, and AI tracking for {{ exercises.length }}+ exercises</p>
    </header>

    <!-- Muscle group filters -->
    <div class="filter-row">
      <button
        v-for="group in muscleGroups"
        :key="group"
        class="filter-btn"
        :class="{ active: activeFilter === group }"
        @click="activeFilter = activeFilter === group ? null : group"
      >{{ group }}</button>
    </div>

    <!-- Exercise grid -->
    <div class="exercise-grid">
      <router-link
        v-for="ex in filteredExercises"
        :key="ex.slug"
        :to="`/exercises/${ex.slug}`"
        class="exercise-card"
      >
        <div v-if="ex.videoId" class="card-thumb">
          <img :src="`https://img.youtube.com/vi/${ex.videoId}/mqdefault.jpg`" :alt="`${ex.name} demonstration`" loading="lazy" />
        </div>
        <div class="card-body">
          <h2 class="card-name">{{ ex.name }}</h2>
          <div class="card-meta">
            <span class="card-muscle">{{ ex.primaryMuscle }}</span>
            <span class="card-diff" :class="ex.difficulty">{{ ex.difficulty }}</span>
            <span v-if="ex.aiTracked" class="card-ai">AI</span>
          </div>
        </div>
      </router-link>
    </div>

    <!-- CTA -->
    <div class="dir-cta">
      <h2 class="cta-title font-display">Get real-time form feedback on every exercise</h2>
      <p class="cta-desc">PushUp Pro uses your phone camera to track your form, count reps, and coach you through each set.</p>
      <router-link to="/signup" class="cta-button">Try PushUp Pro Free</router-link>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useHead } from '@unhead/vue'
import { exercises } from '../content/exercises/index.js'

const activeFilter = ref('all')

const muscleGroups = computed(() => {
  const groups = new Set(exercises.map(e => e.primaryMuscle))
  return ['all', ...Array.from(groups).sort()]
})

const filteredExercises = computed(() => {
  if (!activeFilter.value || activeFilter.value === 'all') return exercises
  return exercises.filter(e => e.primaryMuscle === activeFilter.value)
})

const baseUrl = 'https://pushup.neymo.ai'

useHead({
  title: 'Exercise Library — Form Guides & Video Demos | PushUp Pro',
  meta: [
    { name: 'description', content: `Browse ${exercises.length}+ exercise form guides with step-by-step instructions, video demos, common mistakes, and AI tracking. From dead bugs to Turkish get-ups.` },
    { property: 'og:title', content: 'Exercise Library | PushUp Pro' },
    { property: 'og:description', content: `${exercises.length}+ exercise guides with form cues, video demos, and AI tracking.` },
    { property: 'og:type', content: 'website' },
    { property: 'og:url', content: `${baseUrl}/exercises` },
    { property: 'og:image', content: `${baseUrl}/og-pushup-v2.png` },
    { name: 'twitter:card', content: 'summary_large_image' },
    { name: 'twitter:title', content: 'Exercise Library | PushUp Pro' },
    { name: 'twitter:description', content: `${exercises.length}+ exercise guides with form cues, video demos, and AI tracking.` },
    { name: 'twitter:image', content: `${baseUrl}/og-pushup-v2.png` },
  ],
  link: [
    { rel: 'canonical', href: `${baseUrl}/exercises` },
  ],
  script: [
    {
      type: 'application/ld+json',
      innerHTML: JSON.stringify({
        '@context': 'https://schema.org',
        '@type': 'CollectionPage',
        name: 'Exercise Library',
        description: `${exercises.length}+ exercise form guides with video demos and AI tracking.`,
        url: `${baseUrl}/exercises`,
        isPartOf: { '@type': 'WebSite', name: 'PushUp Pro', url: baseUrl },
      }),
    },
  ],
})
</script>

<style scoped>
.exercise-dir {
  max-width: 900px;
  margin: 0 auto;
  padding: 2rem 1rem 4rem;
}
@media (min-width: 1440px) { .exercise-dir { max-width: 1100px; padding: 3rem 3rem 5rem; } }

.dir-header { margin-bottom: 1.5rem; }
.dir-title { font-size: 2rem; color: var(--text-primary); margin: 0 0 0.5rem; }
.dir-subtitle { color: var(--text-secondary); font-size: 1.05rem; margin: 0; }

/* Filters */
.filter-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  margin-bottom: 1.5rem;
}
.filter-btn {
  font-size: 0.8rem;
  padding: 0.3rem 0.75rem;
  border-radius: var(--radius-full);
  border: 1px solid var(--border-color);
  background: var(--bg-card);
  color: var(--text-secondary);
  cursor: pointer;
  text-transform: capitalize;
  transition: all 0.15s ease;
}
.filter-btn:hover { border-color: var(--color-primary); color: var(--color-primary); }
.filter-btn.active {
  background: var(--color-primary);
  color: var(--color-primary-text);
  border-color: var(--color-primary);
}

/* Grid */
.exercise-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 1rem;
  margin-bottom: 2.5rem;
}
.exercise-card {
  display: block;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  overflow: hidden;
  text-decoration: none;
  transition: box-shadow 0.2s ease, border-color 0.2s ease;
}
.exercise-card:hover { border-color: var(--color-primary); box-shadow: var(--glow-primary); }

.card-thumb { aspect-ratio: 16/9; overflow: hidden; background: var(--bg-page); }
.card-thumb img { width: 100%; height: 100%; object-fit: cover; }

.card-body { padding: 0.75rem 1rem; }
.card-name { font-size: 1rem; color: var(--text-primary); margin: 0 0 0.4rem; font-weight: 500; }
.card-meta { display: flex; align-items: center; gap: 0.4rem; }
.card-muscle {
  font-size: 0.72rem;
  padding: 0.15rem 0.5rem;
  border-radius: var(--radius-full);
  background: var(--color-primary-light);
  color: var(--color-primary);
  text-transform: capitalize;
}
.card-diff {
  font-size: 0.72rem;
  padding: 0.15rem 0.5rem;
  border-radius: var(--radius-full);
}
.card-diff.beginner { background: #dcfce7; color: #166534; }
.card-diff.intermediate { background: #fef3c7; color: #92400e; }
.card-diff.advanced { background: #fecaca; color: #991b1b; }
.card-ai {
  font-size: 0.65rem;
  padding: 0.15rem 0.4rem;
  border-radius: var(--radius-full);
  background: #ede9fe;
  color: #6d28d9;
  font-weight: 600;
}

/* CTA */
.dir-cta {
  padding: 2rem;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  text-align: center;
}
.cta-title { font-size: 1.35rem; color: var(--text-primary); margin: 0 0 0.5rem; }
.cta-desc { color: var(--text-secondary); font-size: 0.95rem; margin: 0 0 1.25rem; line-height: 1.5; }
.cta-button {
  display: inline-block;
  padding: 0.75rem 1.75rem;
  background: var(--gradient-primary);
  color: var(--color-primary-text);
  font-weight: 600;
  font-size: 0.95rem;
  border-radius: var(--radius-full);
  text-decoration: none;
  transition: background 0.2s ease, box-shadow 0.2s ease;
}
.cta-button:hover { background: var(--gradient-primary-hover); box-shadow: var(--glow-primary); }

@media (max-width: 640px) {
  .exercise-dir { padding: 1.5rem 1rem 3rem; }
  .dir-title { font-size: 1.5rem; }
  .exercise-grid { grid-template-columns: 1fr; }
}
</style>
