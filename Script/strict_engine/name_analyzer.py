#!/usr/bin/env python3
"""Known-first name analyzer for Contract V2 analysis artifacts."""
from __future__ import annotations

from typing import Any


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


def analyze_names(
    aligned_segments: list[dict[str, Any]],
    characters_payload: dict[str, Any] | None = None,
    candidate_items: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    chapter_id = aligned_segments[0]["chapter_id"] if aligned_segments else ""
    target_text = "\n\n".join(item.get("target", "") for item in aligned_segments)
    mentions: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    known = []
    for item in (characters_payload or {}).get("characters", []):
        source = _source_name(item)
        target = _target_name(item)
        if source and target:
            known.append((source, target, 1.0))
    for item in candidate_items or []:
        source = str(item.get("name_source") or "")
        target = str(item.get("name_target") or "")
        if source and target:
            known.append((source, target, float(item.get("confidence", 0.8))))

    for source, target, confidence in known:
        if (source, target) in seen:
            continue
        segment = next(
            (item for item in aligned_segments if source in item.get("source", "")),
            None,
        )
        if not segment:
            continue
        seen.add((source, target))
        mentions.append(
            {
                "chapter_id": chapter_id,
                "name_source": source,
                "name_target": target,
                "segment_id": segment["segment_ids"][0],
                "present_in_target": target in target_text,
                "confidence": confidence,
            }
        )

    mappings: dict[str, set[str]] = {}
    for item in mentions:
        mappings.setdefault(item["name_source"], set()).add(item["name_target"])
    ambiguities = [
        {"name_source": source, "targets": sorted(targets)}
        for source, targets in mappings.items()
        if len(targets) > 1
    ]
    return {
        "status": "ok" if mentions else "no_evidence",
        "evidence_count": len(mentions),
        "name_mentions": mentions,
        "name_entries": [
            {"name_source": source, "name_target": next(iter(targets))}
            for source, targets in mappings.items()
            if len(targets) == 1
        ],
        "transliteration_units": [],
        "inferred_name_rules": [],
        "ambiguity_cases": ambiguities,
        "reusable_name_profile": {
            "mapping_count": len(mappings),
            "has_ambiguity": bool(ambiguities),
        },
    }
