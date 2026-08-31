export type UploadStatus = 'idle' | 'hashing' | 'uploading' | 'ready' | 'expired' | 'error';

export interface DocumentItem {
  id: string;
  label: string;
  isAssignment: boolean;
  title: string;
  perfDate: string;
  subDate: string;
  hash: string | null;
  filename: string | null;
  pages: number;
  isOpen: boolean;
  status: UploadStatus;
  errorMessage?: string;
}
