# LabStudio Frontend API Contract

This document specifies the exact, frozen HTTP contract exposed by the Flask backend (`app.py` v3.0.0). Every field, data type, header, status code, and error condition documented below reflects the verified source implementation.

---

## Global Architectural Conventions

### Base URL
* In production: Served from the same origin under `/api/...` via Caddy reverse proxy.
* In development: Vite proxy forwards `/api` to `http://127.0.0.1:7860`.

### Error Response Schema
All error responses from application routes and global exception handlers conform to this structure:
```json
{
  "success": false,
  "error": "Human-readable description of error"
}
```

### Rate Limiting Headers
Enforced by `Flask-Limiter`. When exceeded, endpoints return `HTTP 429 Too Many Requests` with:
```json
{
  "success": false,
  "error": "Rate limit exceeded: <limit>"
}
```

---

## 1. System Health Check

### `GET /api/health`
* **Purpose**: Verifies backend availability, uptime, and storage capacity metrics.
* **Headers**: None required.
* **Request Body**: None.
* **Idempotent**: Yes.
* **Cacheable**: No (dynamic storage metrics).

#### Success Response (`HTTP 200 OK`)
```json
{
  "status": "ok",
  "version": "3.0.0",
  "uptime_seconds": 1248,
  "storage": {
    "used_bytes": 147393478,
    "max_bytes": 16106127360,
    "percent_used": 0.9
  }
}
```

| Field | Type | Nullable | Description |
| :--- | :--- | :--- | :--- |
| `status` | string | No | Always `"ok"` when operational. |
| `version` | string | No | Semantic version of backend engine. |
| `uptime_seconds` | integer | No | Elapsed seconds since Gunicorn master boot. |
| `storage.used_bytes` | integer | No | Total disk bytes consumed in `uploads/` and `output/`. |
| `storage.max_bytes` | integer | No | Configured storage quota ceiling (default: 15 GB). |
| `storage.percent_used` | float | No | Percentage of quota used (`used_bytes / max_bytes * 100`). |

---

## 2. Load Defaults

### `GET /api/load-defaults`
* **Purpose**: Retrieves baseline student profile schema and initial empty experiment item.
* **Headers**: None required.
* **Request Body**: None.
* **Idempotent**: Yes.

#### Success Response (`HTTP 200 OK`)
```json
{
  "student": {
    "name": "",
    "roll_no": "",
    "batch": "",
    "class_name": "",
    "sem": "",
    "subject": "",
    "text_color": "blue",
    "strikethrough_enabled": true
  },
  "experiments": [
    {
      "num": 1,
      "label": "1",
      "title": "",
      "is_assignment": false,
      "perf_date": "",
      "sub_date": "",
      "file_exists": false,
      "pages": 0
    }
  ]
}
```

---

## 3. Check Cached Upload Existence

### `GET /api/file/<hash_val>/exists`
* **Purpose**: Checks whether a PDF with the given SHA-256 hash already exists in `uploads/`. Allows client-side deduplication (skips re-uploading on repeat sessions).
* **URL Parameters**:
  * `hash_val` (string, required): 64-character lowercase hexadecimal SHA-256 string.
* **Idempotent**: Yes.

#### Responses
* **`HTTP 200 OK` (File exists)**:
  ```json
  {
    "exists": true,
    "pages": 4,
    "aim": "Configuring MQTT Broker and Publisher on Raspberry Pi",
    "exp_num": "1",
    "is_assignment": false,
    "extraction_method": "aim_keyword"
  }
  ```
* **`HTTP 404 Not Found` (File does not exist)**:
  ```json
  {
    "exists": false
  }
  ```
* **`HTTP 400 Bad Request` (Invalid hash syntax)**:
  ```json
  {
    "exists": false,
    "error": "Invalid hash"
  }
  ```

---

## 4. File Upload (Chunked Streaming)

