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
}
