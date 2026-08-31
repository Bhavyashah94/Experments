<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue';
import { useProfileStore } from '@/stores/useProfileStore';
import { useDocumentStore } from '@/stores/useDocumentStore';
import {
  X,
  Share2,
  Copy,
  Check,
  Download,
  Upload,
  FileJson,
  Users,
} from 'lucide-vue-next';

const props = defineProps<{
  isOpen: boolean;
}>();

const emit = defineEmits<{
  (e: 'close'): void;
  (e: 'toast', message: string): void;
}>();

const profileStore = useProfileStore();
const documentStore = useDocumentStore();

const activeTab = ref<'export' | 'import'>('export');
const copied = ref(false);
const importInput = ref('');
const importError = ref('');

const jsonContent = computed(() => {
  if (!props.isOpen) return '';
  return profileStore.exportProfilePackage();
});

watch(
  () => props.isOpen,
  (open) => {
    if (open) {
      copied.value = false;
      importInput.value = '';
      importError.value = '';
    }
  }
);

async function handleCopy() {
  try {
    await navigator.clipboard.writeText(jsonContent.value);
    copied.value = true;
    emit('toast', 'Profile JSON copied to clipboard!');
    setTimeout(() => {
      copied.value = false;
    }, 2500);
  } catch {
    emit('toast', 'Could not copy to clipboard.');
  }
}

function handleDownloadJson() {
  const blob = new Blob([jsonContent.value], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  const subj = profileStore.activeProfile.subject || profileStore.activeProfile.name;
  const safeName = subj.replace(/[^\w\-]/g, '_') || 'Subject_Profile';
  a.href = url;
  a.download = `${safeName}.labstudio.json`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
  emit('toast', `Downloaded ${safeName}.labstudio.json`);
}

function handleFileUpload(e: Event) {
  const input = e.target as HTMLInputElement;
  if (!input.files || input.files.length === 0) return;
  const file = input.files[0];
  const reader = new FileReader();
  reader.onload = (evt) => {
    const text = evt.target?.result as string;
    if (text) {
      importInput.value = text;
      handleDoImport();
    }
  };
  reader.readAsText(file);
}

function handleDoImport() {
  importError.value = '';
  if (!importInput.value.trim()) {
    importError.value = 'Please paste profile JSON or upload a file.';
    return;
  }

  const res = profileStore.importProfilePackage(importInput.value.trim());
  if (res.success) {
    documentStore.loadProfileDocuments(profileStore.activeProfileId);
    emit('toast', `Imported "${res.profileName}" with ${res.count} experiment(s)!`);
    emit('close');
  } else {
    importError.value = res.error || 'Failed to import profile.';
  }
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape' && props.isOpen) {
    emit('close');
  }
}

onMounted(() => {
  window.addEventListener('keydown', handleKeydown);
});

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown);
});
</script>

