<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import {
  student,
  subjects,
  activeSubjectId,
  switchSubject,
  addSubject,
  deleteSubject,
  renameActiveSubject,
  experiments,
  renumberExperiments,
  toggleAllCards,
  resetWorkspace,
  addDocument,
  isShareOpen,
} from '../../store/labStore'
import DocumentCard from './DocumentCard.vue'
import {
  ListOrdered,
  ChevronsUpDown,
  Trash2,
  Plus,
  FileText,
  Share2,
  BookOpen,
  ChevronDown,
  Check,
  Edit2,
} from '@lucide/vue'

const dragStartIndex = ref<number | null>(null)
const isDropdownOpen = ref(false)
const isRenaming = ref(false)
const isAdding = ref(false)
const renameInput = ref('')
const newSubjectInput = ref('')
const dropdownRef = ref<HTMLElement | null>(null)

function onDragStart(idx: number) {
  dragStartIndex.value = idx
}

function onDrop(targetIdx: number) {
  if (dragStartIndex.value !== null && dragStartIndex.value !== targetIdx) {
    const moved = experiments.value.splice(dragStartIndex.value, 1)[0]
    experiments.value.splice(targetIdx, 0, moved)
  }
  dragStartIndex.value = null
}

function startRename() {
  renameInput.value = student.subject
  isRenaming.value = true
  isAdding.value = false
}

function saveRename() {
  if (renameInput.value.trim()) {
    renameActiveSubject(renameInput.value.trim())
    isRenaming.value = false
  }
}

function startAdd() {
  newSubjectInput.value = ''
  isAdding.value = true
  isRenaming.value = false
}

function saveAdd() {
  if (newSubjectInput.value.trim()) {
    addSubject(newSubjectInput.value.trim())
    isAdding.value = false
    isDropdownOpen.value = false
  }
}

function handleClickOutside(e: MouseEvent) {
  if (dropdownRef.value && !dropdownRef.value.contains(e.target as Node)) {
    isDropdownOpen.value = false
    isRenaming.value = false
    isAdding.value = false
  }
}

onMounted(() => {
  window.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  window.removeEventListener('click', handleClickOutside)
})
</script>

