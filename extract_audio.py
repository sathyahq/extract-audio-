#!/usr/bin/env python3
"""
Audio File Scanner — Total duration per Job Address (month-wise)

Scans a root folder containing subfolders (one per job address).
Each subfolder holds audio files (.mp3, .wav, .m4a, .flac).

Creates a separate CSV for each month automatically:
  - audio_index_2026-01.csv
  - audio_index_2026-02.csv
  - ...

Also outputs:
  - processing_log.txt    timestamped run log
  - (optional) .xlsx versions of each monthly CSV
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
OUTPUT_DIR = Path(".")                # <-- folder where monthly CSVs are saved
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


def get_folder_date(folder: Path) -> tuple[str, str]:
    """
    Get the date the job folder was received.
    Uses the folder's creation time (or earliest modification time).

    Returns (date_str, month_key):
        date_str  = "2026-02-16"
        month_key = "2026-02"
    """
    stat = folder.stat()
    # st_birthtime exists on macOS; fall back to st_mtime elsewhere
    timestamp = getattr(stat, "st_birthtime", None) or stat.st_mtime
    dt = datetime.fromtimestamp(timestamp)
    return dt.strftime("%Y-%m-%d"), dt.strftime("%Y-%m")


def monthly_csv_path(output_dir: Path, month_key: str) -> Path:
    """Return the CSV path for a given month, e.g. audio_index_2026-02.csv"""
    return output_dir / f"audio_index_{month_key}.csv"


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
# Duration parsing
# ──────────────────────────────────────────────
def duration_to_secs(d: str) -> int:
    """Parse MM:SS or HH:MM:SS back to total seconds."""
    parts = d.split(":")
    if len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    return int(parts[0]) * 60 + int(parts[1])


# ──────────────────────────────────────────────
# Console report
# ──────────────────────────────────────────────
def print_month_report(month: str, rows: list[dict], total_secs: float) -> None:
    """Print a clean summary table for one month."""
    sep = "─" * 64
    print(f"\n  Month: {month}")
    print(f"  {sep}")
    print(f"  {'DATE':<14} {'JOB ADDRESS':<34} {'TOTAL DURATION':>14}")
    print(f"  {sep}")
    for r in rows:
        print(f"  {r['Date_Received']:<14} {r['Job_Address']:<34} {r['Total_Duration']:>14}")
    print(f"  {sep}")
    print(f"  {'':<14} {'MONTH TOTAL':<34} {format_duration(total_secs):>14}")
    print(f"  {sep}")


def print_grand_total(all_months: dict[str, list[dict]]) -> None:
    """Print the grand total across all months."""
    total_jobs = sum(len(rows) for rows in all_months.values())
    total_secs = 0
    for rows in all_months.values():
        total_secs += sum(duration_to_secs(r["Total_Duration"]) for r in rows)
    sep = "═" * 64
    print(f"\n  {sep}")
    print(f"  {'GRAND TOTAL':<48} {total_jobs} job(s)   {format_duration(total_secs)}")
    print(f"  {sep}\n")


# ──────────────────────────────────────────────
# Main processing
# ──────────────────────────────────────────────
def process_folder(
    root: Path,
    output_dir: Path,
    logger: logging.Logger,
    export_xlsx: bool = False,
) -> None:
    """Scan *root* for job-address subfolders, sum durations, write monthly CSVs."""
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

    # Collect all existing job names across all monthly CSVs to detect duplicates
    all_existing_jobs: set[str] = set()
    for csv_file in output_dir.glob("audio_index_*.csv"):
        all_existing_jobs.update(load_existing_jobs(csv_file))

    # Process each job and bucket by month
    new_by_month: dict[str, list[dict]] = defaultdict(list)
    total_new = 0
    total_skipped = 0

    for job_address, files in jobs.items():
        if job_address in all_existing_jobs:
            logger.info("Job already in a CSV, skipping: %s", job_address)
            continue

        logger.info("Processing job: %s  (%d audio files)", job_address, len(files))
        job_secs = 0.0

        # Determine the job folder for date detection
        job_folder = files[0].parent if files else root

        for fp in files:
            duration = get_audio_duration(fp)
            if duration is None:
                logger.warning("  Unreadable — skipped: %s", fp.name)
                total_skipped += 1
                continue
            job_secs += duration
            logger.info("  %s  →  %s", fp.name, format_duration(duration))

        if job_secs > 0:
            date_str, month_key = get_folder_date(job_folder)
            row = {
                "Date_Received": date_str,
                "Job_Address": job_address,
                "Total_Duration": format_duration(job_secs),
            }
            new_by_month[month_key].append(row)
            total_new += 1

    # Write each month's CSV (merge with existing rows)
    all_months_combined: dict[str, list[dict]] = defaultdict(list)

    for month_key, new_rows in sorted(new_by_month.items()):
        csv_path = monthly_csv_path(output_dir, month_key)
        existing_rows = read_existing_rows(csv_path)
        merged = existing_rows + new_rows

        # Month total row
        month_secs = sum(duration_to_secs(r["Total_Duration"]) for r in merged)
        total_row = {
            "Date_Received": "",
            "Job_Address": f"** TOTAL {month_key} **",
            "Total_Duration": format_duration(month_secs),
        }

        write_csv(csv_path, merged + [total_row])
        logger.info("CSV written: %s  (%d jobs, %d new)", csv_path.name, len(merged), len(new_rows))
        all_months_combined[month_key] = merged

        if export_xlsx:
            logger.info("Excel export → %s", export_to_excel(csv_path))

    # Also include months with no new rows (for console report)
    for csv_file in sorted(output_dir.glob("audio_index_*.csv")):
        month_key = csv_file.stem.replace("audio_index_", "")
        if month_key not in all_months_combined:
            rows = read_existing_rows(csv_file)
            if rows:
                all_months_combined[month_key] = rows

    if total_skipped:
        logger.warning("Skipped %d unreadable file(s) — see log for details", total_skipped)

    # Console report
    if all_months_combined:
        for month_key in sorted(all_months_combined):
            rows = all_months_combined[month_key]
            month_secs = sum(duration_to_secs(r["Total_Duration"]) for r in rows)
            print_month_report(month_key, rows, month_secs)
        print_grand_total(all_months_combined)

    logger.info("Run complete — new: %d, skipped: %d", total_new, total_skipped)


# ──────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────
def main() -> None:
    logger = setup_logging(LOG_FILE)
    logger.info("=" * 50)
    logger.info("Audio Scanner started")
    process_folder(AUDIO_FOLDER, OUTPUT_DIR, logger, export_xlsx=EXPORT_EXCEL)
    logger.info("Done.\n")


if __name__ == "__main__":
    main()
