import { describe, it, expect, beforeEach } from 'vitest';
import { setActivePinia, createPinia } from 'pinia';
import { useDocumentStore } from '@/stores/useDocumentStore';
import { useProfileStore } from '@/stores/useProfileStore';

describe('useDocumentStore Pinia Store', () => {
  beforeEach(() => {
    localStorage.clear();
    setActivePinia(createPinia());
  });

  it('initializes with at least one document card', () => {
    const store = useDocumentStore();
    expect(store.documents.length).toBeGreaterThanOrEqual(1);
    expect(store.documents[0].label).toBe('1');
    expect(store.documents[0].isOpen).toBe(true);
  });

  it('adds document card with auto-incremented number label', () => {
    const store = useDocumentStore();
    const doc2 = store.addDocument();
    expect(store.documents.length).toBe(2);
    expect(doc2.label).toBe('2');

    const doc3 = store.addDocument();
    expect(doc3.label).toBe('3');
  });

  it('removes document card by ID', () => {
    const store = useDocumentStore();
    const doc2 = store.addDocument();
    expect(store.documents.length).toBe(2);

    store.removeDocument(doc2.id);
    expect(store.documents.length).toBe(1);
  });

  it('toggles expand / collapse across all cards', () => {
    const store = useDocumentStore();
    store.addDocument();
    expect(store.documents.every((d) => d.isOpen)).toBe(true);

    store.toggleAllCards(false);
    expect(store.documents.every((d) => !d.isOpen)).toBe(true);

    store.toggleAllCards(true);
    expect(store.documents.every((d) => d.isOpen)).toBe(true);
  });

  it('applies global dates across all cards', () => {
    const profileStore = useProfileStore();
    const store = useDocumentStore();
    store.addDocument();

    profileStore.activeProfile.globalPerfDate = '10/10/2026';
    profileStore.activeProfile.globalSubDate = '17/10/2026';

    store.applyGlobalDates();

    expect(store.documents[0].perfDate).toBe('10/10/2026');
    expect(store.documents[0].subDate).toBe('17/10/2026');
    expect(store.documents[1].perfDate).toBe('10/10/2026');
    expect(store.documents[1].subDate).toBe('17/10/2026');
  });

  it('applies sequential +7 days weekly dates series across cards', () => {
    const profileStore = useProfileStore();
    const store = useDocumentStore();
    store.addDocument();
    store.addDocument(); // 3 documents total

    profileStore.activeProfile.globalPerfDate = '01/03/2026';
    profileStore.activeProfile.globalSubDate = '08/03/2026';

    store.applyWeeklyDates();

    expect(store.documents[0].perfDate).toBe('01/03/2026');
    expect(store.documents[1].perfDate).toBe('08/03/2026');
    expect(store.documents[2].perfDate).toBe('15/03/2026');

    expect(store.documents[0].subDate).toBe('08/03/2026');
    expect(store.documents[1].subDate).toBe('15/03/2026');
    expect(store.documents[2].subDate).toBe('22/03/2026');
  });

  it('clears all documents to empty array with clearAllDocuments and persists across reloads', () => {
    const store = useDocumentStore();
    const profileStore = useProfileStore();
    store.addDocument();
    expect(store.documents.length).toBe(2);

    store.clearAllDocuments();
    expect(store.documents.length).toBe(0);

    // Simulate page reload by re-loading profile documents
    store.loadProfileDocuments(profileStore.activeProfileId);
    expect(store.documents.length).toBe(0);
  });

  it('renumbers document cards sequentially with renumberDocuments', () => {
    const store = useDocumentStore();
    store.addDocument();
    store.addDocument();

    // Manually scramble or delete labels
    store.documents[0].label = '4';
    store.documents[1].label = '8';
    store.documents[2].label = '2';

    store.renumberDocuments();

    expect(store.documents[0].label).toBe('1');
    expect(store.documents[1].label).toBe('2');
    expect(store.documents[2].label).toBe('3');
  });
});
