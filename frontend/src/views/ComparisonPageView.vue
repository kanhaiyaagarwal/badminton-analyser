<template>
  <div class="compare-page">
    <div class="compare-container">
      <router-link to="/compare" class="back-link">&larr; All Comparisons</router-link>

      <div v-if="!comp" class="not-found">
        <h1>Comparison not found</h1>
        <router-link to="/compare" class="back-link">Browse all comparisons</router-link>
      </div>

      <template v-else>
        <header class="comp-header">
          <p class="comp-question">{{ comp.heroQuestion }}</p>
          <h1 class="comp-title font-display">{{ comp.title }}</h1>
          <p class="comp-intro">{{ comp.intro }}</p>
        </header>

        <!-- Feature comparison table -->
        <section class="comp-section">
          <h2>Feature Comparison</h2>
          <div class="comp-table-wrap">
            <table class="comp-table">
              <thead>
                <tr>
                  <th>Feature</th>
                  <th>{{ comp.competitor }}</th>
                  <th>PushUp Pro</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(row, i) in comp.comparison" :key="i">
                  <td class="feature-name">
                    {{ row.feature }}
                    <span v-if="row.note" class="feature-note">{{ row.note }}</span>
                  </td>
                  <td class="check-cell">
                    <span v-if="row.competitor === true" class="check yes">&#10003;</span>
                    <span v-else-if="row.competitor === false" class="check no">&#10007;</span>
                    <span v-else class="check price">{{ row.competitor }}</span>
                  </td>
                  <td class="check-cell">
                    <span v-if="row.pushupPro === true" class="check yes">&#10003;</span>
                    <span v-else-if="row.pushupPro === false" class="check no">&#10007;</span>
                    <span v-else class="check price">{{ row.pushupPro }}</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <!-- Strengths -->
        <div class="strengths-grid">
          <section class="strength-col">
            <h2>Where {{ comp.competitor }} Wins</h2>
            <ul class="strength-list competitor">
              <li v-for="(s, i) in comp.competitorStrengths" :key="i">{{ s }}</li>
            </ul>
            <p class="best-for"><strong>Best for:</strong> {{ comp.bestFor.competitor }}</p>
          </section>
          <section class="strength-col">
            <h2>Where PushUp Pro Wins</h2>
            <ul class="strength-list pushup">
              <li v-for="(s, i) in comp.pushupProStrengths" :key="i">{{ s }}</li>
            </ul>
            <p class="best-for"><strong>Best for:</strong> {{ comp.bestFor.pushupPro }}</p>
          </section>
        </div>

        <!-- Verdict -->
        <section class="comp-verdict">
          <h2>The Verdict</h2>
          <p>{{ comp.verdict }}</p>
        </section>

        <!-- CTA -->
        <div class="comp-cta">
          <h2 class="cta-title font-display">See the difference for yourself</h2>
          <p class="cta-desc">Try PushUp Pro's AI form tracking free — no download, just open it on your phone.</p>
          <router-link to="/signup" class="cta-button">Try PushUp Pro Free</router-link>
        </div>

        <!-- Related comparisons -->
        <section v-if="relatedComps.length" class="comp-section">
          <h2>More Comparisons</h2>
          <div class="related-grid">
            <router-link v-for="r in relatedComps" :key="r.slug" :to="`/compare/${r.slug}`" class="related-card">
              <span class="related-name">PushUp Pro vs {{ r.competitor }}</span>
            </router-link>
          </div>
        </section>
      </template>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useHead } from '@unhead/vue'
import { comparisons, getComparison } from '../content/comparisons/index.js'

const route = useRoute()
const comp = computed(() => getComparison(route.params.slug))

const baseUrl = 'https://pushup.neymo.ai'

const relatedComps = computed(() => {
  if (!comp.value) return []
  return comparisons.filter(c => c.slug !== comp.value.slug)
})

useHead({
  title: computed(() => comp.value ? `${comp.value.title} | PushUp Pro` : 'Compare | PushUp Pro'),
  meta: computed(() => {
    if (!comp.value) return []
    const c = comp.value
    const url = `${baseUrl}/compare/${c.slug}`
    return [
      { name: 'description', content: c.description },
      { property: 'og:title', content: c.title },
      { property: 'og:description', content: c.description },
      { property: 'og:type', content: 'article' },
      { property: 'og:url', content: url },
      { property: 'og:image', content: `${baseUrl}/og-pushup-v2.png` },
      { property: 'og:site_name', content: 'PushUp Pro' },
      { name: 'twitter:card', content: 'summary_large_image' },
      { name: 'twitter:title', content: c.title },
      { name: 'twitter:description', content: c.description },
      { name: 'twitter:image', content: `${baseUrl}/og-pushup-v2.png` },
    ]
  }),
  link: computed(() => {
    if (!comp.value) return []
    return [{ rel: 'canonical', href: `${baseUrl}/compare/${comp.value.slug}` }]
  }),
  script: computed(() => {
    if (!comp.value) return []
    const c = comp.value
    return [{
      type: 'application/ld+json',
      innerHTML: JSON.stringify({
        '@context': 'https://schema.org',
        '@graph': [
          {
            '@type': 'Article',
            headline: c.title,
            description: c.description,
            author: { '@type': 'Organization', name: 'PushUp Pro', url: baseUrl },
            publisher: { '@type': 'Organization', name: 'PushUp Pro', url: baseUrl },
            mainEntityOfPage: { '@type': 'WebPage', '@id': `${baseUrl}/compare/${c.slug}` },
          },
          {
            '@type': 'FAQPage',
            mainEntity: [
              {
                '@type': 'Question',
                name: `Is PushUp Pro better than ${c.competitor}?`,
                acceptedAnswer: { '@type': 'Answer', text: c.verdict },
              },
              {
                '@type': 'Question',
                name: `Who should use ${c.competitor} vs PushUp Pro?`,
                acceptedAnswer: { '@type': 'Answer', text: `${c.competitor} is best for: ${c.bestFor.competitor}. PushUp Pro is best for: ${c.bestFor.pushupPro}.` },
              },
            ],
          },
        ],
      }),
    }]
  }),
})
</script>

