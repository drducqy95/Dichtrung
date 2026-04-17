from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT_DIR / "Output"
GLOBAL_STATE_DIR = ROOT_DIR / "Global State"
GLOBAL_GLOSSARY_PATH = GLOBAL_STATE_DIR / "global_glossary.json"
GLOBAL_CHARACTERS_PATH = GLOBAL_STATE_DIR / "global_characters.json"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

CONFIDENCE_RANK = {
    "low": 1,
    "unverified": 1,
    "medium": 2,
    "verified": 3,
    "high": 4,
}


def now_iso() -> str:
    return datetime.now().astimezone().replace(microsecond=0).isoformat()


def load_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return json.loads(json.dumps(default))

    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def dump_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def normalize_confidence(value: Any) -> str:
    if not value:
        return "low"
    normalized = str(value).strip().lower()
    if normalized in {"verified", "high"}:
        return "high"
    if normalized in {"medium"}:
        return "medium"
    return "low"


def confidence_rank(value: str) -> int:
    return CONFIDENCE_RANK.get(value, 0)


def next_id(prefix: str, existing_ids: set[str]) -> str:
    counter = 1
    while True:
        candidate = f"{prefix}_{counter:04d}"
        if candidate not in existing_ids:
            existing_ids.add(candidate)
            return candidate
        counter += 1


def read_project_title(project_dir: Path) -> str:
    config_path = project_dir / "translation_config.json"
    if not config_path.exists():
        return project_dir.name

    try:
        config = load_json(config_path, {})
    except json.JSONDecodeError:
        return project_dir.name

    return str(config.get("project_name") or project_dir.name)


def glossary_default() -> dict[str, Any]:
    return {
        "metadata": {
            "version": "1.0",
            "source_language": "zh",
            "target_language": "vi",
            "last_updated": "",
            "total_entries": 0,
            "source_projects": [],
            "description": "Tổng hợp thuật ngữ dịch thuật từ TẤT CẢ project branch trong repo Dichtrung",
        },
        "entries": [],
    }


def characters_default() -> dict[str, Any]:
    return {
        "metadata": {
            "version": "1.0",
            "last_updated": "",
            "total_characters": 0,
            "source_projects": [],
            "description": "Tổng hợp nhân vật từ TẤT CẢ project branch trong repo Dichtrung",
        },
        "characters": [],
    }


def normalize_notes(*values: Any) -> str:
    parts: list[str] = []
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text and text not in parts:
            parts.append(text)
    return " | ".join(parts)


def iter_glossary_entries(project_dir: Path, project_title: str) -> list[dict[str, Any]]:
    glossary_path = project_dir / "glossary.json"
    if not glossary_path.exists():
        return []

    data = load_json(glossary_path, {"entries": []})
    deduped: dict[str, dict[str, Any]] = {}
    for raw in data.get("entries", []):
        if not isinstance(raw, dict):
            continue

        source_term = raw.get("source_term") or raw.get("source") or raw.get("term")
        target_term = raw.get("target_term") or raw.get("target") or raw.get("name_vi")
        if not source_term or not target_term:
            continue

        normalized = {
            "source_term": str(source_term).strip(),
            "target_term": str(target_term).strip(),
            "category": str(raw.get("category") or "general").strip(),
            "source_project": project_dir.name,
            "project_title": project_title,
            "confidence": normalize_confidence(raw.get("confidence")),
            "notes": normalize_notes(raw.get("notes"), raw.get("context"), raw.get("description")),
            "locked": bool(raw.get("locked", False)),
        }

        existing = deduped.get(normalized["source_term"])
        if existing is None:
            deduped[normalized["source_term"]] = normalized
            continue

        if confidence_rank(normalized["confidence"]) >= confidence_rank(existing["confidence"]):
            existing["target_term"] = normalized["target_term"]
            existing["confidence"] = normalized["confidence"]

        if normalized["category"] and existing.get("category") != normalized["category"]:
            existing["category"] = normalized["category"]

        existing["notes"] = normalize_notes(existing.get("notes"), normalized["notes"])
        existing["locked"] = bool(existing.get("locked") or normalized["locked"])

    return list(deduped.values())


