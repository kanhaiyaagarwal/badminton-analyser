<template>
  <div class="landing-page">
    <!-- Top Navigation Bar -->
    <nav class="top-nav">
      <div class="nav-logo">
        <span class="logo-icon">🏸</span>
        <span class="logo-text">pushup.neymo.ai</span>
      </div>
      <div class="nav-links">
        <a href="#features" class="nav-link">Features</a>
        <a href="#how-it-works" class="nav-link">How it Works</a>
        <button class="nav-link contact-btn" @click="scrollToContact">Contact Us</button>
        <button class="login-btn" @click="goToLogin">Login</button>
      </div>
    </nav>

    <!-- Hero Section -->
    <section class="hero">
      <div class="hero-content">
        <h1 class="hero-title">
          Master Every
          <span class="highlight">Move</span>
        </h1>
        <p class="hero-subtitle">
          AI-powered motion analysis for badminton players.
          Upload your match videos or analyze in real-time using your camera.
        </p>
        <div class="hero-cta">
          <button class="cta-primary" @click="goToSignup">Get Started Free</button>
          <button class="cta-secondary" @click="goToLogin">
            <span class="play-icon">▶</span>
            Watch Demo
          </button>
        </div>
        <div class="hero-features">
          <div class="hero-feature">
            <span class="feature-check">✓</span>
            <span>Upload & Analyze Videos</span>
          </div>
          <div class="hero-feature">
            <span class="feature-check">✓</span>
            <span>Real-time Camera Analysis</span>
          </div>
          <div class="hero-feature">
            <span class="feature-check">✓</span>
            <span>Detailed Performance Reports</span>
          </div>
        </div>
      </div>
      <div class="hero-image">
        <img src="@/assets/images/badminton.png" alt="Badminton Player" />
        <div class="image-glow"></div>
      </div>
    </section>

    <!-- Banner Section -->
    <section class="banner-section">
      <img src="@/assets/images/banner.png" alt="Badminton Analysis Banner" class="banner-image" />
    </section>

    <!-- Features Section -->
    <section id="features" class="features">
      <h2 class="section-title">Analyze Your Game</h2>
      <p class="section-subtitle">Powerful AI tools to elevate your badminton performance</p>

      <div class="features-grid">
        <div class="feature-card active">
          <div class="feature-icon">🏸</div>
          <h3>Shot Detection</h3>
          <p>Automatically detect and classify every shot - smashes, drops, clears, drives, and net plays.</p>
          <span class="feature-badge">Available</span>
        </div>

        <div class="feature-card active">
          <div class="feature-icon">🗺️</div>
          <h3>Movement Heatmaps</h3>
          <p>Visualize your court coverage and identify areas for improvement.</p>
          <span class="feature-badge">Available</span>
        </div>

        <div class="feature-card active">
          <div class="feature-icon">📊</div>
          <h3>Performance Analytics</h3>
          <p>Get detailed statistics on rally patterns, shot distribution, and game flow.</p>
          <span class="feature-badge">Available</span>
        </div>

        <div class="feature-card coming-soon">
          <div class="feature-icon">💃</div>
          <h3>Dance Mimic</h3>
          <p>Upload a dance video and see how well you can match the moves in real-time.</p>
          <span class="feature-badge soon">Coming Soon</span>
        </div>

        <div class="feature-card coming-soon">
          <div class="feature-icon">🧘</div>
          <h3>Yoga Perfect</h3>
          <p>Get real-time feedback on your yoga poses and improve your form.</p>
          <span class="feature-badge soon">Coming Soon</span>
        </div>

        <div class="feature-card coming-soon">
          <div class="feature-icon">💪</div>
          <h3>Fitness Counter</h3>
          <p>Count your reps, track workouts, and challenge your friends.</p>
          <span class="feature-badge soon">Coming Soon</span>
        </div>
      </div>
    </section>

    <!-- How It Works Section -->
    <section id="how-it-works" class="how-it-works">
      <h2 class="section-title">How It Works</h2>
      <p class="section-subtitle">Two ways to analyze your game</p>

      <div class="modes-container">
        <!-- Upload Mode -->
        <div class="mode-card">
          <div class="mode-icon">📹</div>
          <h3 class="mode-title">Upload & Analyze</h3>
          <p class="mode-desc">Perfect for reviewing recorded matches</p>
          <div class="mode-steps">
            <div class="mode-step">
              <span class="mode-step-num">1</span>
              <span>Upload your match video (MP4, AVI, MOV)</span>
            </div>
            <div class="mode-step">
              <span class="mode-step-num">2</span>
              <span>Mark the court boundaries</span>
            </div>
            <div class="mode-step">
              <span class="mode-step-num">3</span>
              <span>Get detailed analysis & heatmaps</span>
            </div>
          </div>
        </div>

        <!-- Live Mode -->
        <div class="mode-card">
          <div class="mode-icon">📷</div>
          <h3 class="mode-title">Real-time Analysis</h3>
          <p class="mode-desc">Live feedback during practice sessions</p>
          <div class="mode-steps">
            <div class="mode-step">
              <span class="mode-step-num">1</span>
              <span>Set up your camera facing the court</span>
            </div>
            <div class="mode-step">
              <span class="mode-step-num">2</span>
              <span>Mark the court boundaries</span>
            </div>
            <div class="mode-step">
              <span class="mode-step-num">3</span>
              <span>Get live shot detection & stats</span>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- Contact Section -->
    <section id="contact" class="contact">
      <h2 class="section-title">Get In Touch</h2>
      <p class="section-subtitle">Have questions? We'd love to hear from you.</p>

      <div class="contact-content">
        <div class="contact-info">
          <div class="contact-item">
            <span class="contact-icon">📧</span>
            <a href="mailto:connect@neymo.ai">connect@neymo.ai</a>
          </div>
        </div>
      </div>
    </section>

    <!-- Footer -->
    <footer class="footer">
      <div class="footer-content">
        <div class="footer-logo">
          <span class="logo-icon">🏸</span>
          <span class="logo-text">pushup.neymo.ai</span>
        </div>
        <p class="footer-text">© 2025 pushup.neymo.ai. Master Every Move.</p>
      </div>
    </footer>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'

