# LabStudio Frontend Architecture Proposal & Technical Design

**Author**: Senior Software Architect & Pair Programmer  
**Status**: Proposal for Review (No implementation until approved)  
**Target Backend**: Frozen LabStudio Backend v3.0.0 (Oracle Cloud VM, 1 GB RAM, Gunicorn 2x4, SQLite WAL)

---

## 1. Observations About the Existing Project

1. **The Backend is Production-Proven**:
   * Benchmarked live on the 1 GB Oracle Cloud VM: 60 experiments (650 pages) compile in **20.64 seconds** and peak at **165.3 MB RSS**.
   * Multi-threaded Caddy + Gunicorn architecture handles concurrent generation and preview requests without queuing.
   * All API contracts and storage rotation rules are frozen and covered by 50 passing backend tests.
2. **The Previous Frontend Was Discarded For Good Reasons**:
   * It suffered from state fragmentation, bloated styling abstractions, and disconnect from the backend's real capabilities.
   * Wiping the slate clean allows building a tight, responsive, resilient single-page application.
3. **The Deployment Model is Single-Origin**:
   * Flask serves the production build directly from `frontend/dist/index.html` and `frontend/dist/assets/*`.
   * Static hashed assets receive 1-year immutable caching (`Cache-Control: public, max-age=31536000, immutable`), while `index.html` receives `no-cache, must-revalidate`.
   * This guarantees students always run the latest frontend code without browser cache friction.

---

## 2. Product Understanding & User Workflow

### What the Application Actually Does
In Indian engineering universities (Mumbai University, VTU, SPPU, etc.), students must submit standardized lab journals containing 10–25 individual experiment reports. Every experiment requires an institutional cover sheet stamped with student details, experiment number, title, and dates, followed by a dynamic vector Table of Contents with exact page numbers.

Doing this manually (Word copy-pasting, manual PDF merging, computing page numbers by hand) takes 2–3 hours per subject and is prone to formatting errors.

**LabStudio's core goal is to reduce this 2-hour chore to a 90-second, frictionless drag-and-drop batch process.**

### The Ideal User Workflow
```
[1. Open App] ──► [2. Student Setup] ──► [3. Drag & Drop PDFs] ──► [4. Automatic Extraction]
                         │                         │                         │
                 Auto-hydrated from        10–25 files dropped        Title & Exp # parsed
                 localStorage              at once into queue         instantly (<50ms/file)
                                                                             │
[7. Download ZIP/PDF] ◄── [6. One-Click Compile] ◄── [5. Live Inspector Review] ◄────┘
   Instant deliverable      20s max for 60 exps        150 DPI real-time A4 preview
   retrieval modal          Interactive bookmarks      Weekly dates rippled (+7 days)
```

---

## 3. Proposed Frontend Architecture

```
src/
├── api/
│   ├── client.ts              # Fetch wrapper with timeout, abort, and error normalization
│   └── endpoints.ts           # Strictly typed endpoint methods matching backend contract
├── components/
│   ├── common/                # Accessible micro-primitives (Button, Modal, Toast, Tooltip)
│   ├── queue/
│   │   ├── DocumentQueue.vue  # Master queue container with virtual scroll / sticky dropzone
│   │   ├── ExperimentCard.vue # Individual row: drag handle, title input, exp#, date, status
│   │   └── UploadDropzone.vue # Drag-and-drop target with click-to-browse fallback
│   ├── preview/
│   │   ├── LiveInspector.vue  # Sticky right-panel container with zoom and tab toggles
│   │   ├── CoverPreview.vue   # 150 DPI A4 rasterized cover sheet preview with debouncing
│   │   └── TocPreview.vue     # Client-rendered HTML Table of Contents index preview
│   └── student/
│       └── StudentSetup.vue   # 6 compulsory fields + text color and strike formatting
├── composables/
│   ├── useLabStore.ts         # Unified reactive state container with localStorage sync
│   ├── useUploadQueue.ts      # Concurrency-pooled (max 3) upload orchestrator
│   ├── usePreviewDebounce.ts  # 150ms debounced preview fetcher with memory cache
│   └── useCompileJob.ts       # Job compilation lifecycle, timer, and download triggers
├── types/
│   ├── api.ts                 # Backend request/response DTOs (from frontend-api-contract.md)
│   └── store.ts               # Client models (StudentProfile, ExperimentQueueItem, UIState)
├── App.vue                    # Responsive 3-Zone Workspace layout
└── main.ts                    # Application bootstrapper
```