def iter_characters(project_dir: Path, project_title: str) -> list[dict[str, Any]]:
    characters_path = project_dir / "characters.json"
    if not characters_path.exists():
        return []

    data = load_json(characters_path, {"characters": []})
    results: list[dict[str, Any]] = []
    for raw in data.get("characters", []):
        if not isinstance(raw, dict):
            continue

        name_original = raw.get("name_original") or raw.get("term") or raw.get("name") or raw.get("original_name")
        name_translated = (
            raw.get("name_translated")
            or raw.get("name_vi")
            or raw.get("translated_name")
            or raw.get("display_name")
        )
        if not name_original and not name_translated:
            continue

        description = raw.get("description") or raw.get("identity") or raw.get("summary")
        results.append(
            {
                "name_original": str(name_original or "").strip(),
                "name_translated": str(name_translated or "").strip(),
                "gender": str(raw.get("gender") or "khác").strip().lower(),
                "role": str(raw.get("role") or "khác").strip(),
                "description": str(description or "").strip(),
                "first_appearance": str(
                    raw.get("first_appearance") or raw.get("chapter") or raw.get("first_seen") or ""
                ).strip(),
                "notes": normalize_notes(raw.get("notes"), raw.get("cultivation")),
                "source_project": project_dir.name,
                "project_title": project_title,
            }
        )
    return results


def merge_glossary(
    global_glossary: dict[str, Any],
    project_entries: list[dict[str, Any]],
) -> tuple[int, int, int]:
    entries = global_glossary.setdefault("entries", [])
    existing_ids = {entry.get("id") for entry in entries if entry.get("id")}
    by_key = {
        (entry.get("source_term"), entry.get("source_project")): entry
        for entry in entries
        if entry.get("source_term") and entry.get("source_project")
    }

    added = 0
    updated = 0
    kept = 0

    for entry in project_entries:
        key = (entry["source_term"], entry["source_project"])
        current = by_key.get(key)
        if current is None:
            new_entry = {
                "id": next_id("GTERM", existing_ids),
                "source_term": entry["source_term"],
                "target_term": entry["target_term"],
                "category": entry["category"],
                "source_project": entry["source_project"],
                "confidence": entry["confidence"],
                "notes": entry["notes"],
                "locked": entry["locked"],
            }
            entries.append(new_entry)
            by_key[key] = new_entry
            added += 1
            continue

        if current.get("locked"):
            kept += 1
            continue

        changed = False
        if not current.get("target_term") or confidence_rank(entry["confidence"]) >= confidence_rank(
            normalize_confidence(current.get("confidence"))
        ):
            if current.get("target_term") != entry["target_term"]:
                current["target_term"] = entry["target_term"]
                changed = True
            if current.get("confidence") != entry["confidence"]:
                current["confidence"] = entry["confidence"]
                changed = True

        if entry["category"] and current.get("category") != entry["category"]:
            current["category"] = entry["category"]
            changed = True

        merged_notes = normalize_notes(current.get("notes"), entry["notes"])
        if merged_notes != (current.get("notes") or ""):
            current["notes"] = merged_notes
            changed = True

        current["source_project"] = entry["source_project"]
        current["locked"] = bool(current.get("locked", False) or entry["locked"])

        if changed:
            updated += 1
        else:
            kept += 1

    metadata = global_glossary.setdefault("metadata", {})
    metadata["last_updated"] = now_iso()
    metadata["total_entries"] = len(entries)
    metadata["source_projects"] = sorted({entry["source_project"] for entry in entries if entry.get("source_project")})
    return added, updated, kept


