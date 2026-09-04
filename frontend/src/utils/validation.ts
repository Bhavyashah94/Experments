import type { StudentProfile, StudentValidationErrors } from '../store/types'

/**
 * Pure validation utility for Student Profile.
 * Validates whether fields satisfy the backend generation requirements.
 */

export function validateStudentField(
  field: keyof StudentProfile,
  value: string | boolean
): string | undefined {
  if (typeof value === 'boolean') return undefined
  const trimmed = value.trim()
  
  switch (field) {
    case 'name':
      if (!trimmed) return 'Full name is required'
      return undefined
    case 'roll_no':
      if (!trimmed) return 'Roll number is required'
      return undefined
    case 'batch':
      if (!trimmed) return 'Batch is required (e.g. B1, B2)'
      return undefined
    case 'class_name':
      if (!trimmed) return 'Class is required (e.g. BE, TE)'
      return undefined
    case 'sem':
      if (!trimmed) return 'Semester is required (e.g. VII, VIII)'
      return undefined
    case 'subject':
      if (!trimmed) return 'Subject is required'
      return undefined
    default:
      return undefined
  }
}

export function validateStudent(student: StudentProfile): StudentValidationErrors {
  const errors: StudentValidationErrors = {}
  
  const nameErr = validateStudentField('name', student.name)
  if (nameErr) errors.name = nameErr
  
  const rollErr = validateStudentField('roll_no', student.roll_no)
  if (rollErr) errors.roll_no = rollErr
  
  const batchErr = validateStudentField('batch', student.batch)
  if (batchErr) errors.batch = batchErr
  
  const classErr = validateStudentField('class_name', student.class_name)
  if (classErr) errors.class_name = classErr
  
  const semErr = validateStudentField('sem', student.sem)
  if (semErr) errors.sem = semErr
  
  const subjErr = validateStudentField('subject', student.subject)
  if (subjErr) errors.subject = subjErr
  
  return errors
}

export function isStudentValid(student: StudentProfile): boolean {
  return (
    student.name.trim().length > 0 &&
    student.roll_no.trim().length > 0 &&
    student.batch.trim().length > 0 &&
    student.class_name.trim().length > 0 &&
    student.sem.trim().length > 0 &&
    student.subject.trim().length > 0
  )
}
