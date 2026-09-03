export interface UploadResponse {
  success: boolean;
  hash?: string;
  filename?: string;
  pages?: number;
  extracted?: {
    aim?: string;
    experiment_number?: string;
    is_assignment?: boolean;
    page_count?: number;
  };
  error?: string;
}

export interface PreviewResponse {
  success: boolean;
  image?: string;
  error?: string;
}

export interface GenerateResponse {
  success: boolean;
  combined_pdf?: string;
  zip_package?: string;
  files?: Array<{ label: string; merged_pdf: string }>;
  error?: string;
}

export const Api = {
  async checkHealth(): Promise<{ status: string; version?: string }> {
    const res = await fetch('/api/health');
    if (!res.ok) throw new Error(`Health check failed: ${res.statusText}`);
    return res.json();
  },

  async uploadPdf(file: File): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch('/api/upload', {
      method: 'POST',
      body: formData,
    });
    return res.json();
  },

  async previewHeader(payload: any): Promise<PreviewResponse> {
    const res = await fetch('/api/preview', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return res.json();
  },

  async generate(payload: any): Promise<GenerateResponse> {
    const res = await fetch('/api/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return res.json();
  },

  getDownloadUrl(filePath: string): string {
    const clean = filePath.replace(/^(output\/|uploads\/)/, '');
    return `/api/download/${encodeURIComponent(clean)}`;
  },
};
