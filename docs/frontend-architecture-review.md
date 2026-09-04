# LabStudio Frontend Architecture: Adversarial Review & Refined Specification

**Author**: Senior Software Architect & Lead Pair Programmer  
**Status**: Second-Pass Adversarial Critique & Revised Architecture  
**Target Backend**: Frozen LabStudio Backend v3.0.0 (Oracle Cloud VM, 1 GB RAM, Gunicorn 2x4, SQLite WAL)  
**Input Documents Evaluated**:  
* `docs/frontend-api-contract.md` (Verified Backend Contract)  
* `docs/frontend-state-model.md` (Initial State Mapping)  
* `docs/frontend-architecture-proposal.md` (First-Pass Architectural Proposal)  

---

## 1. Executive Summary: What We Questioned & What We Simplified

In this adversarial pass, we subjected our first proposal to rigorous scrutiny:
> *"Is this actually necessary, or did we introduce complexity because it sounds architecturally sophisticated?"*

We identified four major areas of premature abstraction and over-engineering in the initial proposal:
1. **Client-Side SHA-256 Pre-Hashing Was An Anti-Pattern**:  
   * *Initial Proposal*: Read every dropped PDF into a browser `ArrayBuffer`, compute SHA-256 via Web Crypto, ping `GET /api/file/<hash>/exists`, and only then upload.  
   * *The Flaw*: Reading 15 PDFs (each 5–20 MB) into memory on a student's laptop or phone creates massive GC pressure, duplicates hashing work the server already performs in C, and forces two network roundtrips per file.  
   * *The Refinement*: Stream dropped files directly to `POST /api/upload`. The backend computes the hash on the fly, deduplicates instantly, extracts the metadata, and returns the hash in a **single roundtrip**. `GET /api/file/<hash>/exists` is reserved strictly for its true purpose: **verifying cached hashes upon restoring `localStorage` on page refresh**.
2. **Preview Canvas & LRU Cache Were Over-Engineered**:  
   * *Initial Proposal*: "150ms Debounced Canvas + In-Memory LRU Cache".  
   * *The Flaw*: `/api/preview` returns a standard Base64 Data URL for a PNG image (`data:image/png;base64,...`). Rendering this onto an HTML5 `<canvas>` adds unnecessary imperative rendering code. Furthermore, 150ms is too aggressive for image generation across a network.  
   * *The Refinement*: Render the preview directly via standard hardware-accelerated `<img>`. Increase debounce to **350ms** with native `AbortController` cancellation for stale requests. Cache previews in a simple reactive `Map<string, string>` (keyed by experiment ID) without complex LRU eviction.
3. **Fragmented Composables Created Dependency Cycles**:  
   * *Initial Proposal*: Splintering state across `useLabStore`, `useUploadQueue`, `usePreviewDebounce`, and `useCompileJob`.  
   * *The Flaw*: When 4 composables all read, write, and synchronize with the same two entities (`student` and `experiments`), passing refs across composable boundaries creates tangled reactivity.  
   * *The Refinement*: Consolidate into a single, cohesive reactive store (`src/store/labStore.ts`) that owns the state and domain actions, while keeping HTTP communication cleanly isolated in a lightweight `src/api/client.ts`.
4. **Third-Party Dependency Diet**:  
   * Eliminated date libraries (`date-fns`), schema libraries (`Zod`), client-side PDF viewers (`pdf.js`), UUID libraries, and UI component frameworks. Vanilla TypeScript and standard Web APIs handle every requirement in under 20 lines of code each.

---

## 2. In-Depth Component & Subsystem Review

