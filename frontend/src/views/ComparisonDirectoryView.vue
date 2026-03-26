<template>
  <div class="compare-dir">
    <header class="dir-header">
      <h1 class="dir-title font-display">PushUp Pro vs The Competition</h1>
      <p class="dir-subtitle">Honest, side-by-side comparisons so you can pick the right app for how you train.</p>
    </header>

    <div class="compare-grid">
      <router-link v-for="c in comparisons" :key="c.slug" :to="`/compare/${c.slug}`" class="compare-card">
        <h2 class="card-title">PushUp Pro vs {{ c.competitor }}</h2>
        <p class="card-desc">{{ c.heroQuestion }}</p>
      </router-link>
    </div>

    <div class="dir-cta">
      <h2 class="cta-title font-display">Still not sure? Try it yourself.</h2>
      <p class="cta-desc">PushUp Pro is free to start — no download, just open it on your phone and do a set.</p>
      <router-link to="/signup" class="cta-button">Try PushUp Pro Free</router-link>
    </div>
  </div>
</template>

<script setup>
import { useHead } from '@unhead/vue'
import { comparisons } from '../content/comparisons/index.js'

const baseUrl = 'https://pushup.neymo.ai'

useHead({
  title: 'PushUp Pro vs Competitors — Honest Comparisons | PushUp Pro',
  meta: [
    { name: 'description', content: 'Compare PushUp Pro with Fitbod, Peloton, Nike Training Club, and personal trainers. Side-by-side features, pricing, and who each is best for.' },
    { property: 'og:title', content: 'PushUp Pro vs Competitors' },
    { property: 'og:description', content: 'Honest side-by-side comparisons of PushUp Pro with popular fitness apps and personal trainers.' },
    { property: 'og:type', content: 'website' },
    { property: 'og:url', content: `${baseUrl}/compare` },
    { property: 'og:image', content: `${baseUrl}/og-pushup-v2.png` },
    { name: 'twitter:card', content: 'summary_large_image' },
    { name: 'twitter:title', content: 'PushUp Pro vs Competitors' },
    { name: 'twitter:description', content: 'Honest side-by-side comparisons with popular fitness apps.' },
  ],
  link: [{ rel: 'canonical', href: `${baseUrl}/compare` }],
})
</script>

<style scoped>
.compare-dir { max-width: 800px; margin: 0 auto; padding: 2rem 1rem 4rem; }

.dir-header { margin-bottom: 2rem; }
.dir-title { font-size: 2rem; color: var(--text-primary); margin: 0 0 0.5rem; }
.dir-subtitle { color: var(--text-secondary); font-size: 1.05rem; margin: 0; }

.compare-grid { display: flex; flex-direction: column; gap: 1rem; margin-bottom: 2.5rem; }
.compare-card {
  display: block; padding: 1.25rem 1.5rem;
  background: var(--bg-card); border: 1px solid var(--border-color);
  border-radius: var(--radius-lg); text-decoration: none;
  transition: border-color 0.2s, box-shadow 0.2s;
}
.compare-card:hover { border-color: var(--color-primary); box-shadow: var(--glow-primary); }
.card-title { font-size: 1.1rem; color: var(--text-primary); margin: 0 0 0.25rem; font-weight: 600; }
.card-desc { font-size: 0.9rem; color: var(--text-muted); margin: 0; }

.dir-cta { padding: 2rem; background: var(--bg-card); border: 1px solid var(--border-color); border-radius: var(--radius-lg); text-align: center; }
.cta-title { font-size: 1.35rem; color: var(--text-primary); margin: 0 0 0.5rem; }
.cta-desc { color: var(--text-secondary); font-size: 0.95rem; margin: 0 0 1.25rem; }
.cta-button { display: inline-block; padding: 0.75rem 1.75rem; background: var(--gradient-primary); color: var(--color-primary-text); font-weight: 600; border-radius: var(--radius-full); text-decoration: none; }
.cta-button:hover { background: var(--gradient-primary-hover); box-shadow: var(--glow-primary); }
</style>
