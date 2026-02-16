# Audio File Scanner

Scans a root folder of audio files organized by **job address** subfolders. Totals the duration of all audio files (`.mp3`, `.wav`, `.m4a`, `.flac`) per job and writes a **monthly CSV** — one file per month, automatically.

---

## Quick Start (non-techie friendly)

You only need **one thing** installed: **Python** (free).

### Step 1 — Install Python

| Your Computer | How to install Python |
|---------------|----------------------|
| **Windows**   | Go to [python.org/downloads](https://www.python.org/downloads/), click the big yellow **"Download Python"** button, run the installer. **Check the box "Add Python to PATH"** before clicking Install. |
| **Mac**       | Go to [python.org/downloads](https://www.python.org/downloads/) and download the macOS installer. Or if you have Homebrew: `brew install python3` |

### Step 2 — Set your audio folder

Open `extract_audio.py` in any text editor (Notepad, TextEdit, etc.) and change line 39 to point to your folder:

```python
AUDIO_FOLDER = Path.home() / "Music"   # change "Music" to your folder name
```

For example, if your audio jobs are in `C:\Users\YourName\Documents\Audio Jobs`:
```python
AUDIO_FOLDER = Path.home() / "Documents" / "Audio Jobs"
```

### Step 3 — Run it (one click)

| Your Computer | What to do |
|---------------|------------|
| **Windows**   | Double-click **`setup_and_run.bat`** |
| **Mac/Linux** | Double-click **`setup_and_run.sh`** (or open Terminal, drag the file in, press Enter) |

The launcher handles everything automatically — installs packages, runs the scanner, and shows your results. Your CSV files will appear in the same folder.

---

## Folder structure expected

```
Audio Jobs/
  ├── 123 Main Street/
  │     ├── recording1.m4a
  │     ├── recording2.m4a
  │     └── recording3.m4a
  ├── 456 Oak Avenue/
  │     ├── part1.mp3
  │     └── part2.mp3
  └── 789 Pine Road/
        └── full_session.wav
```

Each **subfolder name** = the job address. Audio files inside are **never renamed or moved**.

## Setup

```bash
# 1. Create a virtual environment
python3 -m venv venv

# 2. Activate it
#    Linux / macOS:
source venv/bin/activate
#    Windows:
venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt
```

## Configuration

Open `extract_audio.py` and edit the variables at the top:

```python
AUDIO_FOLDER = Path.home() / "Music"   # root folder with job-address subfolders
OUTPUT_DIR   = Path(".")               # where monthly CSVs are saved
EXPORT_EXCEL = False                   # set True for .xlsx export
```

### Example folder paths

| OS      | Example path                              |
|---------|-------------------------------------------|
| Linux   | `Path.home() / "Music"`                   |
| macOS   | `Path.home() / "Music"`                   |
| Windows | `Path.home() / "Music"`                   |
| Custom  | `Path("/mnt/external/my_audio_files")`    |

## Run

```bash
python extract_audio.py
```

## Output

### Monthly CSV files

The script creates one CSV per month, named automatically:

```
audio_index_2026-01.csv
audio_index_2026-02.csv
audio_index_2026-03.csv
...
```

Each file contains:

| Date_Received | Job_Address          | Total_Duration |
|---------------|----------------------|----------------|
| 2026-02-03    | 123 Main Street      | 12:45          |
| 2026-02-10    | 456 Oak Avenue       | 08:22          |
|               | ** TOTAL 2026-02 **  | 21:07          |

### Console output

```
  Month: 2026-01
  ────────────────────────────────────────────────────────────────
  DATE           JOB ADDRESS                        TOTAL DURATION
  ────────────────────────────────────────────────────────────────
  2026-01-15     789 Pine Road                            45:30
  ────────────────────────────────────────────────────────────────
                 MONTH TOTAL                               45:30
  ────────────────────────────────────────────────────────────────

  Month: 2026-02
  ────────────────────────────────────────────────────────────────
  DATE           JOB ADDRESS                        TOTAL DURATION
  ────────────────────────────────────────────────────────────────
  2026-02-03     123 Main Street                          12:45
  2026-02-10     456 Oak Avenue                            08:22
  ────────────────────────────────────────────────────────────────
                 MONTH TOTAL                               21:07
  ────────────────────────────────────────────────────────────────

  ════════════════════════════════════════════════════════════════
  GRAND TOTAL                                       3 job(s)   01:06:37
  ════════════════════════════════════════════════════════════════
```

### `processing_log.txt`

A timestamped log of every run — individual file durations, skipped files, and errors.

## Features

- **Month-wise CSVs** — one file per month, created automatically based on folder dates.
- **3-column output** — Date Received, Job Address, Total Duration (MM:SS or HH:MM:SS).
- **Read-only** — audio files are never renamed, moved, or modified.
- **Grouped by job** — each subfolder = one job address; all audio durations inside are summed.
- **Duplicate detection** — jobs already in any CSV are not re-processed.
- **Error handling** — corrupted or unreadable files are logged and skipped.
- **Append mode** — re-running adds only new jobs; existing rows are preserved.
- **Date auto-detection** — uses the folder's creation/modification date as Date_Received.
- **Cross-platform** — uses `pathlib`; no hardcoded OS paths.
- **Excel export** — set `EXPORT_EXCEL = True` to also write `.xlsx` versions.
