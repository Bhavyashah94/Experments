import { describe, it, expect, beforeEach } from 'vitest';
import { setActivePinia, createPinia } from 'pinia';
import { useLabStore } from '../store';

describe('LabStudio Store Logic', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('correctly tracks the 6 compulsory student fields', () => {
    const store = useLabStore();

    // Initially all 6 required fields are empty
    expect(store.isStudentComplete).toBe(false);
    expect(store.missingStudentFields).toContain('Name');
    expect(store.missingStudentFields).toContain('Roll No');
    expect(store.missingStudentFields).toContain('Batch');
    expect(store.missingStudentFields).toContain('Class');
    expect(store.missingStudentFields).toContain('Semester');
    expect(store.missingStudentFields).toContain('Subject');

    // Fill 5 of 6 fields
    store.student.name = 'Bhavya Shah';
    store.student.rollNo = '34';
    store.student.batch = 'I3';
    store.student.className = 'BE IT';
    store.student.sem = 'VII';

    expect(store.isStudentComplete).toBe(false);
    expect(store.missingStudentFields).toEqual(['Subject']);

    // Fill the 6th field (Subject)
    store.student.subject = 'Internet of Things';
    expect(store.isStudentComplete).toBe(true);
    expect(store.missingStudentFields).toHaveLength(0);
  });

  it('keeps dates strictly optional and allows compiling with blank dates', () => {
    const store = useLabStore();

    // Fill all 6 required student fields
    store.student.name = 'Bhavya Shah';
    store.student.rollNo = '34';
    store.student.batch = 'I3';
    store.student.className = 'BE IT';
    store.student.sem = 'VII';
    store.student.subject = 'Internet of Things';

    // Set an experiment title
    store.documents[0].title = 'Study of MQTT';

    // Dates remain empty
    expect(store.student.globalPerfDate).toBe('');
    expect(store.student.globalSubDate).toBe('');
    expect(store.documents[0].perfDate).toBe('');
    expect(store.documents[0].subDate).toBe('');

    // Compilation MUST be allowed with blank dates!
    expect(store.canCompile).toBe(true);
    expect(store.compileStatusText).toBe('Compile Lab Report (1 doc)');
  });

  it('blocks compilation if any experiment title is missing', () => {
    const store = useLabStore();

    // Student info complete
    store.student.name = 'Bhavya';
    store.student.rollNo = '34';
    store.student.batch = 'I3';
    store.student.className = 'BE IT';
    store.student.sem = 'VII';
    store.student.subject = 'IoT';

    // Document 1 has title, document 2 is empty
    store.documents[0].title = 'Exp 1 Aim';
    store.addDocument(); // adds document 2 with blank title

    expect(store.missingDocTitles).toBe(1);
    expect(store.canCompile).toBe(false);
    expect(store.compileStatusText).toBe('Enter title for all 2 experiments');
  });

  it('correctly auto-fills weekly dates (+7 days) sequentially', () => {
    const store = useLabStore();
    store.addDocument();
    store.addDocument(); // 3 documents total

    store.student.globalPerfDate = '01/08/2026';
    store.student.globalSubDate = '08/08/2026';

    store.applyWeeklyDates();

    expect(store.documents[0].perfDate).toBe('01/08/2026');
    expect(store.documents[0].subDate).toBe('08/08/2026');

    expect(store.documents[1].perfDate).toBe('08/08/2026');
    expect(store.documents[1].subDate).toBe('15/08/2026');

    expect(store.documents[2].perfDate).toBe('15/08/2026');
    expect(store.documents[2].subDate).toBe('22/08/2026');
  });

  it('reorders and automatically renumbers documents', () => {
    const store = useLabStore();
    store.documents[0].title = 'Exp 1';
    const doc2 = store.addDocument();
    doc2.title = 'Exp 2';

    expect(store.documents[0].num).toBe('1');
    expect(store.documents[1].num).toBe('2');

    // Move item 1 down
    store.reorder(0, 1);

    expect(store.documents[0].title).toBe('Exp 2');
    expect(store.documents[0].num).toBe('1'); // renumbered!
    expect(store.documents[1].title).toBe('Exp 1');
    expect(store.documents[1].num).toBe('2'); // renumbered!
  });
});
