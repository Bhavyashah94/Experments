import { describe, it, expect, beforeEach } from 'vitest';
import { setActivePinia, createPinia } from 'pinia';
import { useStudentStore } from '@/stores/useStudentStore';

describe('useStudentStore Pinia Store', () => {
  beforeEach(() => {
    localStorage.clear();
    setActivePinia(createPinia());
  });

  it('initializes with student metadata object', () => {
    const store = useStudentStore();
    expect(store.info).toBeDefined();
    expect(store.info.name).toBe('');
    expect(store.info.rollNo).toBe('');
  });

  it('updates student info with setInfo', () => {
    const store = useStudentStore();
    store.setInfo({
      name: 'Bhavya Shah',
      rollNo: '34',
      batch: 'I3',
      className: 'BE IT',
      sem: 'VII',
    });

    expect(store.info.name).toBe('Bhavya Shah');
    expect(store.info.rollNo).toBe('34');
    expect(store.info.batch).toBe('I3');
    expect(store.info.className).toBe('BE IT');
    expect(store.info.sem).toBe('VII');
  });
});
