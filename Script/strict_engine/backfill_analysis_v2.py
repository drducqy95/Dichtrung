#!/usr/bin/env python3
"""Backfill chapters into Contract V2 without rewriting translated prose files."""
from __future__ import annotations

import argparse
import json
import math
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from analysis_contract import analyzer_payload, join_targets, normalize_text, split_paragraphs
from build_context_pack import build_context_pack, write_context_pack
from build_translation_analysis import build_translation_analysis
from promote_reviewed import promote_reviewed
from source_analyzer import build_scan_report, write_scan_report
from sync_analysis_global import sync_analysis_to_global
from update_analysis_state import rebuild_analysis_state
from utils import io
from validate_analysis import validate_analysis
from validate_translation import run_validation, write_postcheck_report

LOGGER = io.get_logger("backfill_analysis_v2")
ANALYZERS = (
    "term_occurrences",
    "entity_mentions",
    "name_mentions",
    "phrase_patterns",
    "grammar_rule_candidates",
)


def _backup(branch_dir: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target = branch_dir / "backups" / f"strict_engine_v1_{stamp}"
    io.ensure_dir(target)
    for name in ("runtime", "analysis"):
        source = branch_dir / name
        if source.exists():
            shutil.copytree(source, target / name)
    for name in ("glossary.json", "characters.json"):
        source = branch_dir / name
        if source.exists():
            shutil.copy2(source, target / name)
    global_target = target / "global_state_snapshot"
    io.ensure_dir(global_target)
    for name in ("global_glossary.json", "global_characters.json", "global_grammar_rules.jsonl"):
        source = io.GLOBAL_STATE_DIR / name
        if source.exists():
            shutil.copy2(source, global_target / name)
    return target


def _output_hashes(branch_dir: Path) -> dict[str, str]:
    return {
        str(path): io.sha256_text(path.read_text(encoding="utf-8"))
        for path in sorted((branch_dir / "output").glob("*.md"))
    }


def _disable_existing_reviewed(branch_dir: Path) -> None:
    analysis_dir = branch_dir / "analysis"
    for name in (
        "reviewed_terms.jsonl",
        "reviewed_names.jsonl",
        "reviewed_patterns.jsonl",
        "reviewed_rules.jsonl",
        "promotion_review_queue.jsonl",
    ):
        io.write_text_atomic(analysis_dir / name, "")
    glossary_path = branch_dir / "glossary.json"
    glossary = io.load_json(glossary_path, default={"entries": []}) or {"entries": []}
    for item in glossary.get("entries", []):
        if item.get("status") == "auto-locked":
            item["locked"] = False
            item.pop("status", None)
            item.pop("reviewed_chapters", None)
    io.save_json_atomic(glossary_path, glossary)


def _length_cost(source_parts: list[str], target_parts: list[str], ratio: float) -> float:
    source_len = max(1, sum(len(item) for item in source_parts))
    target_len = max(1, sum(len(item) for item in target_parts))
    relative = abs(math.log(target_len / max(1.0, source_len * ratio)))
    grouping_penalty = 0.35 * ((len(source_parts) - 1) + (len(target_parts) - 1))
    return relative + grouping_penalty


def monotonic_align(source_parts: list[str], target_parts: list[str]) -> list[tuple[int, int, int, int]]:
    """Align contiguous blocks with deterministic monotonic dynamic programming."""
    if not source_parts or not target_parts:
        raise ValueError("Cannot align empty source or target text")
    if len(source_parts) == len(target_parts):
        return [
            (index, index + 1, index, index + 1)
            for index in range(len(source_parts))
        ]
    source_total = sum(len(item) for item in source_parts)
    target_total = sum(len(item) for item in target_parts)
    ratio = target_total / max(1, source_total)
    n, m = len(source_parts), len(target_parts)
    inf = float("inf")
    cost = [[inf] * (m + 1) for _ in range(n + 1)]
    previous: list[list[tuple[int, int, int, int] | None]] = [
        [None] * (m + 1) for _ in range(n + 1)
    ]
    cost[0][0] = 0.0
    for source_index in range(n):
        for target_index in range(m):
            if cost[source_index][target_index] == inf:
                continue
            for source_span in range(1, min(4, n - source_index) + 1):
                for target_span in range(1, min(4, m - target_index) + 1):
                    next_source = source_index + source_span
                    next_target = target_index + target_span
                    next_cost = cost[source_index][target_index] + _length_cost(
                        source_parts[source_index:next_source],
                        target_parts[target_index:next_target],
                        ratio,
                    )
                    if next_cost < cost[next_source][next_target]:
                        cost[next_source][next_target] = next_cost
                        previous[next_source][next_target] = (
                            source_index,
                            target_index,
                            source_span,
                            target_span,
                        )
    if cost[n][m] == inf:
        raise ValueError(f"Could not align {n} source blocks to {m} target blocks")
    groups = []
    source_index, target_index = n, m
    while source_index or target_index:
        step = previous[source_index][target_index]
        if step is None:
            raise ValueError("Alignment backtrack failed")
        old_source, old_target, _, _ = step
        groups.append((old_source, source_index, old_target, target_index))
        source_index, target_index = old_source, old_target
    return list(reversed(groups))


def _narrative_type(source: str, target: str) -> str:
    if any(mark in source or mark in target for mark in ('"', "“", "”", "「", "」")):
        return "dialogue"
    return "narration"


def _sanitize_terms(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for item in items:
        source = item.get("source") or item.get("source_term")
        target = item.get("target") or item.get("target_term")
        if source and target:
            row = {"source": str(source), "target": str(target)}
            for key in ("category", "note"):
                if item.get(key) is not None:
                    row[key] = str(item[key])
            if isinstance(item.get("confidence"), (int, float)):
                row["confidence"] = float(item["confidence"])
            rows.append(row)
    return rows


def _sanitize_characters(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    allowed = {
        "id", "name_original", "name_translated", "name_source", "name_target",
        "gender", "age_group", "description", "pronouns", "role",
    }
    rows = []
    for item in items:
        source = item.get("name_original") or item.get("name_source")
        target = item.get("name_translated") or item.get("name_target")
        if source and target:
            rows.append({key: value for key, value in item.items() if key in allowed})
    return rows


def _sanitize_worldbuilding(payload: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    allowed = {"name_source", "name_target", "source", "target", "type", "description"}
    return {
        section: [
            {key: value for key, value in item.items() if key in allowed}
            for item in payload.get(section, [])
            if isinstance(item, dict)
        ]
        for section in ("factions", "locations", "techniques", "items", "cultivation_resources")
    }


def _sanitize_timeline(payload: dict[str, Any], chapter: int, title: str) -> dict[str, Any]:
    characters = []
    for item in payload.get("characters", []):
        if isinstance(item, dict) and item.get("name"):
            characters.append(
                {
                    "name": str(item["name"]),
                    "interaction": str(item.get("interaction") or ""),
                    "is_new": bool(item.get("is_new", False)),
                }
            )
    return {
        "chapter": chapter,
        "title": str(payload.get("title") or title),
        "summary": str(payload.get("summary") or ""),
        "characters": characters,
        "items": payload.get("items", []),
        "plot_points": [str(item) for item in payload.get("plot_points", [])],
        **({"timestamp": str(payload["timestamp"])} if payload.get("timestamp") else {}),
    }


def _legacy_text(result: dict[str, Any]) -> str:
    text = str(result.get("translated_text") or "")
    if not text:
        text = "\n\n".join(
            str(item.get("target") or "") for item in result.get("aligned_segments", [])
        )
    return normalize_text(text)


def _published_text(branch_dir: Path, chapter: int) -> str:
    matches = sorted((branch_dir / "output").glob(f"*{chapter:04d} - *.md"))
    if not matches:
        return ""
    markdown = normalize_text(matches[0].read_text(encoding="utf-8"))
    parts = markdown.split("\n\n", 1)
    return normalize_text(parts[1]) if len(parts) == 2 else ""


def migrate_result(
    branch_name: str,
    chapter: int,
    legacy: dict[str, Any],
    manifest: dict[str, Any],
    translated_text: str | None = None,
) -> dict[str, Any]:
    translated_text = normalize_text(translated_text or _legacy_text(legacy))
    source_parts = [item["source"] for item in manifest["source_segments"]]
    target_parts = split_paragraphs(translated_text)
    groups = monotonic_align(source_parts, target_parts)
    translations = []
    for source_start, source_end, target_start, target_end in groups:
        source = "\n\n".join(source_parts[source_start:source_end])
        target = "\n\n".join(target_parts[target_start:target_end])
        if target not in translated_text:
            raise ValueError(f"Chapter {chapter}: target group is not a legacy prose substring")
        translations.append(
            {
                "segment_ids": [
                    item["segment_id"]
                    for item in manifest["source_segments"][source_start:source_end]
                ],
                "target": target,
                "narrative_type": _narrative_type(source, target),
            }
        )
    if join_targets(translations) != translated_text:
        raise ValueError(f"Chapter {chapter}: migrated targets do not reconstruct legacy prose")
    title = str(legacy.get("chapter_title_translated") or "")
    result = {
        "schema_version": "2.0",
        "chapter_id": manifest["chapter_id"],
        "source_manifest_hash": manifest["source_manifest_hash"],
        "chapter_title_translated": title,
        "segment_translations": translations,
        "new_terms_discovered": _sanitize_terms(legacy.get("new_terms_discovered", [])),
        "new_characters_discovered": _sanitize_characters(legacy.get("new_characters_discovered", [])),
        "chapter_summary": str(legacy.get("chapter_summary") or ""),
        "worldbuilding_updates": _sanitize_worldbuilding(legacy.get("worldbuilding_updates", {})),
        "timeline_entry": _sanitize_timeline(legacy.get("timeline_entry", {}), chapter, title),
        "analysis_candidates": {name: analyzer_payload([]) for name in ANALYZERS},
        "translated_text": translated_text,
    }
    return result


def run_backfill(
    branch_name: str,
    start: int = 1,
    end: int = 39,
    backup: bool = True,
    sync_global: bool = True,
) -> dict[str, Any]:
    branch_dir = io.resolve_branch_dir(branch_name)
    if not branch_dir.exists():
        raise FileNotFoundError(f"Branch not found: {branch_dir}")
    before_outputs = _output_hashes(branch_dir)
    backup_dir = _backup(branch_dir) if backup else None
    _disable_existing_reviewed(branch_dir)
    chapters = []
    for chapter in range(start, end + 1):
        legacy_path = branch_dir / "runtime" / f"chapter_{chapter:04d}.translation_result.json"
        legacy = io.load_json(legacy_path)
        if not legacy:
            raise FileNotFoundError(f"Legacy translation result missing: {legacy_path}")
        scan = build_scan_report(branch_name, chapter)
        write_scan_report(branch_name, chapter, scan)
        pack = build_context_pack(branch_name, chapter)
        write_context_pack(branch_name, chapter, pack)
        manifest = io.load_json(
            branch_dir / "runtime" / "manifests" / f"chapter_{chapter:04d}.source_segments.json"
        )
        result = migrate_result(
            branch_name,
            chapter,
            legacy,
            manifest,
            translated_text=_published_text(branch_dir, chapter),
        )
        io.save_json_atomic(legacy_path, result)
        postcheck = run_validation(branch_name, chapter)
        write_postcheck_report(branch_name, chapter, postcheck)
        if not postcheck["passed"]:
            raise ValueError(f"Chapter {chapter}: translation gate failed: {postcheck['errors']}")
        build_translation_analysis(branch_name, chapter)
        analysis_gate = validate_analysis(branch_name, chapter)
        io.save_json_atomic(
            branch_dir / "runtime" / "gates" / f"chapter_{chapter:04d}.analysischeck.json",
            analysis_gate,
        )
        if not analysis_gate["passed"]:
            raise ValueError(f"Chapter {chapter}: analysis gate failed: {analysis_gate['errors']}")
        chapters.append(chapter)
        LOGGER.info("Backfilled chapter %d", chapter)
    rebuild_report = rebuild_analysis_state(branch_name)
    promotion_report = promote_reviewed(branch_name, end)
    sync_report = sync_analysis_to_global(branch_name) if sync_global else {}
    after_outputs = _output_hashes(branch_dir)
    if before_outputs != after_outputs:
        raise ValueError("Output Markdown changed during backfill")
    report = {
        "branch": branch_name,
        "chapters": chapters,
        "backup_dir": str(backup_dir) if backup_dir else "",
        "output_markdown_unchanged": True,
        "rebuild": rebuild_report,
        "promotion": promotion_report,
        "sync": sync_report,
    }
    io.save_json_atomic(branch_dir / "analysis" / "audit" / "backfill_v2.json", report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill immutable Contract V2 analysis artifacts")
    parser.add_argument("--branch", required=True)
    parser.add_argument("--from-chapter", type=int, default=1)
    parser.add_argument("--to-chapter", type=int, default=39)
    parser.add_argument("--skip-backup", action="store_true")
    parser.add_argument("--no-sync", action="store_true")
    args = parser.parse_args()
    report = run_backfill(
        args.branch,
        args.from_chapter,
        args.to_chapter,
        backup=not args.skip_backup,
        sync_global=not args.no_sync,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