const router = useRouter()

function goToLogin() {
  router.push('/login')
}

function goToSignup() {
  router.push('/signup')
}

function scrollToContact() {
  document.getElementById('contact')?.scrollIntoView({ behavior: 'smooth' })
}
</script>

<style scoped>
.landing-page {
  min-height: 100vh;
  position: relative;
  color: var(--text-primary);
  background: var(--bg-page);
}

/* Navigation */
.top-nav {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 4rem;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(10px);
  z-index: 100;
  border-bottom: 1px solid var(--border-color);
}

.nav-logo {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 1.5rem;
  font-weight: bold;
}

.logo-icon {
  font-size: 1.8rem;
}

.logo-text {
  background: var(--gradient-primary);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.nav-links {
  display: flex;
  align-items: center;
  gap: 2rem;
}

.nav-link {
  color: var(--text-secondary);
  text-decoration: none;
  font-size: 0.95rem;
  transition: color 0.2s;
  background: none;
  border: none;
  cursor: pointer;
}

.nav-link:hover {
  color: var(--color-primary);
}

.login-btn {
  padding: 0.6rem 1.5rem;
  background: var(--gradient-primary);
  color: var(--text-on-primary);
  border: none;
  border-radius: var(--radius-full);
  font-weight: 600;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
}

.login-btn:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-lg);
}

/* Hero Section */
.hero {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 100vh;
  padding: 8rem 4rem 4rem;
  gap: 4rem;
  background: var(--gradient-primary);
}

.hero-content {
  flex: 1;
  max-width: 600px;
}

.hero-title {
  font-size: 4rem;
  font-weight: 800;
  line-height: 1.1;
  margin-bottom: 1.5rem;
  color: #fff;
}

.highlight {
  background: linear-gradient(135deg, #fff, rgba(255, 255, 255, 0.7));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.hero-subtitle {
  font-size: 1.25rem;
  color: rgba(255, 255, 255, 0.8);
  line-height: 1.6;
  margin-bottom: 2rem;
}

.hero-cta {
  display: flex;
  gap: 1rem;
  margin-bottom: 3rem;
}

.cta-primary {
  padding: 1rem 2rem;
  background: #fff;
  color: var(--color-primary);
  border: none;
  border-radius: var(--radius-full);
  font-size: 1.1rem;
  font-weight: 600;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
}

.cta-primary:hover {
  transform: translateY(-3px);
  box-shadow: var(--shadow-xl);
}

.cta-secondary {
  padding: 1rem 2rem;
  background: transparent;
  color: #fff;
  border: 2px solid rgba(255, 255, 255, 0.4);
  border-radius: var(--radius-full);
  font-size: 1.1rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  transition: border-color 0.2s, background 0.2s;
}

.cta-secondary:hover {
  border-color: #fff;
  background: rgba(255, 255, 255, 0.15);
}

.play-icon {
  font-size: 0.8rem;
}

.hero-features {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.hero-feature {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  color: rgba(255, 255, 255, 0.85);
  font-size: 1rem;
}

.feature-check {
  color: #fff;
  font-weight: bold;
  font-size: 1.1rem;
}

.hero-image {
  flex: 1;
  position: relative;
  display: flex;
  justify-content: center;
  align-items: center;
}

.hero-image img {
  max-width: 100%;
  max-height: 500px;
  object-fit: contain;
  border-radius: var(--radius-xl);
  position: relative;
  z-index: 1;
}

.image-glow {
  position: absolute;
  width: 80%;
  height: 80%;
  background: radial-gradient(ellipse, rgba(255, 255, 255, 0.2) 0%, transparent 70%);
  filter: blur(40px);
  z-index: 0;
}

/* Banner Section */
.banner-section {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem 4rem;
}

.banner-image {
  width: 100%;
  height: auto;
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-xl);
  border: 1px solid var(--border-color);
}

/* Sections Common */
.section-title {
  font-size: 2.5rem;
  text-align: center;
  margin-bottom: 0.5rem;
  color: var(--text-primary);
}

.section-subtitle {
  text-align: center;
  color: var(--text-muted);
  font-size: 1.1rem;
  margin-bottom: 3rem;
}

/* Features Section */
.features {
  position: relative;
  z-index: 1;
  padding: 6rem 4rem;
  background: var(--bg-page);
}

.features-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 2rem;
  max-width: 1200px;
  margin: 0 auto;
}

