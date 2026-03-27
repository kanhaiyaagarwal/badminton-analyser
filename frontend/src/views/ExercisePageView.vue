<template>
  <div class="exercise-page">
    <div class="exercise-page-container">
      <router-link to="/exercises" class="back-link">&larr; All Exercises</router-link>

      <div v-if="!exercise" class="not-found">
        <h1>Exercise not found</h1>
        <p>The exercise you're looking for doesn't exist.</p>
        <router-link to="/exercises" class="back-link">Browse all exercises</router-link>
      </div>

      <template v-else>
        <header class="ex-header">
          <div class="ex-badges">
            <span class="badge badge-muscle">{{ exercise.primaryMuscle }}</span>
            <span class="badge badge-difficulty" :class="exercise.difficulty">{{ exercise.difficulty }}</span>
            <span v-if="exercise.aiTracked" class="badge badge-ai">AI Tracked</span>
          </div>
          <h1 class="ex-title font-display">{{ exercise.name }}</h1>
          <p class="ex-intro">{{ exercise.intro }}</p>
        </header>

        <!-- Video -->
        <div v-if="exercise.videoId" class="ex-video">
          <div class="video-wrapper" v-if="showVideo">
            <iframe
              :src="`https://www.youtube.com/embed/${exercise.videoId}?autoplay=1&rel=0`"
              frameborder="0"
              allow="autoplay; encrypted-media"
              allowfullscreen
            ></iframe>
          </div>
          <div v-else class="video-thumbnail" @click="showVideo = true">
            <img :src="`https://img.youtube.com/vi/${exercise.videoId}/hqdefault.jpg`" :alt="`${exercise.name} demonstration video`" loading="lazy" />
            <div class="play-button">&#9654;</div>
          </div>
        </div>

        <!-- Form Cues -->
        <section class="ex-section">
          <h2>How to Do {{ exercise.name }}: Step by Step</h2>
          <ol class="form-cues-list">
            <li v-for="(cue, i) in exercise.formCues" :key="i">{{ cue }}</li>
          </ol>
        </section>

        <!-- Common Mistakes -->
        <section class="ex-section">
          <h2>Common Mistakes to Avoid</h2>
          <ul class="mistakes-list">
            <li v-for="(mistake, i) in exercise.commonMistakes" :key="i">{{ mistake }}</li>
          </ul>
        </section>

        <!-- Muscles Worked -->
        <section class="ex-section">
          <h2>Muscles Worked</h2>
          <div class="muscle-tags">
            <span v-for="m in exercise.muscleGroups" :key="m" class="muscle-tag">{{ m }}</span>
          </div>
          <div class="ex-details">
            <div v-if="exercise.equipment.length && exercise.equipment[0] !== 'none'" class="detail-row">
              <span class="detail-label">Equipment</span>
              <span class="detail-value">{{ exercise.equipment.join(', ') }}</span>
            </div>
            <div v-else class="detail-row">
              <span class="detail-label">Equipment</span>
              <span class="detail-value">No equipment needed</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">Tracking</span>
              <span class="detail-value">{{ exercise.trackingMode === 'hold' ? 'Hold for time' : exercise.trackingMode === 'reps' ? 'Count reps' : 'Timed' }}</span>
            </div>
          </div>
        </section>

        <!-- AI Tracking CTA -->
        <div class="ex-cta">
          <h2 class="cta-title font-display" v-if="exercise.aiTracked">Track Your {{ exercise.name }} With AI</h2>
          <h2 class="cta-title font-display" v-else>Try AI-Powered Form Tracking</h2>
          <p class="cta-desc" v-if="exercise.aiTracked">
            PushUp Pro tracks your {{ exercise.name.toLowerCase() }} form in real-time using your phone camera.
            It counts your {{ exercise.trackingMode === 'hold' ? 'hold time' : 'reps' }}, checks your form, and gives you feedback as you go.
          </p>
          <p class="cta-desc" v-else>
            PushUp Pro uses AI to track your exercise form in real-time — counting reps, checking body alignment, and coaching you through each set.
          </p>
          <router-link to="/signup" class="cta-button">Try PushUp Pro Free</router-link>
        </div>

        <!-- Related Exercises -->
        <section v-if="relatedExercises.length" class="ex-section">
          <h2>Related Exercises</h2>
          <div class="related-grid">
            <router-link
              v-for="rel in relatedExercises"
              :key="rel.slug"
              :to="`/exercises/${rel.slug}`"
              class="related-card"
            >
              <span class="related-name">{{ rel.name }}</span>
              <span class="related-muscle">{{ rel.primaryMuscle }}</span>
            </router-link>
          </div>
        </section>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useHead } from '@unhead/vue'
