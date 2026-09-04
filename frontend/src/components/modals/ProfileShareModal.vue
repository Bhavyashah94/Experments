<script setup lang="ts">
import { ref, computed } from 'vue'
import {
  isShareOpen,
  student,
  experiments,
  exportSubjectPackage,
  importSubjectPackage,
  showToast,
} from '../../store/labStore'
import { Share2, Upload, X, Copy, Check, Download, FileJson, BookOpen } from 'lucide-vue-next'

const activeTab = ref<'export' | 'import'>('export')
const copied = ref(false)
const importInput = ref('')
const importError = ref<string | null>(null)

const jsonContent = computed(() => {
  if (!isShareOpen.value) return ''
  return exportSubjectPackage()
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
    showToast('Copied subject JSON to clipboard')
  } catch (err) {
    showToast('Failed to copy to clipboard')
  }
}

function handleDownloadJson() {
  const blob = new Blob([jsonContent.value], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  const safeName = (student.subject || 'Subject_Experiments').replace(/[^\w\-]/g, '_')
  a.href = url
  a.download = `${safeName}.labstudio.json`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
  showToast(`Downloaded ${safeName}.labstudio.json`)
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
      handleDoImport()
    }
  }
  reader.readAsText(file)
}

function handleDoImport() {
  importError.value = null
  if (!importInput.value.trim()) {
    importError.value = 'Please paste JSON or upload a file.'
    return
  }

  const res = importSubjectPackage(importInput.value.trim())
  if (res.success) {
    showToast(`Imported "${res.subjectName}" with ${res.count} experiment(s)!`)
    close()
  } else {
    importError.value = res.error || 'Failed to import subject.'
  }
}
</script>

<template>
  <div
    v-if="isShareOpen"
    class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-surface/85 backdrop-blur-sm select-none"
    @click.self="close"
  >
    <div class="bg-card border border-edge rounded-2xl w-full max-w-xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
      <!-- Header -->
      <div class="flex items-center justify-between px-5 py-4 border-b border-edge">
        <div class="flex items-center gap-2.5">
          <div class="w-8 h-8 rounded-lg bg-input border border-edge flex items-center justify-center text-amber">
            <BookOpen class="w-4 h-4" />
          </div>
          <div>
            <h2 class="text-xs sm:text-sm font-bold text-hi tracking-tight">
              Share Subject: {{ student.subject || 'Lab Experiments' }}
            </h2>
            <p class="text-[11px] text-mid">
              Share experiment titles &amp; dates with your classmates in 1 click
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

      <!-- Tab Buttons -->
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
          <span>Import Subject Syllabus</span>
        </button>
      </div>

      <!-- Modal Body -->
      <div class="p-5 overflow-y-auto flex-1 space-y-4 text-xs">
        <!-- EXPORT TAB -->
        <div v-if="activeTab === 'export'" class="space-y-4">
          <div class="bg-input border border-edge rounded-xl p-3 text-hi space-y-1">
            <p class="font-semibold text-hi">
              Ready to share "{{ student.subject }}"
            </p>
            <p class="text-[11px] text-mid">
              Only the subject name, experiment aims, and dates are shared. Your personal Student Name and Roll Number are kept private.
            </p>
          </div>

          <div class="space-y-1.5">
            <div class="flex items-center justify-between text-[11px] text-mid">
              <span>Subject Syllabus Data</span>
              <span>{{ experiments.length }} experiment(s)</span>
            </div>
            <textarea
              readonly
              :value="jsonContent"
              rows="7"
              class="w-full bg-input border border-edge rounded-xl p-3 text-[11px] font-mono text-hi select-all outline-none resize-none"
            ></textarea>
          </div>

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

        <!-- IMPORT TAB -->
        <div v-else class="space-y-4">
          <div class="bg-input border border-edge rounded-xl p-3 text-hi space-y-1">
            <p class="font-semibold text-hi">Load a Classmate's Subject Syllabus</p>
            <p class="text-[11px] text-mid">
              Paste the JSON or upload a <code class="text-amber bg-surface border border-edge px-1 rounded">.json</code> file to import all experiment titles and dates as a new subject.
            </p>
          </div>

          <!-- File Upload Dropzone -->
          <label class="block border border-dashed border-edge hover:border-edge-hi bg-input hover:bg-card rounded-xl p-4 text-center cursor-pointer transition">
            <input type="file" accept=".json,application/json" class="hidden" @change="handleFileUpload" />
            <FileJson class="w-6 h-6 mx-auto text-lo mb-1.5" />
            <p class="text-xs font-semibold text-hi">Upload .json file</p>
            <p class="text-[10px] text-mid">or paste the JSON text below</p>
          </label>

          <div class="space-y-1.5">
            <label class="block text-[11px] text-mid font-medium uppercase tracking-wider">Paste JSON</label>
            <textarea
              v-model="importInput"
              placeholder="Paste the shared subject JSON here..."
              rows="5"
              class="w-full bg-input border border-edge rounded-xl p-3 text-xs font-mono text-hi outline-none focus:border-amber resize-none"
            ></textarea>
          </div>

          <div v-if="importError" class="text-xs text-danger font-medium">
            {{ importError }}
          </div>

          <div class="flex items-center justify-end gap-2.5 pt-2">
            <button
              type="button"
              @click="close"
              class="text-xs text-mid hover:text-hi px-3 py-2 rounded-xl transition cursor-pointer"
            >
              Cancel
            </button>

            <button
              type="button"
              @click="handleDoImport"
              class="inline-flex items-center gap-1.5 bg-amber hover:bg-amber-hi text-surface font-semibold px-4 py-2 rounded-xl transition shadow-sm cursor-pointer"
            >
              <Upload class="w-3.5 h-3.5" />
              <span>Import Subject</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
