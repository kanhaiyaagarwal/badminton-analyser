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
  color: #888;
  text-decoration: none;
  font-size: 0.9rem;
}
.back-link:hover { color: #4ecca3; }

.placeholder-card {
  background: rgba(22, 33, 62, 0.8);
  border: 1px solid rgba(78, 204, 163, 0.15);
  border-radius: 12px;
  padding: 4rem 2rem;
  text-align: center;
  margin-top: 2rem;
}

.icon {
  font-size: 4rem;
  margin-bottom: 1rem;
}

.placeholder-card h1 {
  color: #eee;
  margin-bottom: 0.75rem;
}

.placeholder-card p {
  color: #888;
  max-width: 400px;
  margin: 0 auto 1.5rem;
  line-height: 1.5;
}

.badge {
  display: inline-block;
  background: rgba(78, 204, 163, 0.15);
  color: #4ecca3;
  padding: 0.4rem 1.25rem;
  border-radius: 20px;
  font-size: 0.9rem;
  font-weight: 500;
}
</style>
