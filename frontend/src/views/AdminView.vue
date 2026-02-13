<template>
  <div class="admin-view">
    <div class="header">
      <div class="header-nav">
        <router-link to="/dashboard" class="back-link">Back to Dashboard</router-link>
        <router-link to="/tuning" class="tuning-link">Tuning Dashboard</router-link>
      </div>
      <h1>Admin Panel</h1>
    </div>

    <div v-if="!isAdmin" class="not-admin">
      <p>You don't have admin access.</p>
    </div>

    <template v-else>
      <!-- Tabs -->
      <div class="tabs">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          :class="['tab', { active: activeTab === tab.id }]"
          @click="activeTab = tab.id"
        >
          {{ tab.label }}
        </button>
      </div>

      <!-- Invite Codes Tab -->
      <div v-if="activeTab === 'codes'" class="tab-content">
        <div class="section-header">
          <h2>Invite Codes</h2>
          <button @click="showCreateCode = true" class="btn-primary">
            + New Code
          </button>
        </div>

        <div v-if="loadingCodes" class="loading">Loading...</div>

        <table v-else class="data-table">
          <thead>
            <tr>
              <th>Code</th>
              <th>Uses</th>
              <th>Note</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="code in inviteCodes" :key="code.id">
              <td class="code-cell">{{ code.code }}</td>
              <td>{{ code.times_used }} / {{ code.max_uses || '∞' }}</td>
              <td>{{ code.note || '-' }}</td>
              <td>
                <span :class="['status', code.is_active ? 'active' : 'inactive']">
                  {{ code.is_active ? 'Active' : 'Inactive' }}
                </span>
              </td>
              <td class="actions">
                <button @click="toggleCode(code)" class="btn-small">
                  {{ code.is_active ? 'Disable' : 'Enable' }}
                </button>
                <button @click="deleteCode(code)" class="btn-small btn-danger">
                  Delete
                </button>
              </td>
            </tr>
            <tr v-if="inviteCodes.length === 0">
              <td colspan="5" class="empty">No invite codes yet</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Whitelist Tab -->
      <div v-if="activeTab === 'whitelist'" class="tab-content">
        <div class="section-header">
          <h2>Whitelisted Emails</h2>
          <button @click="showAddWhitelist = true" class="btn-primary">
            + Add Email
          </button>
        </div>

        <p class="whitelist-desc">
          Whitelisted emails can sign up without an invite code.
        </p>

        <div v-if="loadingWhitelist" class="loading">Loading...</div>

        <table v-else class="data-table">
          <thead>
            <tr>
              <th>Email</th>
              <th>Note</th>
              <th>Added</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="entry in whitelist" :key="entry.id">
              <td>{{ entry.email }}</td>
              <td>{{ entry.note || '-' }}</td>
              <td>{{ formatDate(entry.created_at) }}</td>
              <td class="actions">
                <button @click="deleteWhitelistEmail(entry)" class="btn-small btn-danger">
                  Remove
                </button>
              </td>
            </tr>
            <tr v-if="whitelist.length === 0">
              <td colspan="4" class="empty">No whitelisted emails</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Waitlist Tab -->
      <div v-if="activeTab === 'waitlist'" class="tab-content">
        <div class="section-header">
          <h2>Waitlist</h2>
          <select v-model="waitlistFilter" @change="loadWaitlist">
            <option value="">All</option>
            <option value="pending">Pending</option>
            <option value="approved">Approved</option>
            <option value="registered">Registered</option>
            <option value="rejected">Rejected</option>
          </select>
        </div>

        <div v-if="loadingWaitlist" class="loading">Loading...</div>

        <table v-else class="data-table">
          <thead>
            <tr>
              <th>Email</th>
              <th>Name</th>
              <th>Status</th>
              <th>Date</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="entry in waitlist" :key="entry.id">
              <td>{{ entry.email }}</td>
              <td>{{ entry.name || '-' }}</td>
              <td>
                <span :class="['status', entry.status]">{{ entry.status }}</span>
              </td>
              <td>{{ formatDate(entry.created_at) }}</td>
              <td class="actions">
                <template v-if="entry.status === 'pending'">
                  <button @click="approveEntry(entry)" class="btn-small btn-success">
                    Approve
                  </button>
                  <button @click="rejectEntry(entry)" class="btn-small btn-danger">
                    Reject
                  </button>
                </template>
                <button @click="deleteEntry(entry)" class="btn-small">Delete</button>
              </td>
            </tr>
            <tr v-if="waitlist.length === 0">
              <td colspan="5" class="empty">No waitlist entries</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Users Tab -->
      <div v-if="activeTab === 'users'" class="tab-content">
        <h2>Users</h2>

        <div v-if="loadingUsers" class="loading">Loading...</div>

        <table v-else class="data-table">
          <thead>
            <tr>
              <th>Email</th>
              <th>Username</th>
              <th>Admin</th>
              <th>Created</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="user in users" :key="user.id">
              <td>{{ user.email }}</td>
              <td>{{ user.username }}</td>
              <td>
                <span :class="['status', user.is_admin ? 'active' : '']">
                  {{ user.is_admin ? 'Yes' : 'No' }}
                </span>
              </td>
              <td>{{ formatDate(user.created_at) }}</td>
              <td class="actions">
                <button
                  @click="toggleAdmin(user)"
                  class="btn-small"
                  :disabled="user.id === currentUser?.id"
                >
                  {{ user.is_admin ? 'Remove Admin' : 'Make Admin' }}
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Challenges Tab -->
      <div v-if="activeTab === 'challenges'" class="tab-content">
        <!-- Sessions Browser -->
        <div class="section-header">
          <h2>Challenge Sessions</h2>
          <select v-model="challengeTypeFilter" @change="loadChallengeSessions">
            <option value="">All Types</option>
            <option value="plank">Plank</option>
            <option value="squat">Squat</option>
            <option value="pushup">Pushup</option>
          </select>
        </div>

        <div v-if="loadingSessions" class="loading">Loading...</div>

        <table v-else class="data-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>User</th>
              <th>Type</th>
              <th>Score</th>
              <th>Duration</th>
              <th>Date</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="s in challengeSessions" :key="s.id">
              <td>{{ s.id }}</td>
              <td>{{ s.username }}</td>
              <td>{{ s.challenge_type }}</td>
              <td>{{ s.score }}</td>
              <td>{{ s.duration_seconds.toFixed(1) }}s</td>
              <td>{{ formatDate(s.created_at) }}</td>
              <td>
                <span :class="['status', s.status === 'ended' ? 'active' : 'pending']">
                  {{ s.status }}
                </span>
              </td>
              <td class="actions">
                <button
                  v-if="s.has_pose_data"
                  @click="downloadPoseData(s.id)"
                  class="btn-small btn-success"
                >
                  Download Pose Data
                </button>
                <span v-else class="no-data">No pose data</span>
              </td>
            </tr>
            <tr v-if="challengeSessions.length === 0">
              <td colspan="8" class="empty">No challenge sessions found</td>
            </tr>
          </tbody>
        </table>

        <!-- Tolerance Config -->
        <h2 class="config-heading">Tolerance Config</h2>

        <div v-if="loadingConfig" class="loading">Loading...</div>

        <div v-else class="config-grid">
          <div v-for="(cfg, ctype) in challengeConfig" :key="ctype" class="config-card">
            <div class="config-card-header">
              <h3>{{ ctype }}</h3>
              <button
                :class="['enabled-pill', cfg.enabled ? 'enabled' : 'disabled']"
                @click="toggleChallengeEnabled(ctype)"
              >
                {{ cfg.enabled ? 'Enabled' : 'Disabled' }}
              </button>
            </div>
            <div v-for="(val, key) in cfg.thresholds" :key="key" class="config-field">
              <label>{{ formatThresholdLabel(key) }}</label>
              <input
                type="number"
                v-model.number="cfg.thresholds[key]"
                step="1"
              />
            </div>
            <div class="config-actions">
              <button @click="saveChallengeConfig(ctype)" class="btn-primary btn-sm">
                Save
              </button>
              <button
                v-if="cfg.is_custom"
                @click="resetChallengeConfig(ctype)"
                class="btn-small"
              >
                Reset to Default
              </button>
            </div>
            <div v-if="cfg.updated_at" class="config-meta">
              Updated: {{ formatDate(cfg.updated_at) }}
            </div>
          </div>
        </div>
      </div>

      <!-- Create Code Modal -->
      <div v-if="showCreateCode" class="modal-overlay" @click="showCreateCode = false">
        <div class="modal-content" @click.stop>
          <h2>Create Invite Code</h2>

          <form @submit.prevent="createCode">
            <div class="form-group">
              <label>Code (leave empty to auto-generate)</label>
              <input v-model="newCode.code" type="text" placeholder="e.g., MYCODE123" />
            </div>

            <div class="form-group">
              <label>Max Uses (0 = unlimited)</label>
              <input v-model.number="newCode.max_uses" type="number" min="0" />
            </div>

            <div class="form-group">
              <label>Note (optional)</label>
              <input v-model="newCode.note" type="text" placeholder="Who is this for?" />
            </div>

            <div v-if="createError" class="error-message">{{ createError }}</div>

            <button type="submit" class="btn-primary" :disabled="creating">
              {{ creating ? 'Creating...' : 'Create Code' }}
            </button>
            <button type="button" @click="showCreateCode = false" class="btn-secondary">
              Cancel
            </button>
          </form>
        </div>
      </div>

      <!-- Add Whitelist Email Modal -->
      <div v-if="showAddWhitelist" class="modal-overlay" @click="showAddWhitelist = false">
        <div class="modal-content" @click.stop>
          <h2>Add Whitelisted Email</h2>

          <form @submit.prevent="addWhitelistEmail">
            <div class="form-group">
              <label>Email Address</label>
              <input v-model="newWhitelist.email" type="email" placeholder="user@example.com" required />
            </div>

            <div class="form-group">
              <label>Note (optional)</label>
              <input v-model="newWhitelist.note" type="text" placeholder="Who is this for?" />
            </div>

            <div v-if="addWhitelistError" class="error-message">{{ addWhitelistError }}</div>

            <button type="submit" class="btn-primary" :disabled="addingWhitelist">
              {{ addingWhitelist ? 'Adding...' : 'Add Email' }}
            </button>
            <button type="button" @click="showAddWhitelist = false" class="btn-secondary">
              Cancel
            </button>
          </form>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useAuthStore } from '../stores/auth'
