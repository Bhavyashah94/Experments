/**
 * Pure date utility functions for Indian academic calendars (DD/MM/YYYY).
 */

export function parseDate(str: string): Date | null {
  if (!str) return null
  const parts = str.trim().split('/')
  if (parts.length !== 3) return null
  const day = parseInt(parts[0], 10)
  const month = parseInt(parts[1], 10) - 1
  const year = parseInt(parts[2], 10)
  if (isNaN(day) || isNaN(month) || isNaN(year)) return null
  const d = new Date(year, month, day)
  if (isNaN(d.getTime())) return null
  return d
}

export function formatDate(d: Date): string {
  const day = String(d.getDate()).padStart(2, '0')
  const month = String(d.getMonth() + 1).padStart(2, '0')
  const year = d.getFullYear()
  return `${day}/${month}/${year}`
}

const MONTH_NAMES = [
  'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'
]

export function formatShortDate(d: Date): string {
  const day = String(d.getDate()).padStart(2, '0')
  const month = MONTH_NAMES[d.getMonth()]
  return `${day} ${month}`
}

export function formatDisplayDate(dateStr: string): string {
  const d = parseDate(dateStr)
  if (!d) return dateStr
  return formatShortDate(d)
}

export function formatDateRange(perfDate: string, subDate: string): string {
  if (!perfDate && !subDate) return ''
  const p = formatDisplayDate(perfDate)
  const s = formatDisplayDate(subDate)
  if (p && s) return `${p} → ${s}`
  return p || s
}

export function addDays(dateStr: string, days: number): string {
  const d = parseDate(dateStr)
  if (!d) return dateStr
  d.setDate(d.getDate() + days)
  return formatDate(d)
}

export function diffDays(d1Str: string, d2Str: string): number {
  const d1 = parseDate(d1Str)
  const d2 = parseDate(d2Str)
  if (!d1 || !d2) return 0
  const diffTime = d2.getTime() - d1.getTime()
  return Math.round(diffTime / (1000 * 60 * 60 * 24))
}

export function generateWeeklySequence(
  startDateStr: string,
  count: number
): Array<{ perf_date: string; sub_date: string }> {
  const results: Array<{ perf_date: string; sub_date: string }> = []
  let currentPerf = startDateStr

  for (let i = 0; i < count; i++) {
    const currentSub = addDays(currentPerf, 7)
    results.push({
      perf_date: currentPerf,
      sub_date: currentSub,
    })
    currentPerf = addDays(currentPerf, 7)
  }

  return results
}

/** Convert DD/MM/YYYY → YYYY-MM-DD for <input type="date"> value binding. */
export function toHtmlDate(ddmmyyyy: string): string {
  const d = parseDate(ddmmyyyy)
  if (!d) return ''
  const yyyy = d.getFullYear()
  const mm = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  return `${yyyy}-${mm}-${dd}`
}

/** Convert YYYY-MM-DD (from <input type="date">) → DD/MM/YYYY used by the app. */
export function fromHtmlDate(yyyymmdd: string): string {
  if (!yyyymmdd) return ''
  const [yyyy, mm, dd] = yyyymmdd.split('-')
  return `${dd}/${mm}/${yyyy}`
}
