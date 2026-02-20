#!/usr/bin/env python3
"""
Audio File Scanner — Monthly Report by Date & Address

Scans a MONTH folder with this structure:

    Month Folder (e.g. January)/
      2/                            ← day of month
        22 Steeplechase Way .../    ← job address folder
          file1.m4a                 ← audio files
          file2.m4a
        Flat C, Dolphin House .../  ← another address
          file3.mp3
      5/                            ← another day
        ...

Outputs:
  - A CSV and on-screen table with totals per date per address
  - Date totals and a grand total for the whole month
"""

import csv
import logging
import platform
import sys
from datetime import datetime
from pathlib import Path

try:
    from mutagen import File as MutagenFile
except ImportError:
    sys.exit("Error: 'mutagen' is not installed. Run: pip install mutagen")

# ──────────────────────────────────────────────
# CONFIGURATION — edit this path to your month folder
# ──────────────────────────────────────────────
AUDIO_FOLDER = Path(r"F:\AURASKY DATA\Clients\NLG - Midchesire\2026\February")
#                    ↑ Change this to your month folder path

OUTPUT_DIR = Path(".")
LOG_FILE = Path("processing_log.txt")
EXPORT_EXCEL = False  # set True to also produce .xlsx

SUPPORTED_EXTENSIONS = {".mp3", ".wav", ".m4a", ".flac", ".ogg", ".wma", ".aac"}


# ──────────────────────────────────────────────
# Logging
# ──────────────────────────────────────────────
def setup_logging(log_path: Path) -> logging.Logger:
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
    """Convert seconds to HH:MM:SS."""
    total = int(round(seconds))
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def duration_to_secs(d: str) -> int:
    """Parse HH:MM:SS or MM:SS back to total seconds."""
    parts = d.split(":")
    if len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    return int(parts[0]) * 60 + int(parts[1])


# ──────────────────────────────────────────────
# Derive date from folder structure
# ──────────────────────────────────────────────
MONTH_NAMES = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
}


def parse_date_from_path(month_folder: Path, day_folder_name: str) -> str:
    """
    Build a date string from the folder structure.

    month_folder = .../2026/January
    day_folder_name = "19"

    Returns "19/01/2026"
    """
    month_name = month_folder.name.lower()
    year_str = month_folder.parent.name

    month_num = MONTH_NAMES.get(month_name)
    if month_num is None:
        # fallback: use current month
        month_num = datetime.now().month

    try:
        year = int(year_str)
    except ValueError:
        year = datetime.now().year

    try:
        day = int(day_folder_name)
    except ValueError:
        day = 1

    return f"{day:02d}/{month_num:02d}/{year}"


# ──────────────────────────────────────────────
# Discover and process
# ──────────────────────────────────────────────
def scan_month_folder(month_folder: Path, logger: logging.Logger):
    """
    Scan the month folder structure:
      month_folder / day / address / audio_files

    Returns a list of dicts:
      [ {Date, Address, Duration_Secs, Duration_Str, Files_Count}, ... ]
    """
    results = []

    # Get all day subfolders, sorted numerically
    day_folders = []
    for item in month_folder.iterdir():
        if item.is_dir():
            try:
                day_num = int(item.name)
                day_folders.append((day_num, item))
            except ValueError:
                logger.warning("Skipping non-date folder: %s", item.name)
    day_folders.sort(key=lambda x: x[0])

    if not day_folders:
        logger.info("No date folders found in %s", month_folder)
        return results

    logger.info("Found %d date folder(s)", len(day_folders))

    for day_num, day_path in day_folders:
        date_str = parse_date_from_path(month_folder, day_path.name)

        # Each subfolder inside the day folder = a job address
        address_folders = sorted(
            [d for d in day_path.iterdir() if d.is_dir()],
            key=lambda x: x.name.lower()
        )

        # Also check for audio files directly in the day folder (no address subfolder)
        loose_files = [
            f for f in day_path.iterdir()
            if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
        ]

        if not address_folders and not loose_files:
            logger.info("  Date %s: no address folders or audio files found", day_path.name)
            continue

        # Process loose files under a generic name
        if loose_files:
            total_secs = 0.0
            file_count = 0
            for fp in sorted(loose_files, key=lambda x: x.name.lower()):
                dur = get_audio_duration(fp)
                if dur is not None:
                    total_secs += dur
                    file_count += 1
                    logger.info("    %s  →  %s", fp.name, format_duration(dur))
                else:
                    logger.warning("    Unreadable: %s", fp.name)

            if total_secs > 0:
                results.append({
                    "Date": date_str,
                    "Address": "(files in date folder)",
                    "Duration_Secs": total_secs,
                    "Duration_Str": format_duration(total_secs),
                    "Files_Count": file_count,
                })

        # Process each address folder
        for addr_folder in address_folders:
            audio_files = sorted(
                [f for f in addr_folder.rglob("*")
                 if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS],
                key=lambda x: x.name.lower()
            )

            if not audio_files:
                continue

            logger.info("  Date %s | %s  (%d files)", day_path.name, addr_folder.name, len(audio_files))

            total_secs = 0.0
            file_count = 0
            for fp in audio_files:
                dur = get_audio_duration(fp)
                if dur is not None:
                    total_secs += dur
                    file_count += 1
                    logger.info("    %s  →  %s", fp.name, format_duration(dur))
                else:
                    logger.warning("    Unreadable: %s", fp.name)

            if total_secs > 0:
                results.append({
                    "Date": date_str,
                    "Address": addr_folder.name,
                    "Duration_Secs": total_secs,
                    "Duration_Str": format_duration(total_secs),
                    "Files_Count": file_count,
                })

    return results


