import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import AnalyticsDashboard from '@/components/analytics/AnalyticsDashboard.vue';
import { ApiService } from '@/services/api';

describe('AnalyticsDashboard Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    sessionStorage.clear();

    vi.spyOn(ApiService, 'checkHealth').mockResolvedValue({
      status: 'ok',
      version: '2.1.0',
      uptime_seconds: 3600,
      storage: { max_bytes: 16106127360, used_bytes: 500000000, percent_used: 3.1 },
    });

    vi.spyOn(ApiService, 'getAnalyticsDiagnostics').mockResolvedValue({
      success: true,
      data: {
        summary: {
          total_documents: 10,
          success_rate_percent: 90,
          methods: { aim_keyword: 9 },
          failures: {},
          discrepancies_count: 1,
        },
        samples: [],
        total: 0,
        limit: 20,
        offset: 0,
      },
    });
  });

  it('renders analytics metrics when authenticated and data loads', async () => {
    vi.spyOn(ApiService, 'getAnalyticsStatus').mockResolvedValue({
      enabled: true,
      auth_required: false,
    });

    vi.spyOn(ApiService, 'getAnalyticsSummary').mockResolvedValue({
      success: true,
      data: {
        total_generations: 42,
        successful_generations: 40,
        failed_generations: 2,
        success_rate: 95.2,
        avg_duration_ms: 185.4,
        total_experiments_generated: 120,
        unique_students: 18,
        daily_trends: [
          { date: '2026-09-01', count: 20, successes: 19 },
          { date: '2026-09-02', count: 22, successes: 21 },
        ],
        top_subjects: [
          { subject: 'Internet of Things', count: 25, students: 12 },
          { subject: 'Cloud Computing', count: 17, students: 8 },
        ],
        top_experiments: [
          { name: 'Exp 1: MQTT Nodes', count: 20 },
        ],
      },
    });

    vi.spyOn(ApiService, 'getAnalyticsEvents').mockResolvedValue({
      success: true,
      data: {
        events: [
          {
            id: 1,
            timestamp: '2026-09-02T12:00:00Z',
            student_name: 'Bhavya Shah',
            roll_no: '34',
            batch: 'I3',
            class_name: 'BE IT',
            sem: 'VII',
            subject: 'Internet of Things',
            experiment_count: 5,
            experiments: [],
            generation_type: 'batch_package',
            success: true,
            error_message: null,
            duration_ms: 190.2,
          },
        ],
        total: 1,
        limit: 20,
        offset: 0,
      },
    });

    const wrapper = mount(AnalyticsDashboard);
    await flushPromises();

    // Verify key metrics render
    expect(wrapper.text()).toContain('Usage Analytics');
    expect(wrapper.text()).toContain('42');
    expect(wrapper.text()).toContain('18');
    expect(wrapper.text()).toContain('95.2%');
    expect(wrapper.text()).toContain('Internet of Things');

    // Switch to Generation Logs tab via accessible Enter key
    const tabs = wrapper.findAll('[role="tab"]');
    expect(tabs.length).toBe(3);
    await tabs[2].trigger('keydown', { key: 'Enter' });
    await flushPromises();
    expect(wrapper.text()).toContain('Bhavya Shah');
  });

  it('displays admin password prompt when auth is required and no session key is stored', async () => {
    vi.spyOn(ApiService, 'getAnalyticsStatus').mockResolvedValue({
      enabled: true,
      auth_required: true,
    });

    const wrapper = mount(AnalyticsDashboard);
    await flushPromises();

    expect(wrapper.text()).toContain('Admin Authentication');
    expect(wrapper.text()).toContain('This analytics dashboard is protected by an admin password.');
    expect(wrapper.find('input[type="password"]').exists()).toBe(true);
  });
});
