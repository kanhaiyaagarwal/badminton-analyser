<template>
  <div class="admin-view">
    <div class="header">
      <div class="header-nav">
        <router-link to="/dashboard" class="back-link">Back to Dashboard</router-link>
        <router-link to="/tuning" class="tuning-link">Badminton Tuning</router-link>
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

        <div v-else class="table-wrapper">
        <table class="data-table">
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

        <div v-else class="table-wrapper">
        <table class="data-table">
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

        <div v-else class="table-wrapper">
        <table class="data-table">
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
      </div>

      <!-- Users Tab -->
      <div v-if="activeTab === 'users'" class="tab-content">
        <h2>Users</h2>

        <div v-if="loadingUsers" class="loading">Loading...</div>

        <div v-else class="table-wrapper">
        <table class="data-table">
          <thead>
            <tr>
              <th>Email</th>
              <th>Username</th>
              <th>Admin</th>
              <th>Features</th>
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
              <td class="features-cell">
                <label
                  v-for="feat in allFeatures"
                  :key="feat"
                  class="feature-check"
                >
                  <input
                    type="checkbox"
                    :checked="user.is_admin || (user.enabled_features || []).includes(feat)"
                    :disabled="user.is_admin"
                    @change="toggleUserFeature(user, feat, $event.target.checked)"
                  />
                  {{ feat }}
                </label>
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
      </div>

      <!-- Feature Access Tab -->
      <div v-if="activeTab === 'feature-access'" class="tab-content">
        <h2>Feature Access</h2>

        <div v-if="loadingFeatureAccess" class="loading">Loading...</div>

        <div v-else class="config-grid">
          <div v-for="fa in featureAccess" :key="fa.feature_name" class="config-card">
            <div class="config-card-header">
              <h3>{{ fa.feature_name }}</h3>
            </div>

            <div class="access-mode-group">
              <label class="access-mode-label">Access Mode</label>
              <div class="segmented-toggle">
                <button
                  v-for="mode in ['global', 'per_user', 'disabled']"
                  :key="mode"
                  :class="['seg-btn', { active: fa.access_mode === mode }]"
                  @click="updateFeatureAccess(fa.feature_name, { access_mode: mode })"
                >
                  {{ mode === 'per_user' ? 'Per User' : mode.charAt(0).toUpperCase() + mode.slice(1) }}
                </button>
              </div>
            </div>

            <label class="default-signup-check">
              <input
                type="checkbox"
                :checked="fa.default_on_signup"
                @change="updateFeatureAccess(fa.feature_name, { default_on_signup: $event.target.checked })"
              />
              Default on signup
            </label>

            <div v-if="fa.updated_at" class="config-meta">
              Updated: {{ formatDate(fa.updated_at) }}
            </div>
          </div>
        </div>
      </div>

      <!-- Challenge Sessions Tab -->
      <div v-if="activeTab === 'sessions'" class="tab-content">
        <div class="section-header">
          <h2>Challenge Sessions</h2>
          <select v-model="challengeTypeFilter" @change="challengePage = 0; loadChallengeSessions()">
            <option value="">All Types</option>
            <option value="plank">Plank</option>
            <option value="squat">Squat</option>
            <option value="pushup">Pushup</option>
          </select>
        </div>

        <div v-if="loadingSessions" class="loading">Loading...</div>

        <div v-else class="table-wrapper">
        <table class="data-table">
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
                  v-if="s.has_screenshots"
                  @click="viewScreenshots(s.id, s.screenshot_count)"
                  class="btn-small"
                >
                  Screenshots ({{ s.screenshot_count }})
                </button>
                <router-link
                  v-if="s.status === 'ended'"
                  :to="`/challenges/results/${s.id}`"
                  class="btn-small btn-info"
                >
                  Results
                </router-link>
                <button
                  v-if="s.has_pose_data"
                  @click="downloadPoseData(s.id)"
                  class="btn-small btn-success"
                >
                  Pose Data
                </button>
                <button
                  v-if="s.has_pose_data"
                  @click="downloadRefinedPoseData(s.id)"
                  class="btn-small"
                >
                  Refined
                </button>
                <span v-if="!s.has_pose_data && !s.has_screenshots" class="no-data">No data</span>
              </td>
            </tr>
            <tr v-if="challengeSessions.length === 0">
              <td colspan="8" class="empty">No challenge sessions found</td>
            </tr>
          </tbody>
        </table>
        </div>

        <div v-if="challengeTotal > PAGE_SIZE" class="pagination">
          <button @click="challengePageChange(-1)" :disabled="challengePage === 0" class="btn-small">Prev</button>
          <span class="page-info">{{ challengePage * PAGE_SIZE + 1 }}–{{ Math.min((challengePage + 1) * PAGE_SIZE, challengeTotal) }} of {{ challengeTotal }}</span>
          <button @click="challengePageChange(1)" :disabled="(challengePage + 1) * PAGE_SIZE >= challengeTotal" class="btn-small">Next</button>
        </div>
      </div>

      <!-- Challenge Config Tab -->
      <div v-if="activeTab === 'challenge-config'" class="tab-content">
        <h2>Challenge Tolerance Config</h2>

        <div v-if="loadingConfig" class="loading">Loading...</div>

        <div v-else class="config-grid">
          <div v-for="(cfg, ctype) in challengeConfig" :key="ctype" class="config-card">
            <div class="config-card-header">
              <h3>{{ ctype }}</h3>
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

      <!-- Badminton Sessions Tab -->
      <div v-if="activeTab === 'badminton'" class="tab-content">
        <h2>Badminton Stream Sessions</h2>

        <div v-if="loadingBadminton" class="loading">Loading...</div>

        <div v-else class="table-wrapper">
        <table class="data-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>User</th>
              <th>Title</th>
              <th>Shots</th>
              <th>Mode</th>
              <th>Date</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="s in badmintonSessions" :key="s.id">
              <td>{{ s.id }}</td>
              <td>{{ s.username }}</td>
              <td>{{ s.title || '-' }}</td>
              <td>{{ s.post_analysis_shots ?? s.total_shots }}</td>
              <td>{{ s.stream_mode }}</td>
              <td>{{ formatDate(s.created_at) }}</td>
              <td>
                <span :class="['status', s.status === 'ended' ? 'active' : 'pending']">
                  {{ s.status }}
                </span>
              </td>
              <td class="actions">
                <router-link
                  v-if="s.status === 'ended'"
                  :to="`/stream-results/${s.id}`"
                  class="btn-small btn-info"
                >
                  Results
                </router-link>
              </td>
            </tr>
            <tr v-if="badmintonSessions.length === 0">
              <td colspan="8" class="empty">No badminton sessions found</td>
            </tr>
          </tbody>
        </table>
        </div>

        <div v-if="badmintonTotal > PAGE_SIZE" class="pagination">
          <button @click="badmintonPageChange(-1)" :disabled="badmintonPage === 0" class="btn-small">Prev</button>
          <span class="page-info">{{ badmintonPage * PAGE_SIZE + 1 }}–{{ Math.min((badmintonPage + 1) * PAGE_SIZE, badmintonTotal) }} of {{ badmintonTotal }}</span>
          <button @click="badmintonPageChange(1)" :disabled="(badmintonPage + 1) * PAGE_SIZE >= badmintonTotal" class="btn-small">Next</button>
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
    <!-- Screenshots modal -->
    <div v-if="screenshotModal.open" class="modal-overlay" @click.self="screenshotModal.open = false">
      <div class="modal-panel screenshots-panel">
        <div class="modal-header">
          <h3>Session #{{ screenshotModal.sessionId }} Screenshots</h3>
          <button class="modal-close" @click="screenshotModal.open = false">&times;</button>
        </div>
        <div v-if="screenshotModal.loading" class="modal-loading">Loading screenshots...</div>
        <div v-else class="screenshots-scroll">
          <div class="screenshots-grid">
            <div v-for="(src, i) in screenshotModal.images" :key="i" class="screenshot-item">
              <img :src="src" :alt="`Screenshot ${i}`" loading="lazy" />
              <span class="screenshot-index">{{ i + 1 }}</span>
            </div>
          </div>
          <div v-if="screenshotModal.images.length < screenshotModal.total" class="load-more-row">
            <button @click="loadMoreScreenshots" class="btn-small" :disabled="screenshotModal.loadingMore">
              {{ screenshotModal.loadingMore ? 'Loading...' : `Load More (${screenshotModal.images.length}/${screenshotModal.total})` }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useAuthStore } from '../stores/auth'
