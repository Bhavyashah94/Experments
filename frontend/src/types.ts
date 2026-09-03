export interface StudentInfo {
  name: string;
  rollNo: string;
  batch: string;
  className: string;
  sem: string;
  subject: string;
  textColor: string;
  strikethrough: boolean;
  includeToc: boolean;
  globalPerfDate: string;
  globalSubDate: string;
}

export interface DocumentItem {
  id: string;
  num: string;
  title: string;
  isAssignment: boolean;
  perfDate: string;
  subDate: string;
  hash: string | null;
  filename: string | null;
  pages: number;
  status: 'idle' | 'uploading' | 'ready' | 'error';
  errorMsg: string | null;
}

export interface SubjectProfile {
  id: string;
  name: string;
  subject: string;
  textColor: string;
  strikethrough: boolean;
  includeToc: boolean;
}
