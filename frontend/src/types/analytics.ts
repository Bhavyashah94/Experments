export interface AnalyticsStatusResponse {
  enabled: boolean;
  auth_required: boolean;
}

export interface DailyTrendItem {
  date: string;
  count: number;
  successes: number;
}

export interface TopSubjectItem {
  subject: string;
  count: number;
  students: number;
}

export interface TopExperimentItem {
  name: string;
  count: number;
}

export interface AnalyticsSummary {
  total_generations: number;
  successful_generations: number;
  failed_generations: number;
  success_rate: number;
  avg_duration_ms: number;
  total_experiments_generated: number;
  unique_students: number;
  daily_trends: DailyTrendItem[];
  top_subjects: TopSubjectItem[];
  top_experiments: TopExperimentItem[];
}

export interface GenerationEventItem {
  id: number;
  timestamp: string;
  student_name: string;
  roll_no: string;
  batch: string;
  class_name: string;
  sem: string;
  subject: string;
  experiment_count: number;
  experiments: Array<{
    label: string;
    is_assignment: boolean;
    title: string;
    hash: string | null;
    pages: number;
    perf_date: string;
    sub_date: string;
  }>;
  generation_type: string;
  success: boolean;
  error_message: string | null;
  duration_ms: number;
}

export interface AnalyticsEventsResponse {
  events: GenerationEventItem[];
  total: number;
  limit: number;
  offset: number;
}

export interface ExtractionDiagnosticsSummary {
  total_documents: number;
  success_rate_percent: number;
  methods: Record<string, number>;
  failures: Record<string, number>;
  discrepancies_count: number;
}

export interface DiagnosticSampleItem {
  sha256: string;
  filename: string;
  file_size: number;
  pages: number;
  extracted_aim: string | null;
  extracted_exp_num: string | null;
  extraction_method: string;
  failure_reason: string;
  student_submitted_title: string | null;
  student_submitted_num: string | null;
  discrepancy: number;
  text_snippet: string;
  uploaded_at: string;
  is_sample_preserved: number;
}

export interface DiagnosticsResponse {
  summary: ExtractionDiagnosticsSummary;
  samples: DiagnosticSampleItem[];
  total: number;
  limit: number;
  offset: number;
}

export interface ServerStorageStatus {
  max_bytes: number;
  used_bytes: number;
  percent_used: number;
}

export interface ServerHealthResponse {
  status: string;
  version?: string;
  uptime_seconds?: number;
  storage?: ServerStorageStatus;
}
