<template>
  <div class="threshold-sliders">
    <!-- Debug info if no categories -->
    <div v-if="!categories || categories.length === 0" class="no-categories">
      <p>No threshold categories found.</p>
      <p class="debug-info">Schema: {{ JSON.stringify(schema).slice(0, 200) }}...</p>
    </div>

    <div
      v-for="category in categories"
      :key="category.key"
      :class="['threshold-group', `group-${category.key}`, { compact: isCompactCategory(category.key) }]"
    >
      <div class="group-header" @click="toggleGroup(category.key)">
        <h3>{{ category.label }}</h3>
        <span class="toggle-icon">{{ expandedGroups[category.key] ? '−' : '+' }}</span>
      </div>
      <p v-if="category.description" class="group-description">{{ category.description }}</p>

      <div v-show="expandedGroups[category.key]" class="group-content">
        <div
          v-for="threshold in category.thresholds"
          :key="threshold.key"
          class="threshold-slider"
        >
          <div class="slider-header">
            <label :for="threshold.key">{{ threshold.label }}</label>
            <div class="value-display">
              <input
                type="number"
                :value="values[threshold.key] ?? threshold.default"
                :min="threshold.min"
                :max="threshold.max"
                :step="threshold.step"
                @input="handleNumberInput(threshold.key, $event)"
                class="value-input"
              />
              <span v-if="threshold.unit" class="unit">{{ threshold.unit }}</span>
            </div>
          </div>

          <div class="slider-container">
            <span class="range-label min">{{ threshold.min }}</span>
            <input
              type="range"
              :id="threshold.key"
              :min="threshold.min"
              :max="threshold.max"
              :step="threshold.step"
              :value="values[threshold.key] ?? threshold.default"
              @input="handleSliderInput(threshold.key, $event)"
              class="slider"
            />
            <span class="range-label max">{{ threshold.max }}</span>
          </div>

          <div class="slider-gauge">
            <div
              class="gauge-fill"
              :style="{ width: getGaugeWidth(threshold) + '%' }"
            ></div>
            <div
              class="gauge-marker default"
              :style="{ left: getDefaultPosition(threshold) + '%' }"
              :title="'Default: ' + threshold.default"
            ></div>
          </div>

          <p v-if="threshold.description" class="threshold-description">{{ threshold.description }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted } from 'vue'

const props = defineProps({
  schema: {
    type: Object,
    required: true
  },
  values: {
    type: Object,
    default: () => ({})
  }
})

const emit = defineEmits(['update'])

// Track which groups are expanded
const expandedGroups = reactive({})

// Safely extract categories from schema (handle different possible structures)
const categories = computed(() => {
  if (!props.schema) {
    console.log('ThresholdSliders: No schema')
    return []
  }

  // Try different possible locations for categories
  const cats = props.schema.categories ||
               props.schema.schema?.categories ||
               []

  console.log('ThresholdSliders: Found', cats.length, 'categories', cats.map(c => c.key))
  return cats
})

// Initialize all groups as expanded
function initializeExpandedGroups() {
  console.log('ThresholdSliders: Initializing groups for', categories.value.length, 'categories')
  categories.value.forEach(cat => {
    if (expandedGroups[cat.key] === undefined) {
      expandedGroups[cat.key] = true
      console.log('ThresholdSliders: Expanded', cat.key)
    }
  })
}

// Initialize on mount and when schema/categories change
onMounted(() => {
  console.log('ThresholdSliders mounted, schema:', props.schema)
  initializeExpandedGroups()
})
watch(() => props.schema, (newSchema) => {
  console.log('ThresholdSliders: Schema changed', newSchema)
  initializeExpandedGroups()
}, { immediate: true, deep: true })

function toggleGroup(key) {
  expandedGroups[key] = !expandedGroups[key]
}

function handleSliderInput(key, event) {
  const value = parseFloat(event.target.value)
  emit('update', key, value)
}

function handleNumberInput(key, event) {
  const value = parseFloat(event.target.value)
  if (!isNaN(value)) {
    emit('update', key, value)
  }
}

function getGaugeWidth(threshold) {
  const value = props.values[threshold.key] ?? threshold.default
  const range = threshold.max - threshold.min
  return ((value - threshold.min) / range) * 100
}

function getDefaultPosition(threshold) {
  const range = threshold.max - threshold.min
  return ((threshold.default - threshold.min) / range) * 100
}

const COMPACT_CATEGORIES = ['cooldown', 'rally']
function isCompactCategory(key) {
  return COMPACT_CATEGORIES.includes(key)
}
</script>

<style scoped>
.threshold-sliders {
  display: grid;
  grid-template-columns: 1fr 1fr auto;
  grid-template-rows: auto auto;
  gap: 0.5rem;
}

/* velocity: col 1, spans both rows */
.group-velocity {
  grid-column: 1;
  grid-row: 1 / 3;
}

/* position: col 2, spans both rows */
.group-position {
  grid-column: 2;
  grid-row: 1 / 3;
}

/* cooldown: col 3, row 1 */
.group-cooldown {
  grid-column: 3;
  grid-row: 1;
  min-width: 220px;
}

/* rally: col 3, row 2 */
.group-rally {
  grid-column: 3;
  grid-row: 2;
  min-width: 220px;
}

