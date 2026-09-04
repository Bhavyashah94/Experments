import { request } from './client'

export interface FileExistsResponse {
  exists: boolean
  pages?: number
  aim?: string | null
  exp_num?: string | null
  is_assignment?: boolean
  extraction_method?: string
  failure_reason?: string
  text_snippet?: string
  error?: string
}

export interface UploadResponse {
  success: boolean
  hash: string
  size: number
  pages: number
  aim: string | null
  exp_num: string | null
  is_assignment: boolean
  extraction_method: string
  failure_reason: string
  text_snippet?: string
  error?: string
}

export async function checkFileExists(hash: string): Promise<FileExistsResponse> {
  return request<FileExistsResponse>(`/api/file/${encodeURIComponent(hash)}/exists`, {
    method: 'GET',
  })
}

export async function uploadPdf(
  file: File,
  hash?: string,
  mode: string = 'auto'
): Promise<UploadResponse> {
  const formData = new FormData()
  formData.append('file', file)
  if (hash) formData.append('hash', hash)
  if (mode) formData.append('mode', mode)

  return request<UploadResponse>('/api/upload', {
    method: 'POST',
    body: formData,
  })
}
