import { defineStore } from 'pinia';
import { ref, watch } from 'vue';
import { useDebounceFn } from '@vueuse/core';
import type { DocumentItem } from '@/types/document';
import { useStudentStore } from './useStudentStore';
import { useProfileStore } from './useProfileStore';
import { ApiService } from '@/services/api';
import {
  safeLocalStorageGet,
  safeLocalStorageSet,
  STORAGE_KEYS,
} from '@/services/storage';

export const useDocumentStore = defineStore('documents', () => {
  const studentStore = useStudentStore();
  const profileStore = useProfileStore();

  const documents = ref<DocumentItem[]>([]);
  const isGenerating = ref(false);
  const isCompiled = ref(false);
  const lastZipPath = ref<string | null>(null);
  const lastCombinedPdfPath = ref<string | null>(null);
  const lastGeneratedFiles = ref<Array<{ label: string; merged_pdf: string }>>([]);

  function loadProfileDocuments(profileId: string): void {
    const key = `${STORAGE_KEYS.DOCUMENTS}_${profileId}`;
    const saved = safeLocalStorageGet<DocumentItem[] | null>(key, null);
    isCompiled.value = false;
    if (saved && Array.isArray(saved) && saved.length > 0) {
      documents.value = saved;
    } else {
      documents.value = [
        {
          id: `doc_${Date.now()}_${Math.random().toString(36).substr(2, 5)}`,
          label: '1',
          isAssignment: false,
          title: '',
          perfDate: '',
          subDate: '',
          hash: null,
          filename: null,
          pages: 0,
          isOpen: true,
          status: 'idle',
        },
      ];
    }
  }

  // Watch for active profile change to load its corresponding documents
  watch(
    () => profileStore.activeProfileId,
    (newId) => {
      if (newId) {
        loadProfileDocuments(newId);
      }
    },
    { immediate: true }
  );

  // Persist documents with 300ms debounce
  const persist = useDebounceFn(() => {
    if (profileStore.activeProfileId) {
      const key = `${STORAGE_KEYS.DOCUMENTS}_${profileStore.activeProfileId}`;
      safeLocalStorageSet(key, documents.value);
    }
  }, 300);

  watch(
    documents,
    () => {
      persist();
      isCompiled.value = false;
    },
    { deep: true }
  );

  function getNextLabel(): string {
    const maxNum = documents.value.reduce((max, d) => {
      const parsed = parseInt(d.label.replace(/\D/g, ''), 10);
      return isNaN(parsed) ? max : Math.max(max, parsed);
    }, 0);
    return String(maxNum + 1);
  }

  function addDocument(): DocumentItem {
    isCompiled.value = false;
    const newDoc: DocumentItem = {
      id: `doc_${Date.now()}_${Math.random().toString(36).substr(2, 5)}`,
      label: getNextLabel(),
      isAssignment: false,
      title: '',
      perfDate: profileStore.activeProfile.globalPerfDate || '',
      subDate: profileStore.activeProfile.globalSubDate || '',
      hash: null,
      filename: null,
      pages: 0,
      isOpen: true,
      status: 'idle',
    };
    documents.value.push(newDoc);
    return newDoc;
  }

  function removeDocument(id: string): void {
    isCompiled.value = false;
    const idx = documents.value.findIndex((d) => d.id === id);
    if (idx !== -1) {
      documents.value.splice(idx, 1);
    }
  }

  function clearAllDocuments(): void {
    isCompiled.value = false;
    documents.value = [];
  }

  function renumberDocuments(): void {
    isCompiled.value = false;
    documents.value.forEach((doc, idx) => {
      doc.label = String(idx + 1);
    });
  }

  function toggleAllCards(expand?: boolean): void {
    const targetState =
      expand !== undefined
        ? expand
        : !documents.value.every((d) => d.isOpen);
    documents.value.forEach((d) => {
      d.isOpen = targetState;
    });
  }

  function applyGlobalDates(): void {
    isCompiled.value = false;
    const pDate = profileStore.activeProfile.globalPerfDate;
    const sDate = profileStore.activeProfile.globalSubDate;
    documents.value.forEach((doc) => {
      if (pDate) doc.perfDate = pDate;
      if (sDate) doc.subDate = sDate;
    });
  }

  function applyWeeklyDates(): void {
    isCompiled.value = false;
    const pBase = profileStore.activeProfile.globalPerfDate;
    const sBase = profileStore.activeProfile.globalSubDate;
    if (!pBase && !sBase) return;

    function addDays(dateStr: string, daysToAdd: number): string {
      const parts = dateStr.split('/');
      if (parts.length !== 3) return dateStr;
      const day = parseInt(parts[0], 10);
      const month = parseInt(parts[1], 10) - 1;
      const year = parseInt(parts[2], 10);
      const d = new Date(year, month, day);
      if (isNaN(d.getTime())) return dateStr;
      d.setDate(d.getDate() + daysToAdd);
      const newD = String(d.getDate()).padStart(2, '0');
      const newM = String(d.getMonth() + 1).padStart(2, '0');
      const newY = d.getFullYear();
      return `${newD}/${newM}/${newY}`;
    }

    documents.value.forEach((doc, idx) => {
      if (pBase) doc.perfDate = addDays(pBase, idx * 7);
      if (sBase) doc.subDate = addDays(sBase, idx * 7);
    });
  }

  async function calculateSha256(file: File): Promise<string> {
    const buffer = await file.arrayBuffer();
    const hashBuffer = await crypto.subtle.digest('SHA-256', buffer);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    return hashArray.map((b) => b.toString(16).padStart(2, '0')).join('');
  }

  async function processFileUpload(docId: string, file: File): Promise<void> {
    const doc = documents.value.find((d) => d.id === docId);
    if (!doc) return;

    isCompiled.value = false;
    doc.status = 'uploading';
    doc.filename = file.name;
    doc.errorMessage = undefined;

    try {
      const hash = await calculateSha256(file);
      doc.hash = hash;

      // 1. Check if backend already has this file
      const existsCheck = await ApiService.checkFileExists(hash);
      if (existsCheck.exists) {
        doc.pages = existsCheck.pages || 1;
        doc.status = 'ready';
        if (profileStore.activeProfile.autoAim) {
          if (existsCheck.aim && !doc.title) doc.title = existsCheck.aim;
          if (existsCheck.exp_num) doc.label = existsCheck.exp_num;
          if (existsCheck.is_assignment !== null && existsCheck.is_assignment !== undefined) {
            doc.isAssignment = existsCheck.is_assignment;
          }
        }
        return;
      }

      // 2. Upload file to backend
      const uploadRes = await ApiService.uploadPdf(file, hash, 'auto');
      if (uploadRes.success) {
        doc.pages = uploadRes.pages || 1;
        doc.status = 'ready';
        if (profileStore.activeProfile.autoAim) {
          if (uploadRes.aim && !doc.title) doc.title = uploadRes.aim;
          if (uploadRes.exp_num) doc.label = uploadRes.exp_num;
          if (uploadRes.is_assignment !== null && uploadRes.is_assignment !== undefined) {
            doc.isAssignment = uploadRes.is_assignment;
          }
        }
      } else {
        doc.status = 'error';
        doc.errorMessage = uploadRes.error || 'Upload failed.';
      }
    } catch (err: any) {
      doc.status = 'error';
      doc.errorMessage = err.message || 'File processing failed.';
    }
  }

  async function processBulkUpload(files: FileList | File[]): Promise<void> {
    const fileArray = Array.from(files).filter((f) => f.name.toLowerCase().endsWith('.pdf'));
    if (fileArray.length === 0) return;

    isCompiled.value = false;
    for (const file of fileArray) {
      // Check if there's an existing empty card to reuse
      let targetDoc = documents.value.find((d) => !d.hash && !d.title);
      if (!targetDoc) {
        targetDoc = addDocument();
      }
      await processFileUpload(targetDoc.id, file);
    }
  }

  async function compileDocuments(includeTocOverride?: boolean): Promise<{ success: boolean; error?: string }> {
    if (documents.value.length === 0) {
      return { success: false, error: 'No experiment cards to compile.' };
    }

    isGenerating.value = true;
    try {
      const payload = {
        student: {
          name: studentStore.info.name,
          roll_no: studentStore.info.rollNo,
          batch: studentStore.info.batch,
          class_name: studentStore.info.className,
          sem: studentStore.info.sem,
          subject: profileStore.activeProfile.subject,
          text_color: profileStore.activeProfile.textColor,
          strikethrough_enabled: profileStore.activeProfile.strikethroughEnabled,
          perf_date: profileStore.activeProfile.globalPerfDate,
          sub_date: profileStore.activeProfile.globalSubDate,
        },
        experiments: documents.value.map((doc) => ({
          label: doc.label,
          is_assignment: doc.isAssignment,
          title: doc.title,
          perf_date: doc.perfDate,
          sub_date: doc.subDate,
          hash: doc.hash,
        })),
        formatting: {
          text_color: profileStore.activeProfile.textColor,
          strikethrough_enabled: profileStore.activeProfile.strikethroughEnabled,
        },
        include_toc: includeTocOverride !== undefined ? includeTocOverride : profileStore.activeProfile.includeToc,
      };

      const res = await ApiService.generateDocuments(payload);
      if (res.success && res.combined_pdf) {
        lastCombinedPdfPath.value = res.combined_pdf;
        lastZipPath.value = res.zip_package || null;
        lastGeneratedFiles.value = res.files || [];
        isCompiled.value = true;
        return { success: true };
      } else {
        return { success: false, error: res.error || 'Compilation failed.' };
      }
    } catch (e: any) {
      return { success: false, error: e.message || 'Request failed.' };
    } finally {
      isGenerating.value = false;
    }
  }

  // Alias for backward-compatibility
  const generateAll = compileDocuments;

  function downloadCombinedPdf(): boolean {
    if (!lastCombinedPdfPath.value) return false;
    const url = ApiService.getDownloadUrl(lastCombinedPdfPath.value);
    const link = document.createElement('a');
    link.href = url;
    link.download = lastCombinedPdfPath.value.split('/').pop() || 'Lab_Report_Combined.pdf';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    return true;
  }

  function downloadZipPackage(): boolean {
    if (!lastZipPath.value) return false;
    const url = ApiService.getDownloadUrl(lastZipPath.value);
    const link = document.createElement('a');
    link.href = url;
    link.download = lastZipPath.value.split('/').pop() || 'Lab_Report_Package.zip';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    return true;
  }

  async function downloadSingleDocument(doc: DocumentItem): Promise<void> {
    // Check if we already have this file in lastGeneratedFiles
    const existing = lastGeneratedFiles.value.find((f) => f.label === doc.label);
    if (existing) {
      const url = ApiService.getDownloadUrl(existing.merged_pdf);
      const link = document.createElement('a');
      link.href = url;
      link.download = existing.merged_pdf.split('/').pop() || `Exp_${doc.label}_with_Header.pdf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      return;
    }

    // Otherwise generate single document on-the-fly
    isGenerating.value = true;
    try {
      const payload = {
        student: {
          name: studentStore.info.name,
          roll_no: studentStore.info.rollNo,
          batch: studentStore.info.batch,
          class_name: studentStore.info.className,
          sem: studentStore.info.sem,
          subject: profileStore.activeProfile.subject,
          text_color: profileStore.activeProfile.textColor,
          strikethrough_enabled: profileStore.activeProfile.strikethroughEnabled,
          perf_date: doc.perfDate || profileStore.activeProfile.globalPerfDate,
          sub_date: doc.subDate || profileStore.activeProfile.globalSubDate,
        },
        experiments: [
          {
            label: doc.label,
            is_assignment: doc.isAssignment,
            title: doc.title,
            perf_date: doc.perfDate,
            sub_date: doc.subDate,
            hash: doc.hash,
          },
        ],
        formatting: {
          text_color: profileStore.activeProfile.textColor,
          strikethrough_enabled: profileStore.activeProfile.strikethroughEnabled,
        },
        include_toc: false,
      };

      const res = await ApiService.generateDocuments(payload);
      if (res.success && res.files && res.files.length > 0) {
        const fileRel = res.files[0].merged_pdf;
        const url = ApiService.getDownloadUrl(fileRel);
        const link = document.createElement('a');
        link.href = url;
        link.download = fileRel.split('/').pop() || `Exp_${doc.label}_with_Header.pdf`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
      }
    } finally {
      isGenerating.value = false;
    }
  }

  return {
    documents,
    isGenerating,
    isCompiled,
    lastZipPath,
    lastCombinedPdfPath,
    lastGeneratedFiles,
    loadProfileDocuments,
    addDocument,
    removeDocument,
    clearAllDocuments,
    renumberDocuments,
    toggleAllCards,
    applyGlobalDates,
    applyWeeklyDates,
    processFileUpload,
    processBulkUpload,
    compileDocuments,
    generateAll,
    downloadCombinedPdf,
    downloadZipPackage,
    downloadSingleDocument,
  };
});