### `POST /api/upload`
* **Purpose**: Uploads a single lab experiment PDF. Streams in 64 KB chunks, enforces magic bytes, verifies SHA-256, stores content-addressed PDF (`uploads/<sha256>.pdf`), extracts metadata, and records diagnostic telemetry.
* **Rate Limit**: 40 uploads per minute per IP.
* **Content-Type**: `multipart/form-data`.
* **Payload Constraints**:
  * Body limit: 100 MB (`MAX_CONTENT_LENGTH`).
  * Page limit: 300 pages (`info["pages"] <= 300`).
  * Magic bytes: Must begin with `%PDF-`.

#### Request Form Fields
| Field | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `file` | Binary File | **Yes** | The PDF file blob. Must have `.pdf` extension. |
| `hash` | string | No | Optional pre-calculated client SHA-256 hex. If supplied, verified server-side. |
| `mode` | string | No | Extraction mode (default: `"auto"`). |

#### Success Response (`HTTP 200 OK`)
```json
{
  "success": true,
  "hash": "d785e45c9a92b28a039bef5218e2e785b9de140a389aac8f0dd4a8a6f0d4a488",
  "size": 310392,
  "pages": 4,
  "aim": "Configuring MQTT Broker and Publisher on Raspberry Pi",
  "exp_num": "1",
  "is_assignment": false,
  "extraction_method": "aim_keyword",
  "failure_reason": "none"
}
```

| Field | Type | Nullable | Description |
| :--- | :--- | :--- | :--- |
| `success` | boolean | No | Always `true` on 200 OK. |
| `hash` | string | No | 64-character lowercase SHA-256 hex string. |
| `size` | integer | No | Exact byte count written to disk. |
| `pages` | integer | No | Total pages detected in PDF. |
| `aim` | string | **Yes** | Extracted experiment aim/title, or `null` if unextracted. |
| `exp_num` | string | **Yes** | Extracted experiment/assignment number (e.g. `"1"`, `"2"`), or `null`. |
| `is_assignment`| boolean | No | `true` if document classified as Assignment; `false` if Experiment. |
| `extraction_method` | string | No | e.g. `"aim_keyword"`, `"first_period"`, `"header_title"`, `"filename_heuristic"`, `"unextracted"`. |
| `failure_reason` | string | No | `"none"`, or e.g. `"no_aim_keyword"`, `"no_text_layer"`, `"password_protected"`. |

#### Error Responses
* **`HTTP 400 Bad Request`**:
  * `{"success": false, "error": "No file provided"}`
  * `{"success": false, "error": "Only PDF files are accepted"}`
  * `{"success": false, "error": "Invalid file format: must be a valid PDF document."}`
  * `{"success": false, "error": "Hash mismatch — file may be corrupted"}`
  * `{"success": false, "error": "Unreadable or corrupted PDF."}`
  * `{"success": false, "error": "PDF exceeds 300-page limit."}`
* **`HTTP 413 Payload Too Large`**:
  * Handled globally: `{"success": false, "error": "File exceeds maximum upload size (100MB)."}`
* **`HTTP 500 Internal Server Error`**:
  * `{"success": false, "error": "<exception message>"}`

---

## 5. Re-Extract Aim from Existing File

### `POST /api/extract-aim`
* **Purpose**: Re-executes heuristic extraction on an already uploaded PDF (useful if student changes extraction mode).
* **Rate Limit**: 60 per minute per IP.
* **Content-Type**: `application/json`.

#### Request Body
```json
{
  "hash": "d785e45c9a92b28a039bef5218e2e785b9de140a389aac8f0dd4a8a6f0d4a488",
  "mode": "auto"
}
```

#### Success Response (`HTTP 200 OK`)
```json
{
  "success": true,
  "aim": "Configuring MQTT Broker and Publisher on Raspberry Pi",
  "pages": 4,
  "exp_num": "1",
  "is_assignment": false
}
```

---

## 6. Live Header Preview

### `POST /api/preview`
* **Purpose**: Renders Page 1 of the filled institutional A4 cover sheet as a rasterized PNG image at 150 DPI.
* **Rate Limit**: 60 per minute per IP.
* **Content-Type**: `application/json`.
* **Idempotent**: Yes.

