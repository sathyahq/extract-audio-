#!/usr/bin/env python3
"""
Audio File Scanner — Total duration per Job Address

Scans a root folder containing subfolders (one per job address).
Each subfolder holds audio files (.mp3, .wav, .m4a, .flac).

Outputs:
  - audio_index.csv       3-column table: Date_Received | Job_Address | Total_Duration
  - processing_log.txt    timestamped run log
  - (optional) audio_index.xlsx
"""

import csv
import logging
import platform
import sys
from collections import defaultdict
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
AUDIO_FOLDER = Path.home() / "Music"  # <-- root folder containing job-address subfolders
OUTPUT_CSV = Path("audio_index.csv")
LOG_FILE = Path("processing_log.txt")
EXPORT_EXCEL = False  # set True to also produce .xlsx

SUPPORTED_EXTENSIONS = {".mp3", ".wav", ".m4a", ".flac"}

CSV_COLUMNS = [
    "Date_Received",
    "Job_Address",
    "Total_Duration",
]


# ──────────────────────────────────────────────
# Logging
# ──────────────────────────────────────────────
def setup_logging(log_path: Path) -> logging.Logger:
    """Configure a logger that writes to both console and a log file."""
    logger = logging.getLogger("audio_scanner")
    logger.setLevel(logging.INFO)
    if logger.handlers:
        return logger

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
    """Return duration in seconds using mutagen, or None on failure."""
    try:
        audio = MutagenFile(str(file_path))
        if audio is None or audio.info is None:
            return None
        return audio.info.length
    except Exception:
        return None


def format_duration(seconds: float) -> str:
    """Convert seconds → MM:SS (or HH:MM:SS if >= 1 hour)."""
    total = int(round(seconds))
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def get_folder_date(folder: Path) -> str:
    """
    Get the date the job folder was received.
    Uses the folder's creation time (or earliest modification time).
    """
    stat = folder.stat()
    # st_birthtime exists on macOS; fall back to st_mtime elsewhere
    timestamp = getattr(stat, "st_birthtime", None) or stat.st_mtime
    return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d")


# ──────────────────────────────────────────────
# File discovery
# ──────────────────────────────────────────────
def discover_jobs(root: Path) -> dict[str, list[Path]]:
    """
    Walk *root* and group audio files by job address.

    Structure expected:
        root/
          Job Address A/
            file1.m4a
            file2.m4a
          Job Address B/
            file3.mp3

    If audio files sit directly in *root* (no subfolders), they are
    grouped under a single job called the root folder name.
    """
    jobs: dict[str, list[Path]] = defaultdict(list)

    # Files directly in the root folder
    for p in sorted(root.iterdir(), key=lambda x: x.name.lower()):
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS:
            jobs[root.name].append(p)

    # Subfolders = job addresses
    for subfolder in sorted(root.iterdir(), key=lambda x: x.name.lower()):
        if not subfolder.is_dir():
            continue
        files = sorted(
            [f for f in subfolder.rglob("*")
             if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS],
            key=lambda x: x.name.lower(),
        )
        if files:
            jobs[subfolder.name] = files

    return dict(jobs)


# ──────────────────────────────────────────────
# CSV helpers
# ──────────────────────────────────────────────
def load_existing_jobs(csv_path: Path) -> set[str]:
    """Return Job_Address values already in the CSV."""
    addresses: set[str] = set()
    if not csv_path.exists():
        return addresses
    with csv_path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            val = row.get("Job_Address", "")
            if val and val != "** GRAND TOTAL **":
                addresses.add(val)
    return addresses


def write_csv(csv_path: Path, rows: list[dict]) -> None:
    """Write (overwrite) a CSV with the 3-column layout + grand total."""
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def read_existing_rows(csv_path: Path) -> list[dict]:
    """Read all non-total rows from the existing CSV."""
    rows: list[dict] = []
    if not csv_path.exists():
        return rows
    with csv_path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            if row.get("Job_Address") != "** GRAND TOTAL **":
                rows.append(row)
    return rows


