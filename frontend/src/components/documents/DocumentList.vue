<script setup lang="ts">
import { ref, computed, nextTick, onMounted, onUnmounted } from 'vue'
import {
  student,
  subjects,
  activeSubjectId,
  activeSubject,
  switchSubject,
  addSubject,
  deleteSubject,
  renameActiveSubject,
  renameSubject,
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
  X,
  Search,
} from '@lucide/vue'

const dragStartIndex = ref<number | null>(null)

// Dropdown & Search state
const isDropdownOpen = ref(false)
const dropdownRef = ref<HTMLElement | null>(null)
const subjectSearchQuery = ref('')

// New Subject Creation state
const isAdding = ref(false)
const newSubjectInput = ref('')
const newSubjectInputRef = ref<HTMLInputElement | null>(null)

// Toolbar Inline Quick-Rename state
const isToolbarRenaming = ref(false)
const toolbarRenameInput = ref('')
const toolbarRenameInputRef = ref<HTMLInputElement | null>(null)

// Dropdown Row Inline Rename state (supports any subject by id)
const editingSubjectId = ref<string | null>(null)
const rowRenameInput = ref('')
const rowRenameInputRef = ref<HTMLInputElement | null>(null)

// Drag-and-Drop Reordering state
const dragOverIndex = ref<number | null>(null)

function onDragStart(e: DragEvent, idx: number) {
  dragStartIndex.value = idx
  if (e.dataTransfer) {
    e.dataTransfer.effectAllowed = 'move'
    e.dataTransfer.setData('text/plain', String(idx))
    const cardEl = (e.target as HTMLElement)?.closest('.document-card-root') as HTMLElement | null
    if (cardEl && e.dataTransfer.setDragImage) {
      e.dataTransfer.setDragImage(cardEl, 24, 24)
    }
  }
}

function onDragOver(idx: number) {
  if (dragStartIndex.value !== null && dragStartIndex.value !== idx) {
    dragOverIndex.value = idx
  }
}

function onDragLeave(idx: number) {
  if (dragOverIndex.value === idx) {
    dragOverIndex.value = null
  }
}

function onDragEnd() {
  dragStartIndex.value = null
  dragOverIndex.value = null
}

function onDrop(targetIdx: number) {
  if (dragStartIndex.value !== null && dragStartIndex.value !== targetIdx) {
    const moved = experiments.value.splice(dragStartIndex.value, 1)[0]
    experiments.value.splice(targetIdx, 0, moved)
  }
  dragStartIndex.value = null
  dragOverIndex.value = null
}

// ── Search & Filter Computations ──────────────────────────────────────────
const filteredOtherSubjects = computed(() => {
  const others = subjects.value.filter((s) => s.id !== activeSubjectId.value)
  const q = subjectSearchQuery.value.trim().toLowerCase()
  if (!q) return others
  return others.filter((s) => s.name.toLowerCase().includes(q))
})

const isCurrentSubjectMatchingSearch = computed(() => {
  const q = subjectSearchQuery.value.trim().toLowerCase()
  if (!q) return true
  const activeName = activeSubject.value?.name || student.subject || ''
  return activeName.toLowerCase().includes(q)
})

// ── Toolbar Quick-Rename Actions ──────────────────────────────────────────
function startToolbarRename() {
  toolbarRenameInput.value = student.subject || activeSubject.value?.name || ''
  isToolbarRenaming.value = true
  isDropdownOpen.value = false
  nextTick(() => {
    toolbarRenameInputRef.value?.focus()
    toolbarRenameInputRef.value?.select()
  })
}

function saveToolbarRename() {
  if (toolbarRenameInput.value.trim()) {
    renameActiveSubject(toolbarRenameInput.value.trim())
  }
  isToolbarRenaming.value = false
}

function cancelToolbarRename() {
  isToolbarRenaming.value = false
}

// ── Dropdown Orchestration ────────────────────────────────────────────────
function toggleDropdown() {
  isDropdownOpen.value = !isDropdownOpen.value
  if (isDropdownOpen.value) {
    isToolbarRenaming.value = false
    isAdding.value = false
    editingSubjectId.value = null
    subjectSearchQuery.value = ''
  }
}

function closeDropdown() {
  isDropdownOpen.value = false
  isAdding.value = false
  editingSubjectId.value = null
  subjectSearchQuery.value = ''
}

function startAdd() {
  newSubjectInput.value = ''
  isAdding.value = true
  editingSubjectId.value = null
  nextTick(() => {
    newSubjectInputRef.value?.focus()
  })
}

