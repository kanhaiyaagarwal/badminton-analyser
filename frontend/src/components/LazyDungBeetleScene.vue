<template>
  <div class="w-full h-full rounded-2xl overflow-hidden" :style="{ background: 'var(--bg-card)' }">
    <TresCanvas clear-color="#F5F2EB" window-size>
      <TresPerspectiveCamera :position="[0, 3, 6]" :look-at="[0, 0, 0]" />
      <OrbitControls auto-rotate :auto-rotate-speed="1.5" :enable-zoom="false" :enable-pan="false" />

      <!-- Lighting -->
      <TresAmbientLight :intensity="0.6" color="#FAF8F3" />
      <TresDirectionalLight :position="[5, 8, 3]" :intensity="0.8" color="#F5F2EB" />

      <!-- Ground plane (sage green) -->
      <TresMesh :position="[0, -0.5, 0]" :rotation="[-Math.PI / 2, 0, 0]">
        <TresCircleGeometry :args="[4, 64]" />
        <TresMeshStandardMaterial color="#A5B08D" :roughness="0.9" />
      </TresMesh>

      <!-- Beetle body -->
      <TresMesh :position="[0, 0.3, 0]">
        <TresSphereGeometry :args="[0.6, 32, 32]" />
        <TresMeshStandardMaterial color="#3E4736" :roughness="0.7" :metalness="0.2" />
      </TresMesh>

      <!-- Beetle head -->
      <TresMesh :position="[0.55, 0.35, 0]">
        <TresSphereGeometry :args="[0.3, 32, 32]" />
        <TresMeshStandardMaterial color="#2A3025" :roughness="0.6" :metalness="0.3" />
      </TresMesh>

      <!-- Dung ball -->
      <TresMesh :position="[-1.2, 0.15, 0.3]">
        <TresSphereGeometry :args="[0.45, 32, 32]" />
        <TresMeshStandardMaterial color="#8A827A" :roughness="1" />
      </TresMesh>

      <!-- Second dung ball (smaller) -->
      <TresMesh :position="[-0.5, 0, 1.2]">
        <TresSphereGeometry :args="[0.25, 32, 32]" />
        <TresMeshStandardMaterial color="#706860" :roughness="1" />
      </TresMesh>
    </TresCanvas>
  </div>
</template>

<script setup>
import { TresCanvas } from '@tresjs/core'
import { OrbitControls } from '@tresjs/cientos'
</script>
