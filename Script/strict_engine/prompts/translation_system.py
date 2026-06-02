#!/usr/bin/env python3
"""
System & User Prompt Builder for AI Translation Node.

Constructs optimised prompts from the context_pack for the mimo-v2.5-pro model
to produce a translation_result.json that passes the postflight gate.
"""
from __future__ import annotations

import json
from typing import Any


# ---------------------------------------------------------------------------
#  Compact helpers – strip bulky fields that waste tokens
# ---------------------------------------------------------------------------

def _compact_glossary(glossary: dict[str, Any]) -> str:
    """Format locked terms as a concise markdown table."""
    locked = glossary.get("locked_terms", [])
    if not locked:
        return "No locked terms for this chapter."
    lines = ["| Source (ZH) | Target (VI) | Category |",
             "|---|---|---|"]
    for t in locked:
        lines.append(f"| {t['source']} | {t['target']} | {t.get('category', '')} |")
    ambiguous = glossary.get("ambiguous_terms", [])
    if ambiguous:
        lines.append("")
        lines.append("Ambiguous terms (use your best judgement):")
        for t in ambiguous:
            lines.append(f"- {t['source']} → {t.get('target', '???')} ({t.get('category', '')})")
    return "\n".join(lines)


def _compact_characters(characters: list[dict[str, Any]]) -> str:
    """Format active characters as a concise list."""
    if not characters:
        return "No active characters detected."
    lines = []
    for c in characters:
        src = c.get("name_source", "")
        tgt = c.get("name_target", "")
        lines.append(f"- {src} → {tgt}")
    return "\n".join(lines)


def _compact_summaries(summaries: list[dict[str, Any]]) -> str:
    """Format previous chapter summaries compactly."""
    if not summaries:
        return "No previous summaries available."
    lines = []
    for s in summaries:
        ch = s.get("chapter", "?")
        text = s.get("summary", "")
        # Truncate to keep token budget under control
        if len(text) > 400:
            text = text[:400] + "..."
        lines.append(f"**Ch.{ch}**: {text}")
    return "\n".join(lines)


def _compact_worldbuilding(wb: dict[str, Any]) -> str:
    """Format worldbuilding notes compactly."""
    parts = []
    for section in ("factions", "locations", "techniques", "cultivation_resources"):
        items = wb.get(section, [])
        if items:
            entries = []
            for item in items:
                src = item.get("name_source") or item.get("source", "")
                tgt = item.get("name_target") or item.get("target", "")
                if src and tgt:
                    entries.append(f"{src} → {tgt}")
            if entries:
                parts.append(f"**{section}**: {', '.join(entries)}")
    return "\n".join(parts) if parts else "No worldbuilding notes."


# ---------------------------------------------------------------------------
#  JSON Output Skeleton
# ---------------------------------------------------------------------------

_OUTPUT_SKELETON = '''{
  "schema_version": "2.0",
  "chapter_id": "<<CHAPTER_ID>>",
  "source_manifest_hash": "<<MANIFEST_HASH>>",
  "chapter_title_translated": "<<TRANSLATED TITLE>>",
  "segment_translations": [
    {
      "segment_ids": ["<<SEGMENT_ID>>"],
      "target": "<<FULL TRANSLATED TEXT>>",
      "narrative_type": "narration"
    }
  ],
  "new_terms_discovered": [],
  "new_characters_discovered": [],
  "chapter_summary": "<<SUMMARY IN VIETNAMESE>>",
  "worldbuilding_updates": {
    "factions": [], "locations": [], "techniques": [], "items": [], "cultivation_resources": []
  },
  "timeline_entry": {
    "chapter": <<CHAPTER_NUM>>,
    "title": "<<TITLE>>",
    "summary": "<<SAME AS chapter_summary>>",
    "characters": [
      {"name": "<<NAME>>", "interaction": "<<WHAT THEY DID>>", "is_new": false}
    ],
    "plot_points": ["<<KEY EVENT 1>>", "<<KEY EVENT 2>>"]
  },
  "analysis_candidates": {
    "term_occurrences":        {"status": "ok|no_evidence", "evidence_count": 0, "items": []},
    "entity_mentions":         {"status": "ok|no_evidence", "evidence_count": 0, "items": []},
    "name_mentions":           {"status": "ok|no_evidence", "evidence_count": 0, "items": []},
    "phrase_patterns":         {"status": "ok|no_evidence", "evidence_count": 0, "items": []},
    "grammar_rule_candidates": {"status": "ok|no_evidence", "evidence_count": 0, "items": []}
  }
}'''


# ---------------------------------------------------------------------------
#  Prompt Builders
# ---------------------------------------------------------------------------

