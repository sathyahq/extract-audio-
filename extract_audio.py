#!/usr/bin/env python3
"""
Audio File Scanner — Monthly Report by Date & Address

Double-click setup_and_run.bat to launch.
A popup window will appear — paste or browse to your month folder.

Expected folder structure:
    Month Folder (e.g. January)/
      2/                            ← day of month
        22 Steeplechase Way .../    ← job address folder
          file1.m4a                 ← audio files
        Flat C, Dolphin House .../
          file3.mp3
      5/
        ...
"""

import csv
import json
import logging
import os
import platform
import subprocess
import sys
import tkinter as tk
from tkinter import filedialog, messagebox
from datetime import datetime
from pathlib import Path

try:
    from mutagen import File as MutagenFile
except ImportError:
    sys.exit("Error: 'mutagen' is not installed. Run: pip install mutagen")

# ──────────────────────────────────────────────
# CONFIGURATION
# ──────────────────────────────────────────────
OUTPUT_DIR = Path(".")
LOG_FILE = Path("processing_log.txt")
SUPPORTED_EXTENSIONS = {".mp3", ".wav", ".m4a", ".flac", ".ogg", ".wma", ".aac"}

# Extensions that are definitely NOT audio — skip these files
SKIP_EXTENSIONS = {
    ".txt", ".doc", ".docx", ".pdf", ".xls", ".xlsx", ".csv", ".rtf",
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".tif", ".svg", ".ico", ".webp",
    ".zip", ".rar", ".7z", ".tar", ".gz", ".bz2",
    ".exe", ".bat", ".cmd", ".ps1", ".sh", ".msi",
    ".py", ".js", ".html", ".htm", ".css", ".xml", ".json", ".yaml", ".yml",
    ".ini", ".cfg", ".log", ".md",
    ".db", ".sqlite", ".sql",
    ".ppt", ".pptx",
}


# ──────────────────────────────────────────────
# Folder picker popup
# ──────────────────────────────────────────────
def ask_for_folder() -> str | None:
    """Show a popup window where user can paste a path or browse for a folder."""
    chosen_path = None

    root = tk.Tk()
    root.title("Audio File Scanner")
    root.resizable(False, False)

    # Center the window on screen
    window_width, window_height = 550, 200
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x = (screen_width - window_width) // 2
    y = (screen_height - window_height) // 2
    root.geometry(f"{window_width}x{window_height}+{x}+{y}")

    # Keep window on top
    root.attributes("-topmost", True)

    tk.Label(root, text="Audio File Scanner", font=("Arial", 14, "bold")).pack(pady=(15, 5))
    tk.Label(root, text="Paste your month folder path below, or click Browse:").pack()

    # Path entry field
    path_var = tk.StringVar()
    entry = tk.Entry(root, textvariable=path_var, width=60, font=("Arial", 10))
    entry.pack(padx=20, pady=8)
    entry.focus_set()

    button_frame = tk.Frame(root)
    button_frame.pack(pady=5)

    def on_browse():
        folder = filedialog.askdirectory(title="Select the MONTH folder (e.g. January)")
        if folder:
            path_var.set(folder)

    def on_scan():
        nonlocal chosen_path
        p = path_var.get().strip().strip('"').strip("'")
        if not p:
            messagebox.showwarning("No path", "Please enter or browse to a folder path.")
            return
        if not os.path.isdir(p):
            messagebox.showerror("Invalid folder", f"Folder not found:\n{p}")
            return
        chosen_path = p
        root.destroy()

    def on_enter(event):
        on_scan()

    entry.bind("<Return>", on_enter)

    tk.Button(button_frame, text="Browse...", command=on_browse, width=12).pack(side=tk.LEFT, padx=5)
    tk.Button(button_frame, text="Scan", command=on_scan, width=12,
              bg="#4CAF50", fg="white", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)

    root.mainloop()
    return chosen_path


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
def is_known_non_audio(file_path: Path) -> bool:
    """Return True for files that are definitely NOT audio (skip these)."""
    ext = file_path.suffix.lower()
    if ext in SKIP_EXTENSIONS:
        return True
    if file_path.name.startswith('.'):
        return True
    return False


