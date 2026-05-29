"""
Backfill progress.json with chapters present in output/ but missing from the chapters list.
Usage: python Script/backfill_progress.py --branch "Linh Hon Negary_Hu Minh"
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "Output"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def now_iso() -> str:
    return datetime.now().astimezone().replace(microsecond=0).isoformat()


def scan_output_chapters(branch_dir: Path) -> dict[int, str]:
    """Scan output/*.md files and return {chapter_num: title}."""
    out_dir = branch_dir / "output"
    result: dict[int, str] = {}
    if not out_dir.exists():
        return result
    pattern = re.compile(r"Ch.*ng\s+(\d{4})\s+-\s+(.+)\.md", re.IGNORECASE)
    for f in sorted(out_dir.iterdir()):
        if not f.is_file() or f.suffix.lower() != ".md":
            continue
        m = pattern.match(f.name)
        if m:
            num = int(m.group(1))
            title = m.group(2).strip()
            result[num] = title
    return result


def backfill(branch_name: str, dry_run: bool = False) -> None:
    branch_dir = OUTPUT_ROOT / branch_name
    progress_path = branch_dir / "progress.json"

    if not progress_path.exists():
        print(f"[ERROR] progress.json not found: {progress_path}")
        return

    with progress_path.open("r", encoding="utf-8-sig") as fh:
        progress = json.load(fh)

    chapters: list[dict] = progress.get("chapters", [])
    existing_nums = {c["chapter_number"] for c in chapters if isinstance(c.get("chapter_number"), int)}

    output_chapters = scan_output_chapters(branch_dir)
    missing = {num: title for num, title in output_chapters.items() if num not in existing_nums}

    if not missing:
        print("[OK] No missing chapters found — progress.json is already complete.")
        return

    print(f"Found {len(missing)} chapters in output/ but missing from progress.json:")
    for num in sorted(missing):
        print(f"  Ch {num:04d}: {missing[num]}")

    if dry_run:
        print("\n[DRY RUN] No changes written.")
        return

    # Add missing entries as DONE
    for num, title in missing.items():
        chapters.append({
            "chapter_number": num,
            "title": title,
            "status": "DONE",
            "last_updated": now_iso(),
            "note": "backfilled from output scan"
        })

    # Sort and recount
    chapters.sort(key=lambda c: c.get("chapter_number", 0))
    progress["chapters"] = chapters

    done_count = sum(1 for c in chapters if c.get("status") == "DONE")
    progress["completed_chapters"] = done_count
    progress["last_updated"] = now_iso()

    with progress_path.open("w", encoding="utf-8") as fh:
        json.dump(progress, fh, ensure_ascii=False, indent=2)
        fh.write("\n")

    print(f"\n[OK] Backfilled {len(missing)} chapters.")
    print(f"     completed_chapters updated: {done_count}/{progress.get('total_chapters', '?')}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill progress.json with output-based chapters.")
    parser.add_argument("--branch", required=True, help="Branch name under Output/")
    parser.add_argument("--dry-run", action="store_true", help="Only print, do not write")
    args = parser.parse_args()
    backfill(args.branch, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
