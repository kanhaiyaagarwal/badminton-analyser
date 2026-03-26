<template>
  <div class="blog">
    <header class="blog-header">
      <h1 class="blog-title font-display">Blog</h1>
      <p class="blog-subtitle">Tips, guides, and updates from the PushUp Pro team</p>
    </header>

    <div class="blog-grid">
      <router-link
        v-for="post in posts"
        :key="post.slug"
        :to="`/blog/${post.slug}`"
        class="blog-card"
      >
        <div v-if="post.image" class="blog-card-image">
          <img :src="post.image" :alt="post.title" loading="lazy" @error="onImgError" />
        </div>
        <div class="blog-card-body">
          <div class="blog-card-meta">
            <time :datetime="post.date">{{ formatDate(post.date) }}</time>
            <span v-if="post.author" class="meta-dot">&middot;</span>
            <span v-if="post.author">{{ post.author }}</span>
          </div>
          <h2 class="blog-card-title">{{ post.title }}</h2>
          <p class="blog-card-desc">{{ post.description }}</p>
          <div class="blog-card-tags" v-if="post.tags?.length">
            <span v-for="tag in post.tags" :key="tag" class="blog-tag">{{ tag }}</span>
          </div>
        </div>
      </router-link>
    </div>
  </div>
</template>

<script setup>
import { useHead } from '@unhead/vue'
import { posts } from '../content/blog/index.js'

useHead({
  title: 'Blog | PushUp Pro',
  meta: [
    { name: 'description', content: 'Tips, guides, and updates from the PushUp Pro team. Exercise form guides, workout tips, and AI fitness coaching insights.' },
    { property: 'og:title', content: 'Blog | PushUp Pro' },
    { property: 'og:description', content: 'Tips, guides, and updates from the PushUp Pro team.' },
    { property: 'og:type', content: 'website' },
    { property: 'og:url', content: 'https://pushup.neymo.ai/blog' },
    { name: 'twitter:card', content: 'summary_large_image' },
    { name: 'twitter:title', content: 'Blog | PushUp Pro' },
    { name: 'twitter:description', content: 'Tips, guides, and updates from the PushUp Pro team.' },
  ],
  link: [
    { rel: 'canonical', href: 'https://pushup.neymo.ai/blog' },
  ],
  script: [
    {
      type: 'application/ld+json',
      innerHTML: JSON.stringify({
        '@context': 'https://schema.org',
        '@type': 'Organization',
        name: 'PushUp Pro',
        url: 'https://pushup.neymo.ai',
        logo: 'https://pushup.neymo.ai/apple-touch-icon.png',
        description: 'AI-powered fitness coaching with real-time camera form tracking. Pushups, squats, planks — tracked live from your phone.',
        sameAs: [],
      }),
    },
    {
      type: 'application/ld+json',
      innerHTML: JSON.stringify({
        '@context': 'https://schema.org',
        '@type': 'CollectionPage',
        name: 'Blog | PushUp Pro',
        description: 'Tips, guides, and updates from the PushUp Pro team.',
        url: 'https://pushup.neymo.ai/blog',
        isPartOf: {
          '@type': 'WebSite',
          name: 'PushUp Pro',
          url: 'https://pushup.neymo.ai',
        },
      }),
    },
  ],
})

function formatDate(dateStr) {
  const d = new Date(dateStr + 'T00:00:00')
  return d.toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })
}

function onImgError(e) {
  e.target.style.display = 'none'
}
</script>

<style scoped>
.blog {
  max-width: 900px;
  margin: 0 auto;
  padding: 2rem 1rem 4rem;
}

@media (min-width: 1440px) {
  .blog {
    max-width: 1100px;
    padding: 3rem 3rem 5rem;
  }
}

.blog-header {
  margin-bottom: 2.5rem;
}

.blog-title {
  font-size: 2rem;
  color: var(--text-primary);
  margin: 0 0 0.5rem;
}

.blog-subtitle {
  color: var(--text-secondary);
  font-size: 1.05rem;
  margin: 0;
}

.blog-grid {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.blog-card {
  display: block;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  overflow: hidden;
  text-decoration: none;
  transition: box-shadow 0.2s ease, border-color 0.2s ease;
}

.blog-card:hover {
  border-color: var(--color-primary);
  box-shadow: var(--glow-primary);
}

.blog-card-image {
  width: 100%;
  aspect-ratio: 2 / 1;
  overflow: hidden;
  background: var(--bg-page);
}

.blog-card-image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.blog-card-body {
  padding: 1.25rem 1.5rem;
}

.blog-card-meta {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.82rem;
  color: var(--text-muted);
  margin-bottom: 0.5rem;
}

.meta-dot {
  color: var(--text-muted);
}

.blog-card-title {
  font-size: 1.25rem;
  color: var(--text-primary);
  margin: 0 0 0.5rem;
  line-height: 1.35;
}

.blog-card-desc {
  color: var(--text-secondary);
  font-size: 0.95rem;
  line-height: 1.5;
  margin: 0 0 0.75rem;
}

.blog-card-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
}

.blog-tag {
  font-size: 0.75rem;
  padding: 0.2rem 0.6rem;
  border-radius: var(--radius-full);
  background: var(--color-primary-light);
  color: var(--color-primary);
  font-weight: 500;
}

@media (max-width: 640px) {
  .blog {
    padding: 1.5rem 1rem 3rem;
  }

  .blog-title {
    font-size: 1.5rem;
  }

  .blog-card-body {
    padding: 1rem;
  }
}
</style>
