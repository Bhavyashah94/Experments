<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import { ApiService } from '@/services/api';
import type { AnalyticsSummary, GenerationEventItem } from '@/types/analytics';
import {
  Activity,
  Users,
  CheckCircle2,
  Clock,
  Layers,
  Search,
  RefreshCw,
  Lock,
  ArrowLeft,
  FileText,
  AlertTriangle,
  BarChart2,
  BookOpen,
  Download,
} from 'lucide-vue-next';

const isLoading = ref(true);
const isExporting = ref(false);
const isAuthRequired = ref(false);
const isAuthenticated = ref(true);
const adminPasswordInput = ref('');
const authError = ref('');

const summary = ref<AnalyticsSummary | null>(null);
const events = ref<GenerationEventItem[]>([]);
const totalEventsCount = ref(0);

const searchQuery = ref('');
const selectedSubject = ref('');
const currentPage = ref(1);
const pageSize = 20;

const autoRefresh = ref(false);
let autoRefreshTimer: any = null;

const selectedEventForDetail = ref<GenerationEventItem | null>(null);

const AUTH_STORAGE_KEY = 'labstudio_analytics_admin_key';

function getStoredAuthKey(): string {
  return sessionStorage.getItem(AUTH_STORAGE_KEY) || '';
}

function setStoredAuthKey(key: string): void {
  if (key) {
    sessionStorage.setItem(AUTH_STORAGE_KEY, key);
  } else {
    sessionStorage.removeItem(AUTH_STORAGE_KEY);
  }
}

async function checkStatusAndLoad(): Promise<void> {
  isLoading.value = true;
  authError.value = '';

  try {
    const status = await ApiService.getAnalyticsStatus();
    isAuthRequired.value = status.auth_required;

    if (status.auth_required) {
      const storedKey = getStoredAuthKey();
      if (!storedKey) {
        isAuthenticated.value = false;
        isLoading.value = false;
        return;
      }
    }

    await Promise.all([loadSummary(), loadEvents()]);
    isAuthenticated.value = true;
  } catch (err: any) {
    if (err?.message?.includes('401') || err?.status === 401) {
      isAuthenticated.value = false;
    }
  } finally {
    isLoading.value = false;
  }
}

async function handleLogin(): Promise<void> {
  if (!adminPasswordInput.value.trim()) {
    authError.value = 'Please enter admin password';
    return;
  }

  isLoading.value = true;
  authError.value = '';

  try {
    const res = await ApiService.verifyAnalyticsAuth(adminPasswordInput.value.trim());
    if (res.valid) {
      setStoredAuthKey(adminPasswordInput.value.trim());
      isAuthenticated.value = true;
      adminPasswordInput.value = '';
      await Promise.all([loadSummary(), loadEvents()]);
    } else {
      authError.value = 'Invalid admin password';
    }
  } catch (err) {
    authError.value = 'Authentication failed';
  } finally {
    isLoading.value = false;
  }
}

async function loadSummary(): Promise<void> {
  const authKey = getStoredAuthKey();
  const res = await ApiService.getAnalyticsSummary(authKey);
  if (res.success && res.data) {
    summary.value = res.data;
  } else if (res.error === 'Unauthorized') {
    isAuthenticated.value = false;
    setStoredAuthKey('');
  }
}

async function loadEvents(): Promise<void> {
  const authKey = getStoredAuthKey();
  const offset = (currentPage.value - 1) * pageSize;
  const res = await ApiService.getAnalyticsEvents(
    {
      q: searchQuery.value,
      subject: selectedSubject.value,
      limit: pageSize,
      offset,
    },
    authKey
  );

  if (res.success && res.data) {
    events.value = res.data.events;
    totalEventsCount.value = res.data.total;
  } else if (res.error === 'Unauthorized') {
    isAuthenticated.value = false;
    setStoredAuthKey('');
  }
}

function handleSearch(): void {
  currentPage.value = 1;
  loadEvents();
}

function handleSubjectFilter(sub: string): void {
  selectedSubject.value = sub === selectedSubject.value ? '' : sub;
  currentPage.value = 1;
  loadEvents();
}

function handleRefresh(): void {
  loadSummary();
  loadEvents();
}

function toggleAutoRefresh(): void {
  autoRefresh.value = !autoRefresh.value;
  if (autoRefresh.value) {
    autoRefreshTimer = setInterval(handleRefresh, 15000);
  } else if (autoRefreshTimer) {
    clearInterval(autoRefreshTimer);
    autoRefreshTimer = null;
  }
}

