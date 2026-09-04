<script setup lang="ts">
import { ref } from 'vue'
import { isGuideOpen, toastMessage, undoStack, undoRemove } from '../store/labStore'
import StudentProfileCard from '../components/sidebar/StudentProfileCard.vue'
import ColorOptionsCard from '../components/sidebar/ColorOptionsCard.vue'
import DateScheduleCard from '../components/sidebar/DateScheduleCard.vue'
import BulkUploadCard from '../components/sidebar/BulkUploadCard.vue'
import DocumentList from '../components/documents/DocumentList.vue'
import CompilationCenter from '../components/documents/CompilationCenter.vue'
import LivePreviewModal from '../components/modals/LivePreviewModal.vue'
import FormatGuideModal from '../components/modals/FormatGuideModal.vue'
import ProfileShareModal from '../components/modals/ProfileShareModal.vue'
import LivePreviewInspector from '../components/preview/LivePreviewInspector.vue'
import { HelpCircle, Undo2, PanelRightClose, PanelRightOpen } from 'lucide-vue-next'

const DEFAULT_PREVIEW_WIDTH = 520
const MIN_PREVIEW_WIDTH = 380

const showInspector = ref(true)
const previewWidth = ref(
  parseInt(localStorage.getItem('labstudio_preview_width') || String(DEFAULT_PREVIEW_WIDTH), 10)
)
const isDragging = ref(false)
const startX = ref(0)
const startWidth = ref(0)

function onResizeStart(e: MouseEvent) {
  isDragging.value = true
  startX.value = e.clientX
  startWidth.value = previewWidth.value
  document.body.style.cursor = 'col-resize'
  document.body.style.userSelect = 'none'

  function onMouseMove(moveEvent: MouseEvent) {
    const delta = startX.value - moveEvent.clientX
    const maxWidth = Math.round(window.innerWidth * 0.55)
    const newWidth = Math.max(MIN_PREVIEW_WIDTH, Math.min(maxWidth, startWidth.value + delta))
    previewWidth.value = Math.round(newWidth)
  }

  function onMouseUp() {
    isDragging.value = false
    document.body.style.cursor = ''
    document.body.style.userSelect = ''
    window.removeEventListener('mousemove', onMouseMove)
    window.removeEventListener('mouseup', onMouseUp)
    localStorage.setItem('labstudio_preview_width', String(previewWidth.value))
  }

  window.addEventListener('mousemove', onMouseMove)
  window.addEventListener('mouseup', onMouseUp)
}

function resetPreviewWidth() {
  previewWidth.value = DEFAULT_PREVIEW_WIDTH
  localStorage.setItem('labstudio_preview_width', String(DEFAULT_PREVIEW_WIDTH))
}
</script>

