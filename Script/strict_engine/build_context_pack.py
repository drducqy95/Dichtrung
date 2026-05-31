#!/usr/bin/env python3
"""Build the Contract V2 context pack consumed by the translation node."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from analysis_contract import build_source_manifest, write_source_manifest  # noqa: E402
from utils import io  # noqa: E402

LOGGER = io.get_logger("build_context_pack")


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    items = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            items.append(json.loads(line))
    return items


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


def detect_active_characters(
    text: str, characters_payload: dict[str, Any]
) -> list[dict[str, Any]]:
    """Find Gold Schema and legacy characters mentioned in the source."""
    return [
        item
        for item in characters_payload.get("characters", [])
        if _source_name(item) and _source_name(item) in text
    ]


def filter_glossary(
    text: str,
    glossary_payload: dict[str, Any],
    reviewed_terms: list[dict[str, Any]] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Filter branch glossary and layer reviewed mappings as locked memory."""
    reviewed_map = {
        str(item.get("source") or item.get("source_term")): str(
            item.get("target") or item.get("target_term")
        )
        for item in reviewed_terms or []
        if item.get("source") or item.get("source_term")
    }
    packed_by_source: dict[str, dict[str, Any]] = {}
    for entry in glossary_payload.get("entries", []):
        source = str(entry.get("source") or "")
        if not source or source not in text:
            continue
        reviewed_target = reviewed_map.get(source)
        packed_by_source[source] = {
            "source": source,
            "target": reviewed_target or entry.get("target"),
            "category": entry.get("category", "other"),
            "note": entry.get("note", ""),
            "locked": bool(entry.get("locked") is True or reviewed_target),
        }
    for source, target in reviewed_map.items():
        if source in text and source not in packed_by_source:
            packed_by_source[source] = {
                "source": source,
                "target": target,
                "category": "reviewed",
                "note": "Promoted from distinct-chapter evidence.",
                "locked": True,
            }
    locked_terms = []
    new_terms = []
    ambiguous_terms = []
    for entry in packed_by_source.values():
        if entry["locked"]:
            locked_terms.append(entry)
        else:
            ambiguous_terms.append(entry)
    return {
        "locked_terms": sorted(locked_terms, key=lambda item: item["source"]),
        "new_terms": new_terms,
        "ambiguous_terms": sorted(ambiguous_terms, key=lambda item: item["source"]),
    }


def resolve_pronouns(
    text: str,
    pronouns_payload: dict[str, Any],
    active_characters: list[dict[str, Any]],
) -> dict[str, Any]:
    """Expose explicit pairs and normalized fallback templates."""
    active_ids = {
        str(item.get("id") or item.get("char_id"))
        for item in active_characters
        if item.get("id") or item.get("char_id")
    }
    active_names = {_source_name(item) for item in active_characters}
    pairs = []
    for pair in pronouns_payload.get("project_pronouns", []):
        speaker = str(pair.get("speaker") or "")
        listener = str(pair.get("listener") or "")
        speaker_name = str(pair.get("speaker_name") or "")
        listener_name = str(pair.get("listener_name") or "")
        if (
            (speaker and listener and speaker in active_ids and listener in active_ids)
            or (
                speaker_name
                and listener_name
                and speaker_name in active_names
                and listener_name in active_names
            )
        ):
            pairs.append(pair)
    templates = [
        {
            "id": item.get("id", ""),
            "self_form": item.get("self_form", ""),
            "other_form": item.get("other_form", ""),
            "relationship": item.get("relationship", "neutral"),
            "contexts": item.get("contexts", []),
            "priority": item.get("priority", 0),
        }
        for item in pronouns_payload.get("pronouns", [])
        if item.get("self_form") and item.get("other_form")
    ]
    warnings = [
        f"speaker == listener in pronoun pair: {pair}"
        for pair in pairs
        if pair.get("speaker") == pair.get("listener")
    ]
    return {
        "pronoun_pairs": pairs,
        "pronoun_templates": templates,
        "relationship_edges": pronouns_payload.get("relationship_edges", []),
        "warnings": warnings,
    }


def filter_worldbuilding(
    text: str, worldbuilding_payload: dict[str, Any]
) -> dict[str, Any]:
    def pick(section: str) -> list[dict[str, Any]]:
        return [
            item
            for item in worldbuilding_payload.get(section, [])
            if isinstance(item, dict)
            and (
                item.get("source")
                or item.get("name_source")
                or item.get("system_name")
            )
            and str(
                item.get("source")
                or item.get("name_source")
                or item.get("system_name")
            )
            in text
        ]

    return {
        "factions": pick("factions"),
        "weapons": pick("weapons"),
        "techniques": pick("techniques"),
        "cultivation_systems": worldbuilding_payload.get("cultivation_systems", []),
        "locations": pick("locations"),
        "cultivation_resources": pick("cultivation_resources"),
    }


def _reviewed_memory(branch_dir: Path) -> dict[str, list[dict[str, Any]]]:
    analysis_dir = branch_dir / "analysis"
    return {
        "terms": _load_jsonl(analysis_dir / "reviewed_terms.jsonl"),
        "rules": _load_jsonl(analysis_dir / "reviewed_rules.jsonl"),
        "patterns": _load_jsonl(analysis_dir / "reviewed_patterns.jsonl"),
    }


