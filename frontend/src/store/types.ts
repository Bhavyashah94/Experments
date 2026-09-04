export interface SubjectRecord {
  id: string
  name: string
  savedExperiments?: Array<{
    num: number
    label: string
    title: string
    is_assignment: boolean
    perf_date: string
    sub_date: string
    pages?: number
  }>
}

export interface StudentProfile {
  name: string
  roll_no: string
  batch: string
  class_name: string
  sem: string
  subject: string
  text_color: string
  strikethrough_enabled: boolean
  include_toc: boolean
  global_perf_date?: string
  global_sub_date?: string
}

export interface StudentValidationErrors {
  name?: string
  roll_no?: string
  batch?: string
  class_name?: string
  sem?: string
  subject?: string
}

export interface ExperimentItem {
  id: string
  num: number
  label: string
  title: string
  is_assignment: boolean
  perf_date: string
  sub_date: string
  hash: string
  pages: number
  filename: string
  isOpen?: boolean
  extraction_method?: string
  failure_reason?: string
  text_snippet?: string
  is_manually_edited?: boolean
}

export interface GenerationDeliverables {
  job_id: string
  combined_pdf: string
  zip_package: string
  files: Array<{
    label: string
    merged_pdf: string
  }>
}

export interface ExportedSubjectPackage {
  labstudio_version: string
  type: string
  subject: string
  experiments: Array<{
    label: string
    isAssignment: boolean
    title: string
    perfDate: string
    subDate: string
  }>
}
