<script setup lang="ts">
import { ref, watch } from 'vue'
import { student, isPreviewOpen, previewItem, closePreview } from '../../store/labStore'
import { fetchCoverPreview } from '../../api/preview'
import { X, Loader2, RefreshCw, FileText } from 'lucide-vue-next'

const previewImage = ref<string | null>(null)
const isLoading = ref(false)
const errorMessage = ref<string | null>(null)

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

watch(
  () => isPreviewOpen.value,
  (open) => {
    if (open) {
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
    class="fixed inset-0 z-50 bg-surface/85 backdrop-blur-sm flex items-center justify-center p-4 sm:p-6"
    @click.self="closePreview"
  >
    <div class="w-full max-w-2xl bg-card border border-edge rounded-2xl overflow-hidden shadow-2xl flex flex-col max-h-[90vh]">
      <!-- Modal Header -->
      <div class="px-5 py-3.5 border-b border-edge flex items-center justify-between text-xs select-none">
        <div class="flex items-center gap-2">
          <FileText class="w-4 h-4 text-amber" />
          <span class="font-bold text-hi">
            Cover Sheet Preview — Exp {{ previewItem.label || previewItem.num }}
          </span>
          <span class="text-lo hidden sm:inline">&bull;</span>
          <span class="text-mid truncate max-w-xs hidden sm:inline">
            {{ previewItem.title || 'Untitled' }}
          </span>
        </div>

        <div class="flex items-center gap-2">
          <button
            type="button"
            @click="loadPreview"
            class="p-1.5 rounded-lg text-mid hover:text-hi hover:bg-input transition cursor-pointer"
            title="Refresh preview"
          >
            <RefreshCw class="w-3.5 h-3.5" :class="{ 'animate-spin': isLoading }" />
          </button>

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

      <!-- Modal Body Canvas -->
      <div class="p-6 flex-1 flex flex-col items-center justify-center overflow-auto bg-surface min-h-[400px]">
        <div v-if="isLoading" class="flex flex-col items-center gap-2 text-xs text-mid">
          <Loader2 class="w-6 h-6 animate-spin text-amber" />
          <span>Generating institutional A4 cover sheet...</span>
        </div>

        <div v-else-if="errorMessage" class="text-xs text-danger text-center max-w-sm">
          <span>{{ errorMessage }}</span>
        </div>

        <div v-else-if="previewImage" class="relative group shadow-2xl">
          <img
            :src="previewImage"
            alt="Cover Preview"
            class="max-w-full h-auto rounded border border-edge bg-white object-contain"
            style="max-height: 560px;"
          />
        </div>
      </div>
    </div>
  </div>
</template>
