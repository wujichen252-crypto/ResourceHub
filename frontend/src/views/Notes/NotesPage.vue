<template>
  <Transition name="fade-slide" appear>
    <div class="notes-page animate-fade-in-up">
      <div class="page-sidebar">
        <NoteTree
          :model-value="selectedFolderId"
          :selected-note-id="selectedNoteId"
          @update:model-value="handleSelectFolder"
          @select-note="handleSelectNote"
        />
      </div>
      <div class="page-content">
        <NoteContent
          :folder-id="selectedFolderId"
          :note-id="selectedNoteId"
          @update:note-id="selectedNoteId = $event"
        />
      </div>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import NoteTree from '../../components/notes/NoteTree.vue'
import NoteContent from '../../components/notes/NoteContent.vue'
import { useNotesStore } from '../../stores/notes'

const notesStore = useNotesStore()
const selectedFolderId = ref<number | null>(null)
const selectedNoteId = ref<number | null>(null)

function handleSelectFolder(folderId: number | null) {
  selectedFolderId.value = folderId
  selectedNoteId.value = null // 回到目录列表视图
}

function handleSelectNote(noteId: number) {
  selectedNoteId.value = noteId
  // 同步高亮笔记所属分类，便于退出阅读后回到对应目录列表
  const note = notesStore.allNotes.find((n) => n.id === noteId)
  if (note && note.category_id != null) {
    selectedFolderId.value = note.category_id
  }
}
</script>

<style scoped>
.notes-page {
  display: flex;
  height: calc(100vh - var(--rh-topbar-height));
  overflow: hidden;
}

.page-sidebar {
  width: 320px;
  min-width: 320px;
  flex-shrink: 0;
  border-right: 1px solid var(--rh-border-faint);
  background: var(--rh-bg-card);
  overflow-y: auto;
  transition: border-color var(--rh-duration-normal) var(--rh-transition-normal),
              background-color var(--rh-duration-normal) var(--rh-transition-normal);
}

.page-content {
  flex: 1;
  min-width: 0;
  overflow-y: auto;
  background: var(--rh-bg-base);
}

@media (max-width: 900px) {
  .page-sidebar {
    width: 280px;
    min-width: 280px;
  }
}

@media (max-width: 640px) {
  .notes-page {
    flex-direction: column;
    overflow-y: auto;
  }

  .page-sidebar {
    width: 100%;
    min-width: 0;
    height: 280px;
    flex-shrink: 0;
    border-right: 0;
    border-bottom: 1px solid var(--rh-border-faint);
  }

  .page-content {
    min-height: 420px;
    flex: 1;
  }
}
</style>
