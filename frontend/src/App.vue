<script setup lang="ts">
import { ref } from 'vue';
import { useLabStore } from './store';
import StudentSetup from './components/StudentSetup.vue';
import DocumentQueue from './components/DocumentQueue.vue';
import LivePreview from './components/LivePreview.vue';
import {
  FileText,
  FolderArchive,
  Loader2,
  CheckCircle2,
  Eye,
  Layers,
} from 'lucide-vue-next';

const store = useLabStore();
const isMobilePreviewOpen = ref(false);
const toastMessage = ref<string | null>(null);

function showToast(msg: string) {
  toastMessage.value = msg;
  setTimeout(() => {
    toastMessage.value = null;
  }, 3500);
}

async function handleCompile() {
  const res = await store.compile();
  if (res.success) {
    showToast('Lab report compiled successfully! Ready to download.');
  } else {
    showToast(`Error: ${res.error || 'Compilation failed'}`);
  }
}
</script>

<template>
  <div class="min-h-screen bg-[#09090b] text-[#fafafa] flex flex-col font-sans selection:bg-zinc-800 selection:text-white">
    <!-- 1. Top Navbar -->
    <header class="bg-[#141417]/90 backdrop-blur-md border-b border-[#27272a] sticky top-0 z-30">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 py-3 flex items-center justify-between">
        <!-- Logo & Branding -->
        <div class="flex items-center gap-2.5">
          <div class="w-2.5 h-2.5 rounded-full bg-blue-500 animate-pulse"></div>
          <div>
            <h1 class="text-sm sm:text-base font-bold text-white tracking-tight leading-none">
              LabStudio
            </h1>
            <p class="text-[10px] text-zinc-400 mt-0.5 hidden sm:block">
              Institutional Lab Report Compiler
            </p>
          </div>
        </div>

        <!-- Current Subject & Mobile Preview Toggle -->
        <div class="flex items-center gap-2">
          <span
            v-if="store.student.subject"
            class="text-xs font-mono text-zinc-300 bg-[#1c1c21] border border-[#27272a] px-2.5 py-1 rounded-lg hidden sm:inline-block"
          >
            {{ store.student.subject }}
          </span>

          <!-- Mobile Live Preview Toggle Button -->
          <button
            type="button"
            @click="isMobilePreviewOpen = !isMobilePreviewOpen"
            class="lg:hidden inline-flex items-center gap-1.5 text-xs text-zinc-300 bg-[#1c1c21] border border-[#27272a] hover:border-zinc-400 px-2.5 py-1.5 rounded-lg"
          >
            <Eye class="w-3.5 h-3.5 text-blue-400" />
            <span>{{ isMobilePreviewOpen ? 'Hide Preview' : 'View Preview' }}</span>
          </button>
        </div>
      </div>
    </header>

    <!-- 2. Main Studio Workspace Layout -->
    <main class="max-w-7xl mx-auto px-4 sm:px-6 py-6 flex-1 w-full pb-28">
      <div class="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        <!-- Left Column: Student Setup & Controls (4 cols) -->
        <div class="lg:col-span-4 space-y-4">
          <StudentSetup />
        </div>

        <!-- Center Column: Document Queue & Bulk Ingestion (5 cols) -->
        <div class="lg:col-span-5 space-y-4">
          <DocumentQueue />
        </div>

        <!-- Right Column: Permanent Live Inspector (3 cols on desktop) -->
        <div class="hidden lg:block lg:col-span-3">
          <LivePreview />
        </div>
      </div>

      <!-- Mobile Slide-Up Preview Drawer (visible when isMobilePreviewOpen on mobile) -->
      <div
        v-if="isMobilePreviewOpen"
        class="lg:hidden fixed inset-x-0 bottom-24 z-40 p-4 max-w-md mx-auto"
      >
        <LivePreview />
      </div>
    </main>

    <!-- 3. Sticky Bottom Compilation Dock -->
    <aside class="fixed inset-x-0 bottom-0 z-50 bg-[#141417]/95 backdrop-blur-md border-t border-[#27272a] p-3 sm:px-6 shadow-2xl">
      <div class="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-3">
        <!-- Status Indicator -->
        <div class="flex items-center gap-2 text-xs">
          <span
            class="w-2.5 h-2.5 rounded-full shrink-0"
            :class="store.canCompile ? 'bg-emerald-400' : 'bg-amber-400'"
          ></span>
          <span :class="store.canCompile ? 'text-zinc-200' : 'text-amber-400 font-medium'">
            {{ store.compileStatusText }}
          </span>
          <span v-if="store.totalPages > 0" class="text-zinc-500 font-mono hidden sm:inline">
            · {{ store.totalPages }} total pages
          </span>
        </div>

        <!-- Actions -->
        <div class="flex items-center gap-2">
          <!-- State A: Not Compiled / Ready to Compile -->
          <template v-if="!store.isCompiled">
            <button
              type="button"
              @click="handleCompile"
              :disabled="store.isCompiling || !store.canCompile"
              class="inline-flex items-center gap-2 text-xs font-semibold px-4 py-2 rounded-xl transition shadow-lg"
              :class="store.canCompile ? 'bg-white text-black hover:bg-zinc-200 active:scale-[0.98]' : 'bg-zinc-800 text-zinc-500 cursor-not-allowed border border-[#27272a]'"
            >
              <Loader2 v-if="store.isCompiling" class="w-4 h-4 animate-spin text-black" />
              <Layers v-else class="w-4 h-4 text-black" />
              <span>{{ store.isCompiling ? 'Compiling PDF Package...' : 'Compile Lab Report' }}</span>
            </button>
          </template>

          <!-- State B: Compiled Successfully -> Direct Downloads -->
          <template v-else>
            <button
              type="button"
              @click="store.downloadCombined"
              class="inline-flex items-center gap-1.5 text-xs font-semibold px-3.5 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-white shadow-lg transition"
            >
              <FileText class="w-4 h-4" />
              <span>Download Combined PDF</span>
            </button>

            <button
              type="button"
              @click="store.downloadZip"
              class="inline-flex items-center gap-1.5 text-xs font-medium px-3 py-2 rounded-xl bg-[#1c1c21] hover:bg-zinc-800 border border-[#27272a] text-zinc-300 transition"
            >
              <FolderArchive class="w-4 h-4" />
              <span class="hidden sm:inline">Download ZIP</span>
            </button>

            <button
              type="button"
              @click="handleCompile"
              :disabled="store.isCompiling"
              class="text-xs text-zinc-400 hover:text-white px-2 py-1"
              title="Re-compile"
            >
              <span>Re-compile</span>
            </button>
          </template>
        </div>
      </div>
    </aside>

    <!-- 4. Floating Toast Notification -->
    <div
      v-if="toastMessage"
      class="fixed bottom-20 right-6 z-50 bg-[#1c1c21] border border-[#27272a] shadow-2xl px-4 py-2.5 rounded-xl text-xs text-white flex items-center gap-2"
    >
      <CheckCircle2 class="w-4 h-4 text-emerald-400 shrink-0" />
      <span>{{ toastMessage }}</span>
    </div>
  </div>
</template>