def get_duration_ffprobe(file_path: Path) -> float | None:
    """Try to get audio duration using ffprobe (requires ffmpeg installed)."""
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                str(file_path),
            ],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode == 0:
            info = json.loads(result.stdout)
            duration = info.get("format", {}).get("duration")
            if duration is not None:
                return float(duration)
    except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError, ValueError):
        pass
    return None


def get_audio_duration(file_path: Path, logger: logging.Logger = None) -> float | None:
    """Return duration in seconds. Tries mutagen first, then ffprobe as fallback."""
    # Try mutagen first (fast, pure Python)
    try:
        audio = MutagenFile(str(file_path))
        if audio is not None and audio.info is not None:
            return audio.info.length
    except Exception:
        pass

    # Fallback to ffprobe for formats mutagen can't handle
    dur = get_duration_ffprobe(file_path)
    if dur is not None:
        if logger:
            logger.info("    (read via ffprobe: %s)", file_path.name)
        return dur

    return None


def format_duration(seconds: float) -> str:
    """Convert seconds to HH:MM:SS."""
    total = int(round(seconds))
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def format_duration_mmss(seconds: float) -> str:
    """Convert seconds to MM:SS (no hours, minutes can exceed 59)."""
    total = int(round(seconds))
    minutes, secs = divmod(total, 60)
    return f"{minutes:02d}:{secs:02d}"


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
    month_folder = .../2026/January, day_folder_name = "19"
    Returns "19/01/2026"
    """
    month_name = month_folder.name.lower()
    year_str = month_folder.parent.name

    month_num = MONTH_NAMES.get(month_name)
    if month_num is None:
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
    Scan: month_folder / day / address / audio_files
    Returns list of dicts with Date, Address, Duration_Secs, Duration_Str, Files_Count.
    """
    results = []

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

        address_folders = sorted(
            [d for d in day_path.iterdir() if d.is_dir()],
            key=lambda x: x.name.lower()
        )

        # Try ALL files that are not obviously non-audio
        loose_files = [
            f for f in day_path.iterdir()
            if f.is_file() and not is_known_non_audio(f)
        ]

        if not address_folders and not loose_files:
            logger.info("  Date %s: no address folders or audio files found", day_path.name)
            continue

        if loose_files:
            total_secs = 0.0
            file_count = 0
            skipped = []
            for fp in sorted(loose_files, key=lambda x: x.name.lower()):
                dur = get_audio_duration(fp, logger)
                if dur is not None:
                    total_secs += dur
                    file_count += 1
                    logger.info("    %s  →  %s", fp.name, format_duration(dur))
                else:
                    skipped.append(fp.name)

            for name in skipped:
                logger.info("    Skipped (not audio): %s", name)

            if total_secs > 0:
                results.append({
                    "Date": date_str,
                    "Address": "(files in date folder)",
                    "Duration_Secs": total_secs,
                    "Duration_Str": format_duration(total_secs),
                    "Files_Count": file_count,
                })

        for addr_folder in address_folders:
            # Try ALL files recursively, skip only known non-audio
            candidate_files = sorted(
                [f for f in addr_folder.rglob("*")
                 if f.is_file() and not is_known_non_audio(f)],
                key=lambda x: x.name.lower()
            )

            if not candidate_files:
                continue

            logger.info("  Date %s | %s  (%d candidate files)", day_path.name, addr_folder.name, len(candidate_files))

            total_secs = 0.0
            file_count = 0
            skipped = []
            for fp in candidate_files:
                dur = get_audio_duration(fp, logger)
                if dur is not None:
                    total_secs += dur
                    file_count += 1
                    logger.info("    %s  →  %s", fp.name, format_duration(dur))
                else:
                    skipped.append(fp.name)

            for name in skipped:
                logger.info("    Skipped (not audio): %s", name)

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
def secs_to_min_sec(seconds: float) -> tuple[int, int]:
    """Convert seconds to (minutes, seconds) tuple."""
    total = int(round(seconds))
    mins, secs = divmod(total, 60)
    return mins, secs


