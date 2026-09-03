<script setup lang="ts">
import { computed } from 'vue';
import type { DocumentItem } from '@/types/document';
import { useDocumentStore } from '@/stores/useDocumentStore';
import {
  GripVertical,
  ChevronDown,
  ChevronRight,
  FileText,
  Eye,
  Download,
  Trash2,
  CheckCircle2,
  AlertCircle,
  Loader2,
  ArrowUp,
  ArrowDown,
} from 'lucide-vue-next';

const props = defineProps<{
  doc: DocumentItem;
  index: number;
  total: number;
}>();

defineEmits<{
  (e: 'preview', doc: DocumentItem): void;
  (e: 'move-up', index: number): void;
  (e: 'move-down', index: number): void;
}>();

const documentStore = useDocumentStore();

const isReady = computed(() => props.doc.status === 'ready' && !!props.doc.hash);

function handleFileInput(e: Event) {
  const files = (e.target as HTMLInputElement).files;
  if (files && files[0]) {
    documentStore.processFileUpload(props.doc.id, files[0]);
  }
}

function handleDrop(e: DragEvent) {
  if (e.dataTransfer?.files && e.dataTransfer.files[0]) {
    documentStore.processFileUpload(props.doc.id, e.dataTransfer.files[0]);
  }
}
</script>