# ──────────────────────────────────────────────
# CSV output
# ──────────────────────────────────────────────
def write_report_csv(output_path: Path, results: list[dict], month_folder: Path):
    """Write the report CSV with a grand total."""
    with output_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["Date", "Job Address", "Files", "Total Duration"])

        grand_secs = 0.0
        grand_files = 0

        for row in results:
            writer.writerow([
                row["Date"],
                row["Address"],
                row["Files_Count"],
                row["Duration_Str"],
            ])
            grand_secs += row["Duration_Secs"]
            grand_files += row["Files_Count"]

        # Grand total
        writer.writerow([])
        client_name = month_folder.parent.parent.name
        month_name = month_folder.name
        year = month_folder.parent.name
        writer.writerow([
            "",
            f"** GRAND TOTAL — {client_name} — {month_name} {year} **",
            grand_files,
            format_duration(grand_secs),
        ])


def write_report_excel(output_path: Path, results: list[dict], month_folder: Path):
    """Write the report as an Excel file."""
    try:
        import pandas as pd
    except ImportError:
        return None

    rows_for_df = []
    grand_secs = 0.0

    for row in results:
        rows_for_df.append({
            "Date": row["Date"],
            "Job Address": row["Address"],
            "Files": row["Files_Count"],
            "Total Duration": row["Duration_Str"],
        })
        grand_secs += row["Duration_Secs"]

    client_name = month_folder.parent.parent.name
    month_name = month_folder.name
    year = month_folder.parent.name
    rows_for_df.append({"Date": "", "Job Address": "", "Files": "", "Total Duration": ""})
    rows_for_df.append({
        "Date": "",
        "Job Address": f"GRAND TOTAL — {client_name} — {month_name} {year}",
        "Files": "",
        "Total Duration": format_duration(grand_secs),
    })

    df = pd.DataFrame(rows_for_df)
    xlsx_path = output_path.with_suffix(".xlsx")
    try:
        df.to_excel(xlsx_path, index=False)
        return xlsx_path
    except ImportError:
        return None


# ──────────────────────────────────────────────
# Console report
# ──────────────────────────────────────────────
def print_report(results: list[dict], month_folder: Path):
    """Print a clean summary table to the console."""
    if not results:
        print("\n  No audio files found.\n")
        return

    client_name = month_folder.parent.parent.name
    month_name = month_folder.name
    year = month_folder.parent.name

    sep = "─" * 90
    thick_sep = "═" * 90

    print(f"\n  {thick_sep}")
    print(f"  AUDIO REPORT — {client_name} — {month_name} {year}")
    print(f"  {thick_sep}")
    print(f"  {'DATE':<14} {'JOB ADDRESS':<50} {'FILES':>6} {'DURATION':>12}")
    print(f"  {sep}")

    grand_secs = 0.0
    grand_files = 0
    total_addresses = 0

    for row in results:
        # Truncate long address names for display
        addr_display = row["Address"]
        if len(addr_display) > 48:
            addr_display = addr_display[:45] + "..."

        print(f"  {row['Date']:<14} {addr_display:<50} {row['Files_Count']:>6} {row['Duration_Str']:>12}")
        grand_secs += row["Duration_Secs"]
        grand_files += row["Files_Count"]
        total_addresses += 1

    print(f"  {thick_sep}")
    print(f"  {'GRAND TOTAL':<14} {total_addresses} address(es) across {len(set(r['Date'] for r in results))} date(s)"
          f"{'':>12} {grand_files:>6} {format_duration(grand_secs):>12}")
    print(f"  {thick_sep}\n")


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────
def main():
    logger = setup_logging(LOG_FILE)
    logger.info("=" * 50)
    logger.info("Audio Scanner started")
    logger.info("OS: %s %s", platform.system(), platform.release())
    logger.info("Python: %s", sys.version.split()[0])

    month_folder = AUDIO_FOLDER

    if not month_folder.is_dir():
        logger.error("Folder does not exist: %s", month_folder)
        print(f"\n  [ERROR] Folder not found: {month_folder}")
        print("  Please edit line 39 in extract_audio.py to set the correct path.\n")
        input("  Press Enter to exit...")
        return

    logger.info("Scanning month folder: %s", month_folder)

    results = scan_month_folder(month_folder, logger)

    if not results:
        print(f"\n  No audio files found in: {month_folder}")
        print("  Make sure the folder structure is: Month / Date / Address / audio files\n")
        input("  Press Enter to exit...")
        return

    # Print to console
    print_report(results, month_folder)

    # Write CSV
    client_name = month_folder.parent.parent.name.replace(" ", "_")
    month_name = month_folder.name
    year = month_folder.parent.name
    csv_filename = f"audio_report_{client_name}_{month_name}_{year}.csv"
    csv_path = OUTPUT_DIR / csv_filename

    write_report_csv(csv_path, results, month_folder)
    logger.info("CSV written: %s", csv_path)
    print(f"  CSV saved: {csv_path.resolve()}")

    # Write Excel if enabled
    if EXPORT_EXCEL:
        xlsx_path = write_report_excel(csv_path, results, month_folder)
        if xlsx_path:
            logger.info("Excel written: %s", xlsx_path)
            print(f"  Excel saved: {xlsx_path.resolve()}")

    logger.info("Done.\n")


if __name__ == "__main__":
    main()
