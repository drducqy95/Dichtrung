#!/usr/bin/env python3
"""
Validates analysis_result.json against its JSON schema and checks
some heuristic quality thresholds.
Phase 1: This is a warning-only validator. It will not block the pipeline.
"""

import json
from pathlib import Path
import jsonschema
import logging

from utils import io

logger = io.get_logger("validate_analysis")

SCHEMA_PATH = io.DICHTRUNG_ROOT / "Script" / "strict_engine" / "schemas" / "analysis_result.schema.json"

def load_schema() -> dict | None:
    if not SCHEMA_PATH.exists():
        logger.error(f"Analysis schema not found at {SCHEMA_PATH}")
        return None
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def validate_analysis(branch_name: str, chapter: int) -> dict:
    """
    Validates the analysis_result.json for a given branch and chapter.
    Returns a report dict: { "passed": bool, "warnings": list[str], "errors": list[str] }
    """
    report = {"passed": True, "warnings": [], "errors": []}
    
    branch_dir = io.resolve_branch_dir(branch_name)
    analysis_dir = branch_dir / "runtime" / "analysis"
    analysis_file = analysis_dir / f"chapter_{chapter:04d}.analysis_result.json"

    if not analysis_file.exists():
        report["errors"].append(f"Analysis result file missing: {analysis_file}")
        report["passed"] = False
        return report

    schema = load_schema()
    if not schema:
        report["errors"].append("Could not load validation schema.")
        report["passed"] = False
        return report

    data = io.load_json(analysis_file)
    if not data:
        report["errors"].append(f"Could not load analysis JSON: {analysis_file}")
        report["passed"] = False
        return report

    # 1. Schema Validation
    try:
        jsonschema.validate(instance=data, schema=schema)
    except jsonschema.ValidationError as e:
        report["errors"].append(f"Schema validation failed: {e.message} at {list(e.path)}")
        report["passed"] = False
    
    # 2. Heuristic Threshold Checks (Warning-only for Phase 1)
    if data.get("quality_audit"):
        audit = data["quality_audit"]
        
        cov = audit.get("segment_coverage", 0)
        if cov < 0.7:
            report["warnings"].append(f"Low segment coverage: {cov:.2f} (expected >= 0.7)")
            
        hit_rate = audit.get("locked_term_hit_rate", 0)
        if hit_rate < 0.8:
            report["warnings"].append(f"Low locked term hit rate: {hit_rate:.2f} (expected >= 0.8)")
            
        cjk_residue = audit.get("cjk_residue_count", 0)
        if cjk_residue > 0:
            report["warnings"].append(f"Found {cjk_residue} CJK residues in analysis.")

    # 3. Aligned Segments Count Validation
    # A typical chapter has 20-80+ sentences. Having <= 3 segments is almost
    # certainly a sign the AI only wrote a token sample instead of analysing
    # the full text.
    segments = data.get("aligned_segments", [])
    MIN_SEGMENTS = 5
    if len(segments) < MIN_SEGMENTS:
        report["warnings"].append(
            f"CRITICAL: Only {len(segments)} aligned_segments found "
            f"(expected >= {MIN_SEGMENTS}). The AI likely wrote only a "
            f"sample segment instead of analysing the full chapter."
        )

    # 4. Entity Mentions minimum sanity check
    entities = data.get("entity_mentions", [])
    if not entities:
        report["warnings"].append(
            "No entity_mentions found. Most chapters have at least "
            "one character mentioned."
        )

    return report

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--branch", required=True)
    parser.add_argument("--chapter", type=int, required=True)
    args = parser.parse_args()
    
    res = validate_analysis(args.branch, args.chapter)
    print(json.dumps(res, indent=2, ensure_ascii=False))