### 2.1 State Architecture & Ownership Boundaries

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           STORE STATE BOUNDARIES                            │
├─────────────────────────────────────────────────────────────────────────────┤
│ 1. PERSISTED (localStorage: "labstudio_v3_state")                          │
│    - student: { name, roll_no, batch, class_name, sem, subject,           │
│                 text_color, strikethrough_enabled }                         │
│    - experiments[]: [ { id, num, label, title, is_assignment, perf_date,   │
│                         sub_date, hash, pages, is_manually_edited } ]       │
├─────────────────────────────────────────────────────────────────────────────┤
│ 2. DERIVED (Computed Properties - Never Stored)                             │
│    - isStudentValid: Boolean (all 6 compulsory fields non-empty)            │
│    - isQueueValid: Boolean (all rows have title, label, and valid hash)     │
│    - isReadyToGenerate: isStudentValid && isQueueValid && count in [1, 60]  │
│    - tocPageCount: count <= 20 ? 1 : 1 + ceil((count - 20) / 24)           │
│    - totalOutputPages: sum(pages) + count + tocPageCount                    │
├─────────────────────────────────────────────────────────────────────────────┤
│ 3. TRANSIENT / UI (In-Memory Only - Cleared on Refresh)                     │
│    - activePreviewId: string | null (ID of row being inspected)             │
│    - previewImageCache: Map<string, string> (id -> base64 PNG)              │
│    - isPreviewLoading: boolean                                              │
│    - uploadQueueState: Map<string, { progress: number, error?: string }>    │
│    - isGenerating: boolean                                                  │
│    - generationDeliverables: GenerationDeliverables | null                  │
│    - globalError: AppError | null                                           │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Why a Unified Store Instead of Splintered Composables?
In a utility app of this scope, having `useUploadQueue` separate from `useLabStore` forces callbacks or bi-directional state binding just to update a row's `hash` or `pages` upon upload completion.  
A single unified store module (`src/store/labStore.ts`) encapsulates:
* State (`student`, `experiments`, `ui`)
* Actions (`addFiles(files)`, `updateExperiment(id, patch)`, `removeExperiment(id)`, `reorder(from, to)`, `rippleDates(startDate, 7)`, `compile()`)
* Persistence synchronization (auto-saving debounced JSON to `localStorage`).

---

### 2.2 Ingestion & Upload Architecture

#### The Fallacy of Client-Side Pre-Hashing
The first proposal assumed the client should hash files with `crypto.subtle.digest` to check `/api/file/<hash>/exists` before uploading.  
**Why this was flawed**:
1. When students drag in fresh lab reports, **0% of those files exist on the server**. Running client-side SHA-256 on 15 PDFs before sending a single byte wastes 1–3 seconds of pure client CPU time.
2. If a student drops a duplicate PDF within the same session, the frontend already tracks attached hashes in `experiments` in memory! It can detect duplicates locally in 0 milliseconds without running Web Crypto.
3. The backend `/api/upload` endpoint streams incoming bytes in 64 KB chunks, computes SHA-256 in C via OpenSSL, and checks disk existence atomically.

#### The Refined Upload Pipeline
```
[User Drops N Files]
         │
         ▼
[Local Sanity Check] ──► Not PDF or > 100MB? ──► Immediate Inline Rejection Toast
         │
         ▼ (Valid PDF)
[Create Skeleton Experiment Row] (Status: "uploading", Progress: 0%)
         │
         ▼
[Upload Worker Pool (Max 3 Concurrent Streams)]
         │
         ├── POST /api/upload (Multipart FormData)
         │       │
         │       └── Success (200 OK)
         │               │
         │               ▼
         │       [Update Row with Backend Metadata]
         │       - hash: res.hash (Durable 64-hex)
         │       - pages: res.pages
         │       - title: res.aim || "Experiment X"
         │       - is_assignment: res.is_assignment
         │       - exp_num: res.exp_num
         │       - extraction_status: (failure_reason == 'none') ? 'success' : 'manual_check'
         │       - Status: "ready"
         │
         └── Network / Parse Error (400 / 500)
                 │
                 ▼
         [Mark Row Error]
         - Status: "error"
         - Error message displayed on card
         - Action: "Retry" or "Remove"
```

#### The True Purpose of `GET /api/file/<hash>/exists`
`GET /api/file/<hash>/exists` is **not** for the initial upload path. It is for **Session Re-hydration**:
1. When the student opens LabStudio, `localStorage` restores their previous session (`student` and `experiments`).
2. The client has the stored `hash` string, but **no binary `File` handle**.
3. In the background, the client issues `GET /api/file/<hash>/exists` for each stored hash:
   * If `200 OK` (`exists: true`): The server still has the file. Keep the row green and ready.
   * If `404 Not Found`: The server pruned old files (e.g. after storage rotation). The row displays an amber badge: *"Session restored, but PDF expired on server. Click to re-attach."*

---

### 2.3 Preview Architecture: Clean & Realistic

