<script setup lang="ts">
import { ref, watch } from 'vue'
import { student, isPreviewOpen, previewItem, closePreview } from '../../store/labStore'
import { fetchCoverPreview } from '../../api/preview'
import { X, Loader2, RefreshCw, FileText, ZoomIn, ZoomOut } from '@lucide/vue'

const previewImage = ref<string | null>(null)
const isLoading = ref(false)
const errorMessage = ref<string | null>(null)
const zoomLevel = ref(100)

async function loadPreview() {
  if (!previewItem.value) return
  isLoading.value = true
  errorMessage.value = null

  try {
    const res = await fetchCoverPreview(student, previewItem.value)
    if (res.success && (res.image_data || res.image)) {
      previewImage.value = res.image_data || res.image || null
    } else {
      errorMessage.value = res.error || 'Failed to render preview'
    }
  } catch (err: any) {
    errorMessage.value = err.message || 'Network error rendering preview'
  } finally {
    isLoading.value = false
  }
}

function zoomIn() {
  if (zoomLevel.value < 160) zoomLevel.value += 15
}

function zoomOut() {
  if (zoomLevel.value > 60) zoomLevel.value -= 15
}

function resetZoom() {
  zoomLevel.value = 100
}

watch(
  () => isPreviewOpen.value,
  (open) => {
    if (open) {
      zoomLevel.value = 100
      loadPreview()
    } else {
      previewImage.value = null
    }
  }
)
</script>

<template>
  <div
    v-if="isPreviewOpen && previewItem"
    class="fixed inset-0 z-50 bg-black/80 backdrop-blur-md flex items-center justify-center p-3 sm:p-6"
    @click.self="closePreview"
  >
    <div class="w-full max-w-4xl bg-card border border-edge rounded-2xl overflow-hidden shadow-2xl flex flex-col max-h-[94vh]">
      <!-- Modal Header -->
      <div class="px-5 py-3 border-b border-edge flex items-center justify-between text-xs select-none bg-surface shrink-0">
        <div class="flex items-center gap-2 min-w-0">
          <div class="w-5 h-5 rounded-md bg-input border border-edge flex items-center justify-center text-amber shrink-0">
            <FileText class="w-3.5 h-3.5" />
          </div>
          <span class="font-bold text-hi truncate">
            A4 Cover Sheet — Exp {{ previewItem.label || previewItem.num }}
          </span>
          <span class="text-lo hidden sm:inline">&bull;</span>
          <span class="text-mid truncate max-w-sm hidden sm:inline">
            {{ previewItem.title || 'Untitled Document' }}
          </span>
        </div>

        <!-- Controls: Zoom, Refresh, Close -->
        <div class="flex items-center gap-1.5 shrink-0">
          <!-- Zoom Controls -->
          <button
            type="button"
            @click="zoomOut"
            class="p-1.5 rounded-lg text-mid hover:text-hi hover:bg-input transition cursor-pointer"
            title="Zoom out"
          >
            <ZoomOut class="w-3.5 h-3.5" />
          </button>

          <button
            type="button"
            @click="resetZoom"
            class="text-[10px] font-mono text-mid hover:text-hi px-1.5 py-1 rounded hover:bg-input transition cursor-pointer"
            title="Reset zoom"
          >
            {{ zoomLevel }}%
          </button>

          <button
            type="button"
            @click="zoomIn"
            class="p-1.5 rounded-lg text-mid hover:text-hi hover:bg-input transition cursor-pointer"
            title="Zoom in"
          >
            <ZoomIn class="w-3.5 h-3.5" />
          </button>

          <span class="w-px h-4 bg-edge mx-1"></span>

          <!-- Refresh -->
          <button
            type="button"
            @click="loadPreview"
            class="p-1.5 rounded-lg text-mid hover:text-hi hover:bg-input transition cursor-pointer"
            title="Refresh preview"
          >
            <RefreshCw class="w-3.5 h-3.5" :class="{ 'animate-spin': isLoading }" />
          </button>

          <!-- Close -->
          <button
            type="button"
            @click="closePreview"
            class="p-1.5 rounded-lg text-mid hover:text-hi hover:bg-input transition cursor-pointer"
            title="Close modal"
          >
            <X class="w-4 h-4" />
          </button>
        </div>
      </div>

      <!-- Modal Body Canvas (Deep Charcoal Canvas with Shadowed Paper) -->
      <div class="p-4 sm:p-6 flex-1 flex flex-col items-center justify-center overflow-auto bg-[#0d0d0f] relative min-h-[450px]">
        <div v-if="isLoading && !previewImage" class="flex flex-col items-center gap-2.5 text-xs text-mid my-auto">
          <Loader2 class="w-7 h-7 animate-spin text-amber" />
          <span>Generating institutional A4 cover sheet...</span>
        </div>

        <div v-else-if="errorMessage" class="text-xs text-danger text-center max-w-sm my-auto space-y-2">
          <p>{{ errorMessage }}</p>
          <button
            type="button"
            @click="loadPreview"
            class="text-xs text-amber hover:text-amber-hi underline cursor-pointer"
          >
            Retry
          </button>
        </div>

        <div
          v-else-if="previewImage"
          class="my-auto flex flex-col items-center justify-center transition-transform duration-150"
          :style="{ transform: `scale(${zoomLevel / 100})`, transformOrigin: 'top center' }"
        >
          <!-- A4 Canvas Sheet with Heavy Cast Drop-Shadow -->
          <div class="relative shadow-2xl shadow-black/90 rounded-sm border border-edge/80 overflow-hidden bg-white max-w-full">
            <img
              :src="previewImage"
              alt="Cover Preview"
              class="max-w-full h-auto object-contain block select-none"
              style="max-height: calc(90vh - 120px);"
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
    </div>
  </div>
</template>