<template>
  <div
    v-if="isOpen"
    class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-150"
    @click.self="emit('close')"
  >
    <div class="bg-card border border-border rounded-2xl w-full max-w-xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
      <!-- Header -->
      <div class="flex items-center justify-between px-5 py-4 border-b border-border">
        <div class="flex items-center gap-2.5">
          <div class="w-8 h-8 rounded-lg bg-inputBg border border-border flex items-center justify-center text-zinc-300">
            <Users class="w-4 h-4" />
          </div>
          <div>
            <h2 class="text-sm font-bold text-white tracking-tight">Share Subject Profile</h2>
            <p class="text-[11px] text-muted">Share experiment titles &amp; dates with your classmates in 1 click</p>
          </div>
        </div>

        <button
          type="button"
          @click="emit('close')"
          class="text-muted hover:text-white p-1 rounded-lg hover:bg-zinc-800 transition"
        >
          <X class="w-4 h-4" />
        </button>
      </div>

      <!-- Tab Buttons -->
      <div class="flex border-b border-border bg-inputBg/40 px-5 pt-2 gap-4 text-xs font-semibold">
        <button
          type="button"
          @click="activeTab = 'export'"
          class="pb-2.5 border-b-2 transition flex items-center gap-1.5"
          :class="activeTab === 'export' ? 'border-white text-white' : 'border-transparent text-muted hover:text-zinc-300'"
        >
          <Share2 class="w-3.5 h-3.5" />
          <span>Export / Share</span>
        </button>

        <button
          type="button"
          @click="activeTab = 'import'"
          class="pb-2.5 border-b-2 transition flex items-center gap-1.5"
          :class="activeTab === 'import' ? 'border-white text-white' : 'border-transparent text-muted hover:text-zinc-300'"
        >
          <Upload class="w-3.5 h-3.5" />
          <span>Import Class Profile</span>
        </button>
      </div>

      <!-- Modal Body -->
      <div class="p-5 overflow-y-auto flex-1 space-y-4 text-xs">
        <!-- EXPORT TAB -->
        <div v-if="activeTab === 'export'" class="space-y-4">
          <div class="bg-inputBg/60 border border-border/80 rounded-xl p-3.5 text-zinc-300 space-y-1">
            <p class="font-semibold text-white">Ready to share "{{ profileStore.activeProfile.name }}"</p>
            <p class="text-[11px] text-muted">
              Only subject details, experiment aims, and dates are shared. Your personal Name and Roll Number are kept private.
            </p>
          </div>

          <div class="space-y-1.5">
            <div class="flex items-center justify-between text-[11px] text-muted">
              <span>Profile JSON Data</span>
              <span>{{ documentStore.documents.length }} experiment(s)</span>
            </div>
            <textarea
              readonly
              :value="jsonContent"
              rows="7"
              class="w-full bg-surface border border-border rounded-xl p-3 text-[11px] font-mono text-zinc-300 select-all outline-none resize-none"
            ></textarea>
          </div>

          <div class="flex items-center justify-end gap-2.5 pt-2">
            <button
              type="button"
              @click="handleCopy"
              class="inline-flex items-center gap-1.5 bg-inputBg hover:bg-zinc-800 border border-border hover:border-zinc-500 text-white font-medium px-3.5 py-2 rounded-xl transition"
            >
              <Check v-if="copied" class="w-3.5 h-3.5 text-emerald-400" />
              <Copy v-else class="w-3.5 h-3.5" />
              <span>{{ copied ? 'Copied to Clipboard!' : 'Copy JSON' }}</span>
            </button>

            <button
              type="button"
              @click="handleDownloadJson"
              class="inline-flex items-center gap-1.5 bg-white hover:bg-zinc-200 text-black font-semibold px-4 py-2 rounded-xl transition shadow-sm"
            >
              <Download class="w-3.5 h-3.5" />
              <span>Download .json File</span>
            </button>
          </div>
        </div>

        <!-- IMPORT TAB -->
        <div v-else class="space-y-4">
          <div class="bg-inputBg/60 border border-border/80 rounded-xl p-3.5 text-zinc-300 space-y-1">
            <p class="font-semibold text-white">Load a Classmate's Profile</p>
            <p class="text-[11px] text-muted">
              Paste the JSON shared by your classmate or upload a <code class="text-zinc-200">.json</code> file to import all experiment titles and dates.
            </p>
          </div>

          <!-- File Upload Dropzone -->
          <label class="block border border-dashed border-border hover:border-zinc-400 bg-surface/40 hover:bg-inputBg rounded-xl p-4 text-center cursor-pointer transition">
            <input type="file" accept=".json,application/json" class="hidden" @change="handleFileUpload" />
            <FileJson class="w-6 h-6 mx-auto text-zinc-400 mb-1.5" />
            <p class="text-xs font-semibold text-white">Upload .json file</p>
            <p class="text-[10px] text-muted">or paste the JSON text below</p>
          </label>

          <div class="space-y-1.5">
            <label class="block text-[11px] text-muted font-medium uppercase tracking-wider">Paste JSON</label>
            <textarea
              v-model="importInput"
              placeholder="Paste the shared profile JSON here..."
              rows="5"
              class="w-full bg-surface border border-border rounded-xl p-3 text-xs font-mono text-white outline-none focus:border-zinc-400 resize-none"
            ></textarea>
          </div>

          <div v-if="importError" class="text-xs text-red-400 font-medium">
            {{ importError }}
          </div>

          <div class="flex items-center justify-end gap-2.5 pt-2">
            <button
              type="button"
              @click="emit('close')"
              class="text-xs text-muted hover:text-white px-3 py-2 rounded-xl transition"
            >
              Cancel
            </button>

            <button
              type="button"
              @click="handleDoImport"
              class="inline-flex items-center gap-1.5 bg-white hover:bg-zinc-200 text-black font-semibold px-4 py-2 rounded-xl transition shadow-sm"
            >
              <Upload class="w-3.5 h-3.5" />
              <span>Import Profile</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