import { exercises, getExercise } from '../content/exercises/index.js'

const route = useRoute()
const showVideo = ref(false)

const exercise = computed(() => getExercise(route.params.slug))

const baseUrl = 'https://pushup.neymo.ai'

const relatedExercises = computed(() => {
  if (!exercise.value) return []
  const muscle = exercise.value.primaryMuscle
  return exercises
    .filter(e => e.primaryMuscle === muscle && e.slug !== exercise.value.slug)
    .slice(0, 4)
})

// Reset video on navigation
watch(() => route.params.slug, () => { showVideo.value = false })

useHead({
  title: computed(() => exercise.value ? `${exercise.value.title} | PushUp Pro` : 'Exercise Guide | PushUp Pro'),
  meta: computed(() => {
    if (!exercise.value) return []
    const e = exercise.value
    const url = `${baseUrl}/exercises/${e.slug}`
    const image = e.videoId ? `https://img.youtube.com/vi/${e.videoId}/hqdefault.jpg` : `${baseUrl}/og-pushup-v2.png`
    return [
      { name: 'description', content: e.description },
      { property: 'og:title', content: e.title },
      { property: 'og:description', content: e.description },
      { property: 'og:type', content: 'article' },
      { property: 'og:url', content: url },
      { property: 'og:image', content: image },
      { property: 'og:site_name', content: 'PushUp Pro' },
      { name: 'twitter:card', content: 'summary_large_image' },
      { name: 'twitter:title', content: e.title },
      { name: 'twitter:description', content: e.description },
      { name: 'twitter:image', content: image },
    ]
  }),
  link: computed(() => {
    if (!exercise.value) return []
    return [{ rel: 'canonical', href: `${baseUrl}/exercises/${exercise.value.slug}` }]
  }),
  script: computed(() => {
    if (!exercise.value) return []
    const e = exercise.value
    const url = `${baseUrl}/exercises/${e.slug}`
    const image = e.videoId ? `https://img.youtube.com/vi/${e.videoId}/hqdefault.jpg` : `${baseUrl}/og-pushup-v2.png`
    const graph = [
      {
        '@type': 'HowTo',
        name: `How to Do ${e.name}`,
        description: e.description,
        image,
        ...(e.videoId ? { video: { '@type': 'VideoObject', name: `${e.name} Demonstration`, contentUrl: `https://www.youtube.com/watch?v=${e.videoId}`, thumbnailUrl: image } } : {}),
        step: e.formCues.map((cue, i) => ({
          '@type': 'HowToStep',
          position: i + 1,
          text: cue,
        })),
      },
      {
        '@type': 'ExerciseAction',
        name: e.name,
        exerciseType: e.name,
        description: e.intro,
      },
    ]
    // FAQ from common mistakes
    if (e.commonMistakes?.length) {
      graph.push({
        '@type': 'FAQPage',
        mainEntity: e.commonMistakes.map(m => {
          const parts = m.split(' — ')
          return {
            '@type': 'Question',
            name: `What's wrong with ${parts[0].toLowerCase()}?`,
            acceptedAnswer: { '@type': 'Answer', text: m },
          }
        }),
      })
    }
    return [{
      type: 'application/ld+json',
      innerHTML: JSON.stringify({ '@context': 'https://schema.org', '@graph': graph }),
    }]
  }),
})
</script>

<style scoped>
.exercise-page {
  max-width: 740px;
  margin: 0 auto;
  padding: 2rem 1rem 4rem;
}

@media (min-width: 1024px) {
  .exercise-page { max-width: 900px; padding: 3rem 2rem 5rem; }
}

.exercise-page-container { width: 100%; }

.back-link {
  display: inline-block;
  color: var(--text-secondary);
  text-decoration: none;
  font-size: 0.9rem;
  padding: 0.5rem 0;
  min-height: 44px;
  margin-bottom: 1rem;
  transition: color 0.15s ease;
}
.back-link:hover { color: var(--color-primary); }

