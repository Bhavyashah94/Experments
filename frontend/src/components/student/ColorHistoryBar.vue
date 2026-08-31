<script setup lang="ts">
import { ref, computed, watch } from 'vue';
import { useProfileStore } from '@/stores/useProfileStore';
import { DEFAULT_COLORS } from '@/services/storage';
import { Pipette, Check } from 'lucide-vue-next';

const profileStore = useProfileStore();

const hexInput = ref(profileStore.activeProfile.textColor);
const nativePicker = ref<HTMLInputElement | null>(null);

watch(
  () => profileStore.activeProfile.textColor,
  (newColor) => {
    hexInput.value = newColor;
  }
);

function isActive(color: string): boolean {
  return profileStore.activeProfile.textColor.toLowerCase() === color.toLowerCase();
}

const allColors = computed(() => {
  const presetSet = new Set(DEFAULT_COLORS.map((c) => c.toLowerCase()));
  const extra = profileStore.recentColors.filter((c) => !presetSet.has(c.toLowerCase()));
  return [...DEFAULT_COLORS, ...extra];
});

function handleHexChange() {
  let clean = hexInput.value.trim().replace(/^#/, '');
  if (clean.length === 3) {
    clean = clean.split('').map((c) => c + c).join('');
  }
  if (/^[0-9a-fA-F]{6}$/.test(clean)) {
    const formatted = '#' + clean.toLowerCase();
    profileStore.setTextColor(formatted);
  }
}

function handleNativePick(e: Event) {
  const val = (e.target as HTMLInputElement).value;
  profileStore.setTextColor(val);
}

function triggerNativePicker() {
  nativePicker.value?.click();
}
</script>

<template>
  <div class="bg-card border border-border rounded-xl p-4 shadow-sm space-y-3 flex flex-col justify-between">
    <!-- Top Row: Label, Active Hex Badge & Pipette -->
    <div class="flex items-center justify-between gap-2">
      <span class="text-xs font-semibold text-muted uppercase tracking-wider">Ink Color:</span>

      <div class="flex items-center gap-2">
        <!-- Interactive Hex Input with Live Color Pill -->
        <div class="flex items-center gap-2 bg-inputBg border border-border px-2.5 py-1 rounded-lg focus-within:border-zinc-400 transition">
          <span
            class="w-3.5 h-3.5 rounded-full border border-white/20 shadow-sm shrink-0"
            :style="{ backgroundColor: profileStore.activeProfile.textColor }"
          ></span>
          <input
            type="text"
            v-model="hexInput"
            @blur="handleHexChange"
            @keyup.enter="handleHexChange"
            maxlength="7"
            class="w-16 bg-transparent text-xs font-mono font-semibold text-white uppercase outline-none focus:outline-none"
          />
        </div>

        <!-- Custom Color Picker Button -->
        <button
          type="button"
          @click="triggerNativePicker"
          class="inline-flex items-center gap-1 text-xs text-zinc-300 hover:text-white bg-inputBg hover:bg-zinc-800 border border-border hover:border-zinc-400 px-2.5 py-1 rounded-lg transition focus:outline-none"
          title="Pick custom color"
        >
          <Pipette class="w-3 h-3" />
          <span>Custom</span>
        </button>
        <input
          ref="nativePicker"
          type="color"
          :value="profileStore.activeProfile.textColor"
          @input="handleNativePick"
          class="sr-only"
        />
      </div>
    </div>

    <!-- Bottom Row: 6 Presets + Custom Swatches (Wrap cleanly, no scrollbar) -->
    <div class="flex flex-wrap items-center gap-2.5 pt-0.5">
      <button
        v-for="color in allColors"
        :key="color"
        type="button"
        @click="profileStore.setTextColor(color)"
        class="w-7 h-7 rounded-full transition-all duration-150 shrink-0 flex items-center justify-center cursor-pointer focus:outline-none"
        :class="isActive(color) ? 'border-2 border-white ring-2 ring-white/30 scale-105' : 'border border-white/10 opacity-70 hover:opacity-100 hover:scale-105'"
        :style="{ backgroundColor: color }"
        :title="color"
      >
        <Check v-if="isActive(color)" class="w-3.5 h-3.5 text-white drop-shadow stroke-[2.5]" />
      </button>
    </div>
  </div>
</template>
