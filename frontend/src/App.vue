<template>
  <div class="app-layout">
    <NavBar v-if="!isLoginPage" />
    <main class="app-main" :class="{ 'no-nav': isLoginPage }">
      <BaseTransition :transition-name="transitionName">
        <router-view :key="$route.fullPath" />
      </BaseTransition>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import NavBar from './components/NavBar.vue'
import BaseTransition from './components/ui/BaseTransition.vue'

const route = useRoute()
const isLoginPage = computed(() => route.path === '/login')

// Track navigation direction for page transitions
const previousRoute = ref('')
watch(
  () => route.path,
  (toPath, fromPath) => {
    previousRoute.value = fromPath
    transitionName.value = computeTransition(fromPath, toPath)
  },
)

const transitionName = ref('fade-slide')

function computeTransition(from: string, to: string): string {
  // Forward navigation (deeper path) → fade-slide-up
  // Backward navigation (shallower path) → fade-slide-reverse-up
  const fromDepth = from.split('/').filter(Boolean).length
  const toDepth = to.split('/').filter(Boolean).length
  return toDepth >= fromDepth ? 'fade-slide' : 'fade-slide-reverse'
}
</script>

<style>
.app-layout {
  display: flex;
  flex-direction: column;
  height: 100vh;
}

.app-main {
  flex: 1;
  overflow-y: auto;
}

.app-main.no-nav {
  height: 100vh;
}
</style>
