import { describe, it, expect, beforeEach } from 'vitest';
import { setActivePinia, createPinia } from 'pinia';
import { useLabStore } from '../store';

describe('LabStudio Phase 2 Store Logic', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('strictly enforces the 6 compulsory student fields', () => {
    const store = useLabStore();

    expect(store.isStudentComplete).toBe(false);
    expect(store.missingStudentFields).toEqual(['Name', 'Roll No', 'Batch', 'Class', 'Semester', 'Subject']);

    store.student.name = 'Bhavya Shah';
    store.student.rollNo = '34';
    store.student.batch = 'I3';
    store.student.className = 'BE IT';
    store.student.sem = 'VII';
    expect(store.isStudentComplete).toBe(false);
    expect(store.missingStudentFields).toEqual(['Subject']);

    store.student.subject = 'Internet of Things';
    expect(store.isStudentComplete).toBe(true);
    expect(store.missingStudentFields).toHaveLength(0);
  });

  it('keeps dates strictly optional and allows compiling with blank dates', () => {
    const store = useLabStore();

    store.student.name = 'Bhavya';
    store.student.rollNo = '34';
    store.student.batch = 'I3';
    store.student.className = 'BE IT';
    store.student.sem = 'VII';
    store.student.subject = 'Internet of Things';
    store.documents[0].title = 'Study of MQTT';

    expect(store.student.globalPerfDate).toBe('');
    expect(store.student.globalSubDate).toBe('');
    expect(store.documents[0].perfDate).toBe('');
    expect(store.documents[0].subDate).toBe('');

    // Must be allowed to compile without any dates!
    expect(store.canCompile).toBe(true);
  });

  it('parses both DD/MM/YYYY and ISO YYYY-MM-DD formats reliably', () => {
    const store = useLabStore();

    // Standard DD/MM/YYYY
    const d1 = store.parseDate('15/08/2026');
    expect(d1).not.toBeNull();
    expect(d1?.getDate()).toBe(15);
    expect(d1?.getMonth()).toBe(7); // August = 7
    expect(d1?.getFullYear()).toBe(2026);

    // ISO format YYYY-MM-DD
    const d2 = store.parseDate('2026-08-15');
    expect(d2).not.toBeNull();
    expect(d2?.getDate()).toBe(15);
    expect(d2?.getMonth()).toBe(7);
    expect(d2?.getFullYear()).toBe(2026);

    // Invalid calendar dates reject gracefully
    expect(store.parseDate('31/02/2026')).toBeNull(); // Feb 31 does not exist
    expect(store.parseDate('')).toBeNull();
    expect(store.parseDate('not-a-date')).toBeNull();
  });

  it('calculates weekly dates (+7 days) across month and leap-year boundaries', () => {
    const store = useLabStore();
    store.addDocument();
    store.addDocument(); // 3 documents total

    store.student.globalPerfDate = '25/02/2028'; // 2028 is a leap year (Feb 29)
    store.applyWeeklyDates();

    expect(store.documents[0].perfDate).toBe('25/02/2028');
    expect(store.documents[1].perfDate).toBe('03/03/2028'); // 25 + 7 in leap year = March 3
    expect(store.documents[2].perfDate).toBe('10/03/2028');
  });

  it('preserves custom sub-experiment numbers (e.g. 1a, 1b) when reordering', () => {
    const store = useLabStore();
    store.documents[0].num = '1a';
    store.documents[0].title = 'Exp 1a';

    const doc2 = store.addDocument();
    doc2.num = '1b';
    doc2.title = 'Exp 1b';

    // Move doc 1 down
    store.reorder(0, 1);

    // Custom non-integer numbers MUST NOT be wiped to 1 and 2!
    expect(store.documents[0].num).toBe('1b');
    expect(store.documents[1].num).toBe('1a');
  });

  it('synchronizes student edits back to the active subject profile bidirectionally', async () => {
    const store = useLabStore();

    store.student.subject = 'Cloud Computing';
    store.student.textColor = '#005000';

    // Allow reactive watcher tick
    await new Promise((resolve) => setTimeout(resolve, 50));

    const active = store.profiles.find((p) => p.id === store.activeProfileId);
    expect(active?.subject).toBe('Cloud Computing');
    expect(active?.textColor).toBe('#005000');
  });
});
