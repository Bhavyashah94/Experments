<script setup lang="ts">
import { useProfileStore } from '@/stores/useProfileStore';
import { useDocumentStore } from '@/stores/useDocumentStore';
import { Calendar, RefreshCw } from 'lucide-vue-next';

const profileStore = useProfileStore();
const documentStore = useDocumentStore();
</script>

<template>
  <div class="bg-card border border-border rounded-xl p-4 shadow-sm space-y-3 flex flex-col justify-between">
    <!-- Top Row: Date Inputs -->
    <div class="flex flex-wrap items-center justify-between gap-2">
      <span class="text-xs font-semibold text-muted uppercase tracking-wider">Date Schedule:</span>

      <div class="flex items-center gap-2">
        <div class="flex items-center gap-1.5 bg-inputBg border border-border px-2 py-1 rounded-lg focus-within:border-zinc-400 transition">
          <span class="text-[11px] text-muted uppercase font-medium">Perf:</span>
          <input
            type="text"
            v-model="profileStore.activeProfile.globalPerfDate"
            placeholder="DD/MM/YYYY"
            class="w-20 bg-transparent text-xs font-mono text-white outline-none"
          />
        </div>

        <div class="flex items-center gap-1.5 bg-inputBg border border-border px-2 py-1 rounded-lg focus-within:border-zinc-400 transition">
          <span class="text-[11px] text-muted uppercase font-medium">Sub:</span>
          <input
            type="text"
            v-model="profileStore.activeProfile.globalSubDate"
            placeholder="DD/MM/YYYY"
            class="w-20 bg-transparent text-xs font-mono text-white outline-none"
          />
        </div>
      </div>
    </div>

    <!-- Bottom Row: Action Buttons -->
    <div class="flex items-center justify-end gap-2 pt-0.5">
      <button
        type="button"
        @click="documentStore.applyGlobalDates"
        class="inline-flex items-center gap-1.5 text-xs text-zinc-300 hover:text-white bg-inputBg border border-border hover:border-zinc-400 px-2.5 py-1 rounded-lg transition"
        title="Copy these global dates to all document cards"
      >
        <RefreshCw class="w-3 h-3" />
        <span>Apply All</span>
      </button>

      <button
        type="button"
        @click="documentStore.applyWeeklyDates"
        class="inline-flex items-center gap-1.5 text-xs text-white bg-zinc-800 hover:bg-zinc-700 border border-zinc-600 px-3 py-1 rounded-lg font-medium transition"
        title="Auto-fill sequential weekly dates (+7 days) across all cards"
      >
        <Calendar class="w-3 h-3" />
        <span>+7 Days Weekly Auto-Fill</span>
      </button>
    </div>
  </div>
</template>
