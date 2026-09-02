<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { ApiService } from '@/services/api';
import type {
  ExtractionDiagnosticsSummary,
  DiagnosticSampleItem,
} from '@/types/analytics';
import {
  FileSearch,
  CheckCircle2,
  AlertCircle,
  Download,
  Copy,
  Check,
  ChevronDown,
  ChevronUp,
  FileCode,
  Layers,
  Sparkles,
  Filter,
} from 'lucide-vue-next';

const props = defineProps<{
  authKey?: string;
}>();

const isLoading = ref(true);
const summary = ref<ExtractionDiagnosticsSummary | null>(null);
const samples = ref<DiagnosticSampleItem[]>([]);
const totalSamples = ref(0);
const currentPage = ref(1);
const pageSize = 20;

const expandedTextHashes = ref<Set<string>>(new Set());
const copiedHash = ref<string | null>(null);
const downloadingHash = ref<string | null>(null);

async function loadDiagnostics(): Promise<void> {
  isLoading.value = true;
  try {
    const offset = (currentPage.value - 1) * pageSize;
    const res = await ApiService.getAnalyticsDiagnostics(
      { limit: pageSize, offset },
      props.authKey
    );
    if (res.success && res.data) {
      summary.value = res.data.summary;
      samples.value = res.data.samples;
      totalSamples.value = res.data.total;
    }
  } catch (err) {
    console.error('Failed to load diagnostics:', err);
  } finally {
    isLoading.value = false;
  }
}

function toggleExpandText(hash: string): void {
  if (expandedTextHashes.value.has(hash)) {
    expandedTextHashes.value.delete(hash);
  } else {
    expandedTextHashes.value.add(hash);
  }
}

async function copyToClipboard(text: string, hash: string): Promise<void> {
  try {
    await navigator.clipboard.writeText(text);
    copiedHash.value = hash;
    setTimeout(() => {
      copiedHash.value = null;
    }, 2000);
  } catch {
    // fallback
  }
}

async function handleDownloadSample(hash: string): Promise<void> {
  downloadingHash.value = hash;
  try {
    await ApiService.downloadDiagnosticSample(hash, props.authKey);
  } catch (err) {
    console.error('Failed to download sample:', err);
  } finally {
    downloadingHash.value = null;
  }
}

function formatBytes(bytes: number): string {
  if (!bytes) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}

function getMethodBadgeClass(method: string): string {
  switch (method) {
    case 'aim_keyword':
      return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20';
    case 'header_title':
      return 'bg-blue-500/10 text-blue-400 border-blue-500/20';
    case 'filename_heuristic':
      return 'bg-purple-500/10 text-purple-400 border-purple-500/20';
    case 'scanned_no_text':
      return 'bg-amber-500/10 text-amber-400 border-amber-500/20';
    default:
      return 'bg-rose-500/10 text-rose-400 border-rose-500/20';
  }
}

defineExpose({
  reload: loadDiagnostics,
});

onMounted(() => {
  loadDiagnostics();
});
</script>