function saveAdd() {
  if (newSubjectInput.value.trim()) {
    addSubject(newSubjectInput.value.trim())
    isAdding.value = false
    closeDropdown()
  }
}

function cancelAdd() {
  isAdding.value = false
}

function startRowRename(id: string, currentName: string) {
  editingSubjectId.value = id
  rowRenameInput.value = currentName
  isAdding.value = false
  nextTick(() => {
    rowRenameInputRef.value?.focus()
    rowRenameInputRef.value?.select()
  })
}

function saveRowRename(id: string) {
  if (rowRenameInput.value.trim()) {
    renameSubject(id, rowRenameInput.value.trim())
  }
  editingSubjectId.value = null
}

function cancelRowRename() {
  editingSubjectId.value = null
}

function handleClickOutside(e: MouseEvent) {
  if (dropdownRef.value && !dropdownRef.value.contains(e.target as Node)) {
    closeDropdown()
    if (isToolbarRenaming.value) {
      saveToolbarRename()
    }
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
        <!-- Subject Pill / Rename Container -->
        <div class="relative min-w-0">
          <!-- Toolbar Quick-Renaming Active State -->
          <div
            v-if="isToolbarRenaming"
            class="inline-flex items-center gap-1 bg-card border border-amber rounded-xl p-1 shadow-sm min-w-0 max-w-[200px] xs:max-w-[260px] sm:max-w-[340px] md:max-w-[400px]"
          >
            <BookOpen class="w-3.5 h-3.5 text-amber ml-1.5 shrink-0" />
            <input
              ref="toolbarRenameInputRef"
              v-model="toolbarRenameInput"
              type="text"
              class="flex-1 bg-input text-xs sm:text-sm font-semibold text-hi rounded px-2 py-1 outline-none min-w-0 focus:ring-1 focus:ring-amber"
              placeholder="Subject name"
              @keyup.enter="saveToolbarRename"
              @keyup.esc="cancelToolbarRename"
            />
            <button
              type="button"
              @click.stop="saveToolbarRename"
              class="p-1.5 text-amber hover:text-amber-hi hover:bg-input rounded-md transition cursor-pointer shrink-0"
              title="Save rename (Enter)"
              aria-label="Save rename"
            >
              <Check class="w-3.5 h-3.5" />
            </button>
            <button
              type="button"
              @click.stop="cancelToolbarRename"
              class="p-1.5 text-mid hover:text-danger hover:bg-input rounded-md transition cursor-pointer shrink-0"
              title="Cancel rename (Esc)"
              aria-label="Cancel rename"
            >
              <X class="w-3.5 h-3.5" />
            </button>
          </div>

          <!-- Normal Toolbar State: Split Pill (Title + Quick Edit + Switcher) -->
          <div
            v-else
            class="inline-flex items-center rounded-xl bg-card border border-edge hover:border-edge-hi shadow-sm transition min-w-0 max-w-[190px] xs:max-w-[250px] sm:max-w-[320px] md:max-w-[380px]"
          >
            <!-- Title Area (Click to open dropdown, double-click to rename) -->
            <button
              type="button"
              @click.stop="toggleDropdown"
              @dblclick.stop="startToolbarRename"
              class="flex items-center gap-1.5 sm:gap-2 px-2.5 sm:px-3 py-1.5 min-w-0 flex-1 hover:text-amber text-hi font-semibold text-xs sm:text-sm cursor-pointer transition text-left group"
              :title="`Current subject: ${student.subject || 'Untitled Subject'} (Click to switch, double-click to rename)`"
            >
              <BookOpen class="w-3.5 h-3.5 text-amber shrink-0" />
              <span class="truncate">{{ student.subject || 'Untitled Subject' }}</span>
            </button>

            <!-- Dedicated Edit Button -->
            <button
              type="button"
              @click.stop="startToolbarRename"
              class="p-1.5 text-mid hover:text-amber hover:bg-input rounded-md transition cursor-pointer shrink-0"
              title="Rename subject"
              aria-label="Rename subject"
            >
              <Edit2 class="w-3 h-3 sm:w-3.5 sm:h-3.5" />
            </button>

            <span class="w-[1px] h-3.5 bg-edge shrink-0"></span>

            <!-- Dropdown Chevron toggle -->
            <button
              type="button"
              @click.stop="toggleDropdown"
              class="p-1.5 sm:px-2 text-mid hover:text-hi hover:bg-input rounded-r-xl transition cursor-pointer shrink-0"
              title="Switch subjects"
              aria-label="Switch subjects"
            >
              <ChevronDown class="w-3.5 h-3.5 transition-transform shrink-0" :class="{ 'rotate-180': isDropdownOpen }" />
            </button>
          </div>

          <!-- Dropdown Popover Menu -->
          <div
            v-if="isDropdownOpen"
            class="absolute left-0 top-full mt-1.5 z-50 w-76 sm:w-84 max-w-[calc(100vw-2rem)] bg-card border border-edge rounded-xl shadow-2xl p-2.5 space-y-2 select-none animate-in fade-in"
            @click.stop
          >
            <!-- Header: Title + New Button -->
            <div class="flex items-center justify-between px-1 text-[10px] font-semibold text-mid uppercase tracking-wider">
              <span>Your Subjects ({{ subjects.length }})</span>
              <button
                type="button"
                @click="startAdd"
                class="text-amber hover:text-amber-hi font-semibold flex items-center gap-1 cursor-pointer transition"
              >
                <Plus class="w-3 h-3" />
                <span>New</span>
              </button>
            </div>

            <!-- Inline Add Subject Input -->
            <div v-if="isAdding" class="p-1.5 bg-surface rounded-lg border border-amber flex items-center gap-1.5">
              <input
                ref="newSubjectInputRef"
                v-model="newSubjectInput"
                type="text"
                placeholder="e.g. Cloud Computing"
                class="flex-1 bg-input border border-edge text-xs text-hi rounded px-2 py-1 outline-none focus:border-amber min-w-0"
                @keyup.enter="saveAdd"
                @keyup.esc="cancelAdd"
              />
              <button
                type="button"
                @click="saveAdd"
                class="text-[11px] bg-amber hover:bg-amber-hi text-surface font-semibold px-2 py-1 rounded transition cursor-pointer shrink-0"
              >
                Add
              </button>
              <button
                type="button"
                @click="cancelAdd"
                class="p-1 text-mid hover:text-danger rounded cursor-pointer shrink-0"
                title="Cancel"
              >
                <X class="w-3.5 h-3.5" />
              </button>
            </div>

            <!-- Search Filter Bar (Shown when subjects >= 3) -->
            <div v-if="subjects.length >= 3" class="relative">
              <Search class="w-3 h-3 absolute left-2.5 top-2.5 text-lo pointer-events-none" />
              <input
                v-model="subjectSearchQuery"
                type="text"
                placeholder="Search subjects..."
                class="w-full bg-input border border-edge rounded-lg pl-7 pr-7 py-1 text-xs text-hi outline-none focus:border-amber placeholder:text-lo transition"
              />
              <button
                v-if="subjectSearchQuery"
                @click="subjectSearchQuery = ''"
                class="absolute right-2 top-2 text-lo hover:text-hi p-0.5 cursor-pointer"
                title="Clear search"
              >
                <X class="w-2.5 h-2.5" />
              </button>
            </div>

            <!-- Pinned Current / Active Subject Card -->
            <div
              v-if="isCurrentSubjectMatchingSearch"
              class="p-2 rounded-lg bg-input/70 border border-edge space-y-1"
            >
              <div class="flex items-center justify-between text-[10px]">
                <span class="font-bold text-amber tracking-wider uppercase flex items-center gap-1">
                  <Check class="w-3 h-3 text-amber shrink-0" />
                  Active Subject
                </span>
                <span class="text-lo font-mono">{{ experiments.length }} doc{{ experiments.length === 1 ? '' : 's' }}</span>
              </div>

              <!-- Active row renaming state -->
              <div v-if="editingSubjectId === activeSubjectId" class="flex items-center gap-1.5 pt-0.5">
                <input
                  ref="rowRenameInputRef"
                  v-model="rowRenameInput"
                  type="text"
                  class="flex-1 bg-card border border-amber text-xs text-hi font-medium rounded px-2 py-1 outline-none min-w-0"
                  @keyup.enter="saveRowRename(activeSubjectId)"
                  @keyup.esc="cancelRowRename"
                />
                <button
                  type="button"
                  @click="saveRowRename(activeSubjectId)"
                  class="p-1 text-amber hover:text-amber-hi hover:bg-input rounded transition cursor-pointer shrink-0"
                  title="Save (Enter)"
                >
                  <Check class="w-3.5 h-3.5" />
                </button>
                <button
                  type="button"
                  @click="cancelRowRename"
                  class="p-1 text-mid hover:text-danger hover:bg-input rounded transition cursor-pointer shrink-0"
                  title="Cancel (Esc)"
                >
                  <X class="w-3.5 h-3.5" />
                </button>
              </div>

              <!-- Active row default state -->
              <div v-else class="flex items-center justify-between gap-2 pt-0.5">
                <span class="text-xs font-semibold text-hi truncate flex-1 min-w-0" :title="student.subject || activeSubject.name">
                  {{ student.subject || activeSubject.name }}
                </span>
                <button
                  type="button"
                  @click="startRowRename(activeSubjectId, student.subject || activeSubject.name)"
                  class="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium text-amber hover:bg-amber/15 border border-amber/30 transition cursor-pointer shrink-0"
                  title="Rename active subject"
                >
                  <Edit2 class="w-2.5 h-2.5" />
                  <span>Rename</span>
                </button>
              </div>
            </div>

            <!-- Other Subjects Section (Scrollable) -->
            <div v-if="filteredOtherSubjects.length" class="space-y-1">
              <div class="px-1 pt-1 text-[9px] font-semibold text-lo uppercase tracking-wider">
                <span>Switch Subject:</span>
              </div>

              <div class="max-h-48 overflow-y-auto space-y-0.5 pr-0.5">
                <div
                  v-for="s in filteredOtherSubjects"
                  :key="s.id"
                  class="group/row flex items-center justify-between px-2.5 py-1.5 rounded-lg text-xs transition"
                  :class="editingSubjectId === s.id ? 'bg-surface border border-amber' : 'text-mid hover:bg-input hover:text-hi cursor-pointer'"
                >
                  <!-- In-place row editing for this subject -->
                  <div v-if="editingSubjectId === s.id" class="flex items-center gap-1.5 w-full">
                    <input
                      ref="rowRenameInputRef"
                      v-model="rowRenameInput"
                      type="text"
                      class="flex-1 bg-input border border-edge text-xs text-hi rounded px-2 py-0.5 outline-none focus:border-amber min-w-0"
                      @keyup.enter="saveRowRename(s.id)"
                      @keyup.esc="cancelRowRename"
                    />
                    <button
                      type="button"
                      @click="saveRowRename(s.id)"
                      class="p-1 text-amber hover:text-amber-hi rounded transition cursor-pointer shrink-0"
                      title="Save"
                    >
                      <Check class="w-3.5 h-3.5" />
                    </button>
                    <button
                      type="button"
                      @click="cancelRowRename"
                      class="p-1 text-mid hover:text-danger rounded transition cursor-pointer shrink-0"
                      title="Cancel"
                    >
                      <X class="w-3.5 h-3.5" />
                    </button>
                  </div>

                  <!-- Normal row display -->
                  <template v-else>
                    <div
                      @click="switchSubject(s.id); closeDropdown()"
                      class="flex items-center gap-2 truncate flex-1 min-w-0"
                      :title="`Click to switch to ${s.name}`"
                    >
                      <span class="truncate">{{ s.name }}</span>
                    </div>

                    <div class="flex items-center gap-1.5 shrink-0 ml-2" @click.stop>
                      <span class="text-[10px] text-lo font-mono">
                        {{ (s.savedExperiments?.length || 0) }} exps
                      </span>

                      <!-- Inline Rename button for this subject -->
                      <button
                        type="button"
                        @click="startRowRename(s.id, s.name)"
                        class="p-1 text-lo hover:text-amber hover:bg-edge/40 rounded transition cursor-pointer"
                        :title="`Rename ${s.name}`"
                      >
                        <Edit2 class="w-3 h-3" />
                      </button>

                      <!-- Delete button for this subject -->
                      <button
                        type="button"
                        @click="deleteSubject(s.id)"
                        class="p-1 text-lo hover:text-danger hover:bg-edge/40 rounded transition cursor-pointer"
                        :title="`Delete ${s.name}`"
                      >
                        <Trash2 class="w-3 h-3" />
                      </button>
                    </div>
                  </template>
                </div>
              </div>
            </div>

            <!-- Empty state if search has no matches -->
            <div
              v-if="!isCurrentSubjectMatchingSearch && !filteredOtherSubjects.length"
              class="py-4 text-center text-xs text-lo"
            >
              No subjects matching "{{ subjectSearchQuery }}"
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
        Drop your experiment PDFs in the bulk upload box, or add an empty card to start typing manually.
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
        @dragstart="onDragStart($event, idx)"
        @dragend="onDragEnd"
        @dragover.prevent="onDragOver(idx)"
        @dragleave="onDragLeave(idx)"
        @drop="onDrop(idx)"
        class="transition-all rounded-xl"
        :class="{
          'opacity-40': dragStartIndex === idx,
          'ring-2 ring-amber/70 ring-offset-2 ring-offset-surface': dragOverIndex === idx && dragStartIndex !== idx
        }"
      >
        <DocumentCard :doc="exp" :index="idx" :total="experiments.length" />
      </div>
    </div>
  </div>
</template>
