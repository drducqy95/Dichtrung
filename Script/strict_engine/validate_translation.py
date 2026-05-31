#!/usr/bin/env python3
"""Strict postcheck gate for translation_result.v2."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import jsonschema

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from analysis_contract import cjk_count, join_targets, load_source_manifest, source_map  # noqa: E402
from utils import io  # noqa: E402

LOGGER = io.get_logger("validate_translation")


def _candidate_refs(result: dict[str, Any]) -> list[str]:
    refs = []
    for report in result.get("analysis_candidates", {}).values():
        for item in report.get("items", []):
            if item.get("segment_id"):
                refs.append(item["segment_id"])
            refs.extend(item.get("segment_ids", []))
    return refs


def run_validation(
    branch_name: str,
    chapter: int,
    persist_hydrated: bool = True,
) -> dict[str, Any]:
    branch_dir = io.resolve_branch_dir(branch_name)
    result_path = branch_dir / "runtime" / f"chapter_{chapter:04d}.translation_result.json"
    errors: list[str] = []
    warnings: list[str] = []

    result = io.load_json(result_path)
    if not result:
        return {
            "schema_version": "2.0",
            "branch": branch_name,
            "chapter": chapter,
            "passed": False,
            "errors": [f"Translation result not found or empty: {result_path}"],
            "warnings": [],
            "generated_at": io.now_iso(),
        }

    schema = io.load_json(ROOT / "schemas" / "translation_result.schema.json")
    try:
        jsonschema.validate(
            instance={key: value for key, value in result.items() if key != "translated_text"},
            schema=schema,
        )
    except jsonschema.ValidationError as exc:
        errors.append(f"Schema validation failed: {exc.message} at path {list(exc.path)}")

    if result.get("refusal"):
        errors.append(f"AI refused to translate: {result['refusal']}")

    try:
        manifest = load_source_manifest(branch_name, chapter)
    except FileNotFoundError as exc:
        manifest = {}
        errors.append(str(exc))

    manifest_segments = source_map(manifest)
    expected_ids = set(manifest_segments)
    translated_ids = [
        segment_id
        for item in result.get("segment_translations", [])
        for segment_id in item.get("segment_ids", [])
    ]
    translated_set = set(translated_ids)
    duplicate_ids = sorted({item for item in translated_ids if translated_ids.count(item) > 1})
    unknown_ids = sorted(translated_set - expected_ids)
    missing_ids = sorted(expected_ids - translated_set)
    if duplicate_ids:
        errors.append(f"Duplicate source segment IDs: {duplicate_ids}")
    if unknown_ids:
        errors.append(f"Unknown source segment IDs: {unknown_ids}")
    if missing_ids:
        errors.append(f"Missing source segment IDs: {missing_ids}")
    if result.get("source_manifest_hash") != manifest.get("source_manifest_hash"):
        errors.append("source_manifest_hash does not match immutable source manifest")

    unknown_candidate_refs = sorted(set(_candidate_refs(result)) - expected_ids)
    if unknown_candidate_refs:
        errors.append(f"Analysis candidate refs are not in source manifest: {unknown_candidate_refs}")

    translated_text = join_targets(result.get("segment_translations", []))
    config = io.load_json(branch_dir / "translation_config.json") or {}
    if config.get("sanitization", {}).get("ban_cjk_in_output", True) is not False:
        residue_count = cjk_count(translated_text)
        if residue_count:
            errors.append(f"CJK characters found in Vietnamese targets: {residue_count}")

    pack = io.load_json(
        branch_dir / "runtime" / "context_packs" / f"chapter_{chapter:04d}.context_pack.json"
    ) or {}
    for term in pack.get("dynamic_glossary", {}).get("locked_terms", []):
        source_term = str(term.get("source") or "")
        target_term = str(term.get("target") or "")
        if source_term and target_term and target_term not in translated_text:
            errors.append(
                f"Locked term violation: source '{source_term}' requires target '{target_term}'"
            )

    source_count = len(expected_ids)
    target_count = len(result.get("segment_translations", []))
    if source_count:
        drift_ratio = abs(target_count - source_count) / source_count
        if drift_ratio > 0.4:
            warnings.append(
                f"Paragraph grouping anomaly: source={source_count}, target={target_count}, drift={drift_ratio:.2f}"
            )

    passed = not errors
    if passed and persist_hydrated:
        result["translated_text"] = translated_text
        io.save_json_atomic(result_path, result)
    return {
        "schema_version": "2.0",
        "branch": branch_name,
        "chapter": chapter,
        "passed": passed,
        "errors": errors,
        "warnings": warnings,
        "generated_at": io.now_iso(),
    }


def write_postcheck_report(branch_name: str, chapter: int, report: dict) -> Path:
    target = (
        io.resolve_branch_dir(branch_name)
        / "runtime"
        / "gates"
        / f"chapter_{chapter:04d}.postcheck.json"
    )
    io.save_json_atomic(target, report)
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description="Strict translation_result.v2 gate")
    parser.add_argument("--branch", required=True)
    parser.add_argument("--chapter", required=True, type=int)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    report = run_validation(args.branch, args.chapter, persist_hydrated=not args.dry_run)
    if args.dry_run:
        import json

        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        target = write_postcheck_report(args.branch, args.chapter, report)
        LOGGER.info("Postcheck %s: %s", "PASS" if report["passed"] else "FAIL", target)
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
