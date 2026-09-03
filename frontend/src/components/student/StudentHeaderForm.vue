<script setup lang="ts">
import { ref } from 'vue';
import { useStudentStore } from '@/stores/useStudentStore';
import { useProfileStore } from '@/stores/useProfileStore';
import ProfileShareModal from '@/components/modals/ProfileShareModal.vue';
import { Plus, Trash2, Share2 } from 'lucide-vue-next';

const emit = defineEmits<{
  (e: 'toast', message: string): void;
}>();

const studentStore = useStudentStore();
const profileStore = useProfileStore();

const newProfileName = ref('');
const isAddingProfile = ref(false);
const isShareOpen = ref(false);

function handleCreateProfile() {
  if (newProfileName.value.trim()) {
    profileStore.addProfile(newProfileName.value.trim());
    newProfileName.value = '';
    isAddingProfile.value = false;
  }
}
</script>

<template>
  <div class="bg-card border border-border rounded-xl p-4 sm:p-5 space-y-4 shadow-sm">
    <!-- Profile Row -->
    <div class="flex items-center justify-between gap-2 border-b border-border pb-3">
      <div class="flex items-center gap-2">
        <span class="text-xs font-semibold text-muted uppercase tracking-wider">Subject Profile:</span>
        <select
          v-model="profileStore.activeProfileId"
          class="bg-inputBg border border-border rounded-lg px-2.5 py-1 text-xs text-white font-medium outline-none focus:border-zinc-400 cursor-pointer transition"
        >
          <option v-for="p in profileStore.profiles" :key="p.id" :value="p.id">
            {{ p.name }}
          </option>
        </select>
      </div>

      <div class="flex items-center gap-1.5">
        <button
          type="button"
          @click="isShareOpen = true"
          class="inline-flex items-center gap-1 text-xs text-zinc-300 hover:text-white bg-inputBg border border-border hover:border-zinc-400 px-2.5 py-1 rounded-lg transition"
          title="Share / Import subject profile with classmates"
        >
          <Share2 class="w-3.5 h-3.5" />
          <span>Share</span>
        </button>

        <button
          type="button"
          @click="isAddingProfile = !isAddingProfile"
          class="inline-flex items-center gap-1 text-xs text-zinc-300 hover:text-white bg-inputBg border border-border hover:border-zinc-400 px-2.5 py-1 rounded-lg transition"
          title="Add new subject profile"
        >
          <Plus class="w-3.5 h-3.5" />
          <span>New</span>
        </button>

        <button
          v-if="profileStore.profiles.length > 1"
          type="button"
          @click="profileStore.deleteProfile(profileStore.activeProfileId)"
          class="p-1 text-zinc-500 hover:text-red-400 bg-inputBg border border-border hover:border-red-900/50 rounded-lg transition"
          title="Delete current profile"
        >
          <Trash2 class="w-3.5 h-3.5" />
        </button>
      </div>
    </div>

    <!-- Add Profile Input Popover -->
    <div v-if="isAddingProfile" class="flex items-center gap-2 bg-inputBg/80 p-3 rounded-lg border border-border">
      <input
        type="text"
        v-model="newProfileName"
        placeholder="Enter subject profile name (e.g. IoT Lab, Cloud)"
        class="flex-1 bg-surface border border-border text-xs text-white rounded-lg px-3 py-1.5 outline-none focus:border-zinc-400"
        @keyup.enter="handleCreateProfile"
      />
      <button
        type="button"
        @click="handleCreateProfile"
        class="text-xs bg-white text-black font-semibold px-3 py-1.5 rounded-lg hover:bg-zinc-200 transition"
      >
        Save
      </button>
      <button
        type="button"
        @click="isAddingProfile = false"
        class="text-xs text-muted hover:text-white px-2 py-1.5"
      >
        Cancel
      </button>
    </div>

    <!-- Option Toggles (Responsive Grid) -->
    <div>
      <p class="text-[11px] font-semibold text-zinc-300 uppercase tracking-wider mb-2">Header options</p>
      <div class="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-2.5 pt-0.5 text-xs">
      <label class="flex items-center gap-2 cursor-pointer select-none bg-inputBg/40 hover:bg-inputBg/80 border border-border/60 rounded-lg p-2 transition">
        <input
          type="checkbox"
          v-model="profileStore.activeProfile.strikethroughEnabled"
          class="rounded bg-inputBg border-border text-zinc-200 focus:ring-0 focus:ring-offset-0 cursor-pointer"
        />
        <span class="text-zinc-300 text-[11px] font-medium leading-tight">Strikethrough Exp/Assign</span>
      </label>

      <label class="flex items-center gap-2 cursor-pointer select-none bg-inputBg/40 hover:bg-inputBg/80 border border-border/60 rounded-lg p-2 transition">
        <input
          type="checkbox"
          v-model="profileStore.activeProfile.autoAim"
          class="rounded bg-inputBg border-border text-zinc-200 focus:ring-0 focus:ring-offset-0 cursor-pointer"
        />
        <span class="text-zinc-300 text-[11px] font-medium leading-tight">Auto-Detect Aim</span>
      </label>

      <label class="flex items-center gap-2 cursor-pointer select-none bg-inputBg/40 hover:bg-inputBg/80 border border-border/60 rounded-lg p-2 transition">
        <input
          type="checkbox"
          v-model="profileStore.activeProfile.includeToc"
          class="rounded bg-inputBg border-border text-zinc-200 focus:ring-0 focus:ring-offset-0 cursor-pointer"
        />
        <span class="text-zinc-300 text-[11px] font-medium leading-tight">Include Index (TOC)</span>
      </label>
      </div>
    </div>

    <!-- Student Metadata Form -->
    <div class="pt-1 border-t border-border/60">
      <p class="text-[11px] font-semibold text-zinc-300 uppercase tracking-wider mb-2">Student details</p>
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
      <div>
        <label class="block text-[11px] font-medium text-muted uppercase tracking-wider mb-1">Student Name</label>
        <input
          type="text"
          v-model="studentStore.info.name"
          placeholder="e.g. Bhavya Shah"
          class="w-full bg-inputBg border border-border text-xs text-white rounded-lg px-3 py-2 outline-none focus:border-zinc-400 transition"
        />
      </div>

      <div>
        <label class="block text-[11px] font-medium text-muted uppercase tracking-wider mb-1">Roll Number</label>
        <input
          type="text"
          v-model="studentStore.info.rollNo"
          placeholder="e.g. 34"
          class="w-full bg-inputBg border border-border text-xs text-white rounded-lg px-3 py-2 outline-none focus:border-zinc-400 transition"
        />
      </div>

      <div>
        <label class="block text-[11px] font-medium text-muted uppercase tracking-wider mb-1">Batch</label>
        <input
          type="text"
          v-model="studentStore.info.batch"
          placeholder="e.g. I3"
          class="w-full bg-inputBg border border-border text-xs text-white rounded-lg px-3 py-2 outline-none focus:border-zinc-400 transition"
        />
      </div>

      <div>
        <label class="block text-[11px] font-medium text-muted uppercase tracking-wider mb-1">Class / Division</label>
        <input
          type="text"
          v-model="studentStore.info.className"
          placeholder="e.g. BE IT"
          class="w-full bg-inputBg border border-border text-xs text-white rounded-lg px-3 py-2 outline-none focus:border-zinc-400 transition"
        />
      </div>

      <div>
        <label class="block text-[11px] font-medium text-muted uppercase tracking-wider mb-1">Semester</label>
        <input
          type="text"
          v-model="studentStore.info.sem"
          placeholder="e.g. VII"
          class="w-full bg-inputBg border border-border text-xs text-white rounded-lg px-3 py-2 outline-none focus:border-zinc-400 transition"
        />
      </div>

      <div>
        <label class="block text-[11px] font-medium text-muted uppercase tracking-wider mb-1">Subject</label>
        <input
          type="text"
          v-model="profileStore.activeProfile.subject"
          placeholder="e.g. Internet of Things"
          class="w-full bg-inputBg border border-border text-xs text-white rounded-lg px-3 py-2 outline-none focus:border-zinc-400 transition"
        />
      </div>
      </div>
    </div>

    <!-- Profile Share / Classmate Export Modal -->
    <ProfileShareModal
      :is-open="isShareOpen"
      @close="isShareOpen = false"
      @toast="(msg) => emit('toast', msg)"
    />
  </div>
</template>
