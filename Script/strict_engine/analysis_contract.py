#!/usr/bin/env python3
"""Shared Contract V2 helpers for immutable source manifests."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from utils import io

CONTRACT_VERSION = "2.0"
NARRATIVE_TYPES = {"narration", "dialogue", "inner_thought", "description"}
ANALYZER_NAMES = (
    "term_occurrences",
    "entity_mentions",
    "name_mentions",
    "phrase_patterns",
    "grammar_rule_candidates",
)


def normalize_text(text: str) -> str:
    """Normalize line endings while preserving paragraph content."""
    return re.sub(
        r"\n{3,}",
        "\n\n",
        text.replace("\r\n", "\n").replace("\r", "\n"),
    ).strip()


def split_paragraphs(text: str) -> list[str]:
    """Split text into stable paragraph blocks."""
    normalized = normalize_text(text)
    if not normalized:
        return []
    return [part.strip() for part in re.split(r"\n\s*\n", normalized) if part.strip()]


def source_segment_id(chapter: int, index: int) -> str:
    return f"chapter_{chapter:04d}:seg_{index:04d}"


def build_source_manifest(
    branch_name: str,
    chapter: int,
    source_text: str,
    source_file: str | Path,
) -> dict[str, Any]:
    normalized = normalize_text(source_text)
    segments = [
        {
            "segment_id": source_segment_id(chapter, index),
            "source": source,
            "source_hash": io.sha256_text(source),
        }
        for index, source in enumerate(split_paragraphs(normalized), start=1)
    ]
    return {
        "schema_version": CONTRACT_VERSION,
        "branch": branch_name,
        "chapter": chapter,
        "chapter_id": f"chapter_{chapter:04d}",
        "source_file": str(source_file),
        "source_hash": io.sha256_text(normalized),
        "source_manifest_hash": io.sha256_text(
            "\n".join(
                f"{item['segment_id']}:{item['source_hash']}" for item in segments
            )
        ),
        "source_segments": segments,
    }


def manifest_path(branch_name: str, chapter: int) -> Path:
    return (
        io.resolve_branch_dir(branch_name)
        / "runtime"
        / "manifests"
        / f"chapter_{chapter:04d}.source_segments.json"
    )


def write_source_manifest(branch_name: str, chapter: int, manifest: dict) -> Path:
    target = manifest_path(branch_name, chapter)
    io.save_json_atomic(target, manifest)
    return target


def load_source_manifest(branch_name: str, chapter: int) -> dict[str, Any]:
    manifest = io.load_json(manifest_path(branch_name, chapter))
    if not manifest:
        raise FileNotFoundError(
            f"Source segment manifest not found for {branch_name} chapter {chapter}"
        )
    return manifest


def join_targets(segment_translations: list[dict[str, Any]]) -> str:
    return "\n\n".join(
        str(item.get("target", "")).strip()
        for item in segment_translations
        if str(item.get("target", "")).strip()
    )


def source_map(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        item["segment_id"]: item
        for item in manifest.get("source_segments", [])
        if item.get("segment_id")
    }


def analyzer_payload(items: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "status": "ok" if items else "no_evidence",
        "evidence_count": len(items),
        "items": items,
    }


def is_cjk(ch: str) -> bool:
    cp = ord(ch)
    return (
        0x4E00 <= cp <= 0x9FFF
        or 0x3400 <= cp <= 0x4DBF
        or 0x20000 <= cp <= 0x2A6DF
        or 0xF900 <= cp <= 0xFAFF
        or 0x2E80 <= cp <= 0x2EFF
        or 0x2F00 <= cp <= 0x2FDF
    )


def cjk_count(text: str) -> int:
    return sum(1 for ch in text if is_cjk(ch))
