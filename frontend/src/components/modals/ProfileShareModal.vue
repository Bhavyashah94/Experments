<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import {
  isShareOpen,
  shareModalInitialTab,
  shareModalExportType,
  student,
  subjects,
  activeSubject,
  experiments,
  exportSubjectListPackage,
  exportExperimentsOnlyPackage,
  importUniversalPackage,
  showToast,
} from '../../store/labStore'
import {
  Share2,
  Upload,
  X,
  Copy,
  Check,
  Download,
  FileJson,
  BookOpen,
  Layers,
  FileText,
  AlertCircle,
  Sparkles,
} from '@lucide/vue'

const activeTab = ref<'export' | 'import'>('export')
const exportType = ref<'subject_list' | 'experiments_only'>('subject_list')
const copied = ref(false)
const importInput = ref('')
const importError = ref<string | null>(null)

watch(isShareOpen, (isOpen) => {
  if (isOpen) {
    activeTab.value = shareModalInitialTab.value || 'export'
    exportType.value = (shareModalExportType.value as any) === 'experiments_only' ? 'experiments_only' : 'subject_list'
    importError.value = null
    importInput.value = ''
    copied.value = false
  }
})

const jsonContent = computed(() => {
  if (!isShareOpen.value) return ''
  if (exportType.value === 'subject_list') {
    return exportSubjectListPackage()
  } else {
    return exportExperimentsOnlyPackage()
  }
})

function close() {
  isShareOpen.value = false
  importError.value = null
  importInput.value = ''
  copied.value = false
}

async function handleCopy() {
  try {
    await navigator.clipboard.writeText(jsonContent.value)
    copied.value = true
    setTimeout(() => {
      copied.value = false
    }, 2500)
    const label =
      exportType.value === 'subject_list'
        ? 'subject list'
        : 'experiments manifest'
    showToast(`Copied ${label} JSON to clipboard`)
  } catch (err) {
    showToast('Failed to copy to clipboard')
  }
}

