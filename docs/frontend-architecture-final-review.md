# Frontend Architecture — Independent Final Review

**Author**: Senior Software Architect & Lead Pair Programmer  
**Status**: Approved Pre-Implementation Architectural Blueprint  
**Target Backend**: Frozen LabStudio Backend v3.0.0 (Oracle Cloud VM, 1 GB RAM, Gunicorn 2x4, SQLite WAL)  
**Evaluated Documents**:  
* `docs/frontend-api-contract.md` (Verified Backend API Contract)  
* `docs/frontend-state-model.md` (Initial State Mapping)  
* `docs/frontend-architecture-proposal.md` (First-Pass Proposal)  
* `docs/frontend-architecture-review.md` (Second-Pass Review)  

---

## 1. Independent Verdict

The core product requirement is straightforward: transform an error-prone, 2-hour end-of-semester lab journal formatting, titling, dating, and merging chore into an automated, reliable batch workflow.

This application consists of **one frontend build containing two deliberately isolated surfaces**:
```text
/
└── Student Lab Studio (exclusively student-facing, zero admin exposure)

/analytics
└── Admin Authentication Gate
    └── Admin Analytics Dashboard (URL-only, strictly authenticated)
```

Earlier proposals contained theoretical abstractions that would have introduced unnecessary implementation friction:
1. **Client-side SHA-256 pre-hashing before upload was an anti-pattern**: Reading multi-megabyte PDFs into browser memory before sending bytes created memory spikes and double-hashing. We upload directly via standard `FormData`, letting the backend compute the hash in C and deduplicate on disk in a single network roundtrip.
2. **Preview canvas and LRU cache were over-engineered**: The backend returns a base64 PNG data URL; an `<img>` tag renders it with native GPU acceleration and zero imperative canvas code. Caching is an optional optimization, not an architectural requirement.
3. **Fragmented composables caused circular dependencies**: We consolidate state into a clean `labStore.ts` for the student workspace and a separate `adminStore.ts` for admin analytics.
4. **Admin Analytics is URL-only and strictly authenticated**: There is **no link, button, footer link, menu item, or keyboard shortcut anywhere in the student UI pointing to `/analytics`**. Visiting `/analytics` requires password authentication validated by the backend.

---

## 2. State Architecture & Isolation Boundaries

The application enforces strict architectural boundaries to prevent stores from becoming dumping grounds:
```text
stores/
  └── application state + business orchestration

api/
  └── HTTP requests and API response handling

utils/
  └── pure calculations, formatting, routing, and validation

components/
  └── presentation and user interaction
```

