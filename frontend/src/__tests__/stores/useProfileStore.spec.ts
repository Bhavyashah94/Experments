import { describe, it, expect, beforeEach } from 'vitest';
import { setActivePinia, createPinia } from 'pinia';
import { useProfileStore } from '@/stores/useProfileStore';

describe('useProfileStore Pinia Store', () => {
  beforeEach(() => {
    localStorage.clear();
    setActivePinia(createPinia());
  });

  it('initializes with default profile and default colors', () => {
    const store = useProfileStore();
    expect(store.profiles.length).toBeGreaterThanOrEqual(1);
    expect(store.activeProfile).toBeDefined();
    expect(store.recentColors.length).toBe(6);
  });

  it('adds a new profile and sets it as active', () => {
    const store = useProfileStore();
    const newProfile = store.addProfile('IoT Security Lab');
    expect(store.profiles.length).toBe(2);
    expect(store.activeProfileId).toBe(newProfile.id);
    expect(store.activeProfile.name).toBe('IoT Security Lab');
  });

  it('switches between profiles smoothly', () => {
    const store = useProfileStore();
    store.addProfile('Machine Learning');
    const p1Id = store.profiles[0].id;

    store.switchProfile(p1Id);
    expect(store.activeProfileId).toBe(p1Id);
  });

  it('prevents deleting the last remaining profile', () => {
    const store = useProfileStore();
    const onlyId = store.profiles[0].id;
    store.deleteProfile(onlyId);
    expect(store.profiles.length).toBe(1);
  });

  it('manages 6-color FIFO recent history buffer on color change', () => {
    const store = useProfileStore();
    store.setTextColor('#112233');
    expect(store.activeProfile.textColor).toBe('#112233');
    expect(store.recentColors[0]).toBe('#112233');
    expect(store.recentColors.length).toBe(6);

    // Push multiple colors
    store.setTextColor('#445566');
    store.setTextColor('#778899');
    expect(store.recentColors[0]).toBe('#778899');
    expect(store.recentColors[1]).toBe('#445566');
    expect(store.recentColors[2]).toBe('#112233');
    expect(store.recentColors.length).toBe(6);
  });

  it('exports and imports subject profiles with experiment configurations', () => {
    const store = useProfileStore();
    store.activeProfile.name = 'Cloud Computing Lab';
    store.activeProfile.subject = 'Cloud Computing';
    store.activeProfile.globalPerfDate = '01/02/2026';
    store.activeProfile.globalSubDate = '08/02/2026';

    const jsonStr = store.exportProfilePackage();
    expect(jsonStr).toContain('Cloud Computing Lab');
    expect(jsonStr).toContain('subject_profile_share');

    // Import into a new session
    const res = store.importProfilePackage(jsonStr);
    expect(res.success).toBe(true);
    expect(res.profileName).toBe('Cloud Computing Lab');
    expect(store.profiles.length).toBe(2);
    expect(store.activeProfile.subject).toBe('Cloud Computing');
  });
});