function handleDownloadJson() {
  const blob = new Blob([jsonContent.value], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')

  let filename = 'labstudio_data.json'
  if (exportType.value === 'subject_list') {
    filename = `labstudio_subjects_list_${subjects.value.length}_courses.json`
  } else {
    filename = `labstudio_experiments_manifest_${experiments.value.length}_items.json`
  }

  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
  showToast(`Downloaded ${filename}`)
}

function handleFileUpload(e: Event) {
  const input = e.target as HTMLInputElement
  if (!input.files || input.files.length === 0) return
  const file = input.files[0]
  const reader = new FileReader()
  reader.onload = (evt) => {
    const text = evt.target?.result as string
    if (text) {
      importInput.value = text
    }
  }
  reader.readAsText(file)
}

interface DetectResult {
  type: 'experiments_only' | 'subject_list' | 'single_subject' | 'invalid' | 'unknown'
  title: string
  count: number
  description: string
  targetSubject?: string
}

const detectedPackage = computed<DetectResult | null>(() => {
  const raw = importInput.value.trim()
  if (!raw) return null
  try {
    const p = JSON.parse(raw)
    // 1. Experiments only
    if (
      p.type === 'experiments_share' ||
      (Array.isArray(p.experiments) && !p.subject && !p.subjects && !p.profile?.subject)
    ) {
      const count = Array.isArray(p.experiments) ? p.experiments.length : 0
      return {
        type: 'experiments_only',
        title: 'Experiment / Assignment Info (No Subject Details)',
        count,
        description: `Contains ${count} experiment item(s) with aims and dates. Does not contain any subject metadata.`,
        targetSubject: student.subject || activeSubject.value?.name || 'Current Subject',
      }
    }

    // 2. Subject list (Pure subject list without experiments)
    if (p.type === 'subject_list_share' || (Array.isArray(p.subjects) && !p.experiments)) {
      const subs = Array.isArray(p.subjects) ? p.subjects : []
      const names = subs
        .map((s: any) => (typeof s === 'string' ? s : String(s.name || s.subject || 'Subject')).trim())
        .filter(Boolean)
      return {
        type: 'subject_list',
        title: 'Subject List Share',
        count: names.length,
        description: `Contains ${names.length} subject name(s): ${names.slice(0, 4).join(', ')}${names.length > 4 ? ` +${names.length - 4} more` : ''}. No experiment contents attached.`,
      }
    }

    // 3. Single subject
    if (p.type === 'subject_share' || p.subject || p.profile?.subject) {
      const sName = p.subject || p.profile?.subject || 'Subject'
      const count = Array.isArray(p.experiments) ? p.experiments.length : 0
      return {
        type: 'single_subject',
        title: `Single Subject: "${sName}"`,
        count,
        description: `Contains full course syllabus for "${sName}" with ${count} experiment(s).`,
      }
    }

    return {
      type: 'unknown',
      title: 'Unrecognized Schema',
      count: 0,
      description: 'The JSON structure does not match a standard LabStudio share package.',
    }
  } catch (err: any) {
    return {
      type: 'invalid',
      title: 'Invalid JSON',
      count: 0,
      description: err.message || 'Syntax error in JSON string.',
    }
  }
})

function executeImport(mode: 'replace' | 'append' = 'replace') {
  importError.value = null
  if (!importInput.value.trim()) {
    importError.value = 'Please paste JSON or upload a file.'
    return
  }

  const res = importUniversalPackage(importInput.value.trim(), { mode })
  if (res.success) {
    close()
  } else {
    importError.value = res.error || 'Failed to import data.'
  }
}
</script>

<template>
  <div
    v-if="isShareOpen"
    class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-surface/85 backdrop-blur-sm select-none"
    @click.self="close"
  >
    <div class="bg-card border border-edge rounded-2xl w-full max-w-xl shadow-2xl overflow-hidden flex flex-col max-h-[92vh]">
      <!-- Header -->
      <div class="flex items-center justify-between px-5 py-4 border-b border-edge">
        <div class="flex items-center gap-2.5">
          <div class="w-8 h-8 rounded-lg bg-input border border-edge flex items-center justify-center text-amber">
            <BookOpen class="w-4 h-4" />
          </div>
          <div>
            <h2 class="text-xs sm:text-sm font-bold text-hi tracking-tight">
              Share &amp; Import Syllabus Data
            </h2>
            <p class="text-[11px] text-mid">
              Exchange subject lists or portable experiment manifests with classmates
            </p>
          </div>
        </div>

        <button
          type="button"
          @click="close"
          class="text-mid hover:text-hi p-1 rounded-lg hover:bg-input transition cursor-pointer"
        >
          <X class="w-4 h-4" />
        </button>
      </div>

      <!-- Tab Navigation -->
      <div class="flex border-b border-edge bg-surface px-5 pt-2 gap-4 text-xs font-semibold">
        <button
          type="button"
          @click="activeTab = 'export'"
          class="pb-2.5 border-b-2 transition flex items-center gap-1.5 cursor-pointer"
          :class="activeTab === 'export' ? 'border-amber text-amber font-semibold' : 'border-transparent text-mid hover:text-hi'"
        >
          <Share2 class="w-3.5 h-3.5" />
          <span>Export / Share</span>
        </button>

        <button
          type="button"
          @click="activeTab = 'import'"
          class="pb-2.5 border-b-2 transition flex items-center gap-1.5 cursor-pointer"
          :class="activeTab === 'import' ? 'border-amber text-amber font-semibold' : 'border-transparent text-mid hover:text-hi'"
        >
          <Upload class="w-3.5 h-3.5" />
          <span>Import Data</span>
        </button>
      </div>

      <!-- Modal Body -->
      <div class="p-5 overflow-y-auto flex-1 space-y-4 text-xs">
        <!-- ════════════════════════ EXPORT TAB ════════════════════════ -->
        <div v-if="activeTab === 'export'" class="space-y-4">
          <!-- Share Type Selector -->
          <div class="space-y-1.5">
            <label class="block text-[11px] font-medium text-mid uppercase tracking-wider">Select What to Share:</label>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
              <!-- Option 1: Subject List Share -->
              <button
                type="button"
                @click="exportType = 'subject_list'"
                class="p-3 rounded-xl border text-left transition cursor-pointer flex flex-col justify-between gap-1.5"
                :class="
                  exportType === 'subject_list'
                    ? 'border-amber bg-amber/10 text-hi ring-1 ring-amber/50'
                    : 'border-edge bg-input text-mid hover:text-hi hover:border-edge-hi'
                "
              >
                <div class="flex items-center justify-between w-full">
                  <div class="flex items-center gap-1.5 font-semibold text-xs text-hi">
                    <Layers class="w-3.5 h-3.5 text-amber" />
                    <span>Subject List Share</span>
                  </div>
                  <span class="text-[10px] bg-card border border-edge px-1.5 py-0.5 rounded text-mid">
                    {{ subjects.length }} subject{{ subjects.length === 1 ? '' : 's' }}
                  </span>
                </div>
                <p class="text-[11px] text-mid leading-relaxed">
                  Shares only the names of all subjects in your studio. No experiments, dates, or files included.
                </p>
              </button>

              <!-- Option 2: Exp / Assignment Info Share (No Subject Details) -->
              <button
                type="button"
                @click="exportType = 'experiments_only'"
                class="p-3 rounded-xl border text-left transition cursor-pointer flex flex-col justify-between gap-1.5"
                :class="
                  exportType === 'experiments_only'
                    ? 'border-amber bg-amber/10 text-hi ring-1 ring-amber/50'
                    : 'border-edge bg-input text-mid hover:text-hi hover:border-edge-hi'
                "
              >
                <div class="flex items-center justify-between w-full">
                  <div class="flex items-center gap-1.5 font-semibold text-xs text-hi">
                    <FileText class="w-3.5 h-3.5 text-amber" />
                    <span>Exp / Assignment Info</span>
                  </div>
                  <span class="text-[10px] bg-amber/10 text-amber font-medium border border-amber/30 px-1.5 py-0.5 rounded">
                    No Subject Details
                  </span>
                </div>
                <p class="text-[11px] text-mid leading-relaxed">
                  Portable manifest of experiment aims &amp; dates. Can be imported into any custom subject.
                </p>
              </button>
            </div>
          </div>

          <!-- Privacy & Scope Banner -->
          <div class="bg-input border border-edge rounded-xl p-3 text-hi space-y-1">
            <div class="flex items-center gap-1.5 text-xs font-semibold text-hi">
              <Sparkles class="w-3.5 h-3.5 text-amber" />
              <span v-if="exportType === 'subject_list'">Sharing Subject Names Only ({{ subjects.length }} subjects)</span>
              <span v-else>Sharing Experiment Info (No Subject Details)</span>
            </div>
            <p class="text-[11px] text-mid leading-relaxed">
              <template v-if="exportType === 'subject_list'">
                Contains only the list of course/subject names. Zero experiments, aims, dates, files, or student details are included.
              </template>
              <template v-else>
                Contains only experiment numbers, aims, and dates for "{{ student.subject }}". <b>No student name, roll number, or subject title</b> are attached.
              </template>
            </p>
          </div>

          <!-- JSON Content Preview -->
          <div class="space-y-1.5">
            <div class="flex items-center justify-between text-[11px] text-mid">
              <span>Payload Preview</span>
              <span v-if="exportType === 'subject_list'">{{ subjects.length }} subject name(s)</span>
              <span v-else>{{ experiments.length }} experiment(s)</span>
            </div>
            <textarea
              readonly
              :value="jsonContent"
              rows="6"
              class="w-full bg-input border border-edge rounded-xl p-3 text-[11px] font-mono text-hi select-all outline-none resize-none"
            ></textarea>
          </div>

          <!-- Export Actions -->
          <div class="flex items-center justify-end gap-2.5 pt-2">
            <button
              type="button"
              @click="handleCopy"
              class="inline-flex items-center gap-1.5 bg-input hover:bg-edge border border-edge hover:border-edge-hi text-hi font-medium px-3.5 py-2 rounded-xl transition cursor-pointer"
            >
              <Check v-if="copied" class="w-3.5 h-3.5 text-success" />
              <Copy v-else class="w-3.5 h-3.5" />
              <span>{{ copied ? 'Copied to Clipboard!' : 'Copy JSON' }}</span>
            </button>

            <button
              type="button"
              @click="handleDownloadJson"
              class="inline-flex items-center gap-1.5 bg-amber hover:bg-amber-hi text-surface font-semibold px-4 py-2 rounded-xl transition shadow-sm cursor-pointer"
            >
              <Download class="w-3.5 h-3.5" />
              <span>Download .json File</span>
            </button>
          </div>
        </div>

        <!-- ════════════════════════ IMPORT TAB ════════════════════════ -->
        <div v-else class="space-y-4">
          <div class="bg-input border border-edge rounded-xl p-3 text-hi space-y-1">
            <p class="font-semibold text-hi">Import Shared Subject or Experiment Data</p>
            <p class="text-[11px] text-mid">
              Paste JSON or upload a <code class="text-amber bg-surface border border-edge px-1 rounded">.json</code> file.
              The importer automatically detects whether it is a <b>Subject List</b> or <b>Experiment Info</b> share.
            </p>
          </div>

          <!-- File Upload Dropzone -->
          <label class="block border border-dashed border-edge hover:border-edge-hi bg-input hover:bg-card rounded-xl p-3.5 text-center cursor-pointer transition">
            <input type="file" accept=".json,application/json" class="hidden" @change="handleFileUpload" />
            <FileJson class="w-5 h-5 mx-auto text-lo mb-1" />
            <p class="text-xs font-semibold text-hi">Upload .json file</p>
            <p class="text-[10px] text-mid">or paste the JSON text directly below</p>
          </label>

          <!-- Textarea Input -->
          <div class="space-y-1.5">
            <div class="flex items-center justify-between text-[11px] text-mid">
              <span class="font-medium uppercase tracking-wider">JSON Payload</span>
              <button
                v-if="importInput"
                type="button"
                @click="importInput = ''"
                class="text-lo hover:text-hi transition cursor-pointer"
              >
                Clear
              </button>
            </div>
            <textarea
              v-model="importInput"
              placeholder="Paste shared Subject List or Experiments JSON here..."
              rows="5"
              class="w-full bg-input border border-edge rounded-xl p-3 text-xs font-mono text-hi outline-none focus:border-amber resize-none"
            ></textarea>
          </div>

          <!-- Detection Callout Banner -->
          <div
            v-if="detectedPackage && detectedPackage.type !== 'invalid' && detectedPackage.type !== 'unknown'"
            class="p-3.5 rounded-xl border bg-surface space-y-2.5 transition"
            :class="
              detectedPackage.type === 'experiments_only'
                ? 'border-amber/40 ring-1 ring-amber/20'
                : 'border-edge'
            "
          >
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-1.5 font-semibold text-xs text-hi">
                <FileText v-if="detectedPackage.type === 'experiments_only'" class="w-4 h-4 text-amber" />
                <Layers v-else-if="detectedPackage.type === 'subject_list'" class="w-4 h-4 text-amber" />
                <BookOpen v-else class="w-4 h-4 text-amber" />
                <span>{{ detectedPackage.title }}</span>
              </div>
              <span
                class="text-[10px] px-2 py-0.5 rounded font-medium"
                :class="
                  detectedPackage.type === 'experiments_only'
                    ? 'bg-amber/15 text-amber'
                    : 'bg-input text-mid'
                "
              >
                {{ detectedPackage.count }} item{{ detectedPackage.count === 1 ? '' : 's' }}
              </span>
            </div>

            <p class="text-[11px] text-mid leading-relaxed">
              {{ detectedPackage.description }}
            </p>

            <!-- Action buttons tailored to payload type -->
            <div v-if="detectedPackage.type === 'experiments_only'" class="flex flex-wrap items-center gap-2 pt-1">
              <button
                type="button"
                @click="executeImport('replace')"
                class="inline-flex items-center gap-1.5 bg-amber hover:bg-amber-hi text-surface font-semibold px-3.5 py-1.5 rounded-lg text-xs transition cursor-pointer shadow-sm"
              >
                <Upload class="w-3.5 h-3.5" />
                <span>Replace Experiments in "{{ detectedPackage.targetSubject }}"</span>
              </button>

              <button
                type="button"
                @click="executeImport('append')"
                class="inline-flex items-center gap-1.5 bg-input hover:bg-edge border border-edge text-hi font-medium px-3.5 py-1.5 rounded-lg text-xs transition cursor-pointer"
              >
                <span>Append (+{{ detectedPackage.count }} docs)</span>
              </button>
            </div>

            <div v-else-if="detectedPackage.type === 'subject_list'" class="flex flex-wrap items-center gap-2 pt-1">
              <button
                type="button"
                @click="executeImport('append')"
                class="inline-flex items-center gap-1.5 bg-amber hover:bg-amber-hi text-surface font-semibold px-3.5 py-1.5 rounded-lg text-xs transition cursor-pointer shadow-sm"
              >
                <Layers class="w-3.5 h-3.5" />
                <span>Add {{ detectedPackage.count }} Subject(s) to Studio</span>
              </button>

              <button
                type="button"
                @click="executeImport('replace')"
                class="inline-flex items-center gap-1.5 bg-input hover:bg-edge border border-edge text-hi font-medium px-3.5 py-1.5 rounded-lg text-xs transition cursor-pointer"
              >
                <span>Replace Studio Subjects</span>
              </button>
            </div>

            <div v-else-if="detectedPackage.type === 'single_subject'" class="pt-1">
              <button
                type="button"
                @click="executeImport('replace')"
                class="inline-flex items-center gap-1.5 bg-amber hover:bg-amber-hi text-surface font-semibold px-4 py-2 rounded-xl text-xs transition cursor-pointer shadow-sm"
              >
                <Upload class="w-3.5 h-3.5" />
                <span>Import as New Subject</span>
              </button>
            </div>
          </div>

          <!-- Fallback or Error Messages -->
          <div v-if="importError" class="flex items-center gap-1.5 text-xs text-danger font-medium p-2.5 bg-danger/10 border border-danger/20 rounded-xl">
            <AlertCircle class="w-4 h-4 shrink-0" />
            <span>{{ importError }}</span>
          </div>

          <div
            v-else-if="detectedPackage?.type === 'invalid' || detectedPackage?.type === 'unknown'"
            class="flex items-center gap-1.5 text-xs text-danger font-medium p-2.5 bg-danger/10 border border-danger/20 rounded-xl"
          >
            <AlertCircle class="w-4 h-4 shrink-0" />
            <span>{{ detectedPackage.description }}</span>
          </div>

          <!-- Generic Fallback Submit if nothing detected yet -->
          <div v-if="!detectedPackage" class="flex items-center justify-end gap-2.5 pt-2">
            <button
              type="button"
              @click="close"
              class="text-xs text-mid hover:text-hi px-3 py-2 rounded-xl transition cursor-pointer"
            >
              Cancel
            </button>

            <button
              type="button"
              @click="executeImport('replace')"
              :disabled="!importInput.trim()"
              class="inline-flex items-center gap-1.5 bg-amber disabled:opacity-40 hover:bg-amber-hi text-surface font-semibold px-4 py-2 rounded-xl transition shadow-sm cursor-pointer"
            >
              <Upload class="w-3.5 h-3.5" />
              <span>Import Data</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
