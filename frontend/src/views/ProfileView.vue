<template>
  <div class="profile-container">
    <div class="profile-card">
      <div class="profile-header">
        <div class="profile-avatar">{{ userInitial }}</div>
        <div class="profile-info">
          <h1>{{ authStore.user?.username }}</h1>
          <p class="profile-email">{{ authStore.user?.email }}</p>
        </div>
      </div>

      <form @submit.prevent="handleSave">
        <div class="form-group">
          <label for="displayName">Display Name</label>
          <input
            id="displayName"
            v-model="displayName"
            type="text"
            placeholder="Your display name"
            maxlength="100"
            required
          />
        </div>

        <div class="form-group">
          <label for="mobile">Mobile Number</label>
          <input
            id="mobile"
            v-model="mobile"
            type="tel"
            placeholder="+91 9876543210"
            maxlength="20"
          />
        </div>

        <div class="form-group">
          <label>Email</label>
          <input :value="authStore.user?.email" type="email" disabled class="input-disabled" />
          <span class="field-hint">Email cannot be changed</span>
        </div>

        <div v-if="error" class="error-message">{{ error }}</div>
        <div v-if="success" class="success-message">{{ success }}</div>

        <button type="submit" class="btn-primary" :disabled="saving || !hasChanges">
          {{ saving ? 'Saving...' : 'Save Changes' }}
        </button>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '../stores/auth'

const authStore = useAuthStore()

const displayName = ref('')
const mobile = ref('')
const saving = ref(false)
const error = ref('')
const success = ref('')

const userInitial = computed(() =>
  (authStore.user?.username || authStore.user?.email || '?')[0].toUpperCase()
)

const hasChanges = computed(() => {
  const u = authStore.user
  if (!u) return false
  return displayName.value !== (u.username || '') || mobile.value !== (u.mobile || '')
})

onMounted(() => {
  if (authStore.user) {
    displayName.value = authStore.user.username || ''
    mobile.value = authStore.user.mobile || ''
  }
})

async function handleSave() {
  saving.value = true
  error.value = ''
  success.value = ''

  try {
    const data = {}
    if (displayName.value !== authStore.user.username) {
      data.username = displayName.value
    }
    if (mobile.value !== (authStore.user.mobile || '')) {
      data.mobile = mobile.value
    }
    await authStore.updateProfile(data)
    success.value = 'Profile updated!'
    setTimeout(() => { success.value = '' }, 3000)
  } catch (err) {
    error.value = err.response?.data?.detail || 'Failed to save changes.'
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.profile-container {
  display: flex;
  justify-content: center;
  padding-top: 1rem;
}

.profile-card {
  background: var(--bg-card);
  padding: 2.5rem;
  border-radius: var(--radius-lg);
  width: 100%;
  max-width: 480px;
  box-shadow: var(--shadow-lg);
  border: 1px solid var(--border-color);
}

.profile-header {
  display: flex;
  align-items: center;
  gap: 1.25rem;
  margin-bottom: 2rem;
  padding-bottom: 1.5rem;
  border-bottom: 1px solid var(--border-color);
}

.profile-avatar {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: var(--gradient-primary);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 1.4rem;
  flex-shrink: 0;
}

.profile-info h1 {
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
}

.profile-email {
  color: var(--text-muted);
  font-size: 0.9rem;
  margin: 0.25rem 0 0;
}

.form-group {
  margin-bottom: 1.25rem;
}

label {
  display: block;
  margin-bottom: 0.5rem;
  color: var(--text-secondary);
  font-weight: 500;
  font-size: 0.9rem;
}

input {
  width: 100%;
  padding: 0.75rem 1rem;
  border: 2px solid var(--border-input);
  border-radius: var(--radius-md);
  background: var(--bg-input);
  color: var(--text-primary);
  font-size: 1rem;
  transition: border-color 0.2s;
}

input:focus {
  outline: none;
  border-color: var(--color-primary);
}

.input-disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.field-hint {
  display: block;
  margin-top: 0.25rem;
  color: var(--text-muted);
  font-size: 0.8rem;
}

.btn-primary {
  width: 100%;
  padding: 0.85rem;
  background: var(--gradient-primary);
  color: var(--text-on-primary);
  border: none;
  border-radius: var(--radius-md);
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.2s;
  margin-top: 0.5rem;
}

.btn-primary:hover:not(:disabled) {
  opacity: 0.9;
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.error-message {
  background: var(--color-destructive-light);
  color: var(--color-destructive);
  padding: 0.75rem 1rem;
  border-radius: var(--radius-md);
  margin-bottom: 1rem;
  font-size: 0.9rem;
}

.success-message {
  background: var(--color-success-light);
  color: var(--color-success);
  padding: 0.75rem 1rem;
  border-radius: var(--radius-md);
  margin-bottom: 1rem;
  font-size: 0.9rem;
}

@media (max-width: 640px) {
  .profile-card {
    padding: 1.5rem;
  }
}
</style>
