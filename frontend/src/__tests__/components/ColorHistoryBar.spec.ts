import { describe, it, expect, beforeEach } from 'vitest';
import { mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import ColorHistoryBar from '@/components/student/ColorHistoryBar.vue';
import { useProfileStore } from '@/stores/useProfileStore';

describe('ColorHistoryBar.vue Component UI/UX', () => {
  beforeEach(() => {
    localStorage.clear();
    setActivePinia(createPinia());
  });

  it('renders presets and updates store color when preset is clicked', async () => {
    const wrapper = mount(ColorHistoryBar);
    const profileStore = useProfileStore();

    // Click Crimson swatch (#cc0000)
    const crimsonBtn = wrapper.find('button[title="#cc0000"]');
    expect(crimsonBtn.exists()).toBe(true);

    await crimsonBtn.trigger('click');
    expect(profileStore.activeProfile.textColor).toBe('#cc0000');
  });

  it('updates text color when valid hex is typed into hex input', async () => {
    const wrapper = mount(ColorHistoryBar);
    const profileStore = useProfileStore();

    const hexInput = wrapper.find('input[type="text"]');
    await hexInput.setValue('#047857');
    await hexInput.trigger('blur');

    expect(profileStore.activeProfile.textColor).toBe('#047857');
  });
});