<style scoped>
.compare-page { max-width: 800px; margin: 0 auto; padding: 2rem 1rem 4rem; }
@media (min-width: 1024px) { .compare-page { max-width: 960px; padding: 3rem 2rem 5rem; } }

.compare-container { width: 100%; }

.back-link { display: inline-block; color: var(--text-secondary); text-decoration: none; font-size: 0.9rem; margin-bottom: 1.5rem; }
.back-link:hover { color: var(--color-primary); }

.not-found { text-align: center; padding: 4rem 1rem; color: var(--text-secondary); }
.not-found h1 { color: var(--text-primary); }

/* Header */
.comp-header { margin-bottom: 2.5rem; }
.comp-question { font-size: 0.9rem; color: var(--color-primary); text-transform: uppercase; letter-spacing: 0.05em; margin: 0 0 0.5rem; font-weight: 600; }
.comp-title { font-size: 2rem; color: var(--text-primary); margin: 0 0 1rem; line-height: 1.25; }
.comp-intro { color: var(--text-secondary); font-size: 1rem; line-height: 1.75; margin: 0; }

/* Sections */
.comp-section { margin-bottom: 2rem; }
.comp-section h2 { font-size: 1.3rem; color: var(--text-primary); margin: 0 0 1rem; }

/* Feature table */
.comp-table-wrap { overflow-x: auto; margin: 0 -1rem; padding: 0 1rem; }
.comp-table { width: 100%; border-collapse: collapse; font-size: 0.9rem; }
.comp-table th { text-align: left; padding: 0.75rem; border-bottom: 2px solid var(--border-color); color: var(--text-primary); font-weight: 600; }
.comp-table td { padding: 0.6rem 0.75rem; border-bottom: 1px solid var(--border-color); }
.feature-name { color: var(--text-primary); }
.feature-note { display: block; font-size: 0.75rem; color: var(--text-muted); margin-top: 0.15rem; }
.check-cell { text-align: center; width: 100px; }
.check.yes { color: #22c55e; font-weight: bold; font-size: 1.1rem; }
.check.no { color: #ef4444; font-size: 1.1rem; }
.check.price { color: var(--text-secondary); font-size: 0.8rem; font-weight: 500; }

/* Strengths */
.strengths-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; margin-bottom: 2rem; }
.strength-col h2 { font-size: 1.15rem; color: var(--text-primary); margin: 0 0 0.75rem; }
.strength-list { list-style: none; padding: 0; margin: 0 0 1rem; }
.strength-list li { padding: 0.4rem 0 0.4rem 1.25rem; position: relative; color: var(--text-secondary); font-size: 0.9rem; line-height: 1.5; }
.strength-list.competitor li::before { content: '\25CF'; position: absolute; left: 0; color: var(--text-muted); font-size: 0.6rem; top: 0.65rem; }
.strength-list.pushup li::before { content: '\25CF'; position: absolute; left: 0; color: var(--color-primary); font-size: 0.6rem; top: 0.65rem; }
.best-for { font-size: 0.85rem; color: var(--text-muted); line-height: 1.5; }

/* Verdict */
.comp-verdict { padding: 1.5rem; background: var(--bg-card); border: 1px solid var(--border-color); border-radius: var(--radius-lg); margin-bottom: 2rem; }
.comp-verdict h2 { font-size: 1.2rem; color: var(--text-primary); margin: 0 0 0.75rem; }
.comp-verdict p { color: var(--text-secondary); line-height: 1.75; margin: 0; font-size: 0.95rem; }

/* CTA */
.comp-cta { margin: 2rem 0; padding: 2rem; background: var(--bg-card); border: 1px solid var(--border-color); border-radius: var(--radius-lg); text-align: center; }
.cta-title { font-size: 1.35rem; color: var(--text-primary); margin: 0 0 0.5rem; }
.cta-desc { color: var(--text-secondary); font-size: 0.95rem; margin: 0 0 1.25rem; }
.cta-button { display: inline-block; padding: 0.75rem 1.75rem; background: var(--gradient-primary); color: var(--color-primary-text); font-weight: 600; font-size: 0.95rem; border-radius: var(--radius-full); text-decoration: none; }
.cta-button:hover { background: var(--gradient-primary-hover); box-shadow: var(--glow-primary); }

/* Related */
.related-grid { display: flex; flex-wrap: wrap; gap: 0.75rem; }
.related-card { padding: 0.6rem 1rem; background: var(--bg-card); border: 1px solid var(--border-color); border-radius: var(--radius-md); text-decoration: none; transition: border-color 0.2s; }
.related-card:hover { border-color: var(--color-primary); }
.related-name { font-size: 0.9rem; color: var(--text-primary); font-weight: 500; }

@media (max-width: 640px) {
  .compare-page { padding: 1.5rem 1rem 3rem; }
  .comp-title { font-size: 1.5rem; }
  .strengths-grid { grid-template-columns: 1fr; }
}
</style>
