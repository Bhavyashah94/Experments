import { request } from './client'
import type { StudentProfile, ExperimentItem } from '../store/types'

export interface GeneratedFile {
  label: string
  merged_pdf: string
}

export interface GenerateResponse {
  success: boolean
  job_id: string
  combined_pdf: string
  zip_package: string
  files: GeneratedFile[]
  error?: string
}

export async function generateJournal(
  student: StudentProfile,
  experiments: ExperimentItem[],
  includeToc: boolean = true
): Promise<GenerateResponse> {
  const payload = {
    student: {
      name: student.name,
      roll_no: student.roll_no,
      batch: student.batch,
      class_name: student.class_name,
      sem: student.sem,
      subject: student.subject,
      text_color: student.text_color,
      strikethrough_enabled: student.strikethrough_enabled,
    },
    experiments: experiments.map((exp, idx) => ({
      num: exp.num || idx + 1,
      label: exp.label || String(idx + 1),
      title: exp.title,
      is_assignment: exp.is_assignment,
      hash: exp.hash,
      pages: exp.pages,
      perf_date: exp.perf_date || '',
      sub_date: exp.sub_date || '',
    })),
    formatting: {
      text_color: student.text_color,
      strikethrough_enabled: student.strikethrough_enabled,
    },
    include_toc: includeToc,
  }

  return request<GenerateResponse>('/api/generate', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function generateSingleExperiment(
  student: StudentProfile,
  item: ExperimentItem
): Promise<GenerateResponse> {
  return generateJournal(student, [item], false)
}

export function getDownloadUrl(relativePath: string): string {
  const cleanPath = relativePath.startsWith('/') ? relativePath.slice(1) : relativePath
  return `/api/download/${cleanPath}`
}
