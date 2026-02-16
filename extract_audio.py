#!/usr/bin/env python3
"""
Desktop Audio File Scanner
Scans a folder for audio files, extracts metadata (filename, duration, size),
and appends structured data into a CSV table. Optionally exports to Excel.
"""

import csv
import logging
import os
import platform
import sys
from datetime import datetime
from pathlib import Path

try:
    from mutagen import File as MutagenFile
except ImportError:
    sys.exit("Error: 'mutagen' is not installed. Run: pip install mutagen")

try:
    import pandas as pd
except ImportError:
    sys.exit("Error: 'pandas' is not installed. Run: pip install pandas")

# ──────────────────────────────────────────────
# CONFIGURATION — edit these values as needed
# ──────────────────────────────────────────────
AUDIO_FOLDER = Path.home() / "Music"  # <-- change this to your target folder
OUTPUT_CSV = Path("audio_index.csv")
LOG_FILE = Path("processing_log.txt")
EXPORT_EXCEL = False  # set True to also write audio_index.xlsx

SUPPORTED_EXTENSIONS = {".mp3", ".wav", ".m4a", ".flac"}

CSV_COLUMNS = [
    "Title",
    "Filename",
    "Duration_Seconds",
    "Duration_Minutes",
    "Duration_Formatted",
    "Full_File_Path",
    "File_Size_MB",
    "Date_Processed",
]


# ──────────────────────────────────────────────
# Logging setup
# ──────────────────────────────────────────────
def setup_logging(log_path: Path) -> logging.Logger:
    """Configure a logger that writes to both console and a log file."""
    logger = logging.getLogger("audio_scanner")
    logger.setLevel(logging.INFO)

    fmt = logging.Formatter("%(asctime)s  %(levelname)-8s  %(message)s",
                            datefmt="%Y-%m-%d %H:%M:%S")

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(fmt)
    logger.addHandler(console_handler)

    return logger


# ──────────────────────────────────────────────
# Audio helpers
# ──────────────────────────────────────────────
def get_audio_duration(file_path: Path) -> float | None:
    """Return the duration in seconds using mutagen, or None on failure."""
    try:
        audio = MutagenFile(str(file_path))
        if audio is None or audio.info is None:
            return None
        return audio.info.length
    except Exception:
        return None


def format_duration(seconds: float) -> str:
    """Convert seconds to MM:SS string."""
    total = int(round(seconds))
    minutes, secs = divmod(total, 60)
    return f"{minutes:02d}:{secs:02d}"


def file_size_mb(file_path: Path) -> float:
    """Return the file size in megabytes, rounded to 2 decimals."""
    return round(file_path.stat().st_size / (1024 * 1024), 2)


# ──────────────────────────────────────────────
# File discovery
# ──────────────────────────────────────────────
def find_audio_files(folder: Path) -> list[Path]:
    """Return a sorted list of supported audio files in *folder*."""
    files = [
        p for p in folder.iterdir()
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
    ]
    files.sort(key=lambda p: p.name.lower())
    return files


# ──────────────────────────────────────────────
# CSV / duplicate handling
# ──────────────────────────────────────────────
def load_existing_paths(csv_path: Path) -> set[str]:
    """Read the CSV and return a set of Full_File_Path values already stored."""
    paths: set[str] = set()
    if not csv_path.exists():
        return paths
    with csv_path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            paths.add(row["Full_File_Path"])
    return paths


def append_rows(csv_path: Path, rows: list[dict]) -> None:
    """Append *rows* to the CSV, creating it with headers if needed."""
    file_exists = csv_path.exists()
    with csv_path.open("a", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_COLUMNS)
        if not file_exists:
            writer.writeheader()
        writer.writerows(rows)


# ──────────────────────────────────────────────
# Excel export
# ──────────────────────────────────────────────
def export_to_excel(csv_path: Path) -> Path:
    """Read the CSV with pandas and write an .xlsx copy next to it."""
    xlsx_path = csv_path.with_suffix(".xlsx")
    df = pd.read_csv(csv_path)
    try:
        df.to_excel(xlsx_path, index=False)
    except ImportError:
        sys.exit(
            "Error: 'openpyxl' is required for Excel export. "
            "Run: pip install openpyxl"
        )
    return xlsx_path


# ──────────────────────────────────────────────
# Main processing
# ──────────────────────────────────────────────
def process_folder(
    folder: Path,
    csv_path: Path,
    logger: logging.Logger,
    export_xlsx: bool = False,
) -> None:
    """Scan *folder* for audio files, extract metadata, and update the CSV."""
    logger.info("OS detected: %s %s", platform.system(), platform.release())
    logger.info("Python version: %s", sys.version.split()[0])
    logger.info("Scanning folder: %s", folder)

    if not folder.is_dir():
        logger.error("Folder does not exist or is not a directory: %s", folder)
        return

    audio_files = find_audio_files(folder)
    logger.info("Found %d audio file(s) with supported extensions", len(audio_files))

    if not audio_files:
        logger.info("Nothing to process — exiting.")
        return

    existing_paths = load_existing_paths(csv_path)
    new_rows: list[dict] = []
    skipped = 0
    duplicates = 0
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for fp in audio_files:
        full_path_str = str(fp.resolve())

        # Duplicate check
        if full_path_str in existing_paths:
            logger.info("Skipping duplicate: %s", fp.name)
            duplicates += 1
            continue

        # Duration extraction
        duration = get_audio_duration(fp)
        if duration is None:
            logger.warning("Could not read audio data — skipped: %s", fp.name)
            skipped += 1
            continue

        row = {
            "Title": fp.stem,
            "Filename": fp.name,
            "Duration_Seconds": round(duration, 2),
            "Duration_Minutes": round(duration / 60, 2),
            "Duration_Formatted": format_duration(duration),
            "Full_File_Path": full_path_str,
            "File_Size_MB": file_size_mb(fp),
            "Date_Processed": now,
        }
        new_rows.append(row)

    # Write results
    if new_rows:
        append_rows(csv_path, new_rows)
        logger.info("Appended %d new row(s) to %s", len(new_rows), csv_path)
    else:
        logger.info("No new files to add.")

    logger.info(
        "Summary — processed: %d, duplicates skipped: %d, errors skipped: %d",
        len(new_rows), duplicates, skipped,
    )

    if export_xlsx:
        if csv_path.exists():
            xlsx = export_to_excel(csv_path)
            logger.info("Excel export written to %s", xlsx)


# ──────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────
def main() -> None:
    logger = setup_logging(LOG_FILE)
    logger.info("=" * 50)
    logger.info("Audio Scanner started")
    process_folder(AUDIO_FOLDER, OUTPUT_CSV, logger, export_xlsx=EXPORT_EXCEL)
    logger.info("Done.\n")


if __name__ == "__main__":
    main()