<template>
  <div class="space-y-3.5">
    <!-- Clean Unified Toolbar (Subject Dropdown + Actions) -->
    <div class="flex flex-wrap items-center justify-between gap-2.5">
      <!-- Left: Subject Dropdown Menu & Share -->
      <div class="flex items-center gap-2 min-w-0" ref="dropdownRef">
        <!-- Subject Dropdown Trigger -->
        <div class="relative min-w-0">
          <button
            type="button"
            @click.stop="isDropdownOpen = !isDropdownOpen"
            class="inline-flex items-center gap-1.5 sm:gap-2 bg-card hover:bg-input border border-edge hover:border-edge-hi text-hi font-semibold text-xs sm:text-sm px-2.5 sm:px-3 py-1.5 rounded-xl transition shadow-sm cursor-pointer min-w-0 max-w-[150px] sm:max-w-[220px]"
            title="Switch or manage subjects"
          >
            <BookOpen class="w-3.5 h-3.5 text-amber shrink-0" />
            <span class="truncate">{{ student.subject || 'Untitled Subject' }}</span>
            <ChevronDown class="w-3.5 h-3.5 text-mid transition-transform shrink-0" :class="{ 'rotate-180': isDropdownOpen }" />
          </button>

          <!-- Simple Subject Dropdown Menu -->
          <div
            v-if="isDropdownOpen"
            class="absolute left-0 top-full mt-1.5 z-50 w-72 bg-card border border-edge rounded-xl shadow-2xl p-2 space-y-1.5 select-none animate-in fade-in"
            @click.stop
          >
            <div class="flex items-center justify-between px-1.5 text-[10px] font-semibold text-mid uppercase tracking-wider">
              <span>Your Subjects ({{ subjects.length }})</span>
              <button
                type="button"
                @click="startAdd"
                class="text-amber hover:text-amber-hi font-semibold flex items-center gap-0.5 cursor-pointer"
              >
                <Plus class="w-3 h-3" />
                <span>New</span>
              </button>
            </div>

            <!-- Inline Add Subject Input -->
            <div v-if="isAdding" class="p-1.5 bg-surface rounded-lg border border-edge flex items-center gap-1.5">
              <input
                v-model="newSubjectInput"
                type="text"
                placeholder="e.g. Cloud Computing"
                class="flex-1 bg-input border border-edge text-xs text-hi rounded px-2 py-1 outline-none focus:border-amber"
                @keyup.enter="saveAdd"
              />
              <button
                type="button"
                @click="saveAdd"
                class="text-[11px] bg-amber hover:bg-amber-hi text-surface font-semibold px-2 py-1 rounded transition cursor-pointer"
              >
                Add
              </button>
            </div>

            <!-- Inline Rename Subject Input -->
            <div v-if="isRenaming" class="p-1.5 bg-surface rounded-lg border border-edge flex items-center gap-1.5">
              <input
                v-model="renameInput"
                type="text"
                class="flex-1 bg-input border border-edge text-xs text-hi rounded px-2 py-1 outline-none focus:border-amber"
                @keyup.enter="saveRename"
              />
              <button
                type="button"
                @click="saveRename"
                class="text-[11px] bg-amber hover:bg-amber-hi text-surface font-semibold px-2 py-1 rounded transition cursor-pointer"
              >
                Save
              </button>
            </div>

            <!-- Subjects List -->
            <div class="max-h-52 overflow-y-auto space-y-0.5">
              <div
                v-for="s in subjects"
                :key="s.id"
                @click="switchSubject(s.id); isDropdownOpen = false; isRenaming = false; isAdding = false"
                class="flex items-center justify-between px-2.5 py-1.5 rounded-lg text-xs transition cursor-pointer"
                :class="s.id === activeSubjectId ? 'bg-amber-dim/30 text-hi font-medium' : 'text-mid hover:bg-input hover:text-hi'"
              >
                <div class="flex items-center gap-2 truncate flex-1 min-w-0">
                  <Check v-if="s.id === activeSubjectId" class="w-3.5 h-3.5 text-amber shrink-0" />
                  <span class="truncate">{{ s.name }}</span>
                </div>

                <div class="flex items-center gap-1.5 shrink-0 ml-2" @click.stop>
                  <span class="text-[10px] text-lo font-mono">
                    {{ s.id === activeSubjectId ? experiments.length : (s.savedExperiments?.length || 0) }} exps
                  </span>

                  <button
                    type="button"
                    @click="deleteSubject(s.id)"
                    class="p-1 text-lo hover:text-danger hover:bg-edge/40 rounded transition cursor-pointer"
                    :title="subjects.length === 1 ? 'Clear and reset subject' : `Delete ${s.name}`"
                  >
                    <Trash2 class="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            </div>

            <!-- Rename Action in Dropdown -->
            <div class="pt-1 border-t border-edge">
              <button
                type="button"
                @click="startRename"
                class="w-full text-left px-2.5 py-1.5 rounded-lg text-xs text-mid hover:text-hi hover:bg-input flex items-center gap-2 cursor-pointer"
              >
                <Edit2 class="w-3 h-3 text-lo" />
                <span>Rename "{{ student.subject }}"</span>
              </button>
            </div>
          </div>
        </div>

        <div class="flex items-center gap-1.5 sm:gap-2 shrink-0">
          <!-- Document Count Pill -->
          <span class="text-xs text-mid font-mono px-2 py-0.5 rounded bg-input border border-edge">
            {{ experiments.length }} doc{{ experiments.length === 1 ? '' : 's' }}
          </span>

          <!-- Share Syllabus Button -->
          <button
            type="button"
            @click="isShareOpen = true"
            class="inline-flex items-center gap-1 text-xs text-mid hover:text-hi bg-card border border-edge hover:border-edge-hi px-2 sm:px-2.5 py-1 rounded-lg transition cursor-pointer"
            title="Share this subject's syllabus with classmates"
          >
            <Share2 class="w-3.5 h-3.5 text-amber" />
            <span class="hidden sm:inline">Share</span>
          </button>
        </div>
      </div>

      <!-- Right: Document Actions -->
      <div class="flex items-center gap-1.5 sm:gap-2 shrink-0">
        <!-- Renumber 1..N -->
        <button
          type="button"
          @click="renumberExperiments"
          class="inline-flex items-center gap-1 text-xs text-mid hover:text-hi p-1.5 sm:px-2.5 sm:py-1.5 rounded-lg hover:bg-card border border-edge/40 sm:border-transparent transition cursor-pointer"
          title="Renumber cards sequentially from 1 to N"
        >
          <ListOrdered class="w-3.5 h-3.5" />
          <span class="hidden 2xl:inline">Renumber 1..N</span>
        </button>

        <!-- Toggle All Cards -->
        <button
          type="button"
          @click="toggleAllCards"
          class="inline-flex items-center gap-1 text-xs text-mid hover:text-hi p-1.5 sm:px-2.5 sm:py-1.5 rounded-lg hover:bg-card border border-edge/40 sm:border-transparent transition cursor-pointer"
          title="Expand or collapse all experiment cards"
        >
          <ChevronsUpDown class="w-3.5 h-3.5" />
          <span class="hidden 2xl:inline">Toggle All</span>
        </button>

        <!-- Clear All -->
        <button
          type="button"
          @click="resetWorkspace"
          class="inline-flex items-center gap-1 text-xs text-mid hover:text-danger p-1.5 sm:px-2.5 sm:py-1.5 rounded-lg hover:bg-card border border-edge/40 sm:border-transparent transition cursor-pointer"
          title="Clear all cards from workspace"
        >
          <Trash2 class="w-3.5 h-3.5" />
          <span class="hidden 2xl:inline">Clear All</span>
        </button>

        <!-- Add Empty Card -->
        <button
          type="button"
          @click="addDocument"
          class="inline-flex items-center gap-1 bg-amber hover:bg-amber-hi text-surface font-semibold px-2.5 sm:px-3 py-1.5 rounded-lg text-xs transition cursor-pointer shadow-sm"
          title="Add a manual experiment card"
        >
          <Plus class="w-3.5 h-3.5" />
          <span>Add Card</span>
        </button>
      </div>
    </div>

    <!-- Empty Workspace State -->
    <div
      v-if="experiments.length === 0"
      class="bg-card border-2 border-dashed border-edge rounded-2xl p-12 text-center select-none"
    >
      <div class="w-12 h-12 rounded-xl bg-input border border-edge flex items-center justify-center mx-auto text-lo mb-3">
        <FileText class="w-6 h-6" />
      </div>
      <h4 class="text-sm font-semibold text-hi mb-1">
        No documents added yet
      </h4>
      <p class="text-xs text-mid max-w-sm mx-auto mb-4">
        Drop your experiment PDFs in the bulk upload box on the left, or add an empty card to start typing manually.
      </p>
      <button
        type="button"
        @click="addDocument"
        class="inline-flex items-center gap-1.5 bg-amber hover:bg-amber-hi text-surface font-semibold px-4 py-2 rounded-lg text-xs transition shadow-sm cursor-pointer"
      >
        <Plus class="w-4 h-4" />
        <span>Add First Card</span>
      </button>
    </div>

    <!-- Cards List with Drag-and-Drop Reordering -->
    <div v-else class="space-y-3">
      <div
        v-for="(exp, idx) in experiments"
        :key="exp.id"
        :draggable="true"
        @dragstart="onDragStart(idx)"
        @dragover.prevent
        @drop="onDrop(idx)"
        class="transition-all"
      >
        <DocumentCard :doc="exp" :index="idx" :total="experiments.length" />
      </div>
    </div>
  </div>
</template>
