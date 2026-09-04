<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import {
  ShieldCheck,
  ShieldAlert,
  Users,
  FileText,
  AlertTriangle,
  Activity,
  Clock,
  Search,
  RefreshCw,
  Download,
  ChevronRight,
  ChevronDown,
  X,
  CheckCircle2,
  XCircle,
  HardDrive,
  Lock,
  LogOut,
  BookOpen,
  Layers,
} from '@lucide/vue'
import {
  checkHealth,
  getAnalyticsStatus,
  authenticateAdmin,
  getAnalyticsSummary,
  getStudents,
  getStudentDetail,
  getGenerationEvents,
  getFailedAims,
  getExportDownloadUrl,
  getSampleDownloadUrl,
  type AnalyticsSummary,
  type StudentSummaryItem,
  type StudentDossier,
  type GenerationEventItem,
  type FailedAimDocument,
  type ExtractionDiagnosticsSummary,
  type HealthResponse,
  type DailyTrendItem,
} from '../api/analytics'
import { navigate } from '../utils/router'

// ── Authentication & Global State ──────────────────────────────────────────
const AUTH_KEY = 'labstudio_analytics_admin_key'
const isAuthRequired = ref(false)
const isAuthenticated = ref(true)
const passwordInput = ref('')
const authError = ref('')
const isAuthSubmitting = ref(false)

const activeTab = ref<'pulse' | 'students' | 'events' | 'failedAims'>('pulse')
const isLoading = ref(true)
const autoRefreshInterval = ref<number>(0) // 0 = off, 15, 30
let autoRefreshTimer: any = null

// Server Health
const serverHealth = ref<HealthResponse | null>(null)

// Tab 1: Pulse Summary Data
const summary = ref<AnalyticsSummary | null>(null)

// Tab 2: Students Directory Data
const students = ref<StudentSummaryItem[]>([])
const totalStudents = ref(0)
const studentQuery = ref('')
const studentClassFilter = ref('')
const studentBatchFilter = ref('')
const studentSortBy = ref('last_active')
const studentPage = ref(1)
const studentLimit = 20
const availableClasses = ref<string[]>([])
const availableBatches = ref<string[]>([])
const selectedStudentDossier = ref<StudentDossier | null>(null)
const isLoadingDossier = ref(false)

// Tab 3: Live Compilations Data
const events = ref<GenerationEventItem[]>([])
const totalEvents = ref(0)
const eventQuery = ref('')
const eventSubjectFilter = ref('')
const eventPage = ref(1)
const eventLimit = 25
const selectedEventForDetail = ref<GenerationEventItem | null>(null)

// Tab 4: Failed Aim Extractions Data
const failedDocs = ref<FailedAimDocument[]>([])
const totalFailedDocs = ref(0)
const diagnosticsSummary = ref<ExtractionDiagnosticsSummary | null>(null)
const failedQuery = ref('')
const failedReasonFilter = ref('')
const failedMethodFilter = ref('')
const discrepancyOnly = ref(false)
const failedPage = ref(1)
const failedLimit = 20
const expandedSnippetHash = ref<string | null>(null)

