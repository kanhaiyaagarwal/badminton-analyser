<template>
  <div class="pre-workout">
    <!-- Top bar with back button -->
    <div class="pre-workout-topbar">
      <button class="back-btn" @click="handleBack">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" width="20" height="20" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"/></svg>
      </button>
      <h2 class="topbar-title">{{ data.day_label || "Today's Workout" }}</h2>
      <button class="edit-toggle" @click="editing = !editing">
        {{ editing ? 'Done' : 'Edit' }}
      </button>
    </div>

    <!-- Exercise plan (top, scrollable) -->
    <div class="plan-section">
      <div class="exercise-list">
        <div
          v-for="(ex, i) in localExercises"
          :key="ex.exercise_id || ex.slug || i"
          class="exercise-item"
          :class="{ 'editing-item': editing }"
        >
          <!-- Move buttons (edit mode) -->
          <div v-if="editing" class="move-btns">
            <button class="move-btn" :disabled="i === 0" @click="moveExercise(i, -1)">
              <svg viewBox="0 0 24 24" fill="currentColor" width="16" height="16"><path d="M7.41 15.41L12 10.83l4.59 4.58L18 14l-6-6-6 6z"/></svg>
            </button>
            <button class="move-btn" :disabled="i === localExercises.length - 1" @click="moveExercise(i, 1)">
              <svg viewBox="0 0 24 24" fill="currentColor" width="16" height="16"><path d="M7.41 8.59L12 13.17l4.59-4.58L18 10l-6 6-6-6z"/></svg>
            </button>
          </div>

          <span v-if="!editing" class="exercise-num">{{ i + 1 }}</span>

          <div class="exercise-info" :class="{ clickable: !editing }" @click="!editing && viewExercise(ex.slug)">
            <span class="exercise-name">{{ ex.name }}</span>
            <div v-if="!editing" class="exercise-detail">
              {{ ex.sets }}x{{ ex.reps }}{{ ex.weight_kg ? ` @ ${ex.weight_kg}kg` : '' }}
            </div>
            <!-- Editable sets/reps (edit mode) -->
            <div v-else class="exercise-edit-row">
              <div class="edit-field">
                <label>Sets</label>
                <div class="stepper">
                  <button class="stepper-btn" @click="adjustSets(i, -1)">−</button>
                  <span class="stepper-val">{{ ex.sets }}</span>
                  <button class="stepper-btn" @click="adjustSets(i, 1)">+</button>
                </div>
              </div>
              <div class="edit-field">
                <label>Reps</label>
                <input
                  class="reps-input"
                  :value="ex.reps"
                  @change="updateReps(i, $event.target.value)"
                />
              </div>
            </div>
          </div>

          <!-- Delete button (edit mode) -->
          <button v-if="editing" class="delete-btn" @click="removeExercise(i)" :disabled="localExercises.length <= 1">
            <svg viewBox="0 0 24 24" fill="currentColor" width="18" height="18"><path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/></svg>
          </button>
        </div>
      </div>

      <!-- Add exercise (edit mode) -->
      <div v-if="editing" class="add-exercise-section">
        <div v-if="!showAddPicker" class="add-exercise-btn" @click="openAddPicker">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
          Add Exercise
        </div>
        <div v-else class="add-picker">
          <input
            ref="addSearchInput"
            v-model="addSearch"
            class="add-search-input"
            placeholder="Search exercises..."
            @input="searchExercises"
          />
          <div v-if="addResults.length" class="add-results">
            <button
              v-for="ex in addResults"
              :key="ex.slug"
              class="add-result-item"
              @click="addExercise(ex)"
            >
              <span class="add-result-name">{{ ex.name }}</span>
              <span class="add-result-muscle">{{ ex.primary_muscle }}</span>
            </button>
          </div>
          <button class="add-cancel" @click="showAddPicker = false">Cancel</button>
        </div>
      </div>

      <div class="plan-meta">
        <span>{{ localExercises.length }} exercises</span>
        <span>~{{ data.estimated_minutes || localExercises.length * 5 }} min</span>
      </div>
    </div>

    <!-- Chat area (bottom) -->
    <div class="chat-section">
      <CoachChat
        ref="chatRef"
        context="pre_workout"
        :session-id="sessionId"
        :initial-message="coachSays || null"
        compact
        @action="handleChatAction"
      />
    </div>

    <!-- Quick actions + Begin button -->
    <div class="pre-workout-actions">
      <div class="quick-buttons">
        <button class="quick-btn" @click="sendQuickAction('swap_exercise')">Swap</button>
        <button class="quick-btn" @click="sendQuickAction('make_shorter')">Shorter</button>
        <button class="quick-btn" @click="sendQuickAction('make_longer')">Longer</button>
        <button
          class="quick-btn"
          :class="{ 'quick-btn-active': locationMode === 'home' }"
          @click="toggleLocation"
        >
          {{ locationMode === 'home' ? 'Back to Gym' : 'Home Workout' }}
        </button>
      </div>
      <button class="btn-primary full-width begin-btn" @click="handleBegin" :disabled="saving">
        {{ saving ? 'Saving...' : 'Begin Workout' }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import CoachChat from '../../../components/workout/CoachChat.vue'
import { useWorkoutStore } from '../../../stores/workout'
import api from '../../../api/client'

const props = defineProps({
  data: { type: Object, required: true },
  coachSays: { type: String, default: '' },
  sessionId: { type: String, default: null },
  startInEdit: { type: Boolean, default: false },
})

const emit = defineEmits(['action'])
const router = useRouter()
const workoutStore = useWorkoutStore()

const editing = ref(props.startInEdit)
const locationMode = ref('gym') // 'gym' | 'home'
const saving = ref(false)
const planDirty = ref(false)

// Local mutable copy of exercises
const localExercises = ref([])

// Initialize from props
watch(() => props.data.exercises, (exercises) => {
  if (exercises?.length && !planDirty.value) {
    localExercises.value = JSON.parse(JSON.stringify(exercises))
  }
}, { immediate: true })

const chatRef = ref(null)

function moveExercise(index, direction) {
  const target = index + direction
  if (target < 0 || target >= localExercises.value.length) return
  const list = [...localExercises.value]
  const item = list.splice(index, 1)[0]
  list.splice(target, 0, item)
  localExercises.value = list
  planDirty.value = true
}

function adjustSets(index, delta) {
  const ex = localExercises.value[index]
  const newSets = Math.max(1, (ex.sets || 3) + delta)
  localExercises.value[index] = { ...ex, sets: newSets }
  planDirty.value = true
}

function updateReps(index, value) {
  const ex = localExercises.value[index]
  localExercises.value[index] = { ...ex, reps: value || ex.reps }
  planDirty.value = true
}

function removeExercise(index) {
  if (localExercises.value.length <= 1) return
  localExercises.value.splice(index, 1)
  planDirty.value = true
}

// --- Add exercise ---
const showAddPicker = ref(false)
const addSearch = ref('')
const addResults = ref([])
const addSearchInput = ref(null)
let searchTimeout = null

async function openAddPicker() {
  showAddPicker.value = true
  addSearch.value = ''
  addResults.value = []
  await nextTick()
  addSearchInput.value?.focus()
}

function searchExercises() {
  clearTimeout(searchTimeout)
  const q = addSearch.value.trim()
  if (q.length < 2) { addResults.value = []; return }
  searchTimeout = setTimeout(async () => {
    try {
      const res = await api.get('/api/v1/workout/exercises', { params: { search: q, limit: 8 } })
      const currentSlugs = new Set(localExercises.value.map(e => e.slug))
      addResults.value = res.data.filter(e => !currentSlugs.has(e.slug))
    } catch { addResults.value = [] }
  }, 250)
}

function addExercise(ex) {
  localExercises.value.push({
    slug: ex.slug,
    name: ex.name,
    exercise_id: ex.id,
    sets: 3,
    reps: '10',
    order: localExercises.value.length,
  })
  planDirty.value = true
  showAddPicker.value = false
  addSearch.value = ''
  addResults.value = []
}

async function savePlan() {
  if (!planDirty.value || !props.sessionId) return
  saving.value = true
  try {
    await workoutStore.sendAction(props.sessionId, 'update_plan', {
      exercises: localExercises.value.map((ex, i) => ({
        exercise_id: ex.exercise_id,
        slug: ex.slug,
        name: ex.name,
        sets: ex.sets,
        reps: ex.reps,
      })),
    })
    planDirty.value = false
  } catch (err) {
    console.error('Failed to save plan:', err)
  } finally {
    saving.value = false
  }
}

function handleChatAction(type, params) {
  if (type === 'begin_workout') {
    handleBegin()
    return
  }
  if (type === 'plan_updated' && params?.exercises) {
    // Chat modified the plan — refresh local exercises
    localExercises.value = JSON.parse(JSON.stringify(params.exercises))
    planDirty.value = false
    return
  }
  emit('action', type, params)
}

async function handleBegin() {
  // Save any pending changes before starting
  if (planDirty.value) {
    await savePlan()
  }
  emit('action', 'begin_workout')
}

function handleBack() {
  workoutStore.clearSession()
  router.push('/workout')
}

function viewExercise(slug) {
  if (slug) router.push(`/workout/exercises/${slug}`)
}

const originalExercises = ref(null) // stash gym plan for "Back to Gym"

async function toggleLocation() {
  if (locationMode.value === 'gym') {
    // Switch to home — stash original, swap exercises via API
    originalExercises.value = JSON.parse(JSON.stringify(localExercises.value))
    locationMode.value = 'home'
    try {
      const { data: result } = await import('../../../api/client').then(m =>
        m.default.post('/api/v1/workout/chat', {
          message: 'Switch to a home workout — only bodyweight and minimal equipment',
          context: 'pre_workout',
          session_id: props.sessionId,
        })
      )
      if (result.actions?.length) {
        for (const action of result.actions) {
          if (action.type === 'plan_updated' && action.params?.exercises) {
            localExercises.value = JSON.parse(JSON.stringify(action.params.exercises))
            planDirty.value = true
          }
        }
      }
    } catch (e) {
      console.error('Home workout switch failed:', e)
    }
  } else {
    // Switch back to gym — restore original
    locationMode.value = 'gym'
    if (originalExercises.value) {
      localExercises.value = JSON.parse(JSON.stringify(originalExercises.value))
      planDirty.value = true
    }
  }
}

function sendQuickAction(action) {
  const messages = {
    swap_exercise: "I'd like to swap an exercise",
    make_shorter: "Can you make the workout shorter?",
    make_longer: "Can you add another exercise to make the workout longer?",
  }
  const msg = messages[action] || action
  if (chatRef.value) {
    chatRef.value.sendFromParent(msg)
  }
}

// Auto-save when exiting edit mode
watch(editing, (isEditing, wasEditing) => {
  if (!isEditing && wasEditing && planDirty.value) {
    savePlan()
  }
})
</script>

<style scoped>
.pre-workout {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  min-height: 100dvh;
}

/* Top bar */
.pre-workout-topbar {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.65rem 1rem;
  border-bottom: 1px solid var(--border-color);
  flex-shrink: 0;
}

.back-btn {
  width: 36px;
  height: 36px;
  border: none;
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  flex-shrink: 0;
  transition: background 0.15s;
}

.back-btn:hover {
  background: var(--color-primary-light);
  color: var(--color-primary);
}

.topbar-title {
  flex: 1;
  font-size: 1rem;
  font-weight: 700;
  color: var(--text-primary);
}

/* Plan section */
.plan-section {
  padding: 0.75rem 1.25rem;
  flex-shrink: 0;
}

.edit-toggle {
  padding: 0.3rem 0.75rem;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-full);
  background: transparent;
  color: var(--color-primary);
  font-size: 0.75rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.edit-toggle:hover {
  background: var(--color-primary-light);
}

.exercise-list {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  margin-bottom: 0.5rem;
}

.exercise-item {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  padding: 0.6rem 0.75rem;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  transition: all 0.2s;
}

.editing-item {
  border-color: var(--color-primary-light);
}

.exercise-num {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: var(--color-primary-light);
  color: var(--color-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.7rem;
  font-weight: 700;
  flex-shrink: 0;
}

.exercise-info {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 0;
}

.exercise-info.clickable {
  cursor: pointer;
}

.exercise-info.clickable:hover .exercise-name {
  color: var(--color-primary);
}

.exercise-name {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--text-primary);
}

.exercise-detail {
  font-size: 0.7rem;
  color: var(--text-muted);
}

/* Move buttons */
.move-btns {
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex-shrink: 0;
}

.move-btn {
  width: 24px;
  height: 20px;
  border: none;
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  transition: all 0.15s;
  padding: 0;
}

.move-btn:hover:not(:disabled) {
  background: var(--color-primary-light);
  color: var(--color-primary);
}

.move-btn:disabled {
  opacity: 0.2;
  cursor: default;
}

/* Edit row */
.exercise-edit-row {
  display: flex;
  gap: 0.75rem;
  margin-top: 0.35rem;
}

.edit-field {
  display: flex;
  align-items: center;
  gap: 0.35rem;
}

.edit-field label {
  font-size: 0.65rem;
  color: var(--text-muted);
  text-transform: uppercase;
  font-weight: 600;
}

.stepper {
  display: flex;
  align-items: center;
  gap: 0;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.stepper-btn {
  width: 28px;
  height: 28px;
  border: none;
  background: transparent;
  color: var(--color-primary);
  font-size: 1rem;
  font-weight: 700;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.15s;
}

.stepper-btn:hover {
  background: var(--color-primary-light);
}

.stepper-val {
  min-width: 24px;
  text-align: center;
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--text-primary);
}

.reps-input {
  width: 48px;
  padding: 0.25rem 0.4rem;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  background: transparent;
  color: var(--text-primary);
  font-size: 0.8rem;
  text-align: center;
  outline: none;
}

.reps-input:focus {
  border-color: var(--color-primary);
}

/* Delete button */
.delete-btn {
  width: 32px;
  height: 32px;
  border: none;
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  flex-shrink: 0;
  transition: all 0.15s;
}

.delete-btn:hover:not(:disabled) {
  color: var(--color-destructive, #dc2626);
  background: rgba(220, 38, 38, 0.1);
}

.delete-btn:disabled {
  opacity: 0.2;
  cursor: default;
}

.plan-meta {
  display: flex;
  justify-content: space-between;
  font-size: 0.75rem;
  color: var(--text-muted);
}

/* Add exercise */
.add-exercise-section {
  margin-top: 0.4rem;
}

.add-exercise-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.35rem;
  padding: 0.5rem;
  border: 1px dashed var(--border-color);
  border-radius: var(--radius-md);
  color: var(--text-muted);
  font-size: 0.8rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
}

.add-exercise-btn:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.add-picker {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.add-search-input {
  width: 100%;
  padding: 0.5rem 0.65rem;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  background: var(--bg-input);
  color: var(--text-primary);
  font-size: 0.8rem;
  outline: none;
}

.add-search-input:focus {
  border-color: var(--color-primary);
}

.add-results {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
  max-height: 180px;
  overflow-y: auto;
}

.add-result-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.45rem 0.6rem;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  background: var(--bg-card);
  cursor: pointer;
  transition: border-color 0.15s;
}

.add-result-item:hover {
  border-color: var(--color-primary);
}

.add-result-name {
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--text-primary);
}

