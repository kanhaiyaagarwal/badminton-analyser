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
              <th>#</th>
              <th>Email</th>
              <th>Username</th>
              <th>Invite Code</th>
              <th>Admin</th>
              <th>Features</th>
              <th>Created</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(user, index) in users" :key="user.id">
              <td>{{ index + 1 }}</td>
              <td>{{ user.email }}</td>
              <td>{{ user.username }}</td>
              <td>{{ user.signed_up_with_code || '-' }}</td>
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

      <!-- Feature Requests Tab -->
      <div v-if="activeTab === 'feature-requests'" class="tab-content">
        <div class="section-header">
          <h2>Feature Requests</h2>
          <select v-model="featureRequestFilter" @change="loadFeatureRequests()">
            <option value="">All Statuses</option>
            <option value="pending">Pending</option>
            <option value="in_review">In Review</option>
            <option value="approved">Approved</option>
            <option value="rejected">Rejected</option>
          </select>
        </div>

        <div v-if="loadingFeatureRequests" class="loading">Loading...</div>

        <div v-else class="table-wrapper">
        <table class="data-table">
          <thead>
            <tr>
              <th>Username</th>
              <th>Email</th>
              <th>Feature</th>
              <th>Status</th>
              <th>Date</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="req in featureRequests" :key="req.id">
              <td>{{ req.username }}</td>
              <td>{{ req.email }}</td>
              <td>{{ req.feature_name }}</td>
              <td>
                <span :class="['status', req.status === 'approved' ? 'active' : req.status === 'pending' ? 'pending' : req.status === 'in_review' ? 'review' : 'inactive']">
                  {{ req.status === 'in_review' ? 'In Review' : req.status }}
                </span>
              </td>
              <td>{{ formatDate(req.created_at) }}</td>
              <td class="actions">
                <template v-if="req.status === 'pending' || req.status === 'in_review'">
                  <button @click="approveFeatureRequest(req)" class="btn-small btn-success">Approve</button>
                  <button @click="openReviewModal(req)" class="btn-small btn-review">In Review</button>
                  <button @click="rejectFeatureRequest(req)" class="btn-small btn-danger">Reject</button>
                </template>
                <span v-else class="text-muted">-</span>
              </td>
            </tr>
            <tr v-if="featureRequests.length === 0">
              <td colspan="6" class="empty">No feature requests</td>
            </tr>
          </tbody>
        </table>
        </div>

        <!-- Review Modal -->
        <div v-if="reviewModal.show" class="modal-overlay" @click.self="reviewModal.show = false">
          <div class="modal-content" @click.stop>
            <h2>Review: {{ reviewModal.req?.feature_name }}</h2>
            <p class="text-muted" style="margin-bottom: 1rem;">Email will be sent to {{ reviewModal.req?.email }}</p>

            <form @submit.prevent="submitReview">
              <div class="form-group">
                <label>Message to user</label>
                <textarea
                  v-model="reviewModal.message"
                  rows="6"
                  placeholder="Enter your message to the user..."
                  style="width: 100%; resize: vertical;"
                ></textarea>
              </div>

              <button
                type="submit"
                class="btn-primary"
                :disabled="!reviewModal.message.trim() || reviewModal.sending"
              >
                {{ reviewModal.sending ? 'Sending...' : 'Send Review Email' }}
              </button>
              <button type="button" @click="reviewModal.show = false" class="btn-secondary">
                Cancel
              </button>
            </form>
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
            <option value="squat_hold">Squat Hold</option>
            <option value="squat_half">Half Squats</option>
            <option value="squat_full">Full Squats</option>
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
                <button
                  v-if="s.has_recording"
                  @click="downloadRecording(s.id)"
                  class="btn-small btn-info"
                >
                  Video
                </button>
                <span v-if="!s.has_pose_data && !s.has_screenshots && !s.has_recording" class="no-data">No data</span>
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

      <!-- MoveMatch Challenges Tab -->
      <div v-if="activeTab === 'mimic-challenges'" class="tab-content">
        <div class="section-header">
          <h2>MoveMatch Challenges</h2>
        </div>

        <div v-if="loadingMimicChallenges" class="loading">Loading...</div>

        <div v-else class="table-wrapper">
        <table class="data-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Title</th>
              <th>Creator</th>
              <th>Status</th>
              <th>Duration</th>
              <th>Plays</th>
              <th>Public</th>
              <th>Trending</th>
              <th>Date</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="ch in mimicChallenges" :key="ch.id">
              <td>{{ ch.id }}</td>
              <td>{{ ch.title }}</td>
              <td>{{ ch.creator_username || '-' }}<br v-if="ch.creator_email" /><span v-if="ch.creator_email" class="text-muted" style="font-size:0.75rem">{{ ch.creator_email }}</span></td>
              <td>
                <span :class="['status', ch.processing_status === 'ready' ? 'active' : 'pending']">
                  {{ ch.processing_status }}
                </span>
              </td>
              <td>{{ ch.video_duration ? ch.video_duration.toFixed(1) + 's' : '-' }}</td>
              <td>{{ ch.play_count }}</td>
              <td>
                <button @click="toggleMimicPublic(ch)" class="btn-small" :class="ch.is_public ? 'btn-success' : ''">
                  {{ ch.is_public ? 'Yes' : 'No' }}
                </button>
              </td>
              <td>
                <button @click="toggleMimicTrending(ch)" class="btn-small" :class="ch.is_trending ? 'btn-success' : ''">
                  {{ ch.is_trending ? 'Yes' : 'No' }}
                </button>
              </td>
              <td>{{ formatDate(ch.created_at) }}</td>
              <td class="actions">
                <button @click="deleteMimicChallenge(ch)" class="btn-small btn-danger">Delete</button>
              </td>
            </tr>
            <tr v-if="mimicChallenges.length === 0">
              <td colspan="10" class="empty">No MoveMatch challenges found</td>
            </tr>
          </tbody>
        </table>
        </div>

        <div v-if="mimicChallengesTotal > PAGE_SIZE" class="pagination">
          <button @click="mimicChallengesPageChange(-1)" :disabled="mimicChallengesPage === 0" class="btn-small">Prev</button>
          <span class="page-info">{{ mimicChallengesPage * PAGE_SIZE + 1 }}–{{ Math.min((mimicChallengesPage + 1) * PAGE_SIZE, mimicChallengesTotal) }} of {{ mimicChallengesTotal }}</span>
          <button @click="mimicChallengesPageChange(1)" :disabled="(mimicChallengesPage + 1) * PAGE_SIZE >= mimicChallengesTotal" class="btn-small">Next</button>
        </div>
      </div>

      <!-- MoveMatch Sessions Tab -->
      <div v-if="activeTab === 'mimic-sessions'" class="tab-content">
        <div class="section-header">
          <h2>MoveMatch Sessions</h2>
        </div>

        <div v-if="loadingMimicSessions" class="loading">Loading...</div>

        <div v-else class="table-wrapper">
        <table class="data-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>User</th>
              <th>Challenge</th>
              <th>Source</th>
              <th>Score</th>
              <th>Duration</th>
              <th>Frames</th>
              <th>Date</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="s in mimicSessions" :key="s.id">
              <td>{{ s.id }}</td>
              <td>{{ s.username }}</td>
              <td>{{ s.challenge_title || `#${s.challenge_id}` }}</td>
              <td>{{ s.source }}</td>
              <td>{{ s.overall_score.toFixed(1) }}</td>
              <td>{{ s.duration_seconds.toFixed(1) }}s</td>
              <td>{{ s.frames_compared }}</td>
              <td>{{ formatDate(s.created_at) }}</td>
              <td>
                <span :class="['status', s.status === 'ended' ? 'active' : 'pending']">
                  {{ s.status }}
                </span>
              </td>
              <td class="actions">
                <button
                  v-if="s.has_comparison_video"
                  @click="openMimicVideo(s)"
                  class="btn-small btn-info"
                >
                  Video
                </button>
                <button
                  v-if="s.has_uploaded_video"
                  @click="downloadMimicUpload(s)"
                  class="btn-small"
                >
                  Original
                </button>
                <button
                  @click="openMimicDetails(s)"
                  class="btn-small"
                >
                  Details
                </button>
                <button
                  v-if="s.has_screenshots"
                  @click="viewMimicScreenshots(s.id, s.screenshot_count)"
                  class="btn-small"
                >
                  Screenshots ({{ s.screenshot_count }})
                </button>
              </td>
            </tr>
            <tr v-if="mimicSessions.length === 0">
              <td colspan="10" class="empty">No MoveMatch sessions found</td>
            </tr>
          </tbody>
        </table>
        </div>

        <div v-if="mimicSessionsTotal > PAGE_SIZE" class="pagination">
          <button @click="mimicSessionsPageChange(-1)" :disabled="mimicSessionsPage === 0" class="btn-small">Prev</button>
          <span class="page-info">{{ mimicSessionsPage * PAGE_SIZE + 1 }}–{{ Math.min((mimicSessionsPage + 1) * PAGE_SIZE, mimicSessionsTotal) }} of {{ mimicSessionsTotal }}</span>
          <button @click="mimicSessionsPageChange(1)" :disabled="(mimicSessionsPage + 1) * PAGE_SIZE >= mimicSessionsTotal" class="btn-small">Next</button>
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
    <!-- MoveMatch Screenshots modal -->
    <div v-if="mimicSsModal.open" class="modal-overlay" @click.self="mimicSsModal.open = false">
      <div class="modal-panel screenshots-panel">
        <div class="modal-header">
          <h3>MoveMatch Session #{{ mimicSsModal.sessionId }} Screenshots</h3>
          <div class="modal-header-actions">
            <button @click="downloadMimicScreenshots" class="btn-small" :disabled="mimicSsDownloading">
              {{ mimicSsDownloading ? 'Downloading...' : 'Download All' }}
            </button>
            <button class="modal-close" @click="mimicSsModal.open = false">&times;</button>
          </div>
        </div>
        <div v-if="mimicSsModal.loading" class="modal-loading">Loading screenshots...</div>
        <div v-else class="screenshots-scroll">
          <div class="screenshots-nav">
            <span class="screenshots-count">Page {{ mimicSsCurrentPage }} of {{ mimicSsTotalPages }} ({{ mimicSsModal.total }} screenshots)</span>
            <div class="screenshots-page-controls">
              <button @click="mimicSsGoToPage(mimicSsCurrentPage - 1)" class="btn-small" :disabled="mimicSsCurrentPage <= 1 || mimicSsModal.loadingMore">&laquo; Prev</button>
              <div class="screenshots-jump">
                <label>Page</label>
                <input
                  type="number"
                  v-model.number="mimicSsJumpPage"
                  :min="1"
                  :max="mimicSsTotalPages"
                  @keyup.enter="mimicSsGoToPage(mimicSsJumpPage)"
                  class="jump-input"
                />
                <button @click="mimicSsGoToPage(mimicSsJumpPage)" class="btn-small" :disabled="mimicSsModal.loadingMore">Go</button>
              </div>
              <button @click="mimicSsGoToPage(mimicSsCurrentPage + 1)" class="btn-small" :disabled="mimicSsCurrentPage >= mimicSsTotalPages || mimicSsModal.loadingMore">Next &raquo;</button>
            </div>
          </div>
          <div v-if="mimicSsModal.loadingMore" class="modal-loading">Loading page...</div>
          <div v-else class="screenshots-grid">
            <div v-for="entry in mimicSsPageEntries" :key="entry.idx" class="screenshot-item">
              <img :src="entry.src" :alt="`Screenshot ${entry.idx + 1}`" />
              <span class="screenshot-index">{{ entry.idx + 1 }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- MoveMatch Video modal -->
    <div v-if="mimicVideoModal.open" class="modal-overlay" @click.self="closeMimicVideo">
      <div class="modal-panel video-panel">
        <div class="modal-header">
          <h3>Comparison Video — Session #{{ mimicVideoModal.sessionId }} ({{ mimicVideoModal.username }})</h3>
          <button class="modal-close" @click="closeMimicVideo">&times;</button>
        </div>
        <div v-if="mimicVideoModal.loading" class="modal-loading">Loading video...</div>
        <video
          v-else-if="mimicVideoModal.src"
          ref="mimicVideoEl"
          controls
          autoplay
          :src="mimicVideoModal.src"
          class="mimic-video-player"
        ></video>
      </div>
    </div>

    <!-- MoveMatch Details modal -->
    <div v-if="mimicDetailsModal.open" class="modal-overlay" @click.self="mimicDetailsModal.open = false">
      <div class="modal-panel details-panel">
        <div class="modal-header">
          <h3>Session Details — #{{ mimicDetailsModal.sessionId }}</h3>
          <button class="modal-close" @click="mimicDetailsModal.open = false">&times;</button>
        </div>
        <div v-if="mimicDetailsModal.loading" class="modal-loading">Loading details...</div>
        <template v-else-if="mimicDetailsModal.data">
          <div class="detail-score-grid">
            <div class="detail-score-card">
              <span class="detail-score-label">Overall Score</span>
              <span class="detail-score-value" :style="{ color: scoreColor(mimicDetailsModal.data.overall_score) }">
                {{ mimicDetailsModal.data.overall_score.toFixed(1) }}
              </span>
            </div>
            <template v-if="mimicDetailsModal.data.score_breakdown">
              <div class="detail-score-card" v-if="mimicDetailsModal.data.score_breakdown.cosine_raw != null">
                <span class="detail-score-label">Cosine Raw</span>
                <span class="detail-score-value">{{ mimicDetailsModal.data.score_breakdown.cosine_raw.toFixed(2) }}</span>
              </div>
              <div class="detail-score-card" v-if="mimicDetailsModal.data.score_breakdown.cosine_normalized != null">
                <span class="detail-score-label">Cosine Normalized</span>
                <span class="detail-score-value">{{ mimicDetailsModal.data.score_breakdown.cosine_normalized.toFixed(2) }}</span>
              </div>
              <div class="detail-score-card" v-if="mimicDetailsModal.data.score_breakdown.angle_score != null">
                <span class="detail-score-label">Angle Score</span>
                <span class="detail-score-value">{{ mimicDetailsModal.data.score_breakdown.angle_score.toFixed(2) }}</span>
              </div>
              <div class="detail-score-card" v-if="mimicDetailsModal.data.score_breakdown.upper_body != null">
                <span class="detail-score-label">Upper Body</span>
                <span class="detail-score-value">{{ mimicDetailsModal.data.score_breakdown.upper_body.toFixed(2) }}</span>
              </div>
              <div class="detail-score-card" v-if="mimicDetailsModal.data.score_breakdown.lower_body != null">
                <span class="detail-score-label">Lower Body</span>
                <span class="detail-score-value">{{ mimicDetailsModal.data.score_breakdown.lower_body.toFixed(2) }}</span>
              </div>
            </template>
          </div>
          <div v-if="mimicDetailsModal.data.feedback" class="detail-feedback">
            <h4>Feedback</h4>
            <p class="feedback-summary">{{ mimicDetailsModal.data.feedback.summary }}</p>
            <div v-if="mimicDetailsModal.data.feedback.items" class="feedback-items">
              <div
                v-for="(item, idx) in mimicDetailsModal.data.feedback.items"
                :key="idx"
                :class="['feedback-item', `feedback-${item.status}`]"
              >
                <span class="feedback-region">{{ item.region.replace('_', ' ') }}</span>
                <span class="feedback-message">{{ item.message }}</span>
              </div>
            </div>
          </div>
          <div class="detail-meta">
            <span><strong>Source:</strong> {{ mimicDetailsModal.data.source }}</span>
            <span><strong>Duration:</strong> {{ mimicDetailsModal.data.duration_seconds.toFixed(1) }}s</span>
            <span><strong>Frames:</strong> {{ mimicDetailsModal.data.frames_compared }}</span>
            <span v-if="mimicDetailsModal.data.created_at"><strong>Started:</strong> {{ formatDate(mimicDetailsModal.data.created_at) }}</span>
            <span v-if="mimicDetailsModal.data.ended_at"><strong>Ended:</strong> {{ formatDate(mimicDetailsModal.data.ended_at) }}</span>
          </div>
        </template>
      </div>
    </div>

    <!-- Screenshots modal -->
    <div v-if="screenshotModal.open" class="modal-overlay" @click.self="screenshotModal.open = false">
      <div class="modal-panel screenshots-panel">
        <div class="modal-header">
          <h3>Session #{{ screenshotModal.sessionId }} Screenshots</h3>
          <div class="modal-header-actions">
            <button @click="downloadAllScreenshots" class="btn-small" :disabled="ssDownloading">
              {{ ssDownloading ? 'Downloading...' : 'Download All' }}
            </button>
            <button class="modal-close" @click="screenshotModal.open = false">&times;</button>
          </div>
        </div>
        <div v-if="screenshotModal.loading" class="modal-loading">Loading screenshots...</div>
        <div v-else class="screenshots-scroll">
          <div class="screenshots-nav">
            <span class="screenshots-count">Page {{ ssCurrentPage }} of {{ ssTotalPages }} ({{ screenshotModal.total }} screenshots)</span>
            <div class="screenshots-page-controls">
              <button @click="ssGoToPage(ssCurrentPage - 1)" class="btn-small" :disabled="ssCurrentPage <= 1 || screenshotModal.loadingMore">&laquo; Prev</button>
              <div class="screenshots-jump">
                <label>Page</label>
                <input
                  type="number"
                  v-model.number="ssJumpPage"
                  :min="1"
                  :max="ssTotalPages"
                  @keyup.enter="ssGoToPage(ssJumpPage)"
                  class="jump-input"
                />
                <button @click="ssGoToPage(ssJumpPage)" class="btn-small" :disabled="screenshotModal.loadingMore">Go</button>
              </div>
              <button @click="ssGoToPage(ssCurrentPage + 1)" class="btn-small" :disabled="ssCurrentPage >= ssTotalPages || screenshotModal.loadingMore">Next &raquo;</button>
            </div>
          </div>
          <div v-if="screenshotModal.loadingMore" class="modal-loading">Loading page...</div>
          <div v-else class="screenshots-grid">
            <div v-for="entry in ssPageEntries" :key="entry.idx" class="screenshot-item">
              <img :src="entry.src" :alt="`Screenshot ${entry.idx + 1}`" />
              <span class="screenshot-index">{{ entry.idx + 1 }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, nextTick } from 'vue'
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
  { id: 'feature-requests', label: 'Feature Requests' },
  { id: 'sessions', label: 'Challenge Sessions' },
  { id: 'challenge-config', label: 'Challenge Config' },
  { id: 'badminton', label: 'Badminton Sessions' },
  { id: 'mimic-challenges', label: 'MoveMatch Challenges' },
  { id: 'mimic-sessions', label: 'MoveMatch Sessions' },
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
const screenshotModal = ref({ open: false, sessionId: null, loading: false, loadingMore: false, total: 0 })

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

// Feature Requests
const featureRequests = ref([])
const loadingFeatureRequests = ref(false)
const featureRequestFilter = ref('')
const reviewModal = ref({ show: false, req: null, message: '', sending: false })

// Challenge Config
const challengeConfig = ref({})
const loadingConfig = ref(false)

// Badminton Sessions (paginated)
const badmintonSessions = ref([])
const loadingBadminton = ref(false)
const badmintonPage = ref(0)
const badmintonTotal = ref(0)

// MoveMatch Challenges (paginated)
const mimicChallenges = ref([])
const loadingMimicChallenges = ref(false)
const mimicChallengesPage = ref(0)
const mimicChallengesTotal = ref(0)

// MoveMatch Sessions (paginated)
const mimicSessions = ref([])
const loadingMimicSessions = ref(false)
const mimicSessionsPage = ref(0)
const mimicSessionsTotal = ref(0)

// MoveMatch video modal
const mimicVideoModal = ref({ open: false, sessionId: null, username: '', src: null, loading: false })
const mimicVideoEl = ref(null)

// MoveMatch details modal
const mimicDetailsModal = ref({ open: false, loading: false, data: null, sessionId: null })

// MoveMatch screenshot modal
const mimicSsModal = ref({ open: false, sessionId: null, loading: false, loadingMore: false, total: 0 })
const mimicSsDownloading = ref(false)
const mimicSsCurrentPage = ref(1)
const mimicSsJumpPage = ref(1)
const mimicSsPageCache = ref({})
const MIMIC_SS_PAGE_SIZE = 10
const mimicSsTotalPages = computed(() => Math.ceil(mimicSsModal.value.total / MIMIC_SS_PAGE_SIZE) || 1)
const mimicSsPageEntries = computed(() => mimicSsPageCache.value[mimicSsCurrentPage.value] || [])

onMounted(async () => {
  if (isAdmin.value) {
    await Promise.all([loadCodes(), loadWhitelist(), loadWaitlist(), loadUsers()])
  }
})

watch(activeTab, (tab) => {
  if (tab === 'feature-access' && featureAccess.value.length === 0) {
    loadFeatureAccess()
  }
  if (tab === 'feature-requests' && featureRequests.value.length === 0) {
    loadFeatureRequests()
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
  if (tab === 'mimic-challenges' && mimicChallenges.value.length === 0) {
    loadMimicChallenges()
  }
  if (tab === 'mimic-sessions' && mimicSessions.value.length === 0) {
    loadMimicSessions()
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

// ---------- Feature Requests ----------

async function loadFeatureRequests() {
  loadingFeatureRequests.value = true
  try {
    const params = featureRequestFilter.value ? { status: featureRequestFilter.value } : {}
    const response = await api.get('/api/v1/admin/feature-requests', { params })
    featureRequests.value = response.data.requests
  } catch (err) {
    console.error('Failed to load feature requests:', err)
  } finally {
    loadingFeatureRequests.value = false
  }
}

async function approveFeatureRequest(req) {
  try {
    await api.post(`/api/v1/admin/feature-requests/${req.id}/approve`)
    await loadFeatureRequests()
  } catch (err) {
    console.error('Failed to approve feature request:', err)
  }
}

async function rejectFeatureRequest(req) {
  try {
    await api.post(`/api/v1/admin/feature-requests/${req.id}/reject`)
    await loadFeatureRequests()
  } catch (err) {
    console.error('Failed to reject feature request:', err)
  }
}

function openReviewModal(req) {
  reviewModal.value = { show: true, req, message: '', sending: false }
}

async function submitReview() {
  const { req, message } = reviewModal.value
  if (!req || !message.trim()) return
  reviewModal.value.sending = true
  try {
    await api.post(`/api/v1/admin/feature-requests/${req.id}/review`, { message: message.trim() })
    reviewModal.value.show = false
    await loadFeatureRequests()
  } catch (err) {
    console.error('Failed to submit review:', err)
  } finally {
    reviewModal.value.sending = false
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

async function downloadRecording(sessionId) {
  try {
    const response = await api.get(`/api/v1/challenges/admin/sessions/${sessionId}/recording`, { responseType: 'blob' })
    const url = URL.createObjectURL(response.data)
    const a = document.createElement('a')
    a.href = url
    a.download = `challenge_recording_${sessionId}.mp4`
    a.click()
    URL.revokeObjectURL(url)
  } catch (err) {
    console.error('Failed to download recording:', err)
  }
}

const SS_PAGE_SIZE = 10
const ssJumpPage = ref(1)
const ssCurrentPage = ref(1)
const ssPageCache = ref({}) // page number -> [{idx, src}]

const ssTotalPages = computed(() => Math.ceil(screenshotModal.value.total / SS_PAGE_SIZE) || 1)

const ssPageEntries = computed(() => ssPageCache.value[ssCurrentPage.value] || [])

async function viewScreenshots(sessionId, count) {
  // Revoke old object URLs
  for (const entries of Object.values(ssPageCache.value)) {
    for (const e of entries) URL.revokeObjectURL(e.src)
  }
  ssPageCache.value = {}
  ssCurrentPage.value = 1
  ssJumpPage.value = 1
  screenshotModal.value = { open: true, sessionId, images: {}, loading: true, loadingMore: false, total: count }
  try {
    await ssLoadPage(1)
  } catch (err) {
    console.error('Failed to load screenshots:', err)
  }
  screenshotModal.value.loading = false
}

async function ssLoadPage(page) {
  if (ssPageCache.value[page]) return // already cached
  const modal = screenshotModal.value
  const start = (page - 1) * SS_PAGE_SIZE
  const end = Math.min(start + SS_PAGE_SIZE, modal.total)
  const entries = []
  for (let i = start; i < end; i++) {
    const res = await api.get(
      `/api/v1/challenges/admin/sessions/${modal.sessionId}/screenshots/${i}`,
      { responseType: 'blob' }
    )
    entries.push({ idx: i, src: URL.createObjectURL(res.data) })
  }
  ssPageCache.value = { ...ssPageCache.value, [page]: entries }
}

async function ssGoToPage(page) {
  page = Math.max(1, Math.min(page, ssTotalPages.value))
  if (page === ssCurrentPage.value && ssPageCache.value[page]) return
  screenshotModal.value.loadingMore = true
  try {
    await ssLoadPage(page)
    ssCurrentPage.value = page
    ssJumpPage.value = page
  } catch (err) {
    console.error('Failed to load screenshot page:', err)
  }
  screenshotModal.value.loadingMore = false
}

const ssDownloading = ref(false)

async function downloadAllScreenshots() {
  const sid = screenshotModal.value.sessionId
  ssDownloading.value = true
  try {
    const res = await api.get(
      `/api/v1/challenges/admin/sessions/${sid}/screenshots/download`,
      { responseType: 'blob' }
    )
    const url = URL.createObjectURL(res.data)
    const a = document.createElement('a')
    a.href = url
    a.download = `session_${sid}_screenshots.zip`
    a.click()
    URL.revokeObjectURL(url)
  } catch (err) {
    console.error('Failed to download screenshots:', err)
  }
  ssDownloading.value = false
}

// ---------- MoveMatch Challenges ----------

async function loadMimicChallenges() {
  loadingMimicChallenges.value = true
  try {
    const params = { offset: mimicChallengesPage.value * PAGE_SIZE, limit: PAGE_SIZE }
    const response = await api.get('/api/v1/mimic/admin/challenges', { params })
    mimicChallenges.value = response.data.challenges
    mimicChallengesTotal.value = response.data.total
  } catch (err) {
    console.error('Failed to load mimic challenges:', err)
  } finally {
    loadingMimicChallenges.value = false
  }
}

function mimicChallengesPageChange(dir) {
  mimicChallengesPage.value += dir
  loadMimicChallenges()
}

async function toggleMimicPublic(ch) {
  try {
    const res = await api.put(`/api/v1/mimic/admin/challenges/${ch.id}/public`)
    ch.is_public = res.data.is_public
  } catch (err) {
    console.error('Failed to toggle public:', err)
  }
}

async function toggleMimicTrending(ch) {
  try {
    const res = await api.put(`/api/v1/mimic/admin/challenges/${ch.id}/trending`)
    ch.is_trending = res.data.is_trending
  } catch (err) {
    console.error('Failed to toggle trending:', err)
  }
}

async function deleteMimicChallenge(ch) {
  if (!confirm(`Delete "${ch.title}"? This will remove all sessions, records, and files.`)) return
  try {
    await api.delete(`/api/v1/mimic/admin/challenges/${ch.id}`)
    await loadMimicChallenges()
  } catch (err) {
    console.error('Failed to delete mimic challenge:', err)
  }
}

// ---------- MoveMatch Sessions ----------

async function loadMimicSessions() {
  loadingMimicSessions.value = true
  try {
    const params = { offset: mimicSessionsPage.value * PAGE_SIZE, limit: PAGE_SIZE }
    const response = await api.get('/api/v1/mimic/admin/sessions', { params })
    mimicSessions.value = response.data.sessions
    mimicSessionsTotal.value = response.data.total
  } catch (err) {
    console.error('Failed to load mimic sessions:', err)
  } finally {
    loadingMimicSessions.value = false
  }
}

function mimicSessionsPageChange(dir) {
  mimicSessionsPage.value += dir
  loadMimicSessions()
}

async function viewMimicScreenshots(sessionId, count) {
  for (const entries of Object.values(mimicSsPageCache.value)) {
    for (const e of entries) URL.revokeObjectURL(e.src)
  }
  mimicSsPageCache.value = {}
  mimicSsCurrentPage.value = 1
  mimicSsJumpPage.value = 1
  mimicSsModal.value = { open: true, sessionId, loading: true, loadingMore: false, total: count }
  try {
    await mimicSsLoadPage(1)
  } catch (err) {
    console.error('Failed to load mimic screenshots:', err)
  }
  mimicSsModal.value.loading = false
}

async function mimicSsLoadPage(page) {
  if (mimicSsPageCache.value[page]) return
  const modal = mimicSsModal.value
  const start = (page - 1) * MIMIC_SS_PAGE_SIZE
  const end = Math.min(start + MIMIC_SS_PAGE_SIZE, modal.total)
  const entries = []
  for (let i = start; i < end; i++) {
    const res = await api.get(
      `/api/v1/mimic/admin/sessions/${modal.sessionId}/screenshots/${i}`,
      { responseType: 'blob' }
    )
    entries.push({ idx: i, src: URL.createObjectURL(res.data) })
  }
  mimicSsPageCache.value = { ...mimicSsPageCache.value, [page]: entries }
}

async function mimicSsGoToPage(page) {
  page = Math.max(1, Math.min(page, mimicSsTotalPages.value))
  if (page === mimicSsCurrentPage.value && mimicSsPageCache.value[page]) return
  mimicSsModal.value.loadingMore = true
  try {
    await mimicSsLoadPage(page)
    mimicSsCurrentPage.value = page
    mimicSsJumpPage.value = page
  } catch (err) {
    console.error('Failed to load mimic screenshot page:', err)
  }
  mimicSsModal.value.loadingMore = false
}

async function downloadMimicScreenshots() {
  const sid = mimicSsModal.value.sessionId
  mimicSsDownloading.value = true
  try {
    const res = await api.get(
      `/api/v1/mimic/admin/sessions/${sid}/screenshots/download`,
      { responseType: 'blob' }
    )
    const url = URL.createObjectURL(res.data)
    const a = document.createElement('a')
    a.href = url
    a.download = `mimic_session_${sid}_screenshots.zip`
    a.click()
    URL.revokeObjectURL(url)
  } catch (err) {
    console.error('Failed to download mimic screenshots:', err)
  }
  mimicSsDownloading.value = false
}

async function downloadMimicUpload(session) {
  try {
    const res = await api.get(
      `/api/v1/mimic/admin/sessions/${session.id}/uploaded-video`,
      { responseType: 'blob' }
    )
    const url = URL.createObjectURL(res.data)
    const a = document.createElement('a')
    a.href = url
    a.download = `mimic_upload_${session.id}.mp4`
    a.click()
    URL.revokeObjectURL(url)
  } catch (err) {
    console.error('Failed to download uploaded video:', err)
  }
}

async function openMimicVideo(session) {
  mimicVideoModal.value = { open: true, sessionId: session.id, username: session.username || '', src: null, loading: true }
  try {
    const res = await api.get(
      `/api/v1/mimic/admin/sessions/${session.id}/comparison-video`,
      { responseType: 'blob' }
    )
    mimicVideoModal.value.src = URL.createObjectURL(res.data)
  } catch (err) {
    console.error('Failed to load comparison video:', err)
  } finally {
    mimicVideoModal.value.loading = false
  }
}

function closeMimicVideo() {
  // Revoke blob URL and stop playback
  if (mimicVideoModal.value.src) {
    URL.revokeObjectURL(mimicVideoModal.value.src)
  }
  if (mimicVideoEl.value) {
    mimicVideoEl.value.pause()
  }
  mimicVideoModal.value = { open: false, sessionId: null, username: '', src: null, loading: false }
}

async function openMimicDetails(session) {
  mimicDetailsModal.value = { open: true, loading: true, data: null, sessionId: session.id }
  try {
    const res = await api.get(`/api/v1/mimic/admin/sessions/${session.id}/details`)
    mimicDetailsModal.value.data = res.data
  } catch (err) {
    console.error('Failed to load session details:', err)
    mimicDetailsModal.value.data = null
  } finally {
    mimicDetailsModal.value.loading = false
  }
}

function scoreColor(score) {
  if (score >= 80) return '#22c55e'
  if (score >= 60) return '#eab308'
  if (score >= 40) return '#f97316'
  return '#ef4444'
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

.status.review {
  background: rgba(59, 130, 246, 0.2);
  color: #3b82f6;
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

.btn-small.btn-review {
  background: rgba(59, 130, 246, 0.2);
  color: #3b82f6;
}

.btn-small.btn-review:hover {
  background: rgba(59, 130, 246, 0.3);
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

.modal-header-actions {
  display: flex;
  align-items: center;
  gap: 0.75rem;
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

.screenshots-nav {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
  padding-bottom: 0.75rem;
  border-bottom: 1px solid var(--border-color);
}

.screenshots-count {
  color: var(--text-muted);
  font-size: 0.85rem;
}

.screenshots-page-controls {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.screenshots-jump {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.screenshots-jump label {
  color: var(--text-muted);
  font-size: 0.85rem;
  white-space: nowrap;
}

.jump-input {
  width: 70px;
  padding: 0.3rem 0.5rem;
  background: var(--bg-input);
  border: 1px solid var(--border-input);
  border-radius: var(--radius-sm);
  color: var(--text-primary);
  font-size: 0.85rem;
}

/* Video modal */
.video-panel {
  max-width: 960px;
  width: 95vw;
}

.mimic-video-player {
  width: 100%;
  max-height: 70vh;
  border-radius: var(--radius-md);
  background: #000;
}

/* Details modal */
.details-panel {
  max-width: 600px;
  width: 95vw;
  max-height: 90vh;
  overflow-y: auto;
}

.detail-score-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 0.75rem;
  margin-bottom: 1.25rem;
}

.detail-score-card {
  background: var(--bg-input);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 0.75rem;
  text-align: center;
}

.detail-score-label {
  display: block;
  color: var(--text-muted);
  font-size: 0.75rem;
  margin-bottom: 0.25rem;
}

.detail-score-value {
  display: block;
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--text-primary);
}

.detail-feedback {
  background: var(--bg-input);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 1rem;
  margin-bottom: 1rem;
}

.detail-feedback h4 {
  margin: 0 0 0.5rem;
  color: var(--text-muted);
  font-size: 0.85rem;
}

.feedback-summary {
  margin: 0 0 0.75rem;
  color: var(--text-primary);
  font-size: 0.9rem;
  line-height: 1.5;
}

.feedback-items {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.feedback-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.5rem 0.75rem;
  border-radius: var(--radius-sm);
  font-size: 0.85rem;
}

.feedback-region {
  font-weight: 600;
  text-transform: capitalize;
  min-width: 80px;
}

.feedback-message {
  color: var(--text-primary);
}

.feedback-good {
  background: rgba(34, 197, 94, 0.1);
  border-left: 3px solid #22c55e;
}

.feedback-needs_work {
  background: rgba(234, 179, 8, 0.1);
  border-left: 3px solid #eab308;
}

.feedback-poor {
  background: rgba(239, 68, 68, 0.1);
  border-left: 3px solid #ef4444;
}

.detail-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  color: var(--text-muted);
  font-size: 0.85rem;
}

.detail-meta strong {
  color: var(--text-secondary);
}
</style>
