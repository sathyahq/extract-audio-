#!/usr/bin/env python3
"""
Audio File Scanner — Monthly Report by Date & Address

Double-click setup_and_run.bat to launch.

Expected folder structure:
    Month Folder (e.g. January)/
      2/                            <- day of month
        22 Steeplechase Way .../    <- job address folder
          file1.m4a                 <- audio files
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

# ── Load dependencies ──
try:
    from mutagen import File as MutagenFile
except ImportError:
    sys.exit("Error: 'mutagen' not installed. Run: pip install mutagen")

try:
    import static_ffmpeg
    static_ffmpeg.add_paths()
except ImportError:
    pass

# ── Config ──
OUTPUT_DIR = Path(".")
LOG_FILE = Path("processing_log.txt")

SKIP_EXTENSIONS = {
    ".txt", ".doc", ".docx", ".pdf", ".xls", ".xlsx", ".csv", ".rtf",
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".tif", ".svg", ".ico", ".webp",
    ".zip", ".rar", ".7z", ".tar", ".gz", ".bz2",
    ".exe", ".bat", ".cmd", ".ps1", ".sh", ".msi",
    ".py", ".js", ".html", ".htm", ".css", ".xml", ".json", ".yaml", ".yml",
    ".ini", ".cfg", ".log", ".md", ".db", ".sqlite", ".sql", ".ppt", ".pptx",
}

MONTH_NAMES = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
}


# ── Folder picker popup ──
def ask_for_folder():
    chosen_path = None

    root = tk.Tk()
    root.title("Audio File Scanner")
    root.resizable(False, False)

    w, h = 550, 200
    x = (root.winfo_screenwidth() - w) // 2
    y = (root.winfo_screenheight() - h) // 2
    root.geometry(f"{w}x{h}+{x}+{y}")
    root.attributes("-topmost", True)

    tk.Label(root, text="Audio File Scanner", font=("Arial", 14, "bold")).pack(pady=(15, 5))
    tk.Label(root, text="Paste your month folder path below, or click Browse:").pack()

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

    entry.bind("<Return>", lambda e: on_scan())

    tk.Button(button_frame, text="Browse...", command=on_browse, width=12).pack(side=tk.LEFT, padx=5)
    tk.Button(button_frame, text="Scan", command=on_scan, width=12,
              bg="#4CAF50", fg="white", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)

    root.mainloop()
    return chosen_path


# ── Logging ──
def setup_logging():
    logger = logging.getLogger("audio_scanner")
    logger.setLevel(logging.INFO)
    if logger.handlers:
        return logger
    fmt = logging.Formatter("%(asctime)s  %(levelname)-8s  %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    logger.addHandler(ch)
    return logger


# ── Audio duration readers ──
def is_skip_file(file_path):
    if file_path.name.startswith('.'):
        return True
    return file_path.suffix.lower() in SKIP_EXTENSIONS


def get_duration_mutagen(file_path):
    try:
        audio = MutagenFile(str(file_path))
        if audio is not None and audio.info is not None:
            return audio.info.length
    except Exception:
        pass
    return None


def get_duration_ffprobe(file_path):
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", str(file_path)],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode == 0:
            info = json.loads(result.stdout)
            dur = info.get("format", {}).get("duration")
            if dur is not None:
                return float(dur)
    except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError, ValueError):
        pass
    return None


def get_duration(file_path, logger=None):
    """Try mutagen first, then ffprobe."""
    dur = get_duration_mutagen(file_path)
    if dur is not None:
        return dur
    dur = get_duration_ffprobe(file_path)
    if dur is not None and logger:
        logger.info("    (read via ffprobe: %s)", file_path.name)
    return dur


def fmt_mmss(seconds):
    total = int(round(seconds))
    m, s = divmod(total, 60)
    return f"{m:02d}:{s:02d}"


def to_min_sec(seconds):
    total = int(round(seconds))
    return divmod(total, 60)


# ── Date from folder structure ──
def parse_date(month_folder, day_name):
    month_num = MONTH_NAMES.get(month_folder.name.lower(), datetime.now().month)
    try:
        year = int(month_folder.parent.name)
    except ValueError:
        year = datetime.now().year
    try:
        day = int(day_name)
    except ValueError:
        day = 1
    return f"{day:02d}/{month_num:02d}/{year}"


# ── Scan folder ──
def scan(month_folder, logger):
    results = []

    day_folders = []
    for item in month_folder.iterdir():
        if item.is_dir():
            try:
                day_folders.append((int(item.name), item))
            except ValueError:
                logger.warning("Skipping non-date folder: %s", item.name)
    day_folders.sort()

    if not day_folders:
        logger.info("No date folders found in %s", month_folder)
        return results

    logger.info("Found %d date folder(s)", len(day_folders))

    for day_num, day_path in day_folders:
        date_str = parse_date(month_folder, day_path.name)

        address_folders = sorted(
            [d for d in day_path.iterdir() if d.is_dir()],
            key=lambda x: x.name.lower()
        )

        # Loose files directly in the day folder
        loose = [f for f in day_path.iterdir() if f.is_file() and not is_skip_file(f)]

        if loose:
            total_secs = 0.0
            count = 0
            for fp in sorted(loose, key=lambda x: x.name.lower()):
                dur = get_duration(fp, logger)
                if dur is not None:
                    total_secs += dur
                    count += 1
                    logger.info("    %s  ->  %s", fp.name, fmt_mmss(dur))
            if total_secs > 0:
                results.append({
                    "Date": date_str, "Address": "(files in date folder)",
                    "Secs": total_secs, "Count": count,
                })

        # Address subfolders
        for addr in address_folders:
            files = sorted(
                [f for f in addr.rglob("*") if f.is_file() and not is_skip_file(f)],
                key=lambda x: x.name.lower()
            )
            if not files:
                continue

            logger.info("  Date %s | %s  (%d files)", day_path.name, addr.name, len(files))

            total_secs = 0.0
            count = 0
            for fp in files:
                dur = get_duration(fp, logger)
                if dur is not None:
                    total_secs += dur
                    count += 1
                    logger.info("    %s  ->  %s", fp.name, fmt_mmss(dur))

            if total_secs > 0:
                results.append({
                    "Date": date_str, "Address": addr.name,
                    "Secs": total_secs, "Count": count,
                })

    return results


# ── CSV output ──
def write_csv(path, results, month_folder):
    with path.open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(["Date", "Job Address", "Files", "Minutes", "Seconds"])

        grand_secs = 0.0
        grand_files = 0

        for row in results:
            m, s = to_min_sec(row["Secs"])
            w.writerow([row["Date"], row["Address"], row["Count"], m, s])
            grand_secs += row["Secs"]
            grand_files += row["Count"]

        w.writerow([])
        client = month_folder.parent.parent.name
        month = month_folder.name
        year = month_folder.parent.name
        gm, gs = to_min_sec(grand_secs)
        w.writerow(["", f"** GRAND TOTAL -- {client} -- {month} {year} **", grand_files, gm, gs])


# ── Console report ──
def print_report(results, month_folder):
    if not results:
        print("\n  No audio files found.\n")
        return

    client = month_folder.parent.parent.name
    month = month_folder.name
    year = month_folder.parent.name

    line = "=" * 95
    print(f"\n  {line}")
    print(f"  AUDIO REPORT -- {client} -- {month} {year}")
    print(f"  {line}")
    print(f"  {'DATE':<14} {'JOB ADDRESS':<50} {'FILES':>6} {'MINS':>8} {'SECS':>8}")
    print(f"  {'-' * 95}")

    grand_secs = 0.0
    grand_files = 0

    for row in results:
        addr = row["Address"][:45] + "..." if len(row["Address"]) > 48 else row["Address"]
        m, s = to_min_sec(row["Secs"])
        print(f"  {row['Date']:<14} {addr:<50} {row['Count']:>6} {m:>8} {s:>8}")
        grand_secs += row["Secs"]
        grand_files += row["Count"]

    gm, gs = to_min_sec(grand_secs)
    dates = len(set(r["Date"] for r in results))
    print(f"  {line}")
    print(f"  {'GRAND TOTAL':<14} {len(results)} address(es) across {dates} date(s)"
          f"{'':>12} {grand_files:>6} {gm:>8} {gs:>8}")
    print(f"  {line}\n")


# ── Main ──
def main():
    logger = setup_logging()
    logger.info("=" * 50)
    logger.info("Audio Scanner started")
    logger.info("OS: %s %s", platform.system(), platform.release())
    logger.info("Python: %s", sys.version.split()[0])

    folder_path = ask_for_folder()
    if not folder_path:
        print("\n  No folder selected. Exiting.\n")
        return

    month_folder = Path(folder_path)
    logger.info("Scanning: %s", month_folder)

    results = scan(month_folder, logger)

    if not results:
        print(f"\n  No audio files found in: {month_folder}")
        print("  Expected structure: Month / Day / Address / audio files\n")
        input("  Press Enter to exit...")
        return

    print_report(results, month_folder)

    client = month_folder.parent.parent.name.replace(" ", "_")
    month = month_folder.name
    year = month_folder.parent.name
    csv_path = OUTPUT_DIR / f"audio_report_{client}_{month}_{year}.csv"

    write_csv(csv_path, results, month_folder)
    logger.info("CSV written: %s", csv_path)
    print(f"  CSV saved: {csv_path.resolve()}\n")


if __name__ == "__main__":
    main()
