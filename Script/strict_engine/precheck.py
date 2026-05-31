#!/usr/bin/env python3
"""
Precheck Gate — Runs BEFORE translation.
Validates that the project branch is in a healthy state to begin translating a chapter.

Checks:
1. Project config exists and is valid.
2. Source chapter file exists.
3. Output chapter does NOT already exist (prevent overwrite).
4. Context pack exists and is valid.
5. Glossary and character schemas are fundamentally sound.

Outputs a PASS/FAIL report to runtime/gates/chapter_XXX.precheck.json.
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
    get_source_chapter_path, get_output_chapter_path, resolve_branch_dir,
    unique_by_key,
)

LOGGER = get_logger("precheck")


def run_precheck(branch_name: str, chapter: int) -> dict[str, Any]:
    """Execute precheck validations."""
    branch_dir = resolve_branch_dir(branch_name)
    errors: list[str] = []
    warnings: list[str] = []

    # 1. Branch existence
    if not branch_dir.exists():
        return {"passed": False, "errors": [f"Branch directory not found: {branch_dir}"]}

    # 2. Config validation
    config_path = branch_dir / "translation_config.json"
    if not config_path.exists():
        errors.append("translation_config.json is missing.")
    else:
        config = load_json(config_path)
        if not config:
            errors.append("translation_config.json is empty or invalid JSON.")
        elif not config.get("source_language") or not config.get("target_language"):
            errors.append("Config missing source_language or target_language.")

    # 3. Source chapter validation
    source_path = get_source_chapter_path(branch_name, chapter)
    if not source_path or not source_path.exists():
        errors.append(f"Source chapter {chapter} not found.")

    # 4. Output chapter validation (prevent overwrite)
    # Output path might have title, so we just check if any file starts with Chương 0000 -
    prefix = f"Chương {chapter:04d}"
    output_dir = branch_dir / "output"
    if output_dir.exists():
        for f in output_dir.iterdir():
            if f.name.startswith(prefix) and f.suffix == ".md":
                warnings.append(f"Output chapter already exists: {f.name}. Translation will overwrite or update it.")
                # We don't error out because the user might be doing a re-translation

    # 5. Context pack validation
    context_pack_path = branch_dir / "runtime" / "context_packs" / f"chapter_{chapter:04d}.context_pack.json"
    if not context_pack_path.exists():
        errors.append(f"Context pack for chapter {chapter} is missing. Run build_context_pack.py first.")
    else:
        pack = load_json(context_pack_path)
        if not pack or "chapter" not in pack or "dynamic_glossary" not in pack:
            errors.append("Context pack is malformed.")

    # 6. Basic state schema sanity (Glossary and Characters uniqueness)
    glossary_path = branch_dir / "glossary.json"
    if glossary_path.exists():
        glossary = load_json(glossary_path)
        if glossary and "entries" in glossary:
            is_unique, dupes = unique_by_key(glossary["entries"], "source")
            if not is_unique:
                errors.append(f"Glossary contains duplicate source terms: {dupes[:5]}")
    
    char_path = branch_dir / "characters.json"
    if char_path.exists():
        characters = load_json(char_path)
        if characters and "characters" in characters:
            # Check both id and source/name_original
            # For IDs
            is_unique, dupes = unique_by_key(characters["characters"], "id")
            if not is_unique:
                 errors.append(f"Characters contain duplicate IDs: {dupes[:5]}")
            
            # Gold Schema uses name_source; keep legacy fallbacks.
            seen_names = set()
            name_dupes = []
            for c in characters["characters"]:
                 name = str(c.get("name_source") or c.get("source") or c.get("name_original") or "").strip()
                 if name:
                     if name in seen_names:
                         name_dupes.append(name)
                     seen_names.add(name)
            if name_dupes:
                errors.append(f"Characters contain duplicate source names: {name_dupes[:5]}")

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

def write_precheck_report(branch_name: str, chapter: int, report: dict) -> Path:
    """Write precheck report to runtime/gates/."""
    branch_dir = resolve_branch_dir(branch_name)
    target = branch_dir / "runtime" / "gates" / f"chapter_{chapter:04d}.precheck.json"
    save_json_atomic(target, report)
    return target

def main() -> int:
    parser = argparse.ArgumentParser(description="Precheck Gate for Dichtrung translation")
    parser.add_argument("--branch", required=True, help="Project branch name")
    parser.add_argument("--chapter", required=True, type=int, help="Chapter number")
    parser.add_argument("--dry-run", action="store_true", help="Print report to stdout without writing")
    args = parser.parse_args()

    report = run_precheck(args.branch, args.chapter)

    if args.dry_run:
        import json as _json
        sys.stdout.reconfigure(encoding="utf-8")
        print(_json.dumps(report, ensure_ascii=False, indent=2))
    else:
        target = write_precheck_report(args.branch, args.chapter, report)
        if report["passed"]:
            LOGGER.info("Precheck PASS: %s", target)
        else:
            LOGGER.error("Precheck FAIL: %s", target)
            for err in report["errors"]:
                LOGGER.error(" - %s", err)

    return 0 if report["passed"] else 1

if __name__ == "__main__":
    sys.exit(main())
