import type {
  ApiHealthResponse,
  ApiFileExistsResponse,
  ApiUploadResponse,
  ApiExtractAimResponse,
  ApiGenerateRequest,
  ApiGenerateResponse,
} from '@/types/api';

const API_BASE = import.meta.env.VITE_API_BASE_URL
  ? import.meta.env.VITE_API_BASE_URL.replace(/\/$/, '')
  : '';

export class ApiService {
  static getBaseUrl(): string {
    return API_BASE;
  }

  static async checkHealth(): Promise<ApiHealthResponse> {
    const res = await fetch(`${API_BASE}/api/health`, { method: 'GET' });
    if (!res.ok) throw new Error(`Health check failed: ${res.status}`);
    return res.json();
  }

  static async checkFileExists(hash: string): Promise<ApiFileExistsResponse> {
    const res = await fetch(`${API_BASE}/api/file/${hash}/exists`, { method: 'GET' });
    if (!res.ok) return { exists: false };
    return res.json();
  }

  static async uploadPdf(
    file: File,
    hash: string,
    mode: string = 'auto'
  ): Promise<ApiUploadResponse> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('hash', hash);
    formData.append('mode', mode);

    const res = await fetch(`${API_BASE}/api/upload`, {
      method: 'POST',
      body: formData,
    });
    return res.json();
  }

  static async extractAim(
    hash: string,
    mode: string = 'auto'
  ): Promise<ApiExtractAimResponse> {
    const res = await fetch(`${API_BASE}/api/extract-aim`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ hash, mode }),
    });
    return res.json();
  }

  static async generateDocuments(payload: ApiGenerateRequest): Promise<ApiGenerateResponse> {
    const res = await fetch(`${API_BASE}/api/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return res.json();
  }

  static getDownloadUrl(relPath: string): string {
    const cleanPath = relPath.replace(/^\//, '');
    return `${API_BASE}/api/download/${cleanPath}`;
  }

  static async getAnalyticsStatus(): Promise<{ enabled: boolean; auth_required: boolean }> {
    const res = await fetch(`${API_BASE}/api/analytics/status`, { method: 'GET' });
    if (!res.ok) return { enabled: false, auth_required: false };
    return res.json();
  }

  static async verifyAnalyticsAuth(password: string): Promise<{ valid: boolean; auth_required: boolean }> {
    const res = await fetch(`${API_BASE}/api/analytics/auth`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ password }),
    });
    return res.json();
  }

  static async getAnalyticsSummary(authKey?: string): Promise<{ success: boolean; data?: any; error?: string }> {
    const headers: Record<string, string> = {};
    if (authKey) headers['X-Analytics-Key'] = authKey;

    const res = await fetch(`${API_BASE}/api/analytics/summary`, {
      method: 'GET',
      headers,
    });
    if (res.status === 401) {
      return { success: false, error: 'Unauthorized' };
    }
    return res.json();
  }

  static async getAnalyticsEvents(
    params: { q?: string; subject?: string; limit?: number; offset?: number },
    authKey?: string
  ): Promise<{ success: boolean; data?: any; error?: string }> {
    const query = new URLSearchParams();
    if (params.q) query.set('q', params.q);
    if (params.subject) query.set('subject', params.subject);
    if (params.limit) query.set('limit', String(params.limit));
    if (params.offset) query.set('offset', String(params.offset));

    const headers: Record<string, string> = {};
    if (authKey) headers['X-Analytics-Key'] = authKey;

    const res = await fetch(`${API_BASE}/api/analytics/events?${query.toString()}`, {
      method: 'GET',
      headers,
    });
    if (res.status === 401) {
      return { success: false, error: 'Unauthorized' };
    }
    return res.json();
  }

  static async downloadAnalyticsExport(format: 'csv' | 'json', authKey?: string): Promise<void> {
    const headers: Record<string, string> = {};
    if (authKey) headers['X-Analytics-Key'] = authKey;

    const res = await fetch(`${API_BASE}/api/analytics/export?format=${format}`, {
      method: 'GET',
      headers,
    });

    if (!res.ok) {
      throw new Error(`Export failed: ${res.status}`);
    }

    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    const dateStr = new Date().toISOString().split('T')[0];
    a.download = `labstudio_analytics_${dateStr}.${format}`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
  }
}
