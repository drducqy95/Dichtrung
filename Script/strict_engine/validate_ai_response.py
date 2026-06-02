#!/usr/bin/env python3
"""
AI Response Validator — validates and auto-fixes AI translation output
before it reaches the postflight gate.

Performs:
1. JSON extraction from raw response text
2. JSON schema validation
3. CJK character detection in target fields
4. Segment coverage verification
5. Locked term compliance check
6. Auto-fix for common issues
"""
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Any

import jsonschema

SCHEMA_PATH = Path(__file__).resolve().parent / "schemas" / "translation_result.schema.json"

# CJK Unicode ranges
_CJK_RANGES = [
    (0x4E00, 0x9FFF),    # CJK Unified Ideographs
    (0x3400, 0x4DBF),    # CJK Extension A
    (0x20000, 0x2A6DF),  # CJK Extension B
    (0x2A700, 0x2B73F),  # CJK Extension C
    (0x2B740, 0x2B81F),  # CJK Extension D
    (0xF900, 0xFAFF),    # CJK Compat Ideographs
    (0x3000, 0x303F),    # CJK Symbols
    (0x3040, 0x309F),    # Hiragana
    (0x30A0, 0x30FF),    # Katakana
    (0xFF00, 0xFFEF),    # Halfwidth/Fullwidth Forms
]


def _has_cjk(text: str) -> list[str]:
    """Find CJK characters in text, return list of offending chars."""
    found = []
    for ch in text:
        cp = ord(ch)
        for lo, hi in _CJK_RANGES:
            if lo <= cp <= hi:
                found.append(ch)
                break
    return found


def extract_json(raw_text: str) -> tuple[dict[str, Any] | None, str | None]:
    """
    Extract JSON object from raw AI response text.
    Handles markdown fences, leading/trailing text, etc.
    Returns (parsed_dict, error_message).
    """
    text = raw_text.strip()

    # Remove markdown code fences if present
    if text.startswith("```"):
        # Find the end fence
        lines = text.split("\n")
        # Skip first line (```json or ```)
        start = 1
        end = len(lines)
        for i in range(len(lines) - 1, 0, -1):
            if lines[i].strip().startswith("```"):
                end = i
                break
        text = "\n".join(lines[start:end]).strip()

    # Try direct parse first
    try:
        return json.loads(text), None
    except json.JSONDecodeError:
        pass

    # Try to find JSON object boundaries
    first_brace = text.find("{")
    if first_brace == -1:
        return None, "No JSON object found in response"

    # Find matching closing brace
    depth = 0
    in_string = False
    escape_next = False
    last_brace = -1

    for i in range(first_brace, len(text)):
        ch = text[i]
        if escape_next:
            escape_next = False
            continue
        if ch == "\\":
            escape_next = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                last_brace = i
                break

    if last_brace == -1:
        return None, "Unbalanced braces in JSON response"

    json_str = text[first_brace:last_brace + 1]

    try:
        return json.loads(json_str), None
    except json.JSONDecodeError as e:
        # Try common auto-fixes
        fixed = _auto_fix_json(json_str)
        try:
            return json.loads(fixed), None
        except json.JSONDecodeError:
            return None, f"JSON parse error: {e}"


def _auto_fix_json(text: str) -> str:
    """Attempt to fix common JSON issues from LLM output."""
    # Remove trailing commas before } or ]
    text = re.sub(r",\s*([}\]])", r"\1", text)
    # Fix unescaped newlines inside strings (crude but effective)
    # Replace actual newlines inside strings with \\n
    # This is tricky; skip for now and rely on the model being good
    return text


def validate_schema(data: dict[str, Any]) -> list[str]:
    """Validate against the translation_result schema. Returns list of errors."""
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    errors = []
    try:
        jsonschema.validate(instance=data, schema=schema)
    except jsonschema.ValidationError as e:
        errors.append(f"Schema validation failed: {e.message} at path {list(e.absolute_path)}")
    except jsonschema.SchemaError as e:
        errors.append(f"Schema itself is invalid: {e.message}")
    return errors


