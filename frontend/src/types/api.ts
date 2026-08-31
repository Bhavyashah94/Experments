export interface ApiHealthResponse {
  status: 'ok' | 'degraded';
  version: string;
  uptime_seconds: number;
}

export interface ApiFileExistsResponse {
  exists: boolean;
  pages?: number;
  aim?: string | null;
  exp_num?: string | null;
  is_assignment?: boolean | null;
  error?: string;
}

export interface ApiUploadResponse {
  success: boolean;
  hash?: string;
  size?: number;
  pages?: number;
  aim?: string | null;
  exp_num?: string | null;
  is_assignment?: boolean | null;
  error?: string;
}

export interface ApiExtractAimResponse {
  success: boolean;
  aim?: string | null;
  pages?: number;
  exp_num?: string | null;
  is_assignment?: boolean | null;
  error?: string;
}

export interface ApiGenerateRequest {
  student: {
    name: string;
    roll_no: string;
    batch: string;
    class_name: string;
    sem: string;
    subject: string;
    text_color: string;
    strikethrough_enabled: boolean;
    perf_date?: string;
    sub_date?: string;
  };
  experiments: Array<{
    label: string;
    is_assignment: boolean;
    title: string;
    perf_date: string;
    sub_date: string;
    hash: string | null;
  }>;
  include_toc?: boolean;
}

export interface ApiGenerateResponse {
  success: boolean;
  job_id?: string;
  combined_pdf?: string;
  zip_package?: string;
  files?: Array<{
    label: string;
    merged_pdf: string;
  }>;
  error?: string;
}
