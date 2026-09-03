<script setup lang="ts">
import { ref } from 'vue';
import { useLabStore } from '../store';
import {
  UploadCloud,
  FileText,
  Plus,
  Trash2,
  ArrowUp,
  ArrowDown,
  Loader2,
  CheckCircle2,
  AlertCircle,
  Eye,
} from 'lucide-vue-next';

const store = useLabStore();
const fileInputRef = ref<HTMLInputElement | null>(null);
const isDragActive = ref(false);

function onDrop(e: DragEvent) {
  isDragActive.value = false;
  if (e.dataTransfer?.files && e.dataTransfer.files.length > 0) {
    store.bulkUpload(e.dataTransfer.files);
  }
}

function onFileInput(e: Event) {
  const files = (e.target as HTMLInputElement).files;
  if (files && files.length > 0) {
    store.bulkUpload(files);
  }
}

function triggerFileInput() {
  fileInputRef.value?.click();
}

function handleSingleUpload(docId: string, e: Event) {
  const files = (e.target as HTMLInputElement).files;
  if (files && files[0]) {
    store.uploadFile(docId, files[0]);
  }
}
</script>

<template>
  <div class="space-y-4">
    <!-- 1. Prominent Bulk Dropzone -->
    <div
      class="border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition flex flex-col items-center justify-center gap-2.5 select-none"
      :class="isDragActive ? 'border-blue-500 bg-blue-950/20' : 'border-[#27272a] hover:border-zinc-500 bg-[#141417]/60'"
      @dragover.prevent="isDragActive = true"
      @dragleave.prevent="isDragActive = false"
      @drop.prevent="onDrop"
      @click="triggerFileInput"
    >
      <input
        ref="fileInputRef"
        type="file"
        multiple
        accept=".pdf,application/pdf"
        class="hidden"
        @change="onFileInput"
      />

      <div class="w-10 h-10 rounded-full bg-zinc-800 flex items-center justify-center text-zinc-300">
        <UploadCloud class="w-5 h-5" />
      </div>

      <div>
        <p class="text-xs font-semibold text-white">
          Drop all your Experiment PDFs here, or <span class="text-blue-400 underline">browse files</span>
        </p>
        <p class="text-[11px] text-zinc-400 mt-0.5">
          Auto-detects experiment numbers, aims, and page counts instantly
        </p>
      </div>
    </div>

    <!-- 2. Queue Header & Controls -->
    <div class="flex items-center justify-between px-1">
      <div class="flex items-center gap-2">
        <span class="text-xs font-semibold text-zinc-300 uppercase tracking-wider">
          Experiments Queue ({{ store.documents.length }})
        </span>
        <span v-if="store.totalPages > 0" class="text-[11px] text-zinc-400 font-mono">
          · {{ store.totalPages }} total pages
        </span>
      </div>

      <div class="flex items-center gap-2">
        <button
          type="button"
          @click="store.addDocument"
          class="inline-flex items-center gap-1 text-xs text-white bg-zinc-800 hover:bg-zinc-700 border border-zinc-600 px-2.5 py-1 rounded-lg font-medium transition"
        >
          <Plus class="w-3.5 h-3.5" />
          <span>Add Experiment</span>
        </button>
      </div>
    </div>

    <!-- 3. Document Rows -->
    <div class="space-y-2.5">
      <div
        v-for="(doc, idx) in store.documents"
        :key="doc.id"
        class="bg-[#141417] border rounded-xl p-3.5 transition shadow-sm space-y-2.5 cursor-pointer"
        :class="store.selectedDocId === doc.id ? 'border-blue-500/80 ring-1 ring-blue-500/30' : 'border-[#27272a] hover:border-zinc-600'"
        @click="store.selectedDocId = doc.id"
      >
        <!-- Top Row: Number, Type, Pages, Status & Controls -->
        <div class="flex items-center justify-between gap-2">
          <div class="flex items-center gap-2">
            <!-- Exp vs Assign Toggle Pill -->
            <button
              type="button"
              @click.stop="doc.isAssignment = !doc.isAssignment"
              class="text-xs font-mono font-bold px-2 py-0.5 rounded border transition shrink-0"
              :class="doc.isAssignment ? 'bg-zinc-900 border-zinc-700 text-zinc-300' : 'bg-zinc-800 border-zinc-600 text-white'"
              title="Click to toggle between Experiment and Assignment"
            >
              {{ doc.isAssignment ? 'Assign' : 'Exp' }}
            </button>

            <!-- Number Input -->
            <div class="flex items-center gap-1" @click.stop>
              <span class="text-[11px] text-zinc-400">No.</span>
              <input
                type="text"
                v-model="doc.num"
                class="w-10 bg-[#1c1c21] border border-[#27272a] rounded px-1.5 py-0.5 text-xs text-white text-center font-mono outline-none focus:border-zinc-400"
              />
            </div>

            <!-- Page Count Badge -->
            <span
              v-if="doc.pages > 0"
              class="text-[10px] font-mono text-zinc-400 bg-[#1c1c21] border border-[#27272a] px-2 py-0.5 rounded"
            >
              {{ doc.pages }} {{ doc.pages === 1 ? 'page' : 'pages' }}
            </span>

            <!-- Status Indicator -->
            <div class="flex items-center gap-1">
              <Loader2 v-if="doc.status === 'uploading'" class="w-3.5 h-3.5 animate-spin text-blue-400" />
              <CheckCircle2 v-else-if="doc.status === 'ready'" class="w-3.5 h-3.5 text-emerald-400" title="PDF Attached" />
              <AlertCircle v-else-if="doc.status === 'error'" class="w-3.5 h-3.5 text-red-400" :title="doc.errorMsg || 'Upload Error'" />
            </div>
          </div>

          <!-- Reorder & Action Buttons -->
          <div class="flex items-center gap-1" @click.stop>
            <button
              type="button"
              @click="store.selectedDocId = doc.id"
              class="inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded border transition"
              :class="store.selectedDocId === doc.id ? 'bg-blue-600 text-white border-blue-500' : 'bg-[#1c1c21] text-zinc-300 border-[#27272a] hover:text-white'"
              title="Inspect cover page on live preview"
            >
              <Eye class="w-3 h-3" />
              <span class="hidden sm:inline">Preview</span>
            </button>

            <button
              v-if="idx > 0"
              type="button"
              @click="store.reorder(idx, idx - 1)"
              class="p-1 text-zinc-400 hover:text-white rounded hover:bg-zinc-800 transition"
              title="Move up"
            >
              <ArrowUp class="w-3.5 h-3.5" />
            </button>

            <button
              v-if="idx < store.documents.length - 1"
              type="button"
              @click="store.reorder(idx, idx + 1)"
              class="p-1 text-zinc-400 hover:text-white rounded hover:bg-zinc-800 transition"
              title="Move down"
            >
              <ArrowDown class="w-3.5 h-3.5" />
            </button>

            <button
              type="button"
              @click="store.removeDocument(doc.id)"
              class="p-1 text-zinc-500 hover:text-red-400 rounded hover:bg-zinc-800 transition"
              title="Remove experiment"
            >
              <Trash2 class="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        <!-- Middle: Aim / Title Input (Compulsory) -->
        <div @click.stop>
          <div class="flex items-center justify-between mb-1">
            <label class="text-[11px] font-medium text-zinc-400 uppercase tracking-wider">
              Aim / Title <span class="text-red-400 font-bold">*</span>
            </label>
            <span v-if="!doc.title.trim()" class="text-[10px] text-amber-400 font-medium">
              Required
            </span>
          </div>
          <input
            type="text"
            v-model="doc.title"
            placeholder="e.g. Study and Implementation of MQTT Protocol for Sensor Nodes"
            class="w-full bg-[#1c1c21] border text-xs text-white rounded-lg px-3 py-2 outline-none focus:border-zinc-400 transition"
            :class="!doc.title.trim() ? 'border-amber-900/60 focus:border-amber-500' : 'border-[#27272a]'"
          />
        </div>

        <!-- Bottom Row: Dates (Optional) + File Attachment -->
        <div class="grid grid-cols-1 sm:grid-cols-3 gap-2 pt-1" @click.stop>
          <!-- Perf Date -->
          <div>
            <label class="block text-[10px] text-zinc-500 uppercase tracking-wider mb-1">
              Perf Date <span class="lowercase">(optional)</span>
            </label>
            <input
              type="text"
              v-model="doc.perfDate"
              placeholder="DD/MM/YYYY"
              class="w-full bg-[#1c1c21] border border-[#27272a] text-xs font-mono text-white rounded-lg px-2.5 py-1.5 outline-none focus:border-zinc-400 transition"
            />
          </div>

          <!-- Sub Date -->
          <div>
            <label class="block text-[10px] text-zinc-500 uppercase tracking-wider mb-1">
              Sub Date <span class="lowercase">(optional)</span>
            </label>
            <input
              type="text"
              v-model="doc.subDate"
              placeholder="DD/MM/YYYY"
              class="w-full bg-[#1c1c21] border border-[#27272a] text-xs font-mono text-white rounded-lg px-2.5 py-1.5 outline-none focus:border-zinc-400 transition"
            />
          </div>

          <!-- PDF Attachment Button/Chip -->
          <div>
            <label class="block text-[10px] text-zinc-500 uppercase tracking-wider mb-1">
              Attached PDF
            </label>
            <label class="flex items-center gap-1.5 bg-[#1c1c21] hover:bg-zinc-800 border border-[#27272a] hover:border-zinc-500 rounded-lg px-2.5 py-1.5 cursor-pointer transition text-xs truncate">
              <input
                type="file"
                accept=".pdf,application/pdf"
                class="hidden"
                @change="(e) => handleSingleUpload(doc.id, e)"
              />
              <FileText class="w-3.5 h-3.5 text-zinc-400 shrink-0" />
              <span class="truncate text-zinc-300" :title="doc.filename || 'Attach PDF'">
                {{ doc.filename || 'Attach PDF' }}
              </span>
            </label>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