def check_cjk_leakage(data: dict[str, Any]) -> list[str]:
    """Check for CJK characters in Vietnamese target fields."""
    errors = []

    # Check segment translations
    for i, seg in enumerate(data.get("segment_translations", [])):
        target = seg.get("target", "")
        cjk_chars = _has_cjk(target)
        if cjk_chars:
            unique = list(set(cjk_chars))[:10]
            errors.append(
                f"CJK leakage in segment_translations[{i}].target: "
                f"found {len(cjk_chars)} CJK chars including {unique}"
            )

    # Check chapter summary
    summary = data.get("chapter_summary", "")
    cjk_chars = _has_cjk(summary)
    if cjk_chars:
        errors.append(f"CJK leakage in chapter_summary: {list(set(cjk_chars))[:5]}")

    # Check chapter title
    title = data.get("chapter_title_translated", "")
    cjk_chars = _has_cjk(title)
    if cjk_chars:
        errors.append(f"CJK leakage in chapter_title_translated: {list(set(cjk_chars))[:5]}")

    # Check timeline entry
    tl = data.get("timeline_entry", {})
    for field in ("title", "summary"):
        val = tl.get(field, "")
        cjk_chars = _has_cjk(val)
        if cjk_chars:
            errors.append(f"CJK leakage in timeline_entry.{field}: {list(set(cjk_chars))[:5]}")

    return errors


def check_segment_coverage(
    data: dict[str, Any],
    context_pack: dict[str, Any],
) -> list[str]:
    """Verify all source segments have translations."""
    errors = []
    expected_ids = set()
    for seg in context_pack.get("chapter", {}).get("source_segments", []):
        expected_ids.add(seg["segment_id"])

    translated_ids = set()
    for seg in data.get("segment_translations", []):
        for sid in seg.get("segment_ids", []):
            translated_ids.add(sid)

    missing = expected_ids - translated_ids
    if missing:
        errors.append(f"Missing segment translations: {sorted(missing)}")

    return errors


def check_manifest_hash(
    data: dict[str, Any],
    context_pack: dict[str, Any],
) -> list[str]:
    """Verify source_manifest_hash matches."""
    expected = context_pack.get("chapter", {}).get("source_manifest_hash", "")
    actual = data.get("source_manifest_hash", "")
    if expected and actual != expected:
        return [f"source_manifest_hash mismatch: expected={expected}, got={actual}"]
    return []


def check_locked_terms(
    data: dict[str, Any],
    context_pack: dict[str, Any],
) -> list[str]:
    """Check that locked glossary terms are used correctly in translation."""
    warnings = []  # Not blocking errors, just warnings
    locked = context_pack.get("dynamic_glossary", {}).get("locked_terms", [])
    if not locked:
        return warnings

    # Collect all target text
    all_target = ""
    for seg in data.get("segment_translations", []):
        all_target += seg.get("target", "") + "\n"

    for term in locked:
        source = term.get("source", "")
        target = term.get("target", "")
        if source and target:
            # Check source text has this term
            source_text = context_pack.get("chapter", {}).get("source_text", "")
            if source in source_text and target not in all_target:
                warnings.append(
                    f"Locked term '{source}' → '{target}' not found in translation output"
                )

    return warnings


def check_analysis_invariants(data: dict[str, Any]) -> list[str]:
    """Check analysis_candidates status/evidence_count/items invariants."""
    errors = []
    candidates = data.get("analysis_candidates", {})
    for analyzer_name, report in candidates.items():
        if not isinstance(report, dict):
            errors.append(f"analysis_candidates.{analyzer_name} is not a dict")
            continue
        status = report.get("status")
        count = report.get("evidence_count", -1)
        items = report.get("items", [])

        if status == "no_evidence":
            if count != 0:
                errors.append(
                    f"analysis_candidates.{analyzer_name}: "
                    f"status=no_evidence but evidence_count={count} (should be 0)"
                )
            if len(items) > 0:
                errors.append(
                    f"analysis_candidates.{analyzer_name}: "
                    f"status=no_evidence but items has {len(items)} entries (should be empty)"
                )
        elif status == "ok":
            if count < 1:
                errors.append(
                    f"analysis_candidates.{analyzer_name}: "
                    f"status=ok but evidence_count={count} (should be >= 1)"
                )
            if len(items) < 1:
                errors.append(
                    f"analysis_candidates.{analyzer_name}: "
                    f"status=ok but items is empty (should have >= 1)"
                )
    return errors


