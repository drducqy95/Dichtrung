#!/usr/bin/env python3
"""Build verified analysis_result.v2 artifacts from immutable source manifests."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from analysis_contract import cjk_count, join_targets, load_source_manifest, source_map  # noqa: E402
from name_analyzer import analyze_names  # noqa: E402
from utils import io  # noqa: E402

LOGGER = io.get_logger("build_analysis")


def _report(items: list[dict[str, Any]]) -> dict[str, Any]:
    return {"status": "ok" if items else "no_evidence", "evidence_count": len(items)}


def _candidate_items(result: dict[str, Any], analyzer: str) -> list[dict[str, Any]]:
    return result.get("analysis_candidates", {}).get(analyzer, {}).get("items", [])


def _first_segment(
    aligned_segments: list[dict[str, Any]], source_surface: str
) -> dict[str, Any] | None:
    return next(
        (item for item in aligned_segments if source_surface in item.get("source", "")),
        None,
    )


def _source_name(item: dict[str, Any]) -> str:
    return str(
        item.get("name_source")
        or item.get("source")
        or item.get("name_original")
        or item.get("zh_name")
        or ""
    )


def _target_name(item: dict[str, Any]) -> str:
    return str(
        item.get("name_target")
        or item.get("target")
        or item.get("name_translated")
        or ""
    )


def _build_aligned_segments(
    chapter_id: str,
    manifest: dict[str, Any],
    result: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[str]]:
    by_id = source_map(manifest)
    aligned = []
    invalid_refs = []
    for index, translation in enumerate(result.get("segment_translations", []), start=1):
        segment_ids = translation.get("segment_ids", [])
        unknown = [segment_id for segment_id in segment_ids if segment_id not in by_id]
        invalid_refs.extend(unknown)
        if unknown or not segment_ids:
            continue
        source = "\n\n".join(by_id[segment_id]["source"] for segment_id in segment_ids)
        aligned.append(
            {
                "alignment_id": f"{chapter_id}:align_{index:04d}",
                "chapter_id": chapter_id,
                "segment_ids": segment_ids,
                "source": source,
                "source_hash": io.sha256_text(source),
                "target": str(translation.get("target") or "").strip(),
                "narrative_type": translation.get("narrative_type", "narration"),
                "alignment_type": "one_to_one" if len(segment_ids) == 1 else "merged_source",
            }
        )
    return aligned, invalid_refs


def _term_occurrences(
    chapter_id: str,
    aligned: list[dict[str, Any]],
    glossary: dict[str, Any],
    candidates: list[dict[str, Any]],
    locked_sources: set[str] | None = None,
) -> list[dict[str, Any]]:
    target_text = join_targets(aligned)
    rows = []
    seen: set[tuple[str, str]] = set()
    known = [
        {
            "source_term": item.get("source"),
            "target_term": item.get("target"),
            "category": item.get("category", "other"),
            "is_locked": item.get("source") in (locked_sources or set()),
            "confidence": 1.0,
        }
        for item in glossary.get("entries", [])
    ]
    known.extend(
        {
            **item,
            "is_locked": False,
        }
        for item in candidates
    )
    for item in known:
        source = str(item.get("source_term") or "")
        target = str(item.get("target_term") or "")
        segment = _first_segment(aligned, source)
        if not source or not target or not segment or (source, target) in seen:
            continue
        seen.add((source, target))
        rows.append(
            {
                "chapter_id": chapter_id,
                "source_term": source,
                "target_term": target,
                "segment_id": segment["segment_ids"][0],
                "present_in_target": target in target_text,
                "is_locked": bool(item.get("is_locked")),
                "category": str(item.get("category") or "other"),
                "confidence": float(item.get("confidence", 1.0)),
            }
        )
    return rows


def _entity_mentions(
    chapter_id: str,
    aligned: list[dict[str, Any]],
    characters: dict[str, Any],
    worldbuilding: dict[str, Any],
    candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows = []
    seen: set[tuple[str, str, str]] = set()
    known = [
        {
            "source_surface": _source_name(item),
            "target_surface": _target_name(item),
            "entity_type": "person",
            "confidence": 1.0,
        }
        for item in characters.get("characters", [])
    ]
    for section, items in worldbuilding.items():
        if not isinstance(items, list):
            continue
        for item in items:
            if isinstance(item, dict):
                known.append(
                    {
                        "source_surface": item.get("source") or item.get("name_source"),
                        "target_surface": item.get("target") or item.get("name_target"),
                        "entity_type": section,
                        "confidence": 1.0,
                    }
                )
    known.extend(candidates)
    for item in known:
        source = str(item.get("source_surface") or "")
        target = str(item.get("target_surface") or "")
        entity_type = str(item.get("entity_type") or "unknown")
        segment = _first_segment(aligned, source)
        key = (source, target, entity_type)
        if not source or not target or not segment or key in seen:
            continue
        seen.add(key)
        rows.append(
            {
                "chapter_id": chapter_id,
                "source_surface": source,
                "target_surface": target,
                "entity_type": entity_type,
                "segment_id": segment["segment_ids"][0],
                "confidence": float(item.get("confidence", 1.0)),
            }
        )
    return rows


def _verified_patterns(
    chapter_id: str,
    aligned: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
    review_queue: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_id = {
        segment_id: item
        for item in aligned
        for segment_id in item.get("segment_ids", [])
    }
    rows = []
    seen = set()
    for item in candidates:
        refs = item.get("segment_ids", [])
        source_pattern = str(item.get("source_pattern") or "")
        evidence_text = "\n\n".join(
            by_id[ref]["source"] for ref in refs if ref in by_id
        )
        if not refs or any(ref not in by_id for ref in refs):
            review_queue.append({"chapter_id": chapter_id, "kind": "invalid_ref", "reason": "Pattern candidate has invalid segment refs.", "payload": item})
            continue
        if source_pattern not in evidence_text:
            review_queue.append({"chapter_id": chapter_id, "kind": "unverified_pattern", "reason": "Pattern text is not exact evidence in referenced source.", "payload": item})
            continue
        key = (item.get("alias"), source_pattern, item.get("target_pattern"))
        if key in seen:
            continue
        seen.add(key)
        rows.append(
            {
                "chapter_id": chapter_id,
                "alias": str(item.get("alias") or ""),
                "source_pattern": source_pattern,
                "target_pattern": str(item.get("target_pattern") or ""),
                "segment_ids": refs,
                "confidence": float(item.get("confidence", 0.0)),
            }
        )
    return rows


def build_translation_analysis(
    branch_name: str,
    chapter: int,
    dry_run: bool = False,
) -> dict[str, Any]:
    branch_dir = io.resolve_branch_dir(branch_name)
    result_path = branch_dir / "runtime" / f"chapter_{chapter:04d}.translation_result.json"
    result = io.load_json(result_path)
    if not result:
        raise FileNotFoundError(f"Translation result not found: {result_path}")
    manifest = load_source_manifest(branch_name, chapter)
    chapter_id = manifest["chapter_id"]
    glossary = io.load_json(branch_dir / "glossary.json", default={"entries": []}) or {"entries": []}
    characters = io.load_json(branch_dir / "characters.json", default={"characters": []}) or {"characters": []}
    worldbuilding = io.load_json(branch_dir / "worldbuilding.json", default={}) or {}
    scan_report = io.load_json(
        branch_dir / "runtime" / "manifests" / f"chapter_{chapter:04d}.scan.json",
        default={},
    ) or {}
    context_pack = io.load_json(
        branch_dir / "runtime" / "context_packs" / f"chapter_{chapter:04d}.context_pack.json",
        default={},
    ) or {}

    aligned, invalid_refs = _build_aligned_segments(chapter_id, manifest, result)
    review_queue = [
        {
            "chapter_id": chapter_id,
            "kind": "heuristic_candidate",
            "reason": "Source heuristic is review-only and is not hard evidence.",
            "payload": item,
        }
        for values in scan_report.get("heuristic_candidates", {}).values()
        for item in values
        if isinstance(item, dict)
    ]
    review_queue.extend(
        {
            "chapter_id": chapter_id,
            "kind": "backfill_alignment_review",
            "reason": "Legacy backfill grouped multiple source segments. Review this split/merge case before using it as semantic training evidence.",
            "payload": {
                "alignment_id": item["alignment_id"],
                "segment_ids": item["segment_ids"],
            },
        }
        for item in aligned
        if len(item.get("segment_ids", [])) > 1
    )
    terms = _term_occurrences(
        chapter_id,
        aligned,
        glossary,
        _candidate_items(result, "term_occurrences"),
        {
            str(item.get("source") or "")
            for item in context_pack.get("dynamic_glossary", {}).get("locked_terms", [])
        },
    )
    entities = _entity_mentions(
        chapter_id,
        aligned,
        characters,
        worldbuilding,
        _candidate_items(result, "entity_mentions"),
    )
    names = analyze_names(aligned, characters, _candidate_items(result, "name_mentions"))
    patterns = _verified_patterns(
        chapter_id,
        aligned,
        _candidate_items(result, "phrase_patterns"),
        review_queue,
    )
    rules = _verified_patterns(
        chapter_id,
        aligned,
        _candidate_items(result, "grammar_rule_candidates"),
        review_queue,
    )

    expected_ids = set(source_map(manifest))
    covered_ids = [
        segment_id for item in aligned for segment_id in item.get("segment_ids", [])
    ]
    candidate_refs = [
        ref
        for analyzer in result.get("analysis_candidates", {}).values()
        for item in analyzer.get("items", [])
        for ref in ([item["segment_id"]] if item.get("segment_id") else item.get("segment_ids", []))
    ]
    invalid_ref_count = len(invalid_refs) + len(set(candidate_refs) - expected_ids)
    source_hash_match = (
        result.get("source_manifest_hash") == manifest.get("source_manifest_hash")
        and all(item["source_hash"] == io.sha256_text(item["source"]) for item in aligned)
    )
    translated_text = join_targets(result.get("segment_translations", []))
    locked_terms = [item for item in terms if item["is_locked"]]
    missing_locked = [
        item["source_term"] for item in locked_terms if not item["present_in_target"]
    ]
    warnings = []
    pronoun_warnings = context_pack.get("relationship_graph", {}).get("warnings", [])
    payload = {
        "schema_version": "2.0",
        "branch": branch_name,
        "chapter": chapter,
        "chapter_id": chapter_id,
        "source_manifest_hash": manifest["source_manifest_hash"],
        "aligned_segments": aligned,
        "term_occurrences": terms,
        "entity_mentions": entities,
        "name_analysis": names,
        "phrase_patterns": patterns,
        "grammar_rule_candidates": rules,
        "analyzer_reports": {
            "term_occurrences": _report(terms),
            "entity_mentions": _report(entities),
            "name_mentions": _report(names["name_mentions"]),
            "phrase_patterns": _report(patterns),
            "grammar_rule_candidates": _report(rules),
        },
        "review_queue": review_queue,
        "quality_audit": {
            "segment_coverage": len(set(covered_ids)) / len(expected_ids) if expected_ids else 0.0,
            "source_hash_match": source_hash_match,
            "target_reconstruction_match": translated_text == join_targets(aligned),
            "invalid_ref_count": invalid_ref_count,
            "locked_term_hit_rate": (
                (len(locked_terms) - len(missing_locked)) / len(locked_terms)
                if locked_terms
                else 1.0
            ),
            "missing_locked_terms": missing_locked,
            "cjk_residue_count": cjk_count(translated_text),
            "paragraph_drift_ratio": (
                abs(len(aligned) - len(expected_ids)) / len(expected_ids)
                if expected_ids
                else 0.0
            ),
            "pronoun_consistency_score": 0.0 if pronoun_warnings else 1.0,
            "warnings": warnings,
        },
    }
    if not dry_run:
        target = (
            branch_dir
            / "runtime"
            / "analysis"
            / f"chapter_{chapter:04d}.analysis_result.json"
        )
        io.save_json_atomic(target, payload)
        LOGGER.info("Built analysis result: %s", target)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Build verified analysis_result.v2")
    parser.add_argument("--branch", required=True)
    parser.add_argument("--chapter", required=True, type=int)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    build_translation_analysis(args.branch, args.chapter, args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