### State Ownership Boundaries

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           APPLICATION STATE BOUNDARIES                      │
├─────────────────────────────────────────────────────────────────────────────┤
│ 1. STUDENT STORE (src/store/labStore.ts - LocalStorage Persisted)          │
│    - student: { name, roll_no, batch, class_name, sem, subject,           │
│                 text_color, strikethrough_enabled }                         │
│    - experiments[]: [ { id, num, label, title, is_assignment, perf_date,   │
│                         sub_date, hash, pages, is_manually_edited } ]       │
├─────────────────────────────────────────────────────────────────────────────┤
│ 2. ADMIN STORE (src/store/adminStore.ts - SessionStorage Auth Only)        │
│    - auth: { isAuthenticated: boolean, adminKey: string | null }            │
│    - summary: AnalyticsSummaryDTO | null                                    │
│    - events: { list: GenerationEventDTO[], total: number, page: number }    │
│    - diagnostics: ExtractionDiagnosticsDTO | null                           │
│    - isFetching: boolean                                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│ 3. DERIVED COMPUTED STATE (Pure Functions - Never Stored)                   │
│    - isStudentValid: Boolean (all 6 compulsory fields non-empty)            │
│    - isQueueValid: Boolean (all rows have title, label, and verified hash)  │
│    - isReadyToGenerate: isStudentValid && isQueueValid && 1 <= count <= 60  │
│    - tocPageCount: count <= 20 ? 1 : 1 + ceil((count - 20) / 24)           │
│    - totalOutputPages: sum(pages) + count + tocPageCount                    │
├─────────────────────────────────────────────────────────────────────────────┤
│ 4. TRANSIENT UI STATE (In-Memory Only - Reset on Refresh)                  │
│    - activePreviewId: string | null                                         │
│    - isPreviewLoading: boolean                                              │
│    - uploadPool: Map<string, { progress: number, error?: string }>          │
│    - isGenerating: boolean                                                  │
│    - deliverables: GenerationDeliverables | null                            │
└─────────────────────────────────────────────────────────────────────────────┘
```

* **No Pinia Required**: The application has two entities (`student` and `experiments`). Native Vue 3 Composition API (`reactive` / `ref` / `computed`) provides 100% type safety, zero ceremony, and zero bundle overhead.
* **Strict Student vs. Admin Isolation**: Student state (`labStore.ts`) and Admin state (`adminStore.ts`) are completely isolated. Admin credentials and analytics caches are **never** serialized into the student's `localStorage`.
* **Zero Networking in Stores or Components**: Stores call typed functions in `src/api/*`, keeping fetch, header management, and response status mapping cleanly contained in the API layer.

---

## 3. Experiment Lifecycle

Every experiment row moves through an explicit, deterministic state machine:

```
[QUEUED] ──► [UPLOADING (0..100%)] ──► [READY / EXTRACTED] ◄──► [MANUALLY EDITED]
                     │                          ▲
                     ▼                          │
                  [ERROR] ──────────────────────┘ (Student fixes or replaces file)
```

| Lifecycle State | Description | Allowed Actions | Previewable? | Valid for Compile? |
| :--- | :--- | :--- | :---: | :---: |
| **`QUEUED`** | File selected, waiting in concurrency pool | Remove | No | No |
| **`UPLOADING`** | In-flight upload to `/api/upload` via FormData | Cancel | No | No |
| **`READY`** | Upload verified, aim/exp# extracted from PDF | Edit title, label, dates, toggle assignment, reorder, delete | **Yes** | **Yes** |
| **`MANUALLY_EDITED`**| Student modified auto-extracted title/exp# | All actions above (`is_manually_edited = true`) | **Yes** | **Yes** |
| **`ERROR`** | Corrupt/password-locked PDF or upload failure | Retry, replace file, delete row | No | No |
| **`STALE_FILE`** | Restored from localStorage, missing on server | Re-attach PDF, delete row | No | No |

---

## 4. Upload Architecture

### Direct FormData Upload (Zero Client Pre-Hashing)
* **What We Avoid**: We do NOT read files into memory with `file.arrayBuffer()` or compute Web Crypto SHA-256 before uploading.
* **What We Do**: Files are dispatched directly to `POST /api/upload` as standard multipart `FormData` via `fetch()`.
  * The backend streams chunks into `uploads/temp_<uuid>.pdf`, computes the SHA-256 hash in C, validates `%PDF-` magic bytes, extracts the Aim, and returns metadata in a **single network roundtrip**.
  * If the file already exists on disk, the backend deduplicates it automatically in 0 ms.
* **Concurrency Pool**: Managed with **maximum 3 concurrent uploads**. This keeps throughput fast while strictly avoiding the backend's 40 requests/minute rate-limit ceiling.
* **Error Classification**:
  * Client-side rejection: Files without `.pdf` extension or $>100\text{ MB}$ are rejected immediately before network dispatch.
  * Server-side rejection: Encrypted/password-protected PDFs or PDFs exceeding 300 pages display an inline red badge on the card with the server's exact error message.

---

## 5. Persistence & Recovery Flow

### Data Classification Matrix
```
PERSIST (localStorage: "labstudio_v3_state"):
├── student profile (all 6 compulsory fields + color + strikethrough)
└── experiment rows (id, num, label, title, dates, is_assignment, hash, pages, is_manually_edited)

SESSION ONLY (sessionStorage: "labstudio_admin_key"):
└── adminKey (raw password string; cleared when browser tab closes)

DERIVED (Pure computed):
├── isStudentValid, isQueueValid, isReadyToGenerate
└── tocPageCount, totalOutputPages

NEVER STORE:
├── binary File handles (cannot serialize)
├── upload progress percentages
├── in-memory preview state
└── generation deliverable paths (server prunes jobs after 24h)
```

### Boot & Recovery Protocol
1. On app boot, read `localStorage["labstudio_v3_state"]`.
2. If `experiments` contains items with `hash`:
   * Dispatch background verification requests to `GET /api/file/<hash>/exists`.
   * If `exists: true`: Set row to `READY`.
   * If `exists: false` (404, file pruned after server storage rotation): Mark row as `STALE_FILE` with amber badge: *"Session restored, but PDF expired on server. Click to re-attach."*
   * **Crucial Rule**: Never delete the student's typed titles, labels, or dates if the server file is missing. Let them simply drop the PDF back onto the card to re-associate.

---

## 6. Preview Architecture

### Authoritative Backend Preview (`POST /api/preview`)
* **What It Returns**: A standard Base64 Data URL for a PNG image (`data:image/png;base64,...`) at 150 DPI.
* **Rendering**: Rendered directly in native `<img>` with GPU acceleration. Zero `<canvas>` code.
* **Debouncing**: **350 ms** debounce window on student input.
* **Stale Response Protection**: Every preview call passes an `AbortController.signal`. When the student types again or selects a different experiment row, the previous in-flight request is aborted immediately so older requests can never overwrite newer selections.
* **Caching Policy**: In-memory caching is an **optional optimization**, not an architectural requirement. The core architecture relies on debounced fetch with cancellation and robust loading/error states.

### Informational Table of Contents (Index) Preview
* Does NOT call `/api/preview` (which only renders cover sheets).
* Rendered client-side as an interactive, styled HTML Table of Contents preview tab based on the exact queue state. This gives instant, zero-latency visual feedback.

---

## 7. Table of Contents: Exact Backend Calculation

To avoid presenting approximate or incorrect page counts, the frontend replicates the exact procedural algorithm from `lab_core/toc_engine.py`:

```typescript
// src/utils/toc.ts
// lab_core/toc_engine.py: Page 1 holds 20 entries; subsequent pages hold 24 entries.
export function calculateTocPages(experimentCount: number): number {
  if (experimentCount <= 0) return 1;
  if (experimentCount <= 20) return 1;
  return 1 + Math.ceil((experimentCount - 20) / 24);
}

export function calculateTotalOutputPages(experiments: Array<{ pages: number }>): number {
  const bodyPages = experiments.reduce((acc, exp) => acc + (exp.pages || 0), 0);
  const headerPages = experiments.length;
  const tocPages = calculateTocPages(experiments.length);
  return bodyPages + headerPages + tocPages;
}
```
This is a pure, zero-dependency utility function that matches backend generation down to the exact page number.

---

## 8. API Layer Architecture

HTTP requests are partitioned into focused API modules under `src/api/`:
* `client.ts`: Base fetch wrapper managing base URLs, headers, and error normalization.
* `upload.ts`: Multipart upload handler with progress callback.
* `preview.ts`: Cover preview fetcher accepting an `AbortSignal`.
* `generate.ts`: Batch generation compiler with timeout handling.
* `analytics.ts`: Authenticated admin analytics client (`X-Analytics-Key` header injection).

---

## 9. Generation & Download UX

### Honest Stepped Status (Zero Fake Progress Bars)
`/api/generate` is an atomic, non-streaming compilation taking 0.5s–20s. We reject creeping fake progress bars.  
During compilation:
1. Primary CTA transforms into an indeterminate spinner: `"Compiling Lab Package..."`.
2. Active status ticker updates authentically based on elapsed time:
   * 0–2s: *"Rendering Institutional Cover Sheets..."*
   * 2–5s: *"Drawing Vector Table of Contents & Clickable Jump Links..."*
   * 5s+: *"Compressing Master Deliverables & ZIP Package..."*
3. Displays an active elapsed timer: `"Elapsed: 4.2s"`.
4. `beforeunload` listener prevents accidental tab closure while compilation is running.

### Deliverable Modal Flow
Upon receiving `200 OK`:
* Master Combined PDF: `GET /api/download/<combined_pdf>` (Primary recommended download).
* Complete ZIP Package: `GET /api/download/<zip_package>` (Secondary download).
* Individual Merged PDFs: Expandable list linking directly to `/api/download/<merged_pdf>`.

---

## 10. Responsive UX & Form Ergonomics

### Desktop ($\ge 1024\text{px}$): Three-Zone Command Center
```
┌──────────────────┬─────────────────────────────────────┬──────────────────┐
│ STUDENT SETUP    │ DOCUMENT QUEUE                      │ LIVE INSPECTOR   │
│ (280px sticky)   │ (Flex-1 dropzone + experiment cards)│ (380px sticky A4)│
└──────────────────┴─────────────────────────────────────┴──────────────────┘
```

### Tablet & Mobile ($< 1024\text{px}$): Two-Segment Focused Workspace
* Student Setup collapses into a clean top summary card: `"Bhavya Shah • BE IT • Roll 77 [Edit]"`.
* Segmented control toggles between:
  * `[• Document Queue (12)]`
  * `[  Live Inspector Preview ]`
* **Touch-Safe Reordering**: Every card includes accessible **`[▲ Move Up]`** and **`[▼ Move Down]`** buttons. Touch users reorder with a single tap without fighting touchscreen drag conflicts.
* Sticky bottom bar: `[ 12/12 Ready ] ──────────────► [ Compile Journal 🚀 ]`.

---

## 11. Accessibility (a11y) Strategy

* **Keyboard Reordering**: `[▲ Up]` and `[▼ Down]` buttons are natively focusable and keyboard-accessible via `Space` / `Enter`.
* **Focus Management**: When an upload finishes with an extraction failure, focus moves automatically to the Aim input field with an accessible announcement (`aria-live="polite"`).
* **High Contrast & Color Independence**: Statuses are never conveyed by color alone. Every badge has an accompanying icon and text label (e.g. green checkmark + `"Ready"`, amber alert + `"Check Title"`, red lock + `"Password-Protected"`).
* **Modal Accessibility**: The Download Modal traps focus, closes on `Escape`, and restores focus to the Compile trigger on close.

---

## 12. Dependencies: Strict Minimalism

### Runtime Dependencies (Only 2)
1. **`vue`** (v3.5+): Core reactivity and component engine.
2. **`lucide-vue-next`**: Tree-shakeable, accessible SVG icons.

### Build / Dev Tooling
1. **`vite`** (v6+): Fast build pipeline and dev server.
2. **`typescript`**: Type safety against backend contracts.
3. **`@tailwindcss/vite`** (Tailwind CSS v4): Utility styling via native CSS variables with zero config files.

**Discarded**: Pinia, Vue Router, date-fns, Zod, pdfjs-dist, vuedraggable, axios, uuid, and Chart.js.

---

## 13. Component Architecture & Suggested Source Tree

The source tree strictly separates the two application surfaces and maintains clean layered boundaries:

```text
src/
├── api/
│   ├── client.ts                      # Base fetch wrapper, error normalization, header injection
│   ├── upload.ts                      # Multipart file upload handler
│   ├── preview.ts                     # Cover preview fetcher with AbortSignal
│   ├── generate.ts                    # Compilation job submitter
│   └── analytics.ts                   # Admin endpoints & sample download URLs
│
├── store/
│   ├── types.ts                       # StudentProfile, ExperimentItem, UIState interfaces
│   ├── labStore.ts                    # Student workspace store (localStorage auto-save)
│   └── adminStore.ts                  # Admin analytics store (sessionStorage auth)
│
├── components/
│   ├── student/
│   │   ├── StudentForm.vue            # 6 compulsory fields + color/strikethrough options
│   │   ├── DocumentQueue.vue          # Multi-file dropzone & scrollable cards list
│   │   ├── ExperimentCard.vue         # Individual row: drag, inputs, status, Up/Down
│   │   ├── LiveInspector.vue          # 150 DPI cover image + HTML TOC tabs
│   │   └── DownloadModal.vue          # Deliverable download links modal
│   │
│   └── admin/
│       ├── AdminKpiCards.vue          # Total gens, success rate, avg duration, student count
│       ├── AdminDailyChart.vue        # Native SVG/CSS daily trend visualization
│       ├── AdminEventsTable.vue       # Filterable, paginated generation event log
│       └── AdminDiagnosticsView.vue   # Heuristic breakdown & sample download list
│
├── utils/
│   ├── router.ts                      # Native History API path switcher (/ and /analytics)
│   ├── dates.ts                       # Native DD/MM/YYYY date ripple logic (+7 days)
│   ├── toc.ts                         # Exact procedural TOC page counter
│   └── validation.ts                  # Pure validation functions (isStudentValid, isQueueValid)
│
├── views/
│   ├── LabStudio.vue                  # Top-level view for student workspace
│   └── AdminDashboard.vue             # Top-level view for admin dashboard (lazy loaded)
│
├── style.css                          # Tailwind v4 entry (@import "tailwindcss";)
├── main.ts                            # Application bootstrapper
└── App.vue                            # View-switching shell (LabStudio vs AdminDashboard)
```

---

## 14. Performance

* **Memory Safety**: Direct `FormData` uploads eliminate reading multi-megabyte PDFs into browser memory.
* **Render Performance**: Base64 PNG previews render via native GPU-accelerated `<img>`.
* **Zero Main-Thread Freezes**: Date math and validation are microsecond operations in pure TypeScript.
* **Code Splitting**: `AdminDashboard.vue` is loaded asynchronously via `defineAsyncComponent`. Students on `/` never download admin analytics code.

---

## 15. Architecture Smell Test

1. **Smell: Reading 15 PDFs into browser memory to pre-hash them.**
   * *Status*: **ELIMINATED**. Dispatches directly to `/api/upload` via `FormData`.
2. **Smell: Imperative HTML5 Canvas for rendering a Base64 PNG.**
   * *Status*: **ELIMINATED**. Replaced with native `<img>`.
3. **Smell: Splintering state into 4 separate composables.**
   * *Status*: **ELIMINATED**. Consolidated into `labStore.ts` (student) and `adminStore.ts` (admin).
4. **Smell: Heavy 200 KB chart library for 1 daily sparkline and 2 bar lists.**
   * *Status*: **ELIMINATED**. Replaced with declarative SVG and Tailwind CSS bars.
5. **Smell: External libraries for dates, validation, and UUIDs.**
   * *Status*: **ELIMINATED**. Replaced with native TypeScript pure functions.

---

## 16. Final Recommended Architecture

A focused **Two-Surface Single-Page Application** built with **Vue 3 (`<script setup>`) + TypeScript + Tailwind CSS v4**:
* **Student Workspace (`/`)**: A Three-Zone Command Center driven by `labStore.ts` with `localStorage` synchronization, maximum 3 concurrent uploads, touch-safe reordering buttons, and a 350ms debounced `<img>` cover preview. Contains zero links, shortcuts, or references to `/analytics`.
* **Admin Dashboard (`/analytics`)**: A lazy-loaded administrative portal driven by `adminStore.ts` with `sessionStorage` credential management, native SVG daily trend charting, paginated event inspection, and raw PDF sample downloads.

---

## 17. Suggested Source Tree (Detailed in Section 13)

Refer to [Section 13](#13-component-architecture--suggested-source-tree) for the full component and module tree.

---

## 18. Implementation Phases

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ORDERED IMPLEMENTATION PHASES                       │
├─────────────────────────────────────────────────────────────────────────────┤
│ Phase 1: Tooling, Layout Shell & Minimal Routing                            │
│ - Scaffold package.json, vite.config.ts, tsconfig.json, Tailwind v4         │
│ - Implement src/utils/router.ts (lightweight path switcher for / and /analytics) │
│ - Implement App.vue, LabStudio.vue, and lazy-loaded AdminDashboard.vue      │
│ - Verification: npm run build succeeds; visiting / and /analytics render    │
│   their respective shell views without console errors; unknown paths        │
│   fallback cleanly to LabStudio.                                            │
├─────────────────────────────────────────────────────────────────────────────┤
│ Phase 2: Student Store & Setup Form                                         │
│ - Implement src/utils/validation.ts and src/store/labStore.ts               │
│ - Implement src/components/student/StudentForm.vue                          │
│ - Verification: 6 compulsory fields validate inline; student details persist│
│   across browser refresh in localStorage.                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│ Phase 3: Document Queue & Concurrency-Pooled Uploads                        │
│ - Implement src/api/upload.ts and DocumentQueue.vue / ExperimentCard.vue    │
│ - Maximum 3 concurrent uploads pool                                         │
│ - Touch-safe Move Up / Move Down reordering controls                        │
│ - Verification: Dropping 5 real PDFs uploads to backend, populates queue,  │
│   and displays extracted aims correctly.                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│ Phase 4: Live Inspector & Table of Contents Preview                         │
│ - Implement src/api/preview.ts (350ms debounce + AbortController)           │
│ - Implement src/components/student/LiveInspector.vue (Cover Image & HTML TOC)│
│ - Verification: Selecting an experiment displays the correct cover preview; │
│   rapid typing cancels in-flight requests; stale requests cannot overwrite  │
│   newer selections; loading and error states display properly.              │
├─────────────────────────────────────────────────────────────────────────────┤
│ Phase 5: Compilation & Deliverable Retrieval                                │
│ - Implement src/api/generate.ts and DownloadModal.vue                       │
│ - Batch validation (1-60 experiments) and elapsed execution timer           │
│ - Verification: Full generation produces downloadable Combined PDF and ZIP  │
│   package; error banners trigger cleanly on oversized or invalid inputs.    │
├─────────────────────────────────────────────────────────────────────────────┤
│ Phase 6: Admin Analytics Dashboard                                          │
│ - Implement src/api/analytics.ts and src/store/adminStore.ts                │
│ - Password authentication against POST /api/analytics/auth                 │
│ - KPI cards, native SVG daily trend chart, paginated event table with       │
│   search, diagnostics view, and CSV/JSON export triggers                    │
│ - Verification: Admin enters password, authenticates against backend,       │
│   inspects real historical events, downloads CSV, and returns to login on   │
│   401 unauthorized response.                                                │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 19. Explicit Non-Goals

1. **DO NOT install heavy UI libraries (Vuetify, Quasar, PrimeVue)**.
2. **DO NOT install charting libraries (Chart.js, ApexCharts)**.
3. **DO NOT install client-side PDF compilers (`pdf-lib`, `pdfjs`)**.
4. **DO NOT pre-hash files on the client before upload**.
5. **DO NOT use HTML5 `<canvas>` for preview images**.
6. **DO NOT invent real-time WebSocket infrastructure for compilation or analytics**.
7. **DO NOT invent hourly traffic breakdowns or endpoint latency metrics not present in backend**.
8. **DO NOT expose any navigation link, button, or menu item to `/analytics` in the student UI**.

---

## 20. Final Decisions

* **DECISIONS I AGREE WITH FROM THE EXISTING PROPOSAL**:
  * Three-Zone Command Center layout on desktop.
  * Direct consumption of `/api/download/<relative_path>`.
  * Using Tailwind CSS v4 for zero-config styling.
  * Storing student profile and experiment metadata in `localStorage`.
  * Using an authentic stepped elapsed timer instead of fake percentage bars.
* **DECISIONS I WOULD CHANGE**:
  * Dropped client-side SHA-256 pre-hashing; stream directly to `POST /api/upload`.
  * Dropped HTML5 `<canvas>` preview rendering; use standard `<img>` tags.
  * Increased preview debounce from 150ms to 350ms with `AbortController`.
  * Replaced mobile drag-and-drop with touch-friendly `[▲ Up]` / `[▼ Down]` buttons.
  * Dropped date-fns, Zod, and Pinia in favor of native TypeScript utilities and Vue reactive singletons.
  * Separated student and admin state into two distinct stores.
* **DECISIONS THAT WERE MISSING (NOW FULLY SPECIFIED)**:
  * Complete Administrative Analytics Dashboard architecture (`/analytics`).
  * Explicit URL-only admin access model: no links or discoverable paths in student UI.
  * Verified authentication lifecycle: backend validates raw password string passed via `X-Analytics-Key` header; credentials stored strictly in `sessionStorage` and cleared on 401.
  * Native SVG/CSS charting specification for daily generation trends.
  * Code-splitting admin surface away from student bundle via `defineAsyncComponent`.

---

## ADMIN ANALYTICS ARCHITECTURE

### 1. Access Model & URL Isolation
* **Exclusively Student Surface on `/`**: The student interface (`LabStudio.vue`) has **zero awareness of `/analytics`**. There is no "Admin" button, footer link, hidden menu, key combination, or any discoverable element in the student UI.
* **Direct Addressability**: `/analytics` is directly reachable via the browser URL bar.
* **URL Obscurity Is NOT Security**: Making `/analytics` unlinked is an ergonomic boundary, not a security mechanism. The authoritative security boundary is the backend constant-time HMAC password verification. Merely visiting `/analytics` exposes zero analytics data.
* **Code Splitting**: `AdminDashboard.vue` is loaded via `defineAsyncComponent(() => import('../views/AdminDashboard.vue'))`. A student on `/` never downloads or parses admin code.

### 2. Forensic Reality of Backend Implementation
Inspection of `app.py` lines 670–840 and `lab_core/analytics.py` defines the exact contract:

1. **Route Serving**:
   * `GET /analytics`: Flask explicitly serves `frontend/dist/index.html` (the SPA entrypoint) if it exists, or falls back to `render_template("index.html")`.
2. **Status Check**:
   * `GET /api/analytics/status`: Returns `{"enabled": true, "auth_required": bool}` (404 if disabled).
3. **Authentication Endpoint**:
   * `POST /api/analytics/auth`: Accepts JSON `{"password": "<candidate>"}` or header `X-Analytics-Key`.
   * Verifies password using `verify_admin_password(candidate)` which calls `hmac.compare_digest(candidate, expected)`.
   * Returns `{"valid": true, "auth_required": bool}` on success, or 401 `{"valid": false, "error": "Invalid admin password"}` on failure.
   * **Crucial Fact**: The backend does NOT issue a session token or JWT! The credential verified on subsequent requests is the **raw admin password itself**.
4. **Credential Passing on Subsequent Requests**:
   * All protected endpoints (`/api/analytics/summary`, `/api/analytics/events`, `/api/analytics/export`, `/api/analytics/diagnostics`, `/api/analytics/sample/<hash>`) call `_check_analytics_auth()`.
   * The handler inspects `request.headers.get("X-Analytics-Key")` or `request.headers.get("Authorization")` (supporting `Bearer <key>`).
   * The frontend attaches `X-Analytics-Key: <password>` to every analytics fetch request.
5. **Credential Storage & Revalidation**:
   * Stored strictly in `sessionStorage.getItem("labstudio_admin_key")`. It is **never stored in `localStorage`** and is never mixed with student profile data.
   * `sessionStorage` is a session-lifetime convenience mechanism, **not a security boundary**.
   * On page refresh while on `/analytics`, the frontend restores the key from `sessionStorage` and immediately re-validates it by calling `/api/analytics/status` and `/api/analytics/summary`.
6. **Session Expiry & 401 Handling**:
   * If any analytics request returns `401 Unauthorized` (`{"error": "Unauthorized", "auth_required": true}`):
     The frontend immediately clears `sessionStorage`, resets `adminStore.isAuthenticated = false`, and returns the admin UI to the password entry screen.

---

## Routing Implementation (`src/utils/router.ts`)

A lightweight, zero-dependency History API switcher handles both top-level surfaces:

```typescript
// src/utils/router.ts
import { ref } from "vue";

// Reactive path tracking
export const currentPath = ref(window.location.pathname);

// Synchronize with browser back/forward buttons
window.addEventListener("popstate", () => {
  currentPath.value = window.location.pathname;
});

// Programmatic navigation
export function navigate(path: string) {
  if (path === window.location.pathname) return;
  window.history.pushState({}, "", path);
  currentPath.value = path;
}
```

In `App.vue`:
```html
<script setup lang="ts">
import { defineAsyncComponent } from "vue";
import { currentPath } from "./utils/router";
import LabStudio from "./views/LabStudio.vue";

// Admin dashboard is lazy-loaded: students on '/' never download admin chunk
const AdminDashboard = defineAsyncComponent(() => import("./views/AdminDashboard.vue"));
</script>

<template>
  <!-- Dedicated Admin Surface (URL-only) -->
  <AdminDashboard v-if="currentPath.startsWith('/analytics')" />
  
  <!-- Student Surface (Default for '/' and fallback for unknown paths) -->
  <LabStudio v-else />
</template>
```
* Supports direct URL navigation to `/` and `/analytics`.
* Supports browser back/forward history.
* Unknown paths cleanly fall back to `LabStudio`.
* Zero external router dependencies.
