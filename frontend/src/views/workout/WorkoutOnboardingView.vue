<template>
  <div class="onboarding">
    <!-- Progress dots -->
    <div class="progress-dots">
      <span
        v-for="s in totalSteps"
        :key="s"
        class="dot"
        :class="{ active: s === step, done: s < step }"
      />
    </div>

    <!-- Step 1: Welcome -->
    <div v-if="step === 1" class="step-content" key="step1">
      <div class="welcome-mascot">
        <img src="/mascot/otter-mascot.png" alt="Coach" class="mascot-img" />
      </div>
      <h1 class="step-title">Let's Build Your Plan</h1>
      <p class="step-desc">
        Tell me about yourself and I'll create a personalized workout plan
        tailored to your goals and schedule.
      </p>
      <div class="welcome-actions">
        <button class="btn-primary" @click="step = 2">Set Up My Plan</button>
        <button class="btn-ghost" @click="skipToWorkout">Just Start Working Out</button>
      </div>
    </div>

    <!-- Step 2: About You -->
    <div v-if="step === 2" class="step-content" key="step2">
      <h2 class="step-title">About You</h2>
      <p class="step-desc">This helps me calibrate your plan.</p>

      <label class="field-label">Fitness Level</label>
      <div class="card-options">
        <button
          v-for="level in fitnessLevels"
          :key="level.value"
          class="option-card"
          :class="{ selected: form.fitness_level === level.value }"
          @click="form.fitness_level = level.value"
        >
          <span class="option-icon">{{ level.icon }}</span>
          <span class="option-label">{{ level.label }}</span>
          <span class="option-desc">{{ level.desc }}</span>
        </button>
      </div>

      <div class="field-row">
        <div class="field">
          <label class="field-label">Age <span class="optional">(optional)</span></label>
          <input v-model.number="form.age" type="number" min="13" max="100" class="input" placeholder="25" />
        </div>
      </div>

      <div class="field-row">
        <div class="field">
          <label class="field-label">Height (cm) <span class="optional">(optional)</span></label>
          <input v-model.number="form.height_cm" type="number" min="100" max="250" class="input" placeholder="175" />
        </div>
        <div class="field">
          <label class="field-label">Weight (kg) <span class="optional">(optional)</span></label>
          <input v-model.number="form.weight_kg" type="number" min="30" max="300" class="input" placeholder="70" />
        </div>
      </div>

      <div class="field">
        <label class="field-label">Injuries / Limitations <span class="optional">(optional)</span></label>
        <input v-model="injuriesText" type="text" class="input" placeholder="e.g. lower back, knee" />
      </div>
    </div>

    <!-- Step 3: Goals -->
    <div v-if="step === 3" class="step-content" key="step3">
      <h2 class="step-title">Your Goals</h2>
      <p class="step-desc">Select all that apply.</p>

      <div class="goal-cards">
        <button
          v-for="goal in goalOptions"
          :key="goal.value"
          class="goal-card"
          :class="{ selected: form.goals.includes(goal.value) }"
          @click="toggleGoal(goal.value)"
        >
          <span class="goal-icon">{{ goal.icon }}</span>
          <span class="goal-label">{{ goal.label }}</span>
        </button>
      </div>
    </div>

    <!-- Step 4: Schedule -->
    <div v-if="step === 4" class="step-content" key="step4">
      <h2 class="step-title">Your Schedule</h2>
      <p class="step-desc">When and where do you train?</p>

      <label class="field-label">Training Days</label>
      <div class="day-picker">
        <button
          v-for="d in dayOptions"
          :key="d.value"
          class="day-circle"
          :class="{ selected: form.preferred_days.includes(d.value) }"
          @click="toggleDay(d.value)"
        >
          {{ d.short }}
        </button>
      </div>

      <label class="field-label">Session Length</label>
      <div class="pill-options">
        <button
          v-for="dur in durationOptions"
          :key="dur"
          class="pill"
          :class="{ selected: form.session_duration_minutes === dur }"
          @click="form.session_duration_minutes = dur"
        >
          {{ dur }} min
        </button>
      </div>

      <label class="field-label">Location</label>
      <div class="pill-options">
        <button
          class="pill"
          :class="{ selected: form.train_location === 'gym' }"
          @click="form.train_location = 'gym'"
        >
          Gym
        </button>
        <button
          class="pill"
          :class="{ selected: form.train_location === 'home' }"
          @click="form.train_location = 'home'"
        >
          Home
        </button>
      </div>

      <div v-if="form.train_location === 'gym' || form.train_location === 'home'" class="field">
        <label class="field-label">Available Equipment <span class="optional">(optional)</span></label>
        <div class="equipment-checks">
          <label
            v-for="eq in equipmentOptions"
            :key="eq"
            class="check-label"
          >
            <input
              type="checkbox"
              :checked="(form.available_equipment || []).includes(eq)"
              @change="toggleEquipment(eq)"
            />
            {{ eq }}
          </label>
        </div>
      </div>
    </div>

    <!-- Step 5: Plan Preview -->
    <div v-if="step === 5" class="step-content" key="step5">
      <h2 class="step-title">Your Plan</h2>

      <div v-if="submitting" class="loading-state">
        <div class="spinner" />
        <p>Generating your plan...</p>
      </div>

      <div v-else-if="planResult">
        <div class="plan-card">
          <h3 class="plan-name">{{ planResult.plan_name }}</h3>
          <p class="plan-meta">{{ planResult.days_per_week }} days/week &middot; {{ planResult.split_type.replace('_', ' ') }}</p>
          <p class="plan-message">{{ planResult.message }}</p>
        </div>
        <button class="btn-primary full-width" @click="finishOnboarding">Looks Good!</button>
      </div>

      <div v-else-if="submitError" class="error-state">
        <p>{{ submitError }}</p>
        <button class="btn-ghost" @click="submitPlan">Try Again</button>
      </div>
    </div>

    <!-- Navigation -->
    <div v-if="step > 1 && step < 5" class="nav-bar">
      <button class="btn-ghost" @click="step--">Back</button>
      <button class="btn-primary" :disabled="!canProceed" @click="handleNext">
        {{ step === 4 ? 'Preview Plan' : 'Next' }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useWorkoutStore } from '../../stores/workout'

