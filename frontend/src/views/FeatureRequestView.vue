<template>
  <div class="catalog-container">
    <div class="catalog-header">
      <router-link to="/hub" class="back-link">&larr; Back to Hub</router-link>
      <h1>Feature Catalog</h1>
      <p class="catalog-subtitle">Browse all available features and request access</p>
    </div>

    <div v-if="loading" class="loading">Loading features...</div>

    <div v-else class="feature-grid">
      <div
        v-for="feature in catalog"
        :key="feature.feature_name"
        class="feature-card"
        :class="{ active: feature.has_access }"
      >
        <div class="card-icon">{{ feature.icon || '&#9889;' }}</div>
        <h2>{{ feature.display_name || feature.feature_name }}</h2>
        <p>{{ feature.description || 'No description available.' }}</p>

        <div class="card-footer">
          <!-- Has access: Active badge + link -->
          <router-link
            v-if="feature.has_access"
            :to="featureRoute(feature.feature_name)"
            class="badge badge-active"
          >
            Active &rarr;
          </router-link>

          <!-- Pending request -->
          <span v-else-if="feature.request_status === 'pending'" class="badge badge-pending">
            Pending Review
          </span>

          <!-- Rejected -->
          <span v-else-if="feature.request_status === 'rejected'" class="badge badge-rejected">
            Rejected
          </span>

          <!-- Requestable -->
          <button
            v-else-if="feature.requestable"
            class="btn-request"
            :disabled="requesting === feature.feature_name"
            @click="requestAccess(feature.feature_name)"
          >
            {{ requesting === feature.feature_name ? 'Requesting...' : 'Request Access' }}
          </button>

          <!-- Not requestable, no access -->
          <span v-else class="badge badge-soon">
            Coming Soon
          </span>
        </div>
      </div>
    </div>

    <div v-if="error" class="error-message">{{ error }}</div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '../api/client'

const catalog = ref([])
const loading = ref(true)
const requesting = ref(null)
const error = ref('')

const featureRoutes = {
  badminton: '/dashboard',
  pushup: '/challenges/pushup',
  squat: '/challenges',
  plank: '/challenges/plank',
  mimic: '/mimic',
}

function featureRoute(name) {
  return featureRoutes[name] || '/hub'
}

async function loadCatalog() {
  loading.value = true
  error.value = ''
  try {
    const res = await api.get('/api/v1/features/catalog')
    catalog.value = res.data
  } catch (err) {
    error.value = 'Failed to load features'
    console.error(err)
  } finally {
    loading.value = false
  }
}

async function requestAccess(featureName) {
  requesting.value = featureName
  error.value = ''
  try {
    await api.post('/api/v1/features/request', { feature_name: featureName })
    // Update local state to show pending
    const item = catalog.value.find(f => f.feature_name === featureName)
    if (item) item.request_status = 'pending'
  } catch (err) {
    const detail = err.response?.data?.detail
    if (detail) {
      error.value = detail
    } else {
      error.value = 'Failed to submit request'
    }
  } finally {
    requesting.value = null
  }
}

onMounted(loadCatalog)
</script>

<style scoped>
.catalog-container {
  max-width: 1000px;
  margin: 0 auto;
  padding: 2rem 1rem;
}

.catalog-header {
  text-align: center;
  margin-bottom: 2.5rem;
}

.back-link {
  display: inline-block;
  color: var(--text-muted);
  text-decoration: none;
  font-size: 0.9rem;
  margin-bottom: 1rem;
}

.back-link:hover {
  color: var(--text-primary);
}

.catalog-header h1 {
  color: var(--text-primary);
  font-size: 2rem;
  margin-bottom: 0.5rem;
}

.catalog-subtitle {
  color: var(--text-muted);
  font-size: 1.1rem;
}

.loading {
  text-align: center;
  color: var(--text-muted);
  padding: 3rem;
}

.feature-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 1.5rem;
}

.feature-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 2rem;
  display: flex;
  flex-direction: column;
  box-shadow: var(--shadow-md);
  transition: all 0.3s ease;
}

.feature-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-lg);
}

.feature-card.active {
  border-color: var(--color-success, #22c55e);
}

.card-icon {
  font-size: 2.5rem;
  margin-bottom: 1rem;
}

.feature-card h2 {
  color: var(--color-primary);
  font-size: 1.3rem;
  margin-bottom: 0.75rem;
}

.feature-card p {
  color: var(--text-secondary);
  font-size: 0.95rem;
  line-height: 1.5;
  flex: 1;
}

.card-footer {
  margin-top: 1.25rem;
}

.badge {
  display: inline-block;
  padding: 0.4rem 1rem;
  border-radius: var(--radius-lg);
  font-size: 0.85rem;
  font-weight: 600;
  text-decoration: none;
}

.badge-active {
  background: var(--color-success-light);
  color: var(--color-success);
}

.badge-active:hover {
  background: rgba(16, 185, 129, 0.25);
}

.badge-pending {
  background: var(--color-warning-light);
  color: var(--color-warning);
}

.badge-rejected {
  background: rgba(127, 127, 127, 0.15);
  color: var(--text-muted);
}

.badge-soon {
  background: rgba(127, 127, 127, 0.1);
  color: var(--text-muted);
}

.btn-request {
  padding: 0.5rem 1.25rem;
  border: none;
  border-radius: var(--radius-md);
  background: var(--color-primary);
  color: white;
  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s, opacity 0.2s;
}

.btn-request:hover:not(:disabled) {
  opacity: 0.9;
}

.btn-request:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.error-message {
  text-align: center;
  color: var(--color-destructive);
  margin-top: 1rem;
  padding: 0.75rem;
  background: var(--color-destructive-light);
  border-radius: var(--radius-md);
}
</style>
