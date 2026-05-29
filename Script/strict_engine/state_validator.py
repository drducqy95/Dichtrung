#!/usr/bin/env python3
"""
State Verification Gate — Runs AFTER state update.
Validates the integrity of the project state files (glossary, characters, progress)
to ensure no corruptions or duplicates were introduced during the translation cycle.

Outputs a PASS/FAIL report to runtime/gates/chapter_XXX.statecheck.json.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from utils.io import (  # noqa: E402
    get_logger, load_json, now_iso, save_json_atomic,
    resolve_branch_dir, unique_by_key, get_output_chapter_path
)

LOGGER = get_logger("state_validator")


def run_state_verification(branch_name: str, chapter: int) -> dict[str, Any]:
    """Execute state verification."""
    branch_dir = resolve_branch_dir(branch_name)
    errors: list[str] = []
    warnings: list[str] = []

    # 1. Output file verification
    # We don't have the exact title, so we check by prefix again
    prefix = f"Chương {chapter:04d}"
    output_dir = branch_dir / "output"
    found_output = False
    if output_dir.exists():
        for f in output_dir.iterdir():
            if f.name.startswith(prefix) and f.suffix == ".md":
                found_output = True
                break
    
    if not found_output:
        errors.append(f"Output markdown file for chapter {chapter} was not created.")

    # 2. Glossary integrity
    glossary_path = branch_dir / "glossary.json"
    if glossary_path.exists():
        glossary = load_json(glossary_path)
        if not glossary or "entries" not in glossary:
            errors.append("glossary.json is corrupted or missing 'entries'.")
        else:
            is_unique, dupes = unique_by_key(glossary["entries"], "source")
            if not is_unique:
                errors.append(f"Glossary integrity compromised: duplicate source terms found: {dupes[:5]}")
    
    # 3. Characters integrity
    char_path = branch_dir / "characters.json"
    if char_path.exists():
        characters = load_json(char_path)
        if not characters or "characters" not in characters:
            errors.append("characters.json is corrupted or missing 'characters'.")
        else:
            is_unique, dupes = unique_by_key(characters["characters"], "id")
            if not is_unique:
                 errors.append(f"Characters integrity compromised: duplicate IDs found: {dupes[:5]}")

    # 4. Progress integrity
    progress_path = branch_dir / "progress.json"
    if progress_path.exists():
        progress = load_json(progress_path)
        if not progress or "chapters" not in progress:
             errors.append("progress.json is corrupted or missing 'chapters'.")
        else:
             # Check if this chapter is marked as DONE
             chapter_found = False
             for ch in progress["chapters"]:
                 if ch.get("chapter_number") == chapter:
                     chapter_found = True
                     if ch.get("status") != "DONE":
                         warnings.append(f"Chapter {chapter} is in progress.json but status is not DONE.")
                     break
             if not chapter_found:
                 warnings.append(f"Chapter {chapter} is missing from progress.json 'chapters' array.")

    passed = len(errors) == 0

    return {
        "schema_version": "1.0",
        "branch": branch_name,
        "chapter": chapter,
        "passed": passed,
        "errors": errors,
        "warnings": warnings,
        "generated_at": now_iso()
    }

def write_statecheck_report(branch_name: str, chapter: int, report: dict) -> Path:
    """Write statecheck report to runtime/gates/."""
    branch_dir = resolve_branch_dir(branch_name)
    target = branch_dir / "runtime" / "gates" / f"chapter_{chapter:04d}.statecheck.json"
    save_json_atomic(target, report)
    return target

def main() -> int:
    parser = argparse.ArgumentParser(description="State Verification Gate for Dichtrung translation")
    parser.add_argument("--branch", required=True, help="Project branch name")
    parser.add_argument("--chapter", required=True, type=int, help="Chapter number")
    parser.add_argument("--dry-run", action="store_true", help="Print report to stdout without writing")
    args = parser.parse_args()

    report = run_state_verification(args.branch, args.chapter)

    if args.dry_run:
        import json as _json
        sys.stdout.reconfigure(encoding="utf-8")
        print(_json.dumps(report, ensure_ascii=False, indent=2))
    else:
        target = write_statecheck_report(args.branch, args.chapter, report)
        if report["passed"]:
            LOGGER.info("State Verification PASS: %s", target)
            for warn in report["warnings"]:
                LOGGER.warning(" - %s", warn)
        else:
            LOGGER.error("State Verification FAIL: %s", target)
            for err in report["errors"]:
                LOGGER.error(" - %s", err)
            for warn in report["warnings"]:
                LOGGER.warning(" - %s", warn)

    return 0 if report["passed"] else 1

if __name__ == "__main__":
    sys.exit(main())
