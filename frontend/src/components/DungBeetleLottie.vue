<template>
  <Vue3Lottie
    v-if="animationData"
    :animation-data="animationData"
    :height="height"
    :width="width"
    :loop="loop"
    :auto-play="autoPlay"
  />
</template>

<script setup>
import { Vue3Lottie } from 'vue3-lottie'

defineProps({
  animationData: { type: Object, default: null },
  height: { type: [Number, String], default: 200 },
  width: { type: [Number, String], default: 200 },
  loop: { type: Boolean, default: true },
  autoPlay: { type: Boolean, default: true }
})
</script>