#### What `/api/preview` Actually Does
* Backend accepts: `student` profile, `item` (title, exp_num, dates, is_assignment), and `formatting`.
* Backend returns: `image_data: "data:image/png;base64,iVBORw..."` (A4 rasterized at 150 DPI, ~150–250 KB).
* Backend takes: ~20–30 ms of CPU time.

#### Concrete Preview Strategy
1. **Direct `<img>` Rendering**:
   No `<canvas>` manipulation. Render `<img :src="activePreviewUrl" class="w-full h-auto rounded shadow border border-slate-700" alt="Cover Preview" />`. The browser's native compositor handles bilinear scaling, retina displays, and pinch-to-zoom effortlessly.
2. **Debounce Interval: 350ms**:
   150ms was too eager; rapid typing triggered multiple back-to-back renders. 350ms ensures preview requests fire only after the student pauses typing.
3. **Stale Request Cancellation with `AbortController`**:
   Every call to `api.fetchPreview(payload, signal)` cancels the previous in-flight preview request if the student keeps typing or switches rows.
4. **Simple In-Memory Cache**:
   A reactive `Map<string, string>` where key is `item.id + item.title + item.label + student.name + student.roll_no + item.perf_date`. If the student clicks between Experiment 1, 2, and 3 without edits, the preview appears **instantly in 0ms** from memory.
5. **Table of Contents (Index) Preview**:
   Does not use `/api/preview` (which only renders cover sheets). The frontend renders an interactive, styled HTML Table of Contents preview directly from the queue state. This gives instant, zero-latency visual verification of the Index page layout.

---

### 2.4 Experiment Lifecycle State Machine

Each row in the queue moves through a strict, deterministic state machine:

```
[QUEUED] ──► [UPLOADING (0..100%)] ──► [EXTRACTED / READY] ◄──► [MANUALLY EDITED]
                     │                          ▲
                     ▼                          │
                  [ERROR] ──────────────────────┘ (User fixes or replaces file)
```

| State | Allowed User Actions | Previewable? | Valid for Compilation? |
| :--- | :--- | :---: | :---: |
| **`QUEUED`** | Remove | No | No |
| **`UPLOADING`** | Cancel | No | No |
| **`EXTRACTED / READY`**| Edit title, change label, toggle assignment, set dates, reorder, delete | **Yes** | **Yes** |
| **`MANUALLY EDITED`** | All actions above | **Yes** | **Yes** |
| **`ERROR`** | Retry upload, replace file, delete row | No | No |
| **`STALE_FILE`** | Re-attach file, delete row | No | No |

---

### 2.5 Responsive Strategy: Practical Touch & Form Ergonomics

#### Why Rigid Mobile Tabs Can Be Harmful
Forcing a strict 3-tab navigation on mobile (Profile $\to$ Queue $\to$ Preview) breaks the student's context.  
Instead, we use a **Responsive Two-Segment Workspace**:

```
Desktop (>= 1024px): 3-Column Simultaneous Command Center
┌──────────────────┬─────────────────────────────────────┬──────────────────┐
│ Student Setup    │ Document Queue                      │ Live Inspector   │
│ (280px sticky)   │ (Flex-1 scrollable dropzone + cards)│ (380px sticky A4)│
└──────────────────┴─────────────────────────────────────┴──────────────────┘

Tablet & Mobile (< 1024px): Stacked Flow with Sticky Bottom Action
┌───────────────────────────────────────────────────────────────────────────┐
│ [Student Details Collapsible Accordion] (Completed: "Bhavya Shah • BE IT")│
├───────────────────────────────────────────────────────────────────────────┤
│ [Segmented Toggle:  (•) Document Queue (12)    ( ) Live Preview ]         │
├───────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│ [Queue View]                                                              │
│  - Bulk Dropzone                                                          │
│  - Experiment Cards with [▲ Up] [▼ Down] buttons for touch reordering    │
│                                                                           │
│ [Preview View]                                                            │
│  - Full-width A4 Cover Image                                              │
│  - Row selector dropdown: "Viewing Exp 1: MQTT Broker..."                 │
├───────────────────────────────────────────────────────────────────────────┤
│ STICKY BOTTOM BAR: [ 12/12 Ready ] ──────────────► [ Compile Journal 🚀 ] │
└───────────────────────────────────────────────────────────────────────────┘
```

