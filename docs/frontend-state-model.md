# LabStudio Frontend State Model & Data Architecture

This document defines the exact state architecture for the LabStudio frontend, derived directly from the frozen backend API contract (`docs/frontend-api-contract.md`).

---

## 1. Separation of Concerns & State Ownership

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CLIENT-OWNED STATE (Durable)                      │
│ - Student Profile (Name, Roll, Batch, Class, Sem, Subject, Color, Strike)   │
│ - Experiment Queue (Order, Labels, Titles, Perf/Sub Dates, Override Flags)  │
│ - Persistence: LocalStorage (Auto-save on every edit)                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                           SERVER-OWNED STATE (Remote)                       │
│ - Content-addressed uploads: sha256 -> { pages, aim, exp_num, type }        │
│ - Backend Health & Quota metrics                                            │
│ - Compiled Job Deliverables: { job_id, combined_pdf, zip_package, files }   │
├─────────────────────────────────────────────────────────────────────────────┤
│                           DERIVED STATE (Computed / Pure)                   │
│ - Student Form Validity (all 6 compulsory fields non-empty)                 │
│ - Queue Validity (all items have title, label, and uploaded file)           │
│ - Ready for Compilation (studentValid && queueValid && items.length > 0)    │
│ - Total Output Pages = Sum(pages) + Count(items) + TOC_Pages                │
│ - TOC Page Count = (count <= 20) ? 1 : 1 + ceil((count - 20) / 24)          │
├─────────────────────────────────────────────────────────────────────────────┤
│                           TRANSIENT UI STATE (Volatile)                     │
│ - Drag & drop drag-over active state                                        │
│ - Upload progress & upload errors per queue row                             │
│ - Live preview debouncing & loading state (150ms debounce)                  │
│ - Live preview cached image data URL                                        │
│ - Compilation modal & download link ready states                            │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Client-Owned State Interfaces

### `StudentProfile`
Represents institutional identity.
```typescript
export interface StudentProfile {
  name: string;                   // Compulsory (e.g. "Bhavya Shah")
  roll_no: string;                // Compulsory (e.g. "77")
  batch: string;                  // Compulsory (e.g. "B3")
  class_name: string;             // Compulsory (e.g. "BE IT")
  sem: string;                    // Compulsory (e.g. "VIII")
  subject: string;                // Compulsory (e.g. "Internet of Things")
  text_color: string;             // Optional formatting, default: "#0000bf"
  strikethrough_enabled: boolean; // Optional formatting, default: true
  font_size?: number;             // Optional, default: 11
}
```

### `ExperimentQueueItem`
Represents an experiment or assignment in the queue.
```typescript
export interface ExperimentQueueItem {
  id: string;                     // Client-side UUID for stable v-for keying
  num: number;                    // 1-indexed sequential integer
  label: string;                  // Display label (e.g. "1", "2A", "Assignment 1")
  title: string;                  // Aim / Title of the experiment
  is_assignment: boolean;         // Distinguishes Experiment vs Assignment
  perf_date: string;              // Optional (e.g. "10/01/2026")
  sub_date: string;               // Optional (e.g. "17/01/2026")
  
  // File association & extraction metadata
  file_name?: string;             // Original user file name
  hash?: string;                  // 64-char SHA-256 hex string
  pages: number;                  // Number of body pages (0 if unattached)
  file_exists: boolean;           // Verified present on server
  is_manually_edited: boolean;    // True if student modified auto-extracted title
}
```

---

## 3. Server-Owned State & API Cache

```typescript
export interface UploadCacheEntry {
  hash: string;
  size: number;
  pages: number;
  aim: string | null;
  exp_num: string | null;
  is_assignment: boolean;
  extraction_method: string;
  failure_reason: string;
}

export interface GenerationDeliverables {
  job_id: string;
  combined_pdf: string;          // Relative path: "job_xxx/Combined.pdf"
  zip_package: string;           // Relative path: "job_xxx/Package.zip"
  files: Array<{
    label: string;
    merged_pdf: string;          // Relative path: "job_xxx/Exp_1_with_Header.pdf"
  }>;
}

export interface SystemHealth {
  status: "ok" | "degraded";
  version: string;
  storage_percent_used: number;
}
```

---

## 4. Derived / Computed State Rules

1. **Student Validity**:
   ```typescript
   const isStudentValid = computed(() => {
     const s = student.value;
     return Boolean(
       s.name.trim() &&
       s.roll_no.trim() &&
       s.batch.trim() &&
       s.class_name.trim() &&
       s.sem.trim() &&
       s.subject.trim()
     );
   });
   ```
2. **Queue Completeness**:
   ```typescript
   const isQueueValid = computed(() => {
     if (experiments.value.length === 0) return false;
     if (experiments.value.length > 60) return false;
     return experiments.value.every(item => 
       item.title.trim() &&
       item.label.trim() &&
       item.hash &&
       item.hash.length === 64 &&
       item.pages > 0
     );
   });
   ```
3. **Table of Contents Page Count Calculation**:
   Matches exact backend layout logic in `lab_core/toc_engine.py`:
   ```typescript
   const tocPageCount = computed(() => {
     const n = experiments.value.length;
     if (n === 0) return 1;
     if (n <= 20) return 1;
     return 1 + Math.ceil((n - 20) / 24);
   });
   ```
4. **Estimated Total Pages**:
   ```typescript
   const totalOutputPages = computed(() => {
     const bodyPages = experiments.value.reduce((acc, curr) => acc + curr.pages, 0);
     const headerPages = experiments.value.length;
     return bodyPages + headerPages + tocPageCount.value;
   });
   ```

---

## 5. Transient UI State

```typescript
export interface UIState {
  is_uploading: boolean;
  upload_progress: Record<string, number>; // id -> percentage
  is_preview_loading: boolean;
  preview_image_url: string | null;
  active_preview_index: number;            // 0-indexed row being inspected
  is_generating: boolean;
  generation_error: string | null;
  deliverables: GenerationDeliverables | null;
  drag_active: boolean;
}
```

---

## 6. Complete Data Transformation Mappings

### Client to `/api/preview` Payload Mapping
```typescript
function buildPreviewPayload(student: StudentProfile, item: ExperimentQueueItem) {
  return {
    student: {
      name: student.name,
      roll_no: student.roll_no,
      batch: student.batch,
      class_name: student.class_name,
      sem: student.sem,
      subject: student.subject,
      text_color: student.text_color,
      strikethrough_enabled: student.strikethrough_enabled,
    },
    item: {
      num: item.num,
      label: item.label,
      title: item.title,
      is_assignment: item.is_assignment,
      perf_date: item.perf_date,
      sub_date: item.sub_date,
    }
  };
}
```

### Client to `/api/generate` Payload Mapping
```typescript
function buildGeneratePayload(
  student: StudentProfile,
  experiments: ExperimentQueueItem[],
  include_toc = true
) {
  return {
    student: {
      name: student.name,
      roll_no: student.roll_no,
      batch: student.batch,
      class_name: student.class_name,
      sem: student.sem,
      subject: student.subject,
      text_color: student.text_color,
      strikethrough_enabled: student.strikethrough_enabled,
    },
    experiments: experiments.map(item => ({
      num: item.num,
      label: item.label,
      title: item.title,
      is_assignment: item.is_assignment,
      hash: item.hash!,
      pages: item.pages,
      perf_date: item.perf_date,
      sub_date: item.sub_date,
    })),
    formatting: {
      text_color: student.text_color,
      strikethrough_enabled: student.strikethrough_enabled,
      font_size: student.font_size ?? 11,
    },
    include_toc: include_toc,
  };
}
```
