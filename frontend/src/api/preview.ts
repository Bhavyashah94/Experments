import { request } from './client'
import type { StudentProfile, ExperimentItem } from '../store/types'

export interface PreviewResponse {
  success: boolean
  image_data?: string
  image?: string
  error?: string
}

export async function fetchCoverPreview(
  student: StudentProfile,
  item: ExperimentItem
): Promise<PreviewResponse> {
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
    item: {
      num: item.num,
      label: item.label,
      title: item.title,
      is_assignment: item.is_assignment,
      perf_date: item.perf_date,
      sub_date: item.sub_date,
    },
  }

  return request<PreviewResponse>('/api/preview', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}