#### Touch-Safe Reordering (Eliminating Drag-and-Drop Dependency)
* **The Problem**: HTML5 drag-and-drop does not work reliably on mobile touchscreens and is hostile to keyboard navigation and screen readers.
* **The Solution**: Every experiment card has dedicated, accessible **`[▲ Move Up]`** and **`[▼ Move Down]`** buttons alongside the drag handle.
  * Desktop users can drag and drop.
  * Mobile users tap Up/Down to reorder instantly.
  * Keyboard users press Up/Down shortcuts.
  * Zero external drag-and-drop libraries required.

---

### 2.6 Dependency Audit: Eliminating Bloat

| Proposed Dependency | Purpose | Native/Browser Alternative | Verdict |
| :--- | :--- | :--- | :---: |
| **`vue`** (v3.5+) | Core reactive framework | None | **KEEP** |
| **`vite`** (v6+) | Fast build & HMR tool | None | **KEEP** |
| **`typescript`** | Static typing & backend DTO safety | None | **KEEP** |
| **`@tailwindcss/vite`** (v4) | Utility CSS with zero config files | Native CSS variables / classes | **KEEP** |
| **`lucide-vue-next`** | Crisp, tree-shakeable SVG icons | Custom SVGs (too tedious to maintain) | **KEEP** |
| **`pinia`** | State management library | Native Vue `reactive()` singleton composable | **DISCARD** |
| **`vue-router`** | Routing library | Single-page application; no routing needed | **DISCARD** |
| **`date-fns` / `dayjs`** | Weekly date addition (+7 days) | 8 lines of native TypeScript (`Date.setDate`) | **DISCARD** |
| **`zod` / `yup`** | Schema validation | Computed properties (`isStudentValid`, `isQueueValid`) | **DISCARD** |
| **`vuedraggable` / `sortablejs`**| Drag-and-drop library | Native HTML5 drag events + Up/Down touch buttons | **DISCARD** |
| **`pdfjs-dist` / `pdf-lib`**| Client-side PDF rendering | Backend `/api/preview` returns PNG Data URL | **DISCARD** |
| **`uuid`** | Unique IDs for queue rows | Native `crypto.randomUUID()` | **DISCARD** |
| **`axios`** | HTTP client | Native browser `fetch()` with typed wrapper | **DISCARD** |

**Total Production Dependencies**: Exactly **5** (`vue`, `vite`, `typescript`, `@tailwindcss/vite`, `lucide-vue-next`). Zero runtime bloat.

---

### 2.7 Date Calculation: The 8-Line Native Solution
Indian universities standardize on `DD/MM/YYYY`. To auto-ripple submission dates (+7 days weekly):
```typescript
export function rippleDate(dateStr: string, daysToAdd = 7): string {
  const parts = dateStr.trim().split(/[\/\-\.]/).map(Number);
  if (parts.length !== 3 || parts.some(isNaN)) return "";
  const [day, month, year] = parts;
  const d = new Date(year, month - 1, day);
  d.setDate(d.getDate() + daysToAdd);
  const dd = String(d.getDate()).padStart(2, "0");
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  return `${dd}/${mm}/${d.getFullYear()}`;
}
```
Zero dependencies. Pure, deterministic, unit-testable.

---

### 2.8 Generation & Download Experience

#### Honest Stepped Compilation UX
The backend `/api/generate` takes 0.5s to 20s as an atomic operation. We reject creeping fake progress bars.  
During compilation:
1. Primary CTA transforms into an indeterminate spinner: `"Compiling Lab Package..."`.
2. A status ticker cycles through authentic stages based on elapsed time:
   * 0–2s: *"Rendering Institutional Cover Sheets..."*
   * 2–5s: *"Drawing Vector Table of Contents & Clickable Bookmarks..."*
   * 5s+: *"Compressing Master Deliverables & ZIP Package..."*
3. An active timer displays elapsed seconds (`"Elapsed: 4.2s"`).
4. Window navigation is locked with `beforeunload` to prevent accidental tab closing.

