<template>
  <router-link
    :to="to"
    class="bottom-nav-item"
    :class="{ active: isActive }"
  >
    <div class="nav-icon">
      <slot />
    </div>
    <span class="nav-label">{{ label }}</span>
  </router-link>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const props = defineProps({
  to: { type: String, required: true },
  label: { type: String, required: true },
  exact: { type: Boolean, default: false }
})

const route = useRoute()
const isActive = computed(() =>
  props.exact
    ? route.path === props.to
    : route.path.startsWith(props.to)
)
</script>

<style scoped>
.bottom-nav-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.2rem;
  padding: 0.4rem 0.75rem;
  border-radius: 0.75rem;
  text-decoration: none;
  color: var(--text-muted);
  transition: color 0.2s, background 0.2s, transform 0.15s;
  -webkit-tap-highlight-color: transparent;
}

.bottom-nav-item:active {
  transform: scale(0.92);
}

.bottom-nav-item.active {
  color: var(--color-primary);
  background: var(--color-primary-light);
  box-shadow: var(--glow-primary);
}

.bottom-nav-item:not(.active):hover {
  color: var(--text-secondary);
}

.nav-icon {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.nav-icon :deep(svg) {
  width: 24px;
  height: 24px;
}

.nav-label {
  font-size: 0.65rem;
  font-weight: 600;
  letter-spacing: 0.02em;
}
</style>