import api from '../api/client'

const authStore = useAuthStore()
const currentUser = computed(() => authStore.user)
const isAdmin = computed(() => authStore.user?.is_admin)

const tabs = [
  { id: 'codes', label: 'Invite Codes' },
  { id: 'whitelist', label: 'Whitelist' },
  { id: 'waitlist', label: 'Waitlist' },
  { id: 'users', label: 'Users' },
  { id: 'challenges', label: 'Challenges' }
]
const activeTab = ref('codes')

// Invite Codes
const inviteCodes = ref([])
const loadingCodes = ref(false)
const showCreateCode = ref(false)
const newCode = ref({ code: '', max_uses: 1, note: '' })
const creating = ref(false)
const createError = ref('')

// Whitelist
const whitelist = ref([])
const loadingWhitelist = ref(false)
const showAddWhitelist = ref(false)
const newWhitelist = ref({ email: '', note: '' })
const addingWhitelist = ref(false)
const addWhitelistError = ref('')

// Waitlist
const waitlist = ref([])
const loadingWaitlist = ref(false)
const waitlistFilter = ref('')

// Users
const users = ref([])
const loadingUsers = ref(false)

// Challenges
const challengeSessions = ref([])
const loadingSessions = ref(false)
const challengeTypeFilter = ref('')
const challengeConfig = ref({})
const loadingConfig = ref(false)

