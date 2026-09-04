<script setup lang="ts">
/**
 * DatePickerInput — custom dark-themed calendar popover.
 * Text field accepts DD/MM/YYYY. Calendar icon opens a popover matching
 * the app's warm zinc / amber palette. No native browser picker.
 */
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { CalendarDays, ChevronLeft, ChevronRight } from '@lucide/vue'
import { parseDate, formatDate } from '../../utils/dates'

const props = withDefaults(
  defineProps<{
    modelValue: string // DD/MM/YYYY
    placeholder?: string
    inputClass?: string
    align?: 'left' | 'right'
  }>(),
  {
    placeholder: 'DD/MM/YYYY',
    align: 'left',
  }
)

const emit = defineEmits<{
  (e: 'update:modelValue', val: string): void
}>()

// ── State ────────────────────────────────────────────────────────────────────

const isOpen = ref(false)
const rootRef = ref<HTMLElement | null>(null)

// Calendar view month/year (separate from selected value)
const viewYear = ref(new Date().getFullYear())
const viewMonth = ref(new Date().getMonth()) // 0-based

const DAYS = ['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa']
const MONTHS = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
]

// ── Derived ──────────────────────────────────────────────────────────────────

const selectedDate = computed<Date | null>(() => parseDate(props.modelValue))

/** The date string YYYY-MM-DD of the selected value for easy comparison */
const selectedKey = computed(() => {
  const d = selectedDate.value
  if (!d) return ''
  return `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`
})

const monthLabel = computed(() => `${MONTHS[viewMonth.value]}, ${viewYear.value}`)

/** All cells to render (including leading/trailing blanks = null) */
const calendarCells = computed<(number | null)[]>(() => {
  const first = new Date(viewYear.value, viewMonth.value, 1)
  const daysInMonth = new Date(viewYear.value, viewMonth.value + 1, 0).getDate()
  const leadingBlanks = first.getDay() // 0=Sun
  const cells: (number | null)[] = Array(leadingBlanks).fill(null)
  for (let d = 1; d <= daysInMonth; d++) cells.push(d)
  // Pad to full rows
  while (cells.length % 7 !== 0) cells.push(null)
  return cells
})

// ── Helpers ──────────────────────────────────────────────────────────────────

function isSelected(day: number | null): boolean {
  if (!day || !selectedDate.value) return false
  return selectedKey.value === `${viewYear.value}-${viewMonth.value}-${day}`
}

function isToday(day: number | null): boolean {
  if (!day) return false
  const t = new Date()
  return t.getFullYear() === viewYear.value && t.getMonth() === viewMonth.value && t.getDate() === day
}

function prevMonth() {
  if (viewMonth.value === 0) {
    viewMonth.value = 11
    viewYear.value--
  } else {
    viewMonth.value--
  }
}

function nextMonth() {
  if (viewMonth.value === 11) {
    viewMonth.value = 0
    viewYear.value++
  } else {
    viewMonth.value++
  }
}

function selectDay(day: number | null) {
  if (!day) return
  const d = new Date(viewYear.value, viewMonth.value, day)
  emit('update:modelValue', formatDate(d))
  isOpen.value = false
}

function selectToday() {
  const d = new Date()
  viewYear.value = d.getFullYear()
  viewMonth.value = d.getMonth()
  emit('update:modelValue', formatDate(d))
  isOpen.value = false
}

function clearDate() {
  emit('update:modelValue', '')
  isOpen.value = false
}

function openCalendar() {
  // Sync view to selected or today
  const d = selectedDate.value ?? new Date()
  viewYear.value = d.getFullYear()
  viewMonth.value = d.getMonth()
  isOpen.value = !isOpen.value
}

// Text field manual input
function onTextInput(e: Event) {
  emit('update:modelValue', (e.target as HTMLInputElement).value)
}

// ── Click-outside ─────────────────────────────────────────────────────────────

