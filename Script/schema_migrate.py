"""
schema_migrate.py
=================
Normalize characters.json, glossary.json, and worldbuilding.json
for ALL Dichtrung branches to the Gold Standard schema (Ác Linh Quốc Gia).

Safe to re-run: idempotent. Existing data is preserved; only missing
fields are backfilled and key names are normalised.

Usage:
  python Script/schema_migrate.py --all                # migrate all
  python Script/schema_migrate.py --branch "Linh Hon Negary_Hu Minh"
  python Script/schema_migrate.py --all --dry-run      # preview only
"""
from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "Output"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SCHEMA_VERSION = "2.0"


# ─────────────────────────────── helpers ────────────────────────────────────

def now_iso() -> str:
    return datetime.now().astimezone().replace(microsecond=0).isoformat()


def load_json(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError) as exc:
        print(f"  [WARN] Cannot parse {path.name}: {exc}")
        return None


def write_json(path: Path, data: Any, dry_run: bool = False) -> None:
    if dry_run:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def first(*values: Any) -> Any:
    """Return first truthy value, or last value (even if falsy)."""
    for v in values[:-1]:
        if v is not None and v != "" and v != [] and v != {}:
            return v
    return values[-1] if values else None


def is_cjk(text: str) -> bool:
    """True if string contains CJK characters — likely the source language."""
    return bool(re.search(r"[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]", str(text or "")))


def next_id(prefix: str, idx: int) -> str:
    return f"{prefix}{idx + 1:04d}"


def is_project_branch(branch_dir: Path) -> bool:
    return (
        branch_dir.is_dir()
        and (branch_dir / "translation_config.json").exists()
        and (branch_dir / "progress.json").exists()
    )


# ═══════════════════════════════════════════════════════════════════════════
#  CHARACTERS.JSON MIGRATION
# ═══════════════════════════════════════════════════════════════════════════

# Gold Schema blank templates
BLANK_APPEARANCE = {"physical": "", "style": "", "distinctive": ""}
BLANK_PERSONALITY = {"traits": [], "speech": ""}
BLANK_CULTIVATION = {
    "primary_system": "",
    "current_realm": "",
    "current_sub_stage": "",
    "notes": "",
}
BLANK_FIRST_APPEARANCE = {"chapter": 0, "context": ""}
BLANK_FACTION = {"current": {}, "history": []}


def _resolve_names(raw: dict[str, Any]) -> tuple[str, str]:
    """Return (name_source, name_target) from any known schema variant."""
    # Detect "names" dict (Sieu Duy style)
    names_obj = raw.get("names")
    if isinstance(names_obj, dict):
        name_source = first(
            names_obj.get("original"),
            names_obj.get("zh"),
            names_obj.get("pinyin"),
            "",
        )
        name_target = first(
            names_obj.get("hanviet"),
            names_obj.get("latin"),
            names_obj.get("vi"),
            "",
        )
        return str(name_source), str(name_target)

    # Priority candidates
    src_candidates = [
        raw.get("name_source"),
        raw.get("name_zh"),
        raw.get("name_original"),
        raw.get("original_name"),
        raw.get("term"),       # Phi Pham style
    ]
    tgt_candidates = [
        raw.get("name_target"),
        raw.get("name_vi"),
        raw.get("name_translated"),
        raw.get("display_name"),
    ]

    name_source = ""
    name_target = ""

    for v in src_candidates:
        if v and isinstance(v, str) and v.strip():
            name_source = v.strip()
            break

    for v in tgt_candidates:
        if v and isinstance(v, str) and v.strip():
            name_target = v.strip()
            break

    # Fallback: generic "name" field — classify by CJK content
    generic_name = str(raw.get("name") or "").strip()
    if generic_name:
        if not name_source and is_cjk(generic_name):
            name_source = generic_name
        elif not name_target and not is_cjk(generic_name):
            name_target = generic_name

    return name_source, name_target