### Core Architectural Decisions

#### A. State Management: Single Typed Composable (`useLabStore.ts`)
* **Decision**: Use a centralized, reactive composable using native Vue 3 `reactive` and `computed`, synchronized with `localStorage` via debounced `watch`.
* **Why NOT Pinia/Vuex?**: Pinia adds ~2.5 KB and extra ceremony (actions, state getters, store hydration plugins) for what is fundamentally a single-screen application with two entity types (`student` and `experiments`). A native composable provides 100% type inference, zero runtime dependencies, and trivial testability without store mocks.
* **Why NOT scattered component state?**: Scattered state leads to prop-drilling and desynchronization between the Document Queue, the Live Preview, and the Compilation trigger.

#### B. Ingestion Architecture: Client-Side SHA-256 & Concurrency Pool
* **Decision**:
  1. When files are dropped, immediately calculate SHA-256 in the browser via `crypto.subtle.digest('SHA-256', buffer)`.
  2. Ping `GET /api/file/<hash>/exists`. If the server already has the file (e.g. from an earlier session or duplicate upload), mark it uploaded in 5 ms **without sending the file across the network!**
  3. If un-cached, enqueue in `useUploadQueue` with a **maximum concurrency of 3 parallel uploads**.
* **Why?**: The backend rate limit is 40 uploads/minute. Firing 25 unthrottled uploads simultaneously risks HTTP 429 errors or saturating a student's uplink. A pool of 3 concurrent streams provides optimal throughput while remaining completely within server thresholds.

#### C. Live Preview Architecture: 150ms Debounced Canvas with In-Memory LRU Cache
* **Decision**:
  1. Debounce live preview calls by 150ms during student typing.
  2. Maintain an in-memory `Map<string, string>` keyed by `hash + student_name + roll + title + dates`.
  3. When the student clicks between experiment rows, **the preview displays instantly from memory cache** without hitting the backend.
  4. Display an in-flight loading overlay with `AbortController` to cancel stale render requests.

#### D. Compilation Progress: Stepped Authenticity, NOT Fake Progress Bars
* **Decision**: The backend `/api/generate` is an atomic, non-streaming operation that takes 0.5s to 20s. We will **never show fake percentage bars** (e.g. `10%... 45%... 85%`). Instead, show:
  * An animated indeterminate compilation spinner.
  * A clear active stage ticker:
    1. *Stamping Institutional Cover Sheets...*
    2. *Building Table of Contents & Clickable Bookmarks...*
    3. *Packaging Master Deliverables...*
  * An authentic elapsed timer (`3.4s elapsed`).

---

## 4. UX & Layout Architecture: The "Command Center" Workspace

