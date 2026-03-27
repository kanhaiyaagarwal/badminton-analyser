<template>
  <div class="blog-post">
    <div class="blog-post-container">
      <router-link to="/blog" class="back-link">&larr; Back to Blog</router-link>

      <div v-if="loading" class="blog-loading">Loading...</div>

      <div v-else-if="!post" class="blog-not-found">
        <h1>Post not found</h1>
        <p>The blog post you're looking for doesn't exist.</p>
        <router-link to="/blog" class="back-link">Browse all posts</router-link>
      </div>

      <template v-else>
        <header class="post-header">
          <div class="post-meta">
            <time :datetime="post.date">{{ formatDate(post.date) }}</time>
            <span class="meta-dot">&middot;</span>
            <span>{{ post.author }}</span>
          </div>
          <h1 class="post-title font-display">{{ post.title }}</h1>
          <div class="post-tags" v-if="post.tags?.length">
            <span v-for="tag in post.tags" :key="tag" class="post-tag">{{ tag }}</span>
          </div>
        </header>

        <article class="post-content" v-html="htmlContent"></article>

        <div class="post-cta">
          <h2 class="cta-title font-display">Ready to check your form?</h2>
          <p class="cta-desc">Try PushUp Pro free — AI-powered form tracking right from your phone camera.</p>
          <router-link to="/signup" class="cta-button">Try PushUp Pro Free</router-link>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useHead } from '@unhead/vue'
import { marked } from 'marked'
import { posts } from '../content/blog/index.js'

const route = useRoute()
const post = ref(null)
const htmlContent = ref('')
const loading = ref(true)

const mdModules = import.meta.glob('../content/blog/*.md', { query: '?raw', import: 'default' })

const baseUrl = 'https://pushup.neymo.ai'

useHead({
  title: computed(() => post.value ? `${post.value.title} | PushUp Pro Blog` : 'Blog | PushUp Pro'),
  meta: computed(() => {
    if (!post.value) return []
    const p = post.value
    const url = `${baseUrl}/blog/${p.slug}`
    const image = p.image ? `${baseUrl}${p.image}` : `${baseUrl}/og-pushup-v2.png`
    return [
      { name: 'description', content: p.description },
      { property: 'og:title', content: p.title },
      { property: 'og:description', content: p.description },
      { property: 'og:type', content: 'article' },
      { property: 'og:url', content: url },
      { property: 'og:image', content: image },
      { property: 'og:site_name', content: 'PushUp Pro' },
      { property: 'article:published_time', content: p.date },
      { property: 'article:author', content: p.author || 'PushUp Pro' },
      ...(p.tags || []).map(tag => ({ property: 'article:tag', content: tag })),
      { name: 'twitter:card', content: 'summary_large_image' },
      { name: 'twitter:title', content: p.title },
      { name: 'twitter:description', content: p.description },
      { name: 'twitter:image', content: image },
    ]
  }),
  link: computed(() => {
    if (!post.value) return []
    return [{ rel: 'canonical', href: `${baseUrl}/blog/${post.value.slug}` }]
  }),
  script: computed(() => {
    if (!post.value) return []
    const p = post.value
    const url = `${baseUrl}/blog/${p.slug}`
    const image = p.image ? `${baseUrl}${p.image}` : `${baseUrl}/og-pushup-v2.png`
    const graph = [
      {
        '@type': 'Article',
        headline: p.title,
        description: p.description,
        image,
        datePublished: p.date,
        dateModified: p.date,
        author: {
          '@type': 'Organization',
          name: p.author || 'PushUp Pro',
          url: baseUrl,
        },
        publisher: {
          '@type': 'Organization',
          name: 'PushUp Pro',
          url: baseUrl,
          logo: {
            '@type': 'ImageObject',
            url: `${baseUrl}/apple-touch-icon.png`,
          },
        },
        mainEntityOfPage: {
          '@type': 'WebPage',
          '@id': url,
        },
        keywords: (p.tags || []).join(', '),
      },
    ]
    // HowTo schema for step-by-step guides
    if (p.howTo) {
      graph.push({
        '@type': 'HowTo',
        name: p.howTo.name,
        description: p.description,
        image,
        totalTime: p.howTo.totalTime,
        step: p.howTo.steps.map((s, i) => ({
          '@type': 'HowToStep',
          position: i + 1,
          name: s.name,
          text: s.text,
        })),
      })
    }
    // FAQ schema for common questions
    if (p.faq?.length) {
      graph.push({
        '@type': 'FAQPage',
        mainEntity: p.faq.map(f => ({
          '@type': 'Question',
          name: f.q,
          acceptedAnswer: {
            '@type': 'Answer',
            text: f.a,
          },
        })),
      })
    }
    return [{
      type: 'application/ld+json',
      innerHTML: JSON.stringify({ '@context': 'https://schema.org', '@graph': graph }),
    }]
  }),
})

function formatDate(dateStr) {
  const d = new Date(dateStr + 'T00:00:00')
  return d.toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })
}

