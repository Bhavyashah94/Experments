<script setup lang="ts">
import { student } from '../../store/labStore'
import { Pipette } from 'lucide-vue-next'

const COLOR_SWATCHES = [
  { name: 'Royal Blue', hex: '#0000bf' },
  { name: 'Dark Blue', hex: '#1e3a8a' },
  { name: 'Black', hex: '#000000' },
  { name: 'Red', hex: '#dc2626' },
  { name: 'Green', hex: '#059669' },
  { name: 'Purple', hex: '#7c3aed' },
]

function setColor(hex: string) {
  student.text_color = hex
}

function handleCustomColorInput(e: Event) {
  const target = e.target as HTMLInputElement
  if (target.value) student.text_color = target.value
}
</script>

<template>
  <div class="bg-card border border-edge rounded-xl p-4 shadow-sm space-y-3.5 select-none">
    <!-- Ink Color Section -->
    <div class="space-y-2">
      <div class="flex items-center justify-between">
        <span class="text-xs font-semibold text-hi uppercase tracking-wider">Ink Color:</span>
        <span class="text-[11px] font-mono text-mid uppercase">{{ student.text_color }}</span>
      </div>

      <!-- Swatches + Custom -->
      <div class="flex items-center gap-2 flex-wrap">
        <button
          v-for="swatch in COLOR_SWATCHES"
          :key="swatch.hex"
          type="button"
          @click="setColor(swatch.hex)"
          class="w-6 h-6 rounded-full border-2 transition-all flex items-center justify-center cursor-pointer"
          :class="student.text_color.toLowerCase() === swatch.hex.toLowerCase()
            ? 'border-hi scale-110 shadow-md ring-2 ring-amber/40'
            : 'border-edge hover:border-edge-hi hover:scale-105'"
          :style="{ backgroundColor: swatch.hex }"
          :title="swatch.name"
        >
          <span
            v-if="student.text_color.toLowerCase() === swatch.hex.toLowerCase()"
            class="text-white text-[10px] font-bold"
          >✓</span>
        </button>

        <!-- Custom picker -->
        <label
          class="relative inline-flex items-center gap-1 bg-input border border-edge hover:border-edge-hi px-2 py-1 rounded-lg text-xs text-mid hover:text-hi transition cursor-pointer"
          title="Pick custom pen ink color"
        >
          <input
            type="color"
            :value="student.text_color.startsWith('#') ? student.text_color : '#0000bf'"
            @input="handleCustomColorInput"
            class="opacity-0 w-0 h-0 absolute pointer-events-none"
          />
          <Pipette class="w-3 h-3 text-amber" />
          <span class="text-[11px]">Custom</span>
        </label>
      </div>
    </div>

    <!-- Toggles -->
    <div class="pt-2 border-t border-edge space-y-2 text-xs">
      <label class="flex items-center gap-2 cursor-pointer text-mid hover:text-hi transition">
        <input
          v-model="student.include_toc"
          type="checkbox"
          class="w-4 h-4 rounded bg-input border-edge accent-amber cursor-pointer"
        />
        <span>Include Index / Table of Contents</span>
      </label>

      <label class="flex items-center gap-2 cursor-pointer text-mid hover:text-hi transition">
        <input
          v-model="student.strikethrough_enabled"
          type="checkbox"
          class="w-4 h-4 rounded bg-input border-edge accent-amber cursor-pointer"
        />
        <span>Strikethrough Exp/Assign header</span>
      </label>
    </div>
  </div>
</template>
