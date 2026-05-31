#!/usr/bin/env python3
"""Strict gate for independently built analysis_result.v2 artifacts."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import jsonschema

from analysis_contract import load_source_manifest, source_map
from utils import io

LOGGER = io.get_logger("validate_analysis")
SCHEMA_PATH = Path(__file__).resolve().parent / "schemas" / "analysis_result.schema.json"


def _refs(data: dict[str, Any]) -> list[str]:
    refs = [
        segment_id
        for item in data.get("aligned_segments", [])
        for segment_id in item.get("segment_ids", [])
    ]
    refs.extend(item["segment_id"] for item in data.get("term_occurrences", []))
    refs.extend(item["segment_id"] for item in data.get("entity_mentions", []))
    refs.extend(item["segment_id"] for item in data.get("name_analysis", {}).get("name_mentions", []))
    for analyzer in ("phrase_patterns", "grammar_rule_candidates"):
        refs.extend(
            segment_id
            for item in data.get(analyzer, [])
            for segment_id in item.get("segment_ids", [])
        )
    return refs


def validate_analysis(branch_name: str, chapter: int) -> dict[str, Any]:
    branch_dir = io.resolve_branch_dir(branch_name)
    analysis_path = (
        branch_dir
        / "runtime"
        / "analysis"
        / f"chapter_{chapter:04d}.analysis_result.json"
    )
    errors: list[str] = []
    warnings: list[str] = []
    data = io.load_json(analysis_path)
    if not data:
        return {"passed": False, "errors": [f"Analysis result missing: {analysis_path}"], "warnings": []}

    try:
        jsonschema.validate(instance=data, schema=io.load_json(SCHEMA_PATH))
    except jsonschema.ValidationError as exc:
        errors.append(f"Schema validation failed: {exc.message} at {list(exc.path)}")

    try:
        manifest = load_source_manifest(branch_name, chapter)
    except FileNotFoundError as exc:
        manifest = {}
        errors.append(str(exc))
    expected_ids = set(source_map(manifest))
    aligned_ids = [
        segment_id
        for item in data.get("aligned_segments", [])
        for segment_id in item.get("segment_ids", [])
    ]
    duplicate_ids = sorted({item for item in aligned_ids if aligned_ids.count(item) > 1})
    missing_ids = sorted(expected_ids - set(aligned_ids))
    unknown_ids = sorted(set(aligned_ids) - expected_ids)
    if duplicate_ids:
        errors.append(f"Duplicate aligned source segment IDs: {duplicate_ids}")
    if missing_ids:
        errors.append(f"Missing aligned source segment IDs: {missing_ids}")
    if unknown_ids:
        errors.append(f"Unknown aligned source segment IDs: {unknown_ids}")
    invalid_refs = sorted(set(_refs(data)) - expected_ids)
    if invalid_refs:
        errors.append(f"Analysis references unknown segment IDs: {invalid_refs}")
    if data.get("source_manifest_hash") != manifest.get("source_manifest_hash"):
        errors.append("Analysis source_manifest_hash does not match immutable manifest")

    audit = data.get("quality_audit", {})
    strict_audit = {
        "segment_coverage": 1.0,
        "source_hash_match": True,
        "target_reconstruction_match": True,
        "invalid_ref_count": 0,
        "cjk_residue_count": 0,
    }
    for field, expected in strict_audit.items():
        if audit.get(field) != expected:
            errors.append(f"quality_audit.{field} must be {expected!r}, got {audit.get(field)!r}")
    if audit.get("missing_locked_terms"):
        errors.append(f"Missing locked terms: {audit['missing_locked_terms']}")
    if audit.get("locked_term_hit_rate") != 1.0:
        errors.append(
            f"quality_audit.locked_term_hit_rate must be 1.0, got {audit.get('locked_term_hit_rate')!r}"
        )

    collections = {
        "term_occurrences": data.get("term_occurrences", []),
        "entity_mentions": data.get("entity_mentions", []),
        "name_mentions": data.get("name_analysis", {}).get("name_mentions", []),
        "phrase_patterns": data.get("phrase_patterns", []),
        "grammar_rule_candidates": data.get("grammar_rule_candidates", []),
    }
    reports = data.get("analyzer_reports", {})
    for name, items in collections.items():
        report = reports.get(name)
        if not report:
            errors.append(f"Missing analyzer report: {name}")
            continue
        expected_status = "ok" if items else "no_evidence"
        if report.get("status") != expected_status:
            errors.append(
                f"Analyzer {name} status must be {expected_status!r} for {len(items)} evidence rows"
            )
        if report.get("evidence_count") != len(items):
            errors.append(
                f"Analyzer {name} evidence_count mismatch: {report.get('evidence_count')} != {len(items)}"
            )

    return {"passed": not errors, "errors": errors, "warnings": warnings}


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate analysis_result.v2")
    parser.add_argument("--branch", required=True)
    parser.add_argument("--chapter", required=True, type=int)
    args = parser.parse_args()
    report = validate_analysis(args.branch, args.chapter)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
