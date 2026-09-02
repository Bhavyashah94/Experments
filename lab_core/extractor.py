import os
import re
import fitz  # PyMuPDF

ROMAN_NUMERALS = {
    'i': '1',
    'ii': '2',
    'iii': '3',
    'iv': '4',
    'v': '5',
    'vi': '6',
    'vii': '7',
    'viii': '8',
    'ix': '9',
    'x': '10',
    'xi': '11',
    'xii': '12',
    'xiii': '13',
    'xiv': '14',
    'xv': '15',
}


def normalize_exp_number(val: str) -> str:
    """Normalize extracted number or roman numeral into standard string."""
    val_clean = val.strip().lower()
    if val_clean in ROMAN_NUMERALS:
        return ROMAN_NUMERALS[val_clean]
    # Remove leading zeros like '04' -> '4', but keep alphanumeric like '1a'
    if re.match(r'^0+\d+', val_clean):
        return val_clean.lstrip('0')
    return val.strip()


def inspect_pdf_info(pdf_path: str, mode: str = 'auto') -> dict:
    """
    Extract Aim/Title text, Experiment/Assignment number, type, and total page count from an experiment PDF.

    :param pdf_path: Path to the PDF file.
    :param mode: Extraction mode ('auto', 'first_period', or 'header_title').
    :return: dict with keys: 'aim', 'pages', 'exp_num', 'is_assignment'
    """
    info = {
        "aim": None,
        "pages": 0,
        "exp_num": None,
        "is_assignment": None,
        "extraction_method": "unextracted",
        "failure_reason": "none",
        "text_snippet": "",
        "page1_has_images": False,
    }
    if not os.path.exists(pdf_path):
        info["failure_reason"] = "file_not_found"
        return info

    try:
        doc = fitz.open(pdf_path)
        if doc.is_encrypted:
            info["error"] = "PDF is password-protected / encrypted."
            info["failure_reason"] = "password_protected"
            doc.close()
            return info

        info["pages"] = len(doc)
        if len(doc) > 0:
            page1 = doc[0]
            text = page1.get_text()
            lines = [l.strip() for l in text.splitlines() if l.strip()]
            img_list = page1.get_images()
            has_images = len(img_list) > 0
            is_scanned = len(text.strip()) < 30 and has_images
            failure_reasons = []

            # 1. Detect Exp/Assign Number and Type from PDF Page 1 text
            roman_re = r'(?:xv|xiv|xiii|xii|xi|x|ix|viii|vii|vi|v|iv|iii|ii|i)'
            for line in lines[:20]:
                match = re.search(
                    rf'\b(Exp|Experiment|Expt|Practical|Prac|Lab|Assignment|Assign|Assgn|Task)[\s\-_.]*(?:No|Num|Number|Session|Exercise)?[\s:_#.-]*(\d+[a-z]?|\b{roman_re}\b)\b',
                    line,
                    re.IGNORECASE,
                )
                if match:
                    type_str = match.group(1).lower()
                    raw_num = match.group(2)
                    info["exp_num"] = normalize_exp_number(raw_num)
                    info["is_assignment"] = True if 'ass' in type_str else False
                    break

            # 2. Fallback: Parse from filename if text had no explicit number
            if not info["exp_num"]:
                filename = os.path.basename(pdf_path)
                fn_match = re.search(
                    rf'\b(Exp|Experiment|Expt|Practical|Prac|Lab|Assignment|Assign|Assgn|Task)[\s\-_.]*(\d+[a-z]?|\b{roman_re}\b)\b',
                    filename,
                    re.IGNORECASE,
                )
                if fn_match:
                    type_str = fn_match.group(1).lower()
                    raw_num = fn_match.group(2)
                    info["exp_num"] = normalize_exp_number(raw_num)
                    info["is_assignment"] = True if 'ass' in type_str else False

            # 3. Method B: Header Title Line Extraction
            header_title = None
            for line in lines[:20]:
                exp_title_match = re.search(
                    rf'\b(?:Exp|Experiment|Expt|Practical|Prac|Lab|Assignment|Assign|Assgn|Task)[\s\-_.]*(?:No|Num|Number|Session|Exercise)?[\s:_#.-]*(?:\d+[a-z]?|\b{roman_re}\b)[\s:_.\-#]+\s*(.+)$',
                    line,
                    re.IGNORECASE,
                )
                if exp_title_match:
                    found_title = exp_title_match.group(1).strip()
                    if len(found_title) > 3 and not found_title.lower().startswith(('date', 'roll', 'name', 'page')):
                        header_title = found_title
                        break

            # 4. Method A: First Full Stop Method (Aim: ...)
            aim_first_period = None
            aim_lines = []
            capture = False

            for line in lines:
                m_aim = re.match(r'^(?:Aim|AIM|Title|TITLE|Objective|OBJECTIVE)[\s:]*(.*)$', line, re.IGNORECASE)
                if m_aim:
                    capture = True
                    val = m_aim.group(1).strip()
                    if val:
                        aim_lines.append(val)
                        if '.' in val:
                            break
                elif capture:
                    if re.search(
                        r'^\s*(?:Step|Task|Section|Phase|Part|\d+\.|\bObjectives?\b|\bTheory\b|\bProcedure\b|\bApparatus\b|\bPrerequisites\b|\bRequirements\b|\bIntroduction\b|\bOverview\b|\bDescription\b|\bGuide\b|\bNote\b|\bRoll\b|\bDate\b)',
                        line,
                        re.IGNORECASE,
                    ):
                        break
                    aim_lines.append(line)
                    if '.' in line:
                        break

            full_aim_text = ' '.join(aim_lines).strip()
            if full_aim_text:
                boundary = re.search(r'(?<!\be\.g)(?<!\bi\.e)(?<!\bvs)(?<!\bfig)(?<!\bno)(?<!\bv)(?<!\b[0-9])\.(?:\s+|$)', full_aim_text, re.IGNORECASE)
                if boundary:
                    aim_first_period = full_aim_text[:boundary.start() + 1].strip()
                else:
                    aim_first_period = full_aim_text

            # 5. Method C: Fallback to Filename Title parsing
            filename_title = None
            if not aim_first_period and not header_title:
                fname_clean = os.path.splitext(os.path.basename(pdf_path))[0]
                fn_title_match = re.search(
                    rf'(?:Exp|Experiment|Expt|Practical|Prac|Lab|Assignment|Assign|Assgn|Task)?[\s\-_.]*(?:No|Num|Number)?[\s:_#.-]*(?:\d+[a-z]?|\b{roman_re}\b)?[\s:_.\-#]+\s*(.+)$',
                    fname_clean,
                    re.IGNORECASE,
                )
                if fn_title_match:
                    cand = fn_title_match.group(1).strip()
                    if len(cand) > 3 and not cand.lower().startswith(('report', 'document', 'pdf', 'scan')):
                        filename_title = cand

            # Resolve title and determine diagnostic method & failure reasons
            if mode == 'header_title' and header_title:
                info["aim"] = header_title
                info["extraction_method"] = "header_title"
            elif aim_first_period:
                info["aim"] = aim_first_period
                info["extraction_method"] = "aim_keyword"
            elif header_title:
                info["aim"] = header_title
                info["extraction_method"] = "header_title"
            elif filename_title:
                info["aim"] = filename_title
                info["extraction_method"] = "filename_heuristic"
            else:
                info["aim"] = None
                if is_scanned:
                    info["extraction_method"] = "scanned_no_text"
                    failure_reasons.append("no_text_layer")
                else:
                    info["extraction_method"] = "unextracted"
                    failure_reasons.append("no_aim_keyword")

            if not info["exp_num"]:
                failure_reasons.append("no_exp_number_found")

            info["failure_reason"] = ", ".join(failure_reasons) if failure_reasons else "none"
            info["text_snippet"] = text[:600].strip() if text else ""
            info["page1_has_images"] = has_images

        doc.close()
    except Exception as e:
        info["error"] = f"Unreadable PDF: {e}"
        info["failure_reason"] = f"unreadable_error: {e}"
        print(f"Warning: Could not inspect PDF {pdf_path}: {e}")

    return info


def extract_aim_from_pdf(pdf_path: str, mode: str = 'auto') -> str | None:
    """Extract Aim/Title text from an experiment PDF."""
    info = inspect_pdf_info(pdf_path, mode=mode)
    return info.get("aim")
