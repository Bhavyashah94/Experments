---
title: LabStudio
sdk: docker
app_port: 7860
pinned: false
---

# LabStudio

**LabStudio** is a fast web application for engineering and college students to generate, customize, and merge standardized lab report header pages with experiment body PDFs.

Built with a monochrome studio aesthetic (**Pitch Black `#050505` + Studio Charcoal `#141417`**), zero emojis, and content-addressable SHA-256 PDF processing.

---

## Key Features

- **Zero-Click Card Editing**: Document cards are expanded by default for instant editing.
- **Auto-Detect Aim & Experiment Number**: Automatically inspects Page 1 of attached PDFs using PyMuPDF regex to extract Aim titles, Experiment/Assignment numbers, and type (`Exp` vs `Assgn`).
- **Bulk Multi-PDF Upload**: Drag and drop multiple experiment PDFs at once. Automatically creates cards, parses numbers, and extracts aims.
- **Quick Date Presets & Weekly Increment**: Set Global Performance and Submission dates and use **`+7 Days Weekly Auto-Fill`** to auto-fill sequential dates across all cards.
- **Hex Color & Ink Controls**: Custom Hex color text field (`#0000BF`), clickable color picker swatch, 6 quick preset swatches (Royal Blue, Navy, Pure Black, Crimson, Emerald, Violet), and persistent recently used color history saved in `localStorage`.
- **Subject Profile Persistence**: Save and switch between subject profiles (e.g. *IoT Lab*, *Cloud Computing*) stored in browser local storage.
- **Content-Addressable PDF Store (SHA-256)**: Computes SHA-256 hashes client-side to eliminate duplicate uploads, with a background thread running a **24-hour TTL sweep** on server files.
- **ZIP Package & Merged PDF Exports**: Generate single merged PDFs or export all documents into a clean `All_Documents_Package.zip`.

---

## Tech Stack

- **Backend**: Python 3, Flask, PyMuPDF (`fitz`), Gunicorn
- **Frontend**: HTML5, Vanilla JavaScript (ES6+), Tailwind CSS, Flowbite
- **Typography**: Inter & JetBrains Mono (Google Fonts)
- **State Management**: `localStorage` (Profiles & Color History) + SHA-256 client hashing (`crypto.subtle`)

---

## Getting Started Locally

### 1. Prerequisites
- Python 3.9 or higher

### 2. Installation & Setup
```bash
# Clone the repository
git clone https://github.com/Bhavyashah94/Experments.git
cd Experments

# Install dependencies
pip install -r requirements.txt

# Start the Flask development server
python app.py
```

Open **`http://localhost:5000`** in your browser.

---

## Usage Analytics (Internal)

LabStudio includes a lightweight, privacy-first, first-party analytics system powered by indexed SQLite storage.

- **Hidden Access Route**: Available directly at `/analytics` (isolated from the student navigation).
- **Zero Third-Party SDKs**: No Google Analytics, Mixpanel, or external telemetry.
- **Fail-Safe**: Analytics recording never interrupts or blocks student document generation.

### Environment Configuration (Render / Server)

Configure the following environment variables in Render:

| Variable | Description | Default |
| :--- | :--- | :--- |
| `ENABLE_ANALYTICS` | Set `true` to enable or `false` to disable. | `true` (Always enabled) |
| `ADMIN_PASSWORD` or `ANALYTICS_ADMIN_PASSWORD` | Password required to view the `/analytics` dashboard. | *(None - Open direct access)* |
| `ANALYTICS_DB_PATH` | Path to the SQLite analytics database file. | `data/analytics.db` |

---

## Authors

- **Bhavya Shah** — [@Bhavyashah94](https://github.com/Bhavyashah94)
- **Antigravity** — Advanced Agentic Coding

---

## License

MIT License. Built for students & researchers.

