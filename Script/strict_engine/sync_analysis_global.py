#!/usr/bin/env python3
"""Sync reviewed branch analysis to Global State without schema drift."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from utils import io

LOGGER = io.get_logger("sync_analysis_global")


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


def sync_analysis_to_global(branch_name: str) -> dict[str, Any]:
    branch_dir = io.resolve_branch_dir(branch_name)
    analysis_dir = branch_dir / "analysis"
    global_dir = io.GLOBAL_STATE_DIR
    io.ensure_dir(global_dir)
    report = {"synced_terms": 0, "synced_rules": 0, "synced_names": 0, "conflicts": []}

    glossary_path = global_dir / "global_glossary.json"
    with io.file_lock(glossary_path.with_suffix(".lock")):
        glossary = io.load_json(glossary_path, default={"entries": []}) or {"entries": []}
        entries = glossary.setdefault("entries", [])
        by_source: dict[str, list[dict[str, Any]]] = {}
        for item in entries:
            by_source.setdefault(str(item.get("source_term") or ""), []).append(item)
        for reviewed in _read_jsonl(analysis_dir / "reviewed_terms.jsonl"):
            source = reviewed["source"]
            target = reviewed["target"]
            matches = by_source.get(source, [])
            if any(item.get("target_term") != target and item.get("locked") is True for item in matches):
                report["conflicts"].append({"kind": "global_term_conflict", "source": source, "target": target})
                continue
            exact = next((item for item in matches if item.get("target_term") == target), None)
            if exact:
                if exact.get("locked") is not True:
                    exact["locked"] = True
                    exact["status"] = "auto-locked"
                    report["synced_terms"] += 1
            else:
                entry = {
                    "source_term": source,
                    "target_term": target,
                    "category": "reviewed",
                    "locked": True,
                    "status": "auto-locked",
                    "source_project": branch_name,
                    "reviewed_chapters": reviewed.get("chapters", []),
                }
                entries.append(entry)
                by_source.setdefault(source, []).append(entry)
                report["synced_terms"] += 1
        io.save_json_atomic(glossary_path, glossary)

    rules_path = global_dir / "global_grammar_rules.jsonl"
    rules = {item.get("alias"): item for item in _read_jsonl(rules_path) if item.get("alias")}
    for item in _read_jsonl(analysis_dir / "reviewed_rules.jsonl"):
        alias = item["alias"]
        existing = rules.get(alias)
        if existing and (
            existing.get("source_pattern"),
            existing.get("target_pattern"),
        ) != (item.get("source_pattern"), item.get("target_pattern")):
            report["conflicts"].append({"kind": "global_rule_conflict", "alias": alias})
            continue
        if existing != item:
            rules[alias] = item
            report["synced_rules"] += 1
    _write_jsonl(rules_path, sorted(rules.values(), key=lambda item: item["alias"]))

    characters_path = global_dir / "global_characters.json"
    characters_payload = io.load_json(characters_path, default={"characters": []}) or {"characters": []}
    characters = characters_payload.setdefault("characters", [])
    by_name = {str(item.get("name_source") or ""): item for item in characters}
    for item in _read_jsonl(analysis_dir / "reviewed_names.jsonl"):
        source = item["source"]
        target = item["target"]
        existing = by_name.get(source)
        if existing and existing.get("name_target") not in (None, "", target):
            report["conflicts"].append({"kind": "global_name_conflict", "source": source, "target": target})
            continue
        if not existing:
            entry = {
                "name_source": source,
                "name_target": target,
                "locked": True,
                "status": "auto-locked",
                "source_project": branch_name,
            }
            characters.append(entry)
            by_name[source] = entry
            report["synced_names"] += 1
    io.save_json_atomic(characters_path, characters_payload)
    io.save_json_atomic(analysis_dir / "audit" / "global_sync.json", report)
    LOGGER.info("Global sync report for %s: %s", branch_name, report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync reviewed analysis to Global State")
    parser.add_argument("--branch", required=True)
    args = parser.parse_args()
    print(json.dumps(sync_analysis_to_global(args.branch), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