def _resolve_role(raw: dict[str, Any]) -> str:
    role = raw.get("base_archetype") or raw.get("role") or raw.get("roles", "")
    if isinstance(role, list):
        role = role[0] if role else ""
    return str(role).strip().lower()


def _resolve_abilities(raw: dict[str, Any]) -> list:
    abilities = raw.get("abilities") or []
    if isinstance(abilities, list):
        return abilities
    if isinstance(abilities, str) and abilities.strip():
        return [{"name": abilities, "type": "unknown", "description": ""}]
    return []


def _resolve_cultivation(raw: dict[str, Any]) -> dict:
    cult = raw.get("cultivation")
    if not cult:
        return copy.deepcopy(BLANK_CULTIVATION)
    if isinstance(cult, dict):
        # Already has some structure — normalize keys
        return {
            "primary_system": str(cult.get("primary_system") or cult.get("system") or ""),
            "current_realm": str(cult.get("current_realm") or cult.get("realm") or ""),
            "current_sub_stage": str(cult.get("current_sub_stage") or cult.get("stage") or ""),
            "notes": str(cult.get("notes") or cult.get("technique") or ""),
        }
    if isinstance(cult, str):
        return {**copy.deepcopy(BLANK_CULTIVATION), "notes": cult}
    return copy.deepcopy(BLANK_CULTIVATION)


def _resolve_appearance(raw: dict[str, Any]) -> dict:
    existing = raw.get("appearance")
    if isinstance(existing, dict):
        return {
            "physical": str(existing.get("physical") or ""),
            "style": str(existing.get("style") or ""),
            "distinctive": str(existing.get("distinctive") or ""),
        }
    if isinstance(existing, str) and existing.strip():
        return {"physical": existing, "style": "", "distinctive": ""}
    # Try to salvage description/identity as fallback
    desc = str(raw.get("description") or raw.get("identity") or "").strip()
    return {"physical": desc, "style": "", "distinctive": ""}


def _resolve_personality(raw: dict[str, Any]) -> dict:
    existing = raw.get("personality")
    if isinstance(existing, dict):
        traits = existing.get("traits", [])
        return {
            "traits": traits if isinstance(traits, list) else [traits],
            "speech": str(existing.get("speech") or existing.get("speech_style") or ""),
        }
    traits_field = raw.get("traits")
    if isinstance(traits_field, list) and traits_field:
        return {"traits": traits_field, "speech": ""}
    return copy.deepcopy(BLANK_PERSONALITY)


def _resolve_first_appearance(raw: dict[str, Any]) -> dict:
    fa = raw.get("first_appearance")
    if isinstance(fa, dict):
        return {
            "chapter": int(fa.get("chapter") or 0),
            "context": str(fa.get("context") or ""),
        }
    if isinstance(fa, (int, float)):
        return {"chapter": int(fa), "context": ""}
    if isinstance(fa, str) and fa.strip():
        # Try to parse chapter number
        m = re.search(r"\d+", fa)
        return {"chapter": int(m.group()) if m else 0, "context": fa}
    return copy.deepcopy(BLANK_FIRST_APPEARANCE)