.not-found { text-align: center; padding: 4rem 1rem; color: var(--text-secondary); }
.not-found h1 { color: var(--text-primary); margin-bottom: 0.5rem; }

/* Header */
.ex-header { margin-bottom: 2rem; }
.ex-badges { display: flex; flex-wrap: wrap; gap: 0.5rem; margin-bottom: 0.75rem; }
.badge {
  font-size: 0.75rem;
  padding: 0.2rem 0.6rem;
  border-radius: var(--radius-full);
  font-weight: 500;
  text-transform: capitalize;
}
.badge-muscle { background: var(--color-primary-light); color: var(--color-primary); }
.badge-difficulty.beginner { background: #dcfce7; color: #166534; }
.badge-difficulty.intermediate { background: #fef3c7; color: #92400e; }
.badge-difficulty.advanced { background: #fecaca; color: #991b1b; }
.badge-ai { background: #ede9fe; color: #6d28d9; }

.ex-title {
  font-size: 2rem;
  color: var(--text-primary);
  margin: 0 0 1rem;
  line-height: 1.25;
}
.ex-intro {
  color: var(--text-secondary);
  font-size: 1rem;
  line-height: 1.75;
  margin: 0;
}

/* Video */
.ex-video { margin-bottom: 2rem; border-radius: var(--radius-lg); overflow: hidden; }
.video-wrapper { position: relative; padding-bottom: 56.25%; height: 0; }
.video-wrapper iframe { position: absolute; top: 0; left: 0; width: 100%; height: 100%; }
.video-thumbnail {
  position: relative;
  cursor: pointer;
  background: var(--bg-page);
}
.video-thumbnail img { width: 100%; display: block; }
.play-button {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 64px;
  height: 64px;
  background: rgba(0,0,0,0.7);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 1.5rem;
  transition: background 0.2s;
}
.video-thumbnail:hover .play-button { background: var(--color-primary); }

/* Sections */
.ex-section {
  margin-bottom: 2rem;
  padding-bottom: 1.5rem;
  border-bottom: 1px solid var(--border-color);
}
.ex-section h2 {
  font-size: 1.3rem;
  color: var(--text-primary);
  margin: 0 0 1rem;
}

.form-cues-list {
  padding-left: 1.5rem;
  color: var(--text-secondary);
  line-height: 1.75;
}
.form-cues-list li { margin-bottom: 0.5rem; }

.mistakes-list {
  list-style: none;
  padding: 0;
  color: var(--text-secondary);
  line-height: 1.75;
}
.mistakes-list li {
  padding: 0.5rem 0 0.5rem 1.5rem;
  position: relative;
}
.mistakes-list li::before {
  content: '\26A0';
  position: absolute;
  left: 0;
  color: #f59e0b;
}

/* Muscles & Details */
.muscle-tags { display: flex; flex-wrap: wrap; gap: 0.4rem; margin-bottom: 1rem; }
.muscle-tag {
  font-size: 0.8rem;
  padding: 0.25rem 0.75rem;
  border-radius: var(--radius-full);
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
  text-transform: capitalize;
}
.ex-details { display: flex; flex-direction: column; gap: 0.5rem; }
.detail-row { display: flex; gap: 1rem; font-size: 0.9rem; }
.detail-label { color: var(--text-muted); min-width: 80px; }
.detail-value { color: var(--text-secondary); text-transform: capitalize; }

/* CTA */
.ex-cta {
  margin: 2rem 0;
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

/* Related */
.related-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 0.75rem; }
.related-card {
  display: flex;
  flex-direction: column;
  padding: 0.75rem 1rem;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  text-decoration: none;
  transition: border-color 0.2s ease;
}
.related-card:hover { border-color: var(--color-primary); }
.related-name { font-size: 0.9rem; color: var(--text-primary); font-weight: 500; }
.related-muscle { font-size: 0.75rem; color: var(--text-muted); text-transform: capitalize; }

@media (max-width: 640px) {
  .exercise-page { padding: 1.5rem 1rem 3rem; }
  .ex-title { font-size: 1.5rem; }
  .related-grid { grid-template-columns: 1fr; }
}
</style>
