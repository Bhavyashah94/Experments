<script setup lang="ts">
import { ref, computed } from 'vue'
import type { ExperimentItem } from '../../store/types'
import {
  openPreview,
  downloadSingleExperiment,
  removeExperimentFromManifest,
  replaceExperimentPdf,
  downloadingIds,
  experiments,
  copyDatesFromPrevious,
  selectedId,
} from '../../store/labStore'
import { addDays } from '../../utils/dates'
import DatePickerInput from '../ui/DatePickerInput.vue'
import {
  GripVertical,
  Eye,
  Download,
  Trash2,
  ChevronDown,
  ChevronRight,
  Loader2,
  FileUp,
} from 'lucide-vue-next'

const props = defineProps<{
  doc: ExperimentItem
  index: number
  total: number
}>()

const replaceFileInputRef = ref<HTMLInputElement | null>(null)
const isDownloading = computed(() => downloadingIds.has(props.doc.id))

function triggerFileInput() {
  replaceFileInputRef.value?.click()
}

function handleFileInput(e: Event) {
  const target = e.target as HTMLInputElement
  if (target.files && target.files[0]) {
    replaceExperimentPdf(props.doc.id, target.files[0])
    target.value = ''
  }
}

function handleDrop(e: DragEvent) {
  e.preventDefault()
  if (e.dataTransfer?.files && e.dataTransfer.files[0]) {
    replaceExperimentPdf(props.doc.id, e.dataTransfer.files[0])
  }
}

function suggestSubDate() {
  if (props.doc.perf_date) {
    props.doc.sub_date = addDays(props.doc.perf_date, 7)
  }
}

function handleSameAsPrevious() {
  copyDatesFromPrevious(props.index)
}

function applySnippet() {
  if (props.doc.text_snippet) {
    const clean = props.doc.text_snippet.replace(/\s+/g, ' ').trim()
    props.doc.title = clean.length > 100 ? clean.slice(0, 100) : clean
  }
}
</script>

