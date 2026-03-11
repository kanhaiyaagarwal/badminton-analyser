<template>
  <div class="landing">
    <!-- Content -->
    <div class="landing-content">

      <!-- Logo + Brand -->
      <div
        v-motion
        :initial="{ opacity: 0, scale: 0.85 }"
        :enter="{ opacity: 1, scale: 1, transition: { duration: 400 } }"
        class="brand-block"
      >
        <img src="/mascot/otter-mascot.png" alt="PushUp Pro" class="brand-logo" />
      </div>

      <h1
        v-motion
        :initial="{ opacity: 0, y: 16 }"
        :enter="{ opacity: 1, y: 0, transition: { delay: 120, duration: 400 } }"
        class="brand-title"
      >PushUp Pro</h1>

      <p
        v-motion
        :initial="{ opacity: 0, y: 16 }"
        :enter="{ opacity: 1, y: 0, transition: { delay: 240, duration: 400 } }"
        class="brand-tagline"
      >AI-powered motion analysis for athletes. Track, compete, and improve.</p>

      <!-- CTAs -->
      <div
        v-motion
        :initial="{ opacity: 0, y: 16 }"
        :enter="{ opacity: 1, y: 0, transition: { delay: 360, duration: 400 } }"
        class="cta-group"
      >
        <button @click="$router.push('/login')" class="btn-primary">Login</button>
        <button @click="$router.push('/signup')" class="btn-outline">Sign Up</button>
      </div>

      <!-- Feature cards -->
      <div
        v-motion
        :initial="{ opacity: 0, y: 20 }"
        :enter="{ opacity: 1, y: 0, transition: { delay: 500, duration: 500 } }"
        class="features"
      >
        <div v-for="(f, i) in features" :key="i" class="feature-card">
          <img v-if="f.iconSrc" :src="f.iconSrc" :alt="f.title" class="feature-icon-img" />
          <span v-else class="feature-icon">{{ f.icon }}</span>
          <div>
            <h3 class="feature-title">{{ f.title }}</h3>
            <p class="feature-desc">{{ f.desc }}</p>
          </div>
        </div>
      </div>

    </div>
  </div>
</template>

<script setup>
const features = [
  { icon: null, iconSrc: '/mascot/otter-pushup-icon.png', title: 'Challenges', desc: 'Pushups, squats, planks — tracked live with AI pose detection.' },
  { icon: '🏸', iconSrc: null, title: 'Analysis', desc: 'Upload or stream video for shot detection and coaching.' },
  { icon: '🪩', iconSrc: null, title: 'MoveMatch', desc: 'Mirror dance moves from reels and score your accuracy.' }
]
</script>

<style scoped>
.landing {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem 1.5rem 2rem;
}

.landing-content {
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
}

/* ---- Brand ---- */
.brand-block {
  margin-bottom: 1rem;
}

.brand-logo {
  width: 72px;
  height: 72px;
  border-radius: 1rem;
  box-shadow: var(--shadow-md);
}

.brand-title {
  font-size: 2rem;
  font-weight: 800;
  color: var(--text-primary);
  text-align: center;
  margin-bottom: 0.5rem;
}

.brand-tagline {
  font-size: 0.95rem;
  color: var(--text-muted);
  text-align: center;
  line-height: 1.5;
  max-width: 280px;
  margin-bottom: 2rem;
}

/* ---- CTAs ---- */
.cta-group {
  display: flex;
  gap: 0.75rem;
  width: 100%;
}

.btn-primary {
  flex: 1;
  height: 52px;
  background: var(--gradient-primary);
  color: #fff;
  border: none;
  border-radius: 1rem;
  font-size: 1rem;
  font-weight: 700;
  font-family: inherit;
  cursor: pointer;
  transition: opacity 0.2s, transform 0.15s;
}

.btn-primary:hover {
  opacity: 0.92;
  transform: translateY(-1px);
}

.btn-outline {
  flex: 1;
  height: 52px;
  background: transparent;
  border: 2px solid var(--color-primary);
  color: var(--color-primary);
  border-radius: 1rem;
  font-size: 1rem;
  font-weight: 700;
  font-family: inherit;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-outline:hover {
  background: var(--color-primary-light);
}

/* ---- Features ---- */
.features {
  width: 100%;
  margin-top: 2.5rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.feature-card {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem 1.25rem;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 1rem;
  box-shadow: var(--shadow-sm);
}

.feature-icon {
  font-size: 1.75rem;
  flex-shrink: 0;
}

.feature-icon-img {
  width: 40px;
  height: 40px;
  object-fit: contain;
  flex-shrink: 0;
}

.feature-title {
  font-size: 0.875rem;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 0.15rem;
}

.feature-desc {
  font-size: 0.8rem;
  color: var(--text-secondary);
  line-height: 1.4;
}
</style>