# ──────────────────────────────────────────────
# Excel export
# ──────────────────────────────────────────────
def export_to_excel(csv_path: Path) -> Path:
    """Read the CSV and write an .xlsx copy next to it."""
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
# Console report
# ──────────────────────────────────────────────
def print_report(rows: list[dict], grand_total_secs: float) -> None:
    """Print a clean summary table to the console."""
    sep = "─" * 64
    print(f"\n{sep}")
    print(f"{'DATE':<14} {'JOB ADDRESS':<34} {'TOTAL DURATION':>14}")
    print(sep)
    for r in rows:
        print(f"{r['Date_Received']:<14} {r['Job_Address']:<34} {r['Total_Duration']:>14}")
    print(sep)
    print(f"{'':<14} {'GRAND TOTAL':<34} {format_duration(grand_total_secs):>14}")
    print(f"{sep}\n")


# ──────────────────────────────────────────────
# Main processing
# ──────────────────────────────────────────────
def process_folder(
    root: Path,
    csv_path: Path,
    logger: logging.Logger,
    export_xlsx: bool = False,
) -> None:
    """Scan *root* for job-address subfolders, sum durations, write CSV."""
    logger.info("OS detected: %s %s", platform.system(), platform.release())
    logger.info("Python version: %s", sys.version.split()[0])
    logger.info("Scanning root folder: %s", root)

    if not root.is_dir():
        logger.error("Folder does not exist: %s", root)
        return

    jobs = discover_jobs(root)
    if not jobs:
        logger.info("No audio files found — exiting.")
        return

    logger.info("Found %d job address(es)", len(jobs))

    # Load existing data so we can append without duplicates
    existing_rows = read_existing_rows(csv_path)
    existing_job_names = {r["Job_Address"] for r in existing_rows}

    new_rows: list[dict] = []
    grand_total_secs = 0.0
    total_skipped = 0

    for job_address, files in jobs.items():
        if job_address in existing_job_names:
            logger.info("Job already in CSV, skipping: %s", job_address)
            continue

        logger.info("Processing job: %s  (%d audio files)", job_address, len(files))
        job_secs = 0.0

        # Determine the job folder for date detection
        if files:
            job_folder = files[0].parent
        else:
            job_folder = root

        for fp in files:
            duration = get_audio_duration(fp)
            if duration is None:
                logger.warning("  Unreadable — skipped: %s", fp.name)
                total_skipped += 1
                continue
            job_secs += duration
            logger.info("  %s  →  %s", fp.name, format_duration(duration))

        if job_secs > 0:
            row = {
                "Date_Received": get_folder_date(job_folder),
                "Job_Address": job_address,
                "Total_Duration": format_duration(job_secs),
            }
            new_rows.append(row)
            grand_total_secs += job_secs

    # Merge old + new rows, recalculate grand total
    all_rows = existing_rows + new_rows

    # Recalculate grand total from ALL rows (old + new)
    def duration_to_secs(d: str) -> int:
        parts = d.split(":")
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        return int(parts[0]) * 60 + int(parts[1])

    total_secs = sum(duration_to_secs(r["Total_Duration"]) for r in all_rows)

    # Grand total row
    grand_row = {
        "Date_Received": "",
        "Job_Address": "** GRAND TOTAL **",
        "Total_Duration": format_duration(total_secs),
    }

    write_csv(csv_path, all_rows + [grand_row])
    logger.info("CSV written to %s  (%d job(s), %d new)", csv_path, len(all_rows), len(new_rows))

    if total_skipped:
        logger.warning("Skipped %d unreadable file(s) — see log for details", total_skipped)

    # Console report
    if all_rows:
        print_report(all_rows, total_secs)

    # Optional Excel export
    if export_xlsx and csv_path.exists():
        logger.info("Excel export → %s", export_to_excel(csv_path))


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