<template>
  <div class="bg-card border border-edge rounded-xl overflow-hidden shadow-sm transition-all duration-150">
    <!-- Hidden Replace File Input -->
    <input
      ref="replaceFileInputRef"
      type="file"
      accept=".pdf,application/pdf"
      class="hidden"
      @change="handleFileInput"
    />

    <!-- Accordion Header -->
    <div
      class="flex items-center gap-2.5 px-4 py-3 cursor-pointer hover:bg-input select-none transition-all"
      :class="{ 'bg-input/60 ring-1 ring-amber/30': selectedId === doc.id }"
      @click="doc.isOpen = !doc.isOpen; selectedId = doc.id"
    >
      <!-- Dedicated Drag Handle -->
      <div
        class="drag-handle p-1 text-lo hover:text-hi cursor-grab active:cursor-grabbing shrink-0 touch-none rounded hover:bg-edge transition"
        @click.stop
        title="Drag to reorder card"
      >
        <GripVertical class="w-4 h-4 pointer-events-none" />
      </div>

      <!-- Exp / Assign Type Badge -->
      <button
        type="button"
        @click.stop="doc.is_assignment = !doc.is_assignment"
        class="text-xs font-mono font-bold px-2 py-0.5 rounded border transition shrink-0 cursor-pointer"
        :class="doc.is_assignment ? 'bg-amber-dim/30 text-amber border-amber/40' : 'bg-input border-edge text-hi'"
        title="Click to toggle between Experiment and Assignment"
      >
        {{ doc.is_assignment ? 'Assign' : 'Exp' }}
      </button>

      <!-- Label Number Input -->
      <div class="flex items-center gap-1 shrink-0" @click.stop>
        <span class="text-xs text-mid">No.</span>
        <input
          v-model="doc.label"
          type="text"
          class="w-10 bg-input border border-edge rounded px-1.5 py-0.5 text-xs text-hi text-center font-mono outline-none focus:border-amber"
        />
      </div>

      <!-- Title Preview Text -->
      <span
        class="flex-1 text-xs truncate"
        :class="doc.title ? 'text-hi font-medium' : 'italic text-lo'"
      >
        {{ doc.title || 'Untitled Document' }}
      </span>

      <!-- Page Count Badge -->
      <span
        v-if="doc.pages > 0"
        class="text-[11px] font-mono text-mid bg-input border border-edge px-2 py-0.5 rounded shrink-0 hidden sm:inline-block"
      >
        {{ doc.pages }} {{ doc.pages === 1 ? 'page' : 'pages' }}
      </span>

      <!-- Action Buttons -->
      <div class="flex items-center gap-1.5 shrink-0" @click.stop>
        <button
          type="button"
          @click="openPreview(doc)"
          class="inline-flex items-center gap-1 text-xs text-mid hover:text-hi bg-input border border-edge hover:border-edge-hi px-2.5 py-1 rounded-lg transition cursor-pointer"
          title="Live preview cover page"
        >
          <Eye class="w-3.5 h-3.5" />
          <span class="hidden sm:inline">Preview</span>
        </button>

        <button
          type="button"
          @click="downloadSingleExperiment(doc)"
          :disabled="isDownloading"
          class="inline-flex items-center gap-1 text-xs text-mid hover:text-hi bg-input border border-edge hover:border-edge-hi px-2.5 py-1 rounded-lg transition disabled:opacity-50 cursor-pointer"
          title="Download single experiment with header"
        >
          <Loader2 v-if="isDownloading" class="w-3.5 h-3.5 animate-spin text-amber" />
          <Download v-else class="w-3.5 h-3.5" />
          <span class="hidden sm:inline">Download</span>
        </button>

        <button
          type="button"
          @click="removeExperimentFromManifest(doc.id)"
          class="p-1.5 text-lo hover:text-danger rounded-lg hover:bg-edge transition cursor-pointer"
          title="Remove document card"
        >
          <Trash2 class="w-3.5 h-3.5" />
        </button>
      </div>

      <!-- Collapse Chevron -->
      <div class="text-lo shrink-0">
        <ChevronDown v-if="doc.isOpen" class="w-4 h-4" />
        <ChevronRight v-else class="w-4 h-4" />
      </div>
    </div>

    <!-- Accordion Body -->
    <div v-show="doc.isOpen" class="p-4 bg-surface border-t border-edge space-y-3.5">
      <!-- Aim / Title Input -->
      <div>
        <label class="block text-[11px] font-medium text-mid uppercase tracking-wider mb-1.5">
          Aim / Title of {{ doc.is_assignment ? 'Assignment' : 'Experiment' }}
        </label>
        <input
          v-model="doc.title"
          type="text"
          placeholder="e.g. Study and Implementation of MQTT Protocol for Sensor Nodes"
          class="w-full bg-input border border-edge text-xs text-hi rounded-lg px-3 py-2 outline-none focus:border-amber transition"
        />

        <!-- Contextual Source Snippet if unextracted -->
        <div
          v-if="doc.text_snippet && (!doc.title || doc.extraction_method === 'unextracted')"
          class="mt-1.5 p-2 rounded bg-input border border-edge text-[11px] text-mid flex items-center justify-between gap-2"
        >
          <span class="truncate font-mono text-[10px]">
            Page 1 text: {{ doc.text_snippet.slice(0, 90) }}...
          </span>
          <button
            type="button"
            @click="applySnippet"
            class="text-amber hover:text-amber-hi underline shrink-0 text-[10px] cursor-pointer"
          >
            Insert snippet
          </button>
        </div>
      </div>

      <!-- Dates Row (Ergonomic max-w constraint) -->
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 max-w-xl">
        <div>
          <div class="flex items-center justify-between mb-1.5">
            <label class="block text-[11px] font-medium text-mid uppercase tracking-wider">
              Performance Date
            </label>
            <button
              v-if="index > 0"
              type="button"
              @click="handleSameAsPrevious"
              class="text-[10px] text-amber hover:text-amber-hi underline cursor-pointer"
            >
              = Same as Exp {{ experiments[index - 1]?.label || index }}
            </button>
          </div>
          <DatePickerInput
            v-model="doc.perf_date"
            input-class="w-full bg-input border border-edge text-xs font-mono text-hi rounded-lg px-3 py-2 pr-8 outline-none focus:border-amber transition"
          />
        </div>

        <div>
          <div class="flex items-center justify-between mb-1.5">
            <label class="block text-[11px] font-medium text-mid uppercase tracking-wider">
              Submission Date
            </label>
            <button
              type="button"
              @click="suggestSubDate"
              class="text-[10px] text-amber hover:text-amber-hi underline cursor-pointer"
            >
              +7d suggested
            </button>
          </div>
          <DatePickerInput
            v-model="doc.sub_date"
            align="right"
            input-class="w-full bg-input border border-edge text-xs font-mono text-hi rounded-lg px-3 py-2 pr-8 outline-none focus:border-amber transition"
          />
        </div>
      </div>

      <!-- Individual File Drop Area / Replace PDF -->
      <div class="max-w-xl">
        <label
          class="border border-dashed border-edge hover:border-edge-hi bg-input hover:bg-card rounded-lg p-3 text-center cursor-pointer transition flex items-center justify-center gap-2 group"
          @dragover.prevent
          @drop.prevent="handleDrop"
          @click="triggerFileInput"
        >
          <FileUp class="w-4 h-4 text-lo group-hover:text-hi transition" />
          <span class="text-xs text-mid">
            <template v-if="doc.filename">
              Attached: <strong class="text-hi">{{ doc.filename }}</strong> ({{ doc.pages }} pages) · Click to replace
            </template>
            <template v-else>
              Drop body PDF file here or click to attach
            </template>
          </span>
        </label>
      </div>
    </div>
  </div>
</template>