onMounted(async () => {
  if (isAdmin.value) {
    await Promise.all([loadCodes(), loadWhitelist(), loadWaitlist(), loadUsers()])
  }
})

watch(activeTab, (tab) => {
  if (tab === 'challenges' && challengeSessions.value.length === 0) {
    loadChallengeSessions()
    loadChallengeConfig()
  }
})

async function loadCodes() {
  loadingCodes.value = true
  try {
    const response = await api.get('/api/v1/admin/invite-codes')
    inviteCodes.value = response.data
  } catch (err) {
    console.error('Failed to load codes:', err)
  } finally {
    loadingCodes.value = false
  }
}

async function loadWhitelist() {
  loadingWhitelist.value = true
  try {
    const response = await api.get('/api/v1/admin/whitelist')
    whitelist.value = response.data
  } catch (err) {
    console.error('Failed to load whitelist:', err)
  } finally {
    loadingWhitelist.value = false
  }
}

async function addWhitelistEmail() {
  addingWhitelist.value = true
  addWhitelistError.value = ''
  try {
    await api.post('/api/v1/admin/whitelist', newWhitelist.value)
    showAddWhitelist.value = false
    newWhitelist.value = { email: '', note: '' }
    await loadWhitelist()
  } catch (err) {
    addWhitelistError.value = err.response?.data?.detail || 'Failed to add email'
  } finally {
    addingWhitelist.value = false
  }
}