function navigateToStudio(): void {
  window.location.href = '/';
}

async function handleDownloadExport(format: 'csv' | 'json'): Promise<void> {
  isExporting.value = true;
  try {
    const authKey = getStoredAuthKey();
    await ApiService.downloadAnalyticsExport(format, authKey);
  } catch (err) {
    console.error('Failed to download analytics export:', err);
  } finally {
    isExporting.value = false;
  }
}

const totalPages = computed(() => Math.ceil(totalEventsCount.value / pageSize) || 1);

const maxDailyCount = computed(() => {
  if (!summary.value?.daily_trends?.length) return 1;
  return Math.max(...summary.value.daily_trends.map((t) => t.count), 1);
});

const maxSubjectCount = computed(() => {
  if (!summary.value?.top_subjects?.length) return 1;
  return Math.max(...summary.value.top_subjects.map((s) => s.count), 1);
});

onMounted(() => {
  checkStatusAndLoad();
});
</script>

<template>
  <div class="min-h-screen bg-surface text-zinc-100 selection:bg-zinc-800 selection:text-white flex flex-col font-sans">
    <!-- Top Minimal Navigation Bar -->
    <header class="border-b border-border bg-surface/90 backdrop-blur sticky top-0 z-40 px-4 sm:px-6 lg:px-8 py-3.5 flex items-center justify-between">
      <div class="flex items-center gap-3">
        <button
          type="button"
          @click="navigateToStudio"
          class="text-xs text-muted hover:text-white inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border border-border hover:border-zinc-500 transition"
        >
          <ArrowLeft class="w-3.5 h-3.5" />
          <span>Back to Studio</span>
        </button>

        <div class="h-4 w-px bg-border"></div>

        <div class="flex items-center gap-2">
          <Activity class="w-4 h-4 text-zinc-300" />
          <h1 class="text-sm font-semibold text-white tracking-wide">Usage Analytics</h1>
          <span class="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-400 border border-zinc-700">
            Internal
          </span>
        </div>
      </div>

      <div class="flex items-center gap-2.5">
        <!-- Export Buttons (When Authenticated) -->
        <template v-if="isAuthenticated">
          <button
            type="button"
            @click="handleDownloadExport('csv')"
            :disabled="isExporting"
            class="text-xs bg-inputBg hover:bg-zinc-800 text-zinc-300 hover:text-white border border-border px-3 py-1.5 rounded-lg transition inline-flex items-center gap-1.5 disabled:opacity-50"
            title="Download full analytics as CSV spreadsheet"
          >
            <Download class="w-3.5 h-3.5" />
            <span>Export CSV</span>
          </button>

          <button
            type="button"
            @click="handleDownloadExport('json')"
            :disabled="isExporting"
            class="text-xs bg-inputBg hover:bg-zinc-800 text-zinc-300 hover:text-white border border-border px-3 py-1.5 rounded-lg transition inline-flex items-center gap-1.5 disabled:opacity-50 hidden sm:inline-flex"
            title="Download full raw analytics as JSON"
          >
            <Download class="w-3.5 h-3.5" />
            <span>Export JSON</span>
          </button>
        </template>

        <button
          type="button"
          @click="toggleAutoRefresh"
          class="text-xs px-2.5 py-1.5 rounded-lg border transition inline-flex items-center gap-1.5"
          :class="autoRefresh ? 'bg-emerald-950/40 border-emerald-800 text-emerald-300' : 'bg-inputBg border-border text-muted hover:text-white'"
        >
          <span class="w-1.5 h-1.5 rounded-full" :class="autoRefresh ? 'bg-emerald-400 animate-pulse' : 'bg-zinc-600'"></span>
          <span>{{ autoRefresh ? 'Live (15s)' : 'Live Off' }}</span>
        </button>

        <button
          type="button"
          @click="handleRefresh"
          :disabled="isLoading"
          class="text-xs bg-inputBg hover:bg-zinc-800 text-zinc-300 hover:text-white border border-border px-3 py-1.5 rounded-lg transition inline-flex items-center gap-1.5 disabled:opacity-50"
        >
          <RefreshCw class="w-3.5 h-3.5" :class="{ 'animate-spin': isLoading }" />
          <span>Refresh</span>
        </button>
      </div>
    </header>

    <!-- Main Content Container -->
    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 flex-1 w-full space-y-6">
      <!-- Admin Password Login Card (When Auth Required) -->
      <div v-if="!isAuthenticated" class="max-w-md mx-auto my-12 p-6 rounded-2xl bg-card border border-border shadow-2xl space-y-4 text-center">
        <div class="w-12 h-12 rounded-xl bg-inputBg border border-border flex items-center justify-center mx-auto text-zinc-300">
          <Lock class="w-6 h-6" />
        </div>
        <div>
          <h2 class="text-base font-semibold text-white">Admin Authentication</h2>
          <p class="text-xs text-muted mt-1">This analytics dashboard is protected by an admin password.</p>
        </div>

        <form @submit.prevent="handleLogin" class="space-y-3 pt-2">
          <input
            v-model="adminPasswordInput"
            type="password"
            placeholder="Enter admin password..."
            class="w-full bg-inputBg border border-border rounded-xl px-3.5 py-2.5 text-xs text-white outline-none focus:border-zinc-400 font-mono text-center"
            autofocus
          />
          <p v-if="authError" class="text-xs text-rose-400">{{ authError }}</p>

          <button
            type="submit"
            :disabled="isLoading"
            class="w-full bg-white hover:bg-zinc-200 text-black font-semibold text-xs py-2.5 rounded-xl transition shadow-sm disabled:opacity-50"
          >
            {{ isLoading ? 'Verifying...' : 'Unlock Analytics' }}
          </button>
        </form>
      </div>

      <!-- Authenticated Dashboard View -->
      <div v-else class="space-y-6">
        <!-- 1. Top Stat Metric Cards -->
        <div class="grid grid-cols-2 lg:grid-cols-5 gap-3.5">
          <!-- Total Generations -->
          <div class="bg-card border border-border rounded-xl p-4 space-y-1">
            <div class="flex items-center justify-between text-muted">
              <span class="text-[11px] font-medium uppercase tracking-wider">Total Runs</span>
              <Activity class="w-4 h-4 text-zinc-400" />
            </div>
            <div class="text-2xl font-bold font-mono text-white">
              {{ summary?.total_generations || 0 }}
            </div>
            <div class="text-[10px] text-muted">
              {{ summary?.successful_generations || 0 }} successful
            </div>
          </div>

          <!-- Unique Students -->
          <div class="bg-card border border-border rounded-xl p-4 space-y-1">
            <div class="flex items-center justify-between text-muted">
              <span class="text-[11px] font-medium uppercase tracking-wider">Students</span>
              <Users class="w-4 h-4 text-zinc-400" />
            </div>
            <div class="text-2xl font-bold font-mono text-white">
              {{ summary?.unique_students || 0 }}
            </div>
            <div class="text-[10px] text-muted">
              distinct roll numbers
            </div>
          </div>

          <!-- Total Experiments -->
          <div class="bg-card border border-border rounded-xl p-4 space-y-1">
            <div class="flex items-center justify-between text-muted">
              <span class="text-[11px] font-medium uppercase tracking-wider">Experiments</span>
              <Layers class="w-4 h-4 text-zinc-400" />
            </div>
            <div class="text-2xl font-bold font-mono text-white">
              {{ summary?.total_experiments_generated || 0 }}
            </div>
            <div class="text-[10px] text-muted">
              documents compiled
            </div>
          </div>

          <!-- Success Rate -->
          <div class="bg-card border border-border rounded-xl p-4 space-y-1">
            <div class="flex items-center justify-between text-muted">
              <span class="text-[11px] font-medium uppercase tracking-wider">Success Rate</span>
              <CheckCircle2 class="w-4 h-4 text-emerald-400" />
            </div>
            <div class="text-2xl font-bold font-mono text-emerald-400">
              {{ summary?.success_rate || 100 }}%
            </div>
            <div class="text-[10px] text-muted">
              {{ summary?.failed_generations || 0 }} errors recorded
            </div>
          </div>

          <!-- Average Duration -->
          <div class="bg-card border border-border rounded-xl p-4 space-y-1 col-span-2 lg:col-span-1">
            <div class="flex items-center justify-between text-muted">
              <span class="text-[11px] font-medium uppercase tracking-wider">Avg Speed</span>
              <Clock class="w-4 h-4 text-zinc-400" />
            </div>
            <div class="text-2xl font-bold font-mono text-white">
              {{ summary?.avg_duration_ms || 0 }}<span class="text-xs text-muted ml-0.5">ms</span>
            </div>
            <div class="text-[10px] text-muted">
              compilation duration
            </div>
          </div>
        </div>

        <!-- 2. Daily Trends & Top Subjects Row -->
        <div class="grid grid-cols-1 lg:grid-cols-12 gap-6">
          <!-- Timeline Activity (7 cols) -->
          <div class="lg:col-span-7 bg-card border border-border rounded-xl p-5 space-y-4">
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2">
                <BarChart2 class="w-4 h-4 text-zinc-300" />
                <h3 class="text-xs font-semibold text-white tracking-wide">Daily Generation Volume</h3>
              </div>
              <span class="text-[11px] text-muted">Last 30 days</span>
            </div>

            <div v-if="summary?.daily_trends?.length" class="space-y-2 pt-2">
              <div class="h-40 flex items-end justify-start gap-3 pt-4 overflow-x-auto pb-1">
                <div
                  v-for="trend in summary.daily_trends"
                  :key="trend.date"
                  class="w-10 flex flex-col items-center gap-1 group relative h-full justify-end shrink-0"
                >
                  <!-- Tooltip -->
                  <div class="absolute -top-8 bg-zinc-900 border border-border text-white text-[10px] px-2 py-1 rounded shadow-lg opacity-0 group-hover:opacity-100 pointer-events-none transition z-20 whitespace-nowrap">
                    {{ trend.date }}: {{ trend.count }} runs ({{ trend.successes }} ok)
                  </div>

                  <!-- Value -->
                  <span class="text-[10px] font-mono text-zinc-400 group-hover:text-white transition">
                    {{ trend.count }}
                  </span>

                  <!-- Bar -->
                  <div
                    class="w-full bg-zinc-700 group-hover:bg-white rounded-t transition-all"
                    :style="{ height: `${Math.max((trend.count / maxDailyCount) * 75, 8)}%` }"
                  ></div>

                  <!-- Date label -->
                  <span class="text-[9px] text-zinc-500 font-mono truncate w-full text-center">
                    {{ trend.date.slice(5) }}
                  </span>
                </div>
              </div>
            </div>
            <div v-else class="text-center py-10 text-xs text-muted">
              No generation records yet. Run your first compilation to see daily trends.
            </div>
          </div>

          <!-- Top Subjects Breakdown (5 cols) -->
          <div class="lg:col-span-5 bg-card border border-border rounded-xl p-5 space-y-4">
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2">
                <BookOpen class="w-4 h-4 text-zinc-300" />
                <h3 class="text-xs font-semibold text-white tracking-wide">Most-Used Subjects</h3>
              </div>
              <span class="text-[11px] text-muted">Top 10</span>
            </div>

            <div v-if="summary?.top_subjects?.length" class="space-y-2.5 pt-1">
              <div
                v-for="sub in summary.top_subjects"
                :key="sub.subject"
                @click="handleSubjectFilter(sub.subject)"
                class="group cursor-pointer space-y-1 text-xs"
              >
                <div class="flex items-center justify-between text-zinc-300">
                  <span
                    class="truncate font-medium group-hover:text-white transition"
                    :class="{ 'text-white font-bold': selectedSubject === sub.subject }"
                  >
                    {{ sub.subject }}
                  </span>
                  <span class="text-[11px] font-mono text-muted shrink-0 ml-2">
                    {{ sub.count }} runs ({{ sub.students }} students)
                  </span>
                </div>
                <div class="h-1.5 w-full bg-inputBg rounded-full overflow-hidden">
                  <div
                    class="h-full bg-zinc-500 group-hover:bg-white transition-all rounded-full"
                    :class="{ '!bg-white': selectedSubject === sub.subject }"
                    :style="{ width: `${(sub.count / maxSubjectCount) * 100}%` }"
                  ></div>
                </div>
              </div>
            </div>
            <div v-else class="text-center py-10 text-xs text-muted">
              No subject data yet.
            </div>
          </div>
        </div>

        <!-- 3. Searchable Student Generation Log Table -->
        <div class="bg-card border border-border rounded-xl overflow-hidden space-y-0">
          <!-- Table Header & Filter Bar -->
          <div class="p-4 border-b border-border flex flex-wrap items-center justify-between gap-3 bg-card/60">
            <div class="flex items-center gap-2">
              <FileText class="w-4 h-4 text-zinc-300" />
              <h3 class="text-xs font-semibold text-white tracking-wide">
                Generation History Log ({{ totalEventsCount }})
              </h3>
              <span v-if="selectedSubject" class="text-[10px] bg-zinc-800 border border-zinc-700 text-zinc-300 px-2 py-0.5 rounded-full inline-flex items-center gap-1">
                Subject: {{ selectedSubject }}
                <button type="button" @click="selectedSubject = ''; loadEvents();" class="hover:text-white">&times;</button>
              </span>
            </div>

            <!-- Search Input Box -->
            <div class="flex items-center gap-2 w-full sm:w-auto">
              <div class="relative flex-1 sm:w-64">
                <Search class="w-3.5 h-3.5 text-zinc-400 absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  v-model="searchQuery"
                  @input="handleSearch"
                  type="text"
                  placeholder="Search name, roll no, class..."
                  class="w-full bg-inputBg border border-border rounded-lg pl-8 pr-3 py-1.5 text-xs text-white placeholder:text-muted outline-none focus:border-zinc-400"
                />
              </div>
            </div>
          </div>

          <!-- Table Content -->
          <div class="overflow-x-auto">
            <table class="w-full text-left text-xs">
              <thead class="bg-inputBg/80 text-[11px] text-muted uppercase font-semibold border-b border-border">
                <tr>
                  <th class="px-4 py-3">Timestamp (UTC)</th>
                  <th class="px-4 py-3">Student Name</th>
                  <th class="px-4 py-3">Roll No</th>
                  <th class="px-4 py-3">Subject</th>
                  <th class="px-4 py-3 text-center">Experiments</th>
                  <th class="px-4 py-3 text-right">Duration</th>
                  <th class="px-4 py-3 text-center">Status</th>
                  <th class="px-4 py-3 text-right">Details</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-border/60">
                <tr
                  v-for="ev in events"
                  :key="ev.id"
                  class="hover:bg-zinc-800/30 transition group"
                >
                  <td class="px-4 py-3 font-mono text-[11px] text-muted whitespace-nowrap">
                    {{ ev.timestamp.replace('T', ' ').replace('Z', '') }}
                  </td>
                  <td class="px-4 py-3 font-medium text-white whitespace-nowrap">
                    {{ ev.student_name }}
                  </td>
                  <td class="px-4 py-3 font-mono text-zinc-300 whitespace-nowrap">
                    {{ ev.roll_no }}
                  </td>
                  <td class="px-4 py-3 text-zinc-300 max-w-xs truncate" :title="ev.subject">
                    {{ ev.subject }}
                  </td>
                  <td class="px-4 py-3 text-center font-mono text-zinc-300">
                    {{ ev.experiment_count }}
                  </td>
                  <td class="px-4 py-3 text-right font-mono text-[11px] text-muted whitespace-nowrap">
                    {{ ev.duration_ms }} ms
                  </td>
                  <td class="px-4 py-3 text-center whitespace-nowrap">
                    <span
                      class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium"
                      :class="ev.success ? 'bg-emerald-950/60 text-emerald-400 border border-emerald-800/60' : 'bg-rose-950/60 text-rose-400 border border-rose-800/60'"
                    >
                      {{ ev.success ? 'Success' : 'Failed' }}
                    </span>
                  </td>
                  <td class="px-4 py-3 text-right">
                    <button
                      type="button"
                      @click="selectedEventForDetail = ev"
                      class="text-xs text-muted hover:text-white px-2 py-1 rounded bg-inputBg border border-border hover:border-zinc-500 transition"
                    >
                      View
                    </button>
                  </td>
                </tr>

                <tr v-if="events.length === 0">
                  <td colspan="8" class="text-center py-12 text-muted">
                    No generation events found.
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- Pagination Bar -->
          <div v-if="totalPages > 1" class="p-3.5 border-t border-border flex items-center justify-between text-xs text-muted bg-card/40">
            <span>Page {{ currentPage }} of {{ totalPages }}</span>
            <div class="flex items-center gap-2">
              <button
                type="button"
                :disabled="currentPage <= 1"
                @click="currentPage--; loadEvents();"
                class="px-2.5 py-1 rounded bg-inputBg border border-border hover:border-zinc-500 text-white disabled:opacity-40 transition"
              >
                Previous
              </button>
              <button
                type="button"
                :disabled="currentPage >= totalPages"
                @click="currentPage++; loadEvents();"
                class="px-2.5 py-1 rounded bg-inputBg border border-border hover:border-zinc-500 text-white disabled:opacity-40 transition"
              >
                Next
              </button>
            </div>
          </div>
        </div>
      </div>
    </main>

    <!-- Event Details Modal Drawer -->
    <div
      v-if="selectedEventForDetail"
      class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm"
      @click.self="selectedEventForDetail = null"
    >
      <div class="bg-card border border-border rounded-2xl max-w-lg w-full overflow-hidden shadow-2xl flex flex-col max-h-[85vh]">
        <div class="flex items-center justify-between px-5 py-4 border-b border-border">
          <div class="flex items-center gap-2">
            <FileText class="w-4 h-4 text-zinc-300" />
            <h3 class="text-sm font-semibold text-white">Generation Run Details</h3>
          </div>
          <button
            type="button"
            @click="selectedEventForDetail = null"
            class="text-zinc-400 hover:text-white p-1 rounded-lg hover:bg-zinc-800 transition"
          >
            &times;
          </button>
        </div>

        <div class="p-5 overflow-y-auto space-y-4 text-xs">
          <!-- Student Summary Grid -->
          <div class="grid grid-cols-2 gap-3 bg-inputBg/60 border border-border p-3.5 rounded-xl text-zinc-300">
            <div>
              <span class="text-[10px] text-muted uppercase block">Student Name</span>
              <span class="font-semibold text-white">{{ selectedEventForDetail.student_name }}</span>
            </div>
            <div>
              <span class="text-[10px] text-muted uppercase block">Roll Number</span>
              <span class="font-mono text-white">{{ selectedEventForDetail.roll_no }}</span>
            </div>
            <div>
              <span class="text-[10px] text-muted uppercase block">Class & Batch</span>
              <span>{{ selectedEventForDetail.class_name }} ({{ selectedEventForDetail.batch }})</span>
            </div>
            <div>
              <span class="text-[10px] text-muted uppercase block">Semester</span>
              <span>{{ selectedEventForDetail.sem }}</span>
            </div>
            <div class="col-span-2">
              <span class="text-[10px] text-muted uppercase block">Subject</span>
              <span class="text-zinc-200 font-medium">{{ selectedEventForDetail.subject }}</span>
            </div>
          </div>

          <!-- Error Details if failed -->
          <div v-if="selectedEventForDetail.error_message" class="bg-rose-950/40 border border-rose-800 p-3 rounded-xl text-rose-300 space-y-1">
            <div class="flex items-center gap-1.5 font-semibold">
              <AlertTriangle class="w-3.5 h-3.5" />
              <span>Compilation Error</span>
            </div>
            <p class="font-mono text-[11px]">{{ selectedEventForDetail.error_message }}</p>
          </div>

          <!-- Experiments List -->
          <div class="space-y-2">
            <h4 class="text-xs font-semibold text-white uppercase tracking-wider">
              Experiments Compiled ({{ selectedEventForDetail.experiments.length }})
            </h4>
            <div class="space-y-1.5 max-h-56 overflow-y-auto pr-1">
              <div
                v-for="(exp, idx) in selectedEventForDetail.experiments"
                :key="idx"
                class="bg-inputBg/40 border border-border/80 p-2.5 rounded-lg flex items-start justify-between gap-2"
              >
                <div class="flex-1 space-y-0.5">
                  <div class="flex items-center gap-1.5">
                    <span class="text-[10px] font-mono px-1 rounded bg-zinc-800 text-zinc-300">
                      {{ exp.is_assignment ? 'Assign' : 'Exp' }} {{ exp.label }}
                    </span>
                    <span class="font-medium text-white text-xs">{{ exp.title || 'Untitled' }}</span>
                  </div>
                  <div class="text-[10px] text-muted flex items-center gap-3">
                    <span v-if="exp.perf_date">Perf: {{ exp.perf_date }}</span>
                    <span v-if="exp.sub_date">Sub: {{ exp.sub_date }}</span>
                    <span v-if="exp.pages">Pages: {{ exp.pages }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="px-5 py-3 border-t border-border bg-inputBg/40 flex justify-end">
          <button
            type="button"
            @click="selectedEventForDetail = null"
            class="bg-white hover:bg-zinc-200 text-black font-semibold px-4 py-1.5 rounded-lg text-xs transition"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