const router = useRouter()
const workoutStore = useWorkoutStore()

const totalSteps = 5
const step = ref(1)
const submitting = ref(false)
const submitError = ref(null)
const planResult = ref(null)
const injuriesText = ref('')

const form = ref({
  fitness_level: 'beginner',
  age: null,
  height_cm: null,
  weight_kg: null,
  goals: [],
  preferred_days: ['mon', 'wed', 'fri'],
  session_duration_minutes: 45,
  train_location: 'gym',
  available_equipment: [],
})

const fitnessLevels = [
  { value: 'beginner', label: 'Beginner', icon: '🌱', desc: 'New to training or getting back into it' },
  { value: 'intermediate', label: 'Intermediate', icon: '💪', desc: '6+ months consistent training' },
  { value: 'advanced', label: 'Advanced', icon: '🔥', desc: '2+ years, solid foundation' },
]

const goalOptions = [
  { value: 'build_muscle', label: 'Build Muscle', icon: '💪' },
  { value: 'lose_fat', label: 'Lose Fat', icon: '🔥' },
  { value: 'get_stronger', label: 'Get Stronger', icon: '🏋️' },
  { value: 'stay_active', label: 'Stay Active', icon: '🏃' },
]

const dayOptions = [
  { value: 'mon', short: 'M' },
  { value: 'tue', short: 'T' },
  { value: 'wed', short: 'W' },
  { value: 'thu', short: 'T' },
  { value: 'fri', short: 'F' },
  { value: 'sat', short: 'S' },
  { value: 'sun', short: 'S' },
]

const durationOptions = [20, 30, 45, 60]

const equipmentOptions = [
  'barbell', 'dumbbells', 'bench', 'squat rack', 'cable machine',
  'leg press machine', 'leg curl machine', 'yoga mat',
]

const canProceed = computed(() => {
  if (step.value === 2) return !!form.value.fitness_level
  if (step.value === 3) return form.value.goals.length > 0
  if (step.value === 4) return form.value.preferred_days.length > 0
  return true
})

function toggleGoal(goal) {
  const idx = form.value.goals.indexOf(goal)
  if (idx >= 0) form.value.goals.splice(idx, 1)
  else form.value.goals.push(goal)
}

function toggleDay(day) {
  const idx = form.value.preferred_days.indexOf(day)
  if (idx >= 0) form.value.preferred_days.splice(idx, 1)
  else form.value.preferred_days.push(day)
}

function toggleEquipment(eq) {
  if (!form.value.available_equipment) form.value.available_equipment = []
  const idx = form.value.available_equipment.indexOf(eq)
  if (idx >= 0) form.value.available_equipment.splice(idx, 1)
  else form.value.available_equipment.push(eq)
}

function skipToWorkout() {
  router.push('/workout')
}

async function handleNext() {
  if (step.value === 4) {
    step.value = 5
    await submitPlan()
  } else {
    step.value++
  }
}

async function submitPlan() {
  submitting.value = true
  submitError.value = null
  try {
    // Add injuries from text
    const payload = { ...form.value }
    if (injuriesText.value) {
      payload.injuries = injuriesText.value.split(',').map(s => s.trim()).filter(Boolean)
    }
    const result = await workoutStore.submitOnboarding(payload)
    planResult.value = result
  } catch (err) {
    submitError.value = err.response?.data?.detail || 'Failed to generate plan'
  } finally {
    submitting.value = false
  }
}

function finishOnboarding() {
  router.push('/workout')
}
</script>

<style scoped>
.onboarding {
  padding: 1.25rem;
  max-width: 100%;
}

/* Progress dots */
.progress-dots {
  display: flex;
  justify-content: center;
  gap: 0.5rem;
  margin-bottom: 1.5rem;
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--border-input);
  transition: all 0.3s;
}

.dot.active {
  background: var(--color-primary);
  width: 24px;
  border-radius: 4px;
}

