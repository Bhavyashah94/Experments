<script setup lang="ts">
import { ref, onUnmounted, watch, nextTick } from 'vue';
import type { DocumentItem } from '@/types/document';
import { useStudentStore } from '@/stores/useStudentStore';
import { useProfileStore } from '@/stores/useProfileStore';
import { PdfPreviewEngine, type PreviewData } from '@/services/pdfPreview';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { ZoomIn, ZoomOut, RotateCcw, Loader2 } from 'lucide-vue-next';

const props = defineProps<{
  isOpen: boolean;
  doc: DocumentItem | null;
}>();

const emit = defineEmits<{
  (e: 'close'): void;
}>();

const studentStore = useStudentStore();
const profileStore = useProfileStore();

const canvasRef = ref<HTMLCanvasElement | null>(null);
const isLoading = ref<boolean>(false);
const zoomScale = ref<number>(1.3);

let engine: PdfPreviewEngine | null = null;

async function renderCanvas() {
  if (!props.isOpen || !props.doc || !canvasRef.value) return;

  isLoading.value = true;
  if (!engine) {
    engine = new PdfPreviewEngine();
  }

  const previewData: PreviewData = {
    sem: studentStore.info.sem,
    className: studentStore.info.className,
    batch: studentStore.info.batch,
    rollNo: studentStore.info.rollNo,
    name: studentStore.info.name,
    subject: profileStore.activeProfile.subject,
    isAssignment: props.doc.isAssignment,
    expNo: props.doc.label,
    title: props.doc.title,
    perfDate: props.doc.perfDate || profileStore.activeProfile.globalPerfDate,
    subDate: props.doc.subDate || profileStore.activeProfile.globalSubDate,
    textColor: profileStore.activeProfile.textColor,
    strikethroughEnabled: profileStore.activeProfile.strikethroughEnabled,
  };

  try {
    await engine.renderPreview(canvasRef.value, previewData, zoomScale.value);
  } catch (err) {
    console.warn('Preview render notice:', err);
  } finally {
    isLoading.value = false;
  }
}

watch(
  () => props.isOpen,
  (val) => {
    if (val) {
      nextTick(() => {
        renderCanvas();
      });
    }
  }
);

watch(zoomScale, () => {
  renderCanvas();
});

onUnmounted(() => {
  if (engine) {
    engine.cleanup();
    engine = null;
  }
});
</script>

<template>
  <Dialog :open="isOpen" @update:open="(val) => !val && emit('close')">
    <DialogContent class="max-w-2xl w-full max-h-[90vh] flex flex-col p-0 overflow-hidden bg-card border-border">
      <DialogHeader class="px-5 py-3.5 border-b border-border flex flex-row items-center justify-between space-y-0">
        <div class="flex items-center gap-2">
          <span class="w-2 h-2 rounded-full bg-white animate-pulse"></span>
          <DialogTitle class="text-sm font-semibold text-white">
            Header Live Preview — {{ doc?.isAssignment ? 'Assignment' : 'Experiment' }} {{ doc?.label }}
          </DialogTitle>
          <DialogDescription class="sr-only">
            Instant client-side PDF.js canvas overlay preview
          </DialogDescription>
        </div>

        <div class="flex items-center gap-1.5 pr-6">
          <Button
            type="button"
            variant="ghost"
            size="icon-sm"
            @click="zoomScale = Math.max(0.8, zoomScale - 0.2)"
            title="Zoom out"
          >
            <ZoomOut class="w-4 h-4" />
          </Button>
          <span class="text-xs font-mono text-muted w-10 text-center">{{ Math.round(zoomScale * 100) }}%</span>
          <Button
            type="button"
            variant="ghost"
            size="icon-sm"
            @click="zoomScale = Math.min(2.0, zoomScale + 0.2)"
            title="Zoom in"
          >
            <ZoomIn class="w-4 h-4" />
          </Button>
          <Button
            type="button"
            variant="ghost"
            size="icon-sm"
            @click="renderCanvas"
            title="Reload canvas"
          >
            <RotateCcw class="w-4 h-4" />
          </Button>
        </div>
      </DialogHeader>

      <div class="flex-1 overflow-auto p-4 flex items-center justify-center bg-surface relative min-h-[450px]">
        <div v-if="isLoading" class="absolute inset-0 flex items-center justify-center bg-surface/60 z-10">
          <Loader2 class="w-8 h-8 animate-spin text-white" />
        </div>
        <div class="shadow-2xl border border-zinc-800 rounded-sm overflow-hidden bg-white">
          <canvas ref="canvasRef"></canvas>
        </div>
      </div>

      <DialogFooter class="px-5 py-3 border-t border-border bg-card flex sm:items-center sm:justify-between text-xs text-muted">
        <span>Instant client-side PDF.js canvas overlay at 60 FPS</span>
        <Button
          type="button"
          variant="secondary"
          size="sm"
          @click="emit('close')"
        >
          Done
        </Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>
