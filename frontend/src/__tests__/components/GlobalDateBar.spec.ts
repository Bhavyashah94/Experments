import { describe, it, expect, beforeEach } from 'vitest';
import { mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import GlobalDateBar from '@/components/student/GlobalDateBar.vue';
import { useProfileStore } from '@/stores/useProfileStore';
import { useDocumentStore } from '@/stores/useDocumentStore';

describe('GlobalDateBar.vue Component UI/UX', () => {
  beforeEach(() => {
    localStorage.clear();
    setActivePinia(createPinia());
  });

  it('triggers Apply All button and copies dates to document store', async () => {
    const wrapper = mount(GlobalDateBar);
    const profileStore = useProfileStore();
    const documentStore = useDocumentStore();

    profileStore.activeProfile.globalPerfDate = '05/05/2026';
    profileStore.activeProfile.globalSubDate = '12/05/2026';

    const applyAllBtn = wrapper.find('button[title*="Copy these global dates"]');
    expect(applyAllBtn.exists()).toBe(true);

    await applyAllBtn.trigger('click');
    expect(documentStore.documents[0].perfDate).toBe('05/05/2026');
    expect(documentStore.documents[0].subDate).toBe('12/05/2026');
  });

  it('triggers +7 Days Weekly Auto-Fill button', async () => {
    const wrapper = mount(GlobalDateBar);
    const profileStore = useProfileStore();
    const documentStore = useDocumentStore();
    documentStore.addDocument(); // 2 documents

    profileStore.activeProfile.globalPerfDate = '01/01/2026';
    profileStore.activeProfile.globalSubDate = '08/01/2026';

    const weeklyBtn = wrapper.find('button[title*="Auto-fill sequential weekly dates"]');
    expect(weeklyBtn.exists()).toBe(true);

    await weeklyBtn.trigger('click');
    expect(documentStore.documents[0].perfDate).toBe('01/01/2026');
    expect(documentStore.documents[1].perfDate).toBe('08/01/2026');
  });
});