.feature-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-xl);
  padding: 2rem;
  transition: transform 0.3s, box-shadow 0.3s;
  position: relative;
  overflow: hidden;
  box-shadow: var(--shadow-md);
}

.feature-card.active:hover {
  transform: translateY(-5px);
  box-shadow: var(--shadow-lg);
  border-color: var(--color-primary);
}

.feature-card.coming-soon {
  opacity: 0.7;
}

.feature-icon {
  font-size: 2.5rem;
  margin-bottom: 1rem;
}

.feature-card h3 {
  font-size: 1.3rem;
  margin-bottom: 0.75rem;
  color: var(--text-primary);
}

.feature-card p {
  color: var(--text-muted);
  line-height: 1.5;
  font-size: 0.95rem;
}

.feature-badge {
  display: inline-block;
  margin-top: 1rem;
  padding: 0.3rem 0.8rem;
  background: var(--color-primary-light);
  color: var(--color-primary);
  border-radius: var(--radius-full);
  font-size: 0.8rem;
  font-weight: 600;
}

.feature-badge.soon {
  background: var(--color-destructive-light);
  color: var(--color-destructive);
}

/* How It Works */
.how-it-works {
  position: relative;
  z-index: 1;
  padding: 6rem 4rem;
  background: var(--bg-card);
}

.modes-container {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 2rem;
  max-width: 900px;
  margin: 0 auto;
}

.mode-card {
  background: var(--bg-page);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-xl);
  padding: 2rem;
  transition: transform 0.3s, box-shadow 0.3s;
  box-shadow: var(--shadow-md);
}

.mode-card:hover {
  transform: translateY(-5px);
  box-shadow: var(--shadow-lg);
  border-color: var(--color-primary);
}

.mode-icon {
  font-size: 3rem;
  margin-bottom: 1rem;
}

.mode-title {
  font-size: 1.4rem;
  margin-bottom: 0.5rem;
  color: var(--text-primary);
}

.mode-desc {
  color: var(--text-muted);
  margin-bottom: 1.5rem;
  font-size: 0.95rem;
}

.mode-steps {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.mode-step {
  display: flex;
  align-items: center;
  gap: 1rem;
  color: var(--text-secondary);
  font-size: 0.9rem;
}

.mode-step-num {
  width: 28px;
  height: 28px;
  background: var(--gradient-primary);
  color: var(--text-on-primary);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.85rem;
  font-weight: bold;
  flex-shrink: 0;
}

/* Contact Section */
.contact {
  position: relative;
  z-index: 1;
  padding: 6rem 4rem;
  background: var(--bg-page);
}

.contact-content {
  max-width: 600px;
  margin: 0 auto;
  text-align: center;
}

.contact-info {
  display: flex;
  justify-content: center;
  gap: 3rem;
}

.contact-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: var(--text-secondary);
}

.contact-item a {
  color: var(--color-primary);
  text-decoration: none;
  transition: color 0.2s;
}

.contact-item a:hover {
  color: var(--color-primary-hover);
  text-decoration: underline;
}

.contact-icon {
  font-size: 1.2rem;
}

/* Footer */
.footer {
  position: relative;
  z-index: 1;
  padding: 2rem 4rem;
  background: var(--bg-card);
  border-top: 1px solid var(--border-color);
}

.footer-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  max-width: 1200px;
  margin: 0 auto;
}

.footer-logo {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 1.2rem;
}

.footer-text {
  color: var(--text-muted);
  font-size: 0.9rem;
}

/* Responsive */
@media (max-width: 1024px) {
  .hero {
    flex-direction: column;
    text-align: center;
    padding-top: 6rem;
  }

  .hero-content {
    max-width: 100%;
  }

  .hero-cta {
    justify-content: center;
  }

  .hero-stats {
    justify-content: center;
  }

  .features-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .modes-container {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .top-nav {
    padding: 1rem 2rem;
  }

  .nav-links {
    gap: 1rem;
  }

  .nav-link:not(.login-btn):not(.contact-btn) {
    display: none;
  }

  .hero {
    padding: 6rem 2rem 3rem;
  }

  .hero-title {
    font-size: 2.5rem;
  }

  .features-grid {
    grid-template-columns: 1fr;
  }

  .contact-info {
    flex-direction: column;
    gap: 1rem;
  }

  .footer-content {
    flex-direction: column;
    gap: 1rem;
    text-align: center;
  }
}
</style>
