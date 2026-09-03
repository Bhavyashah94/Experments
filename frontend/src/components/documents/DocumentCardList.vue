<script setup lang="ts">
import { ref, watch, nextTick, onMounted, onUnmounted } from 'vue';
import { useDocumentStore } from '@/stores/useDocumentStore';
import type { DocumentItem } from '@/types/document';
import Sortable from 'sortablejs';
import DocumentCardItem from './DocumentCardItem.vue';
import {
  Plus,
  ChevronsUpDown,
  Trash2,
  Layers,
  FileText,
  ListOrdered,
} from 'lucide-vue-next';

const emit = defineEmits<{
  (e: 'preview', doc: DocumentItem): void;
}>();

const documentStore = useDocumentStore();
const listRef = ref<HTMLElement | null>(null);
let sortableInstance: Sortable | null = null;

function initSortable() {
  if (sortableInstance) {
    sortableInstance.destroy();
    sortableInstance = null;
  }
  if (listRef.value) {
    sortableInstance = Sortable.create(listRef.value, {
      handle: '.drag-handle',
      animation: 200,
      ghostClass: 'opacity-40',
      chosenClass: 'scale-[1.01]',
      dragClass: 'shadow-2xl',
      fallbackOnBody: true,
      swapThreshold: 0.65,
      onEnd: (evt) => {
        if (
          evt.oldIndex !== undefined &&
          evt.newIndex !== undefined &&
          evt.oldIndex !== evt.newIndex
        ) {
          const item = documentStore.documents.splice(evt.oldIndex, 1)[0];
          documentStore.documents.splice(evt.newIndex, 0, item);
        }
      },
    });
  }
}

watch(
  () => documentStore.documents.length,
  async (len) => {
    if (len > 0) {
      await nextTick();
      initSortable();
    } else if (sortableInstance) {
      sortableInstance.destroy();
      sortableInstance = null;
    }
  },
  { immediate: true }
);

onMounted(async () => {
  await nextTick();
  if (documentStore.documents.length > 0) {
    initSortable();
  }
});

onUnmounted(() => {
  if (sortableInstance) {
    sortableInstance.destroy();
    sortableInstance = null;
  }
});

function handleMoveUp(idx: number) {
  if (idx > 0) {
    const item = documentStore.documents.splice(idx, 1)[0];
    documentStore.documents.splice(idx - 1, 0, item);
  }
}

function handleMoveDown(idx: number) {
  if (idx < documentStore.documents.length - 1) {
    const item = documentStore.documents.splice(idx, 1)[0];
    documentStore.documents.splice(idx + 1, 0, item);
  }
}
</script>

<template>
  <div class="space-y-4">
    <!-- List Controls Toolbar -->
    <div class="flex flex-wrap items-start justify-between gap-3">
      <div class="space-y-1">
        <div class="flex items-center gap-2">
          <div class="w-6 h-6 rounded-md bg-inputBg border border-border flex items-center justify-center text-zinc-400">
            <Layers class="w-3.5 h-3.5" />
          </div>
          <h3 class="text-xs font-semibold text-white tracking-wide">
            Experiment Documents ({{ documentStore.documents.length }})
          </h3>
        </div>
        <p class="text-[11px] text-zinc-400 pl-8">
          Reorder cards using drag handle or arrow buttons before compilation.
        </p>
      </div>

      <div class="flex flex-wrap items-center gap-2">
        <div class="w-6 h-6 rounded-md bg-inputBg border border-border flex items-center justify-center text-zinc-400">
          <ListOrdered class="w-3.5 h-3.5" />
        </div>
        <button
          type="button"
          @click="documentStore.renumberDocuments()"
          :disabled="documentStore.documents.length === 0"
          class="inline-flex items-center gap-1 text-xs text-zinc-400 hover:text-white bg-inputBg border border-border hover:border-zinc-500 px-2.5 py-1.5 rounded-lg transition disabled:opacity-40 disabled:pointer-events-none"
          title="Renumber cards sequentially (1..N)"
        >
          <span>Renumber 1..N</span>
        </button>

        <button
          type="button"
          @click="documentStore.toggleAllCards()"
          :disabled="documentStore.documents.length === 0"
          class="inline-flex items-center gap-1 text-xs text-zinc-400 hover:text-white bg-inputBg border border-border hover:border-zinc-500 px-2.5 py-1.5 rounded-lg transition disabled:opacity-40 disabled:pointer-events-none"
          title="Toggle expand / collapse for all document cards"
        >
          <ChevronsUpDown class="w-3.5 h-3.5" />
          <span>Toggle All</span>
        </button>

        <button
          type="button"
          @click="documentStore.clearAllDocuments"
          :disabled="documentStore.documents.length === 0"
          class="inline-flex items-center gap-1 text-xs text-zinc-500 hover:text-red-400 bg-inputBg border border-border hover:border-red-900/50 px-2.5 py-1.5 rounded-lg transition disabled:opacity-40 disabled:pointer-events-none"
          title="Clear all cards"
        >
          <Trash2 class="w-3.5 h-3.5" />
          <span>Clear All</span>
        </button>

        <button
          type="button"
          @click="documentStore.addDocument()"
          class="inline-flex items-center gap-1.5 text-xs font-semibold bg-white hover:bg-zinc-200 text-black px-3 py-1.5 rounded-lg transition shadow-sm"
        >
          <Plus class="w-3.5 h-3.5" />
          <span>Add Card</span>
        </button>
      </div>
    </div>

    <!-- Empty State Prompt -->
    <div
      v-if="documentStore.documents.length === 0"
      class="bg-card/50 border border-dashed border-border rounded-xl p-8 text-center space-y-3"
    >
      <div class="w-10 h-10 rounded-full bg-inputBg border border-border flex items-center justify-center mx-auto text-zinc-500">
        <FileText class="w-5 h-5" />
      </div>
      <div>
        <p class="text-xs font-semibold text-white">No document cards</p>
        <p class="text-[11px] text-muted mt-0.5">Drop PDFs in the upload box on the left or click Add Card to create one.</p>
        <p class="text-[11px] text-zinc-500 mt-1">Tip: upload in batch first, then fine-tune titles and dates in each card.</p>
      </div>
      <button
        type="button"
        @click="documentStore.addDocument()"
        class="inline-flex items-center gap-1.5 text-xs font-semibold bg-white hover:bg-zinc-200 text-black px-3.5 py-1.5 rounded-lg transition shadow-sm"
      >
        <Plus class="w-3.5 h-3.5" />
        <span>Add First Card</span>
      </button>
    </div>

    <!-- Reorderable Draggable Cards List -->
    <div v-else ref="listRef" class="space-y-3">
      <DocumentCardItem
        v-for="(doc, idx) in documentStore.documents"
        :key="doc.id"
        :doc="doc"
        :index="idx"
        :total="documentStore.documents.length"
        @preview="emit('preview', doc)"
        @move-up="handleMoveUp"
        @move-down="handleMoveDown"
      />
    </div>
  </div>
</template>
