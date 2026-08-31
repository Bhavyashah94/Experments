<script setup lang="ts">
import { ref } from 'vue';
import { useDocumentStore } from '@/stores/useDocumentStore';
import { UploadCloud } from 'lucide-vue-next';

const documentStore = useDocumentStore();
const isDragging = ref(false);
const fileInput = ref<HTMLInputElement | null>(null);

function handleDrop(e: DragEvent) {
  isDragging.value = false;
  if (e.dataTransfer?.files) {
    documentStore.processBulkUpload(e.dataTransfer.files);
  }
}

function handleFileInput(e: Event) {
  const files = (e.target as HTMLInputElement).files;
  if (files) {
    documentStore.processBulkUpload(files);
  }
}

function triggerFileInput() {
  fileInput.value?.click();
}
</script>

<template>
  <div
    @dragover.prevent="isDragging = true"
    @dragleave.prevent="isDragging = false"
    @drop.prevent="handleDrop"
    @click="triggerFileInput"
    class="border border-dashed rounded-xl p-6 text-center cursor-pointer transition-all duration-200"
    :class="isDragging ? 'border-white bg-zinc-800/80 scale-[1.005]' : 'border-border hover:border-zinc-500 bg-card/60'"
  >
    <input
      ref="fileInput"
      type="file"
      multiple
      accept=".pdf"
      @change="handleFileInput"
      class="hidden"
    />

    <div class="flex flex-col items-center justify-center gap-2">
      <div class="w-10 h-10 rounded-full bg-inputBg border border-border flex items-center justify-center text-zinc-300">
        <UploadCloud class="w-5 h-5" />
      </div>
      <div>
        <p class="text-xs font-semibold text-white">
          Drop all your experiment / assignment PDFs here
        </p>
        <p class="text-[11px] text-muted mt-0.5">
          Bulk multi-file upload automatically creates cards, numbers them, and extracts aim titles
        </p>
      </div>
    </div>
  </div>
</template>