.add-result-muscle {
  font-size: 0.7rem;
  color: var(--text-muted);
}

.add-cancel {
  padding: 0.35rem;
  border: none;
  background: transparent;
  color: var(--text-muted);
  font-size: 0.75rem;
  cursor: pointer;
  text-decoration: underline;
}

/* Chat section */
.chat-section {
  flex: 1;
  min-height: 0;
  border-top: 1px solid var(--border-color);
}

/* Actions */
.pre-workout-actions {
  padding: 0.75rem 1.25rem;
  padding-bottom: calc(0.75rem + env(safe-area-inset-bottom, 0px));
  border-top: 1px solid var(--border-color);
  background: var(--bg-card);
}

.quick-buttons {
  display: flex;
  gap: 0.4rem;
  margin-bottom: 0.5rem;
}

.quick-btn {
  flex: 1;
  padding: 0.45rem 0.5rem;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-full);
  background: transparent;
  color: var(--text-secondary);
  font-size: 0.75rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.quick-btn:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.quick-btn-active {
  background: var(--color-primary);
  color: var(--text-on-primary);
  border-color: var(--color-primary);
}

.quick-btn-active:hover {
  opacity: 0.9;
  color: var(--text-on-primary);
}

.begin-btn {
  padding: 0.85rem;
}

.btn-primary {
  display: block;
  width: 100%;
  padding: 0.85rem 1.25rem;
  background: var(--gradient-primary);
  color: white;
  border: none;
  border-radius: var(--radius-md);
  font-weight: 600;
  font-size: 1rem;
  cursor: pointer;
  transition: opacity 0.2s;
}

.btn-primary:hover { opacity: 0.9; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.full-width { width: 100%; }
</style>
