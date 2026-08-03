(() => {
'use strict';

// ── Constants ─────────────────────────────────────────────────────────────────
const PROFILES_KEY = 'lab_header_profiles_v1';
const CURRENT_PROFILE_KEY = 'lab_header_current_profile';

// ── State ─────────────────────────────────────────────────────────────────────
// rows: Map<rowId, { rowId, label, is_assignment, title, perf_date, sub_date, hash, filename, size, pages }>
const rows = new Map();
let currentProfile = 'Default';

// ── DOM refs ──────────────────────────────────────────────────────────────────
const $ = id => document.getElementById(id);
const docsList         = $('documents-list');
const emptyHint        = $('empty-hint');
const docCountBadge    = $('doc-count-badge');
const rowTemplate      = $('row-template');

const profileSelect    = $('profile-select');
const btnSaveProfile   = $('btn-save-profile');
const btnDeleteProfile = $('btn-delete-profile');

const globalPerfDate   = $('global-perf-date');
const globalSubDate    = $('global-sub-date');
const btnApplyDates    = $('btn-apply-global-dates');
const btnWeeklyDates   = $('btn-weekly-increment-dates');

const bulkPdfInput     = $('bulk-pdf-input');
const btnToggleCards   = $('btn-toggle-all-cards');

const btnZipHeader     = $('btn-download-zip');
const btnZipBottom     = $('btn-download-zip-bottom');

const previewModal     = $('preview-modal');
const previewLabel     = $('preview-label');
const previewImg       = $('preview-img');
const previewSpinner   = $('preview-spinner');

const toast            = $('toast');
const toastText        = $('toast-text');

// ── Helpers ───────────────────────────────────────────────────────────────────
function uid() { return crypto.randomUUID(); }

async function sha256(buffer) {
    const hashBuf = await crypto.subtle.digest('SHA-256', buffer);
    return Array.from(new Uint8Array(hashBuf)).map(b => b.toString(16).padStart(2, '0')).join('');
}

let toastTimer;
function showToast(msg, duration = 3000) {
    toastText.textContent = msg;
    toast.classList.remove('hidden');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toast.classList.add('hidden'), duration);
}

function collectStudent() {
    return {
        name:                  $('student-name').value.trim(),
        roll_no:               $('roll-no').value.trim(),
        batch:                 $('batch').value.trim(),
        class_name:            $('class-name').value.trim(),
        sem:                   $('sem').value.trim(),
        subject:               $('subject').value.trim(),
        text_color:            $('text-color').value,
        strikethrough_enabled: $('strikethrough-toggle').checked,
    };
}

function isAutoAim() { return $('auto-aim-toggle').checked; }

function updateDocSummary() {
    const n = rows.size;
    docCountBadge.textContent = `${n} card${n !== 1 ? 's' : ''}`;
    emptyHint.classList.toggle('hidden', n > 0);
    btnToggleCards.classList.toggle('hidden', n === 0);
}

// ── Subject Profile Persistence ──────────────────────────────────────────────
function getSavedProfiles() {
    try {
        return JSON.parse(localStorage.getItem(PROFILES_KEY)) || {};
    } catch { return {}; }
}

function saveProfilesToLS(profiles) {
    try {
        localStorage.setItem(PROFILES_KEY, JSON.stringify(profiles));
    } catch {}
}

function refreshProfileDropdown() {
    const profiles = getSavedProfiles();
    const names = Object.keys(profiles);
    if (!names.includes('Default')) names.unshift('Default');

    profileSelect.innerHTML = '';
    names.forEach(name => {
        const opt = document.createElement('option');
        opt.value = name;
        opt.textContent = name;
        if (name === currentProfile) opt.selected = true;
        profileSelect.appendChild(opt);
    });
}

function saveCurrentProfileState() {
    const profiles = getSavedProfiles();
    profiles[currentProfile] = {
        student: collectStudent(),
        autoAim: isAutoAim(),
        globalPerf: globalPerfDate.value.trim(),
        globalSub:  globalSubDate.value.trim(),
        rows: [...rows.values()],
    };
    saveProfilesToLS(profiles);
    localStorage.setItem(CURRENT_PROFILE_KEY, currentProfile);
}

function loadProfileState(name) {
    currentProfile = name;
    localStorage.setItem(CURRENT_PROFILE_KEY, name);
    refreshProfileDropdown();

    const profiles = getSavedProfiles();
    const data = profiles[name];

    rows.clear();
    docsList.innerHTML = '';

    if (data) {
        if (data.student) {
            const s = data.student;
            $('student-name').value          = s.name || '';
            $('roll-no').value               = s.roll_no || '';
            $('batch').value                 = s.batch || '';
            $('class-name').value            = s.class_name || '';
            $('sem').value                   = s.sem || '';
            $('subject').value               = s.subject || '';
            $('text-color').value            = s.text_color || 'blue';
            $('strikethrough-toggle').checked = s.strikethrough_enabled !== false;
        }
        if (data.autoAim !== undefined) $('auto-aim-toggle').checked = data.autoAim;
        if (data.globalPerf !== undefined) globalPerfDate.value = data.globalPerf;
        if (data.globalSub !== undefined)  globalSubDate.value = data.globalSub;

        if (data.rows?.length) {
            data.rows.forEach(r => {
                r.rowId = r.rowId || uid();
                addRow(r);
            });
            verifyUploadHashes();
            return;
        }
    }
}

// Profile Actions
profileSelect.addEventListener('change', () => {
    saveCurrentProfileState();
    loadProfileState(profileSelect.value);
    showToast(`Loaded profile: ${currentProfile}`);
});

btnSaveProfile.addEventListener('click', () => {
    const newName = prompt('Enter profile name (e.g. IoT Lab, Cloud Lab):', currentProfile);
    if (!newName || !newName.trim()) return;
    currentProfile = newName.trim();
    saveCurrentProfileState();
    refreshProfileDropdown();
    showToast(`Saved profile "${currentProfile}"`);
});

btnDeleteProfile.addEventListener('click', () => {
    if (currentProfile === 'Default') {
        showToast('Cannot delete Default profile');
        return;
    }
    if (!confirm(`Delete profile "${currentProfile}"?`)) return;

    const profiles = getSavedProfiles();
    delete profiles[currentProfile];
    saveProfilesToLS(profiles);

    loadProfileState('Default');
    showToast('Profile deleted');
});

// Auto save state on inputs
['student-name','roll-no','batch','class-name','sem','subject','text-color','strikethrough-toggle','auto-aim-toggle','global-perf-date','global-sub-date']
    .forEach(id => {
        const el = $(id);
        if (el) el.addEventListener('input', saveCurrentProfileState);
    });

// ── Date Auto-Filler Functions ────────────────────────────────────────────────
function parseDate(str) {
    if (!str) return null;
    const parts = str.split('/');
    if (parts.length === 3) {
        const d = parseInt(parts[0]), m = parseInt(parts[1]) - 1, y = parseInt(parts[2]);
        if (!isNaN(d) && !isNaN(m) && !isNaN(y)) return new Date(y, m, d);
    }
    return null;
}

function formatDate(dateObj) {
    if (!dateObj || isNaN(dateObj.getTime())) return '';
    const d = String(dateObj.getDate()).padStart(2, '0');
    const m = String(dateObj.getMonth() + 1).padStart(2, '0');
    const y = dateObj.getFullYear();
    return `${d}/${m}/${y}`;
}

btnApplyDates.addEventListener('click', () => {
    const perf = globalPerfDate.value.trim();
    const sub  = globalSubDate.value.trim();
    if (!perf && !sub) {
        showToast('Enter a Global Perf or Sub date first');
        return;
    }

    for (const [rowId, row] of rows) {
        if (perf) row.perf_date = perf;
        if (sub)  row.sub_date  = sub;
        const el = docsList.querySelector(`[data-rowid="${rowId}"]`);
        if (el) {
            if (perf) el.querySelector('.perf-input').value = perf;
            if (sub)  el.querySelector('.sub-input').value  = sub;
        }
    }
    saveCurrentProfileState();
    showToast('Applied global dates to all document cards');
});

btnWeeklyDates.addEventListener('click', () => {
    const startPerf = parseDate(globalPerfDate.value.trim());
    const startSub  = parseDate(globalSubDate.value.trim());

    if (!startPerf && !startSub) {
        showToast('Enter valid DD/MM/YYYY in Global Perf or Sub date first');
        return;
    }

    let i = 0;
    for (const [rowId, row] of rows) {
        if (startPerf) {
            const nextP = new Date(startPerf);
            nextP.setDate(nextP.getDate() + (i * 7));
            const pStr = formatDate(nextP);
            row.perf_date = pStr;
            const el = docsList.querySelector(`[data-rowid="${rowId}"]`);
            if (el) el.querySelector('.perf-input').value = pStr;
        }
        if (startSub) {
            const nextS = new Date(startSub);
            nextS.setDate(nextS.getDate() + (i * 7));
            const sStr = formatDate(nextS);
            row.sub_date = sStr;
            const el = docsList.querySelector(`[data-rowid="${rowId}"]`);
            if (el) el.querySelector('.sub-input').value = sStr;
        }
        i++;
    }
    saveCurrentProfileState();
    showToast('Weekly +7 days schedule auto-filled across all cards');
});

// ── Card Toggle (Collapse / Expand All) ───────────────────────────────────────
let allCardsOpen = true;
btnToggleCards.addEventListener('click', () => {
    allCardsOpen = !allCardsOpen;
    docsList.querySelectorAll('.acc-content').forEach(content => {
        content.classList.toggle('open', allCardsOpen);
    });
    docsList.querySelectorAll('.chevron-icon').forEach(ch => {
        ch.classList.toggle('open', allCardsOpen);
    });
    btnToggleCards.textContent = allCardsOpen ? 'Collapse All' : 'Expand All';
});

// ── Row / Card Builder ────────────────────────────────────────────────────────
function createRowEl(rowData) {
    const { rowId, label = '1', is_assignment = false, title = '',
            perf_date = '', sub_date = '', hash = null, filename = null, pages = 0 } = rowData;

    const clone = rowTemplate.content.cloneNode(true);
    const el = clone.querySelector('[data-rowid]');
    el.dataset.rowid = rowId;

    // Elements
    const header     = el.querySelector('.acc-header');
    const content    = el.querySelector('.acc-content');
    const chevron    = el.querySelector('.chevron');
    const badge      = el.querySelector('.type-badge');
    const labelInput = el.querySelector('.label-input');
    const titlePrev  = el.querySelector('.title-preview');
    const titleInput = el.querySelector('.title-input');
    const perfInput  = el.querySelector('.perf-input');
    const subInput   = el.querySelector('.sub-input');
    const typeExpBtn  = el.querySelector('.type-exp-btn');
    const typeAssgnBtn= el.querySelector('.type-assgn-btn');
    const uploadDot  = el.querySelector('.upload-dot');
    const pdfInput   = el.querySelector('.pdf-input');
    const pageBadge  = el.querySelector('.page-count-badge');

    const btnPreview        = el.querySelector('.btn-preview');
    const btnDownloadSingle = el.querySelector('.btn-download-single');
    const btnRemove         = el.querySelector('.btn-remove');
    const btnExtract        = el.querySelector('.btn-extract-aim');

    const uploadIdle    = el.querySelector('.upload-idle');
    const uploadLoading = el.querySelector('.upload-loading');
    const uploadDone    = el.querySelector('.upload-done');
    const uploadError   = el.querySelector('.upload-error');
    const uploadExpired = el.querySelector('.upload-expired');
    const uploadFilename= el.querySelector('.upload-filename');
    const uploadErrText = el.querySelector('.upload-error-text');
    const btnClearUpload= el.querySelector('.btn-clear-upload');
    const btnReupload   = el.querySelector('.btn-reupload');

    function getRow() { return rows.get(rowId); }

    function setUploadState(state) {
        uploadIdle.classList.toggle('hidden', state !== 'idle');
        uploadLoading.classList.toggle('hidden', state !== 'loading');
        uploadDone.classList.toggle('hidden', state !== 'done');
        uploadError.classList.toggle('hidden', state !== 'error');
        uploadExpired.classList.toggle('hidden', state !== 'expired');
        uploadDot.classList.toggle('hidden', state !== 'done');
    }

    function updatePageBadge(pCount) {
        if (pCount > 0) {
            pageBadge.textContent = `${pCount} pgs`;
            pageBadge.classList.remove('hidden');
        } else {
            pageBadge.classList.add('hidden');
        }
    }

    function setType(isAssignment) {
        const row = getRow();
        if (row) row.is_assignment = isAssignment;
        badge.textContent = isAssignment ? 'Assgn' : 'Exp';
        badge.className = `type-badge text-xs font-bold font-mono px-2 py-0.5 rounded shrink-0 ${
            isAssignment ? 'bg-zinc-900 border border-zinc-700 text-zinc-300' : 'bg-zinc-800 border border-border text-zinc-200'}`;
        typeExpBtn.className   = `type-exp-btn px-3 py-1.5 transition text-xs font-medium ${!isAssignment ? 'bg-white text-black font-semibold' : 'bg-surface text-muted hover:text-white'}`;
        typeAssgnBtn.className = `type-assgn-btn px-3 py-1.5 transition text-xs font-medium ${isAssignment  ? 'bg-white text-black font-semibold' : 'bg-surface text-muted hover:text-white'}`;
        saveCurrentProfileState();
    }

    labelInput.value = label;
    titleInput.value = title;
    titlePrev.textContent = title || 'Untitled';
    titlePrev.classList.toggle('italic', !title);
    titlePrev.classList.toggle('text-muted', !title);
    perfInput.value  = perf_date;
    subInput.value   = sub_date;
    setType(is_assignment);
    updatePageBadge(pages);

    if (hash) {
        uploadFilename.textContent = filename || hash.slice(0, 8) + '…';
        setUploadState('done');
        if (isAutoAim() && !title) triggerExtractAim(hash, rowId);
    } else {
        setUploadState('idle');
    }

    header.addEventListener('click', () => {
        const open = content.classList.toggle('open');
        chevron.classList.toggle('open', open);
    });

    labelInput.addEventListener('input', () => {
        const row = getRow();
        if (row) row.label = labelInput.value;
        saveCurrentProfileState();
    });

    titleInput.addEventListener('input', () => {
        const row = getRow();
        if (row) row.title = titleInput.value;
        titlePrev.textContent = titleInput.value || 'Untitled';
        titlePrev.classList.toggle('italic', !titleInput.value);
        titlePrev.classList.toggle('text-muted', !titleInput.value);
        saveCurrentProfileState();
    });

    perfInput.addEventListener('input', () => { const r=getRow(); if(r) r.perf_date=perfInput.value; saveCurrentProfileState(); });
    subInput.addEventListener('input',  () => { const r=getRow(); if(r) r.sub_date=subInput.value; saveCurrentProfileState(); });

    typeExpBtn.addEventListener('click',   () => setType(false));
    typeAssgnBtn.addEventListener('click', () => setType(true));

    async function handleFile(file) {
        if (!file || !file.name.toLowerCase().endsWith('.pdf')) {
            uploadErrText.textContent = 'Only PDF files are accepted.';
            setUploadState('error');
            return;
        }
        setUploadState('loading');
        try {
            const buf  = await file.arrayBuffer();
            const hash = await sha256(buf);

            const existsRes  = await fetch(`/api/file/${hash}/exists`);
            const existsData = await existsRes.json();

            if (existsRes.ok && existsData.exists) {
                const row = getRow();
                if (row) {
                    row.hash = hash;
                    row.filename = file.name;
                    row.pages = existsData.pages || 0;
                }
                uploadFilename.textContent = file.name;
                updatePageBadge(existsData.pages || 0);
                setUploadState('done');
                saveCurrentProfileState();
                if (isAutoAim() && !titleInput.value) triggerExtractAim(hash, rowId);
                return;
            }

            const fd = new FormData();
            fd.append('file', file);
            fd.append('hash', hash);
            const upRes  = await fetch('/api/upload', { method: 'POST', body: fd });
            const upData = await upRes.json();

            if (upData.success) {
                const row = getRow();
                if (row) {
                    row.hash = upData.hash;
                    row.filename = file.name;
                    row.pages = upData.pages || 0;
                }
                uploadFilename.textContent = file.name;
                updatePageBadge(upData.pages || 0);
                setUploadState('done');
                saveCurrentProfileState();
                if (isAutoAim() && !titleInput.value) {
                    if (upData.aim) {
                        titleInput.value = upData.aim;
                        titlePrev.textContent = upData.aim;
                        titlePrev.classList.remove('italic','text-muted');
                        if (row) row.title = upData.aim;
                        saveCurrentProfileState();
                    } else {
                        triggerExtractAim(upData.hash, rowId);
                    }
                }
            } else {
                uploadErrText.textContent = upData.error || 'Upload failed.';
                setUploadState('error');
            }
        } catch(e) {
            uploadErrText.textContent = 'Upload error: ' + e.message;
            setUploadState('error');
        }
    }

    pdfInput.addEventListener('change', e => {
        if (e.target.files[0]) handleFile(e.target.files[0]);
    });

    btnClearUpload.addEventListener('click', e => {
        e.stopPropagation();
        const row = getRow();
        if (row) { row.hash = null; row.filename = null; row.pages = 0; }
        pdfInput.value = '';
        updatePageBadge(0);
        setUploadState('idle');
        btnExtract.classList.add('hidden');
        saveCurrentProfileState();
    });

    btnReupload.addEventListener('click', e => {
        e.stopPropagation();
        pdfInput.click();
    });

    btnExtract.addEventListener('click', async () => {
        const row = getRow();
        if (!row?.hash) return;
        btnExtract.textContent = 'Extracting…';
        btnExtract.disabled = true;
        await triggerExtractAim(row.hash, rowId);
        btnExtract.textContent = 'Extract from PDF';
        btnExtract.disabled = false;
    });

    function refreshExtractBtn() {
        const row = getRow();
        const show = !isAutoAim() && !!row?.hash;
        btnExtract.classList.toggle('hidden', !show);
    }
    $('auto-aim-toggle').addEventListener('change', refreshExtractBtn);

    btnPreview.addEventListener('click', e => {
        e.stopPropagation();
        const row = getRow();
        if (row) openPreview(row);
    });

    btnDownloadSingle.addEventListener('click', e => {
        e.stopPropagation();
        const row = getRow();
        if (row) downloadSingle(row);
    });

    btnRemove.addEventListener('click', e => {
        e.stopPropagation();
        rows.delete(rowId);
        el.remove();
        updateDocSummary();
        saveCurrentProfileState();
    });

    return el;
}

// ── Bulk Multi-File Upload ────────────────────────────────────────────────────
function parsePdfFilenameMetadata(name) {
    let isAssignment = false;
    let label = '';
    let cleanTitle = '';

    const lower = name.toLowerCase();
    if (lower.includes('assign') || lower.includes('assgn')) {
        isAssignment = true;
    }

    const numMatch = name.match(/(?:exp|experiment|assgn|assignment|lab)?[\s_\-]*(\d+[a-z]?)/i);
    if (numMatch) {
        label = numMatch[1];
    }

    cleanTitle = name.replace(/\.pdf$/i, '').replace(/[\s_\-]+/g, ' ').trim();

    return { isAssignment, label, cleanTitle };
}

bulkPdfInput.addEventListener('change', async e => {
    const files = Array.from(e.target.files);
    if (!files.length) return;

    showToast(`Processing ${files.length} PDF files…`);

    for (const file of files) {
        const meta = parsePdfFilenameMetadata(file.name);
        const maxLabel = [...rows.values()].reduce((m, r) => {
            const n = parseInt(r.label);
            return isNaN(n) ? m : Math.max(m, n);
        }, 0);

        const newLabel = meta.label || String(maxLabel + 1);

        const rowData = {
            rowId:         uid(),
            label:         newLabel,
            is_assignment: meta.isAssignment,
            title:         '',
            perf_date:     globalPerfDate.value.trim(),
            sub_date:      globalSubDate.value.trim(),
            hash:          null,
            filename:      file.name,
            pages:         0
        };

        const el = addRow(rowData);
        const pdfIn = el.querySelector('.pdf-input');

        if (pdfIn) {
            const dt = new DataTransfer();
            dt.items.add(file);
            pdfIn.files = dt.files;
            pdfIn.dispatchEvent(new Event('change'));
        }
    }
    bulkPdfInput.value = '';
});

// ── Extract Aim ───────────────────────────────────────────────────────────────
async function triggerExtractAim(hash, rowId) {
    try {
        const res  = await fetch('/api/extract-aim', {
            method:  'POST',
            headers: {'Content-Type':'application/json'},
            body:    JSON.stringify({ hash }),
        });
        const data = await res.json();
        if (data.success && data.aim) {
            const el = docsList.querySelector(`[data-rowid="${rowId}"]`);
            if (el) {
                const titleInput = el.querySelector('.title-input');
                const titlePrev  = el.querySelector('.title-preview');
                if (titleInput && !titleInput.value) {
                    titleInput.value = data.aim;
                    titlePrev.textContent = data.aim;
                    titlePrev.classList.remove('italic','text-muted');
                    const row = rows.get(rowId);
                    if (row) row.title = data.aim;
                    saveCurrentProfileState();
                    showToast('Aim detected and filled.');
                }
            }
        }
    } catch {}
}

// ── Verify Upload Hashes on Restore ───────────────────────────────────────────
async function verifyUploadHashes() {
    for (const [rowId, row] of rows) {
        if (!row.hash) continue;
        const res = await fetch(`/api/file/${row.hash}/exists`);
        const data = await res.json();
        const el  = docsList.querySelector(`[data-rowid="${rowId}"]`);
        if (!el) continue;
        if (!res.ok || !data.exists) {
            row.hash = null; row.filename = null; row.pages = 0;
            el.querySelector('.upload-idle').classList.add('hidden');
            el.querySelector('.upload-done').classList.add('hidden');
            el.querySelector('.upload-expired').classList.remove('hidden');
            el.querySelector('.upload-dot').classList.add('hidden');
            saveCurrentProfileState();
        } else if (data.pages) {
            row.pages = data.pages;
            const pageBadge = el.querySelector('.page-count-badge');
            if (pageBadge) {
                pageBadge.textContent = `${data.pages} pgs`;
                pageBadge.classList.remove('hidden');
            }
        }
    }
}

// ── Preview Modal ─────────────────────────────────────────────────────────────
async function openPreview(row) {
    const label = row.is_assignment ? `Assignment ${row.label}` : `Experiment ${row.label}`;
    previewLabel.textContent = label;
    previewImg.classList.add('hidden');
    previewSpinner.classList.remove('hidden');
    previewModal.classList.remove('hidden');

    const item = {
        label:         row.label,
        is_assignment: row.is_assignment,
        title:         row.title,
        perf_date:     row.perf_date,
        sub_date:      row.sub_date,
        hash:          row.hash || null,
    };

    try {
        const res  = await fetch('/api/preview', {
            method:  'POST',
            headers: {'Content-Type':'application/json'},
            body:    JSON.stringify({ student: collectStudent(), item }),
        });
        const data = await res.json();
        if (data.success) {
            previewImg.src = data.image_data;
            previewSpinner.classList.add('hidden');
            previewImg.classList.remove('hidden');
        } else {
            showToast('Preview failed: ' + data.error);
            previewModal.classList.add('hidden');
        }
    } catch {
        showToast('Preview request failed.');
        previewModal.classList.add('hidden');
    }
}

$('btn-close-preview').addEventListener('click', () => previewModal.classList.add('hidden'));
previewModal.addEventListener('click', e => { if (e.target === previewModal) previewModal.classList.add('hidden'); });

// ── Add Row ───────────────────────────────────────────────────────────────────
function addRow(rowData = null) {
    const maxLabel = [...rows.values()].reduce((m, r) => {
        const n = parseInt(r.label);
        return isNaN(n) ? m : Math.max(m, n);
    }, 0);

    const data = rowData || {
        rowId:         uid(),
        label:         String(maxLabel + 1),
        is_assignment: false,
        title:         '',
        perf_date:     globalPerfDate.value.trim(),
        sub_date:      globalSubDate.value.trim(),
        hash:          null,
        filename:      null,
        pages:         0
    };

    rows.set(data.rowId, data);
    const el = createRowEl(data);
    docsList.appendChild(el);
    updateDocSummary();
    saveCurrentProfileState();
    return el;
}

$('btn-add-row').addEventListener('click', () => {
    addRow();
});

// ── Clear All ─────────────────────────────────────────────────────────────────
$('btn-clear').addEventListener('click', () => {
    ['student-name','roll-no','batch','class-name','sem','subject','global-perf-date','global-sub-date']
        .forEach(id => $(id).value = '');
    $('text-color').value = 'blue';
    $('strikethrough-toggle').checked = true;
    $('auto-aim-toggle').checked = false;

    rows.clear();
    docsList.innerHTML = '';
    updateDocSummary();
    saveCurrentProfileState();
    showToast('Cleared current profile.');
});

// ── Generate & Export ────────────────────────────────────────────────────────
let lastZipFile = null;

async function generate(downloadZip = false) {
    const student = collectStudent();
    if (!student.name) { showToast('Please fill in student details first.'); return; }
    if (!rows.size)    { showToast('Add at least one document.'); return; }

    const experiments = [...rows.values()].map(r => ({
        label:         r.label,
        is_assignment: r.is_assignment,
        title:         r.title,
        perf_date:     r.perf_date,
        sub_date:      r.sub_date,
        hash:          r.hash || null,
    }));

    showToast('Generating PDFs…', 10000);
    try {
        const res  = await fetch('/api/generate', {
            method:  'POST',
            headers: {'Content-Type':'application/json'},
            body:    JSON.stringify({ student, experiments }),
        });
        const data = await res.json();
        if (data.success) {
            lastZipFile = data.zip_package;
            btnZipHeader.classList.remove('hidden');
            btnZipBottom.classList.remove('hidden');

            // Show individual download buttons on rows
            data.files.forEach(f => {
                const targetRow = [...rows.values()].find(r => r.label === f.label);
                if (targetRow) {
                    const el = docsList.querySelector(`[data-rowid="${targetRow.rowId}"]`);
                    if (el) {
                        const btnDl = el.querySelector('.btn-download-single');
                        if (btnDl) {
                            btnDl.classList.remove('hidden');
                            btnDl.onclick = () => {
                                window.location.href = `/api/download/${f.merged_pdf}`;
                            };
                        }
                    }
                }
            });

            if (downloadZip && data.zip_package) {
                showToast('Done! Downloading ZIP package…');
                window.location.href = `/api/download/${data.zip_package}`;
            } else {
                showToast('Done! Downloading combined PDF…');
                window.location.href = `/api/download/${data.combined_pdf}`;
            }
        } else {
            showToast('Error: ' + (data.error || 'Generation failed.'));
        }
    } catch(e) {
        showToast('Request failed: ' + e.message);
    }
}

$('btn-generate-all').addEventListener('click', () => generate(false));
$('btn-generate-bottom').addEventListener('click', () => generate(false));

btnZipHeader.addEventListener('click', () => {
    if (lastZipFile) window.location.href = `/api/download/${lastZipFile}`;
    else generate(true);
});
btnZipBottom.addEventListener('click', () => {
    if (lastZipFile) window.location.href = `/api/download/${lastZipFile}`;
    else generate(true);
});

// ── Init ──────────────────────────────────────────────────────────────────────
function init() {
    const savedCurrent = localStorage.getItem(CURRENT_PROFILE_KEY) || 'Default';
    loadProfileState(savedCurrent);
}

init();
})();
