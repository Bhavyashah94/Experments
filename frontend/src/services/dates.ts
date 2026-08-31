export class DateScheduler {
  static parseDate(str: string): Date | null {
    if (!str) return null;
    const parts = str.trim().split(/[/.-]/).map(Number);
    if (parts.length === 3) {
      const [d, m, y] = parts;
      if (d >= 1 && d <= 31 && m >= 1 && m <= 12 && y >= 1900) {
        return new Date(y, m - 1, d);
      }
    }
    return null;
  }

  static formatDate(date: Date): string {
    if (!date || isNaN(date.getTime())) return '';
    const d = String(date.getDate()).padStart(2, '0');
    const m = String(date.getMonth() + 1).padStart(2, '0');
    const y = date.getFullYear();
    return `${d}/${m}/${y}`;
  }

  static generateWeeklySeries(startDateStr: string, count: number): string[] {
    const baseDate = this.parseDate(startDateStr);
    if (!baseDate) return Array(count).fill('');

    return Array.from({ length: count }, (_, i) => {
      const nextDate = new Date(baseDate);
      nextDate.setDate(nextDate.getDate() + i * 7);
      return this.formatDate(nextDate);
    });
  }
}
