<script setup lang="ts">
import {
  experiments,
  isReadyToCompile,
  isCompiling,
  deliverables,
  compileJournal,
  downloadCombinedPdf,
  downloadZipPackage,
  unextractedCount,
} from '../../store/labStore'
import { Layers, Loader2, CheckCircle2, FileText, FolderArchive } from 'lucide-vue-next'
</script>

<template>
  <div v-if="experiments.length > 0" class="pt-2">
    <!-- State A: Draft Mode -->
    <div
      v-if="!deliverables"
      class="flex flex-wrap items-center justify-between gap-3 p-4 rounded-xl bg-card border border-edge shadow-sm transition-all select-none"
    >
      <div class="text-xs text-mid flex items-center gap-2 min-w-0">
        <span v-if="unextractedCount > 0" class="text-warn font-medium truncate">
          {{ unextractedCount }} {{ unextractedCount === 1 ? 'card needs an aim title' : 'cards need aim titles' }}
        </span>
        <span v-else class="truncate text-hi/80">
          Ready to compile <strong class="text-hi font-semibold">{{ experiments.length }}</strong> {{ experiments.length === 1 ? 'document' : 'documents' }} with cover pages.
        </span>
      </div>

      <div class="flex items-center gap-2.5 shrink-0">
        <button
          type="button"
          @click="compileJournal"
          :disabled="isCompiling || !isReadyToCompile"
          class="text-xs font-semibold bg-amber hover:bg-amber-hi text-surface px-5 py-2 rounded-lg transition shadow-sm inline-flex items-center gap-2 disabled:opacity-40 disabled:pointer-events-none cursor-pointer active:scale-[0.98]"
        >
          <Loader2 v-if="isCompiling" class="w-4 h-4 animate-spin text-surface" />
          <Layers v-else class="w-4 h-4" />
          <span>{{ isCompiling ? 'Compiling PDF Package...' : 'Compile Reports' }}</span>
        </button>
      </div>
    </div>

    <!-- State B: Compiled & Ready to Download -->
    <div
      v-else
      class="flex flex-wrap items-center justify-between gap-3 p-4 rounded-xl bg-card border border-success/40 shadow-sm transition-all select-none"
    >
      <div class="text-xs text-success flex items-center gap-2 font-medium truncate min-w-0">
        <CheckCircle2 class="w-4 h-4 text-success shrink-0" />
        <span class="truncate">
          Compiled successfully ({{ experiments.length }} {{ experiments.length === 1 ? 'document' : 'documents' }} ready).
        </span>
      </div>

      <div class="flex flex-wrap items-center gap-2.5 shrink-0">
        <button
          type="button"
          @click="downloadCombinedPdf"
          class="text-xs font-semibold bg-amber hover:bg-amber-hi text-surface px-4 py-2 rounded-lg transition shadow-sm inline-flex items-center gap-1.5 cursor-pointer active:scale-[0.98]"
        >
          <FileText class="w-4 h-4" />
          <span>Download Combined PDF</span>
        </button>

        <button
          type="button"
          @click="downloadZipPackage"
          class="text-xs font-medium bg-input border border-edge hover:border-edge-hi text-hi px-3.5 py-2 rounded-lg transition inline-flex items-center gap-1.5 cursor-pointer"
        >
          <FolderArchive class="w-4 h-4" />
          <span>Download ZIP</span>
        </button>

        <button
          type="button"
          @click="compileJournal"
          :disabled="isCompiling"
          class="text-xs text-mid hover:text-hi px-2.5 py-1.5 rounded-lg hover:bg-input transition cursor-pointer"
          title="Re-compile report package"
        >
          <span>Re-compile</span>
        </button>
      </div>
    </div>
  </div>
</template>