import api from '../api/client'

const authStore = useAuthStore()
const currentUser = computed(() => authStore.user)
const isAdmin = computed(() => authStore.user?.is_admin)

const allFeatures = ['badminton', 'pushup', 'squat', 'plank']

const tabs = [
  { id: 'codes', label: 'Invite Codes' },
  { id: 'whitelist', label: 'Whitelist' },
  { id: 'waitlist', label: 'Waitlist' },
  { id: 'users', label: 'Users' },
  { id: 'feature-access', label: 'Feature Access' },
  { id: 'sessions', label: 'Challenge Sessions' },
  { id: 'challenge-config', label: 'Challenge Config' },
  { id: 'badminton', label: 'Badminton Sessions' },
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
const screenshotModal = ref({ open: false, sessionId: null, images: [], loading: false, loadingMore: false, total: 0 })

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

// Challenge Sessions (paginated)
const challengeSessions = ref([])
const loadingSessions = ref(false)
const challengeTypeFilter = ref('')
const challengePage = ref(0)
const challengeTotal = ref(0)
const PAGE_SIZE = 20

// Feature Access
const featureAccess = ref([])
const loadingFeatureAccess = ref(false)

// Challenge Config
const challengeConfig = ref({})
const loadingConfig = ref(false)

// Badminton Sessions (paginated)
const badmintonSessions = ref([])
const loadingBadminton = ref(false)
const badmintonPage = ref(0)
const badmintonTotal = ref(0)

onMounted(async () => {
  if (isAdmin.value) {
    await Promise.all([loadCodes(), loadWhitelist(), loadWaitlist(), loadUsers()])
  }
})

watch(activeTab, (tab) => {
  if (tab === 'feature-access' && featureAccess.value.length === 0) {
    loadFeatureAccess()
  }
  if (tab === 'sessions' && challengeSessions.value.length === 0) {
    loadChallengeSessions()
  }
  if (tab === 'challenge-config' && Object.keys(challengeConfig.value).length === 0) {
    loadChallengeConfig()
  }
  if (tab === 'badminton' && badmintonSessions.value.length === 0) {
    loadBadmintonSessions()
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

async function toggleUserFeature(user, feature, checked) {
  const current = [...(user.enabled_features || [])]
  const updated = checked
    ? [...new Set([...current, feature])]
    : current.filter(f => f !== feature)

  // Optimistic update
  user.enabled_features = updated

  try {
    await api.patch(`/api/v1/admin/users/${user.id}/features`, {
      enabled_features: updated
    })
  } catch (err) {
    console.error('Failed to update features:', err)
    // Revert on failure
    user.enabled_features = current
    await loadUsers()
  }
}

// ---------- Challenges ----------

async function loadChallengeSessions() {
  loadingSessions.value = true
  try {
    const params = { skip: challengePage.value * PAGE_SIZE, limit: PAGE_SIZE }
    if (challengeTypeFilter.value) params.challenge_type = challengeTypeFilter.value
    const response = await api.get('/api/v1/challenges/admin/sessions', { params })
    challengeSessions.value = response.data.sessions
    challengeTotal.value = response.data.total
  } catch (err) {
    console.error('Failed to load challenge sessions:', err)
  } finally {
    loadingSessions.value = false
  }
}

async function loadBadmintonSessions() {
  loadingBadminton.value = true
  try {
    const params = { skip: badmintonPage.value * PAGE_SIZE, limit: PAGE_SIZE }
    const response = await api.get('/api/v1/admin/stream-sessions', { params })
    badmintonSessions.value = response.data.sessions
    badmintonTotal.value = response.data.total
  } catch (err) {
    console.error('Failed to load badminton sessions:', err)
  } finally {
    loadingBadminton.value = false
  }
}

function challengePageChange(dir) {
  challengePage.value += dir
  loadChallengeSessions()
}

function badmintonPageChange(dir) {
  badmintonPage.value += dir
  loadBadmintonSessions()
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


// ---------- Feature Access ----------

async function loadFeatureAccess() {
  loadingFeatureAccess.value = true
  try {
    const response = await api.get('/api/v1/admin/feature-access')
    featureAccess.value = response.data
  } catch (err) {
    console.error('Failed to load feature access:', err)
  } finally {
    loadingFeatureAccess.value = false
  }
}

async function updateFeatureAccess(featureName, patch) {
  try {
    await api.patch(`/api/v1/admin/feature-access/${featureName}`, patch)
    await loadFeatureAccess()
  } catch (err) {
    console.error('Failed to update feature access:', err)
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

async function downloadRefinedPoseData(sessionId) {
  try {
    const response = await api.get(`/api/v1/challenges/admin/sessions/${sessionId}/pose-data/refined`)
    const blob = new Blob([JSON.stringify(response.data, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `refined_pose_data_${sessionId}.json`
    a.click()
    URL.revokeObjectURL(url)
  } catch (err) {
    console.error('Failed to download refined pose data:', err)
  }
}

const SCREENSHOTS_PAGE_SIZE = 10

async function viewScreenshots(sessionId, count) {
  screenshotModal.value = { open: true, sessionId, images: [], loading: true, loadingMore: false, total: count }
  try {
    await loadScreenshotsBatch(sessionId, 0, Math.min(SCREENSHOTS_PAGE_SIZE, count))
  } catch (err) {
    console.error('Failed to load screenshots:', err)
  }
  screenshotModal.value.loading = false
}

async function loadMoreScreenshots() {
  const modal = screenshotModal.value
  if (modal.loadingMore || modal.images.length >= modal.total) return
  modal.loadingMore = true
  try {
    const start = modal.images.length
    const end = Math.min(start + SCREENSHOTS_PAGE_SIZE, modal.total)
    await loadScreenshotsBatch(modal.sessionId, start, end)
  } catch (err) {
    console.error('Failed to load more screenshots:', err)
  }
  modal.loadingMore = false
}

async function loadScreenshotsBatch(sessionId, start, end) {
  for (let i = start; i < end; i++) {
    const res = await api.get(
      `/api/v1/challenges/admin/sessions/${sessionId}/screenshots/${i}`,
      { responseType: 'blob' }
    )
    screenshotModal.value.images.push(URL.createObjectURL(res.data))
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
  color: var(--text-muted);
  text-decoration: none;
  font-size: 0.9rem;
}

.tuning-link {
  color: var(--color-primary);
  text-decoration: none;
  font-size: 0.9rem;
  padding: 0.5rem 1rem;
  background: var(--color-primary-light);
  border-radius: var(--radius-sm);
  transition: background 0.2s;
}

.tuning-link:hover {
  background: var(--color-primary-light);
}

h1 {
  color: var(--color-secondary);
  margin-top: 0.5rem;
}

.not-admin {
  text-align: center;
  padding: 3rem;
  color: var(--text-muted);
}

.tabs {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1.5rem;
  border-bottom: 1px solid var(--border-color);
  padding-bottom: 0.5rem;
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}

.tab {
  padding: 0.75rem 1.5rem;
  white-space: nowrap;
  background: transparent;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  border-radius: var(--radius-md) var(--radius-md) 0 0;
  transition: all 0.2s;
  font-weight: 600;
}

.tab:hover {
  color: var(--text-primary);
}

.tab.active {
  background: var(--bg-card);
  color: var(--color-secondary);
}

.tab-content {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 1.5rem;
  box-shadow: var(--shadow-md);
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.section-header h2 {
  margin: 0;
  color: var(--text-primary);
}

.table-wrapper {
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  min-width: 600px;
}

.data-table th,
.data-table td {
  padding: 0.75rem;
  text-align: left;
  border-bottom: 1px solid var(--border-color);
  white-space: nowrap;
}

.data-table th {
  color: var(--text-muted);
  font-weight: normal;
  font-size: 0.85rem;
  background: var(--bg-input);
}

.data-table td {
  color: var(--text-primary);
}

.code-cell {
  font-family: monospace;
  color: var(--color-secondary) !important;
}

.status {
  padding: 0.25rem 0.5rem;
  border-radius: var(--radius-sm);
  font-size: 0.8rem;
}

.status.active {
  background: var(--color-primary-light);
  color: var(--color-primary);
}

.status.inactive {
  background: rgba(136, 136, 136, 0.2);
  color: var(--text-muted);
}

.status.pending {
  background: var(--color-warning-light, rgba(241, 196, 15, 0.2));
  color: var(--color-warning);
}

.status.approved {
  background: var(--color-primary-light);
  color: var(--color-primary);
}

.status.rejected {
  background: var(--color-destructive-light);
  color: var(--color-destructive);
}

.status.registered {
  background: var(--color-info-light);
  color: var(--color-info);
}

.actions {
  display: flex;
  gap: 0.5rem;
}

.btn-small {
  padding: 0.25rem 0.75rem;
  background: var(--border-color);
  border: none;
  color: var(--text-primary);
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: 0.8rem;
  font-weight: 600;
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
  background: var(--color-destructive-light);
  color: var(--color-destructive);
}

.btn-small.btn-danger:hover {
  background: var(--color-destructive-light);
}

.btn-small.btn-success {
  background: var(--color-primary-light);
  color: var(--color-primary);
}

.btn-small.btn-success:hover {
  background: var(--color-primary-light);
}

.btn-small.btn-info {
  background: var(--color-secondary, #7c3aed);
  color: #fff;
  text-decoration: none;
}

.btn-small.btn-info:hover {
  opacity: 0.85;
}

.empty {
  text-align: center;
  color: var(--text-muted);
  padding: 2rem !important;
}

.loading {
  text-align: center;
  color: var(--text-muted);
  padding: 2rem;
}

.btn-primary {
  padding: 0.75rem 1.5rem;
  background: var(--color-secondary);
  color: var(--text-on-primary);
  border: none;
  border-radius: var(--radius-md);
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-primary:hover:not(:disabled) {
  background: var(--color-secondary-hover, #8e4aaa);
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
  background: var(--bg-card);
  padding: 2rem;
  border-radius: var(--radius-lg);
  width: 100%;
  max-width: 400px;
  box-shadow: var(--shadow-lg);
}

.modal-content h2 {
  color: var(--color-secondary);
  margin-bottom: 1rem;
}

.form-group {
  margin-bottom: 1rem;
}

.form-group label {
  display: block;
  color: var(--text-muted);
  margin-bottom: 0.5rem;
  font-size: 0.9rem;
}

.form-group input,
.form-group select {
  width: 100%;
  padding: 0.75rem;
  background: var(--bg-input);
  border: 1px solid var(--border-input);
  border-radius: var(--radius-md);
  color: var(--text-primary);
}

.btn-secondary {
  width: 100%;
  padding: 0.75rem;
  background: transparent;
  border: 1px solid var(--border-color);
  color: var(--text-muted);
  border-radius: var(--radius-md);
  margin-top: 0.75rem;
  cursor: pointer;
  font-weight: 600;
}

.error-message {
  background: var(--color-destructive-light);
  color: var(--color-destructive);
  padding: 0.75rem;
  border-radius: var(--radius-md);
  margin-bottom: 1rem;
}

select {
  padding: 0.5rem;
  background: var(--bg-input);
  border: 1px solid var(--border-input);
  border-radius: var(--radius-sm);
  color: var(--text-primary);
}

.whitelist-desc {
  color: var(--text-muted);
  font-size: 0.9rem;
  margin-bottom: 1rem;
}

.no-data {
  color: var(--text-muted);
  font-size: 0.8rem;
}

.features-cell {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.feature-check {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  font-size: 0.8rem;
  color: var(--text-secondary);
  text-transform: capitalize;
  cursor: pointer;
  white-space: nowrap;
}

.feature-check input[type="checkbox"] {
  width: auto;
  cursor: pointer;
}

.feature-check input[type="checkbox"]:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.config-heading {
  color: var(--text-primary);
  margin-top: 2rem;
  margin-bottom: 1rem;
}

.config-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 1rem;
}

.config-card {
  background: var(--bg-input);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 1.25rem;
  box-shadow: var(--shadow-md);
}

.config-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.config-card h3 {
  color: var(--color-secondary);
  margin: 0;
  text-transform: capitalize;
}

.access-mode-group {
  margin-bottom: 1rem;
}

.access-mode-label {
  display: block;
  color: var(--text-muted);
  font-size: 0.8rem;
  margin-bottom: 0.5rem;
}

.segmented-toggle {
  display: flex;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.seg-btn {
  flex: 1;
  padding: 0.4rem 0.5rem;
  background: transparent;
  border: none;
  border-right: 1px solid var(--border-color);
  color: var(--text-muted);
  font-size: 0.75rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.seg-btn:last-child {
  border-right: none;
}

.seg-btn:hover:not(.active) {
  background: rgba(136, 136, 136, 0.15);
}

.seg-btn.active {
  background: var(--color-secondary);
  color: var(--text-on-primary);
}

.default-signup-check {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.85rem;
  color: var(--text-secondary);
  cursor: pointer;
  margin-top: 0.5rem;
}

.default-signup-check input[type="checkbox"] {
  width: auto;
  cursor: pointer;
}

.config-field {
  margin-bottom: 0.75rem;
}

.config-field label {
  display: block;
  color: var(--text-muted);
  font-size: 0.8rem;
  margin-bottom: 0.25rem;
}

.config-field input {
  width: 100%;
  padding: 0.5rem;
  background: var(--bg-card);
  border: 1px solid var(--border-input);
  border-radius: var(--radius-sm);
  color: var(--text-primary);
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
  color: var(--text-muted);
  font-size: 0.75rem;
  margin-top: 0.5rem;
}

.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  margin-top: 1rem;
  padding: 0.75rem 0;
}

.page-info {
  color: var(--text-secondary);
  font-size: 0.85rem;
  font-weight: 500;
}

.modal-panel {
  background: var(--bg-card);
  padding: 1.5rem;
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
}

/* Screenshots modal */
.screenshots-panel {
  max-width: 900px;
  width: 95vw;
  max-height: 90vh;
  overflow-y: auto;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.modal-header h3 {
  margin: 0;
  color: var(--text-primary);
}

.modal-close {
  background: none;
  border: none;
  color: var(--text-muted);
  font-size: 1.5rem;
  cursor: pointer;
  padding: 0.25rem 0.5rem;
  line-height: 1;
}

.modal-loading {
  text-align: center;
  color: var(--text-muted);
  padding: 2rem;
}

.screenshots-scroll {
  max-height: calc(90vh - 5rem);
  overflow-y: auto;
}

.screenshots-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 0.75rem;
}

.load-more-row {
  text-align: center;
  padding: 1rem 0;
}

.screenshot-item {
  position: relative;
  border-radius: var(--radius-sm);
  overflow: hidden;
  background: #000;
}

.screenshot-item img {
  width: 100%;
  display: block;
}

.screenshot-index {
  position: absolute;
  top: 0.25rem;
  left: 0.25rem;
  background: rgba(0, 0, 0, 0.6);
  color: #fff;
  font-size: 0.7rem;
  font-weight: 600;
  padding: 0.1rem 0.4rem;
  border-radius: var(--radius-sm);
}
</style>