def merge_characters(
    global_characters: dict[str, Any],
    project_characters: list[dict[str, Any]],
) -> tuple[int, int]:
    characters = global_characters.setdefault("characters", [])
    existing_ids = {entry.get("id") for entry in characters if entry.get("id")}
    by_key = {
        (
            entry.get("name_original") or entry.get("name_translated"),
            entry.get("source_project"),
        ): entry
        for entry in characters
        if (entry.get("name_original") or entry.get("name_translated")) and entry.get("source_project")
    }

    added = 0
    updated = 0

    for character in project_characters:
        key_name = character["name_original"] or character["name_translated"]
        key = (key_name, character["source_project"])
        current = by_key.get(key)
        if current is None:
            new_character = {
                "id": next_id("GCHAR", existing_ids),
                "source_project": character["source_project"],
                "name_original": character["name_original"],
                "name_translated": character["name_translated"],
                "gender": character["gender"],
                "role": character["role"],
                "description": character["description"],
                "first_appearance": character["first_appearance"],
                "notes": character["notes"],
            }
            characters.append(new_character)
            by_key[key] = new_character
            added += 1
            continue

        changed = False
        for field in ("name_original", "name_translated", "gender", "role", "description", "first_appearance"):
            value = character[field]
            if value and current.get(field) != value:
                current[field] = value
                changed = True

        merged_notes = normalize_notes(current.get("notes"), character["notes"])
        if merged_notes != (current.get("notes") or ""):
            current["notes"] = merged_notes
            changed = True

        if changed:
            updated += 1

    metadata = global_characters.setdefault("metadata", {})
    metadata["last_updated"] = now_iso()
    metadata["total_characters"] = len(characters)
    metadata["source_projects"] = sorted(
        {entry["source_project"] for entry in characters if entry.get("source_project")}
    )
    return added, updated


def write_branch_log(project_dir: Path, lines: list[str]) -> None:
    logs_dir = project_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    log_path = logs_dir / f"sync-state-{timestamp}.log"
    log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def sync_branch(
    project_dir: Path,
    global_glossary: dict[str, Any],
    global_characters: dict[str, Any],
) -> dict[str, Any]:
    project_title = read_project_title(project_dir)
    glossary_entries = iter_glossary_entries(project_dir, project_title)
    characters = iter_characters(project_dir, project_title)

    glossary_added, glossary_updated, glossary_kept = merge_glossary(global_glossary, glossary_entries)
    characters_added, characters_updated = merge_characters(global_characters, characters)

    report_lines = [
        "GLOBAL STATE SYNC HOÀN TẤT",
        f"Branch: {project_dir.name}",
        f"Glossary: +{glossary_added} mới, ~{glossary_updated} cập nhật, ={glossary_kept} giữ nguyên",
        f"Characters: +{characters_added} mới, ~{characters_updated} cập nhật",
    ]
    write_branch_log(project_dir, report_lines)

    return {
        "branch": project_dir.name,
        "glossary_added": glossary_added,
        "glossary_updated": glossary_updated,
        "glossary_kept": glossary_kept,
        "characters_added": characters_added,
        "characters_updated": characters_updated,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Đồng bộ state cục bộ từ Output/ lên Global State/.")
    parser.add_argument(
        "--branch",
        action="append",
        dest="branches",
        help="Tên project branch trong Output/. Có thể dùng nhiều lần. Nếu bỏ qua sẽ sync tất cả.",
    )
    return parser.parse_args()


def resolve_projects(branches: list[str] | None) -> list[Path]:
    if not branches:
        return sorted([path for path in OUTPUT_DIR.iterdir() if path.is_dir()], key=lambda path: path.name.lower())

    available = {path.name: path for path in OUTPUT_DIR.iterdir() if path.is_dir()}
    missing = [branch for branch in branches if branch not in available]
    if missing:
        raise SystemExit(f"Không tìm thấy branch: {', '.join(missing)}")

    return [available[branch] for branch in branches]


def main() -> int:
    args = parse_args()
    projects = resolve_projects(args.branches)

    global_glossary = load_json(GLOBAL_GLOSSARY_PATH, glossary_default())
    global_characters = load_json(GLOBAL_CHARACTERS_PATH, characters_default())

    reports = [sync_branch(project, global_glossary, global_characters) for project in projects]

    dump_json(GLOBAL_GLOSSARY_PATH, global_glossary)
    dump_json(GLOBAL_CHARACTERS_PATH, global_characters)

    for report in reports:
        print(
            f"[{report['branch']}] glossary +{report['glossary_added']}/~{report['glossary_updated']}/={report['glossary_kept']} | "
            f"characters +{report['characters_added']}/~{report['characters_updated']}"
        )

    metadata_glossary = global_glossary.get("metadata", {})
    metadata_characters = global_characters.get("metadata", {})
    print(
        f"Global glossary: {metadata_glossary.get('total_entries', 0)} entries | "
        f"Global characters: {metadata_characters.get('total_characters', 0)} characters"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
