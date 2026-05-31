#!/usr/bin/env python3
"""
State Updater — Runs AFTER Postcheck Gate.
Merges the AI's translation results into the project's state files:
1. Writes the final markdown file to output/
2. Appends new_terms_discovered to glossary.json with pending_sync=True
3. Appends new_characters_discovered to characters.json
4. Updates progress.json to mark the chapter as DONE
5. (Optional) Rebuilds compiled reference wikis (Placeholder for future hook)

This script MUTATES the project state.
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
    resolve_branch_dir, get_output_chapter_path,
    write_text_atomic
)

LOGGER = get_logger("update_state")


def update_glossary(branch_dir: Path, new_terms: list[dict]) -> None:
    """Append new terms to glossary.json enforcing Gold Schema v2.0."""
    if not new_terms:
        return
    glossary_path = branch_dir / "glossary.json"
    raw = load_json(glossary_path, {"metadata": {}, "entries": []})

    # Normalise root format (handle legacy list-root files)
    if isinstance(raw, list):
        entries = raw
        metadata = {}
    elif isinstance(raw, dict):
        entries = raw.get("entries", [])
        metadata = raw.get("metadata", {})
    else:
        entries, metadata = [], {}

    # Dedup index: key = source term (lower)
    existing_sources = {str(e.get("source", "")).strip().lower() for e in entries}

    added_count = 0
    for term in new_terms:
        # Accept both legacy key names from AI output
        src = str(
            term.get("source") or term.get("source_term") or term.get("term") or ""
        ).strip()
        tgt = str(
            term.get("target") or term.get("target_term") or term.get("definition") or ""
        ).strip()
        if not src or src.lower() in existing_sources:
            continue

        entry = {
            "source": src,
            "source_language": str(term.get("source_language") or "zh"),
            "target": tgt,
            "category": str(term.get("category") or "general"),
            "context": str(term.get("context") or ""),
            "confidence": str(term.get("confidence") or "medium"),
            "notes": str(term.get("notes") or term.get("note") or ""),
            "locked": bool(term.get("locked", False)),
        }
        entries.append(entry)
        existing_sources.add(src.lower())
        added_count += 1

    if added_count > 0:
        metadata["version"] = "2.0"
        metadata["schema"] = "gold"
        metadata["last_updated"] = now_iso()
        metadata["total_entries"] = len(entries)
        save_json_atomic(glossary_path, {"metadata": metadata, "entries": entries})
        LOGGER.info("Added %d new terms to glossary (Gold Schema).", added_count)


def update_characters(branch_dir: Path, new_chars: list[dict]) -> None:
    """Append new characters to characters.json enforcing Gold Schema v2.0."""
    if not new_chars:
        return
    char_path = branch_dir / "characters.json"
    raw = load_json(char_path, {"metadata": {}, "characters": []})

    # Normalise root format
    if isinstance(raw, list):
        char_list = raw
        metadata = {}
    elif isinstance(raw, dict):
        char_list = raw.get("characters", [])
        metadata = raw.get("metadata", {})
    else:
        char_list, metadata = [], {}

    # Dedup index: key = name_source
    existing_sources = {
        str(c.get("name_source") or c.get("name_original") or c.get("source") or "").strip().lower()
        for c in char_list
    }

    added_count = 0
    for char in new_chars:
        # Accept both legacy and gold key names from AI output
        src = str(
            char.get("name_source") or char.get("name_original") or char.get("source") or ""
        ).strip()
        if not src or src.lower() in existing_sources:
            continue

        tgt = str(
            char.get("name_target") or char.get("name_translated") or char.get("name_vi") or ""
        ).strip()
        gender_raw = str(char.get("gender") or "").strip().lower()
        if gender_raw in {"nam", "male", "m"}: gender = "male"
        elif gender_raw in {"nữ", "nu", "female", "f"}: gender = "female"
        else: gender = gender_raw or "unknown"

        role = str(char.get("base_archetype") or char.get("role") or "secondary").strip().lower()
        description = str(char.get("description") or char.get("identity") or "").strip()

        entry = {
            "id": str(char.get("id") or ""),
            "name_source": src,
            "name_target": tgt,
            "name_aliases": list(char.get("name_aliases") or []),
            "gender": gender,
            "age_group": str(char.get("age_group") or ""),
            "social_status": str(char.get("social_status") or ""),
            "base_archetype": role,
            "speech_style": str(char.get("speech_style") or ""),
            "first_appearance": char.get("first_appearance") or {"chapter": 0, "context": ""},
            "cultivation": char.get("cultivation") or {
                "primary_system": "", "current_realm": "", "current_sub_stage": "", "notes": ""
            },
            "abilities": list(char.get("abilities") or []),
            "faction": char.get("faction") or {"current": {}, "history": []},
            "achievements": list(char.get("achievements") or []),
            "status": str(char.get("status") or "active").lower(),
            "appearance": char.get("appearance") or {"physical": description, "style": "", "distinctive": ""},
            "personality": char.get("personality") or {"traits": [], "speech": ""},
            "notes": str(char.get("notes") or ""),
        }
        char_list.append(entry)
        existing_sources.add(src.lower())
        added_count += 1

    if added_count > 0:
        metadata["version"] = "2.0"
        metadata["schema"] = "gold"
        metadata["last_updated"] = now_iso()
        metadata["total_characters"] = len(char_list)
        save_json_atomic(char_path, {"metadata": metadata, "characters": char_list})
        LOGGER.info("Added %d new characters to characters.json (Gold Schema).", added_count)


def update_progress(branch_dir: Path, chapter: int, title: str) -> None:
    """Mark chapter as DONE in progress.json."""
    progress_path = branch_dir / "progress.json"
    progress = load_json(progress_path)
    if not progress:
        LOGGER.warning("progress.json not found, skipping progress update.")
        return
        
    chapters = progress.get("chapters", [])
    chapter_found = False
    
    for ch in chapters:
        if ch.get("chapter_number") == chapter:
            ch["status"] = "DONE"
            ch["title"] = title
            ch["last_updated"] = now_iso()
            chapter_found = True
            break
            
    if not chapter_found:
        chapters.append({
            "chapter_number": chapter,
            "title": title,
            "status": "DONE",
            "last_updated": now_iso()
        })
        
    # Sort chapters to maintain order
    chapters.sort(key=lambda x: x.get("chapter_number", 0))
    progress["chapters"] = chapters
    
    # Update completed count
    completed_count = sum(1 for c in chapters if c.get("status") == "DONE")
    progress["completed_chapters"] = completed_count
    
    save_json_atomic(progress_path, progress)
    LOGGER.info("Updated progress.json: Chapter %d marked as DONE.", chapter)


def update_worldbuilding(branch_dir: Path, updates: dict) -> None:
    """Merge new worldbuilding entries into worldbuilding.json."""
    if not updates:
        return
    wb_path = branch_dir / "worldbuilding.json"
    wb = load_json(wb_path, default={}) or {}
    
    sections = ["factions", "locations", "techniques", "items", "cultivation_resources"]
    added_count = 0
    
    for section in sections:
        if section not in wb:
            wb[section] = []
        existing_sources = {str(item.get("name_source") or "").strip().lower() for item in wb[section]}
        
        for item in updates.get(section, []):
            src = str(item.get("name_source") or "").strip()
            if not src or src.lower() in existing_sources:
                continue
            wb[section].append(item)
            existing_sources.add(src.lower())
            added_count += 1
            
    if added_count > 0:
        save_json_atomic(wb_path, wb)
        LOGGER.info("Added %d new worldbuilding entries.", added_count)


def update_context(branch_dir: Path, chapter: int, summary: str) -> None:
    """Append chapter_summary to context.json."""
    if not summary:
        return
    ctx_path = branch_dir / "context.json"
    ctx = load_json(ctx_path, default={}) or {}
    
    summaries = ctx.get("chapter_summaries", [])
    
    # Check if this chapter already has a summary
    for entry in summaries:
        if entry.get("chapter") == chapter:
            entry["summary"] = summary
            break
    else:
        summaries.append({"chapter": chapter, "summary": summary})
        
    summaries.sort(key=lambda x: x.get("chapter", 0))
    ctx["chapter_summaries"] = summaries
    
    if "current_state" not in ctx:
        ctx["current_state"] = {}
    ctx["current_state"]["last_major_event"] = summary[:100] + "..." if len(summary) > 100 else summary
    
    save_json_atomic(ctx_path, ctx)
    LOGGER.info("Updated context.json for chapter %d.", chapter)


def update_timeline(branch_dir: Path, timeline_entry: dict) -> None:
    """Append entry to Story-TimeLine.jsonl."""
    if not timeline_entry or not timeline_entry.get("summary"):
        return
        
    tl_path = branch_dir / "Story-TimeLine.jsonl"
    
    import json
    # Read existing entries to prevent duplication
    existing_chapters = set()
    if tl_path.exists():
        with open(tl_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip(): continue
                try:
                    data = json.loads(line)
                    if "chapter" in data:
                        existing_chapters.add(data["chapter"])
                except json.JSONDecodeError:
                    pass
                    
    chapter = timeline_entry.get("chapter")
    if chapter in existing_chapters:
        LOGGER.info("Timeline entry for chapter %d already exists, skipping.", chapter)
        return
        
    if "timestamp" not in timeline_entry:
        timeline_entry["timestamp"] = now_iso()
        
    # Append
    with open(tl_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(timeline_entry, ensure_ascii=False) + "\n")
    LOGGER.info("Appended timeline entry for chapter %d.", chapter)


def update_state(branch_name: str, chapter: int) -> bool:
    """Execute state update based on translation result."""
    branch_dir = resolve_branch_dir(branch_name)
    result_path = branch_dir / "runtime" / f"chapter_{chapter:04d}.translation_result.json"
    
    if not result_path.exists():
        LOGGER.error("Translation result not found: %s", result_path)
        return False
        
    result = load_json(result_path)
    if not result:
        LOGGER.error("Translation result is empty or invalid.")
        return False
        
    # 1. Write Markdown file
    translated_title = result.get("chapter_title_translated", f"Chương {chapter}")
    translated_text = result.get("translated_text", "")
    
    output_md_path = get_output_chapter_path(branch_name, chapter, title=translated_title)
    
    # ── CJK Safety Net (last-resort sanitization before disk write) ──
    _cjk_found = []
    for i, ch in enumerate(translated_text):
        cp = ord(ch)
        if (0x4E00 <= cp <= 0x9FFF or 0x3400 <= cp <= 0x4DBF
                or 0x20000 <= cp <= 0x2A6DF or 0xF900 <= cp <= 0xFAFF
                or 0x2E80 <= cp <= 0x2EFF or 0x2F00 <= cp <= 0x2FDF):
            ctx_start = max(0, i - 10)
            ctx_end = min(len(translated_text), i + 10)
            _cjk_found.append(f"U+{cp:04X} '{ch}' @{i}: ...{translated_text[ctx_start:ctx_end]}...")
    if _cjk_found:
        LOGGER.error(
            "CJK characters detected in ch.%d output (%d chars). State update aborted. Details:\n  %s",
            chapter, len(_cjk_found), "\n  ".join(_cjk_found[:10])
        )
        return False
    # ── End CJK Safety Net ──

    # Format the markdown content
    md_content = f"# Chương {chapter:04d}: {translated_title}\n\n{translated_text}"
    write_text_atomic(output_md_path, md_content)
    LOGGER.info("Wrote markdown output to %s", output_md_path.name)
    
    # 2. Update Glossary
    update_glossary(branch_dir, result.get("new_terms_discovered", []))
    
    # 3. Update Characters
    update_characters(branch_dir, result.get("new_characters_discovered", []))
    
    # 4. Update Progress
    update_progress(branch_dir, chapter, translated_title)
    
    # 5. Update Worldbuilding
    update_worldbuilding(branch_dir, result.get("worldbuilding_updates", {}))
    
    # 6. Update Context
    update_context(branch_dir, chapter, result.get("chapter_summary", ""))
    
    # 7. Update Timeline
    update_timeline(branch_dir, result.get("timeline_entry", {}))
    
    # 8. Re-run branch scaffold to update home.json and ebook metadata
    import subprocess
    try:
        LOGGER.info("Triggering branch_scaffold to update home.json...")
        scaffold_script = ROOT.parent / "branch_scaffold.py"
        subprocess.run(
            [sys.executable, str(scaffold_script), "--branch", branch_name],
            cwd=str(ROOT.parent.parent),
            check=True,
            capture_output=True,
            text=True
        )
        LOGGER.info("branch_scaffold executed successfully.")
    except Exception as e:
        LOGGER.warning("branch_scaffold execution failed: %s", e)
    
    LOGGER.info("State update completed successfully for chapter %d.", chapter)
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="State Updater for Dichtrung translation")
    parser.add_argument("--branch", required=True, help="Project branch name")
    parser.add_argument("--chapter", required=True, type=int, help="Chapter number")
    args = parser.parse_args()

    success = update_state(args.branch, args.chapter)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
