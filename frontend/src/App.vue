<script setup lang="ts">
import { defineAsyncComponent } from 'vue'
import { currentPath } from './utils/router'
import LabStudio from './views/LabStudio.vue'

// Lazy-load admin surface so students on '/' never download admin code
const AdminDashboard = defineAsyncComponent(() => import('./views/AdminDashboard.vue'))
</script>

<template>
  <!-- Exact match for /analytics renders dedicated Admin Portal -->
  <AdminDashboard v-if="currentPath === '/analytics'" />

  <!-- Student surface for '/' and clean fallback for any unknown path -->
  <LabStudio v-else />
</template>
