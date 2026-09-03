<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue';
import { useDocumentStore } from '@/stores/useDocumentStore';
import { ApiService } from '@/services/api';
import StudentHeaderForm from '@/components/student/StudentHeaderForm.vue';
import ColorHistoryBar from '@/components/student/ColorHistoryBar.vue';
import GlobalDateBar from '@/components/student/GlobalDateBar.vue';
import BulkDropzone from '@/components/documents/BulkDropzone.vue';
import DocumentCardList from '@/components/documents/DocumentCardList.vue';
import LivePreviewModal from '@/components/modals/LivePreviewModal.vue';
import FormatGuideModal from '@/components/modals/FormatGuideModal.vue';
import AnalyticsDashboard from '@/components/analytics/AnalyticsDashboard.vue';
import type { DocumentItem } from '@/types/document';

const currentPath = ref(window.location.pathname);

function handlePopState() {
  currentPath.value = window.location.pathname;
}

onMounted(() => {
  window.addEventListener('popstate', handlePopState);
});

onUnmounted(() => {
  window.removeEventListener('popstate', handlePopState);
});
import {
  HelpCircle,
  Loader2,
  Layers,
  FileText,
  FolderArchive,
  CheckCircle2,
} from 'lucide-vue-next';

const documentStore = useDocumentStore();

const isPreviewOpen = ref(false);
const previewDoc = ref<DocumentItem | null>(null);
const isGuideOpen = ref(false);
const showToast = ref(false);
const toastMessage = ref('');
const isBackendWakingUp = ref(false);

function triggerToast(msg: string) {
  toastMessage.value = msg;
  showToast.value = true;
  setTimeout(() => {
    showToast.value = false;
  }, 3500);
}

function handleOpenPreview(doc: DocumentItem) {
  previewDoc.value = doc;
  isPreviewOpen.value = true;
}

async function handleCompile(includeTocOverride?: boolean) {
  const res = await documentStore.compileDocuments(includeTocOverride);
  if (res.success) {
    triggerToast('Report compiled successfully! Ready to download.');
  } else {
    triggerToast(`Error: ${res.error}`);
  }
}

onMounted(async () => {
  const timer = setTimeout(() => {
    isBackendWakingUp.value = true;
  }, 1200);

  try {
    const health = await ApiService.checkHealth();
    clearTimeout(timer);
    isBackendWakingUp.value = false;
    if (health.status !== 'ok') {
      console.warn('[Backend] Unexpected health status:', health);
    }
  } catch (err) {
    console.warn('[Backend] Cold start or offline:', err);
  }
});
</script>

