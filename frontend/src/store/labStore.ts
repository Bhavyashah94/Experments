import { reactive, ref, computed, watch } from 'vue'
import type { StudentProfile, ExperimentItem, GenerationDeliverables, SubjectRecord, ExportedSubjectPackage } from './types'
import { isStudentValid, validateStudent } from '../utils/validation'
import { calculateSha256 } from '../utils/crypto'
import { generateWeeklySequence } from '../utils/dates'
import { checkFileExists, uploadPdf } from '../api/upload'
import { generateJournal, generateSingleExperiment, getDownloadUrl } from '../api/generate'

const STORAGE_KEY = 'labstudio_v3_ace_state'

function createDefaultSubject(name: string = 'Untitled Subject'): SubjectRecord {
  return {
    id: `subj_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
    name,
    savedExperiments: [],
  }
}

function getDefaultStudent(): StudentProfile {
  return {
    name: '',
    roll_no: '',
    batch: '',
    class_name: '',
    sem: '',
    subject: 'Untitled Subject',
    text_color: '#0000bf',
    strikethrough_enabled: true,
    include_toc: true,
    global_perf_date: '',
    global_sub_date: '',
  }
}

// ── Persistent Domain State ───────────────────────────────────────────────────

export const subjects = ref<SubjectRecord[]>([createDefaultSubject('Untitled Subject')])
export const activeSubjectId = ref<string>(subjects.value[0].id)
export const student = reactive<StudentProfile>(getDefaultStudent())
export const experiments = ref<ExperimentItem[]>([])

// Hydrate from localStorage
function loadPersistedState(): void {
  if (typeof window === 'undefined') return
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return
    const parsed = JSON.parse(raw)

    if (parsed && typeof parsed === 'object') {
      // 1. Student Identity
      if (parsed.student && typeof parsed.student === 'object') {
        const s = parsed.student
        student.name = typeof s.name === 'string' ? s.name : ''
        student.roll_no = typeof s.roll_no === 'string' ? s.roll_no : ''
        student.batch = typeof s.batch === 'string' ? s.batch : ''
        student.class_name = typeof s.class_name === 'string' ? s.class_name : ''
        student.sem = typeof s.sem === 'string' ? s.sem : ''
        student.text_color = typeof s.text_color === 'string' ? s.text_color : '#0000bf'
        student.strikethrough_enabled = typeof s.strikethrough_enabled === 'boolean' ? s.strikethrough_enabled : true
        student.include_toc = typeof s.include_toc === 'boolean' ? s.include_toc : true
        student.global_perf_date = typeof s.global_perf_date === 'string' ? s.global_perf_date : ''
        student.global_sub_date = typeof s.global_sub_date === 'string' ? s.global_sub_date : ''
      }

      // 2. Subjects
      if (Array.isArray(parsed.subjects) && parsed.subjects.length > 0) {
        subjects.value = parsed.subjects
        const validId = parsed.activeSubjectId && subjects.value.some((s) => s.id === parsed.activeSubjectId)
          ? parsed.activeSubjectId
          : subjects.value[0].id
        activeSubjectId.value = validId
      } else if (parsed.profiles && Array.isArray(parsed.profiles)) {
        // Migration from old profiles schema
        subjects.value = parsed.profiles.map((p: any) => ({
          id: p.id || `subj_${Math.random().toString(36).slice(2, 6)}`,
          name: p.subject || p.name || 'Lab Subject',
          savedExperiments: p.savedExperiments || [],
        }))
        activeSubjectId.value = subjects.value[0].id
      }

      // 3. Hydrate active subject name and experiments
      const active = subjects.value.find((s) => s.id === activeSubjectId.value) || subjects.value[0]
      if (active) {
        student.subject = active.name
        if (Array.isArray(active.savedExperiments) && active.savedExperiments.length > 0) {
          experiments.value = active.savedExperiments.map((e, idx) => ({
            id: `exp_saved_${idx}_${Date.now()}`,
            num: e.num || idx + 1,
            label: e.label || String(idx + 1),
            title: e.title || '',
            is_assignment: Boolean(e.is_assignment),
            perf_date: e.perf_date || '',
            sub_date: e.sub_date || '',
            hash: '',
            pages: e.pages || 1,
            filename: '',
            isOpen: false,
            extraction_method: 'saved',
            failure_reason: 'none',
          }))
        }
      }
    }
  } catch (e) {
    console.warn('[labStore] Failed to load persisted state:', e)
  }
}

loadPersistedState()

export const activeSubject = computed<SubjectRecord>(() => {
  return subjects.value.find((s) => s.id === activeSubjectId.value) || subjects.value[0]
})

// ── Transient UI State ────────────────────────────────────────────────────────

export const selectedId = ref<string | null>(null)
export const downloadingIds = reactive(new Set<string>())
export const isUploading = ref(false)
export const uploadError = ref<string | null>(null)
export const isCompiling = ref(false)
export const compileError = ref<string | null>(null)
export const deliverables = ref<GenerationDeliverables | null>(null)
export const toastMessage = ref<string | null>(null)
export const isPreviewOpen = ref(false)
export const previewItem = ref<ExperimentItem | null>(null)
export const isGuideOpen = ref(false)
export const isShareOpen = ref(false)

export interface UndoEntry {
  item: ExperimentItem
  index: number
  timerId: ReturnType<typeof setTimeout>
}

export const undoStack = ref<UndoEntry[]>([])

// ── Computed Properties ───────────────────────────────────────────────────────

export const isStudentComplete = computed(() => isStudentValid(student))
export const studentErrors = computed(() => validateStudent(student))

export const totalPagesCount = computed(() => {
  const bodyPages = experiments.value.reduce((acc, curr) => acc + (curr.pages || 0), 0)
  const coverPages = experiments.value.length
  let tocPages = 0
  if (student.include_toc && experiments.value.length > 0) {
    tocPages = experiments.value.length <= 20 ? 1 : 1 + Math.ceil((experiments.value.length - 20) / 24)
  }
  return bodyPages + coverPages + tocPages
})

export const unextractedCount = computed(() => {
  return experiments.value.filter((e) => !e.title || !e.title.trim()).length
})

export const hasAnyDates = computed(() => {
  return experiments.value.some((e) => Boolean((e.perf_date && e.perf_date.trim()) || (e.sub_date && e.sub_date.trim())))
})

export const isReadyToCompile = computed(() => {
  return isStudentComplete.value && experiments.value.length > 0 && unextractedCount.value === 0
})

// ── Toast Helper ──────────────────────────────────────────────────────

let toastTimer: ReturnType<typeof setTimeout> | null = null
export function showToast(message: string, durationMs: number = 4000): void {
  toastMessage.value = message
  if (toastTimer) clearTimeout(toastTimer)
  toastTimer = setTimeout(() => {
    toastMessage.value = null
  }, durationMs)
}

// ── Debounced Persistence ─────────────────────────────────────────────────────

let saveTimeout: ReturnType<typeof setTimeout> | null = null

function persistState() {
  if (typeof window === 'undefined') return
  try {
    // Sync current active subject's name and experiments
    const current = activeSubject.value
    if (current) {
      current.name = student.subject
      current.savedExperiments = experiments.value.map((e) => ({
        num: e.num,
        label: e.label,
        title: e.title,
        is_assignment: e.is_assignment,
        perf_date: e.perf_date,
        sub_date: e.sub_date,
        pages: e.pages,
      }))
    }

    const payload = {
      version: 6,
      student: {
        name: student.name,
        roll_no: student.roll_no,
        batch: student.batch,
        class_name: student.class_name,
        sem: student.sem,
        text_color: student.text_color,
        strikethrough_enabled: student.strikethrough_enabled,
        include_toc: student.include_toc,
        global_perf_date: student.global_perf_date,
        global_sub_date: student.global_sub_date,
      },
      subjects: subjects.value,
      activeSubjectId: activeSubjectId.value,
    }
    localStorage.setItem(STORAGE_KEY, JSON.stringify(payload))
  } catch (e) {
    console.warn('[labStore] Failed to save state to localStorage:', e)
  }
}

watch(
  [student, subjects, activeSubjectId, experiments],
  () => {
    if (saveTimeout) clearTimeout(saveTimeout)
    saveTimeout = setTimeout(persistState, 300)
  },
  { deep: true }
)

// ── Subject Management Actions ────────────────────────────────────────────────

export function addSubject(name: string): SubjectRecord {
  const trimmed = name.trim() || `Subject ${subjects.value.length + 1}`
  // 1. Save current experiments into active subject
  if (activeSubject.value) {
    activeSubject.value.savedExperiments = experiments.value.map((e) => ({
      num: e.num,
      label: e.label,
      title: e.title,
      is_assignment: e.is_assignment,
      perf_date: e.perf_date,
      sub_date: e.sub_date,
      pages: e.pages,
    }))
  }

  // 2. Create new subject
  const newSubj = createDefaultSubject(trimmed)
  subjects.value.push(newSubj)
  activeSubjectId.value = newSubj.id

  // 3. Reset subject field & manifest for this new subject
  student.subject = trimmed
  experiments.value = []
  deliverables.value = null

  showToast(`Added subject "${trimmed}"`)
  return newSubj
}

export function deleteSubject(id: string): void {
  const idx = subjects.value.findIndex((s) => s.id === id)
  if (idx === -1) return
  const deletedName = subjects.value[idx].name || 'Subject'

  if (subjects.value.length === 1) {
    // If it's the only subject, reset to a clean Untitled Subject and clear manifest
    const freshSubj = createDefaultSubject('Untitled Subject')
    subjects.value = [freshSubj]
    activeSubjectId.value = freshSubj.id
    student.subject = freshSubj.name
    experiments.value = []
    deliverables.value = null
    showToast(`Reset to new subject`)
    return
  }

  subjects.value.splice(idx, 1)
  if (activeSubjectId.value === id) {
    switchSubject(subjects.value[0].id)
  }
  showToast(`Removed subject "${deletedName}"`)
}

export function switchSubject(id: string): void {
  if (id === activeSubjectId.value) return
  const target = subjects.value.find((s) => s.id === id)
  if (!target) return

  // 1. Save current experiments into currently active subject
  if (activeSubject.value) {
    activeSubject.value.savedExperiments = experiments.value.map((e) => ({
      num: e.num,
      label: e.label,
      title: e.title,
      is_assignment: e.is_assignment,
      perf_date: e.perf_date,
      sub_date: e.sub_date,
      pages: e.pages,
    }))
  }

  // 2. Set new active subject
  activeSubjectId.value = id
  student.subject = target.name

  // 3. Restore experiments from target subject
  if (Array.isArray(target.savedExperiments) && target.savedExperiments.length > 0) {
    experiments.value = target.savedExperiments.map((e, idx) => ({
      id: `exp_${Date.now()}_${idx}`,
      num: e.num || idx + 1,
      label: e.label || String(idx + 1),
      title: e.title || '',
      is_assignment: Boolean(e.is_assignment),
      perf_date: e.perf_date || '',
      sub_date: e.sub_date || '',
      hash: '',
      pages: e.pages || 1,
      filename: '',
      isOpen: false,
      extraction_method: 'saved',
      failure_reason: 'none',
    }))
  } else {
    experiments.value = []
  }

  deliverables.value = null
  showToast(`Switched to "${target.name}"`)
}

export function renameActiveSubject(newName: string): void {
  student.subject = newName
  if (activeSubject.value) {
    activeSubject.value.name = newName
  }
}

export function exportSubjectPackage(): string {
  const currentSubjectName = student.subject || activeSubject.value?.name || 'Lab Subject'

  const pkg: ExportedSubjectPackage = {
    labstudio_version: '3.1',
    type: 'subject_share',
    subject: currentSubjectName,
    experiments: experiments.value.map((d) => ({
      label: d.label,
      isAssignment: d.is_assignment,
      title: d.title,
      perfDate: d.perf_date,
      subDate: d.sub_date,
    })),
  }

  return JSON.stringify(pkg, null, 2)
}

export function importSubjectPackage(jsonStr: string): { success: boolean; subjectName?: string; count?: number; error?: string } {
  try {
    const parsed = JSON.parse(jsonStr)
    const rawSubject = (parsed.subject || parsed.profile?.subject || parsed.profile?.name || 'Imported Subject').trim()
    const newSubj = createDefaultSubject(rawSubject)

    const rawExps = Array.isArray(parsed.experiments) ? parsed.experiments : []
    newSubj.savedExperiments = rawExps.map((e: any, idx: number) => ({
      num: idx + 1,
      label: String(e.label || idx + 1),
      title: String(e.title || ''),
      is_assignment: Boolean(e.isAssignment !== undefined ? e.isAssignment : e.is_assignment),
      perf_date: String(e.perfDate || e.perf_date || student.global_perf_date || ''),
      sub_date: String(e.subDate || e.sub_date || student.global_sub_date || ''),
      pages: 1,
    }))

    subjects.value.push(newSubj)
    switchSubject(newSubj.id)

    return { success: true, subjectName: newSubj.name, count: newSubj.savedExperiments?.length || 0 }
  } catch (err: any) {
    return { success: false, error: err.message || 'Malformed JSON file.' }
  }
}

// ── Orchestration Actions ─────────────────────────────────────────────────────

export function openPreview(item: ExperimentItem): void {
  previewItem.value = item
  selectedId.value = item.id
  isPreviewOpen.value = true
}

export function closePreview(): void {
  isPreviewOpen.value = false
}

export function addDocument(): ExperimentItem {
  deliverables.value = null
  const currentCount = experiments.value.length + 1
  const defaultLabel = String(currentCount)

  const item: ExperimentItem = {
    id: `exp_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
    num: currentCount,
    label: defaultLabel,
    title: '',
    is_assignment: false,
    perf_date: student.global_perf_date || '',
    sub_date: student.global_sub_date || '',
    hash: '',
    pages: 1,
    filename: '',
    isOpen: true,
    extraction_method: 'unextracted',
    failure_reason: 'none',
    text_snippet: '',
  }

  experiments.value.push(item)
  selectedId.value = item.id
  return item
}

