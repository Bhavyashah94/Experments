import { defineStore } from 'pinia';
import { ref, watch } from 'vue';
import { useDebounceFn } from '@vueuse/core';
import type { GlobalStudentInfo } from '@/types/student';
import { STORAGE_KEYS, safeLocalStorageGet, safeLocalStorageSet } from '@/services/storage';

export const useStudentStore = defineStore('student', () => {
  const info = ref<GlobalStudentInfo>(
    safeLocalStorageGet<GlobalStudentInfo>(STORAGE_KEYS.GLOBAL_STUDENT, {
      name: '',
      rollNo: '',
      batch: '',
      className: '',
      sem: '',
    })
  );

  const persist = useDebounceFn(() => {
    safeLocalStorageSet(STORAGE_KEYS.GLOBAL_STUDENT, info.value);
  }, 300);

  watch(info, persist, { deep: true });

  function setInfo(newInfo: Partial<GlobalStudentInfo>) {
    Object.assign(info.value, newInfo);
  }

  return {
    info,
    setInfo,
  };
});
