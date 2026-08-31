export interface GlobalStudentInfo {
  name: string;
  rollNo: string;
  batch: string;
  className: string;
  sem: string;
}

export interface SubjectProfile {
  id: string;
  name: string;
  subject: string;
  textColor: string;
  strikethroughEnabled: boolean;
  autoAim: boolean;
  aimMode: 'auto' | 'first_period' | 'header_title';
  includeToc: boolean;
  globalPerfDate: string;
  globalSubDate: string;
}
