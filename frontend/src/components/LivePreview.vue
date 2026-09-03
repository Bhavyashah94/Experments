<script setup lang="ts">
import { ref, watch, onMounted } from 'vue';
import { useLabStore } from '../store';
import { Api } from '../api';
import { useDebounceFn } from '@vueuse/core';
import { Eye, Loader2, RefreshCw, Layers } from 'lucide-vue-next';

const store = useLabStore();

const activeTab = ref<'cover' | 'toc'>('cover');
const previewImage = ref<string | null>(null);
const isLoading = ref(false);
const errorMsg = ref<string | null>(null);

const fetchPreview = useDebounceFn(async () => {
  if (!store.selectedDoc) {
    previewImage.value = null;
    return;
  }

  isLoading.value = true;
  errorMsg.value = null;

  try {
    const payload = {
      name: store.student.name || 'Student Name',
      roll_no: store.student.rollNo || '00',
      batch: store.student.batch || 'B1',
      class_name: store.student.className || 'Class',
      sem: store.student.sem || 'Sem',
      subject: store.student.subject || 'Subject Name',
      experiment_number: store.selectedDoc.num || '1',
      title: store.selectedDoc.title || 'Aim / Title of Experiment',
      perf_date: store.selectedDoc.perfDate || '',
      sub_date: store.selectedDoc.subDate || '',
      text_color: store.student.textColor || '#0000bf',
      strikethrough_enabled: store.student.strikethrough,
      is_assignment: store.selectedDoc.isAssignment,
    };

    const res = await Api.previewHeader(payload);
    if (res.success && res.image) {
      previewImage.value = res.image;
    } else {
      errorMsg.value = res.error || 'Preview unavailable';
    }
  } catch (e: any) {
    errorMsg.value = e.message || 'Error generating preview';
  } finally {
    isLoading.value = false;
  }
}, 150);

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
  <div class="bg-[#141417] border border-[#27272a] rounded-xl overflow-hidden flex flex-col h-full sticky top-20 shadow-sm">
    <!-- Inspector Top Bar -->
    <div class="flex items-center justify-between px-4 py-3 border-b border-[#27272a] bg-[#1c1c21]/50">
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
          @click="fetchPreview"
          class="p-1 text-zinc-400 hover:text-white rounded hover:bg-zinc-800 transition"
          title="Refresh preview"
        >
          <RefreshCw class="w-3.5 h-3.5" :class="isLoading ? 'animate-spin' : ''" />
        </button>
      </div>
    </div>

    <!-- Inspector Tabs -->
    <div class="flex border-b border-[#27272a] bg-[#141417] text-xs">
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
    <div class="flex-1 p-4 flex items-center justify-center bg-[#09090b]/80 min-h-[420px] max-h-[640px] overflow-auto">
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
      <div v-else-if="activeTab === 'cover'" class="relative w-full flex justify-center">
        <img
          v-if="previewImage"
          :src="`data:image/png;base64,${previewImage}`"
          alt="A4 Cover Page Live Preview"
          class="w-full max-w-[340px] rounded shadow-2xl border border-zinc-800"
        />
        <div v-else class="text-xs text-zinc-500 text-center py-10">
          No document selected for preview
        </div>
      </div>

      <!-- Tab B: Table of Contents Preview / Summary -->
      <div v-else class="w-full space-y-3 p-2 text-xs">
        <div class="flex items-center gap-2 text-zinc-300 font-semibold border-b border-[#27272a] pb-2">
          <Layers class="w-4 h-4 text-blue-400" />
          <span>Institutional Table of Contents</span>
        </div>

        <p class="text-[11px] text-zinc-400">
          The generated index page links directly to each experiment body in your submission with clickable bookmarks.
        </p>

        <!-- Simulated Table Entries -->
        <div class="space-y-1.5 font-mono text-[11px] bg-[#141417] p-3 rounded-lg border border-[#27272a]">
          <div class="flex items-center justify-between text-zinc-400 pb-1 border-b border-[#27272a] font-bold">
            <span>Sr.</span>
            <span>Title</span>
            <span>Date</span>
          </div>

          <div
            v-for="d in store.documents"
            :key="d.id"
            class="flex items-center justify-between text-zinc-300 py-0.5"
          >
            <span class="text-zinc-500 w-6">{{ d.num }}.</span>
            <span class="truncate flex-1 px-2">{{ d.title || 'Untitled' }}</span>
            <span class="text-zinc-400 text-[10px]">{{ d.perfDate || '—' }}</span>
          </div>
        </div>

        <p class="text-[10px] text-zinc-500 italic">
          * Automatically paginated according to Mumbai University lab guidelines.
        </p>
      </div>
    </div>
  </div>
</template>
