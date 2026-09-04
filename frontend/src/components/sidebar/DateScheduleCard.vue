<script setup lang="ts">
import { student, applyGlobalDates, applyWeeklyDates, clearAllDates, hasAnyDates } from '../../store/labStore'
import { RefreshCw, Calendar, XCircle } from 'lucide-vue-next'
import DatePickerInput from '../ui/DatePickerInput.vue'
</script>

<template>
  <div class="bg-card border border-edge rounded-xl p-4 shadow-sm space-y-3 select-none">
    <!-- Header Row -->
    <div class="flex items-center justify-between">
      <span class="text-xs font-semibold text-hi uppercase tracking-wider">
        Date Schedule:
      </span>
      <span class="text-[10px] text-lo font-medium">Batch Defaults</span>
    </div>

    <!-- Inputs Row: 2 equal-width pills with ample space -->
    <div class="grid grid-cols-2 gap-2">
      <!-- Perf Input -->
      <div class="flex items-center gap-1.5 bg-input border border-edge px-2.5 py-1.5 rounded-lg focus-within:border-amber transition min-w-0">
        <span class="text-[11px] text-mid uppercase font-mono font-medium shrink-0">Perf:</span>
        <DatePickerInput
          :model-value="student.global_perf_date || ''"
          @update:model-value="student.global_perf_date = $event"
          align="left"
          class="flex-1 min-w-0"
        />
      </div>

      <!-- Sub Input -->
      <div class="flex items-center gap-1.5 bg-input border border-edge px-2.5 py-1.5 rounded-lg focus-within:border-amber transition min-w-0">
        <span class="text-[11px] text-mid uppercase font-mono font-medium shrink-0">Sub:</span>
        <DatePickerInput
          :model-value="student.global_sub_date || ''"
          @update:model-value="student.global_sub_date = $event"
          align="right"
          class="flex-1 min-w-0"
        />
      </div>
    </div>

    <!-- Action Buttons Row -->
    <div class="flex flex-wrap items-center justify-end gap-2 pt-1 border-t border-edge">
      <button
        v-if="hasAnyDates"
        type="button"
        @click="clearAllDates"
        class="inline-flex items-center gap-1 text-xs text-danger hover:text-red-300 px-2 py-1 rounded-lg transition cursor-pointer"
        title="Clear dates from all document cards"
      >
        <XCircle class="w-3 h-3" />
        <span>Clear</span>
      </button>

      <button
        type="button"
        @click="applyGlobalDates"
        class="inline-flex items-center gap-1.5 text-xs text-mid hover:text-hi bg-input border border-edge hover:border-edge-hi px-2.5 py-1 rounded-lg transition cursor-pointer"
        title="Copy these global dates to all document cards"
      >
        <RefreshCw class="w-3 h-3 text-lo" />
        <span>Apply All</span>
      </button>

      <button
        type="button"
        @click="applyWeeklyDates"
        class="inline-flex items-center gap-1.5 text-xs text-surface bg-amber hover:bg-amber-hi font-semibold px-3 py-1 rounded-lg transition cursor-pointer shadow-sm"
        title="Auto-fill sequential weekly dates (+7 days) across all cards"
      >
        <Calendar class="w-3 h-3" />
        <span>+7 Days Weekly Auto-Fill</span>
      </button>
    </div>
  </div>
</template>
