import { describe, it, expect, beforeEach } from 'vitest';
import { mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import StudentHeaderForm from '@/components/student/StudentHeaderForm.vue';
import { useStudentStore } from '@/stores/useStudentStore';
import { useProfileStore } from '@/stores/useProfileStore';

describe('StudentHeaderForm.vue Component UI/UX', () => {
  beforeEach(() => {
    localStorage.clear();
    setActivePinia(createPinia());
  });

  it('renders all student input fields and binds two-way reactive state', async () => {
    const wrapper = mount(StudentHeaderForm);
    const studentStore = useStudentStore();

    const nameInput = wrapper.find('input[placeholder="e.g. Bhavya Shah"]');
    expect(nameInput.exists()).toBe(true);

    await nameInput.setValue('Alice Johnson');
    expect(studentStore.info.name).toBe('Alice Johnson');

    const rollInput = wrapper.find('input[placeholder="e.g. 34"]');
    await rollInput.setValue('42');
    expect(studentStore.info.rollNo).toBe('42');
  });

  it('allows creating a new subject profile from UI popover', async () => {
    const wrapper = mount(StudentHeaderForm);
    const profileStore = useProfileStore();

    // Click "New" profile button
    const newBtn = wrapper.find('button[title="Add new subject profile"]');
    expect(newBtn.exists()).toBe(true);
    await newBtn.trigger('click');

    // Input new profile name
    const profileInput = wrapper.find('input[placeholder*="Enter subject profile name"]');
    expect(profileInput.exists()).toBe(true);
    await profileInput.setValue('Embedded Systems Lab');

    const saveBtn = wrapper.find('button.bg-white');
    await saveBtn.trigger('click');

    expect(profileStore.profiles.length).toBe(2);
    expect(profileStore.activeProfile.name).toBe('Embedded Systems Lab');
  });

  it('toggles option checkboxes (strikethrough, autoAim, includeToc)', async () => {
    const wrapper = mount(StudentHeaderForm);
    const profileStore = useProfileStore();

    const checkboxes = wrapper.findAll('input[type="checkbox"]');
    expect(checkboxes.length).toBe(3);

    // Toggle TOC
    const tocCheckbox = checkboxes[2];
    await tocCheckbox.setValue(false);
    expect(profileStore.activeProfile.includeToc).toBe(false);
  });
});