def auto_fix_result(
    data: dict[str, Any],
    context_pack: dict[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    """
    Apply auto-fixes to the translation result.
    Returns (fixed_data, list_of_fixes_applied).
    """
    fixes = []

    # Fix manifest hash
    expected_hash = context_pack.get("chapter", {}).get("source_manifest_hash", "")
    if expected_hash and data.get("source_manifest_hash") != expected_hash:
        data["source_manifest_hash"] = expected_hash
        fixes.append("Fixed source_manifest_hash")

    # Fix schema_version
    if data.get("schema_version") != "2.0":
        data["schema_version"] = "2.0"
        fixes.append("Fixed schema_version to 2.0")

    # Fix chapter_id
    expected_id = context_pack.get("chapter", {}).get("chapter_id", "")
    if expected_id and data.get("chapter_id") != expected_id:
        data["chapter_id"] = expected_id
        fixes.append(f"Fixed chapter_id to {expected_id}")

    # Ensure worldbuilding_updates has all required keys and items are objects
    wb = data.get("worldbuilding_updates", {})
    for key in ("factions", "locations", "techniques", "items", "cultivation_resources"):
        if key not in wb:
            wb[key] = []
            fixes.append(f"Added missing worldbuilding_updates.{key}")
        else:
            # Auto-fix strings to objects
            fixed_list = []
            for item in wb[key]:
                if isinstance(item, str):
                    fixed_list.append({"name_source": item, "name_target": item, "description": ""})
                    fixes.append(f"Auto-fixed string '{item}' to object in worldbuilding_updates.{key}")
                else:
                    fixed_list.append(item)
            wb[key] = fixed_list
    data["worldbuilding_updates"] = wb

    # Fix analysis candidates invariants
    candidates = data.get("analysis_candidates", {})
    for name in ("term_occurrences", "entity_mentions", "name_mentions",
                 "phrase_patterns", "grammar_rule_candidates"):
        if name not in candidates:
            candidates[name] = {"status": "no_evidence", "evidence_count": 0, "items": []}
            fixes.append(f"Added missing analysis_candidates.{name}")
        else:
            report = candidates[name]
            items = report.get("items", [])
            if report.get("status") == "no_evidence":
                if report.get("evidence_count", 0) != 0:
                    report["evidence_count"] = 0
                    fixes.append(f"Fixed {name}.evidence_count to 0")
                if len(items) > 0:
                    report["items"] = []
                    fixes.append(f"Cleared {name}.items for no_evidence status")
            elif report.get("status") == "ok":
                if report.get("evidence_count", 0) != len(items):
                    report["evidence_count"] = len(items)
                    fixes.append(f"Fixed {name}.evidence_count to {len(items)}")
    data["analysis_candidates"] = candidates

    # Fix new_characters_discovered field names and properties
    for char in data.get("new_characters_discovered", []):
        if "name_source" in char and "name_original" not in char:
            char["name_original"] = char.pop("name_source")
            fixes.append("Renamed name_source → name_original in new_characters_discovered")
        if "name_target" in char and "name_translated" not in char:
            char["name_translated"] = char.pop("name_target")
            fixes.append("Renamed name_target → name_translated in new_characters_discovered")
        if "is_new" in char:
            char.pop("is_new")
            fixes.append("Removed invalid property 'is_new' from new_characters_discovered")

    # Ensure timeline_entry.chapter is integer
    tl = data.get("timeline_entry", {})
    if isinstance(tl.get("chapter"), str):
        try:
            tl["chapter"] = int(tl["chapter"])
            fixes.append("Converted timeline_entry.chapter to integer")
        except ValueError:
            pass

    return data, fixes


def validate_ai_response(
    raw_text: str,
    context_pack: dict[str, Any],
) -> tuple[dict[str, Any] | None, list[str], list[str]]:
    """
    Full validation pipeline for AI response.
    Returns (parsed_data_or_none, errors, warnings).
    """
    errors: list[str] = []
    warnings: list[str] = []

    # 1. Extract JSON
    data, parse_error = extract_json(raw_text)
    if data is None:
        return None, [parse_error or "Failed to extract JSON"], warnings

    # 2. Auto-fix common issues
    data, fixes = auto_fix_result(data, context_pack)
    if fixes:
        warnings.extend([f"Auto-fixed: {f}" for f in fixes])

    # 3. Schema validation
    schema_errors = validate_schema(data)
    errors.extend(schema_errors)

    # 4. CJK check
    cjk_errors = check_cjk_leakage(data)
    errors.extend(cjk_errors)

    # 5. Segment coverage
    coverage_errors = check_segment_coverage(data, context_pack)
    errors.extend(coverage_errors)

    # 6. Manifest hash
    hash_errors = check_manifest_hash(data, context_pack)
    errors.extend(hash_errors)

    # 7. Analysis invariants
    analysis_errors = check_analysis_invariants(data)
    errors.extend(analysis_errors)

    # 8. Locked term warnings (non-blocking)
    term_warnings = check_locked_terms(data, context_pack)
    warnings.extend(term_warnings)

    return data, errors, warnings
