<script setup lang="ts">
import { ref, watch, onMounted, computed } from 'vue';
import { useLabStore } from '../store';
import { Api } from '../api';
import { useDebounceFn } from '@vueuse/core';
import { Eye, Loader2, RefreshCw, Layers, ZoomIn, ZoomOut } from 'lucide-vue-next';

const store = useLabStore();

const activeTab = ref<'cover' | 'toc'>('cover');
const previewImage = ref<string | null>(null);
const isLoading = ref(false);
const errorMsg = ref<string | null>(null);
const isZoomed = ref(false);

// AbortController to cancel pending in-flight requests and prevent race conditions
let activeAbortController: AbortController | null = null;

const fetchPreview = useDebounceFn(async () => {
  if (!store.selectedDoc) {
    previewImage.value = null;
    return;
  }

  // Cancel prior in-flight preview request
  if (activeAbortController) {
    activeAbortController.abort();
  }
  activeAbortController = new AbortController();

  isLoading.value = true;
  errorMsg.value = null;

  try {
    // Nested structure expected by app.py /api/preview
    const payload = {
      student: {
        name: store.student.name || '',
        roll_no: store.student.rollNo || '',
        batch: store.student.batch || '',
        class_name: store.student.className || '',
        sem: store.student.sem || '',
        subject: store.student.subject || '',
        text_color: store.student.textColor || '#0000bf',
        strikethrough_enabled: store.student.strikethrough,
      },
      item: {
        experiment_number: store.selectedDoc.num || '1',
        title: store.selectedDoc.title || 'Aim / Title of Experiment',
        perf_date: store.selectedDoc.perfDate || '',
        sub_date: store.selectedDoc.subDate || '',
        is_assignment: store.selectedDoc.isAssignment,
      },
      text_color: store.student.textColor || '#0000bf',
      strikethrough_enabled: store.student.strikethrough,
    };

    const res = await Api.previewHeader(payload);
    const rawImage = res.image_data || res.image;
    if (res.success && rawImage) {
      // Backend may already include data:image/png;base64,
      previewImage.value = rawImage.startsWith('data:')
        ? rawImage
        : `data:image/png;base64,${rawImage}`;
    } else {
      errorMsg.value = res.error || 'Preview unavailable';
    }
  } catch (e: any) {
    if (e.name !== 'AbortError') {
      errorMsg.value = e.message || 'Error generating preview';
    }
  } finally {
    isLoading.value = false;
  }
}, 300);

// Calculate page ranges for TOC preview
const tocEntries = computed(() => {
  let currentPage = 1;
  return store.documents.map((d) => {
    const pages = Math.max(d.pages || 1, 1);
    const startP = currentPage;
    const endP = currentPage + pages - 1;
    currentPage = endP + 1;
    return {
      ...d,
      pageRange: `${startP}-${endP}`,
    };
  });
});

// Re-fetch whenever selected document or student info changes
watch(
  [
    () => store.selectedDocId,
    () => store.selectedDoc?.title,
    () => store.selectedDoc?.num,
    () => store.selectedDoc?.perfDate,
    () => store.selectedDoc?.subDate,
    () => store.selectedDoc?.isAssignment,
    () => store.student.name,
    () => store.student.rollNo,
    () => store.student.batch,
    () => store.student.className,
    () => store.student.sem,
    () => store.student.subject,
    () => store.student.textColor,
    () => store.student.strikethrough,
  ],
  () => {
    fetchPreview();
  },
  { deep: true }
);

onMounted(() => {
  fetchPreview();
});
</script>