We reject rigid step-by-step wizards. Document compilation is an iterative editing task; students need to see their student details, their document queue, and the live cover preview **simultaneously**.

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│  LABSTUDIO                                      [Auto-Saved ✓]  [Generate Journal 🚀] │
├─────────────────────────┬───────────────────────────────────────┬──────────────────────┤
│  STUDENT DETAILS (280px)│  DOCUMENT QUEUE (Flex-1)              │ LIVE INSPECTOR(380px)│
│                         │                                       │                      │
│  [Name*               ] │  ┌─────────────────────────────────┐ │  [Cover] [Index TOC] │
│  [Roll*] [Batch*      ] │  │ 📁 Drag & drop 10-25 PDFs here   │ │                      │
│  [Class*] [Sem*       ] │  └─────────────────────────────────┘ │  ┌──────────────────┐│
│  [Subject*            ] │                                       │  │ A4 PREVIEW       ││
│                         │  1. Exp 1: MQTT Client  [4 pgs] [🗑]  │  │ (150 DPI Render) ││
│  Formatting:            │  2. Exp 2: Socket Server [8 pgs] [🗑] │  │                  ││
│  Color: [ Blue ▾ ]      │  3. Assign 1: SQL Joins [6 pgs] [🗑] │  │ Exp 1: MQTT...   ││
│  [✓] Strike assignment  │                                       │  └──────────────────┘│
│                         │  [+ Add Experiment] [📅 Ripple Dates] │  Total: 28 pages     │
└─────────────────────────┴───────────────────────────────────────┴──────────────────────┘
```

### Responsive Adaptations
1. **Desktop ($\ge 1280\text{px}$)**: Full 3-column Command Center (Setup | Queue | Inspector).
2. **Tablet ($768\text{px} - 1279\text{px}$)**: 2-column layout. Student Setup collapses into a sticky drawer; Document Queue takes 60% and Live Inspector takes 40%.
3. **Mobile ($< 768\text{px}$)**: Single-column view with bottom navigation bar:
   * **Tab 1: Profile**: 6 compulsory fields.
   * **Tab 2: Queue**: Upload dropzone and experiment cards.
   * **Tab 3: Preview**: Full A4 pinch-to-zoom preview canvas and Table of Contents tab.
   * Sticky bottom bar: `Ready (12/12) — [Compile Journal]`.

---

## 5. State Persistence Architecture

### What Survives Browser Refresh (in `localStorage`)
* `student`: The 6 compulsory fields + color and strikethrough options.
* `experiments`: Sequential order, labels, titles, dates, `is_assignment`, `hash`, and `pages`.
* `is_manually_edited`: Preserved to maintain research ground-truth signals.

### What Does NOT Survive Refresh (Pure Transient)
* Active file binary `File` / `Blob` references (cannot serialize into localStorage).
* In-flight upload progress percentages.
* Generation deliverables (job folders on the server expire after 24 hours).

### Re-Hydration Protocol on Page Load
```
Page Load ──► Read localStorage
                   │
                   ▼
         Hashes present in queue?
         ├── NO  ──► Render empty state.
         └── YES ──► Dispatch background GET /api/file/<hash>/exists
                         │
                         ├── File exists: Keep green checkmark, show page count.
                         └── File pruned (404): Show amber badge: "Server session expired. Drop PDF to re-attach."
```

---

## 6. Error Handling & Recovery Matrix

| Scenario | UI Presentation | Student Recovery Action |
| :--- | :--- | :--- |
| **Non-PDF file dropped** | File rejected instantly; toast notification. | Drop `.pdf` document. |
| **Password-protected PDF** | Card highlighted with red border & lock icon. | Drop unencrypted PDF; backend returns `"password_protected"`. |
| **PDF exceeds 300 pages** | Card flagged: "File exceeds 300 page limit." | Remove or split file. |
| **Auto-extraction failed** | Amber chip: "Aim not auto-detected." | Input field automatically focused for manual entry. |
| **Network drop during upload**| Card shows "Upload interrupted" with retry button. | Click "Retry" or re-drop file. |
| **Compilation failed (500)** | Non-destructive modal showing backend error message. | Queue stays completely intact; student can fix the error and re-click Compile. |
| **Backend unavailable (503)**| Global top banner: "Backend unreachable." | Auto-retries health check every 10 seconds. |

---

## 7. Visual & Styling Direction

* **Framework**: **Tailwind CSS v4** (using native `@theme` CSS variables without legacy JS config bloat).
* **Typography**: Clean system font stack (`system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif`) with high-contrast text.
* **Component Primitives**: Lightweight, accessible custom primitives or `@radix-vue` unstyled primitives for modals and dropdowns. Zero heavyweight full UI frameworks (no Vuetify, no Quasar).
* **Icons**: `lucide-vue-next` (crisp, lightweight SVG icons).
* **Color Palette**:
  * Neutral Dark: Slate-900 / Zinc-900 background.
  * Slate-800 card surfaces with subtle 1px border (`border-slate-700/60`).
  * Primary Action: Indigo-600 / Blue-600 (`#2563eb`) with vibrant hover transitions.
  * Success: Emerald-500.
  * Warning: Amber-500.
  * Error: Rose-500.

