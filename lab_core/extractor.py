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
    info = {"aim": None, "pages": 0, "exp_num": None, "is_assignment": None}
    if not os.path.exists(pdf_path):
        return info

    try:
        doc = fitz.open(pdf_path)
        if doc.is_encrypted:
            info["error"] = "PDF is password-protected / encrypted."
            doc.close()
            return info

        info["pages"] = len(doc)
        if len(doc) > 0:
            text = doc[0].get_text()
            lines = [l.strip() for l in text.splitlines() if l.strip()]

            # 1. Detect Exp/Assign Number and Type from PDF Page 1 text
            for line in lines[:20]:
                match = re.search(
                    r'\b(Exp|Experiment|Practical|Prac|Lab|Assignment|Assign|Assgn|Task)[\s\-_.]*(?:No|Num|Number|Session|Exercise)?[\s:_#.-]*(\d+[a-z]?|[ivx]+)\b',
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
                    r'\b(Exp|Experiment|Practical|Prac|Lab|Assignment|Assign|Assgn|Task)[\s\-_.]*(\d+[a-z]?|[ivx]+)\b',
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
                    r'\b(?:Exp|Experiment|Practical|Prac|Lab|Assignment|Assign|Assgn|Task)[\s\-_.]*(?:No|Num|Number|Session|Exercise)?[\s:_#.-]*(?:\d+[a-z]?|[ivx]+)[\s:_.\-#]+\s*(.+)$',
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
                period_pos = full_aim_text.find('.')
                if period_pos != -1:
                    aim_first_period = full_aim_text[:period_pos + 1].strip()
                else:
                    aim_first_period = full_aim_text

            # Apply requested mode logic
            if mode == 'header_title':
                info["aim"] = header_title or aim_first_period
            elif mode == 'first_period':
                info["aim"] = aim_first_period or header_title
            else:  # auto
                info["aim"] = aim_first_period or header_title

        doc.close()
    except Exception as e:
        print(f"Warning: Could not inspect PDF {pdf_path}: {e}")

    return info


def extract_aim_from_pdf(pdf_path: str, mode: str = 'auto') -> str | None:
    """Extract Aim/Title text from an experiment PDF."""
    info = inspect_pdf_info(pdf_path, mode=mode)
    return info.get("aim")
