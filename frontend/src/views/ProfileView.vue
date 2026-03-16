<template>
  <div class="profile-page">
    <!-- Header -->
    <header class="profile-top">
      <h1 class="profile-heading font-display">Me</h1>
      <button class="settings-btn" @click="showSettings = !showSettings">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="20" height="20">
          <circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
        </svg>
      </button>
    </header>

    <!-- User Info Card -->
    <section class="user-section">
      <div
        v-motion
        :initial="{ opacity: 0, y: 20 }"
        :enter="{ opacity: 1, y: 0, transition: { duration: 400 } }"
        class="user-card glass"
      >
        <div class="user-info-row">
          <div class="user-avatar">
            <span class="avatar-emoji">💪</span>
          </div>
          <div class="user-details">
            <h2 class="user-name font-display">{{ authStore.user?.username || 'User' }}</h2>
            <p class="user-meta">
              {{ workoutProfile?.fitness_level ? capitalize(workoutProfile.fitness_level) : 'Beginner' }}
              <template v-if="memberSince"> • {{ memberSince }}</template>
            </p>
          </div>
        </div>

        <!-- Stats Grid -->
        <div class="profile-stats">
          <div
            v-for="(stat, i) in profileStats"
            :key="stat.label"
            v-motion
            :initial="{ opacity: 0, scale: 0.9 }"
            :enter="{ opacity: 1, scale: 1, transition: { delay: 100 + i * 50 } }"
            class="profile-stat"
          >
            <span class="profile-stat-value gradient-text">{{ stat.value }}</span>
            <span class="profile-stat-label">{{ stat.label }}</span>
          </div>
        </div>
      </div>
    </section>

    <!-- Menu Items -->
    <section class="menu-section">
      <button
        v-for="(item, i) in menuItems"
        :key="item.label"
        v-motion
        :initial="{ opacity: 0, x: -20 }"
        :enter="{ opacity: 1, x: 0, transition: { delay: 200 + i * 50 } }"
        class="menu-item glass"
        @click="handleMenuItem(item)"
      >
        <div class="menu-icon-wrap">
          <span class="menu-emoji">{{ item.icon }}</span>
        </div>
        <span class="menu-label font-display">{{ item.label }}</span>
        <svg class="menu-chevron" viewBox="0 0 20 20" fill="none" width="20" height="20">
          <path d="M7.5 15L12.5 10L7.5 5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </button>
    </section>

    <!-- Settings panel (inline, replaces old edit rows) -->
    <section v-if="showSettings" class="settings-panel">
      <h2 class="section-label">Account</h2>
      <div class="settings-group glass">
        <div class="setting-row">
          <span class="setting-label">Name</span>
          <template v-if="editing === 'name'">
            <input ref="nameInput" v-model="editName" class="setting-input" @keydown.enter="saveName" @keydown.escape="cancelEdit" />
            <button class="setting-action save" @click="saveName" :disabled="saving">✓</button>
            <button class="setting-action cancel" @click="cancelEdit">✕</button>
          </template>
          <template v-else>
            <span class="setting-value">{{ authStore.user?.username || '—' }}</span>
            <button class="setting-action edit" @click="startEdit('name')">Edit</button>
          </template>
        </div>
        <div class="setting-row">
          <span class="setting-label">Phone</span>
          <template v-if="editing === 'phone'">
            <input ref="phoneInput" v-model="editPhone" class="setting-input" type="tel" @keydown.enter="savePhone" @keydown.escape="cancelEdit" />
            <button class="setting-action save" @click="savePhone" :disabled="saving">✓</button>
            <button class="setting-action cancel" @click="cancelEdit">✕</button>
          </template>
          <template v-else>
            <span class="setting-value">{{ authStore.user?.mobile || '—' }}</span>
            <button class="setting-action edit" @click="startEdit('phone')">Edit</button>
          </template>
        </div>
        <div class="setting-row">
          <span class="setting-label">Email</span>
          <span class="setting-value muted">{{ authStore.user?.email || '—' }}</span>
        </div>
      </div>

      <div v-if="authStore.hasFeature('workout')" class="danger-row">
        <button @click="handleResetWorkout" class="btn-danger-sm" :disabled="resetting">
          {{ resetting ? '...' : 'Reset Workout Data' }}
        </button>
      </div>

      <button @click="handleLogout" class="btn-logout">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16" stroke-linecap="round" stroke-linejoin="round">
          <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/>
        </svg>
        Log Out
      </button>
    </section>

    <!-- Feedback -->
    <div v-if="error" class="toast error">{{ error }}</div>
    <div v-if="success" class="toast success">{{ success }}</div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useWorkoutStore } from '../stores/workout'
