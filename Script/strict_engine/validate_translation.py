#!/usr/bin/env python3
"""
Postcheck Gate — Runs AFTER translation.
Validates the AI's translation output against schema, formatting rules,
and translation constraints (e.g., CJK ban, locked term enforcement).

Outputs a PASS/FAIL report to runtime/gates/chapter_XXX.postcheck.json.
"""
from __future__ import annotations

import argparse
import sys
import re
from pathlib import Path
from typing import Any

import jsonschema

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from utils.io import (  # noqa: E402
    get_logger, load_json, now_iso, save_json_atomic,
    resolve_branch_dir,
)

LOGGER = get_logger("validate_translation")


def is_cjk(ch: str) -> bool:
    """Check if a character is in any CJK Ideograph range (Unified, Ext-A/B, Compat, Radicals)."""
    cp = ord(ch)
    return (
        0x4E00 <= cp <= 0x9FFF        # CJK Unified Ideographs
        or 0x3400 <= cp <= 0x4DBF     # CJK Extension A
        or 0x20000 <= cp <= 0x2A6DF   # CJK Extension B
        or 0xF900 <= cp <= 0xFAFF     # CJK Compatibility Ideographs
        or 0x2E80 <= cp <= 0x2EFF     # CJK Radicals Supplement
        or 0x2F00 <= cp <= 0x2FDF     # Kangxi Radicals
    )


def run_validation(branch_name: str, chapter: int) -> dict[str, Any]:
    """Execute postcheck validations on the translation result."""
    branch_dir = resolve_branch_dir(branch_name)
    errors: list[str] = []
    warnings: list[str] = []

    # 1. Check if files exist
    result_path = branch_dir / "runtime" / f"chapter_{chapter:04d}.translation_result.json"
    if not result_path.exists():
        return {"passed": False, "errors": [f"Translation result not found: {result_path}"]}
    
    result = load_json(result_path)
    if not result:
        return {"passed": False, "errors": ["Translation result is empty or invalid JSON."]}

    # 2. Schema Validation
    schema_path = ROOT / "schemas" / "translation_result.schema.json"
    if schema_path.exists():
        schema = load_json(schema_path)
        try:
            jsonschema.validate(instance=result, schema=schema)
        except jsonschema.ValidationError as e:
            errors.append(f"Schema validation failed: {e.message} at path {list(e.path)}")
    else:
        warnings.append("Schema file not found. Skipping strict schema validation.")

    # 3. Refusal check
    refusal = result.get("refusal")
    if refusal:
        errors.append(f"AI refused to translate: {refusal}")

    if errors:
        # If schema fails or refusal, stop here to avoid KeyError on missing fields
        return {
            "schema_version": "1.0",
            "branch": branch_name,
            "chapter": chapter,
            "passed": False,
            "errors": errors,
            "warnings": warnings,
            "generated_at": now_iso()
        }

    aligned_segments = result.get("aligned_segments", [])
    if aligned_segments:
        translated_text = "\n\n".join(seg.get("target", "") for seg in aligned_segments if seg.get("target"))
        result["translated_text"] = translated_text
        # Hydrate the file on disk so downstream scripts (like update_state.py) can read translated_text
        save_json_atomic(result_path, result)
    else:
        translated_text = result.get("translated_text", "")

    # Load context pack and config for rules
    context_pack_path = branch_dir / "runtime" / "context_packs" / f"chapter_{chapter:04d}.context_pack.json"
    pack = load_json(context_pack_path)
    config = load_json(branch_dir / "translation_config.json") or {}

    # 4. CJK Ban Enforcement (DEFAULT ON — only skip if explicitly disabled)
    ban_cjk = config.get("sanitization", {}).get("ban_cjk_in_output", True)
    if ban_cjk is not False:
        cjk_chars = [ch for ch in translated_text if is_cjk(ch)]
        if cjk_chars:
            unique_cjk = list(set(cjk_chars))[:10]
            # Collect all positions for detailed diagnostics
            positions = []
            for i, ch in enumerate(translated_text):
                if is_cjk(ch):
                    start = max(0, i - 15)
                    end = min(len(translated_text), i + 15)
                    positions.append(f"  U+{ord(ch):04X} '{ch}' at pos {i}: '...{translated_text[start:end]}...'")
                    if len(positions) >= 5:
                        break
            detail = "\n".join(positions)
            errors.append(
                f"CJK characters found in output ({len(cjk_chars)} occurrences, "
                f"{len(set(cjk_chars))} unique): {unique_cjk}\n{detail}"
            )

    # 5. Locked Terms Enforcement
    if pack and "dynamic_glossary" in pack:
        source_text = pack.get("chapter", {}).get("source_text", "")
        for term in pack["dynamic_glossary"].get("locked_terms", []):
            source_term = term.get("source")
            target_term = term.get("target")
            if source_term and target_term and source_term in source_text:
                if target_term not in translated_text:
                    warnings.append(f"Locked term violation: '{source_term}' is in source, but target '{target_term}' not found in translation.")
                    # Note: We make this a warning rather than error because translation might rephrase it or uppercase it,
                    # but depending on strictness, this could be an error.

    # 6. Paragraph Ratio Heuristic
    if pack:
        source_text = pack.get("chapter", {}).get("source_text", "")
        source_lines = len([l for l in source_text.splitlines() if l.strip()])
        target_lines = len([l for l in translated_text.splitlines() if l.strip()])
        
        if source_lines > 5:
            ratio = target_lines / source_lines
            if ratio < 0.6 or ratio > 1.8:
                warnings.append(f"Paragraph ratio anomaly: source={source_lines}, target={target_lines}, ratio={ratio:.2f}")

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

def write_postcheck_report(branch_name: str, chapter: int, report: dict) -> Path:
    """Write postcheck report to runtime/gates/."""
    branch_dir = resolve_branch_dir(branch_name)
    target = branch_dir / "runtime" / "gates" / f"chapter_{chapter:04d}.postcheck.json"
    save_json_atomic(target, report)
    return target

def main() -> int:
    parser = argparse.ArgumentParser(description="Postcheck Gate for Dichtrung translation")
    parser.add_argument("--branch", required=True, help="Project branch name")
    parser.add_argument("--chapter", required=True, type=int, help="Chapter number")
    parser.add_argument("--dry-run", action="store_true", help="Print report to stdout without writing")
    args = parser.parse_args()

    report = run_validation(args.branch, args.chapter)

    if args.dry_run:
        import json as _json
        sys.stdout.reconfigure(encoding="utf-8")
        print(_json.dumps(report, ensure_ascii=False, indent=2))
    else:
        target = write_postcheck_report(args.branch, args.chapter, report)
        if report["passed"]:
            LOGGER.info("Postcheck PASS: %s", target)
            for warn in report["warnings"]:
                LOGGER.warning(" - %s", warn)
        else:
            LOGGER.error("Postcheck FAIL: %s", target)
            for err in report["errors"]:
                LOGGER.error(" - %s", err)
            for warn in report["warnings"]:
                LOGGER.warning(" - %s", warn)

    return 0 if report["passed"] else 1

if __name__ == "__main__":
    sys.exit(main())