def normalise_character_entry(raw: dict[str, Any], idx: int) -> dict[str, Any]:
    """Convert any schema variant into Gold Schema character entry."""
    name_source, name_target = _resolve_names(raw)
    char_id = str(raw.get("id") or next_id("C", idx))
    gender_raw = str(raw.get("gender") or "").strip().lower()
    if gender_raw in {"nam", "male", "m"}:
        gender = "male"
    elif gender_raw in {"nữ", "nu", "female", "f"}:
        gender = "female"
    elif gender_raw in {"neutral", "trung tính"}:
        gender = "neutral"
    else:
        gender = gender_raw or "unknown"

    # Build aliases
    aliases_raw = raw.get("name_aliases") or raw.get("aliases") or []
    if isinstance(aliases_raw, str):
        aliases_raw = [a.strip() for a in aliases_raw.split(",") if a.strip()]
    aliases = list(aliases_raw) if isinstance(aliases_raw, list) else []

    # Notes: merge description + notes + identity into one field
    desc = str(raw.get("description") or raw.get("identity") or raw.get("summary") or "").strip()
    notes_raw = str(raw.get("notes") or "").strip()
    notes = " | ".join(filter(None, [desc, notes_raw])) if notes_raw and notes_raw != desc else desc or notes_raw

    return {
        "id": char_id,
        "name_source": name_source,
        "name_target": name_target,
        "name_aliases": aliases,
        "gender": gender,
        "age_group": str(raw.get("age_group") or ""),
        "social_status": str(raw.get("social_status") or ""),
        "base_archetype": _resolve_role(raw),
        "speech_style": str(raw.get("speech_style") or ""),
        "first_appearance": _resolve_first_appearance(raw),
        "cultivation": _resolve_cultivation(raw),
        "abilities": _resolve_abilities(raw),
        "faction": raw.get("faction") if isinstance(raw.get("faction"), dict) else copy.deepcopy(BLANK_FACTION),
        "achievements": list(raw.get("achievements") or []),
        "status": str(raw.get("status") or "active").strip().lower(),
        "appearance": _resolve_appearance(raw),
        "personality": _resolve_personality(raw),
        "notes": notes,
    }


def migrate_characters(branch_dir: Path, dry_run: bool) -> dict[str, Any]:
    path = branch_dir / "characters.json"
    raw_data = load_json(path)
    if raw_data is None:
        # Create minimal scaffold
        result = {
            "metadata": {
                "version": SCHEMA_VERSION, "schema": "gold",
                "branch": branch_dir.name, "last_updated": now_iso(),
                "total_characters": 0,
            },
            "characters": [],
        }
        write_json(path, result, dry_run)
        return {"file": "characters.json", "status": "created", "count": 0}

    # Unwrap root
    if isinstance(raw_data, list):
        raw_chars = raw_data
        old_metadata = {}
    else:
        raw_chars = raw_data.get("characters", [])
        old_metadata = raw_data.get("metadata", {})

    # Already Gold? Check schema version
    if str(old_metadata.get("schema")) == "gold" and str(old_metadata.get("version")) == SCHEMA_VERSION:
        return {"file": "characters.json", "status": "already_gold", "count": len(raw_chars)}

    migrated = [normalise_character_entry(c, i) for i, c in enumerate(raw_chars) if isinstance(c, dict)]

    result = {
        "metadata": {
            "version": SCHEMA_VERSION,
            "schema": "gold",
            "branch": branch_dir.name,
            "last_updated": now_iso(),
            "total_characters": len(migrated),
            "previous_schema": old_metadata.get("schema") or "legacy",
        },
        "characters": migrated,
    }
    write_json(path, result, dry_run)
    return {"file": "characters.json", "status": "migrated", "count": len(migrated)}


# ═══════════════════════════════════════════════════════════════════════════
#  GLOSSARY.JSON MIGRATION
# ═══════════════════════════════════════════════════════════════════════════

CONFIDENCE_MAP = {
    "verified": "verified", "high": "high", "medium": "medium",
    "low": "low", "unverified": "low", "true": "medium", "": "medium",
}


def normalise_glossary_entry(raw: dict[str, Any], idx: int) -> dict[str, Any]:
    """Convert any glossary schema variant into Gold Schema entry."""
    # Resolve source term (Chinese)
    source = first(
        raw.get("source"),
        raw.get("source_term"),
        raw.get("term_zh"),
        raw.get("term"),           # Ta Trong Binh / legacy
        "",
    )
    # Resolve target term (Vietnamese)
    target = first(
        raw.get("target"),
        raw.get("target_term"),
        raw.get("term_vi"),
        raw.get("definition"),     # Ta Trong Binh: definition = Vietnamese meaning
        raw.get("name_vi"),
        "",
    )
    category = first(
        raw.get("category"),
        raw.get("context"),        # Some schemas use context as category
        "general",
    )
    context = first(raw.get("context"), "")
    # Don't use context as both category and context
    if category == context and category:
        context = ""

    notes = first(raw.get("notes"), raw.get("note"), raw.get("description"), "")
    conf_raw = str(raw.get("confidence") or raw.get("source_target") or "").strip().lower()
    confidence = CONFIDENCE_MAP.get(conf_raw, "medium")
    locked = bool(raw.get("locked", False))
    source_lang = str(raw.get("source_language") or "zh")

    return {
        "source": str(source),
        "source_language": source_lang,
        "target": str(target),
        "category": str(category),
        "context": str(context),
        "confidence": confidence,
        "notes": str(notes),
        "locked": locked,
    }