export function toggleAllCards(): void {
  const hasClosed = experiments.value.some((d) => !d.isOpen)
  experiments.value.forEach((d) => {
    d.isOpen = hasClosed
  })
}

export function applyGlobalDates(): void {
  deliverables.value = null
  const pDate = student.global_perf_date?.trim()
  const sDate = student.global_sub_date?.trim()
  if (!pDate && !sDate) {
    showToast('Enter a date first in the Date Schedule box')
    return
  }
  experiments.value.forEach((doc) => {
    if (pDate) doc.perf_date = pDate
    if (sDate) doc.sub_date = sDate
  })
  showToast('Applied global dates to all documents')
}

export function applyWeeklyDates(): void {
  deliverables.value = null
  const pBase = student.global_perf_date?.trim()
  if (!pBase) {
    showToast('Enter a Start Performance Date first')
    return
  }

  const seq = generateWeeklySequence(pBase, experiments.value.length)
  experiments.value.forEach((exp, idx) => {
    if (seq[idx]) {
      exp.perf_date = seq[idx].perf_date
      exp.sub_date = seq[idx].sub_date
    }
  })
  showToast(`Auto-filled sequential weekly dates (+7d)`)
}

export function copyDatesFromPrevious(index: number): void {
  if (index <= 0 || index >= experiments.value.length) return
  const prev = experiments.value[index - 1]
  const curr = experiments.value[index]
  curr.perf_date = prev.perf_date
  curr.sub_date = prev.sub_date
  deliverables.value = null
  showToast(`Copied dates from Exp ${prev.label || prev.num}`)
}

