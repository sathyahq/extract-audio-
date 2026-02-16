# Audio File Scanner

Scans a desktop folder for audio files (`.mp3`, `.wav`, `.m4a`, `.flac`), extracts metadata (title, duration, file size), and writes the results to a CSV table. Optionally exports to Excel.

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
AUDIO_FOLDER = Path.home() / "Music"   # folder to scan
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

| Title | Filename | Duration_Seconds | Duration_Minutes | Duration_Formatted | Full_File_Path | File_Size_MB | Date_Processed |
|-------|----------|------------------|------------------|--------------------|----------------|--------------|----------------|
| song1 | song1.mp3 | 245.67 | 4.09 | 04:06 | /home/user/Music/song1.mp3 | 5.82 | 2026-02-16 10:30:00 |
| track | track.flac | 312.44 | 5.21 | 05:12 | /home/user/Music/track.flac | 32.10 | 2026-02-16 10:30:00 |

### `processing_log.txt`

A timestamped log of every run — files processed, duplicates skipped, and errors encountered.

## Features

- **Duplicate detection** — files already in the CSV (matched by full path) are skipped.
- **Error handling** — corrupted or unreadable files are logged and skipped.
- **Append mode** — re-running the script adds only new files; existing rows are preserved.
- **Cross-platform** — uses `pathlib` throughout; no hardcoded OS paths.
- **Excel export** — set `EXPORT_EXCEL = True` and the script writes `audio_index.xlsx` alongside the CSV.
