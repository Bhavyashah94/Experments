<script setup lang="ts">
import { student, studentErrors } from '../../store/labStore'
</script>

<template>
  <div class="bg-card border border-edge rounded-xl p-4 shadow-sm space-y-3 select-none">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <span class="text-xs font-semibold text-hi uppercase tracking-wider">
        Student Details:
      </span>
      <span class="text-[10px] text-lo font-medium">One-time setup</span>
    </div>

    <!-- Student Name & Roll Number -->
    <div class="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
      <div>
        <label class="block text-[11px] font-medium text-mid mb-1">Student Name</label>
        <input
          v-model="student.name"
          type="text"
          placeholder="e.g. Bhavya Shah"
          class="w-full bg-input border border-edge rounded-lg px-2.5 py-1.5 text-xs text-hi outline-none focus:border-amber transition"
          :class="{ 'border-danger': studentErrors.name }"
        />
      </div>

      <div>
        <label class="block text-[11px] font-medium text-mid mb-1">Roll Number</label>
        <input
          v-model="student.roll_no"
          type="text"
          placeholder="e.g. 77"
          class="w-full bg-input border border-edge rounded-lg px-2.5 py-1.5 text-xs text-hi outline-none focus:border-amber transition"
          :class="{ 'border-danger': studentErrors.roll_no }"
        />
      </div>
    </div>

    <!-- Batch & Class -->
    <div class="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
      <div>
        <label class="block text-[11px] font-medium text-mid mb-1">Batch</label>
        <input
          v-model="student.batch"
          type="text"
          placeholder="e.g. B3"
          class="w-full bg-input border border-edge rounded-lg px-2.5 py-1.5 text-xs text-hi outline-none focus:border-amber transition"
        />
      </div>

      <div>
        <label class="block text-[11px] font-medium text-mid mb-1">Class / Division</label>
        <input
          v-model="student.class_name"
          type="text"
          placeholder="e.g. BE IT"
          class="w-full bg-input border border-edge rounded-lg px-2.5 py-1.5 text-xs text-hi outline-none focus:border-amber transition"
        />
      </div>
    </div>

    <!-- Semester -->
    <div>
      <label class="block text-[11px] font-medium text-mid mb-1">Semester</label>
      <input
        v-model="student.sem"
        type="text"
        placeholder="e.g. VII"
        class="w-full bg-input border border-edge rounded-lg px-2.5 py-1.5 text-xs text-hi outline-none focus:border-amber transition"
      />
    </div>
  </div>
</template>