def migrate_glossary(branch_dir: Path, dry_run: bool) -> dict[str, Any]:
    path = branch_dir / "glossary.json"
    raw_data = load_json(path)
    if raw_data is None:
        result = {
            "metadata": {
                "version": SCHEMA_VERSION, "schema": "gold",
                "branch": branch_dir.name, "last_updated": now_iso(),
                "total_entries": 0,
            },
            "entries": [],
        }
        write_json(path, result, dry_run)
        return {"file": "glossary.json", "status": "created", "count": 0}

    # Unwrap root
    if isinstance(raw_data, list):
        raw_entries = raw_data
        old_metadata = {}
    else:
        raw_entries = raw_data.get("entries", [])
        old_metadata = raw_data.get("metadata", {})

    if str(old_metadata.get("schema")) == "gold" and str(old_metadata.get("version")) == SCHEMA_VERSION:
        return {"file": "glossary.json", "status": "already_gold", "count": len(raw_entries)}

    # Deduplicate by source term while migrating
    seen: set[str] = set()
    migrated: list[dict] = []
    for i, raw in enumerate(raw_entries):
        if not isinstance(raw, dict):
            continue
        entry = normalise_glossary_entry(raw, i)
        key = entry["source"].strip().lower()
        if not key:
            continue
        if key not in seen:
            seen.add(key)
            migrated.append(entry)

    result = {
        "metadata": {
            "version": SCHEMA_VERSION,
            "schema": "gold",
            "branch": branch_dir.name,
            "last_updated": now_iso(),
            "total_entries": len(migrated),
            "previous_schema": old_metadata.get("schema") or "legacy",
        },
        "entries": migrated,
    }
    write_json(path, result, dry_run)
    return {"file": "glossary.json", "status": "migrated", "count": len(migrated)}


# ═══════════════════════════════════════════════════════════════════════════
#  WORLDBUILDING.JSON MIGRATION
# ═══════════════════════════════════════════════════════════════════════════

WORLDBUILDING_SECTIONS = [
    "factions",
    "weapons",
    "techniques",
    "cultivation_systems",
    "cultivation_resources",
    "power_ranking",
    "locations",
    "world_map",
    "relationship_diagrams",
]

WORLDBUILDING_DEFAULTS: dict[str, Any] = {
    "factions": [],
    "weapons": [],
    "techniques": [],
    "cultivation_systems": [],
    "cultivation_resources": [],
    "power_ranking": {
        "last_updated_chapter": 0,
        "notes": "",
        "ranking": [],
    },
    "locations": [],
    "world_map": {
        "description": "",
        "generated": False,
        "image_path": "",
        "last_updated_chapter": 0,
        "readiness_score": 0,
        "scale": "",
    },
    "relationship_diagrams": {
        "character_relationship": [],
        "faction_relationship": [],
        "family_tree": [],
    },
}


