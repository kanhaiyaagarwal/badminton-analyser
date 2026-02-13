<template>
  <div class="landing-simple">
    <div class="landing-card">
      <div class="brand">
        <span class="brand-icon">🏸</span>
        <span class="brand-name">vision.neymo.ai</span>
      </div>
      <p class="tagline">AI-powered motion analysis for athletes</p>
      <div class="actions">
        <button class="btn-primary" @click="$router.push('/login')">Login</button>
        <button class="btn-secondary" @click="$router.push('/signup')">Sign Up</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.landing-simple {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1rem;
}

.landing-card {
  text-align: center;
  max-width: 360px;
  width: 100%;
}

.brand {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
}

.brand-icon {
  font-size: 2.5rem;
}

.brand-name {
  font-size: 1.8rem;
  font-weight: 800;
  background: linear-gradient(135deg, #4ecca3, #45b7aa);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.tagline {
  color: #888;
  font-size: 1rem;
  margin-bottom: 2.5rem;
}

.actions {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.btn-primary {
  width: 100%;
  padding: 1rem;
  background: linear-gradient(135deg, #4ecca3, #45b7aa);
  color: #0a0a1a;
  border: none;
  border-radius: 12px;
  font-size: 1.1rem;
  font-weight: 700;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
}

.btn-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 24px rgba(78, 204, 163, 0.4);
}

.btn-secondary {
  width: 100%;
  padding: 1rem;
  background: transparent;
  color: #fff;
  border: 2px solid rgba(78, 204, 163, 0.4);
  border-radius: 12px;
  font-size: 1.1rem;
  font-weight: 600;
  cursor: pointer;
  transition: border-color 0.2s, background 0.2s;
}

.btn-secondary:hover {
  border-color: #4ecca3;
  background: rgba(78, 204, 163, 0.1);
}
</style>
