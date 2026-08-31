import { describe, it, expect, beforeEach } from 'vitest';
import { mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { reactive } from 'vue';
import DocumentCardItem from '@/components/documents/DocumentCardItem.vue';
import type { DocumentItem } from '@/types/document';

describe('DocumentCardItem.vue Component UI/UX', () => {
  beforeEach(() => {
    localStorage.clear();
    setActivePinia(createPinia());
  });

  const createMockDoc = (): DocumentItem => ({
    id: 'doc-test-1',
    label: '1',
    isAssignment: false,
    title: 'Sensor Interfacing with ESP32',
    perfDate: '01/02/2026',
    subDate: '08/02/2026',
    hash: 'mockhash123',
    filename: 'esp32_report.pdf',
    pages: 3,
    isOpen: true,
    status: 'ready',
  });

  it('renders document card with title, page badge, and ready indicator', () => {
    const mockDoc = createMockDoc();
    const wrapper = mount(DocumentCardItem, {
      props: {
        doc: mockDoc,
        index: 0,
        total: 1,
      },
    });

    expect(wrapper.text()).toContain('Sensor Interfacing with ESP32');
    expect(wrapper.text()).toContain('3 pages');
    expect(wrapper.find('.drag-handle').exists()).toBe(true);
  });

  it('toggles Experiment vs Assignment type badge on click', async () => {
    const reactiveDoc = reactive(createMockDoc());
    const wrapper = mount(DocumentCardItem, {
      props: {
        doc: reactiveDoc,
        index: 0,
        total: 1,
      },
    });

    const typeBadge = wrapper.find('button[title*="Click to toggle between Experiment and Assignment"]');
    expect(typeBadge.text()).toBe('Exp');

    await typeBadge.trigger('click');
    expect(reactiveDoc.isAssignment).toBe(true);
    expect(typeBadge.text()).toBe('Assign');
  });

  it('emits preview event when Preview button is clicked', async () => {
    const mockDoc = createMockDoc();
    const wrapper = mount(DocumentCardItem, {
      props: {
        doc: mockDoc,
        index: 0,
        total: 1,
      },
    });

    const buttons = wrapper.findAll('button');
    const previewBtn = buttons.find((b) => b.text().includes('Preview'));
    expect(previewBtn).toBeDefined();

    await previewBtn!.trigger('click');
    expect(wrapper.emitted('preview')).toBeTruthy();
    expect(wrapper.emitted('preview')![0]).toEqual([mockDoc]);
  });
});
