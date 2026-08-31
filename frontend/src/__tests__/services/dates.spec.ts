import { describe, it, expect } from 'vitest';
import { DateScheduler } from '@/services/dates';

describe('DateScheduler Service', () => {
  it('correctly parses DD/MM/YYYY, DD-MM-YYYY, and DD.MM.YYYY dates', () => {
    const d1 = DateScheduler.parseDate('15/08/2026');
    expect(d1).not.toBeNull();
    expect(d1?.getDate()).toBe(15);
    expect(d1?.getMonth()).toBe(7); // 0-indexed August
    expect(d1?.getFullYear()).toBe(2026);

    const d2 = DateScheduler.parseDate('01-01-2026');
    expect(d2?.getDate()).toBe(1);
    expect(d2?.getMonth()).toBe(0);

    const d3 = DateScheduler.parseDate('31.12.2025');
    expect(d3?.getDate()).toBe(31);
    expect(d3?.getMonth()).toBe(11);
  });

  it('returns null for invalid date strings', () => {
    expect(DateScheduler.parseDate('')).toBeNull();
    expect(DateScheduler.parseDate('invalid-date')).toBeNull();
    expect(DateScheduler.parseDate('99/99/9999')).toBeNull();
  });

  it('formats dates consistently to DD/MM/YYYY', () => {
    const date = new Date(2026, 4, 5); // May 5, 2026
    expect(DateScheduler.formatDate(date)).toBe('05/05/2026');
  });

  it('generates accurate sequential weekly series (+7 days)', () => {
    const series = DateScheduler.generateWeeklySeries('01/02/2026', 4);
    expect(series).toEqual([
      '01/02/2026',
      '08/02/2026',
      '15/02/2026',
      '22/02/2026',
    ]);
  });

  it('handles month-end and leap-year rollovers in weekly series', () => {
    const leapSeries = DateScheduler.generateWeeklySeries('20/02/2024', 3); // 2024 is leap year (29 days in Feb)
    expect(leapSeries).toEqual([
      '20/02/2024',
      '27/02/2024',
      '05/03/2024',
    ]);

    const yearEndSeries = DateScheduler.generateWeeklySeries('25/12/2026', 2);
    expect(yearEndSeries).toEqual([
      '25/12/2026',
      '01/01/2027',
    ]);
  });
});