function onClickOutside(e: MouseEvent) {
  if (rootRef.value && !rootRef.value.contains(e.target as Node)) {
    isOpen.value = false
  }
}

onMounted(() => window.addEventListener('mousedown', onClickOutside, true))
onBeforeUnmount(() => window.removeEventListener('mousedown', onClickOutside, true))

// Sync view when value changes externally
watch(
  () => props.modelValue,
  (val) => {
    const d = parseDate(val)
    if (d) {
      viewYear.value = d.getFullYear()
      viewMonth.value = d.getMonth()
    }
  }
)
</script>

<template>
  <div ref="rootRef" class="relative flex items-center w-full min-w-0">
    <!-- Text input (DD/MM/YYYY) with guaranteed right padding so text never overlaps icon -->
    <input
      :value="modelValue"
      type="text"
      :placeholder="placeholder"
      :class="[
        inputClass || 'w-full bg-transparent text-xs font-mono text-hi outline-none placeholder:text-lo',
        'pr-6'
      ]"
      @input="onTextInput"
    />

    <!-- Calendar icon trigger -->
    <button
      type="button"
      @click.stop="openCalendar"
      class="absolute right-0.5 p-1 text-mid hover:text-amber rounded transition cursor-pointer shrink-0"
      title="Pick a date"
      tabindex="-1"
    >
      <CalendarDays class="w-3.5 h-3.5" />
    </button>

    <!-- Custom dark calendar popover -->
    <div
      v-if="isOpen"
      class="absolute top-full mt-1.5 z-[9999] w-[232px] bg-card border border-edge rounded-xl shadow-2xl shadow-black/80 p-3 select-none"
      :class="align === 'right' ? 'right-0' : 'left-0'"
      @mousedown.stop
    >
      <!-- Month / Year header -->
      <div class="flex items-center justify-between mb-2.5">
        <button
          type="button"
          @click="prevMonth"
          class="p-1 text-mid hover:text-hi hover:bg-input rounded-lg transition cursor-pointer"
        >
          <ChevronLeft class="w-3.5 h-3.5" />
        </button>

        <span class="text-xs font-semibold text-hi">{{ monthLabel }}</span>

        <button
          type="button"
          @click="nextMonth"
          class="p-1 text-mid hover:text-hi hover:bg-input rounded-lg transition cursor-pointer"
        >
          <ChevronRight class="w-3.5 h-3.5" />
        </button>
      </div>

      <!-- Day-of-week headers -->
      <div class="grid grid-cols-7 mb-1">
        <span
          v-for="d in DAYS"
          :key="d"
          class="text-center text-[10px] font-medium text-mid py-0.5"
        >{{ d }}</span>
      </div>

      <!-- Calendar cells -->
      <div class="grid grid-cols-7 gap-y-0.5">
        <button
          v-for="(cell, idx) in calendarCells"
          :key="idx"
          type="button"
          :disabled="!cell"
          @click="selectDay(cell)"
          class="h-7 w-7 mx-auto flex items-center justify-center text-[11px] rounded-lg transition cursor-pointer disabled:cursor-default"
          :class="[
            !cell ? '' :
            isSelected(cell)
              ? 'bg-amber text-surface font-semibold'
              : isToday(cell)
              ? 'bg-input text-amber font-semibold hover:bg-amber hover:text-surface'
              : 'text-hi hover:bg-input hover:text-hi'
          ]"
        >
          {{ cell ?? '' }}
        </button>
      </div>

      <!-- Footer actions -->
      <div class="flex items-center justify-between mt-2.5 pt-2 border-t border-edge">
        <button
          type="button"
          @click="clearDate"
          class="text-[11px] text-mid hover:text-danger transition cursor-pointer"
        >
          Clear
        </button>
        <button
          type="button"
          @click="selectToday"
          class="text-[11px] text-amber hover:text-amber-hi transition cursor-pointer font-medium"
        >
          Today
        </button>
      </div>
    </div>
  </div>
</template>
