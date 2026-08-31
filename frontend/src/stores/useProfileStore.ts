import { defineStore } from 'pinia';
import { ref, computed, watch } from 'vue';
import { useDebounceFn } from '@vueuse/core';
import type { SubjectProfile } from '@/types/student';
import type { DocumentItem } from '@/types/document';
import {
  STORAGE_KEYS,
  DEFAULT_COLORS,
  safeLocalStorageGet,
  safeLocalStorageSet,
} from '@/services/storage';

export interface ExportedProfilePackage {
  labstudio_version: string;
  type: string;
  profile: Omit<SubjectProfile, 'id'>;
  experiments: Array<{
    label: string;
    isAssignment: boolean;
    title: string;
    perfDate: string;
    subDate: string;
  }>;
}

function createDefaultProfile(name: string = 'Default'): SubjectProfile {
  return {
    id: crypto.randomUUID(),
    name,
    subject: '',
    textColor: '#0000bf',
    strikethroughEnabled: true,
    autoAim: true,
    aimMode: 'auto',
    includeToc: true,
    globalPerfDate: '',
    globalSubDate: '',
  };
}

export const useProfileStore = defineStore('profile', () => {
  const initialProfiles = safeLocalStorageGet<SubjectProfile[]>(STORAGE_KEYS.PROFILES, [
    createDefaultProfile('Default'),
  ]);

  const profiles = ref<SubjectProfile[]>(initialProfiles);
  const activeProfileId = ref<string>(
    safeLocalStorageGet<string>(STORAGE_KEYS.CURRENT_PROFILE, initialProfiles[0]?.id || '')
  );

  const recentColors = ref<string[]>(
    safeLocalStorageGet<string[]>(STORAGE_KEYS.COLOR_HISTORY, [...DEFAULT_COLORS])
  );

  const activeProfile = computed<SubjectProfile>(() => {
    let p = profiles.value.find((prof) => prof.id === activeProfileId.value);
    if (!p) {
      p = profiles.value[0] || createDefaultProfile('Default');
      activeProfileId.value = p.id;
    }
    return p;
  });

  const persist = useDebounceFn(() => {
    safeLocalStorageSet(STORAGE_KEYS.PROFILES, profiles.value);
    safeLocalStorageSet(STORAGE_KEYS.CURRENT_PROFILE, activeProfileId.value);
    safeLocalStorageSet(STORAGE_KEYS.COLOR_HISTORY, recentColors.value);
  }, 300);

  watch([profiles, activeProfileId, recentColors], persist, { deep: true });

  function addProfile(name: string): SubjectProfile {
    const trimmed = name.trim() || `Profile ${profiles.value.length + 1}`;
    const newProf = createDefaultProfile(trimmed);
    profiles.value.push(newProf);
    activeProfileId.value = newProf.id;
    return newProf;
  }

  function deleteProfile(id: string): void {
    if (profiles.value.length <= 1) return; // Keep at least one profile
    const idx = profiles.value.findIndex((p) => p.id === id);
    if (idx !== -1) {
      profiles.value.splice(idx, 1);
      if (activeProfileId.value === id) {
        activeProfileId.value = profiles.value[0].id;
      }
    }
  }

  function switchProfile(id: string): void {
    const exists = profiles.value.some((p) => p.id === id);
    if (exists) {
      activeProfileId.value = id;
    }
  }

  function pushColor(hex: string): void {
    if (!/^#[0-9a-fA-F]{6}$/.test(hex)) return;
    const lower = hex.toLowerCase();
    const filtered = recentColors.value.filter((c) => c.toLowerCase() !== lower);
    filtered.unshift(lower);
    recentColors.value = filtered.slice(0, 6);
  }

  function setTextColor(hex: string): void {
    activeProfile.value.textColor = hex;
    pushColor(hex);
  }

  function exportProfilePackage(targetId?: string): string {
    const id = targetId || activeProfileId.value;
    const profile = profiles.value.find((p) => p.id === id) || activeProfile.value;
    const docsKey = `${STORAGE_KEYS.DOCUMENTS}_${profile.id}`;
    const docs = safeLocalStorageGet<DocumentItem[]>(docsKey, []);

    const pkg: ExportedProfilePackage = {
      labstudio_version: '2.1',
      type: 'subject_profile_share',
      profile: {
        name: profile.name,
        subject: profile.subject,
        textColor: profile.textColor,
        strikethroughEnabled: profile.strikethroughEnabled,
        autoAim: profile.autoAim,
        aimMode: profile.aimMode,
        includeToc: profile.includeToc,
        globalPerfDate: profile.globalPerfDate,
        globalSubDate: profile.globalSubDate,
      },
      experiments: docs.map((d) => ({
        label: d.label,
        isAssignment: d.isAssignment,
        title: d.title,
        perfDate: d.perfDate,
        subDate: d.subDate,
      })),
    };

    return JSON.stringify(pkg, null, 2);
  }

  function importProfilePackage(jsonStr: string): { success: boolean; profileName?: string; count?: number; error?: string } {
    try {
      const parsed = JSON.parse(jsonStr);
      if (!parsed.profile || typeof parsed.profile !== 'object') {
        return { success: false, error: 'Invalid profile format. Missing profile object.' };
      }

      const pData = parsed.profile;
      const rawName = (pData.name || pData.subject || 'Imported Subject').trim();
      const newProf = createDefaultProfile(rawName);

      if (pData.subject) newProf.subject = pData.subject;
      if (pData.textColor) newProf.textColor = pData.textColor;
      if (typeof pData.strikethroughEnabled === 'boolean') newProf.strikethroughEnabled = pData.strikethroughEnabled;
      if (typeof pData.autoAim === 'boolean') newProf.autoAim = pData.autoAim;
      if (typeof pData.includeToc === 'boolean') newProf.includeToc = pData.includeToc;
      if (pData.globalPerfDate) newProf.globalPerfDate = pData.globalPerfDate;
      if (pData.globalSubDate) newProf.globalSubDate = pData.globalSubDate;

      profiles.value.push(newProf);

      // Create document items from shared experiments
      const exps = Array.isArray(parsed.experiments) ? parsed.experiments : [];
      const newDocs: DocumentItem[] = exps.map((e: any, idx: number) => ({
        id: `doc_${Date.now()}_${idx}_${Math.random().toString(36).substr(2, 4)}`,
        label: String(e.label || idx + 1),
        isAssignment: Boolean(e.isAssignment),
        title: String(e.title || ''),
        perfDate: String(e.perfDate || newProf.globalPerfDate || ''),
        subDate: String(e.subDate || newProf.globalSubDate || ''),
        hash: null,
        filename: null,
        pages: 0,
        isOpen: true,
        status: 'idle',
      }));

      // If empty, add 1 default card
      if (newDocs.length === 0) {
        newDocs.push({
          id: `doc_${Date.now()}_0`,
          label: '1',
          isAssignment: false,
          title: '',
          perfDate: newProf.globalPerfDate || '',
          subDate: newProf.globalSubDate || '',
          hash: null,
          filename: null,
          pages: 0,
          isOpen: true,
          status: 'idle',
        });
      }

      const docsKey = `${STORAGE_KEYS.DOCUMENTS}_${newProf.id}`;
      safeLocalStorageSet(docsKey, newDocs);

      activeProfileId.value = newProf.id;
      return { success: true, profileName: newProf.name, count: newDocs.length };
    } catch (err: any) {
      return { success: false, error: err.message || 'Malformed JSON file.' };
    }
  }

  return {
    profiles,
    activeProfileId,
    activeProfile,
    recentColors,
    addProfile,
    deleteProfile,
    switchProfile,
    pushColor,
    setTextColor,
    exportProfilePackage,
    importProfilePackage,
  };
});
