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

export async function checkHealth(): Promise<HealthResponse> {
  return request<HealthResponse>('/api/health', {
    method: 'GET',
  })
}