import api from '../api/client'

const router = useRouter()
const authStore = useAuthStore()
const workoutStore = useWorkoutStore()

const showSettings = ref(false)
const editing = ref(null)
const editName = ref('')
const editPhone = ref('')
const saving = ref(false)
const resetting = ref(false)
const error = ref('')
const success = ref('')
const nameInput = ref(null)
const phoneInput = ref(null)
const workoutProfile = ref(null)
const progressStats = ref(null)

function capitalize(s) { return s ? s.charAt(0).toUpperCase() + s.slice(1) : '' }

const memberSince = computed(() => {
  if (!authStore.user?.created_at) return ''
  const months = Math.floor((Date.now() - new Date(authStore.user.created_at).getTime()) / (30 * 24 * 60 * 60 * 1000))
  if (months < 1) return 'New member'
  return months === 1 ? '1 month' : `${months} months`
})

const profileStats = computed(() => [
  { value: progressStats.value?.total_workouts || 0, label: 'Workouts' },
  { value: progressStats.value?.total_prs || 0, label: 'PRs' },
  { value: (progressStats.value?.current_streak || 0) + 'd', label: 'Streak' },
])

const menuItems = [
  { label: 'Workout History', icon: '📊', action: 'history' },
  { label: 'Body Measurements', icon: '📏', action: 'measurements' },
  { label: 'Goals & Progress', icon: '🎯', action: 'goals' },
  { label: 'Settings', icon: '⚙️', action: 'settings' },
]

function handleMenuItem(item) {
  if (item.action === 'settings') {
    showSettings.value = !showSettings.value
  }
  // Other items can be routed later
}

function startEdit(field) {
  editing.value = field
  if (field === 'name') {
    editName.value = authStore.user?.username || ''
    nextTick(() => nameInput.value?.focus())
  } else if (field === 'phone') {
    editPhone.value = authStore.user?.mobile || ''
    nextTick(() => phoneInput.value?.focus())
  }
}

function cancelEdit() { editing.value = null }

async function saveName() {
  if (!editName.value.trim()) return
  saving.value = true; error.value = ''
  try {
    await authStore.updateProfile({ username: editName.value.trim() })
    editing.value = null; flashSuccess('Name updated')
  } catch (err) { error.value = err.response?.data?.detail || 'Failed to save' }
  finally { saving.value = false }
}

async function savePhone() {
  saving.value = true; error.value = ''
  try {
    await authStore.updateProfile({ mobile: editPhone.value.trim() })
    editing.value = null; flashSuccess('Phone updated')
  } catch (err) { error.value = err.response?.data?.detail || 'Failed to save' }
  finally { saving.value = false }
}

function flashSuccess(msg) { success.value = msg; setTimeout(() => { success.value = '' }, 2000) }

async function handleResetWorkout() {
  if (!confirm('Reset all workout data?')) return
  resetting.value = true; error.value = ''
  try {
    await api.delete('/api/v1/workout/profile/reset')
    flashSuccess('Workout data reset!')
    setTimeout(() => router.push('/workout/onboarding'), 500)
  } catch (err) { error.value = err.response?.data?.detail || 'Failed to reset.' }
  finally { resetting.value = false }
}

function handleLogout() { authStore.logout(); router.push('/') }

onMounted(async () => {
  if (authStore.hasFeature('workout')) {
    try {
      const data = await workoutStore.fetchProfile()
      if (data?.onboarding_completed) workoutProfile.value = data
      const stats = await workoutStore.fetchProgressStats()
      if (stats) progressStats.value = stats
    } catch { /* Not critical */ }
  }
})
</script>

<style scoped>
.profile-page {
  padding-bottom: 2rem;
}

/* Header */
.profile-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 2.5rem 1.5rem 1.5rem;
}

.profile-heading {
  font-size: 1.75rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: -0.02em;
  color: var(--text-primary);
}