async function deleteWhitelistEmail(entry) {
  if (!confirm(`Remove "${entry.email}" from whitelist?`)) return
  try {
    await api.delete(`/api/v1/admin/whitelist/${entry.id}`)
    await loadWhitelist()
  } catch (err) {
    console.error('Failed to delete whitelist entry:', err)
  }
}

async function loadWaitlist() {
  loadingWaitlist.value = true
  try {
    const params = waitlistFilter.value ? { status_filter: waitlistFilter.value } : {}
    const response = await api.get('/api/v1/admin/waitlist', { params })
    waitlist.value = response.data
  } catch (err) {
    console.error('Failed to load waitlist:', err)
  } finally {
    loadingWaitlist.value = false
  }
}

async function loadUsers() {
  loadingUsers.value = true
  try {
    const response = await api.get('/api/v1/admin/users')
    users.value = response.data
  } catch (err) {
    console.error('Failed to load users:', err)
  } finally {
    loadingUsers.value = false
  }
}

async function createCode() {
  creating.value = true
  createError.value = ''
  try {
    await api.post('/api/v1/admin/invite-codes', newCode.value)
    showCreateCode.value = false
    newCode.value = { code: '', max_uses: 1, note: '' }
    await loadCodes()
  } catch (err) {
    createError.value = err.response?.data?.detail || 'Failed to create code'
  } finally {
    creating.value = false
  }
}

async function toggleCode(code) {
  try {
    await api.patch(`/api/v1/admin/invite-codes/${code.id}/toggle`)
    await loadCodes()
  } catch (err) {
    console.error('Failed to toggle code:', err)
  }
}

async function deleteCode(code) {
  if (!confirm(`Delete invite code "${code.code}"?`)) return
  try {
    await api.delete(`/api/v1/admin/invite-codes/${code.id}`)
    await loadCodes()
  } catch (err) {
    console.error('Failed to delete code:', err)
  }
}

async function approveEntry(entry) {
  try {
    const response = await api.post(`/api/v1/admin/waitlist/${entry.id}/approve`)
    alert(`Approved! Invite code: ${response.data.invite_code}`)
    await loadWaitlist()
    await loadCodes()
  } catch (err) {
    console.error('Failed to approve:', err)
  }
}

async function rejectEntry(entry) {
  try {
    await api.post(`/api/v1/admin/waitlist/${entry.id}/reject`)
    await loadWaitlist()
  } catch (err) {
    console.error('Failed to reject:', err)
  }
}

async function deleteEntry(entry) {
  if (!confirm(`Delete waitlist entry for "${entry.email}"?`)) return
  try {
    await api.delete(`/api/v1/admin/waitlist/${entry.id}`)
    await loadWaitlist()
  } catch (err) {
    console.error('Failed to delete:', err)
  }
}

async function toggleAdmin(user) {
  try {
    await api.patch(`/api/v1/admin/users/${user.id}/toggle-admin`)
    await loadUsers()
  } catch (err) {
    console.error('Failed to toggle admin:', err)
  }
}

// ---------- Challenges ----------

async function loadChallengeSessions() {
  loadingSessions.value = true
  try {
    const params = challengeTypeFilter.value ? { challenge_type: challengeTypeFilter.value } : {}
    const response = await api.get('/api/v1/challenges/admin/sessions', { params })
    challengeSessions.value = response.data
  } catch (err) {
    console.error('Failed to load challenge sessions:', err)
  } finally {
    loadingSessions.value = false
  }
}

