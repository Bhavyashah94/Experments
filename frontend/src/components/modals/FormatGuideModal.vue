<script setup lang="ts">
import { X, HelpCircle, Sparkles } from 'lucide-vue-next';

defineProps<{
  isOpen: boolean;
}>();

const emit = defineEmits<{
  (e: 'close'): void;
}>();
</script>

<template>
  <div
    v-if="isOpen"
    class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm"
    @click.self="emit('close')"
  >
    <div class="bg-card border border-border rounded-2xl max-w-lg w-full overflow-hidden shadow-2xl flex flex-col">
      <!-- Modal Header -->
      <div class="flex items-center justify-between px-5 py-4 border-b border-border">
        <div class="flex items-center gap-2">
          <HelpCircle class="w-4 h-4 text-zinc-300" />
          <h3 class="text-sm font-semibold text-white">PDF Auto-Detection & Formatting Guide</h3>
        </div>
        <button
          type="button"
          @click="emit('close')"
          class="p-1.5 text-zinc-400 hover:text-white rounded-lg hover:bg-zinc-800 transition"
        >
          <X class="w-4 h-4" />
        </button>
      </div>

      <!-- Modal Body Content -->
      <div class="p-5 space-y-4 text-xs text-zinc-300 leading-relaxed overflow-y-auto max-h-[70vh]">
        <div class="bg-inputBg/60 border border-border p-3.5 rounded-xl space-y-1.5">
          <div class="flex items-center gap-1.5 text-white font-semibold">
            <Sparkles class="w-3.5 h-3.5 text-zinc-300" />
            <span>How Aim & Number Detection Works</span>
          </div>
          <p class="text-muted text-[11px]">
            When you attach or bulk-drop PDFs, the studio inspects Page 1 text and filename patterns to auto-populate document cards, labels, and assignment switches.
          </p>
        </div>

        <div class="space-y-2">
          <h4 class="text-xs font-semibold text-white uppercase tracking-wider">Supported Numbering Formats:</h4>
          <ul class="list-disc pl-4 space-y-1.5 text-muted text-[11px]">
            <li>
              <strong class="text-zinc-200">Experiments:</strong>
              <code class="text-zinc-200 font-mono ml-1">Experiment No: 4</code>,
              <code class="text-zinc-200 font-mono ml-1">Exp 4</code>,
              <code class="text-zinc-200 font-mono ml-1">Exp - 4A</code>,
              <code class="text-zinc-200 font-mono ml-1">Experiment IV</code>
            </li>
            <li>
              <strong class="text-zinc-200">Assignments:</strong>
              <code class="text-zinc-200 font-mono ml-1">Assignment 2</code>,
              <code class="text-zinc-200 font-mono ml-1">Assign - 2</code>,
              <code class="text-zinc-200 font-mono ml-1">Assignment No. II</code>
            </li>
            <li>
              <strong class="text-zinc-200">Practicals & Labs:</strong>
              <code class="text-zinc-200 font-mono ml-1">Practical 3</code>,
              <code class="text-zinc-200 font-mono ml-1">Prac No: 3</code>,
              <code class="text-zinc-200 font-mono ml-1">Lab Session 5</code>,
              <code class="text-zinc-200 font-mono ml-1">Task 1</code>
            </li>
            <li>
              <strong class="text-zinc-200">Filename Fallbacks:</strong>
              <code class="text-zinc-200 font-mono ml-1">Exp_04.pdf</code>,
              <code class="text-zinc-200 font-mono ml-1">Assignment_2.pdf</code>,
              <code class="text-zinc-200 font-mono ml-1">Prac3.pdf</code>
            </li>
          </ul>
        </div>

        <div class="space-y-2">
          <h4 class="text-xs font-semibold text-white uppercase tracking-wider">Supported Aim & Title Formats:</h4>
          <ul class="list-disc pl-4 space-y-1 text-muted text-[11px]">
            <li><strong class="text-zinc-200">Aim:</strong> To study and implement MQTT Protocol for sensor nodes.</li>
            <li><strong class="text-zinc-200">Objective:</strong> Configuration of BGP Routing on Cisco Routers.</li>
            <li><strong class="text-zinc-200">Title:</strong> Convolutional Neural Networks for Image Classification.</li>
            <li><strong class="text-zinc-200">Header Line:</strong> <code class="text-zinc-200 font-mono">Exp 3: Implementation of AES Encryption</code></li>
          </ul>
        </div>
      </div>

      <!-- Modal Footer -->
      <div class="px-5 py-3 border-t border-border bg-inputBg/40 flex justify-end">
        <button
          type="button"
          @click="emit('close')"
          class="bg-white hover:bg-zinc-200 text-black font-semibold px-4 py-1.5 rounded-lg text-xs transition"
        >
          Got It
        </button>
      </div>
    </div>
  </div>
</template>
