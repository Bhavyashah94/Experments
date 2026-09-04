<script setup lang="ts">
import { isGuideOpen } from '../../store/labStore'
import { X, HelpCircle, CheckCircle, FileText } from 'lucide-vue-next'

function close() {
  isGuideOpen.value = false
}
</script>

<template>
  <div
    v-if="isGuideOpen"
    class="fixed inset-0 z-50 bg-surface/85 backdrop-blur-sm flex items-center justify-center p-4 sm:p-6 select-none"
    @click.self="close"
  >
    <div class="w-full max-w-lg bg-card border border-edge rounded-2xl overflow-hidden shadow-2xl flex flex-col max-h-[85vh]">
      <!-- Header -->
      <div class="px-5 py-3.5 border-b border-edge flex items-center justify-between text-xs">
        <div class="flex items-center gap-2 text-amber font-bold">
          <HelpCircle class="w-4 h-4" />
          <span>LabStudio Formatting Guide</span>
        </div>
        <button
          type="button"
          @click="close"
          class="p-1 rounded-lg text-mid hover:text-hi hover:bg-input transition cursor-pointer"
        >
          <X class="w-4 h-4" />
        </button>
      </div>

      <!-- Body -->
      <div class="p-5 text-xs text-mid space-y-4 overflow-y-auto leading-relaxed">
        <div>
          <h4 class="font-bold text-hi mb-1 flex items-center gap-1.5">
            <CheckCircle class="w-3.5 h-3.5 text-success" />
            Automatic Aim Detection
          </h4>
          <p class="text-mid text-[11px]">
            The backend inspects Page 1 of uploaded PDFs for standard keywords like <code class="text-amber bg-input border border-edge px-1 rounded">Aim:</code>, <code class="text-amber bg-input border border-edge px-1 rounded">Title:</code>, <code class="text-amber bg-input border border-edge px-1 rounded">Problem Statement:</code>, or <code class="text-amber bg-input border border-edge px-1 rounded">Experiment No. X</code>.
          </p>
        </div>

        <div>
          <h4 class="font-bold text-hi mb-1 flex items-center gap-1.5">
            <FileText class="w-3.5 h-3.5 text-amber" />
            Date Management
          </h4>
          <p class="text-mid text-[11px]">
            Enter a start date in the <strong>Date Schedule</strong> sidebar card and click <strong>+7 Days Weekly Auto-Fill</strong> to automatically compute sequential experiment dates. Dates are optional and can be left blank.
          </p>
        </div>

        <div>
          <h4 class="font-bold text-hi mb-1 flex items-center gap-1.5">
            <CheckCircle class="w-3.5 h-3.5 text-success" />
            Cover Sheet & Table of Contents
          </h4>
          <p class="text-mid text-[11px]">
            Institutional cover sheets are stamped onto each experiment with student details in selected pen ink. When Table of Contents is enabled, an auto-paginated Index sheet is prepended.
          </p>
        </div>
      </div>
    </div>
  </div>
</template>