def write_report_csv(output_path: Path, results: list[dict], month_folder: Path):
    """Write the report CSV with a grand total."""
    with output_path.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.writer(fh)
        writer.writerow(["Date", "Job Address", "Files", "Minutes", "Seconds"])

        grand_secs = 0.0
        grand_files = 0

        for row in results:
            mins, secs = secs_to_min_sec(row["Duration_Secs"])
            writer.writerow([
                row["Date"],
                row["Address"],
                row["Files_Count"],
                mins,
                secs,
            ])
            grand_secs += row["Duration_Secs"]
            grand_files += row["Files_Count"]

        # Grand total
        writer.writerow([])
        client_name = month_folder.parent.parent.name
        month_name = month_folder.name
        year = month_folder.parent.name
        grand_mins, grand_s = secs_to_min_sec(grand_secs)
        writer.writerow([
            "",
            f"** GRAND TOTAL -- {client_name} -- {month_name} {year} **",
            grand_files,
            grand_mins,
            grand_s,
        ])


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

    sep = "-" * 95
    thick_sep = "=" * 95

    print(f"\n  {thick_sep}")
    print(f"  AUDIO REPORT -- {client_name} -- {month_name} {year}")
    print(f"  {thick_sep}")
    print(f"  {'DATE':<14} {'JOB ADDRESS':<50} {'FILES':>6} {'MINS':>8} {'SECS':>8}")
    print(f"  {sep}")

    grand_secs = 0.0
    grand_files = 0
    total_addresses = 0

    for row in results:
        addr_display = row["Address"]
        if len(addr_display) > 48:
            addr_display = addr_display[:45] + "..."

        mins, secs = secs_to_min_sec(row["Duration_Secs"])
        print(f"  {row['Date']:<14} {addr_display:<50} {row['Files_Count']:>6} {mins:>8} {secs:>8}")
        grand_secs += row["Duration_Secs"]
        grand_files += row["Files_Count"]
        total_addresses += 1

    grand_mins, grand_s = secs_to_min_sec(grand_secs)
    print(f"  {thick_sep}")
    print(f"  {'GRAND TOTAL':<14} {total_addresses} address(es) across {len(set(r['Date'] for r in results))} date(s)"
          f"{'':>12} {grand_files:>6} {grand_mins:>8} {grand_s:>8}")
    print(f"  {thick_sep}\n")


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────
def check_ffprobe() -> bool:
    """Check if ffprobe (ffmpeg) is available on the system."""
    try:
        subprocess.run(["ffprobe", "-version"], capture_output=True, timeout=5)
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def main():
    logger = setup_logging(LOG_FILE)
    logger.info("=" * 50)
    logger.info("Audio Scanner started")
    logger.info("OS: %s %s", platform.system(), platform.release())
    logger.info("Python: %s", sys.version.split()[0])

    has_ffprobe = check_ffprobe()
    if has_ffprobe:
        logger.info("ffprobe: available (can read all audio formats)")
    else:
        logger.warning("ffprobe: NOT found. Some audio files (e.g. Express Scribe, dictation) may not be readable.")
        logger.warning("Install ffmpeg from https://ffmpeg.org/download.html to fix this.")

    # Show popup to get folder path
    folder_path = ask_for_folder()

    if not folder_path:
        print("\n  No folder selected. Exiting.\n")
        return

    month_folder = Path(folder_path)

    logger.info("Scanning month folder: %s", month_folder)

    results = scan_month_folder(month_folder, logger)

    if not results:
        print(f"\n  No audio files found in: {month_folder}")
        print("  Make sure the folder structure is: Month / Date / Address / audio files\n")
        input("  Press Enter to exit...")
        return

    # Print to console
    print_report(results, month_folder)

    # Write CSV next to the script
    client_name = month_folder.parent.parent.name.replace(" ", "_")
    month_name = month_folder.name
    year = month_folder.parent.name
    csv_filename = f"audio_report_{client_name}_{month_name}_{year}.csv"
    csv_path = OUTPUT_DIR / csv_filename

    write_report_csv(csv_path, results, month_folder)
    logger.info("CSV written: %s", csv_path)
    print(f"  CSV saved: {csv_path.resolve()}\n")


if __name__ == "__main__":
    main()
