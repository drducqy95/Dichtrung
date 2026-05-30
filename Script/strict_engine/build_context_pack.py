#!/usr/bin/env python3
"""
Context Pack Builder — Assembles the single JSON input for Antigravity AI node.

A context pack is the ONLY input the AI receives during translation. It bundles:
- Project config (genre, name_setting, style)
- Chapter source text
- Macro context (arc, previous summaries, plot threads)
- Dynamic glossary (locked + new + ambiguous terms)
- Relationship graph (pronoun pairs, warnings)
- Worldbuilding notes (factions, techniques, locations...)
- Hard constraints

Adapted for Dichtrung mono-repo: reads from branch state files and
Source/Source split/[Name]/ for chapter content.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from utils.io import (  # noqa: E402
    get_logger, load_json, now_iso, save_json_atomic,
    get_source_chapter_path, resolve_branch_dir,
)

LOGGER = get_logger("build_context_pack")


# ─── Active Character Detection ─────────────────────────────────────────────

def detect_active_characters(
    text: str, characters_payload: dict[str, Any]
) -> list[dict[str, Any]]:
    """Find characters whose source name appears in the chapter text."""
    results = []
    for item in characters_payload.get("characters", []):
        # Support both Dichtrung format (name_original) and dich.md format (source)
        source = (
            item.get("source")
            or item.get("name_original")
            or item.get("zh_name")
        )
        if source and source in text:
            results.append(item)
    return results


# ─── Glossary Filtering ─────────────────────────────────────────────────────

def filter_glossary(
    text: str, glossary_payload: dict[str, Any]
) -> dict[str, list[dict[str, Any]]]:
    """Filter glossary to only terms appearing in this chapter.

    Returns dict with locked_terms, new_terms, ambiguous_terms.
    Dichtrung glossary entries may not have 'locked' field — treat entries
    without 'pending_sync' and without 'locked' as locked by default.
    """
    locked_terms, new_terms, ambiguous_terms = [], [], []

    for entry in glossary_payload.get("entries", []):
        source = str(entry.get("source", ""))
        if not source or source not in text:
            continue

        packed = {
            "source": source,
            "target": entry.get("target"),
            "category": entry.get("category", "other"),
            "note": entry.get("note", ""),
            "locked": bool(entry.get("locked", True)),  # Default locked for existing entries
        }

        if entry.get("pending_sync"):
            new_terms.append(packed)
        elif packed["locked"]:
            locked_terms.append(packed)
        else:
            ambiguous_terms.append(packed)

    return {
        "locked_terms": locked_terms,
        "new_terms": new_terms,
        "ambiguous_terms": ambiguous_terms,
    }


# ─── Pronoun Resolution ─────────────────────────────────────────────────────

def resolve_pronouns(
    text: str,
    pronouns_payload: dict[str, Any],
    active_characters: list[dict[str, Any]],
) -> dict[str, Any]:
    """Resolve pronoun pairs relevant to this chapter.

    Matches based on character IDs or name presence in text.
    """
    active_ids = {
        str(c.get("id") or c.get("char_id") or "")
        for c in active_characters
        if c.get("id") or c.get("char_id")
    }
    active_names = {
        str(c.get("source") or c.get("name_original") or c.get("zh_name") or "")
        for c in active_characters
    }

    pairs = []
    warnings = []

    for pair in pronouns_payload.get("project_pronouns", []):
        speaker = str(pair.get("speaker") or "")
        listener = str(pair.get("listener") or "")
        speaker_name = str(pair.get("speaker_name") or "")
        listener_name = str(pair.get("listener_name") or "")

        # Match by ID
        if active_ids and speaker in active_ids and listener in active_ids:
            pairs.append(pair)
        # Match by name in text
        elif speaker_name and listener_name and speaker_name in text and listener_name in text:
            pairs.append(pair)

    # Validate
    for pair in pairs:
        if pair.get("speaker") == pair.get("listener"):
            warnings.append(
                f"speaker == listener in pronoun pair: {pair}"
            )

    return {
        "pronoun_pairs": pairs,
        "relationship_edges": pronouns_payload.get("relationship_edges", []),
        "warnings": warnings,
    }


# ─── Worldbuilding Filter ───────────────────────────────────────────────────

def filter_worldbuilding(
    text: str, worldbuilding_payload: dict[str, Any]
) -> dict[str, Any]:
    """Filter worldbuilding entries to those mentioned in this chapter."""
    def pick(section: str) -> list[dict[str, Any]]:
        selected = []
        for item in worldbuilding_payload.get(section, []):
            source = (
                item.get("source")
                or item.get("name_source")
                or item.get("system_name")
            )
            if source and source in text:
                selected.append(item)
        return selected

    return {
        "factions": pick("factions"),
        "weapons": pick("weapons"),
        "techniques": pick("techniques"),
        "cultivation_systems": worldbuilding_payload.get("cultivation_systems", []),
        "locations": pick("locations"),
        "cultivation_resources": pick("cultivation_resources"),
    }


# ─── Build Context Pack ─────────────────────────────────────────────────────

def build_context_pack(
    branch_name: str,
    chapter: int,
    summary_limit: int = 5,
) -> dict[str, Any]:
    """Build a complete context pack for AI translation.

    Args:
        branch_name: Project branch name
        chapter: Chapter number
        summary_limit: Max number of previous chapter summaries to include

    Returns:
        Complete context pack dict ready for AI consumption
    """
    branch_dir = resolve_branch_dir(branch_name)

    # Load all state files
    config = load_json(branch_dir / "translation_config.json") or {}
    glossary = load_json(branch_dir / "glossary.json", default={"entries": []}) or {"entries": []}
    pronouns = load_json(branch_dir / "pronouns.json", default={"project_pronouns": []}) or {"project_pronouns": []}
    characters = load_json(branch_dir / "characters.json", default={"characters": []}) or {"characters": []}
    context = load_json(branch_dir / "context.json", default={"chapter_summaries": []}) or {"chapter_summaries": []}
    worldbuilding = load_json(branch_dir / "worldbuilding.json", default={}) or {}

    # Read source chapter
    chapter_path = get_source_chapter_path(branch_name, chapter)
    if chapter_path is None or not chapter_path.exists():
        raise FileNotFoundError(
            f"Source chapter not found: branch={branch_name}, chapter={chapter}"
        )
    source_text = chapter_path.read_text(encoding="utf-8").strip()

    # Detect active characters
    active_characters = detect_active_characters(source_text, characters)

    # Build style context from config
    style_context = config.get("style_context", "")
    if not style_context and config.get("context_note"):
        style_context = config["context_note"]

    # Build hard constraints from config
    hard_constraints = [
        "Dịch đầy đủ, không tóm tắt",
        "Không bỏ câu",
        "Không tự ý thêm tình tiết",
        "Tuân thủ locked glossary",
        "Tuân thủ relationship_graph",
        "Giữ ngữ pháp tiếng Việt tự nhiên",
        "PHẢI điền worldbuilding_updates (factions, locations, techniques, items mới)",
        "PHẢI viết chapter_summary tóm tắt 2-3 câu",
        "PHẢI viết timeline_entry với summary, characters, plot_points",
        "new_characters_discovered PHẢI có đầy đủ: gender, age_group, description chi tiết",
        "Tuân thủ narrator_pronoun_guide khi chọn đại từ ngôi 3",
    ]

    # Add config-specific constraints
    if config.get("sanitization", {}).get("ban_cjk_in_output"):
        hard_constraints.append("Output KHÔNG được chứa ký tự CJK")

    # Add term_rules as constraints if present
    term_rules = config.get("term_rules", {})
    if term_rules.get("notes"):
        hard_constraints.append(f"QUY TẮC THUẬT NGỮ: {term_rules['notes']}")

    # Add forbidden patterns from global config
    style_rules = config.get("style_rules", {})
    for pattern in style_rules.get("forbidden_patterns", []):
        hard_constraints.append(f"CẤM: {pattern}")

    # Assemble context pack
    pack = {
        "schema_version": "1.0",
        "project": {
            "project_name": config.get("project_name", branch_name),
            "source_language": config.get("source_language", "zh"),
            "target_language": config.get("target_language", "vi"),
            "genre": config.get("genre", "general"),
            "sub_genre": config.get("sub_genre", "general"),
            "name_setting": config.get("name_setting", "phien_am"),
            "style_context": style_context,
        },
        "chapter": {
            "chapter_number": chapter,
            "chapter_id": f"chapter-{chapter:04d}",
            "title": chapter_path.stem if chapter_path else f"Chapter {chapter}",
            "source_file": str(chapter_path),
            "source_text": source_text,
            "char_count": len(source_text),
        },
        "macro_context": {
            "current_arc": context.get("current_arc", ""),
            "previous_summaries": context.get("chapter_summaries", [])[-summary_limit:],
            "active_plot_threads": context.get("plot_threads", []),
            "active_characters": [
                c.get("id") or c.get("char_id") or c.get("name_translated", "")
                for c in active_characters
                if c.get("id") or c.get("char_id") or c.get("name_translated")
            ],
        },
        "dynamic_glossary": filter_glossary(source_text, glossary),
        "relationship_graph": resolve_pronouns(
            source_text, pronouns, active_characters
        ),
        "narrator_pronoun_guide": config.get("narrator_pronoun_guide", {}),
        "worldbuilding_notes": filter_worldbuilding(source_text, worldbuilding),
        "hard_constraints": hard_constraints,
        "analysis_instructions": {
            "output_analysis": True,
            "analysis_schema_version": "1.0",
            "required_sections": [
                "aligned_segments", "term_occurrences", "entity_mentions",
                "phrase_patterns", "grammar_rule_candidates", "quality_audit"
            ],
            "segment_rules": [
                "aligned_segments PHẢI chứa TẤT CẢ các câu/đoạn hội thoại trong source_text, KHÔNG chỉ 1 segment mẫu.",
                "Mỗi câu/đoạn riêng biệt trong source = 1 segment riêng biệt với seg_id tuần tự (seg_0001, seg_0002...).",
                "Mỗi segment phải có source (câu gốc), target (câu dịch tương ứng), alignment_type, và narrative_type.",
                "narrative_type: 'narration' cho tự sự, 'dialogue' cho hội thoại có dấu ngoặc kép, 'inner_thought' cho suy nghĩ nội tâm, 'description' cho miêu tả cảnh vật.",
                "Nếu source có N câu thì aligned_segments phải có xấp xỉ N entries. Chấp nhận sai lệch ±10% do merge/split.",
                "segment_coverage trong quality_audit = (số segments thực tế) / (số câu source). Phải >= 0.8 mới đạt."
            ],
            "entity_rules": [
                "entity_mentions PHẢI liệt kê TẤT CẢ các tên nhân vật, địa danh, môn phái, kỹ thuật xuất hiện trong chương.",
                "Mỗi lần xuất hiện đầu tiên của entity mới = 1 entry mới. Nếu entity đã ghi rồi thì bỏ qua.",
                "Ghi confidence: 1.0 nếu mapping rõ ràng, 0.8 nếu suy luận."
            ],
            "term_rules": [
                "term_occurrences PHẢI ghi nhận MỌI thuật ngữ locked hoặc glossary xuất hiện trong chương.",
                "Ghi seg_id của segment mà thuật ngữ xuất hiện LẦN ĐẦU."
            ],
            # To be hydrated with actual reviewed rules in Phase 4
            "reviewed_rules": [],
            "reviewed_patterns": []
        },
        "built_at": now_iso(),
    }

    return pack


# ─── Write Context Pack ─────────────────────────────────────────────────────

def write_context_pack(
    branch_name: str, chapter: int, pack: dict[str, Any]
) -> Path:
    """Write context pack to runtime/context_packs/."""
    branch_dir = resolve_branch_dir(branch_name)
    target = (
        branch_dir / "runtime" / "context_packs"
        / f"chapter_{chapter:04d}.context_pack.json"
    )
    save_json_atomic(target, pack)
    return target


# ─── CLI ────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build context pack for Dichtrung translation"
    )
    parser.add_argument(
        "--branch", required=True,
        help="Project branch name"
    )
    parser.add_argument(
        "--chapter", required=True, type=int,
        help="Chapter number"
    )
    parser.add_argument(
        "--summary-limit", type=int, default=5,
        help="Max previous chapter summaries to include (default: 5)"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print context pack to stdout without writing"
    )
    args = parser.parse_args()

    pack = build_context_pack(
        args.branch, args.chapter,
        summary_limit=args.summary_limit,
    )

    if args.dry_run:
        import json as _json
        # Don't dump full source_text in dry-run — too large
        display = dict(pack)
        ch = dict(display["chapter"])
        ch["source_text"] = ch["source_text"][:200] + "... [TRUNCATED]"
        display["chapter"] = ch
        print(_json.dumps(display, ensure_ascii=False, indent=2))
    else:
        target = write_context_pack(args.branch, args.chapter, pack)
        LOGGER.info("Wrote context pack: %s", target)

    gl = pack["dynamic_glossary"]
    LOGGER.info(
        "Chapter %d: %d chars, %d locked terms, %d new terms, "
        "%d pronoun pairs, %d active characters",
        args.chapter,
        pack["chapter"]["char_count"],
        len(gl["locked_terms"]),
        len(gl["new_terms"]),
        len(pack["relationship_graph"]["pronoun_pairs"]),
        len(pack["macro_context"]["active_characters"]),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
