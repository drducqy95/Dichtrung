#!/usr/bin/env python3
"""Promote verified analysis evidence using distinct-chapter thresholds."""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from utils import io

LOGGER = io.get_logger("promote_reviewed")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    io.write_text_atomic(
        path,
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
    )


def aggregate_terms(
    rows: list[dict[str, Any]],
    kind: str = "term",
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    mappings: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    for item in rows:
        source = str(item.get("source_term") or item.get("name_source") or "")
        target = str(item.get("target_term") or item.get("name_target") or "")
        chapter_id = str(item.get("chapter_id") or "")
        present = item.get("present_in_target", True)
        if source and target and chapter_id and present:
            mappings[source][target].add(chapter_id)
    reviewed = []
    review_queue = []
    for source, targets in mappings.items():
        if len(targets) > 1:
            review_queue.append(
                {
                    "kind": f"{kind}_conflict",
                    "reason": "A source surface has conflicting verified mappings.",
                    "payload": {source: {target: sorted(chapters) for target, chapters in targets.items()}},
                }
            )
            continue
        target, chapters = next(iter(targets.items()))
        if len(chapters) >= 2:
            reviewed.append(
                {
                    "source": source,
                    "target": target,
                    "chapters": sorted(chapters),
                    "evidence_count": len(chapters),
                    "status": "auto-locked",
                    "locked": True,
                    "kind": kind,
                }
            )
    return sorted(reviewed, key=lambda item: item["source"]), review_queue


def aggregate_patterns(
    rows: list[dict[str, Any]],
    kind: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    aliases: dict[str, set[tuple[str, str]]] = defaultdict(set)
    for item in rows:
        alias = str(item.get("alias") or "")
        source = str(item.get("source_pattern") or "")
        target = str(item.get("target_pattern") or "")
        if alias and source and target and item.get("chapter_id"):
            grouped[(alias, source, target)].append(item)
            aliases[alias].add((source, target))
    reviewed = []
    queue = []
    conflicted = {alias for alias, mappings in aliases.items() if len(mappings) > 1}
    for alias in sorted(conflicted):
        queue.append(
            {
                "kind": f"{kind}_conflict",
                "reason": "An alias has conflicting pattern mappings.",
                "payload": {"alias": alias, "mappings": sorted(aliases[alias])},
            }
        )
    for (alias, source, target), items in grouped.items():
        chapters = sorted({str(item["chapter_id"]) for item in items})
        avg_confidence = sum(float(item.get("confidence", 0.0)) for item in items) / len(items)
        if alias not in conflicted and len(chapters) >= 3 and avg_confidence >= 0.85:
            reviewed.append(
                {
                    "alias": alias,
                    "source_pattern": source,
                    "target_pattern": target,
                    "chapters": chapters,
                    "evidence_count": len(chapters),
                    "confidence": round(avg_confidence, 4),
                    "status": "reviewed",
                    "kind": kind,
                }
            )
    return sorted(reviewed, key=lambda item: item["alias"]), queue


def _lock_branch_glossary(
    branch_dir: Path,
    reviewed_terms: list[dict[str, Any]],
    review_queue: list[dict[str, Any]],
) -> None:
    path = branch_dir / "glossary.json"
    glossary = io.load_json(path, default={"entries": []}) or {"entries": []}
    by_source = {str(item.get("source") or ""): item for item in glossary.get("entries", [])}
    for reviewed in reviewed_terms:
        existing = by_source.get(reviewed["source"])
        if existing and existing.get("locked") is True and existing.get("target") != reviewed["target"]:
            review_queue.append(
                {
                    "kind": "manual_lock_conflict",
                    "reason": "Auto-promotion cannot overwrite a manual locked mapping.",
                    "payload": {"existing": existing, "candidate": reviewed},
                }
            )
            continue
        if existing:
            existing["locked"] = True
            existing["status"] = "auto-locked"
            existing["reviewed_chapters"] = reviewed["chapters"]
        else:
            entry = {
                "source": reviewed["source"],
                "target": reviewed["target"],
                "category": "reviewed",
                "locked": True,
                "status": "auto-locked",
                "reviewed_chapters": reviewed["chapters"],
            }
            glossary.setdefault("entries", []).append(entry)
            by_source[entry["source"]] = entry
    io.save_json_atomic(path, glossary)


def promote_reviewed(branch_name: str, chapter: int) -> dict[str, Any]:
    branch_dir = io.resolve_branch_dir(branch_name)
    analysis_dir = branch_dir / "analysis"
    terms, queue_terms = aggregate_terms(_read_jsonl(analysis_dir / "term_occurrences.jsonl"))
    names, queue_names = aggregate_terms(_read_jsonl(analysis_dir / "name_mentions.jsonl"), kind="name")
    patterns, queue_patterns = aggregate_patterns(
        _read_jsonl(analysis_dir / "phrase_patterns.jsonl"), "phrase_pattern"
    )
    rules, queue_rules = aggregate_patterns(
        _read_jsonl(analysis_dir / "grammar_rules.jsonl"), "grammar_rule"
    )
    review_queue = queue_terms + queue_names + queue_patterns + queue_rules
    _lock_branch_glossary(branch_dir, terms, review_queue)
    _write_jsonl(analysis_dir / "reviewed_terms.jsonl", terms)
    _write_jsonl(analysis_dir / "reviewed_names.jsonl", names)
    _write_jsonl(analysis_dir / "reviewed_patterns.jsonl", patterns)
    _write_jsonl(analysis_dir / "reviewed_rules.jsonl", rules)
    _write_jsonl(analysis_dir / "promotion_review_queue.jsonl", review_queue)
    report = {
        "chapter": chapter,
        "promoted_terms_count": len(terms),
        "promoted_names_count": len(names),
        "promoted_patterns_count": len(patterns),
        "promoted_rules_count": len(rules),
        "review_queue_count": len(review_queue),
    }
    io.save_json_atomic(analysis_dir / "audit" / f"chapter_{chapter:04d}.promote.json", report)
    LOGGER.info("Promotion report for %s: %s", branch_name, report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Promote reviewed analysis evidence")
    parser.add_argument("--branch", required=True)
    parser.add_argument("--chapter", required=True, type=int)
    args = parser.parse_args()
    print(json.dumps(promote_reviewed(args.branch, args.chapter), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