@media (max-width: 1200px) {
  .threshold-sliders {
    grid-template-columns: 1fr 1fr;
    grid-template-rows: auto auto auto;
  }
  .group-velocity {
    grid-column: 1;
    grid-row: 1 / 3;
  }
  .group-position {
    grid-column: 2;
    grid-row: 1;
  }
  .group-cooldown {
    grid-column: 2;
    grid-row: 2;
    min-width: unset;
  }
  .group-rally {
    grid-column: 2;
    grid-row: 3;
    min-width: unset;
  }
}

@media (max-width: 800px) {
  .threshold-sliders {
    grid-template-columns: 1fr 1fr;
    grid-template-rows: auto auto auto;
  }
  .group-velocity {
    grid-column: 1 / -1;
    grid-row: auto;
  }
  .group-position {
    grid-column: 1 / -1;
    grid-row: auto;
  }
  .group-cooldown {
    grid-column: 1;
    grid-row: auto;
    min-width: unset;
  }
  .group-rally {
    grid-column: 2;
    grid-row: auto;
    min-width: unset;
  }
}

@media (max-width: 500px) {
  .threshold-sliders {
    grid-template-columns: 1fr;
  }
  .group-velocity,
  .group-position,
  .group-cooldown,
  .group-rally {
    grid-column: 1;
    grid-row: auto;
    min-width: unset;
  }
}

.no-categories {
  text-align: center;
  padding: 1rem;
  color: #888;
  background: #1a1a2e;
  border-radius: 6px;
  grid-column: 1 / -1;
}

.no-categories .debug-info {
  font-size: 0.65rem;
  color: #555;
  word-break: break-all;
  margin-top: 0.25rem;
}

.threshold-group {
  background: #1a1a2e;
  border-radius: 6px;
  overflow: hidden;
}

/* Compact groups (cooldown, rally) — tighter spacing */
.threshold-group.compact .group-header {
  padding: 0.3rem 0.5rem;
}
.threshold-group.compact .group-header h3 {
  font-size: 0.7rem;
}
.threshold-group.compact .group-content {
  padding: 0.3rem 0.5rem;
}
.threshold-group.compact .threshold-slider {
  margin-bottom: 0.25rem;
  padding-bottom: 0.25rem;
}
.threshold-group.compact .slider-header label {
  font-size: 0.68rem;
}
.threshold-group.compact .value-input {
  width: 44px;
  font-size: 0.68rem;
  padding: 0.1rem 0.2rem;
}

.group-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.4rem 0.6rem;
  cursor: pointer;
  background: rgba(78, 204, 163, 0.1);
  border-bottom: 1px solid #2a2a4a;
}

.group-header:hover {
  background: rgba(78, 204, 163, 0.15);
}

.group-header h3 {
  margin: 0;
  font-size: 0.75rem;
  color: #4ecca3;
}

.toggle-icon {
  color: #4ecca3;
  font-size: 0.9rem;
  font-weight: bold;
}

.group-description {
  margin: 0;
  padding: 0.25rem 0.6rem;
  font-size: 0.65rem;
  color: #666;
  background: #1a1a2e;
}

.group-content {
  padding: 0.4rem 0.6rem;
}

.threshold-slider {
  margin-bottom: 0.4rem;
  padding-bottom: 0.4rem;
  border-bottom: 1px solid #232342;
}

.threshold-slider:last-child {
  margin-bottom: 0;
  padding-bottom: 0;
  border-bottom: none;
}

.slider-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.15rem;
}

.slider-header label {
  color: #ccc;
  font-size: 0.72rem;
}

.value-display {
  display: flex;
  align-items: center;
  gap: 0.15rem;
}

.value-input {
  width: 48px;
  padding: 0.1rem 0.3rem;
  background: #2a2a4a;
  border: 1px solid #3a3a5a;
  border-radius: 3px;
  color: #4ecca3;
  font-size: 0.72rem;
  text-align: right;
}

.value-input:focus {
  outline: none;
  border-color: #4ecca3;
}

.unit {
  color: #666;
  font-size: 0.65rem;
}

.slider-container {
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.range-label {
  color: #555;
  font-size: 0.6rem;
  min-width: 22px;
}

.range-label.min {
  text-align: left;
}

.range-label.max {
  text-align: right;
}

.slider {
  flex: 1;
  -webkit-appearance: none;
  appearance: none;
  height: 4px;
  background: #2a2a4a;
  border-radius: 2px;
  outline: none;
}

.slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 12px;
  height: 12px;
  background: #4ecca3;
  border-radius: 50%;
  cursor: pointer;
  transition: transform 0.1s;
}

.slider::-webkit-slider-thumb:hover {
  transform: scale(1.2);
}

.slider::-moz-range-thumb {
  width: 12px;
  height: 12px;
  background: #4ecca3;
  border: none;
  border-radius: 50%;
  cursor: pointer;
}

.slider-gauge {
  position: relative;
  height: 3px;
  background: #2a2a4a;
  border-radius: 2px;
  margin-top: 0.2rem;
  margin-left: 24px;
  margin-right: 24px;
}

.gauge-fill {
  position: absolute;
  top: 0;
  left: 0;
  height: 100%;
  background: linear-gradient(90deg, #4ecca3 0%, #3db892 100%);
  border-radius: 2px;
  transition: width 0.1s;
}

.gauge-marker {
  position: absolute;
  top: -2px;
  width: 2px;
  height: 7px;
  background: #888;
  transform: translateX(-50%);
}

.gauge-marker.default {
  background: #f1c40f;
}

.threshold-description {
  margin: 0.2rem 0 0;
  font-size: 0.6rem;
  color: #555;
  margin-left: 24px;
}
</style>
