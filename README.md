# Audio File Scanner

Scans a root folder of audio files organized by **job address** subfolders. Totals the duration of all audio files (`.mp3`, `.wav`, `.m4a`, `.flac`) per job and writes a clean 3-column CSV.

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

Each **subfolder name** = the job address.

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
OUTPUT_CSV   = Path("audio_index.csv") # output CSV path
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

### `audio_index.csv`

| Date_Received | Job_Address       | Total_Duration |
|---------------|-------------------|----------------|
| 2026-01-15    | 123 Main Street   | 12:45          |
| 2026-02-03    | 456 Oak Avenue    | 08:22          |
| 2026-02-10    | 789 Pine Road     | 45:30          |
|               | ** GRAND TOTAL ** | 01:06:37       |

### Console output

```
────────────────────────────────────────────────────────────────
DATE           JOB ADDRESS                        TOTAL DURATION
────────────────────────────────────────────────────────────────
2026-01-15     123 Main Street                          12:45
2026-02-03     456 Oak Avenue                            08:22
2026-02-10     789 Pine Road                             45:30
────────────────────────────────────────────────────────────────
               GRAND TOTAL                            01:06:37
────────────────────────────────────────────────────────────────
```

### `processing_log.txt`

A timestamped log of every run — individual file durations, skipped files, and errors.

## Features

- **3-column output** — Date Received, Job Address, Total Duration (MM:SS or HH:MM:SS).
- **Grouped by job** — each subfolder is treated as one job address; all audio durations inside are summed.
- **Duplicate detection** — jobs already in the CSV are not re-processed.
- **Error handling** — corrupted or unreadable files are logged and skipped.
- **Append mode** — re-running adds only new jobs; existing rows are preserved.
- **Date auto-detection** — uses the folder's creation/modification date as Date_Received.
- **Cross-platform** — uses `pathlib`; no hardcoded OS paths.
- **Excel export** — set `EXPORT_EXCEL = True` to also write `audio_index.xlsx`.
