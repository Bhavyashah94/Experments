import type { GlobalStudentInfo, SubjectProfile } from '@/types/student';
import type { DocumentItem } from '@/types/document';

export const STORAGE_KEYS = {
  GLOBAL_STUDENT: 'lab_header_global_student_v2',
  PROFILES: 'lab_header_profiles_v2',
  CURRENT_PROFILE: 'lab_header_current_profile_v2',
  COLOR_HISTORY: 'lab_header_color_history_v2',
  DOCUMENTS: 'lab_header_documents_v2', // keyed by profileId
};

export const DEFAULT_COLORS = [
  '#0000bf', // Royal Blue
  '#000080', // Navy
  '#000000', // Pure Black
  '#cc0000', // Crimson
  '#047857', // Emerald
  '#6b21a8', // Violet
];

export function safeLocalStorageSet(key: string, value: unknown): boolean {
  try {
    localStorage.setItem(key, JSON.stringify(value));
    return true;
  } catch (err: any) {
    if (
      err.name === 'QuotaExceededError' ||
      err.name === 'NS_ERROR_DOM_QUOTA_REACHED' ||
      err.code === 22
    ) {
      console.warn('[Storage] Quota exceeded. Evicting non-critical cache...');
      localStorage.removeItem(STORAGE_KEYS.COLOR_HISTORY);
      try {
        localStorage.setItem(key, JSON.stringify(value));
        return true;
      } catch {
        return false;
      }
    }
    return false;
  }
}

export function safeLocalStorageGet<T>(key: string, fallback: T): T {
  try {
    const item = localStorage.getItem(key);
    return item ? JSON.parse(item) : fallback;
  } catch {
    return fallback;
  }
}

export function migrateV1ToV2(): void {
  const v1ProfilesRaw = localStorage.getItem('lab_header_profiles_v1');
  const v1GlobalStudentRaw = localStorage.getItem('lab_header_global_student_v1');

  if (v1ProfilesRaw && !localStorage.getItem(STORAGE_KEYS.PROFILES)) {
    try {
      const v1Profiles = JSON.parse(v1ProfilesRaw);
      const v1Global = v1GlobalStudentRaw ? JSON.parse(v1GlobalStudentRaw) : {};

      // Migrate Global Student Info
      const globalInfo: GlobalStudentInfo = {
        name: v1Global.name || '',
        rollNo: v1Global.roll_no || '',
        batch: v1Global.batch || '',
        className: v1Global.class_name || '',
        sem: v1Global.sem || '',
      };
      safeLocalStorageSet(STORAGE_KEYS.GLOBAL_STUDENT, globalInfo);

      // Migrate Profiles
      const migratedProfiles: SubjectProfile[] = [];
      const migratedDocsMap: Record<string, DocumentItem[]> = {};

      for (const [profName, profData] of Object.entries<any>(v1Profiles)) {
        const profileId = crypto.randomUUID();
        migratedProfiles.push({
          id: profileId,
          name: profName,
          subject: profData.student?.subject || '',
          textColor: profData.student?.text_color || '#0000bf',
          strikethroughEnabled: profData.student?.strikethrough_enabled ?? true,
          autoAim: profData.autoAim ?? true,
          aimMode: profData.aimMode || 'auto',
          includeToc: true,
          globalPerfDate: profData.globalPerf || '',
          globalSubDate: profData.globalSub || '',
        });

        migratedDocsMap[profileId] = (profData.rows || []).map((r: any, idx: number) => ({
          id: r.rowId || crypto.randomUUID(),
          label: String(r.label || idx + 1),
          isAssignment: Boolean(r.is_assignment),
          title: r.title || '',
          perfDate: r.perf_date || '',
          subDate: r.sub_date || '',
          hash: r.hash || null,
          filename: r.filename || null,
          pages: r.pages || 0,
          isOpen: true,
          status: r.hash ? 'ready' : 'idle',
        }));
      }

      if (migratedProfiles.length > 0) {
        safeLocalStorageSet(STORAGE_KEYS.PROFILES, migratedProfiles);
        safeLocalStorageSet(STORAGE_KEYS.CURRENT_PROFILE, migratedProfiles[0].id);
        for (const [pId, docs] of Object.entries(migratedDocsMap)) {
          safeLocalStorageSet(`${STORAGE_KEYS.DOCUMENTS}_${pId}`, docs);
        }
        console.info('[Storage] Successfully migrated v1 LocalStorage to v2 schema');
      }
    } catch (e) {
      console.warn('[Storage] Migration failed gracefully:', e);
    }
  }
}
