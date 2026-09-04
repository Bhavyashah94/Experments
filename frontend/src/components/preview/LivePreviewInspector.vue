<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import {
  student,
  experiments,
  selectedId,
  openModalPreview,
} from '../../store/labStore'
import { fetchCoverPreview } from '../../api/preview'
import {
  Eye,
  RefreshCw,
  Loader2,
  FileText,
  Sparkles,
  Maximize2,
  ZoomIn,
  ZoomOut,
  X,
} from 'lucide-vue-next'

const emit = defineEmits<{
  (e: 'close'): void
}>()

const previewImage = ref<string | null>(null)
const isLoading = ref(false)
const errorMessage = ref<string | null>(null)
const zoomLevel = ref(100) // percent
let debounceTimer: ReturnType<typeof setTimeout> | null = null

// Current active experiment to preview
const activeItem = computed(() => {
  if (experiments.value.length === 0) return null
  if (selectedId.value) {
    const found = experiments.value.find((e) => e.id === selectedId.value)
    if (found) return found
  }
  return experiments.value[0]
})

async function loadPreview() {
  if (!activeItem.value) {
    previewImage.value = null
    return
  }

  isLoading.value = true
  errorMessage.value = null

  try {
    const res = await fetchCoverPreview(student, activeItem.value)
    if (res.success && (res.image_data || res.image)) {
      previewImage.value = res.image_data || res.image || null
    } else {
      errorMessage.value = res.error || 'Failed to render cover preview'
    }
  } catch (err: any) {
    errorMessage.value = err.message || 'Network error rendering preview'
  } finally {
    isLoading.value = false
  }
}

function debouncedLoad() {
  if (debounceTimer) clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    loadPreview()
  }, 450)
}

function zoomIn() {
  if (zoomLevel.value < 150) zoomLevel.value += 15
}

function zoomOut() {
  if (zoomLevel.value > 60) zoomLevel.value -= 15
}

function resetZoom() {
  zoomLevel.value = 100
}

// Watch active item selection
watch(
  () => activeItem.value?.id,
  () => {
    loadPreview()
  }
)

// Watch item content changes (label, title, dates, etc.)
watch(
  () => [
    activeItem.value?.label,
    activeItem.value?.title,
    activeItem.value?.perf_date,
    activeItem.value?.sub_date,
    activeItem.value?.is_assignment,
  ],
  () => {
    debouncedLoad()
  }
)

// Watch student profile changes
watch(
  () => [
    student.name,
    student.roll_no,
    student.batch,
    student.class_name,
    student.sem,
    student.subject,
    student.text_color,
    student.strikethrough_enabled,
  ],
  () => {
    debouncedLoad()
  }
)

onMounted(() => {
  loadPreview()
})
</script>