export function clearAllDates(): void {
  experiments.value.forEach((exp) => {
    exp.perf_date = ''
    exp.sub_date = ''
  })
  student.global_perf_date = ''
  student.global_sub_date = ''
  deliverables.value = null
  showToast('Cleared all dates')
}

export function renumberExperiments(): void {
  experiments.value.forEach((exp, idx) => {
    exp.num = idx + 1
    exp.label = String(idx + 1)
  })
  showToast('Renumbered experiments 1..N')
}

export async function batchUpload(files: FileList | File[]): Promise<void> {
  const fileArray = Array.from(files).filter((f) => f.name.toLowerCase().endsWith('.pdf'))
  if (fileArray.length === 0) return

  isUploading.value = true
  uploadError.value = null
  deliverables.value = null

  try {
    for (const file of fileArray) {
      const hash = await calculateSha256(file)
      const currentCount = experiments.value.length + 1
      const defaultLabel = String(currentCount)

      let pages = 1
      let aim: string | null = null
      let expNum: string | null = defaultLabel
      let isAssignment = false
      let extractionMethod = 'unextracted'
      let failureReason = 'none'
      let textSnippet = ''

      try {
        const existRes = await checkFileExists(hash)
        if (existRes.exists) {
          pages = existRes.pages || 1
          aim = existRes.aim || null
          expNum = existRes.exp_num || defaultLabel
          isAssignment = Boolean(existRes.is_assignment)
          extractionMethod = existRes.extraction_method || 'cached'
          failureReason = existRes.failure_reason || 'none'
          textSnippet = existRes.text_snippet || ''
        } else {
          const uploadRes = await uploadPdf(file, hash, 'auto')
          pages = uploadRes.pages || 1
          aim = uploadRes.aim || null
          expNum = uploadRes.exp_num || defaultLabel
          isAssignment = Boolean(uploadRes.is_assignment)
          extractionMethod = uploadRes.extraction_method || 'unextracted'
          failureReason = uploadRes.failure_reason || 'none'
          textSnippet = uploadRes.text_snippet || ''
        }
      } catch (err: any) {
        console.warn(`[labStore] Upload error for ${file.name}:`, err)
        failureReason = err.message || 'Upload error'
      }

      // Match any card that has no PDF attached yet (hash=''), including cards
      // restored from localStorage which may already have a saved title.
      // Prefer cards with no title first (freshly added), then fall back to
      // saved-but-no-PDF cards so we re-attach the file and refresh the AIM.
      let targetDoc =
        experiments.value.find((d) => !d.hash && !d.title) ||
        experiments.value.find((d) => !d.hash)

      if (targetDoc) {
        targetDoc.hash = hash
        targetDoc.pages = pages
        targetDoc.filename = file.name
        targetDoc.title = aim || targetDoc.title || ''
        targetDoc.label = expNum || targetDoc.label
        targetDoc.is_assignment = isAssignment
        targetDoc.extraction_method = extractionMethod
        targetDoc.failure_reason = failureReason
        targetDoc.text_snippet = textSnippet
      } else {
        const item: ExperimentItem = {
          id: `exp_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
          num: currentCount,
          label: expNum || defaultLabel,
          title: aim || '',
          is_assignment: isAssignment,
          perf_date: student.global_perf_date || '',
          sub_date: student.global_sub_date || '',
          hash,
          pages,
          filename: file.name,
          isOpen: false,
          extraction_method: extractionMethod,
          failure_reason: failureReason,
          text_snippet: textSnippet,
        }
        experiments.value.push(item)
      }
    }
  } catch (err: any) {
    uploadError.value = err.message || 'Failed to process files.'
  } finally {
    isUploading.value = false
  }
}

export async function replaceExperimentPdf(id: string, file: File): Promise<void> {
  const index = experiments.value.findIndex((e) => e.id === id)
  if (index === -1) return

  deliverables.value = null
  try {
    const hash = await calculateSha256(file)
    const existRes = await checkFileExists(hash)
    let pages = 1
    let aim: string | null = null
    let expNum: string | null = null
    let isAssignment = experiments.value[index].is_assignment
    let extractionMethod = 'unextracted'
    let failureReason = 'none'
    let textSnippet = ''

    if (existRes.exists) {
      pages = existRes.pages || 1
      aim = existRes.aim || null
      expNum = existRes.exp_num || null
      isAssignment = existRes.is_assignment !== undefined ? Boolean(existRes.is_assignment) : isAssignment
      extractionMethod = existRes.extraction_method || 'cached'
      failureReason = existRes.failure_reason || 'none'
      textSnippet = existRes.text_snippet || ''
    } else {
      const uploadRes = await uploadPdf(file, hash, 'auto')
      pages = uploadRes.pages || 1
      aim = uploadRes.aim || null
      expNum = uploadRes.exp_num || null
      isAssignment = uploadRes.is_assignment !== undefined ? Boolean(uploadRes.is_assignment) : isAssignment
      extractionMethod = uploadRes.extraction_method || 'unextracted'
      failureReason = uploadRes.failure_reason || 'none'
      textSnippet = uploadRes.text_snippet || ''
    }

    const current = experiments.value[index]
    experiments.value[index] = {
      ...current,
      hash,
      pages,
      filename: file.name,
      title: aim || current.title || '',
      label: expNum || current.label || String(current.num),
      is_assignment: isAssignment,
      extraction_method: extractionMethod,
      failure_reason: failureReason,
      text_snippet: textSnippet,
    }
    showToast(`Updated source PDF for ${aim || current.title || file.name}`)
  } catch (err: any) {
    showToast(`Failed to replace PDF: ${err.message}`)
  }
}

export function removeExperimentFromManifest(id: string): void {
  const index = experiments.value.findIndex((e) => e.id === id)
  if (index === -1) return

  const [removedItem] = experiments.value.splice(index, 1)
  deliverables.value = null

  if (selectedId.value === id) {
    selectedId.value = experiments.value[index]?.id || experiments.value[index - 1]?.id || null
  }

  const timerId = setTimeout(() => {
    const entryIdx = undoStack.value.findIndex((u) => u.item.id === id)
    if (entryIdx !== -1) undoStack.value.splice(entryIdx, 1)
  }, 5000)

  undoStack.value.push({ item: removedItem, index, timerId })
  showToast(`Removed "${removedItem.title || removedItem.filename || 'Experiment'}"`, 5000)
}

export function undoRemove(): void {
  const entry = undoStack.value.pop()
  if (!entry) return
  clearTimeout(entry.timerId)
  experiments.value.splice(entry.index, 0, entry.item)
  selectedId.value = entry.item.id
  deliverables.value = null
  showToast(`Restored "${entry.item.title || entry.item.filename}"`)
}

export async function downloadSingleExperiment(item: ExperimentItem): Promise<void> {
  downloadingIds.add(item.id)
  try {
    const res = await generateSingleExperiment(student, item)
    if (res.success && res.files && res.files.length > 0) {
      const fileRel = res.files[0].merged_pdf
      const url = getDownloadUrl(fileRel)
      const link = document.createElement('a')
      link.href = url
      link.download = `Exp_${item.label || item.num}_with_Header.pdf`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      showToast(`Downloaded Exp ${item.label}`)
    } else {
      showToast(res.error || 'Failed to generate single document')
    }
  } catch (err: any) {
    showToast(`Download failed: ${err.message}`)
  } finally {
    downloadingIds.delete(item.id)
  }
}

export async function compileJournal(): Promise<void> {
  if (!isReadyToCompile.value) return

  isCompiling.value = true
  compileError.value = null

  try {
    const res = await generateJournal(student, experiments.value, student.include_toc)
    if (res.success && res.combined_pdf) {
      deliverables.value = {
        job_id: res.job_id,
        combined_pdf: res.combined_pdf,
        zip_package: res.zip_package,
        files: res.files || [],
      }
      showToast('Lab journal compiled successfully!')
    } else {
      const msg = res.error || 'Compilation failed.'
      compileError.value = msg
      showToast(msg)
    }
  } catch (err: any) {
    const msg = err.message || 'Request failed.'
    compileError.value = msg
    showToast(msg)
  } finally {
    isCompiling.value = false
  }
}

export function downloadCombinedPdf(): boolean {
  if (!deliverables.value?.combined_pdf) return false
  const url = getDownloadUrl(deliverables.value.combined_pdf)
  const link = document.createElement('a')
  link.href = url
  link.download = deliverables.value.combined_pdf.split('/').pop() || 'Lab_Journal_Combined.pdf'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  return true
}

export function downloadZipPackage(): boolean {
  if (!deliverables.value?.zip_package) return false
  const url = getDownloadUrl(deliverables.value.zip_package)
  const link = document.createElement('a')
  link.href = url
  link.download = deliverables.value.zip_package.split('/').pop() || 'Lab_Journal_Package.zip'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  return true
}

export function resetWorkspace(): void {
  experiments.value = []
  selectedId.value = null
  deliverables.value = null
  undoStack.value = []
  showToast('Workspace cleared')
}
