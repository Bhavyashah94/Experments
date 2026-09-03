import { defineStore } from 'pinia';
import { ref, computed, watch } from 'vue';
import type { StudentInfo, DocumentItem, SubjectProfile } from './types';
import { Api } from './api';

const STORAGE_STUDENT = 'labstudio_student_v3';
const STORAGE_PROFILES = 'labstudio_profiles_v3';
const STORAGE_DOCS = 'labstudio_docs_v3';

function load<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : fallback;
  } catch {
    return fallback;
  }
}

function save<T>(key: string, data: T) {
  try {
    localStorage.setItem(key, JSON.stringify(data));
  } catch {}
}

export const useLabStore = defineStore('lab', () => {
  // ── 1. Student Identity (6 Required Fields + Styling + Optional Dates) ──
  const student = ref<StudentInfo>(
    load<StudentInfo>(STORAGE_STUDENT, {
      name: '',
      rollNo: '',
      batch: '',
      className: '',
      sem: '',
      subject: '',
      textColor: '#0000bf',
      strikethrough: true,
      includeToc: true,
      globalPerfDate: '',
      globalSubDate: '',
    })
  );

  // ── 2. Subject Profiles ────────────────────────────────────────────────
  const profiles = ref<SubjectProfile[]>(
    load<SubjectProfile[]>(STORAGE_PROFILES, [
      {
        id: 'default',
        name: 'Default',
        subject: '',
        textColor: '#0000bf',
        strikethrough: true,
        includeToc: true,
      },
    ])
  );
  const activeProfileId = ref<string>('default');

  // ── 3. Document Queue ──────────────────────────────────────────────────
  const documents = ref<DocumentItem[]>(
    load<DocumentItem[]>(STORAGE_DOCS, [
      {
        id: 'doc_1',
        num: '1',
        title: '',
        isAssignment: false,
        perfDate: '',
        subDate: '',
        hash: null,
        filename: null,
        pages: 0,
        status: 'idle',
        errorMsg: null,
      },
    ])
  );

  // Selected document ID for the live preview inspector
  const selectedDocId = ref<string>(documents.value[0]?.id || '');

  const selectedDoc = computed(() => {
    return documents.value.find((d) => d.id === selectedDocId.value) || documents.value[0] || null;
  });

  // ── 4. Compilation State ───────────────────────────────────────────────
  const isCompiling = ref(false);
  const isCompiled = ref(false);
  const combinedPdfPath = ref<string | null>(null);
  const zipPath = ref<string | null>(null);

  // ── Auto-Persistence ───────────────────────────────────────────────────
  watch(student, (val) => save(STORAGE_STUDENT, val), { deep: true });
  watch(profiles, (val) => save(STORAGE_PROFILES, val), { deep: true });
  watch(
    documents,
    (val) => {
      save(STORAGE_DOCS, val);
      isCompiled.value = false;
    },
    { deep: true }
  );

  // ── 5. Validation Rules (Strict Compulsory vs Strictly Optional Dates) ──
  const missingStudentFields = computed<string[]>(() => {
    const missing: string[] = [];
    if (!student.value.name.trim()) missing.push('Name');
    if (!student.value.rollNo.trim()) missing.push('Roll No');
    if (!student.value.batch.trim()) missing.push('Batch');
    if (!student.value.className.trim()) missing.push('Class');
    if (!student.value.sem.trim()) missing.push('Semester');
    if (!student.value.subject.trim()) missing.push('Subject');
    return missing;
  });

  const isStudentComplete = computed(() => missingStudentFields.value.length === 0);

  const missingDocTitles = computed<number>(() => {
    return documents.value.filter((d) => !d.title || !d.title.trim()).length;
  });

  const totalPages = computed(() => {
    return documents.value.reduce((acc, d) => acc + (d.pages || 0), 0);
  });

  const canCompile = computed<boolean>(() => {
    return (
      documents.value.length > 0 &&
      missingStudentFields.value.length === 0 &&
      missingDocTitles.value === 0
    );
  });

  const compileStatusText = computed<string>(() => {
    if (documents.value.length === 0) {
      return 'Add experiment files to compile';
    }
    if (missingStudentFields.value.length > 0) {
      if (missingStudentFields.value.length === 1) {
        return `Enter ${missingStudentFields.value[0]} to compile`;
      }
      return `Complete ${missingStudentFields.value.length} required fields to compile`;
    }
    if (missingDocTitles.value > 0) {
      return `Enter title for all ${documents.value.length} experiments`;
    }
    return `Compile Lab Report (${documents.value.length} ${documents.value.length === 1 ? 'doc' : 'docs'})`;
  });

  // ── 6. Document Actions ────────────────────────────────────────────────
  function addDocument(): DocumentItem {
    const nextNum = String(documents.value.length + 1);
    const newDoc: DocumentItem = {
      id: `doc_${Date.now()}_${Math.random().toString(36).substring(2, 6)}`,
      num: nextNum,
      title: '',
      isAssignment: false,
      perfDate: student.value.globalPerfDate || '',
      subDate: student.value.globalSubDate || '',
      hash: null,
      filename: null,
      pages: 0,
      status: 'idle',
      errorMsg: null,
    };
    documents.value.push(newDoc);
    selectedDocId.value = newDoc.id;
    return newDoc;
  }

  function removeDocument(id: string) {
    if (documents.value.length <= 1) {
      // Reset the single remaining row instead of leaving empty
      documents.value = [
        {
          id: `doc_${Date.now()}`,
          num: '1',
          title: '',
          isAssignment: false,
          perfDate: '',
          subDate: '',
          hash: null,
          filename: null,
          pages: 0,
          status: 'idle',
          errorMsg: null,
        },
      ];
      selectedDocId.value = documents.value[0].id;
      return;
    }
    const idx = documents.value.findIndex((d) => d.id === id);
    if (idx !== -1) {
      documents.value.splice(idx, 1);
      renumber();
      if (selectedDocId.value === id) {
        selectedDocId.value = documents.value[0]?.id || '';
      }
    }
  }

  function renumber() {
    documents.value.forEach((doc, i) => {
      doc.num = String(i + 1);
    });
  }

  function reorder(fromIndex: number, toIndex: number) {
    if (fromIndex < 0 || fromIndex >= documents.value.length) return;
    if (toIndex < 0 || toIndex >= documents.value.length) return;
    const [moved] = documents.value.splice(fromIndex, 1);
    documents.value.splice(toIndex, 0, moved);
    renumber();
  }

  // ── Date Automation (+7 Days Weekly Ripple) ────────────────────────────
  function applyGlobalDates() {
    documents.value.forEach((d) => {
      if (student.value.globalPerfDate) d.perfDate = student.value.globalPerfDate;
      if (student.value.globalSubDate) d.subDate = student.value.globalSubDate;
    });
  }

  function parseDate(str: string): Date | null {
    if (!str) return null;
    const parts = str.split(/[-/.]/);
    if (parts.length === 3) {
      const d = parseInt(parts[0], 10);
      const m = parseInt(parts[1], 10) - 1;
      const y = parseInt(parts[2], 10);
      const date = new Date(y < 100 ? y + 2000 : y, m, d);
      if (!isNaN(date.getTime())) return date;
    }
    return null;
  }

  function formatDate(d: Date): string {
    const day = String(d.getDate()).padStart(2, '0');
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const year = d.getFullYear();
    return `${day}/${month}/${year}`;
  }

  function applyWeeklyDates() {
    const basePerf = parseDate(student.value.globalPerfDate || documents.value[0]?.perfDate);
    const baseSub = parseDate(student.value.globalSubDate || documents.value[0]?.subDate);

    documents.value.forEach((doc, idx) => {
      if (basePerf) {
        const next = new Date(basePerf);
        next.setDate(basePerf.getDate() + idx * 7);
        doc.perfDate = formatDate(next);
      }
      if (baseSub) {
        const next = new Date(baseSub);
        next.setDate(baseSub.getDate() + idx * 7);
        doc.subDate = formatDate(next);
      }
    });
  }

  // ── Ingestion Engine (Single & Bulk PDF Upload) ─────────────────────────
  async function uploadFile(docId: string, file: File) {
    const doc = documents.value.find((d) => d.id === docId);
    if (!doc) return;

    doc.status = 'uploading';
    doc.errorMsg = null;
    try {
      const res = await Api.uploadPdf(file);
      if (res.success && res.hash) {
        doc.hash = res.hash;
        doc.filename = res.filename || file.name;
        doc.pages = res.pages || 0;
        doc.status = 'ready';

        if (res.extracted) {
          if (res.extracted.aim && !doc.title) {
            doc.title = res.extracted.aim;
          }
          if (res.extracted.experiment_number) {
            doc.num = res.extracted.experiment_number;
          }
          if (res.extracted.is_assignment !== undefined) {
            doc.isAssignment = res.extracted.is_assignment;
          }
        }
      } else {
        doc.status = 'error';
        doc.errorMsg = res.error || 'Upload failed';
      }
    } catch (e: any) {
      doc.status = 'error';
      doc.errorMsg = e.message || 'Network error';
    }
  }

  async function bulkUpload(files: FileList | File[]) {
    const fileList = Array.from(files).filter((f) => f.type === 'application/pdf' || f.name.endsWith('.pdf'));
    if (fileList.length === 0) return;

    for (const file of fileList) {
      // Find existing empty row or add a new one
      let target = documents.value.find((d) => !d.hash && !d.title);
      if (!target) {
        target = addDocument();
      }
      await uploadFile(target.id, file);
    }
  }

  // ── Profile Management ─────────────────────────────────────────────────
  function switchProfile(profileId: string) {
    const found = profiles.value.find((p) => p.id === profileId);
    if (found) {
      activeProfileId.value = found.id;
      student.value.subject = found.subject;
      student.value.textColor = found.textColor;
      student.value.strikethrough = found.strikethrough;
      student.value.includeToc = found.includeToc;
    }
  }

  function saveAsNewProfile(name: string) {
    const trimmed = name.trim();
    if (!trimmed) return;
    const newProfile: SubjectProfile = {
      id: `prof_${Date.now()}`,
      name: trimmed,
      subject: student.value.subject,
      textColor: student.value.textColor,
      strikethrough: student.value.strikethrough,
      includeToc: student.value.includeToc,
    };
    profiles.value.push(newProfile);
    activeProfileId.value = newProfile.id;
  }

  // ── 7. Compilation Action ──────────────────────────────────────────────
  async function compile(): Promise<{ success: boolean; error?: string }> {
    if (!canCompile.value) {
      return { success: false, error: compileStatusText.value };
    }

    isCompiling.value = true;
    try {
      const payload = {
        student: {
          name: student.value.name,
          roll_no: student.value.rollNo,
          batch: student.value.batch,
          class_name: student.value.className,
          sem: student.value.sem,
          subject: student.value.subject,
          text_color: student.value.textColor,
          strikethrough_enabled: student.value.strikethrough,
          perf_date: student.value.globalPerfDate,
          sub_date: student.value.globalSubDate,
        },
        experiments: documents.value.map((d) => ({
          label: d.num,
          is_assignment: d.isAssignment,
          title: d.title,
          perf_date: d.perfDate,
          sub_date: d.subDate,
          hash: d.hash,
        })),
        formatting: {
          text_color: student.value.textColor,
          strikethrough_enabled: student.value.strikethrough,
        },
        include_toc: student.value.includeToc,
      };

      const res = await Api.generate(payload);
      if (res.success && res.combined_pdf) {
        combinedPdfPath.value = res.combined_pdf;
        zipPath.value = res.zip_package || null;
        isCompiled.value = true;
        return { success: true };
      } else {
        return { success: false, error: res.error || 'Compilation failed' };
      }
    } catch (e: any) {
      return { success: false, error: e.message || 'Server error' };
    } finally {
      isCompiling.value = false;
    }
  }

  function downloadCombined() {
    if (!combinedPdfPath.value) return;
    const url = Api.getDownloadUrl(combinedPdfPath.value);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${student.value.rollNo || 'Report'}_${student.value.subject || 'Combined'}.pdf`;
    a.click();
  }

  function downloadZip() {
    if (!zipPath.value) return;
    const url = Api.getDownloadUrl(zipPath.value);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${student.value.rollNo || 'Report'}_${student.value.subject || 'Package'}.zip`;
    a.click();
  }

  return {
    student,
    profiles,
    activeProfileId,
    documents,
    selectedDocId,
    selectedDoc,
    isCompiling,
    isCompiled,
    combinedPdfPath,
    zipPath,
    missingStudentFields,
    isStudentComplete,
    missingDocTitles,
    totalPages,
    canCompile,
    compileStatusText,
    addDocument,
    removeDocument,
    renumber,
    reorder,
    applyGlobalDates,
    applyWeeklyDates,
    uploadFile,
    bulkUpload,
    switchProfile,
    saveAsNewProfile,
    compile,
    downloadCombined,
    downloadZip,
  };
});
