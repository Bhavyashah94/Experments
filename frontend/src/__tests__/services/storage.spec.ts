import { describe, it, expect, beforeEach } from 'vitest';
import {
  STORAGE_KEYS,
  safeLocalStorageGet,
  safeLocalStorageSet,
  migrateV1ToV2,
} from '@/services/storage';

describe('Storage Service & Migration', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('safely gets and sets items in localStorage', () => {
    safeLocalStorageSet('test_key', { foo: 'bar' });
    const result = safeLocalStorageGet('test_key', { foo: 'default' });
    expect(result).toEqual({ foo: 'bar' });
  });

  it('returns fallback value when key does not exist or JSON is invalid', () => {
    expect(safeLocalStorageGet('non_existent', 'fallback')).toBe('fallback');
    localStorage.setItem('corrupted', '{bad json');
    expect(safeLocalStorageGet('corrupted', 42)).toBe(42);
  });

  it('migrates legacy v1 localStorage schemas to typed v2 structures', () => {
    // Setup synthetic legacy v1 data
    const v1Global = {
      name: 'Legacy Student',
      roll_no: '88',
      batch: 'B1',
      class_name: 'TE IT',
      sem: 'VI',
    };
    const v1Profiles = {
      'Cloud Computing': {
        student: {
          subject: 'Cloud Computing',
          text_color: '#000080',
          strikethrough_enabled: true,
        },
        autoAim: true,
        aimMode: 'auto',
        globalPerf: '01/01/2026',
        globalSub: '08/01/2026',
        rows: [
          {
            rowId: 'row-1',
            label: '1',
            is_assignment: false,
            title: 'AWS S3 Setup',
            perf_date: '01/01/2026',
            sub_date: '08/01/2026',
            hash: 'abc123hash',
            filename: 'exp1.pdf',
            pages: 4,
          },
        ],
      },
    };

    localStorage.setItem('lab_header_global_student_v1', JSON.stringify(v1Global));
    localStorage.setItem('lab_header_profiles_v1', JSON.stringify(v1Profiles));

    // Run migration
    migrateV1ToV2();

    // Verify v2 global student
    const migratedGlobal = safeLocalStorageGet<any>(STORAGE_KEYS.GLOBAL_STUDENT, null);
    expect(migratedGlobal).not.toBeNull();
    expect(migratedGlobal.name).toBe('Legacy Student');
    expect(migratedGlobal.rollNo).toBe('88');

    // Verify v2 profile
    const migratedProfiles = safeLocalStorageGet<any[]>(STORAGE_KEYS.PROFILES, []);
    expect(migratedProfiles.length).toBe(1);
    expect(migratedProfiles[0].name).toBe('Cloud Computing');
    expect(migratedProfiles[0].subject).toBe('Cloud Computing');
    expect(migratedProfiles[0].textColor).toBe('#000080');

    // Verify v2 documents
    const pId = migratedProfiles[0].id;
    const migratedDocs = safeLocalStorageGet<any[]>(`${STORAGE_KEYS.DOCUMENTS}_${pId}`, []);
    expect(migratedDocs.length).toBe(1);
    expect(migratedDocs[0].title).toBe('AWS S3 Setup');
    expect(migratedDocs[0].pages).toBe(4);
    expect(migratedDocs[0].status).toBe('ready');
  });
});
