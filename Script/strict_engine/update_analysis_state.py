#!/usr/bin/env python3
"""Rebuild derived JSONL analysis state from chapter artifacts idempotently."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from utils import io

LOGGER = io.get_logger("update_analysis_state")


def _write_jsonl(path: Path, items: list[dict[str, Any]]) -> None:
    text = "".join(json.dumps(item, ensure_ascii=False) + "\n" for item in items)
    io.write_text_atomic(path, text)


def rebuild_analysis_state(branch_name: str) -> dict[str, int]:
    branch_dir = io.resolve_branch_dir(branch_name)
    runtime_dir = branch_dir / "runtime" / "analysis"
    output_dir = branch_dir / "analysis"
    io.ensure_dir(output_dir)
    io.ensure_dir(output_dir / "audit")
    buckets: dict[str, list[dict[str, Any]]] = {
        "aligned_segments": [],
        "term_occurrences": [],
        "entity_mentions": [],
        "name_mentions": [],
        "phrase_patterns": [],
        "grammar_rules": [],
        "review_queue": [],
    }
    chapter_count = 0
    for path in sorted(runtime_dir.glob("chapter_*.analysis_result.json")):
        data = io.load_json(path)
        if not data:
            continue
        chapter_count += 1
        buckets["aligned_segments"].extend(data.get("aligned_segments", []))
        buckets["term_occurrences"].extend(data.get("term_occurrences", []))
        buckets["entity_mentions"].extend(data.get("entity_mentions", []))
        buckets["name_mentions"].extend(data.get("name_analysis", {}).get("name_mentions", []))
        buckets["phrase_patterns"].extend(data.get("phrase_patterns", []))
        buckets["grammar_rules"].extend(data.get("grammar_rule_candidates", []))
        buckets["review_queue"].extend(data.get("review_queue", []))
        if data.get("quality_audit"):
            io.save_json_atomic(
                output_dir / "audit" / f"chapter_{int(data['chapter']):04d}.json",
                data["quality_audit"],
            )
    for name, rows in buckets.items():
        _write_jsonl(output_dir / f"{name}.jsonl", rows)
    report = {"chapters": chapter_count, **{name: len(rows) for name, rows in buckets.items()}}
    LOGGER.info("Rebuilt derived analysis state for %s: %s", branch_name, report)
    return report


def update_analysis_state(
    branch_name: str,
    chapter: int,
    promote: bool | None = None,
) -> bool:
    branch_dir = io.resolve_branch_dir(branch_name)
    artifact = (
        branch_dir
        / "runtime"
        / "analysis"
        / f"chapter_{chapter:04d}.analysis_result.json"
    )
    if not artifact.exists():
        LOGGER.error("Analysis artifact missing: %s", artifact)
        return False
    rebuild_analysis_state(branch_name)
    should_promote = chapter % 10 == 0 if promote is None else promote
    if should_promote:
        import promote_reviewed
        import sync_analysis_global

        promote_reviewed.promote_reviewed(branch_name, chapter)
        sync_analysis_global.sync_analysis_to_global(branch_name)
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Rebuild idempotent analysis JSONL state")
    parser.add_argument("--branch", required=True)
    parser.add_argument("--chapter", required=True, type=int)
    parser.add_argument("--no-promote", action="store_true")
    args = parser.parse_args()
    return 0 if update_analysis_state(args.branch, args.chapter, promote=not args.no_promote) else 1


if __name__ == "__main__":
    raise SystemExit(main())
