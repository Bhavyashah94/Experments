/**
 * Base HTTP client for LabStudio API.
 * Normalized error handling matching docs/frontend-api-contract.md.
 */

export class ApiError extends Error {
  constructor(public message: string, public status?: number) {
    super(message)
    this.name = 'ApiError'
  }
}

export async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = endpoint.startsWith('/') ? endpoint : `/${endpoint}`
  const headers = new Headers(options.headers || {})

  if (!(options.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }

  try {
    const response = await fetch(url, {
      ...options,
      headers,
    })

    if (!response.ok) {
      let errorMessage = `HTTP ${response.status}: ${response.statusText}`
      try {
        const errorJson = await response.json()
        if (errorJson && typeof errorJson.error === 'string') {
          errorMessage = errorJson.error
        }
      } catch {
        // Fall back to status text if body is not JSON
      }
      throw new ApiError(errorMessage, response.status)
    }

    return (await response.json()) as T
  } catch (err: any) {
    if (err instanceof ApiError) throw err
    throw new ApiError(err.message || 'Network request failed')
  }
}