def build_system_prompt(context_pack: dict[str, Any]) -> str:
    """Build the system prompt from context_pack data."""
    project = context_pack.get("project", {})
    glossary = context_pack.get("dynamic_glossary", {})
    characters = context_pack.get("macro_context", {}).get("active_characters", [])
    narrator_guide = context_pack.get("narrator_pronoun_guide", "")
    constraints = context_pack.get("hard_constraints", [])
    wb = context_pack.get("worldbuilding_notes", {})

    constraints_text = "\n".join(f"- {c}" for c in constraints)
    glossary_table = _compact_glossary(glossary)
    char_list = _compact_characters(characters)
    wb_text = _compact_worldbuilding(wb)

    system = f"""You are an expert Chinese-to-Vietnamese literary translator specialising in web novel fiction (Western fantasy / wizard genre).

## PROJECT
- Name: {project.get('project_name', 'Unknown')}
- Source: {project.get('source_language', 'zh')} → Target: {project.get('target_language', 'vi')}
- Genre: {project.get('genre', '')} / {project.get('sub_genre', '')}
- Name convention: {project.get('name_setting', 'keep_original')}

## NARRATOR GUIDE
{narrator_guide if isinstance(narrator_guide, str) else json.dumps(narrator_guide, ensure_ascii=False)}

## LOCKED TERMINOLOGY (MUST use exactly)
{glossary_table}

## ACTIVE CHARACTERS (name mapping)
{char_list}

## WORLDBUILDING CONTEXT
{wb_text}

## HARD CONSTRAINTS
{constraints_text}

## CRITICAL RULES
1. You MUST return ONLY a single valid JSON object matching the schema below.
2. Do NOT wrap in markdown code fences. Do NOT add any text before or after the JSON.
3. ABSOLUTELY NO CJK CHARACTERS (Chinese, Japanese, Korean) are allowed in ANY Vietnamese text fields. All text must be fully translated into Vietnamese. Check your output carefully.
4. Keep any chain-of-thought or reasoning extremely concise to save token budget. Focus on outputting the JSON.
5. The "target" field must contain the COMPLETE translation — no omissions, no summaries.
6. Use the EXACT locked terminology mappings provided above.
7. For new_characters_discovered, use "name_original" and "name_translated" fields.
8. For analysis_candidates: if you find evidence, set status="ok" and evidence_count=N>0. If none, set status="no_evidence" and evidence_count=0 with empty items=[].
9. segment_ids must be an array of strings matching pattern "chapter_XXXX:seg_XXXX".
10. source_manifest_hash must be copied EXACTLY from the input.
11. For term_occurrences items: use source_term, target_term, segment_id, category, confidence.
12. For name_mentions items: use name_source, name_target, segment_id, confidence.

## OUTPUT JSON SKELETON
{_OUTPUT_SKELETON}
"""
    return system


def build_user_prompt(context_pack: dict[str, Any]) -> str:
    """Build the user prompt with source text and context."""
    chapter = context_pack.get("chapter", {})
    macro = context_pack.get("macro_context", {})

    chapter_id = chapter.get("chapter_id", "chapter_0000")
    chapter_num = chapter.get("chapter_number", 0)
    manifest_hash = chapter.get("source_manifest_hash", "")
    source_text = chapter.get("source_text", "")

    segments = chapter.get("source_segments", [])
    segment_info = ""
    if segments:
        seg_lines = []
        for seg in segments:
            seg_lines.append(f"- {seg['segment_id']}: {len(seg.get('source', ''))} chars")
        segment_info = "\n".join(seg_lines)

    summaries = _compact_summaries(macro.get("previous_summaries", []))

    user = f"""## TRANSLATION TASK

Translate the following Chinese source text into Vietnamese and return the result as a single JSON object.

### Chapter Info
- chapter_id: {chapter_id}
- chapter_number: {chapter_num}
- source_manifest_hash: {manifest_hash}

### Source Segments
{segment_info}

### Previous Chapter Context
{summaries}

### SOURCE TEXT (translate this completely)
---
{source_text}
---

Return ONLY the JSON translation result. No markdown fences, no explanations."""
    return user


def build_retry_prompt(
    errors: list[str],
    previous_response: str,
    context_pack: dict[str, Any],
) -> str:
    """Build a retry prompt with error feedback."""
    error_list = "\n".join(f"- {e}" for e in errors)

    return f"""Your previous translation attempt had the following errors:

{error_list}

Please fix these issues and return a corrected JSON translation result.
The chapter_id is {context_pack.get('chapter', {}).get('chapter_id', '???')}.
The source_manifest_hash is {context_pack.get('chapter', {}).get('source_manifest_hash', '???')}.

IMPORTANT:
- Return ONLY valid JSON, no markdown fences
- Fix ALL errors listed above
- Keep the complete translation, do not shorten it

Your previous (broken) response started with:
{previous_response[:500]}...

Please provide the corrected complete JSON now."""