<template>
  <div class="h-full w-full flex flex-col select-none overflow-hidden bg-[#0d0d0f]">
    <!-- Split Pane Header (h-11) -->
    <div class="h-11 border-b border-edge px-4 flex items-center justify-between bg-surface shrink-0">
      <div class="flex items-center gap-2 min-w-0">
        <div class="w-5 h-5 rounded-md bg-input border border-edge flex items-center justify-center text-amber shrink-0">
          <Eye class="w-3 h-3" />
        </div>
        <span class="text-xs font-semibold text-hi truncate">
          A4 Preview
        </span>
        <span
          v-if="activeItem"
          class="text-[10px] font-mono font-medium px-1.5 py-0.5 bg-input border border-edge rounded text-amber shrink-0"
        >
          Exp {{ activeItem.label || activeItem.num }}
        </span>
      </div>

      <!-- Controls: Zoom, Refresh, Fullscreen Modal, Close -->
      <div class="flex items-center gap-1 shrink-0">
        <!-- Zoom Out -->
        <button
          type="button"
          @click="zoomOut"
          class="p-1 text-mid hover:text-hi hover:bg-input rounded transition cursor-pointer"
          title="Zoom out"
        >
          <ZoomOut class="w-3.5 h-3.5" />
        </button>

        <!-- Zoom Reset -->
        <button
          type="button"
          @click="resetZoom"
          class="text-[10px] font-mono text-mid hover:text-hi px-1 rounded transition cursor-pointer"
          title="Reset zoom"
        >
          {{ zoomLevel }}%
        </button>

        <!-- Zoom In -->
        <button
          type="button"
          @click="zoomIn"
          class="p-1 text-mid hover:text-hi hover:bg-input rounded transition cursor-pointer"
          title="Zoom in"
        >
          <ZoomIn class="w-3.5 h-3.5" />
        </button>

        <span class="w-px h-3.5 bg-edge mx-1"></span>

        <!-- Refresh -->
        <button
          type="button"
          @click="loadPreview"
          class="p-1 text-mid hover:text-hi hover:bg-input rounded transition cursor-pointer"
          title="Refresh preview"
        >
          <RefreshCw class="w-3.5 h-3.5" :class="{ 'animate-spin': isLoading }" />
        </button>

        <!-- Expand Modal -->
        <button
          v-if="activeItem"
          type="button"
          @click="openModalPreview(activeItem)"
          class="p-1 text-mid hover:text-hi hover:bg-input rounded transition cursor-pointer"
          title="Expand to modal"
        >
          <Maximize2 class="w-3.5 h-3.5" />
        </button>

        <!-- Close Pane -->
        <button
          type="button"
          @click="emit('close')"
          class="p-1 text-mid hover:text-hi hover:bg-input rounded transition cursor-pointer"
          title="Close split pane"
        >
          <X class="w-3.5 h-3.5" />
        </button>
      </div>
    </div>

    <!-- Split Pane Document Canvas Viewport -->
    <div class="flex-1 min-h-0 overflow-y-auto p-4 sm:p-5 flex flex-col items-center justify-center bg-[#0d0d0f] relative">
      <!-- State 1: No Experiments Yet -->
      <div
        v-if="!activeItem"
        class="text-center p-8 space-y-3 max-w-xs my-auto"
      >
        <div class="w-10 h-10 rounded-xl bg-input border border-edge flex items-center justify-center mx-auto text-lo">
          <FileText class="w-5 h-5" />
        </div>
        <p class="text-xs font-semibold text-hi">
          No Experiment Selected
        </p>
        <p class="text-[11px] text-mid leading-relaxed">
          Add an experiment card or drop PDFs to see the real-time stamped A4 cover sheet rendered here.
        </p>
      </div>

      <!-- State 2: Initial Loading -->
      <div
        v-else-if="isLoading && !previewImage"
        class="flex flex-col items-center gap-2.5 text-xs text-mid my-auto"
      >
        <Loader2 class="w-6 h-6 animate-spin text-amber" />
        <span>Rendering A4 document...</span>
      </div>

      <!-- State 3: Error -->
      <div
        v-else-if="errorMessage"
        class="text-center p-6 space-y-2 max-w-xs my-auto"
      >
        <p class="text-xs text-danger font-medium">{{ errorMessage }}</p>
        <button
          type="button"
          @click="loadPreview"
          class="text-xs text-amber hover:text-amber-hi underline cursor-pointer"
        >
          Retry
        </button>
      </div>

      <!-- State 4: Rendered A4 Document Sheet -->
      <div
        v-else-if="previewImage"
        class="my-auto flex flex-col items-center justify-center transition-transform duration-150 w-full"
        :style="{ transform: `scale(${zoomLevel / 100})`, transformOrigin: 'top center' }"
      >
        <!-- The Paper Canvas with Crisp Drop Shadow -->
        <div class="relative shadow-2xl shadow-black/90 rounded-sm border border-edge/80 overflow-hidden bg-white max-w-full">
          <img
            :src="previewImage"
            alt="Institutional Cover Sheet Preview"
            class="max-w-full h-auto object-contain block select-none"
            style="max-height: calc(100vh - 130px);"
          />
          <div
            v-if="isLoading"
            class="absolute inset-0 bg-black/20 backdrop-blur-[1px] flex items-center justify-center transition-all"
          >
            <Loader2 class="w-6 h-6 animate-spin text-amber" />
          </div>
        </div>
      </div>
    </div>

    <!-- Split Pane Bottom Status Bar (h-7) -->
    <div class="h-7 border-t border-edge px-4 flex items-center justify-between text-[10px] text-lo bg-surface shrink-0">
      <div class="flex items-center gap-2 font-mono">
        <span>A4 Portrait (210 &times; 297mm)</span>
        <span>&bull;</span>
        <span class="uppercase">Ink: {{ student.text_color }}</span>
      </div>

      <div class="flex items-center gap-1.5 text-mid">
        <Sparkles class="w-3 h-3 text-amber" />
        <span>Live synchronized</span>
      </div>
    </div>
  </div>
</template>