def migrate_worldbuilding(branch_dir: Path, dry_run: bool) -> dict[str, Any]:
    path = branch_dir / "worldbuilding.json"
    raw_data = load_json(path)
    if raw_data is None or not isinstance(raw_data, dict):
        write_json(path, copy.deepcopy(WORLDBUILDING_DEFAULTS), dry_run)
        return {"file": "worldbuilding.json", "status": "created", "added_sections": list(WORLDBUILDING_SECTIONS)}

    # Check if already has all required sections
    existing_sections = set(raw_data.keys())
    missing = [s for s in WORLDBUILDING_SECTIONS if s not in existing_sections]

    # Rename legacy keys
    renames: dict[str, str] = {
        "power_system": "cultivation_systems",   # Negary used this
        "artifacts": "weapons",                   # Negary artifacts → weapons
    }
    renamed = []
    for old_key, new_key in renames.items():
        if old_key in raw_data and new_key not in raw_data:
            raw_data[new_key] = raw_data.pop(old_key)
            renamed.append(f"{old_key}→{new_key}")
            missing = [s for s in missing if s != new_key]

    if not missing and not renamed:
        return {"file": "worldbuilding.json", "status": "ok", "added_sections": []}

    # Backfill missing sections with defaults
    for section in missing:
        raw_data[section] = copy.deepcopy(WORLDBUILDING_DEFAULTS[section])

    # Preserve ordering: required sections first, then any extras
    ordered = {s: raw_data[s] for s in WORLDBUILDING_SECTIONS if s in raw_data}
    extras = {k: v for k, v in raw_data.items() if k not in WORLDBUILDING_SECTIONS}
    ordered.update(extras)

    write_json(path, ordered, dry_run)
    return {
        "file": "worldbuilding.json",
        "status": "patched",
        "renamed": renamed,
        "added_sections": missing,
    }


# ═══════════════════════════════════════════════════════════════════════════
#  BRANCH MIGRATION RUNNER
# ═══════════════════════════════════════════════════════════════════════════

def migrate_branch(branch_dir: Path, dry_run: bool) -> list[dict[str, Any]]:
    results = []
    for fn, migrator in [
        ("characters.json", migrate_characters),
        ("glossary.json", migrate_glossary),
        ("worldbuilding.json", migrate_worldbuilding),
    ]:
        try:
            r = migrator(branch_dir, dry_run)
            results.append(r)
        except Exception as exc:  # noqa: BLE001
            results.append({"file": fn, "status": "ERROR", "error": str(exc)})
    return results


def print_results(branch: str, results: list[dict[str, Any]], dry_run: bool) -> None:
    prefix = "[DRY-RUN]" if dry_run else "[OK]"
    for r in results:
        status = r.get("status", "?")
        file = r.get("file", "?")
        if status == "already_gold":
            print(f"  {file}: ✓ already gold schema")
        elif status == "migrated":
            print(f"  {file}: ✓ migrated → {r.get('count', 0)} entries  {prefix}")
        elif status == "created":
            print(f"  {file}: + created (empty)  {prefix}")
        elif status == "patched":
            renamed = r.get("renamed", [])
            added = r.get("added_sections", [])
            print(f"  {file}: ✓ patched — renamed={renamed}, added={added}  {prefix}")
        elif status == "ok":
            print(f"  {file}: ✓ no changes needed")
        elif status == "ERROR":
            print(f"  {file}: ✗ ERROR — {r.get('error')}")


# ═══════════════════════════════════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════════════════════════════════

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Migrate branch state files to Gold Schema v2.0")
    parser.add_argument("--branch", help="Branch name under Output/")
    parser.add_argument("--all", action="store_true", help="Process all branches")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.branch and not args.all:
        raise SystemExit("Cần truyền --branch [Tên] hoặc --all")

    if args.all:
        branches = sorted(p for p in OUTPUT_ROOT.iterdir() if is_project_branch(p))
    else:
        branch_dir = OUTPUT_ROOT / args.branch
        if not branch_dir.exists():
            raise SystemExit(f"Branch không tồn tại: {branch_dir}")
        branches = [branch_dir]

    if args.dry_run:
        print("=== DRY RUN — no files will be written ===\n")

    for branch_dir in branches:
        print(f"\n▸ {branch_dir.name}")
        results = migrate_branch(branch_dir, dry_run=args.dry_run)
        print_results(branch_dir.name, results, dry_run=args.dry_run)

    print("\n✓ Migration complete." if not args.dry_run else "\n✓ Dry-run complete — no changes written.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