def build_context_pack(
    branch_name: str,
    chapter: int,
    summary_limit: int = 5,
) -> dict[str, Any]:
    branch_dir = io.resolve_branch_dir(branch_name)
    config = io.load_json(branch_dir / "translation_config.json") or {}
    glossary = io.load_json(branch_dir / "glossary.json", default={"entries": []}) or {"entries": []}
    pronouns = io.load_json(branch_dir / "pronouns.json", default={}) or {}
    characters = io.load_json(branch_dir / "characters.json", default={"characters": []}) or {"characters": []}
    context = io.load_json(branch_dir / "context.json", default={}) or {}
    worldbuilding = io.load_json(branch_dir / "worldbuilding.json", default={}) or {}
    reviewed = _reviewed_memory(branch_dir)

    chapter_path = io.get_source_chapter_path(branch_name, chapter)
    if chapter_path is None or not chapter_path.exists():
        raise FileNotFoundError(
            f"Source chapter not found: branch={branch_name}, chapter={chapter}"
        )
    source_text = chapter_path.read_text(encoding="utf-8").strip()
    manifest = build_source_manifest(branch_name, chapter, source_text, chapter_path)
    write_source_manifest(branch_name, chapter, manifest)
    active_characters = detect_active_characters(source_text, characters)
    current_state = context.get("current_state", {})

    hard_constraints = [
        "Translate the complete source without omissions, summaries, or invented events.",
        "Honor every locked glossary mapping exactly.",
        "Do not emit CJK characters in Vietnamese targets.",
        "Return one target per source segment ID for new translations.",
        "Never echo, rewrite, or normalize source text.",
        "Report every analysis analyzer as status=ok with evidence or status=no_evidence with evidence_count=0.",
    ]
    if config.get("term_rules", {}).get("notes"):
        hard_constraints.append(f"TERM RULES: {config['term_rules']['notes']}")

    return {
        "schema_version": "2.0",
        "project": {
            "project_name": config.get("project_name", branch_name),
            "source_language": config.get("source_language", "zh"),
            "target_language": config.get("target_language", "vi"),
            "genre": config.get("genre", "general"),
            "sub_genre": config.get("sub_genre", "general"),
            "name_setting": config.get("name_setting", "phien_am"),
            "style_context": config.get("style_context") or config.get("context_note", ""),
        },
        "chapter": {
            "chapter_number": chapter,
            "chapter_id": manifest["chapter_id"],
            "title": chapter_path.stem,
            "source_file": str(chapter_path),
            "source_text": source_text,
            "source_hash": manifest["source_hash"],
            "source_manifest_hash": manifest["source_manifest_hash"],
            "source_segments": manifest["source_segments"],
            "char_count": len(source_text),
        },
        "macro_context": {
            "current_arc": context.get("current_arc") or current_state.get("current_arc", ""),
            "previous_summaries": context.get("chapter_summaries", [])[-summary_limit:],
            "active_plot_threads": context.get("plot_threads") or current_state.get("plot_threads", []),
            "active_characters": [
                {
                    "id": item.get("id") or item.get("char_id") or _source_name(item),
                    "name_source": _source_name(item),
                    "name_target": _target_name(item),
                }
                for item in active_characters
            ],
        },
        "dynamic_glossary": filter_glossary(source_text, glossary, reviewed["terms"]),
        "relationship_graph": resolve_pronouns(source_text, pronouns, active_characters),
        "narrator_pronoun_guide": config.get("narrator_pronoun_guide", {}),
        "worldbuilding_notes": filter_worldbuilding(source_text, worldbuilding),
        "hard_constraints": hard_constraints,
        "analysis_instructions": {
            "contract": "translation_result.v2",
            "source_policy": "Return segment IDs and Vietnamese targets only. Source is immutable manifest data.",
            "candidate_policy": "Candidate references must use stable chapter_XXXX:seg_XXXX IDs. Empty analyzers require status=no_evidence and evidence_count=0.",
            "reviewed_rules": reviewed["rules"],
            "reviewed_patterns": reviewed["patterns"],
        },
        "built_at": io.now_iso(),
    }


def write_context_pack(branch_name: str, chapter: int, pack: dict[str, Any]) -> Path:
    target = (
        io.resolve_branch_dir(branch_name)
        / "runtime"
        / "context_packs"
        / f"chapter_{chapter:04d}.context_pack.json"
    )
    io.save_json_atomic(target, pack)
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Contract V2 translation context pack")
    parser.add_argument("--branch", required=True)
    parser.add_argument("--chapter", required=True, type=int)
    parser.add_argument("--summary-limit", type=int, default=5)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    pack = build_context_pack(args.branch, args.chapter, args.summary_limit)
    if args.dry_run:
        display = dict(pack)
        display["chapter"] = dict(pack["chapter"])
        display["chapter"]["source_text"] = display["chapter"]["source_text"][:200] + "..."
        print(json.dumps(display, ensure_ascii=False, indent=2))
    else:
        LOGGER.info("Wrote context pack: %s", write_context_pack(args.branch, args.chapter, pack))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
