<template>
  <div class="equipment-page">
    <header class="eq-header">
      <router-link to="/profile" class="back-btn">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" width="20" height="20" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"/></svg>
      </router-link>
      <h1>My Equipment</h1>
    </header>

    <!-- Location toggle -->
    <div class="location-toggle">
      <button :class="['loc-btn', { active: trainLocation === 'gym' }]" @click="trainLocation = 'gym'">Gym</button>
      <button :class="['loc-btn', { active: trainLocation === 'home' }]" @click="trainLocation = 'home'">Home</button>
    </div>
    <p class="loc-hint" v-if="trainLocation === 'gym'">Select what your gym has. We'll build your plan around it.</p>
    <p class="loc-hint" v-else>Select what you have at home. We'll stick to exercises you can actually do.</p>

    <div v-if="loading" class="loading">Loading...</div>

    <template v-else>
      <!-- Equipment categories -->
      <div v-for="(items, category) in categories" :key="category" class="eq-category">
        <h3 class="cat-title">{{ category }}</h3>
        <div class="eq-grid">
          <button
            v-for="item in items"
            :key="item"
            :class="['eq-chip', { selected: selectedEquipment.has(item) }]"
            @click="toggleEquipment(item)"
          >
            <span class="eq-name">{{ formatName(item) }}</span>
            <span class="eq-count">{{ exerciseCounts[item] || 0 }} exercises</span>
          </button>
        </div>
      </div>

      <!-- Quick presets -->
      <div class="presets">
        <h3 class="cat-title">Quick Setup</h3>
        <div class="preset-row">
          <button class="preset-btn" @click="applyPreset('full_gym')">Full Gym</button>
          <button class="preset-btn" @click="applyPreset('basic_home')">Basic Home</button>
          <button class="preset-btn" @click="applyPreset('dumbbells_only')">Dumbbells Only</button>
          <button class="preset-btn" @click="applyPreset('bodyweight')">Bodyweight Only</button>
        </div>
      </div>

      <!-- Summary -->
      <div class="summary-bar">
        <span class="summary-text">{{ selectedEquipment.size }} items selected — {{ unlockCount }} exercises available</span>
      </div>

      <!-- Save -->
      <button class="btn-save" :disabled="saving" @click="save">
        {{ saving ? 'Saving...' : 'Save Equipment' }}
      </button>
    </template>

    <div v-if="toast" class="toast" @click="toast = ''">{{ toast }}</div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useWorkoutStore } from '../../stores/workout'

const workoutStore = useWorkoutStore()

const loading = ref(true)
const saving = ref(false)
const toast = ref('')
const trainLocation = ref('gym')
const categories = ref({})
const exerciseCounts = ref({})
const selectedEquipment = ref(new Set())

const PRESETS = {
  full_gym: [
    'barbell', 'dumbbells', 'kettlebell', 'bench', 'decline bench', 'squat rack',
    'preacher bench', 'dip bars', 'pull-up bar', 'cable machine', 'smith machine',
    'leg press machine', 'leg extension machine', 'leg curl machine',
    'seated leg curl machine', 'seated calf raise machine', 'hack squat machine',
    'chest press machine', 'pec deck machine', 'row machine',
    'abductor machine', 'adductor machine', 'hyperextension bench',
    'resistance band', 'ab wheel', 'yoga mat', 'box',
  ],
  basic_home: ['dumbbells', 'resistance band', 'yoga mat', 'pull-up bar'],
  dumbbells_only: ['dumbbells'],
  bodyweight: [],
}

const unlockCount = computed(() => {
  if (!exerciseCounts.value) return 0
  // Bodyweight exercises are always available
  let count = exerciseCounts.value['__bodyweight'] || 0
  for (const eq of selectedEquipment.value) {
    count += exerciseCounts.value[eq] || 0
  }
  // Rough dedup — many exercises share equipment
  return Math.min(count, 120)
})

function formatName(item) {
  return item.replace(/\b\w/g, c => c.toUpperCase())
}

function toggleEquipment(item) {
  const s = new Set(selectedEquipment.value)
  if (s.has(item)) s.delete(item)
  else s.add(item)
  selectedEquipment.value = s
}