#### Request Body
```json
{
  "student": {
    "name": "Bhavya Shah",
    "roll_no": "77",
    "batch": "B3",
    "class_name": "BE IT",
    "sem": "VIII",
    "subject": "Internet of Things",
    "text_color": "#0000bf",
    "strikethrough_enabled": true
  },
  "item": {
    "num": 1,
    "label": "1",
    "title": "Interfacing Temperature Sensor with ESP32",
    "is_assignment": false,
    "perf_date": "10/01/2026",
    "sub_date": "17/01/2026"
  }
}
```

*Note on schema flexibility*: The backend accepts flat fields or nested `student`/`item` objects.

#### Success Response (`HTTP 200 OK`)
```json
{
  "success": true,
  "image_data": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...",
  "image": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA..."
}
```

---

## 7. Generate Compiled Lab Package

### `POST /api/generate`
* **Purpose**: The core compilation orchestrator. Merges institutional headers with body PDFs, generates the vector Table of Contents with clickable links, bookmarks all sections, produces individual PDFs, a master combined PDF, and a `.zip` archive.
* **Rate Limit**: 20 requests per minute per IP.
* **Content-Type**: `application/json`.
* **Timeout Window**: 120 seconds (typical execution: 0.5s–20.6s).
* **Batch Constraint**: `1 <= len(experiments) <= 60`.

#### Request Body
```json
{
  "student": {
    "name": "Bhavya Shah",
    "roll_no": "77",
    "batch": "B3",
    "class_name": "BE IT",
    "sem": "VIII",
    "subject": "Internet of Things",
    "text_color": "#0000bf",
    "strikethrough_enabled": true
  },
  "experiments": [
    {
      "num": 1,
      "label": "1",
      "title": "Interfacing Temperature Sensor with ESP32",
      "is_assignment": false,
      "hash": "d785e45c9a92b28a039bef5218e2e785b9de140a389aac8f0dd4a8a6f0d4a488",
      "pages": 4,
      "perf_date": "10/01/2026",
      "sub_date": "17/01/2026"
    }
  ],
  "formatting": {
    "text_color": "#0000bf",
    "strikethrough_enabled": true,
    "font_size": 11
  },
  "include_toc": true
}
```

#### Success Response (`HTTP 200 OK`)
```json
{
  "success": true,
  "job_id": "job_29a3b86edc",
  "combined_pdf": "job_29a3b86edc/77_Internet_of_Things_Combined.pdf",
  "zip_package": "job_29a3b86edc/77_Internet_of_Things_Package.zip",
  "files": [
    {
      "label": "1",
      "merged_pdf": "job_29a3b86edc/Exp_1_with_Header.pdf"
    }
  ]
}
```

| Field | Type | Description |
| :--- | :--- | :--- |
| `success` | boolean | `true` upon successful compilation. |
| `job_id` | string | Unique 14-character hexadecimal execution folder identifier. |
| `combined_pdf` | string | Relative download path to master combined PDF containing TOC + all experiments. |
| `zip_package` | string | Relative download path to ZIP package containing combined PDF + all individual PDFs. |
| `files` | array | List of individual compiled PDF deliverables. |
| `files[i].label` | string | Experiment/assignment label (e.g. `"1"`, `"2A"`). |
| `files[i].merged_pdf`| string | Relative download path to individual merged PDF. |

#### Error Responses
* **`HTTP 400 Bad Request`**:
  * `{"success": false, "error": "No experiments provided."}`
  * `{"success": false, "error": "Batch limit exceeded (maximum 60 experiments allowed per compilation)."}`
* **`HTTP 500 Internal Server Error`**:
  * `{"success": false, "error": "<reason>"}` (Open handles are automatically closed in `finally:` blocks).

---

## 8. Download Deliverables

### `GET /api/download/<path:filepath>`
* **Purpose**: Serves compiled deliverables from `output/<filepath>`.
* **Path Validation**: Strictly forbids `..`, leading slashes, and restricts resolution to `OUTPUT_DIR`.
* **Idempotent**: Yes.

#### Response
* **`HTTP 200 OK`**: Binary stream (`application/pdf` or `application/zip`) with `Content-Disposition: attachment; filename="<filename>"`.
* **`HTTP 400 Bad Request`**: `{"error": "Invalid path"}` (if traversal detected).
* **`HTTP 404 Not Found`**: `{"error": "File not found"}` (if job expired or does not exist).
