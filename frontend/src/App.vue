<template>
  <div class="app-layout">
    <NavBar v-if="!isLoginPage" />
    <main class="app-main" :class="{ 'no-nav': isLoginPage }">
      <router-view />
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import NavBar from './components/NavBar.vue'

const route = useRoute()
const isLoginPage = computed(() => route.path === '/login')
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
