"""
build_character_prompts.py
==========================
Synthesise character illustration prompts from characters.json for each branch.

Reads characters.json (handles all known schema variants), extracts visual and
personality cues, then produces:
  - ebook/character_manifest.json  (ebook-ready, one entry per character)
  - converter_db/character_profiles.json  (full profiles with portrait + scene prompts)

Integrated automatically by branch_scaffold.py.
Can also be run standalone:
  python Script/build_character_prompts.py --branch "Linh Hon Negary_Hu Minh"
  python Script/build_character_prompts.py --all
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from datetime import datetime
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "Output"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# ── Visual archetype lookup ────────────────────────────────────────────────────
GENDER_LABEL: dict[str, str] = {
    "male": "man",
    "nam": "man",
    "female": "woman",
    "nữ": "woman",
    "nu": "woman",
    "neutral": "androgynous figure",
    "unknown": "figure",
    "khác": "figure",
}

ROLE_VISUAL: dict[str, str] = {
    "protagonist": "heroic aura, determined expression, center of frame",
    "antagonist": "menacing presence, cold calculating eyes, imposing stance",
    "identity": "ethereal, soul-like manifestation, otherworldly",
    "villain": "menacing presence, cold calculating eyes",
    "ally": "loyal bearing, trustworthy expression, supportive posture",
    "secondary": "supporting character, distinct silhouette",
    "side": "background character, unique trait",
    "phụ": "supporting character, distinct silhouette",
    "thần linh": "divine radiance, ethereal glow, god-like presence",
    "spirit": "translucent form, soul energy, spectral aura",
    "deity": "divine radiance, towering presence",
    "elder": "wise elder, weathered features, authoritative bearing",
    "villain_side": "intimidating, sharp features, dark aesthetic",
}

STYLE_MAP: dict[str, str] = {
    "dark fantasy": "dark gothic fantasy art style, oil painting aesthetic, moody lighting",
    "fantasy": "epic fantasy illustration, detailed linework, rich color palette",
    "horror": "horror atmosphere, unsettling shadows, cold desaturated tones",
    "xianxia": "xianxia wuxia art style, flowing robes, mystical qi aura, Chinese ink painting influence",
    "tiên hiệp": "xianxia wuxia art style, flowing robes, mystical qi aura",
    "wizardry": "arcane magic, runic glow, scholarly wizard aesthetic",
    "evolution_scifi": "biopunk sci-fi illustration, organic-mechanical hybrid aesthetic",
    "sáng thế": "cosmic creation art, primordial energy, divine light rays",
    "hồng hoang": "primordial era art style, ancient mythological aesthetic, epic scale",
    "đô thị": "modern urban setting, realistic lighting, cinematic photography style",
    "fanfic": "anime illustration style, clean linework, vibrant colors",
    "sci-fi": "futuristic sci-fi illustration, neon lighting, chrome surfaces",
}


def now_iso() -> str:
    return datetime.now().astimezone().replace(microsecond=0).isoformat()


def load_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError):
        return default


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def is_project_branch(branch_dir: Path) -> bool:
    return (
        branch_dir.is_dir()
        and (branch_dir / "translation_config.json").exists()
        and (branch_dir / "progress.json").exists()
    )


# ── Schema normalisation ──────────────────────────────────────────────────────

def _first(*values: Any) -> str:
    for v in values:
        if isinstance(v, list):
            v = ", ".join(str(i) for i in v if i)
        s = str(v or "").strip()
        if s:
            return s
    return ""


def normalise_character(raw: dict[str, Any], source_project: str) -> dict[str, Any]:
    """Flatten all known schema variants into a canonical dict."""
    name_orig = _first(
        raw.get("name_source"),
        raw.get("name_original"),
        raw.get("name"),
    )
    name_vi = _first(
        raw.get("name_target"),
        raw.get("name_translated"),
        raw.get("display_name"),
    )
    gender_raw = str(raw.get("gender") or "").strip().lower()
    gender = GENDER_LABEL.get(gender_raw, "figure")
    role_raw = str(raw.get("role") or raw.get("base_archetype") or "").strip().lower()

    # appearance block (Ac Linh style)
    appearance_block = raw.get("appearance") or {}
    if isinstance(appearance_block, str):
        appearance_text = appearance_block
    elif isinstance(appearance_block, dict):
        appearance_text = _first(
            appearance_block.get("physical"),
            appearance_block.get("style"),
            appearance_block.get("distinctive"),
        )
    else:
        appearance_text = ""

    # personality block
    personality_block = raw.get("personality") or {}
    if isinstance(personality_block, str):
        personality_text = personality_block
    elif isinstance(personality_block, dict):
        traits = personality_block.get("traits") or []
        personality_text = ", ".join(str(t) for t in traits if t) if traits else ""
    else:
        personality_text = ""

    # abilities
    abilities_block = raw.get("abilities") or []
    if isinstance(abilities_block, list):
        ability_names = [str(a.get("name", a) if isinstance(a, dict) else a) for a in abilities_block[:3]]
        abilities_text = ", ".join(ability_names)
    else:
        abilities_text = str(abilities_block)

    description = _first(raw.get("description"), raw.get("identity"), raw.get("summary"))
    notes = _first(raw.get("notes"), raw.get("cultivation"))
    traits_extra = _first(raw.get("traits"))
    status = str(raw.get("status") or "active").strip().lower()
    first_appearance = _first(raw.get("first_appearance"), raw.get("chapter"), raw.get("first_seen"))

    return {
        "id": raw.get("id") or "",
        "name_original": name_orig,
        "name_translated": name_vi,
        "gender_raw": gender_raw,
        "gender_label": gender,
        "role": role_raw,
        "description": description,
        "appearance": appearance_text,
        "personality": personality_text,
        "abilities": abilities_text,
        "notes": notes,
        "traits": traits_extra,
        "status": status,
        "first_appearance": first_appearance,
        "source_project": source_project,
    }


# ── Prompt synthesis ──────────────────────────────────────────────────────────

def _extract_visual_keywords(text: str) -> list[str]:
    """Pull visually meaningful keywords from a Vietnamese description string."""
    if not text:
        return []
    # Common visual descriptors in Vietnamese
    PATTERNS = [
        (r"tóc\s+(\w+)", "hair {0}"),
        (r"mắt\s+(\w+)", "{0} eyes"),
        (r"cao\s+ráo", "tall slender build"),
        (r"gầy\s+gò", "thin gaunt figure"),
        (r"vạm\s+vỡ|to\s+lớn", "muscular imposing build"),
        (r"già\s+nua|lão\s+già", "elderly aged features"),
        (r"trẻ\s+tuổi|thiếu\s+niên", "youthful appearance"),
        (r"xinh\s+đẹp|diễm\s+lệ|tú\s+lệ", "beautiful striking features"),
        (r"xấu\s+xí|thô\s+kệch", "rugged rough features"),
        (r"áo\s+choàng|long\s+bào", "flowing robes"),
        (r"giáp\s+trụ|áo\s+giáp", "armored warrior attire"),
        (r"mặt\s+nạ", "wearing a mask"),
        (r"sẹo", "scarred face"),
        (r"râu\s+rậm|râu\s+dài", "heavy beard"),
        (r"bào\s+bệnh|gầy\s+yếu|ốm\s+yếu", "frail sickly appearance"),
        (r"linh\s+hồn|tàn\s+hồn|vong\s+hồn", "spectral soul form, translucent ghost-like"),
        (r"Quỷ|ma\s+vương|ác\s+thần", "demonic corrupted appearance, dark aura"),
        (r"thần\s+linh|thần\s+thánh", "divine radiant aura"),
        (r"mầm\s+bệnh|vi\s+khuẩn", "surrounded by swarming black particles"),
        (r"quạ\s+đen|Crow", "surrounded by black crows"),
        (r"băng\s+giá|băng\s+tuyết", "ice crystal aura, frost energy"),
        (r"lửa|hỏa\s+diệm", "flame aura, fire energy"),
        (r"bóng\s+tối|hắc\s+ám", "shadow energy, darkness aura"),
    ]
    keywords = []
    for pattern, template in PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            groups = match.groups()
            kw = template.format(*groups) if groups else template
            keywords.append(kw)
    return keywords[:5]


def get_style_string(style_tags: list[str]) -> str:
    """Map branch style tags to art direction string."""
    for tag in style_tags:
        tag_lower = tag.strip().lower()
        if tag_lower in STYLE_MAP:
            return STYLE_MAP[tag_lower]
        for key, val in STYLE_MAP.items():
            if key in tag_lower:
                return val
    return "high-quality fantasy illustration, detailed character art, cinematic lighting"


def build_portrait_prompt(char: dict[str, Any], style_tags: list[str], book_title: str) -> str:
    """Generate a portrait illustration prompt (head+shoulders or 3/4 shot)."""
    name = char["name_translated"] or char["name_original"] or "the character"
    gender = char["gender_label"]
    role_hint = ROLE_VISUAL.get(char["role"], "distinctive character")
    style = get_style_string(style_tags)
    visual_kws = _extract_visual_keywords(
        " ".join(filter(None, [char["appearance"], char["description"], char["notes"]]))
    )
    visual_detail = ", ".join(visual_kws) if visual_kws else ""

    # Core description
    desc_parts = []
    if char["appearance"]:
        desc_parts.append(char["appearance"][:180])
    elif char["description"]:
        desc_parts.append(char["description"][:180])

    core_desc = ". ".join(desc_parts)

    prompt_parts = [
        f"Portrait of {name}, a {gender} character from '{book_title}'.",
        f"Role: {role_hint}.",
    ]
    if visual_detail:
        prompt_parts.append(f"Visual traits: {visual_detail}.")
    if core_desc:
        prompt_parts.append(f"Character context: {core_desc[:200]}.")
    if char["personality"]:
        prompt_parts.append(f"Personality expressed in pose: {char['personality'][:120]}.")

    prompt_parts += [
        "Composition: bust portrait, 3/4 angle, expressive face.",
        f"Art style: {style}.",
        "High detail, professional illustration, no text or watermarks.",
    ]
    return " ".join(prompt_parts)


def build_scene_prompt(char: dict[str, Any], style_tags: list[str], book_title: str, backdrop: str) -> str:
    """Generate a scene/action illustration prompt (full body in environment)."""
    name = char["name_translated"] or char["name_original"] or "the character"
    gender = char["gender_label"]
    role_hint = ROLE_VISUAL.get(char["role"], "distinctive character")
    style = get_style_string(style_tags)
    visual_kws = _extract_visual_keywords(
        " ".join(filter(None, [char["appearance"], char["description"], char["notes"], char["abilities"]]))
    )
    visual_detail = ", ".join(visual_kws) if visual_kws else ""

    abilities_hint = f"Manifesting power: {char['abilities'][:100]}." if char["abilities"] else ""
    appearance_hint = (char["appearance"] or char["description"] or "")[:200]
    first_app = f"First appears in {char['first_appearance']}." if char["first_appearance"] else ""

    prompt_parts = [
        f"Full-body scene illustration of {name} ({gender}) from '{book_title}'.",
        f"Role: {role_hint}.",
    ]
    if visual_detail:
        prompt_parts.append(f"Visual: {visual_detail}.")
    if appearance_hint:
        prompt_parts.append(f"Description: {appearance_hint}.")
    if abilities_hint:
        prompt_parts.append(abilities_hint)
    if backdrop:
        prompt_parts.append(f"Setting: {backdrop[:180]}.")
    if first_app:
        prompt_parts.append(first_app)
    prompt_parts += [
        f"Art style: {style}.",
        "Dynamic composition, full body visible, dramatic lighting, no text or watermarks.",
    ]
    return " ".join(prompt_parts)


def build_char_prompt_entry(
    char: dict[str, Any],
    style_tags: list[str],
    book_title: str,
    backdrop: str,
) -> dict[str, Any]:
    """Build full prompt entry for a single character."""
    portrait = build_portrait_prompt(char, style_tags, book_title)
    scene = build_scene_prompt(char, style_tags, book_title, backdrop)

    # Illustration slot paths
    slug = re.sub(r"[^a-z0-9]+", "_", (char["name_translated"] or char["name_original"] or "char").lower()).strip("_")
    branch = char["source_project"]
    base = f"Output/{branch}/illustrations/characters"

    return {
        "id": char["id"],
        "name_original": char["name_original"],
        "name_translated": char["name_translated"],
        "gender": char["gender_raw"],
        "role": char["role"],
        "status": char["status"],
        "first_appearance": char["first_appearance"],
        "description_vi": (char["description"] or char["appearance"] or "")[:300],
        "personality": char["personality"][:200] if char["personality"] else "",
        "abilities": char["abilities"][:200] if char["abilities"] else "",
        "illustration": {
            "portrait_prompt": portrait,
            "scene_prompt": scene,
            "portrait_slot": f"{base}/{slug}_portrait.png",
            "scene_slot": f"{base}/{slug}_scene.png",
            "asset_candidates": [],
            "status": "prompt_ready",
        },
    }


# ── Main builder ──────────────────────────────────────────────────────────────

def build_character_prompts(branch_dir: Path) -> dict[str, Any]:
    """Process characters.json for a branch and produce prompt manifests."""
    branch = branch_dir.name

    # Load characters
    char_path = branch_dir / "characters.json"
    raw_data = load_json(char_path, {})
    if isinstance(raw_data, list):
        raw_chars = raw_data
    elif isinstance(raw_data, dict):
        raw_chars = raw_data.get("characters", [])
    else:
        raw_chars = []

    if not raw_chars:
        return {"branch": branch, "total": 0, "characters": []}

    # Load metadata for style + context
    metadata = load_json(branch_dir / "converter_db" / "metadata.json", {})
    style_tags = metadata.get("style_tags") or []
    backdrop = metadata.get("backdrop") or ""
    book_title = metadata.get("display_title") or branch

    # Normalise all characters
    normed = [normalise_character(c, branch) for c in raw_chars if isinstance(c, dict)]

    # Build prompt entries
    entries = [build_char_prompt_entry(c, style_tags, book_title, backdrop) for c in normed]

    # Sort: protagonist first, then by name
    role_order = {"protagonist": 0, "antagonist": 1, "identity": 0}
    entries.sort(key=lambda e: (role_order.get(e["role"], 5), e["name_translated"] or e["name_original"]))

    # Build manifests
    ebook_manifest = {
        "metadata": {
            "branch": branch,
            "book_title": book_title,
            "generated_at": now_iso(),
            "total_characters": len(entries),
            "style_tags": style_tags,
        },
        "characters": [
            {
                "name_translated": e["name_translated"],
                "name_original": e["name_original"],
                "role": e["role"],
                "status": e["status"],
                "first_appearance": e["first_appearance"],
                "portrait_slot": e["illustration"]["portrait_slot"],
                "scene_slot": e["illustration"]["scene_slot"],
                "portrait_prompt": e["illustration"]["portrait_prompt"],
                "scene_prompt": e["illustration"]["scene_prompt"],
                "asset_status": e["illustration"]["status"],
            }
            for e in entries
        ],
    }

    full_profiles = {
        "metadata": {
            "branch": branch,
            "book_title": book_title,
            "generated_at": now_iso(),
            "total_characters": len(entries),
            "style_tags": style_tags,
            "backdrop": backdrop,
        },
        "characters": entries,
    }

    # Write outputs
    write_json(branch_dir / "ebook" / "character_manifest.json", ebook_manifest)
    write_json(branch_dir / "converter_db" / "character_profiles.json", full_profiles)

    return {
        "branch": branch,
        "total": len(entries),
        "ebook_manifest": f"ebook/character_manifest.json",
        "full_profiles": f"converter_db/character_profiles.json",
    }


# ── CLI ───────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Synthesise character illustration prompts from characters.json."
    )
    parser.add_argument("--branch", help="Branch name under Output/")
    parser.add_argument("--all", action="store_true", help="Process all branches")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.branch and not args.all:
        raise SystemExit("Cần truyền --branch [Tên] hoặc --all")

    if args.all:
        branches = sorted(p for p in OUTPUT_ROOT.iterdir() if is_project_branch(p))
    else:
        branches = [OUTPUT_ROOT / args.branch]

    for branch_dir in branches:
        if not is_project_branch(branch_dir):
            print(f"[SKIP] {branch_dir.name}: không phải project branch hợp lệ")
            continue
        result = build_character_prompts(branch_dir)
        print(f"[OK] {result['branch']}: {result['total']} characters → {result.get('ebook_manifest', '-')}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