<template>
  <div class="h-screen w-screen bg-surface text-hi flex flex-col overflow-hidden antialiased selection:bg-amber-dim/50 selection:text-hi">
    <!-- Top Edge-to-Edge Sticky Navbar (h-12) -->
    <header class="h-12 border-b border-edge bg-surface/95 backdrop-blur-md px-4 sm:px-6 flex items-center justify-between shrink-0 z-30">
      <!-- Left: Logo & Subtitle -->
      <div class="flex items-center gap-3">
        <h1 class="text-sm font-bold text-hi tracking-tight whitespace-nowrap flex items-center gap-2">
          <span>LabStudio</span>
          <span class="text-[10px] font-mono font-medium px-1.5 py-0.5 rounded bg-input border border-edge text-mid">v3.1</span>
        </h1>
        <span class="text-lo hidden md:inline">&bull;</span>
        <p class="text-[11px] text-mid hidden md:block">
          Standardized Lab Reports Studio
        </p>
      </div>

      <!-- Right: Inspector Toggle & Guide Button -->
      <div class="flex items-center gap-2">
        <!-- Big Screen Live Preview Split-Pane Toggle -->
        <button
          type="button"
          @click="showInspector = !showInspector"
          class="hidden xl:inline-flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-lg border transition cursor-pointer"
          :class="showInspector
            ? 'bg-amber text-surface border-amber font-semibold shadow-sm hover:bg-amber-hi'
            : 'text-mid hover:text-hi hover:bg-input border-edge'"
          :title="showInspector ? 'Hide Preview Split Pane' : 'Open Preview Split Pane'"
        >
          <component :is="showInspector ? PanelRightClose : PanelRightOpen" class="w-3.5 h-3.5" />
          <span>{{ showInspector ? 'Split Preview On' : 'Split Preview' }}</span>
        </button>

        <button
          type="button"
          @click="isGuideOpen = true"
          class="text-xs text-mid hover:text-hi transition px-2.5 py-1 rounded-lg hover:bg-input inline-flex items-center gap-1.5 border border-transparent hover:border-edge cursor-pointer"
          title="Formatting & Auto-Aim guide"
        >
          <HelpCircle class="w-3.5 h-3.5 text-amber" />
          <span>Guide</span>
        </button>
      </div>
    </header>

    <!-- Main Split Layout: [ (Left Pane | Right Pane) | Preview Pane ] -->
    <div class="flex-1 min-h-0 flex overflow-hidden">
      <!-- 1. The Core App Container: (Left Pane | Right Pane) centered together -->
      <div class="flex-1 min-w-0 overflow-y-auto bg-surface p-4 sm:p-6 lg:p-8">
        <div class="max-w-6xl xl:max-w-7xl mx-auto flex flex-col lg:flex-row gap-6 items-start">
          <!-- LEFT PANE: Controls Sidebar (Student Details, Ink, Schedule, Upload) -->
          <aside class="w-full lg:w-80 xl:w-[320px] 2xl:w-[340px] shrink-0 lg:sticky lg:top-0 space-y-4">
            <!-- 1. Student Details Section -->
            <StudentProfileCard />

            <!-- 2. Ink & Options Section -->
            <ColorOptionsCard />

            <!-- 3. Date Schedule Section -->
            <DateScheduleCard />

            <!-- 4. Bulk PDF Upload Dropzone -->
            <BulkUploadCard />

            <!-- Sidebar Compact Credits Footer -->
            <div class="pt-3 border-t border-edge text-[11px] text-lo flex items-center justify-between select-none">
              <span>LabStudio v3.1</span>
              <div class="flex items-center gap-1 text-mid">
                <span>Built by</span>
                <a
                  href="https://github.com/Bhavyashah94"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="text-hi hover:text-amber transition underline font-medium"
                >
                  Bhavya Shah
                </a>
                <span>&amp;</span>
                <a
                  href="https://antigravity.google"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="text-hi hover:text-amber transition underline font-medium"
                >
                  Antigravity
                </a>
              </div>
            </div>
          </aside>

          <!-- RIGHT PANE: Document Cards Workspace + Compilation Center -->
          <main class="flex-1 min-w-0 space-y-4">
            <!-- Document Cards List -->
            <DocumentList />

            <!-- Sticky Compilation Center -->
            <CompilationCenter />
          </main>
        </div>
      </div>

      <!-- Draggable Splitter Divider (Between Workspace and Preview) -->
      <div
        v-if="showInspector"
        @mousedown="onResizeStart"
        @dblclick="resetPreviewWidth"
        class="hidden xl:flex items-center justify-center relative select-none z-20 cursor-col-resize group shrink-0 w-2 -ml-1 bg-transparent hover:bg-amber/20 transition-colors"
        :class="{ 'bg-amber/30': isDragging }"
        title="Drag to resize preview • Double-click to reset"
      >
        <!-- Grip indicator on hover/drag -->
        <div
          class="w-1 h-8 rounded-full bg-edge group-hover:bg-amber transition-colors"
          :class="{ 'bg-amber': isDragging }"
        ></div>
      </div>

      <!-- 2. The Dedicated A4 Preview Pane Sidecar (Draggable Width) -->
      <section
        v-if="showInspector"
        class="hidden xl:flex shrink-0 border-l border-edge bg-[#0d0d0f] flex-col overflow-hidden"
        :style="{ width: `${previewWidth}px` }"
      >
        <LivePreviewInspector @close="showInspector = false" />
      </section>
    </div>

    <!-- Live Preview Modal (Fallback & Fullscreen modal) -->
    <LivePreviewModal />

    <!-- Formatting Guide Modal -->
    <FormatGuideModal />

    <!-- Subject Profile Share / Import Modal -->
    <ProfileShareModal />

    <!-- Undo Removal Snackbar -->
    <div
      v-if="undoStack.length > 0"
      class="fixed bottom-6 left-6 z-50 bg-card border border-edge shadow-2xl px-3.5 py-2 rounded-xl text-xs text-hi flex items-center gap-3 animate-in fade-in"
    >
      <span class="text-mid">Removed document card</span>
      <button
        type="button"
        @click="undoRemove"
        class="text-amber hover:text-amber-hi font-semibold inline-flex items-center gap-1 underline cursor-pointer"
      >
        <Undo2 class="w-3 h-3" />
        <span>Undo</span>
      </button>
    </div>

    <!-- Global Toast Notification -->
    <div
      v-if="toastMessage"
      class="fixed bottom-6 right-6 z-50 bg-card border border-edge shadow-2xl px-4 py-2.5 rounded-xl text-xs text-hi flex items-center animate-in fade-in"
    >
      <span>{{ toastMessage }}</span>
    </div>
  </div>
</template>
