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
      class="threshold-group"
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
</script>

<style scoped>
.threshold-sliders {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.no-categories {
  text-align: center;
  padding: 1.5rem;
  color: #888;
  background: #1a1a2e;
  border-radius: 8px;
}

.no-categories .debug-info {
  font-size: 0.7rem;
  color: #555;
  word-break: break-all;
  margin-top: 0.5rem;
}

.threshold-group {
  background: #1a1a2e;
  border-radius: 8px;
  overflow: hidden;
}

.group-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 1rem;
  cursor: pointer;
  background: rgba(78, 204, 163, 0.1);
  border-bottom: 1px solid #2a2a4a;
}

.group-header:hover {
  background: rgba(78, 204, 163, 0.15);
}

.group-header h3 {
  margin: 0;
  font-size: 0.9rem;
  color: #4ecca3;
}

.toggle-icon {
  color: #4ecca3;
  font-size: 1.2rem;
  font-weight: bold;
}

.group-description {
  margin: 0;
  padding: 0.5rem 1rem;
  font-size: 0.8rem;
  color: #666;
  background: #1a1a2e;
}

.group-content {
  padding: 1rem;
}

.threshold-slider {
  margin-bottom: 1.25rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid #2a2a4a;
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
  margin-bottom: 0.5rem;
}

.slider-header label {
  color: #eee;
  font-size: 0.85rem;
}

.value-display {
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.value-input {
  width: 60px;
  padding: 0.25rem 0.5rem;
  background: #2a2a4a;
  border: 1px solid #3a3a5a;
  border-radius: 4px;
  color: #4ecca3;
  font-size: 0.85rem;
  text-align: right;
}

.value-input:focus {
  outline: none;
  border-color: #4ecca3;
}

.unit {
  color: #666;
  font-size: 0.8rem;
}

.slider-container {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.range-label {
  color: #666;
  font-size: 0.7rem;
  min-width: 30px;
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
  height: 6px;
  background: #2a2a4a;
  border-radius: 3px;
  outline: none;
}

.slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 16px;
  height: 16px;
  background: #4ecca3;
  border-radius: 50%;
  cursor: pointer;
  transition: transform 0.1s;
}

.slider::-webkit-slider-thumb:hover {
  transform: scale(1.2);
}

.slider::-moz-range-thumb {
  width: 16px;
  height: 16px;
  background: #4ecca3;
  border: none;
  border-radius: 50%;
  cursor: pointer;
}

.slider-gauge {
  position: relative;
  height: 4px;
  background: #2a2a4a;
  border-radius: 2px;
  margin-top: 0.5rem;
  margin-left: 35px;
  margin-right: 35px;
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
  top: -3px;
  width: 2px;
  height: 10px;
  background: #888;
  transform: translateX(-50%);
}

.gauge-marker.default {
  background: #f1c40f;
}

.threshold-description {
  margin: 0.5rem 0 0;
  font-size: 0.75rem;
  color: #666;
  margin-left: 35px;
}
</style>
