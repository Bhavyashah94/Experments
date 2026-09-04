import { request } from './client'

export interface HealthResponse {
  status: string
  version: string
  uptime_seconds: number
  storage: {
    used_bytes: number
    max_bytes: number
    percent_used: number
  }
}

export interface AnalyticsStatusResponse {
  enabled: boolean
  auth_required: boolean
}

export interface DailyTrendItem {
  date: string
  count: number
  successes: number
}

export interface TopSubjectItem {
  subject: string
  count: number
  students: number
}

export interface TopExperimentItem {
  name: string
  count: number
}

export interface AnalyticsSummary {
  total_generations: number
  successful_generations: number
  failed_generations: number
  success_rate: number
  avg_duration_ms: number
  total_experiments_generated: number
  unique_students: number
  daily_trends: DailyTrendItem[]
  top_subjects: TopSubjectItem[]
  top_experiments: TopExperimentItem[]
}

export interface StudentSummaryItem {
  roll_no: string
  student_name: string
  class_name: string
  batch: string
  sem: string
  total_compilations: number
  successful_compilations: number
  failed_compilations: number
  total_experiments: number
  subjects: string[]
  subjects_count: number
  first_active: string
  last_active: string
}

export interface StudentDossierTimelineItem {
  id: number
  timestamp: string
  subject: string
  experiment_count: number
  experiments: Array<{
    label?: string
    title?: string
    is_assignment?: boolean
    pages?: number
    perf_date?: string
    sub_date?: string
    hash?: string
  }>
  generation_type: string
  success: boolean
  error_message: string | null
  duration_ms: number
}

export interface StudentDossier {
  roll_no: string
  student_name: string
  class_name: string
  batch: string
  sem: string
  total_compilations: number
  successful_compilations: number
  failed_compilations: number
  total_experiments: number
  avg_duration_ms: number
  subjects: string[]
  subjects_count: number
  first_active: string
  last_active: string
  timeline: StudentDossierTimelineItem[]
}

export interface GenerationEventItem {
  id: number
  timestamp: string
  student_name: string
  roll_no: string
  batch: string
  class_name: string
  sem: string
  subject: string
  experiment_count: number
  experiments: Array<{
    label?: string
    title?: string
    is_assignment?: boolean
    pages?: number
    perf_date?: string
    sub_date?: string
    hash?: string
  }>
  generation_type: string
  success: boolean
  error_message: string | null
  duration_ms: number
}

export interface FailedAimDocument {
  sha256: string
  filename: string
  file_size: number
  pages: number
  extracted_aim: string | null
  extracted_exp_num: string | null
  extraction_method: string
  failure_reason: string
  student_submitted_title: string | null
  student_submitted_num: string | null
  discrepancy: number
  text_snippet: string
  uploaded_at: string
  is_sample_preserved: number
}

export interface ExtractionDiagnosticsSummary {
  total_documents: number
  success_rate_percent: number
  methods: Record<string, number>
  failures: Record<string, number>
  discrepancies_count: number
}

function getAuthHeaders(token?: string): Record<string, string> {
  const t = token || (typeof sessionStorage !== 'undefined' ? sessionStorage.getItem('labstudio_analytics_admin_key') || '' : '')
  if (t) {
    return { 'X-Analytics-Key': t }
  }
  return {}
}

export async function checkHealth(): Promise<HealthResponse> {
  return request<HealthResponse>('/api/health', {
    method: 'GET',
  })
}

export async function getAnalyticsStatus(): Promise<AnalyticsStatusResponse> {
  return request<AnalyticsStatusResponse>('/api/analytics/status', {
    method: 'GET',
  })
}

export async function authenticateAdmin(password: string): Promise<{ valid: boolean; auth_required: boolean }> {
  return request<{ valid: boolean; auth_required: boolean }>('/api/analytics/auth', {
    method: 'POST',
    body: JSON.stringify({ password }),
  })
}

