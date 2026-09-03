<script setup lang="ts">
import { ref } from 'vue';
import { useLabStore } from '../store';
import { Palette, Calendar, RefreshCw, Plus, Check } from 'lucide-vue-next';

const store = useLabStore();

const newProfileName = ref('');
const showNewProfile = ref(false);

const colorPresets = [
  { name: 'Royal Blue', hex: '#0000bf' },
  { name: 'Navy', hex: '#000050' },
  { name: 'Black', hex: '#000000' },
  { name: 'Emerald', hex: '#005000' },
  { name: 'Crimson', hex: '#700000' },
];

function handleCreateProfile() {
  if (newProfileName.value.trim()) {
    store.saveAsNewProfile(newProfileName.value.trim());
    newProfileName.value = '';
    showNewProfile.value = false;
  }
}
</script>

<template>
  <div class="bg-[#141417] border border-[#27272a] rounded-xl p-4 sm:p-5 space-y-4">
    <!-- Top Row: Subject Profile Selector -->
    <div class="flex items-center justify-between gap-2 border-b border-[#27272a] pb-3">
      <div class="flex items-center gap-2">
        <span class="text-[11px] font-semibold text-zinc-400 uppercase tracking-wider">Subject Profile:</span>
        <select
          :value="store.activeProfileId"
          @change="(e) => store.switchProfile((e.target as HTMLSelectElement).value)"
          class="bg-[#1c1c21] border border-[#27272a] rounded-lg px-2.5 py-1 text-xs text-white font-medium outline-none focus:border-zinc-400 cursor-pointer"
        >
          <option v-for="p in store.profiles" :key="p.id" :value="p.id">
            {{ p.name }}
          </option>
        </select>
      </div>

      <button
        type="button"
        @click="showNewProfile = !showNewProfile"
        class="inline-flex items-center gap-1 text-xs text-zinc-300 hover:text-white bg-[#1c1c21] border border-[#27272a] hover:border-zinc-400 px-2 py-1 rounded-lg transition"
      >
        <Plus class="w-3.5 h-3.5" />
        <span>New</span>
      </button>
    </div>

    <!-- Add Profile Inline Form -->
    <div v-if="showNewProfile" class="flex items-center gap-2 bg-[#1c1c21] p-2.5 rounded-lg border border-[#27272a]">
      <input
        type="text"
        v-model="newProfileName"
        placeholder="Profile name (e.g. IoT Lab, Cloud Lab)"
        class="flex-1 bg-[#141417] border border-[#27272a] text-xs text-white rounded px-2.5 py-1 outline-none focus:border-zinc-400"
        @keyup.enter="handleCreateProfile"
      />
      <button
        type="button"
        @click="handleCreateProfile"
        class="text-xs bg-white text-black font-semibold px-2.5 py-1 rounded hover:bg-zinc-200"
      >
        Save
      </button>
      <button
        type="button"
        @click="showNewProfile = false"
        class="text-xs text-zinc-400 hover:text-white px-1.5 py-1"
      >
        Cancel
      </button>
    </div>

    <!-- Student Details Header & Readiness Pill -->
    <div class="flex items-center justify-between pt-1">
      <span class="text-xs font-semibold text-zinc-300 uppercase tracking-wider">Student Details</span>
      <span
        v-if="store.isStudentComplete"
        class="text-[10px] font-medium text-emerald-400 bg-emerald-950/40 border border-emerald-800/60 px-2 py-0.5 rounded-full flex items-center gap-1"
      >
        <Check class="w-3 h-3" />
        <span>6/6 Complete</span>
      </span>
      <span
        v-else
        class="text-[10px] font-medium text-amber-400 bg-amber-950/40 border border-amber-800/60 px-2 py-0.5 rounded-full"
      >
        {{ store.missingStudentFields.length }} Required Left
      </span>
    </div>

    <!-- The 6 Compulsory Fields -->
    <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
      <div>
        <label class="block text-[11px] font-medium text-zinc-400 uppercase tracking-wider mb-1">
          Student Name <span class="text-red-400 font-bold">*</span>
        </label>
        <input
          type="text"
          v-model="store.student.name"
          placeholder="e.g. Bhavya Shah"
          class="w-full bg-[#1c1c21] border border-[#27272a] text-xs text-white rounded-lg px-3 py-2 outline-none focus:border-zinc-400 transition"
          :class="!store.student.name.trim() ? 'border-amber-900/40' : ''"
        />
      </div>

      <div>
        <label class="block text-[11px] font-medium text-zinc-400 uppercase tracking-wider mb-1">
          Roll Number <span class="text-red-400 font-bold">*</span>
        </label>
        <input
          type="text"
          v-model="store.student.rollNo"
          placeholder="e.g. 34"
          class="w-full bg-[#1c1c21] border border-[#27272a] text-xs text-white rounded-lg px-3 py-2 outline-none focus:border-zinc-400 transition"
          :class="!store.student.rollNo.trim() ? 'border-amber-900/40' : ''"
        />
      </div>

      <div>
        <label class="block text-[11px] font-medium text-zinc-400 uppercase tracking-wider mb-1">
          Batch <span class="text-red-400 font-bold">*</span>
        </label>
        <input
          type="text"
          v-model="store.student.batch"
          placeholder="e.g. I3"
          class="w-full bg-[#1c1c21] border border-[#27272a] text-xs text-white rounded-lg px-3 py-2 outline-none focus:border-zinc-400 transition"
          :class="!store.student.batch.trim() ? 'border-amber-900/40' : ''"
        />
      </div>

      <div>
        <label class="block text-[11px] font-medium text-zinc-400 uppercase tracking-wider mb-1">
          Class / Division <span class="text-red-400 font-bold">*</span>
        </label>
        <input
          type="text"
          v-model="store.student.className"
          placeholder="e.g. BE IT"
          class="w-full bg-[#1c1c21] border border-[#27272a] text-xs text-white rounded-lg px-3 py-2 outline-none focus:border-zinc-400 transition"
          :class="!store.student.className.trim() ? 'border-amber-900/40' : ''"
        />
      </div>

      <div>
        <label class="block text-[11px] font-medium text-zinc-400 uppercase tracking-wider mb-1">
          Semester <span class="text-red-400 font-bold">*</span>
        </label>
        <input
          type="text"
          v-model="store.student.sem"
          placeholder="e.g. VII"
          class="w-full bg-[#1c1c21] border border-[#27272a] text-xs text-white rounded-lg px-3 py-2 outline-none focus:border-zinc-400 transition"
          :class="!store.student.sem.trim() ? 'border-amber-900/40' : ''"
        />
      </div>

      <div>
        <label class="block text-[11px] font-medium text-zinc-400 uppercase tracking-wider mb-1">
          Subject <span class="text-red-400 font-bold">*</span>
        </label>
        <input
          type="text"
          v-model="store.student.subject"
          placeholder="e.g. Internet of Things"
          class="w-full bg-[#1c1c21] border border-[#27272a] text-xs text-white rounded-lg px-3 py-2 outline-none focus:border-zinc-400 transition"
          :class="!store.student.subject.trim() ? 'border-amber-900/40' : ''"
        />
      </div>
    </div>

    <!-- Ink Color Selection -->
    <div class="border-t border-[#27272a] pt-3 space-y-2">
      <div class="flex items-center justify-between">
        <span class="text-[11px] font-semibold text-zinc-400 uppercase tracking-wider flex items-center gap-1.5">
          <Palette class="w-3.5 h-3.5" />
          <span>Ink Color</span>
        </span>
        <div class="flex items-center gap-1">
          <input
            type="color"
            v-model="store.student.textColor"
            class="w-5 h-5 rounded cursor-pointer border-0 bg-transparent"
            title="Custom ink color"
          />
          <span class="text-[11px] font-mono text-zinc-400">{{ store.student.textColor }}</span>
        </div>
      </div>

      <div class="flex items-center gap-2">
        <button
          v-for="c in colorPresets"
          :key="c.hex"
          type="button"
          @click="store.student.textColor = c.hex"
          class="flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-lg border transition"
          :class="store.student.textColor === c.hex ? 'border-white bg-zinc-800 text-white font-medium' : 'border-[#27272a] text-zinc-400 hover:border-zinc-500'"
        >
          <span class="w-2.5 h-2.5 rounded-full" :style="{ backgroundColor: c.hex }"></span>
          <span>{{ c.name }}</span>
        </button>
      </div>
    </div>

    <!-- Global Schedule Dates (Strictly Optional) -->
    <div class="border-t border-[#27272a] pt-3 space-y-2">
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-1.5">
          <span class="text-[11px] font-semibold text-zinc-400 uppercase tracking-wider flex items-center gap-1.5">
            <Calendar class="w-3.5 h-3.5" />
            <span>Date Schedule</span>
          </span>
          <span class="text-[10px] text-zinc-500 lowercase">(optional)</span>
        </div>

        <div class="flex items-center gap-1.5">
          <button
            type="button"
            @click="store.applyGlobalDates"
            class="inline-flex items-center gap-1 text-[11px] text-zinc-300 hover:text-white bg-[#1c1c21] border border-[#27272a] hover:border-zinc-400 px-2 py-0.5 rounded transition"
            title="Apply these dates to all experiments"
          >
            <RefreshCw class="w-3 h-3" />
            <span>Apply All</span>
          </button>

          <button
            type="button"
            @click="store.applyWeeklyDates"
            class="inline-flex items-center gap-1 text-[11px] text-white bg-zinc-800 hover:bg-zinc-700 border border-zinc-600 px-2 py-0.5 rounded font-medium transition"
            title="Auto-fill weekly dates (+7 days) sequentially"
          >
            <span>+7 Days Auto-Fill</span>
          </button>
        </div>
      </div>

      <div class="grid grid-cols-2 gap-2">
        <div class="flex items-center gap-1.5 bg-[#1c1c21] border border-[#27272a] px-2.5 py-1.5 rounded-lg">
          <span class="text-[10px] text-zinc-400 uppercase font-medium">Perf:</span>
          <input
            type="text"
            v-model="store.student.globalPerfDate"
            placeholder="DD/MM/YYYY"
            class="w-full bg-transparent text-xs font-mono text-white outline-none"
          />
        </div>
        <div class="flex items-center gap-1.5 bg-[#1c1c21] border border-[#27272a] px-2.5 py-1.5 rounded-lg">
          <span class="text-[10px] text-zinc-400 uppercase font-medium">Sub:</span>
          <input
            type="text"
            v-model="store.student.globalSubDate"
            placeholder="DD/MM/YYYY"
            class="w-full bg-transparent text-xs font-mono text-white outline-none"
          />
        </div>
      </div>
    </div>

    <!-- Document Formatting Toggles -->
    <div class="border-t border-[#27272a] pt-3 grid grid-cols-2 gap-2 text-xs">
      <label class="flex items-center gap-2 cursor-pointer select-none bg-[#1c1c21]/50 hover:bg-[#1c1c21] border border-[#27272a] rounded-lg p-2 transition">
        <input
          type="checkbox"
          v-model="store.student.strikethrough"
          class="rounded bg-[#1c1c21] border-[#27272a] text-white cursor-pointer"
        />
        <span class="text-zinc-300 text-[11px]">Strikethrough Line</span>
      </label>

      <label class="flex items-center gap-2 cursor-pointer select-none bg-[#1c1c21]/50 hover:bg-[#1c1c21] border border-[#27272a] rounded-lg p-2 transition">
        <input
          type="checkbox"
          v-model="store.student.includeToc"
          class="rounded bg-[#1c1c21] border-[#27272a] text-white cursor-pointer"
        />
        <span class="text-zinc-300 text-[11px]">Generate Index Sheet</span>
      </label>
    </div>
  </div>
</template>