// ── Formatting Utilities ───────────────────────────────────────────────────
function formatBytes(bytes?: number): string {
  if (!bytes) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`
}

function formatUptime(seconds?: number): string {
  if (!seconds) return '0m'
  const d = Math.floor(seconds / (3600 * 24))
  const h = Math.floor((seconds % (3600 * 24)) / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  if (d > 0) return `${d}d ${h}h`
  if (h > 0) return `${h}h ${m}m`
  return `${m}m`
}

function formatDate(isoStr?: string): string {
  if (!isoStr) return '—'
  try {
    const d = new Date(isoStr)
    return d.toLocaleString('en-IN', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return isoStr
  }
}

function formatRelativeTime(isoStr?: string): string {
  if (!isoStr) return '—'
  try {
    const date = new Date(isoStr)
    const diffSec = Math.floor((Date.now() - date.getTime()) / 1000)
    if (diffSec < 60) return 'Just now'
    if (diffSec < 3600) return `${Math.floor(diffSec / 60)}m ago`
    if (diffSec < 86400) return `${Math.floor(diffSec / 3600)}h ago`
    const days = Math.floor(diffSec / 86400)
    if (days === 1) return 'Yesterday'
    if (days < 30) return `${days}d ago`
    return dToStr(date)
  } catch {
    return isoStr
  }
}

function dToStr(d: Date): string {
  return d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short' })
}

function getInitials(name: string): string {
  if (!name || name === 'Anonymous') return 'AN'
  const parts = name.trim().split(/\s+/)
  if (parts.length >= 2) return `${parts[0][0]}${parts[1][0]}`.toUpperCase()
  return name.slice(0, 2).toUpperCase()
}

// ── Auth & Data Loading ────────────────────────────────────────────────────
function getStoredToken(): string {
  return sessionStorage.getItem(AUTH_KEY) || ''
}

function setStoredToken(t: string): void {
  if (t) sessionStorage.setItem(AUTH_KEY, t)
  else sessionStorage.removeItem(AUTH_KEY)
}

async function checkAuthAndInit(): Promise<void> {
  isLoading.value = true
  authError.value = ''
  try {
    const status = await getAnalyticsStatus()
    isAuthRequired.value = status.auth_required

    if (status.auth_required) {
      const stored = getStoredToken()
      if (!stored) {
        isAuthenticated.value = false
        isLoading.value = false
        return
      }
      isAuthenticated.value = true
    } else {
      isAuthenticated.value = true
    }

    await refreshActiveTab()
  } catch (err: any) {
    if (err?.status === 401) {
      isAuthenticated.value = false
      setStoredToken('')
    }
  } finally {
    isLoading.value = false
  }
}

async function handleLogin(): Promise<void> {
  if (!passwordInput.value.trim()) {
    authError.value = 'Please enter the admin password.'
    return
  }
  isAuthSubmitting.value = true
  authError.value = ''
  try {
    const res = await authenticateAdmin(passwordInput.value.trim())
    if (res.valid) {
      setStoredToken(passwordInput.value.trim())
      isAuthenticated.value = true
      passwordInput.value = ''
      await refreshActiveTab()
    } else {
      authError.value = 'Invalid admin password.'
    }
  } catch (err: any) {
    authError.value = err.message || 'Authentication failed. Please check password.'
  } finally {
    isAuthSubmitting.value = false
  }
}

function handleLogout(): void {
  setStoredToken('')
  isAuthenticated.value = false
  passwordInput.value = ''
}

// ── Tab Refresh Orchestration ──────────────────────────────────────────────
async function refreshActiveTab(): Promise<void> {
  try {
    loadHealth()
    if (activeTab.value === 'pulse') {
      await loadPulseSummary()
    } else if (activeTab.value === 'students') {
      await loadStudentsData()
    } else if (activeTab.value === 'events') {
      await loadEventsData()
    } else if (activeTab.value === 'failedAims') {
      await loadFailedAimsData()
    }
  } catch (err: any) {
    if (err?.status === 401) {
      isAuthenticated.value = false
      setStoredToken('')
    }
  }
}

async function loadHealth(): Promise<void> {
  try {
    serverHealth.value = await checkHealth()
  } catch {
    // health is non-blocking
  }
}

async function loadPulseSummary(): Promise<void> {
  summary.value = await getAnalyticsSummary()
}

async function loadStudentsData(): Promise<void> {
  const res = await getStudents({
    q: studentQuery.value,
    class_name: studentClassFilter.value,
    batch: studentBatchFilter.value,
    sort_by: studentSortBy.value,
    limit: studentLimit,
    offset: (studentPage.value - 1) * studentLimit,
  })
  students.value = res.students
  totalStudents.value = res.total
  availableClasses.value = res.classes
  availableBatches.value = res.batches
}

async function openStudentDossier(s: StudentSummaryItem): Promise<void> {
  isLoadingDossier.value = true
  selectedStudentDossier.value = null
  try {
    selectedStudentDossier.value = await getStudentDetail(s.roll_no, s.student_name)
  } catch (err) {
    console.error('Failed to load student dossier:', err)
  } finally {
    isLoadingDossier.value = false
  }
}

function closeStudentDossier(): void {
  selectedStudentDossier.value = null
}

async function loadEventsData(): Promise<void> {
  const res = await getGenerationEvents({
    q: eventQuery.value,
    subject: eventSubjectFilter.value,
    limit: eventLimit,
    offset: (eventPage.value - 1) * eventLimit,
  })
  events.value = res.events
  totalEvents.value = res.total
}

async function loadFailedAimsData(): Promise<void> {
  const res = await getFailedAims({
    q: failedQuery.value,
    reason: failedReasonFilter.value,
    method: failedMethodFilter.value,
    discrepancy_only: discrepancyOnly.value,
    limit: failedLimit,
    offset: (failedPage.value - 1) * failedLimit,
  })
  failedDocs.value = res.documents
  totalFailedDocs.value = res.total
  diagnosticsSummary.value = res.summary
}

function toggleSnippet(hash: string): void {
  if (expandedSnippetHash.value === hash) expandedSnippetHash.value = null
  else expandedSnippetHash.value = hash
}

function handleTabChange(tab: 'pulse' | 'students' | 'events' | 'failedAims'): void {
  activeTab.value = tab
  refreshActiveTab()
}

function setAutoRefresh(interval: number): void {
  autoRefreshInterval.value = interval
  if (autoRefreshTimer) {
    clearInterval(autoRefreshTimer)
    autoRefreshTimer = null
  }
  if (interval > 0) {
    autoRefreshTimer = setInterval(() => {
      refreshActiveTab()
    }, interval * 1000)
  }
}

// ── SVG Activity Chart Computations ────────────────────────────────────────
const maxTrendCount = computed(() => {
  if (!summary.value?.daily_trends?.length) return 10
  return Math.max(...summary.value.daily_trends.map((t: DailyTrendItem) => t.count), 5)
})

// ── Lifecycle ──────────────────────────────────────────────────────────────
onMounted(() => {
  checkAuthAndInit()
})

onUnmounted(() => {
  if (autoRefreshTimer) clearInterval(autoRefreshTimer)
})
</script>

<template>
  <div class="min-h-screen flex flex-col bg-surface text-hi selection:bg-amber-dim/50 selection:text-hi">
    <!-- Top Global Header -->
    <header class="h-14 border-b border-edge bg-surface/90 backdrop-blur-md px-4 sm:px-6 flex items-center justify-between sticky top-0 z-30">
      <div class="flex items-center space-x-3 min-w-0">
        <div class="w-8 h-8 rounded-lg bg-amber flex items-center justify-center shadow-sm shrink-0">
          <ShieldCheck class="w-5 h-5 text-surface" />
        </div>
        <div class="min-w-0">
          <div class="flex items-center gap-2">
            <h1 class="text-sm font-semibold tracking-tight text-hi truncate">
              LabStudio Analytics
            </h1>
            <span class="text-[10px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded bg-amber-dim/30 text-amber border border-amber/30 shrink-0">
              Admin Portal
            </span>
          </div>
          <p class="text-[11px] text-mid truncate hidden sm:block">
            Student dossiers, generation telemetry & heuristic discovery
          </p>
        </div>
      </div>

      <!-- Right Global Actions -->
      <div class="flex items-center space-x-2 sm:space-x-3 text-xs">
        <!-- Server Storage & Uptime Pill -->
        <div v-if="serverHealth" class="hidden md:flex items-center gap-2 px-2.5 py-1 rounded-md bg-card border border-edge text-mid text-[11px]">
          <HardDrive class="w-3.5 h-3.5 text-amber" />
          <span>{{ formatBytes(serverHealth.storage.used_bytes) }} / {{ formatBytes(serverHealth.storage.max_bytes) }}</span>
          <span class="text-lo">&bull;</span>
          <span class="text-lo">Up {{ formatUptime(serverHealth.uptime_seconds) }}</span>
        </div>

        <!-- Export Dropdown / Buttons -->
        <div v-if="isAuthenticated" class="relative group">
          <button
            class="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-input border border-edge text-hi hover:border-edge-hi transition font-medium"
            title="Download Reports"
          >
            <Download class="w-3.5 h-3.5 text-amber" />
            <span class="hidden sm:inline">Export</span>
            <ChevronDown class="w-3 h-3 text-mid" />
          </button>
          <div class="absolute right-0 top-full mt-1 w-48 rounded-xl bg-card border border-edge shadow-xl py-1 hidden group-hover:block z-50">
            <a
              :href="getExportDownloadUrl('students', 'csv')"
              target="_blank"
              class="flex items-center gap-2 px-3 py-2 text-xs text-hi hover:bg-input hover:text-amber transition"
            >
              <Users class="w-3.5 h-3.5 text-amber" />
              <span>Student Summary CSV</span>
            </a>
            <a
              :href="getExportDownloadUrl('events', 'csv')"
              target="_blank"
              class="flex items-center gap-2 px-3 py-2 text-xs text-hi hover:bg-input hover:text-amber transition"
            >
              <FileText class="w-3.5 h-3.5 text-amber" />
              <span>All Events CSV</span>
            </a>
            <a
              :href="getExportDownloadUrl('events', 'json')"
              target="_blank"
              class="flex items-center gap-2 px-3 py-2 text-xs text-hi hover:bg-input hover:text-amber transition"
            >
              <Layers class="w-3.5 h-3.5 text-amber" />
              <span>Complete Data JSON</span>
            </a>
          </div>
        </div>

        <!-- Auto Refresh Toggle -->
        <button
          v-if="isAuthenticated"
          @click="setAutoRefresh(autoRefreshInterval === 0 ? 15 : autoRefreshInterval === 15 ? 30 : 0)"
          class="flex items-center gap-1 px-2.5 py-1.5 rounded-lg border transition text-xs font-medium"
          :class="autoRefreshInterval > 0 ? 'bg-amber-dim/20 border-amber/40 text-amber' : 'bg-input border-edge text-mid hover:text-hi'"
          :title="`Auto-Refresh: ${autoRefreshInterval > 0 ? autoRefreshInterval + 's' : 'Off'}`"
        >
          <RefreshCw class="w-3.5 h-3.5" :class="{ 'animate-spin': autoRefreshInterval > 0 }" />
          <span class="hidden sm:inline">{{ autoRefreshInterval > 0 ? `${autoRefreshInterval}s` : 'Manual' }}</span>
        </button>

        <!-- Back to Studio -->
        <button
          @click="navigate('/')"
          class="px-2.5 py-1.5 rounded-lg bg-input border border-edge text-mid hover:text-hi hover:border-edge-hi transition font-medium"
        >
          Studio &rarr;
        </button>

        <!-- Logout if password enabled -->
        <button
          v-if="isAuthenticated && isAuthRequired"
          @click="handleLogout"
          class="p-1.5 rounded-lg bg-input border border-edge text-lo hover:text-danger hover:border-danger/30 transition"
          title="Lock Analytics"
        >
          <LogOut class="w-4 h-4" />
        </button>
      </div>
    </header>

    <!-- ── AUTHENTICATION PASSCODE GATEKEEPER ─────────────────────────────── -->
    <main v-if="!isAuthenticated" class="flex-1 flex items-center justify-center p-6">
      <div class="max-w-md w-full p-8 rounded-2xl border border-edge bg-card shadow-2xl text-center">
        <div class="w-12 h-12 rounded-xl bg-amber-dim/30 border border-amber/30 flex items-center justify-center mx-auto mb-4 text-amber shadow-sm">
          <Lock class="w-6 h-6" />
        </div>
        <h2 class="text-base font-semibold text-hi mb-1">
          Administrative Authentication
        </h2>
        <p class="text-xs text-mid leading-relaxed mb-6">
          This portal is protected. Enter the admin password configured in your environment to view student dossiers and diagnostics.
        </p>

        <form @submit.prevent="handleLogin" class="space-y-4">
          <div class="relative">
            <input
              v-model="passwordInput"
              type="password"
              placeholder="Enter Admin Password..."
              class="w-full h-10 px-3.5 rounded-lg bg-input border border-edge text-hi placeholder:text-lo text-sm focus:outline-none focus:border-amber focus:ring-1 focus:ring-amber transition"
              autocomplete="current-password"
              autofocus
            />
          </div>

          <div v-if="authError" class="p-2.5 rounded-lg bg-danger/10 border border-danger/30 text-danger text-xs flex items-center gap-2">
            <ShieldAlert class="w-4 h-4 shrink-0" />
            <span>{{ authError }}</span>
          </div>

          <button
            type="submit"
            :disabled="isAuthSubmitting"
            class="w-full h-10 rounded-lg bg-amber hover:bg-amber-hi text-surface font-semibold text-xs tracking-wide transition flex items-center justify-center gap-2 disabled:opacity-50 shadow-sm"
          >
            <ShieldCheck class="w-4 h-4" />
            <span>{{ isAuthSubmitting ? 'Verifying...' : 'Unlock Portal' }}</span>
          </button>
        </form>
      </div>
    </main>

    <!-- ── AUTHENTICATED DASHBOARD ────────────────────────────────────────── -->
    <template v-else>
      <!-- Navigation Tabs Ribbon -->
      <div class="border-b border-edge bg-surface sticky top-14 z-20 px-4 sm:px-6">
        <div class="max-w-6xl mx-auto flex gap-1 sm:gap-2 overflow-x-auto py-2 scrollbar-none">
          <button
            @click="handleTabChange('pulse')"
            class="flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-medium transition shrink-0"
            :class="activeTab === 'pulse' ? 'bg-amber text-surface font-semibold shadow-sm' : 'bg-input border border-edge text-mid hover:text-hi hover:border-edge-hi'"
          >
            <Activity class="w-3.5 h-3.5" />
            <span>Overview Pulse</span>
          </button>

          <button
            @click="handleTabChange('students')"
            class="flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-medium transition shrink-0"
            :class="activeTab === 'students' ? 'bg-amber text-surface font-semibold shadow-sm' : 'bg-input border border-edge text-mid hover:text-hi hover:border-edge-hi'"
          >
            <Users class="w-3.5 h-3.5" />
            <span>Student Directory</span>
            <span
              v-if="totalStudents > 0"
              class="text-[10px] px-1.5 py-0.2 rounded-full"
              :class="activeTab === 'students' ? 'bg-surface/20 text-surface' : 'bg-edge text-lo'"
            >
              {{ totalStudents }}
            </span>
          </button>

          <button
            @click="handleTabChange('events')"
            class="flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-medium transition shrink-0"
            :class="activeTab === 'events' ? 'bg-amber text-surface font-semibold shadow-sm' : 'bg-input border border-edge text-mid hover:text-hi hover:border-edge-hi'"
          >
            <FileText class="w-3.5 h-3.5" />
            <span>Live Compilations</span>
            <span
              v-if="totalEvents > 0"
              class="text-[10px] px-1.5 py-0.2 rounded-full"
              :class="activeTab === 'events' ? 'bg-surface/20 text-surface' : 'bg-edge text-lo'"
            >
              {{ totalEvents }}
            </span>
          </button>

          <button
            @click="handleTabChange('failedAims')"
            class="flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-medium transition shrink-0"
            :class="activeTab === 'failedAims' ? 'bg-amber text-surface font-semibold shadow-sm' : 'bg-input border border-edge text-mid hover:text-hi hover:border-edge-hi'"
          >
            <AlertTriangle class="w-3.5 h-3.5" />
            <span>Failed Aim Extractions</span>
            <span
              v-if="totalFailedDocs > 0"
              class="text-[10px] px-1.5 py-0.2 rounded-full"
              :class="activeTab === 'failedAims' ? 'bg-surface/20 text-surface' : 'bg-danger/20 text-danger border border-danger/30'"
            >
              {{ totalFailedDocs }}
            </span>
          </button>
        </div>
      </div>

      <!-- Main Content Container -->
      <main class="flex-1 max-w-6xl w-full mx-auto p-4 sm:p-6">
        <!-- ── TAB 1: OVERVIEW PULSE ──────────────────────────────────────── -->
        <div v-if="activeTab === 'pulse'" class="space-y-6">
          <!-- KPI Row -->
          <div v-if="summary" class="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
            <!-- Total Compilations -->
            <div class="p-4 rounded-xl border border-edge bg-card">
              <div class="flex items-center justify-between text-mid text-xs mb-1">
                <span>Compilations</span>
                <span class="text-[10px] font-semibold px-1.5 py-0.5 rounded bg-success/10 text-success border border-success/30">
                  {{ summary.success_rate }}% Success
                </span>
              </div>
              <div class="text-2xl font-bold text-hi">
                {{ summary.total_generations }}
              </div>
              <p class="text-[11px] text-lo mt-0.5">
                {{ summary.successful_generations }} succeeded &bull; {{ summary.failed_generations }} failed
              </p>
            </div>

            <!-- Unique Students -->
            <div class="p-4 rounded-xl border border-edge bg-card">
              <div class="flex items-center justify-between text-mid text-xs mb-1">
                <span>Active Students</span>
                <Users class="w-3.5 h-3.5 text-amber" />
              </div>
              <div class="text-2xl font-bold text-hi">
                {{ summary.unique_students }}
              </div>
              <p class="text-[11px] text-lo mt-0.5">
                Distinct student identities recorded
              </p>
            </div>

            <!-- Total Experiments Generated -->
            <div class="p-4 rounded-xl border border-edge bg-card">
              <div class="flex items-center justify-between text-mid text-xs mb-1">
                <span>Total Experiments</span>
                <BookOpen class="w-3.5 h-3.5 text-amber" />
              </div>
              <div class="text-2xl font-bold text-hi">
                {{ summary.total_experiments_generated }}
              </div>
              <p class="text-[11px] text-lo mt-0.5">
                Report sections merged and stamped
              </p>
            </div>

            <!-- Avg Pipeline Latency -->
            <div class="p-4 rounded-xl border border-edge bg-card">
              <div class="flex items-center justify-between text-mid text-xs mb-1">
                <span>Avg Duration</span>
                <Clock class="w-3.5 h-3.5 text-amber" />
              </div>
              <div class="text-2xl font-bold text-hi">
                {{ summary.avg_duration_ms }} ms
              </div>
              <p class="text-[11px] text-lo mt-0.5">
                p50 generation & merging latency
              </p>
            </div>
          </div>

          <!-- Two-Column Analytics Layout -->
          <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <!-- Left 2 Cols: 30-Day Activity Chart & Top Subjects -->
            <div class="lg:col-span-2 space-y-6">
              <!-- Native SVG 30-Day Activity Chart -->
              <div class="p-5 rounded-2xl border border-edge bg-card shadow-sm">
                <div class="flex items-center justify-between mb-4">
                  <div>
                    <h3 class="text-xs font-semibold uppercase tracking-wider text-mid">
                      Daily Compilation Volume
                    </h3>
                    <p class="text-xs text-lo">Daily generation events over the last 30 active days</p>
                  </div>
                  <div class="flex items-center gap-3 text-[11px]">
                    <span class="flex items-center gap-1 text-success">
                      <span class="w-2 h-2 rounded-full bg-success"></span>
                      Success
                    </span>
                    <span class="flex items-center gap-1 text-danger">
                      <span class="w-2 h-2 rounded-full bg-danger"></span>
                      Failed
                    </span>
                  </div>
                </div>

                <div v-if="summary?.daily_trends?.length" class="w-full overflow-x-auto">
                  <svg viewBox="0 0 600 140" class="w-full h-36">
                    <!-- Grid Lines -->
                    <line x1="0" y1="20" x2="600" y2="20" stroke="#242426" stroke-dasharray="3 3" />
                    <line x1="0" y1="60" x2="600" y2="60" stroke="#242426" stroke-dasharray="3 3" />
                    <line x1="0" y1="100" x2="600" y2="100" stroke="#242426" stroke-dasharray="3 3" />

                    <!-- Bars -->
                    <g v-for="(day, idx) in summary.daily_trends" :key="day.date">
                      <!-- Bar position calculations -->
                      <g :transform="`translate(${idx * (600 / Math.max(summary.daily_trends.length, 1)) + 4}, 0)`">
                        <!-- Success Bar -->
                        <rect
                          :y="120 - Math.round((day.successes / maxTrendCount) * 100)"
                          :height="Math.max(Math.round((day.successes / maxTrendCount) * 100), 2)"
                          :width="Math.max(Math.floor((600 / summary.daily_trends.length) - 6), 6)"
                          rx="2"
                          class="fill-success/80 hover:fill-success transition"
                        >
                          <title>{{ day.date }}: {{ day.successes }} successful compilations</title>
                        </rect>
                        <!-- Failure Bar (stacked on top if any) -->
                        <rect
                          v-if="day.count - day.successes > 0"
                          :y="120 - Math.round((day.count / maxTrendCount) * 100)"
                          :height="Math.max(Math.round(((day.count - day.successes) / maxTrendCount) * 100), 2)"
                          :width="Math.max(Math.floor((600 / summary.daily_trends.length) - 6), 6)"
                          rx="2"
                          class="fill-danger/80 hover:fill-danger transition"
                        >
                          <title>{{ day.date }}: {{ day.count - day.successes }} failed compilations</title>
                        </rect>
                        <!-- Date label on every 5th item -->
                        <text
                          v-if="idx % Math.ceil(summary.daily_trends.length / 7) === 0"
                          x="0"
                          y="135"
                          font-size="9"
                          fill="#555555"
                        >
                          {{ day.date.slice(5) }}
                        </text>
                      </g>
                    </g>
                  </svg>
                </div>
                <div v-else class="h-32 flex items-center justify-center text-xs text-lo">
                  No generation trends recorded yet.
                </div>
              </div>

              <!-- Top Subjects Leaderboard -->
              <div class="p-5 rounded-2xl border border-edge bg-card shadow-sm">
                <h3 class="text-xs font-semibold uppercase tracking-wider text-mid mb-3">
                  Top Subjects by Compilation Demand
                </h3>
                <div v-if="summary?.top_subjects?.length" class="space-y-3">
                  <div
                    v-for="sub in summary.top_subjects"
                    :key="sub.subject"
                    class="flex items-center justify-between p-2.5 rounded-lg bg-input border border-edge text-xs"
                  >
                    <div class="flex items-center gap-2.5 min-w-0 flex-1">
                      <div class="w-7 h-7 rounded bg-amber-dim/20 text-amber flex items-center justify-center shrink-0 text-[11px] font-bold">
                        {{ sub.count }}
                      </div>
                      <div class="min-w-0 flex-1">
                        <div class="font-medium text-hi truncate">{{ sub.subject }}</div>
                        <div class="text-[11px] text-lo">{{ sub.students }} distinct students</div>
                      </div>
                    </div>
                    <span class="text-mid font-mono text-[11px] shrink-0 ml-3">
                      {{ sub.count }} builds
                    </span>
                  </div>
                </div>
                <div v-else class="text-xs text-lo py-6 text-center">
                  No subject records found.
                </div>
              </div>
            </div>

            <!-- Right Col: Top Experiments & Server Info -->
            <div class="space-y-6">
              <!-- Top Experiments -->
              <div class="p-5 rounded-2xl border border-edge bg-card shadow-sm">
                <h3 class="text-xs font-semibold uppercase tracking-wider text-mid mb-3">
                  Popular Experiment Aims
                </h3>
                <div v-if="summary?.top_experiments?.length" class="space-y-2">
                  <div
                    v-for="exp in summary.top_experiments"
                    :key="exp.name"
                    class="p-2.5 rounded-lg bg-input border border-edge text-xs flex items-center justify-between gap-2"
                  >
                    <span class="text-hi truncate flex-1" :title="exp.name">{{ exp.name }}</span>
                    <span class="text-amber font-mono text-[11px] shrink-0 font-semibold">{{ exp.count }}x</span>
                  </div>
                </div>
                <div v-else class="text-xs text-lo py-6 text-center">
                  No experiment items aggregated yet.
                </div>
              </div>

              <!-- Server Telemetry & Database Status -->
              <div class="p-5 rounded-2xl border border-edge bg-card shadow-sm space-y-3">
                <h3 class="text-xs font-semibold uppercase tracking-wider text-mid">
                  Engine & Telemetry Status
                </h3>
                <div class="space-y-2 text-xs">
                  <div class="flex items-center justify-between py-1 border-b border-edge">
                    <span class="text-mid">Storage Engine</span>
                    <span class="text-hi font-mono">SQLite WAL Mode</span>
                  </div>
                  <div class="flex items-center justify-between py-1 border-b border-edge">
                    <span class="text-mid">Server Version</span>
                    <span class="text-hi font-mono">{{ serverHealth?.version || '3.1.0' }}</span>
                  </div>
                  <div class="flex items-center justify-between py-1 border-b border-edge">
                    <span class="text-mid">Uptime</span>
                    <span class="text-hi font-mono">{{ formatUptime(serverHealth?.uptime_seconds) }}</span>
                  </div>
                  <div class="flex items-center justify-between py-1">
                    <span class="text-mid">Disk Usage</span>
                    <span class="text-amber font-mono">{{ serverHealth?.storage?.percent_used ?? 0 }}%</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- ── TAB 2: STUDENT DIRECTORY (STUDENT-WISE ANALYTICS) ──────────── -->
        <div v-else-if="activeTab === 'students'" class="space-y-4">
          <!-- Directory Search & Filter Ribbon -->
          <div class="p-4 rounded-2xl border border-edge bg-card shadow-sm flex flex-col md:flex-row gap-3 items-stretch md:items-center justify-between">
            <div class="flex flex-col sm:flex-row gap-2.5 flex-1 min-w-0">
              <!-- Search Input -->
              <div class="relative flex-1 min-w-0">
                <Search class="w-4 h-4 text-lo absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
                <input
                  v-model="studentQuery"
                  @input="loadStudentsData"
                  type="text"
                  placeholder="Search by student name or roll number..."
                  class="w-full h-9 pl-9 pr-3 rounded-lg bg-input border border-edge text-hi placeholder:text-lo text-xs focus:outline-none focus:border-amber transition"
                />
              </div>

              <!-- Class Filter -->
              <select
                v-model="studentClassFilter"
                @change="loadStudentsData"
                class="h-9 px-3 rounded-lg bg-input border border-edge text-hi text-xs focus:outline-none focus:border-amber transition"
              >
                <option value="">All Classes</option>
                <option v-for="c in availableClasses" :key="c" :value="c">{{ c }}</option>
              </select>

              <!-- Batch Filter -->
              <select
                v-model="studentBatchFilter"
                @change="loadStudentsData"
                class="h-9 px-3 rounded-lg bg-input border border-edge text-hi text-xs focus:outline-none focus:border-amber transition"
              >
                <option value="">All Batches</option>
                <option v-for="b in availableBatches" :key="b" :value="b">Batch {{ b }}</option>
              </select>

              <!-- Sort Filter -->
              <select
                v-model="studentSortBy"
                @change="loadStudentsData"
                class="h-9 px-3 rounded-lg bg-input border border-edge text-hi text-xs focus:outline-none focus:border-amber transition"
              >
                <option value="last_active">Sort: Last Active</option>
                <option value="compilations">Sort: Compilations</option>
                <option value="experiments">Sort: Total Experiments</option>
                <option value="roll_no">Sort: Roll Number</option>
                <option value="name">Sort: Name</option>
              </select>
            </div>

            <!-- Export Students CSV Button -->
            <a
              :href="getExportDownloadUrl('students', 'csv')"
              target="_blank"
              class="h-9 px-3.5 rounded-lg bg-input hover:bg-amber hover:text-surface border border-edge text-hi text-xs font-semibold transition flex items-center justify-center gap-1.5 shrink-0"
            >
              <Download class="w-3.5 h-3.5" />
              <span>Export CSV</span>
            </a>
          </div>

          <!-- Students Directory Cards Grid -->
          <div v-if="students.length" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            <div
              v-for="st in students"
              :key="`${st.roll_no}_${st.student_name}`"
              @click="openStudentDossier(st)"
              class="p-4 rounded-xl border border-edge bg-card hover:border-amber/50 hover:shadow-lg transition cursor-pointer flex flex-col justify-between group"
            >
              <div>
                <div class="flex items-start justify-between gap-2 mb-2">
                  <div class="flex items-center gap-2.5 min-w-0">
                    <div class="w-9 h-9 rounded-lg bg-amber-dim/30 border border-amber/30 text-amber flex items-center justify-center font-bold text-xs shrink-0">
                      {{ getInitials(st.student_name) }}
                    </div>
                    <div class="min-w-0">
                      <div class="font-semibold text-xs text-hi truncate group-hover:text-amber transition">
                        {{ st.student_name }}
                      </div>
                      <div class="text-[11px] text-lo flex items-center gap-1.5">
                        <span class="font-mono text-mid">Roll #{{ st.roll_no }}</span>
                        <span>&bull;</span>
                        <span>{{ st.class_name }}</span>
                        <span v-if="st.batch !== '—'">({{ st.batch }})</span>
                      </div>
                    </div>
                  </div>

                  <span class="text-[10px] font-semibold px-2 py-0.5 rounded bg-input border border-edge text-mid shrink-0">
                    {{ st.total_compilations }} builds
                  </span>
                </div>

                <!-- Subjects Chips -->
                <div class="flex flex-wrap gap-1 mt-2.5">
                  <span
                    v-for="sub in st.subjects.slice(0, 3)"
                    :key="sub"
                    class="text-[10px] px-2 py-0.5 rounded-md bg-input border border-edge text-mid truncate max-w-[140px]"
                  >
                    {{ sub }}
                  </span>
                  <span v-if="st.subjects.length > 3" class="text-[10px] px-1.5 py-0.5 rounded-md bg-input text-lo">
                    +{{ st.subjects.length - 3 }} more
                  </span>
                </div>
              </div>

              <div class="mt-4 pt-2.5 border-t border-edge flex items-center justify-between text-[11px] text-lo">
                <span>{{ st.total_experiments }} exps generated</span>
                <span class="text-mid flex items-center gap-1">
                  {{ formatRelativeTime(st.last_active) }}
                  <ChevronRight class="w-3 h-3 text-lo group-hover:text-amber group-hover:translate-x-0.5 transition" />
                </span>
              </div>
            </div>
          </div>
          <div v-else class="p-12 text-center border border-edge rounded-2xl bg-card">
            <Users class="w-8 h-8 text-lo mx-auto mb-2" />
            <p class="text-xs text-mid">No student records match the active query or filter.</p>
          </div>

          <!-- Pagination Bar -->
          <div v-if="totalStudents > studentLimit" class="flex items-center justify-between text-xs text-mid py-2">
            <span>
              Showing {{ (studentPage - 1) * studentLimit + 1 }}–{{ Math.min(studentPage * studentLimit, totalStudents) }} of {{ totalStudents }} students
            </span>
            <div class="flex items-center gap-2">
              <button
                :disabled="studentPage <= 1"
                @click="studentPage--; loadStudentsData()"
                class="px-3 py-1 rounded bg-input border border-edge text-hi disabled:opacity-30 disabled:cursor-not-allowed hover:border-edge-hi transition"
              >
                Previous
              </button>
              <button
                :disabled="studentPage * studentLimit >= totalStudents"
                @click="studentPage++; loadStudentsData()"
                class="px-3 py-1 rounded bg-input border border-edge text-hi disabled:opacity-30 disabled:cursor-not-allowed hover:border-edge-hi transition"
              >
                Next
              </button>
            </div>
          </div>
        </div>

        <!-- ── TAB 3: LIVE COMPILATIONS EXPLORER ──────────────────────────── -->
        <div v-else-if="activeTab === 'events'" class="space-y-4">
          <!-- Search & Filter Bar -->
          <div class="p-4 rounded-2xl border border-edge bg-card shadow-sm flex flex-col sm:flex-row gap-3 items-stretch sm:items-center justify-between">
            <div class="relative flex-1 min-w-0">
              <Search class="w-4 h-4 text-lo absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
              <input
                v-model="eventQuery"
                @input="loadEventsData"
                type="text"
                placeholder="Search compilations by student name, roll number, or class..."
                class="w-full h-9 pl-9 pr-3 rounded-lg bg-input border border-edge text-hi placeholder:text-lo text-xs focus:outline-none focus:border-amber transition"
              />
            </div>
            <button
              @click="loadEventsData"
              class="h-9 px-3 rounded-lg bg-input border border-edge text-mid hover:text-hi transition flex items-center justify-center gap-1 text-xs"
            >
              <RefreshCw class="w-3.5 h-3.5" />
              <span>Refresh</span>
            </button>
          </div>

          <!-- Compilations Table -->
          <div class="border border-edge rounded-2xl bg-card overflow-hidden shadow-sm">
            <div class="overflow-x-auto">
              <table class="w-full text-left text-xs">
                <thead class="bg-input/50 text-lo uppercase text-[10px] tracking-wider border-b border-edge">
                  <tr>
                    <th class="py-3 px-4">Timestamp</th>
                    <th class="py-3 px-4">Student</th>
                    <th class="py-3 px-4">Class & Batch</th>
                    <th class="py-3 px-4">Subject</th>
                    <th class="py-3 px-4 text-center">Exps</th>
                    <th class="py-3 px-4 text-center">Duration</th>
                    <th class="py-3 px-4 text-center">Status</th>
                    <th class="py-3 px-4 text-right">Details</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-edge">
                  <tr
                    v-for="ev in events"
                    :key="ev.id"
                    @click="selectedEventForDetail = ev"
                    class="hover:bg-input/40 transition cursor-pointer"
                  >
                    <td class="py-3 px-4 font-mono text-mid text-[11px] whitespace-nowrap">
                      {{ formatDate(ev.timestamp) }}
                    </td>
                    <td class="py-3 px-4">
                      <div class="font-medium text-hi truncate max-w-[150px]">{{ ev.student_name }}</div>
                      <div class="text-[10px] text-lo font-mono">Roll #{{ ev.roll_no }}</div>
                    </td>
                    <td class="py-3 px-4 text-mid whitespace-nowrap">
                      {{ ev.class_name }} <span v-if="ev.batch !== '—'">({{ ev.batch }})</span>
                    </td>
                    <td class="py-3 px-4 text-hi font-medium truncate max-w-[180px]">
                      {{ ev.subject }}
                    </td>
                    <td class="py-3 px-4 text-center font-mono text-mid">
                      {{ ev.experiment_count }}
                    </td>
                    <td class="py-3 px-4 text-center font-mono text-lo text-[11px]">
                      {{ ev.duration_ms }}ms
                    </td>
                    <td class="py-3 px-4 text-center">
                      <span
                        class="text-[10px] font-semibold px-2 py-0.5 rounded-full"
                        :class="ev.success ? 'bg-success/10 text-success border border-success/30' : 'bg-danger/10 text-danger border border-danger/30'"
                      >
                        {{ ev.success ? 'SUCCESS' : 'FAILED' }}
                      </span>
                    </td>
                    <td class="py-3 px-4 text-right">
                      <button class="text-mid hover:text-amber transition text-[11px]">
                        Inspect &rarr;
                      </button>
                    </td>
                  </tr>
                  <tr v-if="!events.length">
                    <td colspan="8" class="py-8 text-center text-lo">
                      No compilation records found.
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <!-- Pagination -->
          <div v-if="totalEvents > eventLimit" class="flex items-center justify-between text-xs text-mid py-2">
            <span>
              Showing {{ (eventPage - 1) * eventLimit + 1 }}–{{ Math.min(eventPage * eventLimit, totalEvents) }} of {{ totalEvents }} compilations
            </span>
            <div class="flex items-center gap-2">
              <button
                :disabled="eventPage <= 1"
                @click="eventPage--; loadEventsData()"
                class="px-3 py-1 rounded bg-input border border-edge text-hi disabled:opacity-30 disabled:cursor-not-allowed hover:border-edge-hi transition"
              >
                Previous
              </button>
              <button
                :disabled="eventPage * eventLimit >= totalEvents"
                @click="eventPage++; loadEventsData()"
                class="px-3 py-1 rounded bg-input border border-edge text-hi disabled:opacity-30 disabled:cursor-not-allowed hover:border-edge-hi transition"
              >
                Next
              </button>
            </div>
          </div>
        </div>

        <!-- ── TAB 4: FAILED AIM EXTRACTIONS WORKBENCH ───────────────────── -->
        <div v-else-if="activeTab === 'failedAims'" class="space-y-4">
          <!-- Summary Diagnostics KPI Ribbon -->
          <div v-if="diagnosticsSummary" class="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div class="p-3.5 rounded-xl border border-edge bg-card">
              <span class="text-mid text-[11px]">Processed Uploads</span>
              <div class="text-xl font-bold text-hi">{{ diagnosticsSummary.total_documents }}</div>
            </div>
            <div class="p-3.5 rounded-xl border border-edge bg-card">
              <span class="text-mid text-[11px]">Extraction Accuracy</span>
              <div class="text-xl font-bold text-success">{{ diagnosticsSummary.success_rate_percent }}%</div>
            </div>
            <div class="p-3.5 rounded-xl border border-edge bg-card">
              <span class="text-mid text-[11px]">Heuristic Failures</span>
              <div class="text-xl font-bold text-danger">
                {{ (Object.values(diagnosticsSummary.failures) as number[]).reduce((a: number, b: number) => a + b, 0) }}
              </div>
            </div>
            <div class="p-3.5 rounded-xl border border-edge bg-card">
              <span class="text-mid text-[11px]">Student Ground-Truth Corrections</span>
              <div class="text-xl font-bold text-amber">{{ diagnosticsSummary.discrepancies_count }}</div>
            </div>
          </div>

          <!-- Search & Filter Ribbon -->
          <div class="p-4 rounded-2xl border border-edge bg-card shadow-sm flex flex-col md:flex-row gap-3 items-stretch md:items-center justify-between">
            <div class="flex flex-col sm:flex-row gap-2.5 flex-1 min-w-0">
              <div class="relative flex-1 min-w-0">
                <Search class="w-4 h-4 text-lo absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
                <input
                  v-model="failedQuery"
                  @input="loadFailedAimsData"
                  type="text"
                  placeholder="Search failed documents by filename or aim..."
                  class="w-full h-9 pl-9 pr-3 rounded-lg bg-input border border-edge text-hi placeholder:text-lo text-xs focus:outline-none focus:border-amber transition"
                />
              </div>

              <!-- Filter by Reason -->
              <select
                v-model="failedReasonFilter"
                @change="loadFailedAimsData"
                class="h-9 px-3 rounded-lg bg-input border border-edge text-hi text-xs focus:outline-none focus:border-amber transition"
              >
                <option value="">All Failure Reasons</option>
                <option value="scanned_no_text">Scanned PDF (No Text)</option>
                <option value="no_aim_found">No Aim Keyword Found</option>
                <option value="no_pattern_match">No Pattern Match</option>
                <option value="empty_pdf">Empty Document</option>
              </select>

              <!-- Discrepancy Only Checkbox -->
              <label class="flex items-center gap-2 px-3 rounded-lg bg-input border border-edge text-mid text-xs cursor-pointer select-none">
                <input
                  v-model="discrepancyOnly"
                  @change="loadFailedAimsData"
                  type="checkbox"
                  class="rounded bg-card border-edge text-amber focus:ring-amber focus:ring-offset-0"
                />
                <span>Corrections Only</span>
              </label>
            </div>
          </div>

          <!-- Failed Documents Cards List -->
          <div v-if="failedDocs.length" class="space-y-3">
            <div
              v-for="doc in failedDocs"
              :key="doc.sha256"
              class="p-4 rounded-xl border border-edge bg-card shadow-sm space-y-3"
            >
              <!-- Card Top Header -->
              <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div class="flex items-center gap-2.5 min-w-0">
                  <div class="w-8 h-8 rounded-lg bg-danger/10 border border-danger/30 text-danger flex items-center justify-center shrink-0">
                    <AlertTriangle class="w-4 h-4" />
                  </div>
                  <div class="min-w-0">
                    <div class="font-semibold text-xs text-hi truncate" :title="doc.filename">
                      {{ doc.filename }}
                    </div>
                    <div class="text-[10px] text-lo font-mono">
                      {{ formatBytes(doc.file_size) }} &bull; {{ doc.pages }} page(s) &bull; {{ formatDate(doc.uploaded_at) }}
                    </div>
                  </div>
                </div>

                <div class="flex items-center gap-2 shrink-0">
                  <!-- Failure badge -->
                  <span
                    v-if="doc.failure_reason && doc.failure_reason !== 'none'"
                    class="text-[10px] font-semibold px-2 py-0.5 rounded bg-danger/15 text-danger border border-danger/30"
                  >
                    {{ doc.failure_reason }}
                  </span>

                  <!-- Method badge -->
                  <span class="text-[10px] font-mono px-2 py-0.5 rounded bg-input border border-edge text-mid">
                    method: {{ doc.extraction_method }}
                  </span>

                  <!-- Download Sample PDF button -->
                  <a
                    :href="getSampleDownloadUrl(doc.sha256)"
                    target="_blank"
                    class="flex items-center gap-1 px-2.5 py-1 rounded bg-amber hover:bg-amber-hi text-surface text-xs font-semibold transition"
                    title="Download raw uploaded PDF to write local parser test"
                  >
                    <Download class="w-3 h-3" />
                    <span>Download PDF</span>
                  </a>
                </div>
              </div>

              <!-- Side-by-Side Ground Truth Comparison -->
              <div class="grid grid-cols-1 md:grid-cols-2 gap-3 p-3 rounded-lg bg-input/70 border border-edge text-xs">
                <!-- Parser Extracted Aim -->
                <div>
                  <div class="text-[10px] font-semibold uppercase tracking-wider text-lo mb-1 flex items-center gap-1">
                    <XCircle class="w-3.5 h-3.5 text-danger" />
                    <span>Parser Extracted Aim</span>
                  </div>
                  <div class="text-mid italic" :class="{ 'text-danger font-medium': !doc.extracted_aim }">
                    {{ doc.extracted_aim ? `"${doc.extracted_aim}"` : 'Failed (No aim extracted)' }}
                  </div>
                </div>

                <!-- Student Submitted Ground Truth -->
                <div>
                  <div class="text-[10px] font-semibold uppercase tracking-wider text-lo mb-1 flex items-center gap-1">
                    <CheckCircle2 class="w-3.5 h-3.5 text-success" />
                    <span>Student-Submitted Title (Ground Truth)</span>
                  </div>
                  <div class="text-hi font-medium">
                    {{ doc.student_submitted_title ? `"${doc.student_submitted_title}"` : '—' }}
                  </div>
                </div>
              </div>

              <!-- Raw Page 1 Text Snippet Toggle -->
              <div v-if="doc.text_snippet">
                <button
                  @click="toggleSnippet(doc.sha256)"
                  class="text-[11px] text-mid hover:text-amber flex items-center gap-1 transition"
                >
                  <ChevronRight
                    class="w-3 h-3 transition-transform"
                    :class="{ 'rotate-90': expandedSnippetHash === doc.sha256 }"
                  />
                  <span>{{ expandedSnippetHash === doc.sha256 ? 'Hide' : 'Inspect' }} Raw Page 1 Snippet</span>
                </button>

                <div
                  v-if="expandedSnippetHash === doc.sha256"
                  class="mt-2 p-3 rounded-lg bg-surface border border-edge font-mono text-[11px] text-mid whitespace-pre-wrap leading-relaxed max-h-48 overflow-y-auto"
                >
                  {{ doc.text_snippet }}
                </div>
              </div>
            </div>
          </div>
          <div v-else class="p-12 text-center border border-edge rounded-2xl bg-card">
            <CheckCircle2 class="w-8 h-8 text-success mx-auto mb-2" />
            <p class="text-xs text-mid">No failed aim documents match the current filter.</p>
          </div>

          <!-- Pagination -->
          <div v-if="totalFailedDocs > failedLimit" class="flex items-center justify-between text-xs text-mid py-2">
            <span>
              Showing {{ (failedPage - 1) * failedLimit + 1 }}–{{ Math.min(failedPage * failedLimit, totalFailedDocs) }} of {{ totalFailedDocs }} documents
            </span>
            <div class="flex items-center gap-2">
              <button
                :disabled="failedPage <= 1"
                @click="failedPage--; loadFailedAimsData()"
                class="px-3 py-1 rounded bg-input border border-edge text-hi disabled:opacity-30 disabled:cursor-not-allowed hover:border-edge-hi transition"
              >
                Previous
              </button>
              <button
                :disabled="failedPage * failedLimit >= totalFailedDocs"
                @click="failedPage++; loadFailedAimsData()"
                class="px-3 py-1 rounded bg-input border border-edge text-hi disabled:opacity-30 disabled:cursor-not-allowed hover:border-edge-hi transition"
              >
                Next
              </button>
            </div>
          </div>
        </div>
      </main>

      <!-- ── STUDENT DOSSIER SLIDE-OVER MODAL ────────────────────────────── -->
      <div
        v-if="selectedStudentDossier || isLoadingDossier"
        class="fixed inset-0 bg-surface/80 backdrop-blur-sm z-50 flex justify-end transition-opacity"
        @click.self="closeStudentDossier"
      >
        <div class="w-full max-w-xl h-full bg-card border-l border-edge shadow-2xl flex flex-col overflow-hidden animate-in slide-in-from-right duration-200">
          <!-- Drawer Header -->
          <div class="p-5 border-b border-edge flex items-center justify-between bg-surface/50">
            <div class="flex items-center gap-3 min-w-0">
              <div class="w-10 h-10 rounded-xl bg-amber flex items-center justify-center text-surface font-bold text-sm shrink-0">
                {{ selectedStudentDossier ? getInitials(selectedStudentDossier.student_name) : '...' }}
              </div>
              <div class="min-w-0">
                <h2 class="text-sm font-semibold text-hi truncate">
                  {{ selectedStudentDossier?.student_name || 'Loading dossier...' }}
                </h2>
                <div class="text-xs text-mid flex items-center gap-1.5 font-mono">
                  <span>Roll #{{ selectedStudentDossier?.roll_no || '—' }}</span>
                  <span>&bull;</span>
                  <span>{{ selectedStudentDossier?.class_name }}</span>
                  <span v-if="selectedStudentDossier?.batch !== '—'">({{ selectedStudentDossier?.batch }})</span>
                </div>
              </div>
            </div>

            <button
              @click="closeStudentDossier"
              class="p-1.5 rounded-lg bg-input border border-edge text-mid hover:text-hi hover:border-edge-hi transition"
            >
              <X class="w-4 h-4" />
            </button>
          </div>

          <!-- Drawer Body Content -->
          <div v-if="selectedStudentDossier" class="flex-1 overflow-y-auto p-5 space-y-6">
            <!-- Student KPI Summary Bar -->
            <div class="grid grid-cols-3 gap-2.5">
              <div class="p-3 rounded-lg bg-input border border-edge text-center">
                <span class="text-[10px] text-lo uppercase">Compilations</span>
                <div class="text-base font-bold text-hi">{{ selectedStudentDossier.total_compilations }}</div>
              </div>
              <div class="p-3 rounded-lg bg-input border border-edge text-center">
                <span class="text-[10px] text-lo uppercase">Experiments</span>
                <div class="text-base font-bold text-hi">{{ selectedStudentDossier.total_experiments }}</div>
              </div>
              <div class="p-3 rounded-lg bg-input border border-edge text-center">
                <span class="text-[10px] text-lo uppercase">Avg Time</span>
                <div class="text-base font-bold text-amber">{{ selectedStudentDossier.avg_duration_ms }}ms</div>
              </div>
            </div>

            <!-- Enrolled Subjects -->
            <div>
              <h3 class="text-xs font-semibold uppercase tracking-wider text-mid mb-2">
                Courses / Subjects Compiled
              </h3>
              <div class="flex flex-wrap gap-1.5">
                <span
                  v-for="sub in selectedStudentDossier.subjects"
                  :key="sub"
                  class="px-2.5 py-1 rounded-lg bg-input border border-edge text-xs text-hi"
                >
                  {{ sub }}
                </span>
              </div>
            </div>

            <!-- Historical Compilation Timeline -->
            <div>
              <h3 class="text-xs font-semibold uppercase tracking-wider text-mid mb-3">
                Compilation Timeline History
              </h3>
              <div class="space-y-3">
                <div
                  v-for="job in selectedStudentDossier.timeline"
                  :key="job.id"
                  class="p-3.5 rounded-xl border border-edge bg-input/40 space-y-2.5"
                >
                  <div class="flex items-center justify-between">
                    <div class="font-medium text-xs text-hi">{{ job.subject }}</div>
                    <span
                      class="text-[10px] font-semibold px-2 py-0.5 rounded-full"
                      :class="job.success ? 'bg-success/10 text-success border border-success/30' : 'bg-danger/10 text-danger border border-danger/30'"
                    >
                      {{ job.success ? 'SUCCESS' : 'FAILED' }}
                    </span>
                  </div>

                  <div class="text-[11px] text-lo flex items-center gap-2">
                    <span class="font-mono">{{ formatDate(job.timestamp) }}</span>
                    <span>&bull;</span>
                    <span>{{ job.experiment_count }} experiments</span>
                    <span>&bull;</span>
                    <span class="font-mono">{{ job.duration_ms }}ms</span>
                  </div>

                  <!-- Experiments List in this job -->
                  <div v-if="job.experiments?.length" class="space-y-1 pt-1">
                    <div
                      v-for="(item, idx) in job.experiments"
                      :key="idx"
                      class="p-2 rounded bg-surface border border-edge text-[11px] flex items-center justify-between"
                    >
                      <div class="truncate flex-1 pr-2">
                        <span class="text-amber font-mono">{{ item.is_assignment ? 'Assign' : 'Exp' }} {{ item.label || idx + 1 }}:</span>
                        <span class="text-hi ml-1.5">{{ item.title || 'Untitled' }}</span>
                      </div>
                      <span v-if="item.pages" class="text-lo font-mono text-[10px] shrink-0">
                        {{ item.pages }}p
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
          <div v-else class="flex-1 flex items-center justify-center text-xs text-lo">
            Loading student timeline...
          </div>
        </div>
      </div>

      <!-- ── COMPILATION EVENT INSPECTOR MODAL ───────────────────────────── -->
      <div
        v-if="selectedEventForDetail"
        class="fixed inset-0 bg-surface/80 backdrop-blur-sm z-50 flex items-center justify-center p-4"
        @click.self="selectedEventForDetail = null"
      >
        <div class="max-w-lg w-full max-h-[85vh] bg-card border border-edge rounded-2xl shadow-2xl flex flex-col overflow-hidden">
          <div class="p-4 border-b border-edge flex items-center justify-between bg-surface/50">
            <div>
              <h2 class="text-sm font-semibold text-hi">Compilation Job #{{ selectedEventForDetail.id }}</h2>
              <p class="text-[11px] text-lo font-mono">{{ formatDate(selectedEventForDetail.timestamp) }}</p>
            </div>
            <button @click="selectedEventForDetail = null" class="p-1 rounded bg-input text-mid hover:text-hi">
              <X class="w-4 h-4" />
            </button>
          </div>

          <div class="p-4 overflow-y-auto space-y-4 text-xs">
            <div class="grid grid-cols-2 gap-2 p-3 rounded-lg bg-input border border-edge">
              <div>
                <span class="text-[10px] text-lo uppercase">Student</span>
                <div class="font-semibold text-hi">{{ selectedEventForDetail.student_name }}</div>
                <div class="text-lo font-mono text-[11px]">Roll #{{ selectedEventForDetail.roll_no }}</div>
              </div>
              <div>
                <span class="text-[10px] text-lo uppercase">Academic Cohort</span>
                <div class="font-medium text-hi">{{ selectedEventForDetail.class_name }}</div>
                <div class="text-lo text-[11px]">Batch {{ selectedEventForDetail.batch }} &bull; Sem {{ selectedEventForDetail.sem }}</div>
              </div>
            </div>

            <div>
              <span class="text-[10px] text-lo uppercase font-semibold">Subject</span>
              <div class="text-sm font-semibold text-amber">{{ selectedEventForDetail.subject }}</div>
            </div>

            <div v-if="selectedEventForDetail.experiments?.length" class="space-y-1.5">
              <span class="text-[10px] text-lo uppercase font-semibold">
                Processed Experiments ({{ selectedEventForDetail.experiments.length }})
              </span>
              <div
                v-for="(exp, idx) in selectedEventForDetail.experiments"
                :key="idx"
                class="p-2.5 rounded-lg bg-input border border-edge text-[11px] flex items-center justify-between"
              >
                <div class="truncate flex-1 pr-2">
                  <span class="text-amber font-mono">{{ exp.is_assignment ? 'Assign' : 'Exp' }} {{ exp.label || idx + 1 }}:</span>
                  <span class="text-hi ml-1.5">{{ exp.title || 'Untitled' }}</span>
                </div>
                <div class="flex items-center gap-2 text-lo text-[10px] shrink-0 font-mono">
                  <span v-if="exp.perf_date">{{ exp.perf_date }}</span>
                  <span v-if="exp.pages">{{ exp.pages }}p</span>
                </div>
              </div>
            </div>

            <div v-if="selectedEventForDetail.error_message" class="p-3 rounded-lg bg-danger/10 border border-danger/30 text-danger text-xs font-mono">
              {{ selectedEventForDetail.error_message }}
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