<template>
  <div class="bg-card border border-border rounded-xl overflow-hidden shadow-sm transition-all duration-150">
    <!-- Accordion Header -->
    <div
      class="flex flex-wrap sm:flex-nowrap items-center gap-2.5 px-4 py-3 cursor-pointer hover:bg-zinc-800/40 select-none"
      @click="doc.isOpen = !doc.isOpen"
    >
      <!-- Dedicated Drag Handle -->
      <div
        class="drag-handle p-1.5 text-zinc-500 hover:text-white cursor-grab active:cursor-grabbing shrink-0 touch-none rounded hover:bg-zinc-800/80 transition"
        @click.stop
        title="Drag to reorder experiment card"
      >
        <GripVertical class="w-4 h-4 pointer-events-none" />
      </div>

      <!-- Exp / Assign Type Badge -->
      <button
        type="button"
        @click.stop="doc.isAssignment = !doc.isAssignment"
        class="text-xs font-mono font-bold px-2 py-0.5 rounded border transition shrink-0"
        :class="doc.isAssignment ? 'bg-zinc-900 border-zinc-700 text-zinc-300' : 'bg-zinc-800 border-border text-white'"
        title="Click to toggle between Experiment and Assignment"
      >
        {{ doc.isAssignment ? 'Assign' : 'Exp' }}
      </button>

      <!-- Label Number Input -->
      <div class="flex items-center gap-1 shrink-0" @click.stop>
        <span class="text-xs text-muted">No.</span>
        <input
          type="text"
          v-model="doc.label"
          class="w-10 bg-inputBg border border-border rounded px-1.5 py-0.5 text-xs text-white text-center font-mono outline-none focus:border-zinc-400"
        />
      </div>

      <!-- Title Preview Text -->
      <span
        class="order-last sm:order-none basis-full sm:basis-auto sm:flex-1 text-xs truncate mt-1 sm:mt-0"
        :class="doc.title ? 'text-zinc-200 font-medium' : 'italic text-muted'"
      >
        {{ doc.title || 'Untitled Document' }}
      </span>

      <!-- Page Count Badge -->
      <span
        v-if="doc.pages > 0"
        class="text-[11px] font-mono text-zinc-400 bg-inputBg border border-border px-2 py-0.5 rounded shrink-0 hidden sm:inline-block"
      >
        {{ doc.pages }} {{ doc.pages === 1 ? 'page' : 'pages' }}
      </span>

      <!-- Ready Status Indicator Dot -->
      <span
        v-if="isReady"
        class="w-2 h-2 rounded-full bg-emerald-400 shrink-0"
        title="PDF Attached and verified"
      ></span>

      <!-- Accessible Move Up / Down Buttons -->
      <div class="flex items-center gap-0.5 shrink-0" @click.stop>
        <button
          v-if="index > 0"
          type="button"
          @click="$emit('move-up', index)"
          class="p-1 text-zinc-500 hover:text-white rounded hover:bg-zinc-800 transition"
          title="Move card up"
          aria-label="Move card up"
        >
          <ArrowUp class="w-3.5 h-3.5" />
        </button>
        <button
          v-if="index < total - 1"
          type="button"
          @click="$emit('move-down', index)"
          class="p-1 text-zinc-500 hover:text-white rounded hover:bg-zinc-800 transition"
          title="Move card down"
          aria-label="Move card down"
        >
          <ArrowDown class="w-3.5 h-3.5" />
        </button>
      </div>

      <!-- Action Buttons -->
      <div class="flex items-center gap-1.5 shrink-0" @click.stop>
        <button
          type="button"
          @click="$emit('preview', doc)"
          class="inline-flex items-center gap-1 text-xs text-subtle hover:text-white bg-inputBg border border-border hover:border-zinc-400 px-2.5 py-1 rounded-lg transition"
          title="Live preview cover page"
        >
          <Eye class="w-3.5 h-3.5" />
          <span class="hidden sm:inline">Preview</span>
        </button>

        <button
          type="button"
          @click="documentStore.downloadSingleDocument(doc)"
          :disabled="documentStore.isGenerating"
          class="inline-flex items-center gap-1 text-xs text-subtle hover:text-white bg-inputBg border border-border hover:border-zinc-400 px-2.5 py-1 rounded-lg transition disabled:opacity-50"
          title="Download single experiment with header"
        >
          <Download class="w-3.5 h-3.5" />
          <span class="hidden sm:inline">Download</span>
        </button>

        <button
          type="button"
          @click="documentStore.removeDocument(doc.id)"
          class="p-1.5 text-zinc-500 hover:text-red-400 rounded-lg hover:bg-zinc-800 transition"
          title="Remove document card"
          aria-label="Remove document card"
        >
          <Trash2 class="w-3.5 h-3.5" />
        </button>
      </div>

      <!-- Collapse Chevron -->
      <div class="text-zinc-500 shrink-0">
        <ChevronDown v-if="doc.isOpen" class="w-4 h-4" />
        <ChevronRight v-else class="w-4 h-4" />
      </div>
    </div>

    <!-- Accordion Body -->
    <div v-show="doc.isOpen" class="p-4 bg-surface/50 border-t border-border space-y-4">
      <!-- Aim / Title Input -->
      <div>
        <label class="block text-[11px] font-medium text-muted uppercase tracking-wider mb-1.5">
          Aim / Title of {{ doc.isAssignment ? 'Assignment' : 'Experiment' }}
        </label>
        <input
          type="text"
          v-model="doc.title"
          placeholder="e.g. Study and Implementation of MQTT Protocol for Sensor Nodes"
          class="w-full bg-inputBg border border-border text-xs text-white rounded-lg px-3 py-2 outline-none focus:border-zinc-400 transition"
        />
      </div>

      <!-- Dates Row -->
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div>
          <label class="block text-[11px] font-medium text-muted uppercase tracking-wider mb-1.5">
            Performance Date
          </label>
          <input
            type="text"
            v-model="doc.perfDate"
            placeholder="DD/MM/YYYY"
            class="w-full bg-inputBg border border-border text-xs text-white rounded-lg px-3 py-2 outline-none focus:border-zinc-400 transition"
          />
        </div>

        <div>
          <label class="block text-[11px] font-medium text-muted uppercase tracking-wider mb-1.5">
            Submission Date
          </label>
          <input
            type="text"
            v-model="doc.subDate"
            placeholder="DD/MM/YYYY"
            class="w-full bg-inputBg border border-border text-xs text-white rounded-lg px-3 py-2 outline-none focus:border-zinc-400 transition"
          />
        </div>
      </div>

      <p class="text-[10px] text-zinc-500 -mt-1">
        Use DD/MM/YYYY format for both dates.
      </p>

      <!-- Individual File Drop Area -->
      <div>
        <label
          class="border border-dashed border-border hover:border-zinc-400 bg-inputBg/40 hover:bg-inputBg/80 rounded-lg p-3 text-center cursor-pointer transition flex items-center justify-center gap-2 group"
          @dragover.prevent
          @drop.prevent="handleDrop"
        >
          <input
            type="file"
            accept=".pdf,application/pdf"
            class="hidden"
            @change="handleFileInput"
          />

          <Loader2 v-if="doc.status === 'uploading'" class="w-4 h-4 animate-spin text-zinc-400" />
          <CheckCircle2 v-else-if="isReady" class="w-4 h-4 text-emerald-400" />
          <AlertCircle v-else-if="doc.status === 'error'" class="w-4 h-4 text-red-400" />
          <FileText v-else class="w-4 h-4 text-zinc-500 group-hover:text-zinc-300 transition" />

          <span class="text-xs text-zinc-300">
            <template v-if="doc.status === 'uploading'">Processing and extracting aim...</template>
            <template v-else-if="doc.status === 'ready' && doc.filename">
              Attached: <strong class="text-white">{{ doc.filename }}</strong> ({{ doc.pages }} pages)
            </template>
            <template v-else-if="doc.status === 'error'">
              {{ doc.errorMessage || 'Upload failed. Click to retry.' }}
            </template>
            <template v-else>
              Drop body PDF file here or click to attach
            </template>
          </span>
        </label>
      </div>
    </div>
  </div>
</template>
