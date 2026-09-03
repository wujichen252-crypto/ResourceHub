<template>
  <Transition name="fade-slide" appear>
    <div class="notes-page animate-fade-in-up">
      <div class="page-sidebar">
        <NoteTree v-model="selectedFolderId" />
      </div>
      <div class="page-content">
        <NoteContent :folder-id="selectedFolderId" />
      </div>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import NoteTree from '../../components/notes/NoteTree.vue'
import NoteContent from '../../components/notes/NoteContent.vue'

const selectedFolderId = ref<number | null>(null)
</script>

<style scoped>
.notes-page {
  display: flex;
  height: calc(100vh - var(--rh-nav-height));
  overflow: hidden;
}

.page-sidebar {
  width: 240px;
  flex-shrink: 0;
  border-right: 1px solid var(--rh-border-faint);
  background: var(--rh-bg-card);
  overflow-y: auto;
  transition: border-color var(--rh-duration-normal) var(--rh-transition-normal),
              background-color var(--rh-duration-normal) var(--rh-transition-normal);
}

.page-content {
  flex: 1;
  overflow-y: auto;
  background: var(--rh-bg-base);
}
</style>