function applyPreset(name) {
  selectedEquipment.value = new Set(PRESETS[name] || [])
  if (name === 'bodyweight' || name === 'basic_home') trainLocation.value = 'home'
  else trainLocation.value = 'gym'
}

async function save() {
  saving.value = true
  try {
    await workoutStore.updateEquipment([...selectedEquipment.value], trainLocation.value)
    toast.value = 'Equipment saved!'
    setTimeout(() => { toast.value = '' }, 2000)
  } catch {
    toast.value = 'Failed to save'
    setTimeout(() => { toast.value = '' }, 3000)
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  try {
    const data = await workoutStore.fetchEquipment()
    categories.value = data.categories || {}
    exerciseCounts.value = data.exercise_counts || {}
    trainLocation.value = data.train_location || 'gym'
    selectedEquipment.value = new Set(data.user_equipment || [])
  } catch { /* non-critical */ }
  finally { loading.value = false }
})
</script>

<style scoped>
.equipment-page {
  padding: 1rem;
  padding-bottom: 6rem;
}

.eq-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 1rem;
}

.eq-header h1 {
  font-size: 1.2rem;
  font-weight: 800;
  color: var(--text-primary);
}

.back-btn {
  color: var(--text-muted);
  display: flex;
}

/* Location toggle */
.location-toggle {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.loc-btn {
  flex: 1;
  padding: 0.6rem;
  border-radius: var(--radius-md);
  border: 2px solid var(--border-color);
  background: var(--bg-card);
  color: var(--text-secondary);
  font-weight: 600;
  font-size: 0.85rem;
  cursor: pointer;
  transition: all 0.2s;
}

.loc-btn.active {
  border-color: var(--color-primary);
  background: var(--color-primary-light);
  color: var(--color-primary);
}

.loc-hint {
  font-size: 0.75rem;
  color: var(--text-muted);
  margin-bottom: 1.25rem;
  text-align: center;
}

/* Categories */
.eq-category {
  margin-bottom: 1.25rem;
}

.cat-title {
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-muted);
  margin-bottom: 0.5rem;
}

.eq-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
}

.eq-chip {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 0.5rem 0.7rem;
  border-radius: 0.6rem;
  border: 1.5px solid var(--border-color);
  background: var(--bg-card);
  cursor: pointer;
  transition: all 0.15s;
  min-width: 0;
}

.eq-chip.selected {
  border-color: var(--color-primary);
  background: var(--color-primary-light);
}

.eq-chip:active {
  transform: scale(0.96);
}

.eq-name {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--text-primary);
  white-space: nowrap;
}

.eq-count {
  font-size: 0.6rem;
  color: var(--text-muted);
}

.eq-chip.selected .eq-name {
  color: var(--color-primary);
}

/* Presets */
.presets {
  margin-bottom: 1.25rem;
}

.preset-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
}

.preset-btn {
  padding: 0.4rem 0.75rem;
  border-radius: var(--radius-full);
  border: 1.5px solid var(--border-color);
  background: var(--bg-card);
  color: var(--text-secondary);
  font-size: 0.75rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s;
}

.preset-btn:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

/* Summary */
.summary-bar {
  text-align: center;
  padding: 0.6rem;
  margin-bottom: 1rem;
  background: var(--bg-input);
  border-radius: var(--radius-md);
}

.summary-text {
  font-size: 0.8rem;
  color: var(--text-secondary);
  font-weight: 500;
}

/* Save */
.btn-save {
  width: 100%;
  padding: 0.85rem;
  background: var(--gradient-primary);
  color: var(--text-on-primary);
  border: none;
  border-radius: var(--radius-md);
  font-weight: 700;
  font-size: 0.9rem;
  cursor: pointer;
}

.btn-save:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.loading {
  text-align: center;
  padding: 2rem;
  color: var(--text-muted);
}

.toast {
  position: fixed;
  bottom: 5rem;
  left: 50%;
  transform: translateX(-50%);
  padding: 0.5rem 1rem;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-full);
  font-size: 0.8rem;
  color: var(--text-primary);
  z-index: 100;
}
</style>
