<script setup lang="ts">
import { ref, computed, watch } from 'vue';
import { useProfileStore } from '@/stores/useProfileStore';
import { useDocumentStore } from '@/stores/useDocumentStore';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import {
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
      activeTab.value = 'export';
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
</script>

<template>
  <Dialog :open="isOpen" @update:open="(val) => !val && emit('close')">
    <DialogContent class="max-w-xl w-full p-0 overflow-hidden bg-card border-border flex flex-col max-h-[90vh]">
      <!-- Header -->
      <DialogHeader class="px-5 py-4 border-b border-border flex flex-row items-center gap-2.5 space-y-0">
        <div class="w-8 h-8 rounded-lg bg-inputBg border border-border flex items-center justify-center text-zinc-300">
          <Users class="w-4 h-4" />
        </div>
        <div>
          <DialogTitle class="text-sm font-bold text-white tracking-tight">
            Share Subject Profile
          </DialogTitle>
          <DialogDescription class="text-[11px] text-muted mt-0.5">
            Share experiment titles &amp; dates with your classmates in 1 click
          </DialogDescription>
        </div>
      </DialogHeader>

      <Tabs v-model="activeTab" class="w-full flex flex-col flex-1">
        <!-- Tabs Header -->
        <div class="border-b border-border bg-inputBg/40 px-5 pt-2">
          <TabsList class="bg-transparent p-0 gap-4 h-auto">
            <TabsTrigger
              value="export"
              class="rounded-none border-b-2 border-transparent data-[state=active]:border-white data-[state=active]:bg-transparent data-[state=active]:text-white text-muted pb-2.5 px-1 font-semibold text-xs flex items-center gap-1.5 shadow-none"
            >
              <Share2 class="w-3.5 h-3.5" />
              <span>Export / Share</span>
            </TabsTrigger>

            <TabsTrigger
              value="import"
              class="rounded-none border-b-2 border-transparent data-[state=active]:border-white data-[state=active]:bg-transparent data-[state=active]:text-white text-muted pb-2.5 px-1 font-semibold text-xs flex items-center gap-1.5 shadow-none"
            >
              <Upload class="w-3.5 h-3.5" />
              <span>Import Class Profile</span>
            </TabsTrigger>
          </TabsList>
        </div>

        <!-- Tab Content -->
        <div class="p-5 overflow-y-auto flex-1 text-xs">
          <!-- EXPORT TAB -->
          <TabsContent value="export" class="space-y-4 mt-0">
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
              <Button
                type="button"
                variant="outline"
                size="sm"
                @click="handleCopy"
              >
                <Check v-if="copied" class="w-3.5 h-3.5 text-emerald-400" />
                <Copy v-else class="w-3.5 h-3.5" />
                <span>{{ copied ? 'Copied to Clipboard!' : 'Copy JSON' }}</span>
              </Button>

              <Button
                type="button"
                variant="default"
                size="sm"
                @click="handleDownloadJson"
              >
                <Download class="w-3.5 h-3.5" />
                <span>Download .json File</span>
              </Button>
            </div>
          </TabsContent>

          <!-- IMPORT TAB -->
          <TabsContent value="import" class="space-y-4 mt-0">
            <div class="bg-inputBg/60 border border-border/80 rounded-xl p-3.5 text-zinc-300 space-y-1">
              <p class="font-semibold text-white">Load a Classmate's Profile</p>
              <p class="text-[11px] text-muted">
                Paste the JSON shared by your classmate or upload a <code class="text-zinc-200">.json</code> file to import all experiment titles and dates.
              </p>
            </div>

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
              <Button
                type="button"
                variant="ghost"
                size="sm"
                @click="emit('close')"
              >
                Cancel
              </Button>

              <Button
                type="button"
                variant="default"
                size="sm"
                @click="handleDoImport"
              >
                <Upload class="w-3.5 h-3.5" />
                <span>Import Profile</span>
              </Button>
            </div>
          </TabsContent>
        </div>
      </Tabs>
    </DialogContent>
  </Dialog>
</template>