<template>
  <div class="space-y-6">
    <!-- Header Description -->
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-zinc-900/60 border border-border rounded-xl p-5">
      <div>
        <div class="flex items-center gap-2">
          <FileSearch class="w-5 h-5 text-indigo-400" />
          <h2 class="text-base font-semibold text-zinc-100">Format Discovery & Extraction Lab</h2>
          <span class="text-xs px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 font-medium">Internal Dataset</span>
        </div>
        <p class="text-xs text-muted mt-1 max-w-2xl">
          Analyze heuristic failures across institutional lab manual formats. Compare algorithmic extractions against student ground-truth titles, inspect raw header text, and download edge-case sample PDFs to build new regexes.
        </p>
      </div>

      <button
        type="button"
        @click="loadDiagnostics"
        class="self-start sm:self-auto px-3 py-1.5 rounded-lg border border-border hover:border-zinc-500 text-xs font-medium text-zinc-300 hover:text-white transition flex items-center gap-1.5"
      >
        <span>Refresh Dataset</span>
      </button>
    </div>

    <!-- Extraction Health KPI Cards -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      <div class="bg-zinc-900/60 border border-border rounded-xl p-4">
        <div class="flex items-center justify-between text-xs text-muted">
          <span>Auto-Extraction Rate</span>
          <CheckCircle2 class="w-4 h-4 text-emerald-400" />
        </div>
        <div class="text-2xl font-bold text-zinc-100 mt-2">
          {{ summary?.success_rate_percent ?? 100 }}%
        </div>
        <div class="text-[11px] text-muted mt-1">
          High-confidence Aim / Header match
        </div>
      </div>

      <div class="bg-zinc-900/60 border border-border rounded-xl p-4">
        <div class="flex items-center justify-between text-xs text-muted">
          <span>Student Discrepancies</span>
          <AlertCircle class="w-4 h-4 text-amber-400" />
        </div>
        <div class="text-2xl font-bold text-zinc-100 mt-2">
          {{ summary?.discrepancies_count ?? 0 }}
        </div>
        <div class="text-[11px] text-muted mt-1">
          Ground-truth titles corrected by students
        </div>
      </div>

      <div class="bg-zinc-900/60 border border-border rounded-xl p-4">
        <div class="flex items-center justify-between text-xs text-muted">
          <span>Total Documents Logged</span>
          <Layers class="w-4 h-4 text-blue-400" />
        </div>
        <div class="text-2xl font-bold text-zinc-100 mt-2">
          {{ summary?.total_documents ?? 0 }}
        </div>
        <div class="text-[11px] text-muted mt-1">
          Retained indefinitely for analysis
        </div>
      </div>

      <div class="bg-zinc-900/60 border border-border rounded-xl p-4">
        <div class="flex items-center justify-between text-xs text-muted">
          <span>Research Samples</span>
          <FileCode class="w-4 h-4 text-purple-400" />
        </div>
        <div class="text-2xl font-bold text-zinc-100 mt-2">
          {{ totalSamples }}
        </div>
        <div class="text-[11px] text-muted mt-1">
          Protected from storage rotation
        </div>
      </div>
    </div>

    <!-- Diagnostic Breakdown: Methods & Failure Causes -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
      <!-- Extraction Methods Distribution -->
      <div class="bg-zinc-900/60 border border-border rounded-xl p-4 space-y-3">
        <div class="flex items-center justify-between border-b border-border/50 pb-2">
          <span class="text-xs font-semibold text-zinc-200">Extraction Method Breakdown</span>
          <span class="text-[11px] text-muted">Resolution Strategy</span>
        </div>
        <div class="space-y-2">
          <div
            v-for="(count, method) in summary?.methods || {}"
            :key="method"
            class="flex items-center justify-between text-xs py-1"
          >
            <div class="flex items-center gap-2">
              <span
                class="px-2 py-0.5 rounded border text-[11px] font-mono capitalize"
                :class="getMethodBadgeClass(String(method))"
              >
                {{ String(method).replace(/_/g, ' ') }}
              </span>
            </div>
            <span class="font-mono text-zinc-200 font-medium">{{ count }}</span>
          </div>
          <div v-if="!summary || Object.keys(summary.methods).length === 0" class="text-xs text-muted py-2">
            No document extractions recorded yet.
          </div>
        </div>
      </div>

      <!-- Root-Cause Failure Analysis -->
      <div class="bg-zinc-900/60 border border-border rounded-xl p-4 space-y-3">
        <div class="flex items-center justify-between border-b border-border/50 pb-2">
          <span class="text-xs font-semibold text-zinc-200">Failure Root-Causes</span>
          <span class="text-[11px] text-muted">Opportunities for New Regexes</span>
        </div>
        <div class="space-y-2">
          <div
            v-for="(count, reason) in summary?.failures || {}"
            :key="reason"
            class="flex items-center justify-between text-xs py-1"
          >
            <span class="text-zinc-300 font-mono text-[11px]">{{ String(reason).replace(/_/g, ' ') }}</span>
            <span class="px-2 py-0.5 rounded bg-rose-500/10 text-rose-400 border border-rose-500/20 font-mono text-[11px] font-semibold">
              {{ count }}
            </span>
          </div>
          <div v-if="!summary || Object.keys(summary.failures).length === 0" class="text-xs text-muted py-2">
            Zero heuristic failures detected!
          </div>
        </div>
      </div>
    </div>

    <!-- Problematic Samples Inspector -->
    <div class="bg-zinc-900/60 border border-border rounded-xl p-5 space-y-4">
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-border/50 pb-4">
        <div>
          <div class="flex items-center gap-2">
            <Filter class="w-4 h-4 text-zinc-300" />
            <h3 class="text-sm font-semibold text-zinc-100">Failed & Discrepant Sample Inspector</h3>
            <span class="text-xs text-muted">({{ totalSamples }} candidate files)</span>
          </div>
          <p class="text-xs text-muted mt-0.5">
            Documents where the extractor failed or where student ground-truth differs from algorithm.
          </p>
        </div>
      </div>

      <!-- Samples List -->
      <div v-if="isLoading" class="py-12 text-center text-xs text-muted">
        Loading sample dataset...
      </div>

      <div v-else-if="samples.length === 0" class="py-12 text-center text-xs text-muted">
        No failed or discrepant samples found. All uploads were extracted with 100% agreement!
      </div>

      <div v-else class="space-y-3">
        <div
          v-for="sample in samples"
          :key="sample.sha256"
          class="border border-border/70 rounded-xl p-4 bg-zinc-950/40 hover:border-zinc-600 transition space-y-3"
        >
          <!-- Top Row: File Name, Size, Method, Actions -->
          <div class="flex flex-wrap items-center justify-between gap-2">
            <div class="flex items-center gap-2">
              <span class="text-xs font-semibold text-zinc-200">{{ sample.filename }}</span>
              <span class="text-[11px] text-muted">({{ formatBytes(sample.file_size) }}, {{ sample.pages }} pages)</span>
            </div>

            <div class="flex items-center gap-2">
              <!-- Method Badge -->
              <span
                class="px-2 py-0.5 rounded border text-[11px] font-mono capitalize"
                :class="getMethodBadgeClass(sample.extraction_method)"
              >
                {{ sample.extraction_method.replace(/_/g, ' ') }}
              </span>

              <!-- Failure Reason Badge -->
              <span
                v-if="sample.failure_reason && sample.failure_reason !== 'none'"
                class="px-2 py-0.5 rounded bg-rose-500/10 text-rose-400 border border-rose-500/20 text-[11px] font-mono"
              >
                {{ sample.failure_reason }}
              </span>

              <!-- 1-Click Download Sample PDF -->
              <button
                type="button"
                @click="handleDownloadSample(sample.sha256)"
                :disabled="downloadingHash === sample.sha256"
                class="px-2.5 py-1 rounded bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-xs font-medium inline-flex items-center gap-1.5 transition border border-border disabled:opacity-50"
                title="Download raw uploaded PDF for local analysis"
              >
                <Download class="w-3.5 h-3.5" />
                <span>{{ downloadingHash === sample.sha256 ? 'Downloading...' : 'Download Sample' }}</span>
              </button>
            </div>
          </div>

          <!-- Ground Truth vs Extracted Comparison -->
          <div class="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs bg-zinc-900/40 rounded-lg p-3 border border-border/40">
            <div>
              <div class="text-[11px] font-medium text-muted mb-1 flex items-center gap-1">
                <span>Algorithmic Extraction:</span>
                <span v-if="!sample.extracted_aim" class="text-rose-400">(Missed)</span>
              </div>
              <div class="font-mono text-zinc-300 text-[11px] break-words">
                {{ sample.extracted_aim || '— No Aim Extracted —' }}
              </div>
            </div>

            <div>
              <div class="text-[11px] font-medium text-emerald-400 mb-1 flex items-center gap-1">
                <Sparkles class="w-3 h-3" />
                <span>Student Ground Truth (Submitted):</span>
              </div>
              <div class="font-mono text-emerald-300 text-[11px] font-medium break-words">
                {{ sample.student_submitted_title || '— Not provided / Same —' }}
              </div>
            </div>
          </div>

          <!-- SHA-256 & Text Snippet Toggle -->
          <div class="flex flex-wrap items-center justify-between gap-2 pt-1 border-t border-border/30 text-[11px]">
            <div class="flex items-center gap-2 font-mono text-muted">
              <span>SHA-256: {{ sample.sha256.slice(0, 16) }}...</span>
              <button
                type="button"
                @click="copyToClipboard(sample.sha256, sample.sha256)"
                class="text-zinc-400 hover:text-white"
                title="Copy SHA-256 hash"
              >
                <Check v-if="copiedHash === sample.sha256" class="w-3 h-3 text-emerald-400" />
                <Copy v-else class="w-3 h-3" />
              </button>
            </div>

            <button
              type="button"
              @click="toggleExpandText(sample.sha256)"
              class="text-zinc-400 hover:text-zinc-200 inline-flex items-center gap-1 transition"
            >
              <span>{{ expandedTextHashes.has(sample.sha256) ? 'Hide Page 1 Text' : 'Inspect Page 1 Text' }}</span>
              <ChevronUp v-if="expandedTextHashes.has(sample.sha256)" class="w-3.5 h-3.5" />
              <ChevronDown v-else class="w-3.5 h-3.5" />
            </button>
          </div>

          <!-- Expandable Raw Page 1 Text Snippet -->
          <div
            v-if="expandedTextHashes.has(sample.sha256)"
            class="mt-2 bg-zinc-950 rounded-lg p-3 border border-border font-mono text-[11px] text-zinc-300 whitespace-pre-wrap leading-relaxed max-h-48 overflow-y-auto"
          >
            {{ sample.text_snippet || '— No text layer found on Page 1 (Scanned or graphical document) —' }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