async function loadChallengeConfig() {
  loadingConfig.value = true
  try {
    const response = await api.get('/api/v1/challenges/admin/config')
    challengeConfig.value = response.data
  } catch (err) {
    console.error('Failed to load challenge config:', err)
  } finally {
    loadingConfig.value = false
  }
}

async function saveChallengeConfig(ctype) {
  try {
    await api.put(`/api/v1/challenges/admin/config/${ctype}`, {
      thresholds: challengeConfig.value[ctype].thresholds
    })
    await loadChallengeConfig()
  } catch (err) {
    console.error('Failed to save challenge config:', err)
  }
}

async function resetChallengeConfig(ctype) {
  if (!confirm(`Reset ${ctype} thresholds to defaults?`)) return
  try {
    await api.post(`/api/v1/challenges/admin/config/${ctype}/reset`)
    await loadChallengeConfig()
  } catch (err) {
    console.error('Failed to reset challenge config:', err)
  }
}

async function toggleChallengeEnabled(ctype) {
  try {
    await api.patch(`/api/v1/challenges/admin/config/${ctype}/toggle-enabled`)
    await loadChallengeConfig()
  } catch (err) {
    console.error('Failed to toggle challenge enabled:', err)
  }
}

async function downloadPoseData(sessionId) {
  try {
    const response = await api.get(`/api/v1/challenges/admin/sessions/${sessionId}/pose-data`)
    const blob = new Blob([JSON.stringify(response.data, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `pose_data_${sessionId}.json`
    a.click()
    URL.revokeObjectURL(url)
  } catch (err) {
    console.error('Failed to download pose data:', err)
  }
}

function formatThresholdLabel(key) {
  return key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()) + ' (\u00b0)'
}

function formatDate(dateStr) {
  return new Date(dateStr).toLocaleDateString()
}
</script>

<style scoped>
.admin-view {
  max-width: 1200px;
  margin: 0 auto;
  padding: 1rem;
}

.header {
  margin-bottom: 2rem;
}

.header-nav {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.back-link {
  color: #888;
  text-decoration: none;
  font-size: 0.9rem;
}

.tuning-link {
  color: #4ecca3;
  text-decoration: none;
  font-size: 0.9rem;
  padding: 0.5rem 1rem;
  background: rgba(78, 204, 163, 0.1);
  border-radius: 6px;
  transition: background 0.2s;
}

.tuning-link:hover {
  background: rgba(78, 204, 163, 0.2);
}

h1 {
  color: #4ecca3;
  margin-top: 0.5rem;
}

.not-admin {
  text-align: center;
  padding: 3rem;
  color: #888;
}

.tabs {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1.5rem;
  border-bottom: 1px solid #2a2a4a;
  padding-bottom: 0.5rem;
}

.tab {
  padding: 0.75rem 1.5rem;
  background: transparent;
  border: none;
  color: #888;
  cursor: pointer;
  border-radius: 8px 8px 0 0;
  transition: all 0.2s;
}

.tab:hover {
  color: #eee;
}

.tab.active {
  background: #16213e;
  color: #4ecca3;
}

.tab-content {
  background: #16213e;
  border-radius: 12px;
  padding: 1.5rem;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.section-header h2 {
  margin: 0;
  color: #eee;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
}

.data-table th,
.data-table td {
  padding: 0.75rem;
  text-align: left;
  border-bottom: 1px solid #2a2a4a;
}

.data-table th {
  color: #888;
  font-weight: normal;
  font-size: 0.85rem;
}

.data-table td {
  color: #eee;
}

.code-cell {
  font-family: monospace;
  color: #4ecca3 !important;
}

.status {
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.8rem;
}

.status.active {
  background: rgba(78, 204, 163, 0.2);
  color: #4ecca3;
}

.status.inactive {
  background: rgba(136, 136, 136, 0.2);
  color: #888;
}

.status.pending {
  background: rgba(241, 196, 15, 0.2);
  color: #f1c40f;
}

.status.approved {
  background: rgba(78, 204, 163, 0.2);
  color: #4ecca3;
}

.status.rejected {
  background: rgba(231, 76, 60, 0.2);
  color: #e74c3c;
}

.status.registered {
  background: rgba(52, 152, 219, 0.2);
  color: #3498db;
}

.actions {
  display: flex;
  gap: 0.5rem;
}

.btn-small {
  padding: 0.25rem 0.75rem;
  background: #2a2a4a;
  border: none;
  color: #eee;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.8rem;
  transition: background 0.2s;
}

.btn-small:hover:not(:disabled) {
  background: #3a3a5a;
}

.btn-small:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-small.btn-danger {
  background: rgba(231, 76, 60, 0.2);
  color: #e74c3c;
}

.btn-small.btn-danger:hover {
  background: rgba(231, 76, 60, 0.4);
}

.btn-small.btn-success {
  background: rgba(78, 204, 163, 0.2);
  color: #4ecca3;
}

.btn-small.btn-success:hover {
  background: rgba(78, 204, 163, 0.4);
}

.empty {
  text-align: center;
  color: #888;
  padding: 2rem !important;
}

.loading {
  text-align: center;
  color: #888;
  padding: 2rem;
}

.btn-primary {
  padding: 0.75rem 1.5rem;
  background: #4ecca3;
  color: #1a1a2e;
  border: none;
  border-radius: 8px;
  font-weight: bold;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-primary:hover:not(:disabled) {
  background: #3db892;
}

.btn-primary:disabled {
  opacity: 0.6;
}

.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: #16213e;
  padding: 2rem;
  border-radius: 12px;
  width: 100%;
  max-width: 400px;
}

.modal-content h2 {
  color: #4ecca3;
  margin-bottom: 1rem;
}

.form-group {
  margin-bottom: 1rem;
}

.form-group label {
  display: block;
  color: #888;
  margin-bottom: 0.5rem;
  font-size: 0.9rem;
}

.form-group input,
.form-group select {
  width: 100%;
  padding: 0.75rem;
  background: #1a1a2e;
  border: 1px solid #2a2a4a;
  border-radius: 8px;
  color: #eee;
}

.btn-secondary {
  width: 100%;
  padding: 0.75rem;
  background: transparent;
  border: 1px solid #3a3a5a;
  color: #888;
  border-radius: 8px;
  margin-top: 0.75rem;
  cursor: pointer;
}

.error-message {
  background: rgba(231, 76, 60, 0.2);
  color: #e74c3c;
  padding: 0.75rem;
  border-radius: 8px;
  margin-bottom: 1rem;
}

select {
  padding: 0.5rem;
  background: #1a1a2e;
  border: 1px solid #2a2a4a;
  border-radius: 6px;
  color: #eee;
}

.whitelist-desc {
  color: #888;
  font-size: 0.9rem;
  margin-bottom: 1rem;
}

.no-data {
  color: #555;
  font-size: 0.8rem;
}

.config-heading {
  color: #eee;
  margin-top: 2rem;
  margin-bottom: 1rem;
}

.config-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 1rem;
}

.config-card {
  background: #1a1a2e;
  border-radius: 10px;
  padding: 1.25rem;
}

.config-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.config-card h3 {
  color: #4ecca3;
  margin: 0;
  text-transform: capitalize;
}

.enabled-pill {
  padding: 0.25rem 0.75rem;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 600;
  border: none;
  cursor: pointer;
  transition: all 0.2s;
}

.enabled-pill.enabled {
  background: rgba(78, 204, 163, 0.2);
  color: #4ecca3;
}

.enabled-pill.enabled:hover {
  background: rgba(78, 204, 163, 0.35);
}

.enabled-pill.disabled {
  background: rgba(136, 136, 136, 0.2);
  color: #888;
}

.enabled-pill.disabled:hover {
  background: rgba(136, 136, 136, 0.35);
}

.config-field {
  margin-bottom: 0.75rem;
}

.config-field label {
  display: block;
  color: #888;
  font-size: 0.8rem;
  margin-bottom: 0.25rem;
}

.config-field input {
  width: 100%;
  padding: 0.5rem;
  background: #16213e;
  border: 1px solid #2a2a4a;
  border-radius: 6px;
  color: #eee;
}

.config-actions {
  display: flex;
  gap: 0.5rem;
  margin-top: 1rem;
}

.btn-sm {
  padding: 0.4rem 1rem;
  font-size: 0.85rem;
}

.config-meta {
  color: #555;
  font-size: 0.75rem;
  margin-top: 0.5rem;
}
</style>