.dot.done {
  background: var(--color-primary);
}

/* Steps */
.step-content {
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

.step-title {
  font-size: 1.4rem;
  font-weight: 800;
  color: var(--text-primary);
  margin-bottom: 0.35rem;
}

.step-desc {
  font-size: 0.875rem;
  color: var(--text-secondary);
  margin-bottom: 1.25rem;
  line-height: 1.5;
}

/* Welcome */
.welcome-mascot {
  text-align: center;
  margin-bottom: 1rem;
}

.mascot-img {
  width: 100px;
  height: 100px;
  border-radius: 50%;
  object-fit: cover;
}

.welcome-actions {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  margin-top: 1.5rem;
}

/* Cards / Options */
.card-options {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-bottom: 1.25rem;
}

.option-card {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.85rem 1rem;
  background: var(--bg-card);
  border: 2px solid var(--border-color);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all 0.2s;
  text-align: left;
}

.option-card.selected {
  border-color: var(--color-primary);
  background: var(--color-primary-light);
}

.option-icon {
  font-size: 1.25rem;
  flex-shrink: 0;
}

.option-label {
  font-weight: 600;
  font-size: 0.9rem;
  color: var(--text-primary);
}

.option-desc {
  font-size: 0.75rem;
  color: var(--text-muted);
  margin-left: auto;
}

/* Goals */
.goal-cards {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.75rem;
}

.goal-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.35rem;
  padding: 1.25rem 0.75rem;
  background: var(--bg-card);
  border: 2px solid var(--border-color);
  border-radius: var(--radius-lg);
  cursor: pointer;
  transition: all 0.2s;
}

.goal-card.selected {
  border-color: var(--color-primary);
  background: var(--color-primary-light);
}

.goal-icon {
  font-size: 1.5rem;
}

.goal-label {
  font-weight: 600;
  font-size: 0.85rem;
  color: var(--text-primary);
}

/* Day picker */
.day-picker {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1.25rem;
}

.day-circle {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  border: 2px solid var(--border-color);
  background: var(--bg-card);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 0.8rem;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.2s;
}

.day-circle.selected {
  border-color: var(--color-primary);
  background: var(--color-primary);
  color: white;
}

/* Pills */
.pill-options {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1.25rem;
  flex-wrap: wrap;
}

.pill {
  padding: 0.5rem 1rem;
  border-radius: var(--radius-full);
  border: 2px solid var(--border-color);
  background: var(--bg-card);
  font-size: 0.85rem;
  font-weight: 500;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.2s;
}

.pill.selected {
  border-color: var(--color-primary);
  background: var(--color-primary);
  color: white;
}

/* Equipment */
.equipment-checks {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.4rem;
}

.check-label {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.8rem;
  color: var(--text-secondary);
  cursor: pointer;
}

.check-label input[type="checkbox"] {
  accent-color: var(--color-primary);
}

/* Fields */
.field-label {
  display: block;
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 0.4rem;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.optional {
  font-weight: 400;
  text-transform: none;
  color: var(--text-muted);
}

.field {
  margin-bottom: 1rem;
}

.field-row {
  display: flex;
  gap: 0.75rem;
}

.field-row .field {
  flex: 1;
}

.input {
  width: 100%;
  padding: 0.65rem 0.85rem;
  border: 1px solid var(--border-input);
  border-radius: var(--radius-sm);
  background: var(--bg-input);
  font-size: 0.9rem;
  color: var(--text-primary);
  outline: none;
  transition: border-color 0.2s;
  box-sizing: border-box;
}

.input:focus {
  border-color: var(--border-input-focus);
}

/* Plan preview */
.plan-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 1.25rem;
  margin-bottom: 1.25rem;
  box-shadow: var(--shadow-sm);
}

.plan-name {
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 0.25rem;
}

.plan-meta {
  font-size: 0.8rem;
  color: var(--text-muted);
  margin-bottom: 0.75rem;
}

.plan-message {
  font-size: 0.9rem;
  color: var(--text-secondary);
  line-height: 1.5;
}

/* Loading */
.loading-state {
  text-align: center;
  padding: 2rem 0;
}

.spinner {
  width: 32px;
  height: 32px;
  border: 3px solid var(--border-color);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin: 0 auto 1rem;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.error-state {
  text-align: center;
  color: var(--color-destructive);
  padding: 1rem 0;
}

/* Navigation */
.nav-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 1rem;
  margin-top: 1rem;
  border-top: 1px solid var(--border-color);
}

/* Buttons */
.btn-primary {
  padding: 0.75rem 1.5rem;
  background: var(--gradient-primary);
  color: white;
  border: none;
  border-radius: var(--radius-md);
  font-weight: 600;
  font-size: 0.95rem;
  cursor: pointer;
  transition: opacity 0.2s;
}

.btn-primary:hover { opacity: 0.9; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-primary.full-width { width: 100%; }

.btn-ghost {
  padding: 0.75rem 1.5rem;
  background: transparent;
  color: var(--text-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  font-weight: 500;
  font-size: 0.9rem;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-ghost:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}
</style>