async function loadPost(slug) {
  loading.value = true
  post.value = posts.find(p => p.slug === slug) || null

  if (!post.value) {
    loading.value = false
    return
  }

  const key = `../content/blog/${slug}.md`
  const loader = mdModules[key]
  if (loader) {
    const raw = await loader()
    htmlContent.value = marked(raw)
  } else {
    htmlContent.value = '<p>Content not available.</p>'
  }

  loading.value = false
}

onMounted(() => loadPost(route.params.slug))

watch(() => route.params.slug, (slug) => {
  if (slug) loadPost(slug)
})
</script>

<style scoped>
.blog-post {
  max-width: 740px;
  margin: 0 auto;
  padding: 2rem 1rem 4rem;
}

@media (min-width: 1024px) {
  .blog-post {
    max-width: 900px;
    padding: 3rem 2rem 5rem;
  }
}

@media (min-width: 1440px) {
  .blog-post {
    max-width: 1060px;
    padding: 3rem 3rem 5rem;
  }
}

.blog-post-container {
  width: 100%;
}

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

.back-link:hover {
  color: var(--color-primary);
}

.blog-loading,
.blog-not-found {
  text-align: center;
  padding: 4rem 1rem;
  color: var(--text-secondary);
}

.blog-not-found h1 {
  color: var(--text-primary);
  margin-bottom: 0.5rem;
}

.post-header {
  margin-bottom: 2rem;
  padding-bottom: 1.5rem;
  border-bottom: 1px solid var(--border-color);
}

.post-meta {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.85rem;
  color: var(--text-muted);
  margin-bottom: 0.75rem;
}

.meta-dot {
  color: var(--text-muted);
}

.post-title {
  font-size: 2rem;
  line-height: 1.25;
  color: var(--text-primary);
  margin: 0 0 1rem;
}

.post-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
}

.post-tag {
  font-size: 0.75rem;
  padding: 0.2rem 0.6rem;
  border-radius: var(--radius-full);
  background: var(--color-primary-light);
  color: var(--color-primary);
  font-weight: 500;
}

/* Blog prose styling */
.post-content :deep(h1),
.post-content :deep(h2),
.post-content :deep(h3) {
  color: var(--text-primary);
  margin-top: 2rem;
  margin-bottom: 0.75rem;
  line-height: 1.3;
}

.post-content :deep(h1) {
  display: none; /* Title already shown in header */
}

.post-content :deep(h2) {
  font-size: 1.4rem;
  padding-bottom: 0.4rem;
  border-bottom: 1px solid var(--border-color);
}

.post-content :deep(h3) {
  font-size: 1.15rem;
}

.post-content :deep(p) {
  color: var(--text-secondary);
  line-height: 1.75;
  margin-bottom: 1.25rem;
  font-size: 1rem;
}

.post-content :deep(ul),
.post-content :deep(ol) {
  color: var(--text-secondary);
  line-height: 1.75;
  margin-bottom: 1.25rem;
  padding-left: 1.5rem;
}

.post-content :deep(li) {
  margin-bottom: 0.4rem;
}

.post-content :deep(strong) {
  color: var(--text-primary);
  font-weight: 600;
}

.post-content :deep(a) {
  color: var(--color-primary);
  text-decoration: underline;
}

.post-content :deep(a:hover) {
  opacity: 0.85;
}

.post-content :deep(code) {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 0.15em 0.4em;
  font-size: 0.9em;
}

.post-content :deep(pre) {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 1rem;
  overflow-x: auto;
  margin-bottom: 1.25rem;
}

.post-content :deep(pre code) {
  background: none;
  border: none;
  padding: 0;
}

.post-content :deep(blockquote) {
  border-left: 3px solid var(--color-primary);
  margin: 1.5rem 0;
  padding: 0.5rem 1rem;
  color: var(--text-secondary);
  background: var(--color-primary-light);
  border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
}

.post-content :deep(img) {
  max-width: 100%;
  border-radius: var(--radius-md);
  margin: 1.5rem 0;
}

.post-content :deep(hr) {
  border: none;
  border-top: 1px solid var(--border-color);
  margin: 2rem 0;
}

/* CTA Banner */
.post-cta {
  margin-top: 3rem;
  padding: 2rem;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  text-align: center;
}

.cta-title {
  font-size: 1.35rem;
  color: var(--text-primary);
  margin: 0 0 0.5rem;
}

.cta-desc {
  color: var(--text-secondary);
  font-size: 0.95rem;
  margin: 0 0 1.25rem;
  line-height: 1.5;
}

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

.cta-button:hover {
  background: var(--gradient-primary-hover);
  box-shadow: var(--glow-primary);
}

@media (min-width: 1024px) {
  .post-title {
    font-size: 2.5rem;
  }

  .post-content :deep(h2) {
    font-size: 1.6rem;
  }

  .post-content :deep(h3) {
    font-size: 1.3rem;
  }

  .post-content :deep(p),
  .post-content :deep(ul),
  .post-content :deep(ol) {
    font-size: 1.1rem;
    line-height: 1.8;
  }
}

@media (max-width: 640px) {
  .blog-post {
    padding: 1.5rem 1rem 3rem;
  }

  .post-title {
    font-size: 1.5rem;
  }

  .post-cta {
    padding: 1.5rem;
  }
}
</style>
