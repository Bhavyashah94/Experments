<script setup lang="ts">
import { ShieldCheck, BarChart3, Database } from 'lucide-vue-next'
</script>

<template>
  <div class="min-h-screen flex flex-col bg-surface text-hi selection:bg-amber-dim/50 selection:text-hi">
    <!-- Admin Header -->
    <header class="h-14 border-b border-edge bg-surface/90 backdrop-blur-md px-6 flex items-center justify-between sticky top-0 z-30">
      <div class="flex items-center space-x-3">
        <div class="w-8 h-8 rounded-lg bg-amber flex items-center justify-center shadow-sm">
          <ShieldCheck class="w-5 h-5 text-surface" />
        </div>
        <div>
          <h1 class="text-sm font-semibold tracking-tight text-hi flex items-center gap-2">
            LabStudio Admin
            <span class="text-[10px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded bg-amber-dim/30 text-amber border border-amber/30">
              Authenticated Portal
            </span>
          </h1>
          <p class="text-[11px] text-mid leading-none">
            Overview, Submission Explorer & Diagnostics
          </p>
        </div>
      </div>

      <div class="flex items-center space-x-2 text-xs text-mid">
        <Database class="w-3.5 h-3.5 text-mid" />
        <span>SQLite WAL Telemetry</span>
      </div>
    </header>

    <!-- Phase 1 Admin Shell Placeholder -->
    <main class="flex-1 max-w-6xl w-full mx-auto p-6 flex flex-col justify-center items-center text-center">
      <div class="max-w-md w-full p-8 rounded-2xl border border-edge bg-card shadow-xl">
        <div class="w-12 h-12 rounded-xl bg-input border border-edge flex items-center justify-center mx-auto mb-4 text-amber">
          <BarChart3 class="w-6 h-6" />
        </div>
        <h2 class="text-base font-semibold text-hi mb-2">
          Administrative Portal Shell
        </h2>
        <p class="text-xs text-mid leading-relaxed mb-6">
          This URL-only surface hosts submission history, raw source PDF inspection, heuristic diagnostics, and CSV export.
        </p>
        <div class="p-3 rounded-lg bg-input border border-edge text-[11px] text-mid font-mono">
          Route: /analytics &bull; Lazy Loaded Chunk
        </div>
        <p class="mt-4 text-[11px] text-lo italic">
          Password authentication and submission explorer activate in Phase 7.
        </p>
      </div>
    </main>

    <footer class="border-t border-edge py-3 text-center text-xs text-lo">
      LabStudio Internal Administration &bull; Unlinked Surface
    </footer>
  </div>
</template>