export async function getAnalyticsSummary(token?: string): Promise<AnalyticsSummary> {
  const res = await request<{ success: boolean; data: AnalyticsSummary }>('/api/analytics/summary', {
    method: 'GET',
    headers: getAuthHeaders(token),
  })
  return res.data
}

export interface GetStudentsParams {
  q?: string
  class_name?: string
  batch?: string
  sort_by?: string
  limit?: number
  offset?: number
}

export interface GetStudentsResponse {
  students: StudentSummaryItem[]
  total: number
  limit: number
  offset: number
  classes: string[]
  batches: string[]
}

export async function getStudents(params: GetStudentsParams = {}, token?: string): Promise<GetStudentsResponse> {
  const query = new URLSearchParams()
  if (params.q) query.set('q', params.q)
  if (params.class_name) query.set('class_name', params.class_name)
  if (params.batch) query.set('batch', params.batch)
  if (params.sort_by) query.set('sort_by', params.sort_by)
  if (params.limit) query.set('limit', String(params.limit))
  if (params.offset) query.set('offset', String(params.offset))

  const res = await request<{ success: boolean; data: GetStudentsResponse }>(`/api/analytics/students?${query.toString()}`, {
    method: 'GET',
    headers: getAuthHeaders(token),
  })
  return res.data
}

export async function getStudentDetail(rollNo?: string, studentName?: string, token?: string): Promise<StudentDossier> {
  const query = new URLSearchParams()
  if (rollNo && rollNo !== '—') query.set('roll_no', rollNo)
  if (studentName && studentName !== 'Anonymous') query.set('student_name', studentName)

  const res = await request<{ success: boolean; data: StudentDossier }>(`/api/analytics/student-detail?${query.toString()}`, {
    method: 'GET',
    headers: getAuthHeaders(token),
  })
  return res.data
}

export interface GetEventsParams {
  q?: string
  subject?: string
  limit?: number
  offset?: number
}

export interface GetEventsResponse {
  events: GenerationEventItem[]
  total: number
  limit: number
  offset: number
}

export async function getGenerationEvents(params: GetEventsParams = {}, token?: string): Promise<GetEventsResponse> {
  const query = new URLSearchParams()
  if (params.q) query.set('q', params.q)
  if (params.subject) query.set('subject', params.subject)
  if (params.limit) query.set('limit', String(params.limit))
  if (params.offset) query.set('offset', String(params.offset))

  const res = await request<{ success: boolean; data: GetEventsResponse }>(`/api/analytics/events?${query.toString()}`, {
    method: 'GET',
    headers: getAuthHeaders(token),
  })
  return res.data
}

export interface GetFailedAimsParams {
  q?: string
  reason?: string
  method?: string
  discrepancy_only?: boolean
  limit?: number
  offset?: number
}

export interface GetFailedAimsResponse {
  documents: FailedAimDocument[]
  total: number
  limit: number
  offset: number
  summary: ExtractionDiagnosticsSummary
}

export async function getFailedAims(params: GetFailedAimsParams = {}, token?: string): Promise<GetFailedAimsResponse> {
  const query = new URLSearchParams()
  if (params.q) query.set('q', params.q)
  if (params.reason) query.set('reason', params.reason)
  if (params.method) query.set('method', params.method)
  if (params.discrepancy_only) query.set('discrepancy_only', 'true')
  if (params.limit) query.set('limit', String(params.limit))
  if (params.offset) query.set('offset', String(params.offset))

  const res = await request<{ success: boolean; data: GetFailedAimsResponse }>(`/api/analytics/failed-aims?${query.toString()}`, {
    method: 'GET',
    headers: getAuthHeaders(token),
  })
  return res.data
}

export function getExportDownloadUrl(type: 'students' | 'events', format: 'csv' | 'json' = 'csv'): string {
  const query = new URLSearchParams({ type, format })
  return `/api/analytics/export?${query.toString()}`
}

export function getSampleDownloadUrl(hash: string): string {
  return `/api/analytics/sample/${hash}`
}