.settings-btn {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: var(--bg-card);
  border: none;
  color: var(--text-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

/* User card */
.user-section {
  padding: 0 1.5rem;
  margin-bottom: 1rem;
}

.user-card {
  padding: 1.5rem;
  border-radius: 1rem;
}

.user-info-row {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.user-avatar {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background: var(--gradient-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.avatar-emoji {
  font-size: 2.5rem;
}

.user-name {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 0.15rem;
}

.user-meta {
  font-size: 0.875rem;
  color: var(--text-muted);
}

.profile-stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.75rem;
}

.profile-stat {
  text-align: center;
}

.profile-stat-value {
  display: block;
  font-family: var(--font-display);
  font-size: 1.5rem;
  font-weight: 900;
  margin-bottom: 0.1rem;
}

.gradient-text {
  background: linear-gradient(135deg, hsl(18 95% 55%), hsl(18 95% 65%));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.profile-stat-label {
  font-size: 0.65rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

/* Menu items */
.menu-section {
  padding: 0 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.menu-item {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1.25rem;
  border-radius: 1rem;
  cursor: pointer;
  text-align: left;
  transition: transform 0.15s, border-color 0.2s;
}

.menu-item:hover {
  border-color: var(--color-secondary);
}

.menu-item:active {
  transform: scale(0.98);
}

.menu-icon-wrap {
  width: 48px;
  height: 48px;
  border-radius: 0.75rem;
  background: linear-gradient(135deg, rgba(242, 101, 34, 0.15), rgba(242, 101, 34, 0.05));
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.menu-emoji {
  font-size: 1.5rem;
}

.menu-label {
  flex: 1;
  font-weight: 700;
  font-size: 0.95rem;
  color: var(--text-primary);
}

.menu-chevron {
  color: var(--text-muted);
  flex-shrink: 0;
}

/* Settings panel */
.settings-panel {
  padding: 1.5rem;
  margin-top: 1rem;
}

.section-label {
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-muted);
  margin-bottom: 0.5rem;
}

.settings-group {
  border-radius: 0.75rem;
  overflow: hidden;
  margin-bottom: 1rem;
}

.setting-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.65rem 0.75rem;
}

.setting-row + .setting-row {
  border-top: 1px solid var(--border-color);
}

.setting-label {
  width: 55px;
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--text-muted);
  flex-shrink: 0;
}

.setting-value {
  flex: 1;
  font-size: 0.85rem;
  color: var(--text-primary);
  text-align: right;
}

.setting-value.muted { color: var(--text-muted); }

.setting-input {
  flex: 1;
  padding: 0.3rem 0.5rem;
  border: 1px solid var(--border-input-focus);
  border-radius: var(--radius-sm);
  background: var(--bg-input);
  font-size: 0.85rem;
  color: var(--text-primary);
  outline: none;
  text-align: right;
}

.setting-action {
  padding: 0.25rem 0.5rem;
  border-radius: var(--radius-sm);
  border: none;
  font-size: 0.75rem;
  font-weight: 600;
  cursor: pointer;
}

.setting-action.edit {
  background: transparent;
  color: var(--color-primary);
}

.setting-action.save {
  background: var(--color-primary);
  color: var(--text-on-primary);
}

.setting-action.cancel {
  background: transparent;
  color: var(--text-muted);
}

.danger-row {
  margin-bottom: 0.75rem;
}

.btn-danger-sm {
  padding: 0.5rem 1rem;
  background: transparent;
  border: 1px solid var(--color-destructive);
  color: var(--color-destructive);
  border-radius: var(--radius-full);
  font-size: 0.8rem;
  font-weight: 600;
  cursor: pointer;
}

.btn-logout {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.4rem;
  padding: 0.7rem;
  background: transparent;
  border: 1.5px solid var(--color-destructive);
  color: var(--color-destructive);
  border-radius: var(--radius-md);
  font-size: 0.85rem;
  font-weight: 600;
  font-family: inherit;
  cursor: pointer;
}

/* Toast */
.toast {
  position: fixed;
  bottom: 5rem;
  left: 50%;
  transform: translateX(-50%);
  padding: 0.5rem 1rem;
  border-radius: var(--radius-full);
  font-size: 0.8rem;
  z-index: 100;
}

.toast.error {
  background: var(--color-destructive-light);
  color: var(--color-destructive);
}

.toast.success {
  background: var(--color-success-light);
  color: var(--color-success);
}
</style>