---

## 8. Things We Explicitly Recommend NOT Building

1. **DO NOT build client-side PDF compilation (pdf-lib / pdfjs)**:
   * The Python PyMuPDF engine is benchmarked, handles vector TOC drawing, sets clickable Jump Links, and compiles 60 experiments in 20 seconds.
   * Compiling 600 pages in client-side JavaScript would cause massive mobile browser Out-Of-Memory crashes.
2. **DO NOT build a multi-step checkout wizard**:
   * Wizards create unnecessary friction when students need to cross-reference experiment titles with the cover sheet preview.
3. **DO NOT build a complex backend WebSocket / SSE system**:
   * The backend compiles in 0.5s to 20s. Standard HTTP POST with a clean client spinner is faster, simpler, and requires zero stateful socket infrastructure.
4. **DO NOT install monolithic UI libraries (Vuetify, Quasar, PrimeVue)**:
   * They inject 300+ KB of CSS/JS, override custom styling, and complicate responsive adaptations.
5. **DO NOT show fake progress bars**:
   * Progress bars that creep from 0% to 90% and stall are dishonest UX. Show elapsed execution time and authentic status messages.

---

## 9. Phased Implementation Plan

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       RECOMMENDED IMPLEMENTATION PHASES                     │
├─────────────────────────────────────────────────────────────────────────────┤
│ Phase 1: Clean Tooling & Scaffold                                           │
│ - Vite + Vue 3 + TypeScript + Tailwind CSS v4 setup                         │
│ - Base layout shell (3-column responsive grid)                              │
│ - Deliverable: Clean, building skeleton.                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│ Phase 2: Reactive State & Student Setup                                     │
│ - useLabStore composable with localStorage sync                             │
│ - StudentSetup form (6 compulsory fields with inline validation markers)    │
│ - Deliverable: Student profile auto-saves and validates.                    │
├─────────────────────────────────────────────────────────────────────────────┤
│ Phase 3: Document Queue & Ingestion Pipeline                                │
│ - Drag & drop zone with multi-file support                                  │
│ - Client-side SHA-256 calculation & /api/file/<hash>/exists deduplication   │
│ - Concurrency-pooled /api/upload (max 3 concurrent)                         │
│ - Experiment cards with reordering and manual title overrides               │
│ - Deliverable: Files drop, upload, extract aims, and populate queue.        │
├─────────────────────────────────────────────────────────────────────────────┤
│ Phase 4: Live Inspector & Table of Contents Preview                         │
│ - 150ms debounced /api/preview with in-memory LRU cache                     │
│ - Interactive HTML Table of Contents preview tab                            │
│ - Deliverable: Real-time visual feedback on cover sheets.                   │
├─────────────────────────────────────────────────────────────────────────────┤
│ Phase 5: Compilation, Deliverables Modal & Error Recovery                   │
│ - /api/generate trigger with batch validation (1-60 exps)                   │
│ - Deliverable download modal (Combined PDF, ZIP, Individual files)          │
│ - Comprehensive error toast and network drop handling                       │
│ - Deliverable: End-to-end working application ready for deployment.         │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 10. Summary Recommendation

> **YOUR RECOMMENDED FRONTEND ARCHITECTURE**:
> A **Three-Zone Command Center SPA** built on **Vue 3 (`<script setup>`) + TypeScript + Tailwind CSS v4**, orchestrated by a **Single Reactive Composable (`useLabStore`)** with client-side SHA-256 upload deduplication and a 150ms debounced Live Inspector.
>
> This architecture is chosen because it directly mirrors how students actually compile journals: seeing their profile, editing their experiment queue, and inspecting their cover pages side by side with zero page switching, while strictly respecting the 1 GB Oracle VM's concurrency and rate-limiting boundaries.