#### Deliverable Modal Flow
Upon receiving `200 OK`:
```
┌────────────────────────────────────────────────────────────────────────┐
│  🎉 LAB JOURNAL COMPILED SUCCESSFULLY!                                 │
│  650 pages compiled in 18.4s                                           │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  [📥 DOWNLOAD MASTER COMBINED PDF (Recommended)]                       │
│  Includes generated Table of Contents + all 60 experiments merged.     │
│                                                                        │
│  [📦 DOWNLOAD COMPLETE ZIP ARCHIVE]                                    │
│  Includes Combined PDF + all individual experiment files in a folder.  │
│                                                                        │
│  ▾ Download Individual Experiment Files (Dropdown list 1..60)          │
│                                                                        │
├────────────────────────────────────────────────────────────────────────┤
│  [ Keep Editing ]                                      [ Close ]       │
└────────────────────────────────────────────────────────────────────────┘
```
All buttons link directly to `/api/download/<relative_path>` matching the backend contract.

---

## 3. Revised Component Architecture & Directory Tree

```
frontend/
├── index.html
├── package.json
├── tsconfig.json
├── vite.config.ts
└── src/
    ├── style.css                      # Tailwind v4 entry (@import "tailwindcss";)
    ├── main.ts                        # Application mounting
    ├── App.vue                        # Shell layout (Header, Main Workspace, Modal)
    ├── api/
    │   ├── types.ts                   # Backend request/response DTO interfaces
    │   └── client.ts                  # Typed fetch wrapper (upload, preview, generate)
    ├── store/
    │   ├── types.ts                   # Store models: StudentProfile, ExperimentItem, UIState
    │   └── labStore.ts                # Reactive singleton store with localStorage sync
    ├── utils/
    │   ├── dates.ts                   # Native DD/MM/YYYY date ripple logic
    │   └── formatters.ts              # File size, page counter, label helpers
    └── components/
        ├── HeaderBar.vue              # Top institutional branding, storage indicator, status
        ├── StudentForm.vue            # 6 compulsory fields + color & strikethrough options
        ├── DocumentQueue.vue          # Bulk dropzone + experiment cards container
        ├── ExperimentCard.vue         # Individual row: drag handle, title, exp#, date, status
        ├── LiveInspector.vue          # Right panel: A4 cover preview & HTML TOC preview tabs
        └── DownloadModal.vue          # Compilation results modal with direct download buttons
```

**Total Component Count**: Exactly **6 focused Vue components**. No arbitrary wrapper nesting.

---

## 4. Phased Implementation Plan

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        REVISED IMPLEMENTATION PHASES                        │
├─────────────────────────────────────────────────────────────────────────────┤
│ Phase 1: Tooling & Types Baseline                                           │
│ - Initialize package.json, vite.config.ts, tsconfig.json, Tailwind v4       │
│ - Create src/api/types.ts & src/store/types.ts matching backend contract    │
│ - Verification: npm run build produces clean frontend/dist/index.html       │
├─────────────────────────────────────────────────────────────────────────────┤
│ Phase 2: Reactive Store & Student Setup Form                                │
│ - Implement src/store/labStore.ts with debounced localStorage auto-save     │
│ - Implement src/components/StudentForm.vue (6 compulsory fields)            │
│ - Verification: Form validates inputs; state persists across browser refresh│
├─────────────────────────────────────────────────────────────────────────────┤
│ Phase 3: Document Queue & Direct Streaming Ingestion                        │
│ - Implement src/api/client.ts (upload_file with FormData)                   │
│ - Implement src/components/DocumentQueue.vue & ExperimentCard.vue           │
│ - Multi-file dropzone with max-3 concurrent upload pool                     │
│ - Manual title edit tracking (is_manually_edited)                           │
│ - Touch-safe Move Up / Move Down buttons                                    │
│ - Verification: Dropping 5 real PDFs streams to backend, populates queue,  │
│   and displays extracted aims correctly.                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│ Phase 4: Live Inspector & Table of Contents Preview                         │
│ - Implement 350ms debounced /api/preview with AbortController in labStore   │
│ - Implement src/components/LiveInspector.vue (Cover Image & HTML TOC tabs)  │
│ - Verification: Typing student name or title updates A4 preview image;      │
│   switching rows loads cached preview instantly.                            │
├─────────────────────────────────────────────────────────────────────────────┤
│ Phase 5: Compilation, Deliverable Modal & Error Hardening                   │
│ - Implement compile action calling /api/generate with full payload          │
│ - Implement src/components/DownloadModal.vue with direct download links     │
│ - Implement error toasts for password-locked, corrupt, or oversized PDFs    │
│ - Final end-to-end browser test with real student submissions               │
│ - Verification: Complete compilation of 10+ experiments produces valid      │
│   downloadable Combined PDF and ZIP archive.                                │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Architectural Decisions Summary