<template>
  <!-- Dedicated Hidden Analytics Dashboard Route -->
  <AnalyticsDashboard v-if="currentPath === '/analytics'" />

  <!-- Normal Student-Facing Document Studio Workspace (100% Unchanged) -->
  <div v-else class="min-h-screen bg-surface text-zinc-100 flex flex-col selection:bg-zinc-800 selection:text-white">
    <!-- Top Clean Sticky Navbar -->
    <nav class="bg-card/90 backdrop-blur-md border-b border-border sticky top-0 z-40">
      <div class="max-w-7xl mx-auto px-3 sm:px-6 lg:px-8 py-3 sm:py-3.5 flex items-center justify-between gap-3 sm:gap-4">
        <!-- Logo & Title -->
        <div class="min-w-0 flex items-center gap-3 shrink-0">
          <div class="w-2.5 h-2.5 rounded-full bg-white animate-pulse shrink-0"></div>
          <div>
            <h1 class="text-sm sm:text-base font-bold text-white tracking-tight whitespace-nowrap">LabStudio</h1>
            <p class="text-[11px] text-muted hidden md:block">Fill details, attach PDFs, and export standardized lab reports</p>
          </div>
        </div>

        <!-- Header Actions: Guide Only -->
        <div class="flex items-center gap-2 shrink-0">
          <button
            type="button"
            @click="isGuideOpen = true"
            class="text-xs text-muted hover:text-white transition px-3 py-1.5 rounded-lg hover:bg-zinc-800 inline-flex items-center gap-1.5 border border-transparent hover:border-border"
            title="Formatting & Auto-Aim guide"
          >
            <HelpCircle class="w-3.5 h-3.5" />
            <span>Guide</span>
          </button>
        </div>
      </div>
    </nav>

    <!-- Render Backend Cold-Start Alert Banner -->
    <div
      v-if="isBackendWakingUp"
      class="bg-amber-950/40 border-b border-amber-800/60 px-4 py-2 text-center text-xs text-amber-200 flex items-center justify-center gap-2"
      role="status"
      aria-live="polite"
    >
      <Loader2 class="w-3.5 h-3.5 animate-spin shrink-0 text-amber-400" />
      <span>Connecting to backend service... (Render free-tier may take ~30s to wake up on first visit)</span>
    </div>

    <!-- Main Fluid Responsive Studio Workspace -->
    <main class="max-w-7xl mx-auto px-3 sm:px-6 lg:px-8 py-5 sm:py-8 flex-1 w-full">
      <div class="mb-4 sm:mb-6 rounded-xl border border-border bg-card/40 px-3 py-2.5 text-[11px] sm:text-xs text-zinc-300 flex flex-wrap items-center gap-1.5 sm:gap-2">
        <span class="font-semibold text-white">Workflow:</span>
        <span>1) Fill student details</span>
        <span class="text-zinc-500 hidden sm:inline">→</span>
        <span>2) Upload PDFs</span>
        <span class="text-zinc-500 hidden sm:inline">→</span>
        <span>3) Compile &amp; download</span>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-12 gap-5 sm:gap-6 lg:gap-8 items-start">
        <!-- Left Sticky Sidebar Column (lg:col-span-5 xl:col-span-4) -->
        <div class="lg:col-span-5 xl:col-span-4 lg:sticky lg:top-20 space-y-4">
          <!-- 1. Student Details Section -->
          <section>
            <StudentHeaderForm @toast="triggerToast" />
          </section>

          <!-- 2. Ink & Date Controls -->
          <section class="space-y-4">
            <ColorHistoryBar />
            <GlobalDateBar />
          </section>

          <!-- 3. Bulk PDF Upload Dropzone -->
          <section>
            <BulkDropzone />
          </section>
        </div>

        <!-- Right Document Studio Column (lg:col-span-7 xl:col-span-8) -->
        <div class="lg:col-span-7 xl:col-span-8 space-y-5 sm:space-y-6">
          <!-- 4. Document Card List (Reorderable with SortableJS) -->
          <section>
            <DocumentCardList @preview="handleOpenPreview" />
          </section>

          <!-- 5. Separated Compilation & Download Action Center -->
          <!-- State A: Not Compiled / Draft -->
          <section
            v-if="!documentStore.isCompiled"
            class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 p-3.5 sm:p-4 rounded-xl bg-card border border-border shadow-sm transition-all"
          >
            <div class="text-xs text-muted flex items-center gap-2">
              <span class="w-2 h-2 rounded-full bg-zinc-600"></span>
              <span>Ready to compile {{ documentStore.documents.length }} document(s) with cover pages.</span>
            </div>

            <div class="flex items-center gap-2.5 w-full sm:w-auto">
              <button
                type="button"
                @click="handleCompile(false)"
                :disabled="documentStore.isGenerating || documentStore.documents.length === 0"
                class="text-xs font-semibold bg-white hover:bg-zinc-200 text-black px-4 sm:px-5 py-2 rounded-lg transition shadow-md inline-flex items-center justify-center gap-2 disabled:opacity-50 w-full sm:w-auto"
              >
                <Loader2 v-if="documentStore.isGenerating" class="w-4 h-4 animate-spin" />
                <Layers v-else class="w-4 h-4" />
                <span>{{ documentStore.isGenerating ? 'Compiling PDF Package...' : 'Compile Reports' }}</span>
              </button>
            </div>
          </section>

          <!-- State B: Compiled & Ready to Download -->
          <section
            v-else
            class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 p-3.5 sm:p-4 rounded-xl bg-card border border-emerald-900/60 shadow-sm transition-all"
          >
            <div class="text-xs text-emerald-400 flex items-center gap-2 font-medium">
              <CheckCircle2 class="w-4 h-4 text-emerald-400 shrink-0" />
              <span>Compiled successfully ({{ documentStore.documents.length }} document{{ documentStore.documents.length === 1 ? '' : 's' }} ready).</span>
            </div>

            <div class="grid grid-cols-1 sm:flex sm:flex-wrap items-center gap-2.5 w-full sm:w-auto">
              <button
                type="button"
                @click="documentStore.downloadCombinedPdf()"
                class="text-xs font-semibold bg-white hover:bg-zinc-200 text-black px-4 py-2 rounded-lg transition shadow-md inline-flex items-center justify-center gap-1.5 w-full sm:w-auto"
              >
                <FileText class="w-4 h-4" />
                <span>Download Combined PDF</span>
              </button>

              <button
                type="button"
                @click="documentStore.downloadZipPackage()"
                class="text-xs font-medium bg-inputBg border border-border hover:border-zinc-400 text-zinc-200 px-3.5 py-2 rounded-lg transition inline-flex items-center justify-center gap-1.5 w-full sm:w-auto"
              >
                <FolderArchive class="w-4 h-4" />
                <span>Download ZIP</span>
              </button>

              <button
                type="button"
                @click="handleCompile(false)"
                :disabled="documentStore.isGenerating"
                class="text-xs text-zinc-400 hover:text-white px-2 py-1.5 rounded transition text-center"
                title="Re-compile report package"
              >
                <span>Re-compile</span>
              </button>
            </div>
          </section>
        </div>
      </div>
    </main>

    <!-- Studio Footer -->
    <footer class="border-t border-border py-6 mt-8 bg-card/40">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-2.5 text-xs text-muted">
        <div class="flex items-center gap-2">
          <span>LabStudio v2.0</span>
          <span>·</span>
          <span>Standardized Lab Reports</span>
        </div>
        <div class="flex items-center gap-1.5 text-zinc-400">
          <span>Built by</span>
          <a
            href="https://github.com/Bhavyashah94"
            target="_blank"
            rel="noopener noreferrer"
            class="text-white hover:underline font-medium hover:text-zinc-200 transition"
          >
            Bhavya Shah
          </a>
          <span>&amp;</span>
          <a
            href="https://antigravity.google"
            target="_blank"
            rel="noopener noreferrer"
            class="text-white hover:underline font-medium hover:text-zinc-200 transition"
          >
            Antigravity
          </a>
        </div>
      </div>
    </footer>

    <!-- Live Preview Modal -->
    <LivePreviewModal
      :is-open="isPreviewOpen"
      :doc="previewDoc"
      @close="isPreviewOpen = false"
    />

    <!-- Formatting Guide Modal -->
    <FormatGuideModal
      :is-open="isGuideOpen"
      @close="isGuideOpen = false"
    />

    <!-- Global Toast Notification -->
    <div
      v-if="showToast"
      class="fixed bottom-4 sm:bottom-6 left-3 right-3 sm:left-auto sm:right-6 z-50 bg-card border border-border shadow-2xl px-4 py-2.5 rounded-xl text-xs text-white flex items-center gap-2 animate-in fade-in slide-in-from-bottom-3 max-w-[92vw] sm:max-w-sm"
      role="status"
      aria-live="polite"
    >
      <div class="w-2 h-2 rounded-full bg-white animate-pulse shrink-0"></div>
      <span>{{ toastMessage }}</span>
    </div>
  </div>
</template>
