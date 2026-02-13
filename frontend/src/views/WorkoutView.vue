<template>
  <div class="workout-placeholder">
    <router-link to="/hub" class="back-link">&larr; Back to Hub</router-link>
    <div class="placeholder-card">
      <div class="icon">&#127947;</div>
      <h1>Workout with Me</h1>
      <p>Follow guided workout routines with real-time form feedback and rep counting.</p>
      <span class="badge">Coming Soon</span>
    </div>
  </div>
</template>

<style scoped>
.workout-placeholder {
  max-width: 600px;
  margin: 0 auto;
  padding: 1rem;
}

.back-link {
  color: var(--text-muted);
  text-decoration: none;
  font-size: 0.9rem;
}
.back-link:hover { color: var(--color-primary); }

.placeholder-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 4rem 2rem;
  text-align: center;
  margin-top: 2rem;
  box-shadow: var(--shadow-md);
}

.icon {
  font-size: 4rem;
  margin-bottom: 1rem;
}

.placeholder-card h1 {
  color: var(--text-primary);
  margin-bottom: 0.75rem;
}

.placeholder-card p {
  color: var(--text-muted);
  max-width: 400px;
  margin: 0 auto 1.5rem;
  line-height: 1.5;
}

.badge {
  display: inline-block;
  background: var(--color-primary-light);
  color: var(--color-primary);
  padding: 0.4rem 1.25rem;
  border-radius: 20px;
  font-size: 0.9rem;
  font-weight: 600;
}
</style>