1. **Architecture Model**: Single-Page Workspace with responsive two-segment fallback on mobile.
2. **State Pattern**: Native Vue 3 Composition API singleton store (`labStore.ts`) with debounced `localStorage` hydration. Zero Pinia ceremony.
3. **Upload Pipeline**: Direct streaming to `POST /api/upload` with a concurrency pool of 3 streams. Eliminates client-side pre-hashing overhead.
4. **Preview Engine**: 350ms debounced `POST /api/preview` rendered via standard `<img>` with `AbortController` cancellation. Table of Contents rendered client-side in HTML.
5. **Compilation UX**: Stepped elapsed-time status messages; zero fake creeping percentage bars. Direct download links to `/api/download/<filepath>`.
6. **Reordering Controls**: Dual controls: HTML5 drag-and-drop for mouse users + `[▲ Up] / [▼ Down]` buttons for mobile touch and keyboard accessibility.
7. **Dependencies**: Exactly 5 (`vue`, `vite`, `typescript`, `@tailwindcss/vite`, `lucide-vue-next`).

---

## 6. Changes From Original Proposal

| Area | Original Proposal | Revised Adversarial Decision | Rationale |
| :--- | :--- | :--- | :--- |
| **Ingestion** | Client-side SHA-256 pre-hashing via Web Crypto | Direct streaming to `POST /api/upload` | Eliminates memory-heavy `arrayBuffer()` reads and redundant double-hashing. Server already deduplicates in C. |
| **Hash Verification**| `GET /api/file/<hash>/exists` on every upload | Reserved strictly for session re-hydration on page boot | Checking server existence before uploading is wasteful when 100% of new files are un-cached. |
| **Preview Rendering**| Rendered via HTML5 `<canvas>` | Standard `<img>` with Base64 Data URL | Native browser image decoding is faster, simpler, retina-ready, and hardware accelerated. |
| **Preview Debounce** | 150ms debounce | 350ms debounce + `AbortController` | 150ms was too eager, firing intermediate requests during active typing. |
| **Composables** | 4 separate composable files | Consolidated `src/store/labStore.ts` | Eliminates circular dependencies and cross-composable prop drilling. |
| **Mobile Reorder** | Drag-and-drop on mobile | Touch-friendly `[▲ Up]` / `[▼ Down]` buttons | HTML5 drag-and-drop fails on mobile screens and breaks keyboard accessibility. |
| **Date Ripple** | Underspecified | 8-line native `rippleDate()` helper | Avoids adding 40 KB `date-fns` for a simple +7 day integer addition. |

---

## 7. Remaining Open Questions for Product Alignment

1. **Default Color Preference**:  
   The backend `/api/load-defaults` specifies `text_color: "blue"`, whereas our test scripts and students frequently use dark institutional blue (`"#0000bf"`). Both work identically on the backend. Should the default color picker preset be `#0000bf` (Institutional Blue)?
2. **Session Expiry Notice**:  
   If a student returns after 2 weeks and their server files were deleted by 15 GB quota rotation, should the UI show an inline badge on each expired row asking to re-attach the PDF, or automatically offer a one-click "Clear Expired Files" action? *(Recommended: Inline badge per card so their titles and dates are preserved).*

---

## Final Recommended Architecture

> **FINAL RECOMMENDED FRONTEND ARCHITECTURE**:  
> A lightweight, zero-bloat **Three-Zone Workspace SPA** built with **Vue 3 (`<script setup>`) + TypeScript + Tailwind CSS v4**, driven by a **Single Reactive Singleton Store (`labStore.ts`)** with direct 3-stream upload pooling, native touch/keyboard reordering controls, and a 350ms debounced `<img>` preview canvas.  
>  
> It relies on only 5 total packages, introduces zero unnecessary abstractions, and aligns 100% with the frozen v3.0.0 Python backend.

---

**FRONTEND ARCHITECTURE REVIEW COMPLETE — NO IMPLEMENTATION YET**
