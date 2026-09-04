<script setup lang="ts">
import { ref } from 'vue'
import { batchUpload, isUploading, uploadError } from '../../store/labStore'
import { Upload, Loader2, AlertCircle } from 'lucide-vue-next'

const fileInputRef = ref<HTMLInputElement | null>(null)
const isDragging = ref(false)

function triggerFileSelect() {
  fileInputRef.value?.click()
}

function handleFileInput(e: Event) {
  const target = e.target as HTMLInputElement
  if (target.files && target.files.length > 0) {
    batchUpload(target.files)
    target.value = ''
  }
}

function handleDrop(e: DragEvent) {
  e.preventDefault()
  isDragging.value = false
  if (e.dataTransfer?.files && e.dataTransfer.files.length > 0) {
    batchUpload(e.dataTransfer.files)
  }
}
</script>

<template>
  <div
    class="bg-card border-2 border-dashed rounded-xl p-5 text-center transition-all cursor-pointer select-none group"
    :class="isDragging ? 'border-amber bg-amber-dim/20' : 'border-edge hover:border-edge-hi hover:bg-input'"
    @dragover.prevent="isDragging = true"
    @dragleave.prevent="isDragging = false"
    @drop="handleDrop"
    @click="triggerFileSelect"
  >
    <input
      ref="fileInputRef"
      type="file"
      multiple
      accept=".pdf,application/pdf"
      class="hidden"
      @change="handleFileInput"
    />

    <div class="flex flex-col items-center justify-center space-y-2">
      <div class="w-9 h-9 rounded-full bg-input border border-edge flex items-center justify-center text-mid group-hover:text-amber transition">
        <Loader2 v-if="isUploading" class="w-4 h-4 animate-spin text-amber" />
        <Upload v-else class="w-4 h-4" />
      </div>

      <div>
        <p class="text-xs font-semibold text-hi">
          {{ isUploading ? 'Extracting metadata & aims...' : 'Drop all your experiment / assignment PDFs here' }}
        </p>
        <p class="text-[11px] text-mid mt-0.5 leading-relaxed max-w-xs">
          Bulk multi-file upload automatically creates cards, numbers them, and extracts aim titles
        </p>
      </div>

      <div v-if="uploadError" class="text-[11px] text-danger flex items-center gap-1 mt-1">
        <AlertCircle class="w-3.5 h-3.5 shrink-0" />
        <span>{{ uploadError }}</span>
      </div>
    </div>
  </div>
</template>