<template>
  <div class="bg-surface border border-border rounded-xl overflow-hidden flex flex-col h-full sticky top-20 shadow-sm">
    <!-- Inspector Top Bar -->
    <div class="flex items-center justify-between px-4 py-3 border-b border-border bg-surface-hover/50">
      <div class="flex items-center gap-2">
        <Eye class="w-4 h-4 text-blue-400" />
        <span class="text-xs font-semibold text-white">Live Inspector</span>
        <span v-if="store.selectedDoc" class="text-[11px] text-zinc-400 font-mono">
          ({{ store.selectedDoc.isAssignment ? 'Assign' : 'Exp' }} {{ store.selectedDoc.num }})
        </span>
      </div>

      <div class="flex items-center gap-1.5">
        <button
          type="button"
          @click="isZoomed = !isZoomed"
          class="p-1 text-zinc-400 hover:text-white rounded hover:bg-zinc-800 transition"
          :title="isZoomed ? 'Reset zoom' : 'Enlarge cover page'"
          :aria-label="isZoomed ? 'Reset zoom' : 'Enlarge cover page'"
        >
          <ZoomOut v-if="isZoomed" class="w-3.5 h-3.5 text-blue-400" />
          <ZoomIn v-else class="w-3.5 h-3.5" />
        </button>

        <button
          type="button"
          @click="fetchPreview"
          class="p-1 text-zinc-400 hover:text-white rounded hover:bg-zinc-800 transition"
          title="Refresh preview"
          aria-label="Refresh preview"
        >
          <RefreshCw class="w-3.5 h-3.5" :class="isLoading ? 'animate-spin' : ''" />
        </button>
      </div>
    </div>

    <!-- Inspector Tabs -->
    <div class="flex border-b border-border bg-surface text-xs">
      <button
        type="button"
        @click="activeTab = 'cover'"
        class="flex-1 py-2 text-center font-medium border-b-2 transition"
        :class="activeTab === 'cover' ? 'border-white text-white bg-zinc-800/30' : 'border-transparent text-zinc-400 hover:text-zinc-200'"
      >
        Cover Page
      </button>

      <button
        type="button"
        @click="activeTab = 'toc'"
        class="flex-1 py-2 text-center font-medium border-b-2 transition"
        :class="activeTab === 'toc' ? 'border-white text-white bg-zinc-800/30' : 'border-transparent text-zinc-400 hover:text-zinc-200'"
      >
        Index / TOC
      </button>
    </div>

    <!-- Canvas Preview Body -->
    <div class="flex-1 p-4 flex items-center justify-center bg-background/90 min-h-[420px] max-h-[640px] overflow-auto">
      <!-- Loading State -->
      <div v-if="isLoading && !previewImage" class="flex flex-col items-center gap-2 text-zinc-400">
        <Loader2 class="w-6 h-6 animate-spin text-blue-400" />
        <span class="text-xs">Generating preview...</span>
      </div>

      <!-- Error State -->
      <div v-else-if="errorMsg" class="text-center p-4 text-xs text-red-400">
        {{ errorMsg }}
      </div>

      <!-- Tab A: Cover Page Render -->
      <div v-else-if="activeTab === 'cover'" class="relative w-full flex justify-center transition-all">
        <img
          v-if="previewImage"
          :src="previewImage"
          alt="A4 Cover Page Live Preview"
          class="rounded shadow-2xl border border-zinc-800 transition-all cursor-pointer"
          :class="isZoomed ? 'w-full max-w-[540px]' : 'w-full max-w-[320px]'"
          @click="isZoomed = !isZoomed"
          title="Click to toggle zoom"
        />
        <div v-else class="text-xs text-zinc-500 text-center py-10">
          No document selected for preview
        </div>
      </div>

      <!-- Tab B: Table of Contents Preview / Summary -->
      <div v-else class="w-full space-y-3 p-2 text-xs">
        <div class="flex items-center gap-2 text-zinc-300 font-semibold border-b border-border pb-2">
          <Layers class="w-4 h-4 text-blue-400" />
          <span>Institutional Table of Contents</span>
        </div>

        <p class="text-[11px] text-zinc-400">
          The generated index page links directly to each experiment body in your submission with clickable bookmarks.
        </p>

        <!-- Structured Table Entries -->
        <div class="space-y-1.5 font-mono text-[11px] bg-surface p-3 rounded-lg border border-border">
          <div class="grid grid-cols-12 text-zinc-400 pb-1 border-b border-border font-bold">
            <span class="col-span-2">No.</span>
            <span class="col-span-6">Title</span>
            <span class="col-span-2 text-right">Date</span>
            <span class="col-span-2 text-right">Pages</span>
          </div>

          <div
            v-for="d in tocEntries"
            :key="d.id"
            class="grid grid-cols-12 text-zinc-300 py-0.5 items-center"
          >
            <span class="col-span-2 text-zinc-500">{{ d.isAssignment ? 'A' : 'E' }}-{{ d.num }}</span>
            <span class="col-span-6 truncate pr-1" :title="d.title || 'Untitled'">{{ d.title || 'Untitled' }}</span>
            <span class="col-span-2 text-zinc-400 text-[10px] text-right">{{ d.perfDate || '—' }}</span>
            <span class="col-span-2 text-zinc-500 text-[10px] text-right">{{ d.pageRange }}</span>
          </div>
        </div>

        <p class="text-[10px] text-zinc-500 italic">
          * Automatically paginated according to Mumbai University lab guidelines.
        </p>
      </div>
    </div>
  </div>
</template>
