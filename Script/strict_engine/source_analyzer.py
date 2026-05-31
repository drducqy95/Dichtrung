#!/usr/bin/env python3
"""
Source Analyzer — Rule-based entity scanner for Chinese source text.
Scans a chapter for person names, organizations, locations, realm terms,
and technique patterns. Outputs a scan report JSON.

Adapted for Dichtrung mono-repo: reads from Source/Source split/[Name]/.
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

# Resolve imports from strict_engine package
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from utils.io import (  # noqa: E402
    get_logger, load_json, now_iso, save_json_atomic,
    get_source_chapter_path, resolve_branch_dir, ensure_dir,
)
from analysis_contract import (  # noqa: E402
    build_source_manifest,
    normalize_text,
    write_source_manifest,
)

LOGGER = get_logger("source_analyzer")

# ─── Name Detection Data ────────────────────────────────────────────────────

COMMON_SURNAMES = set(
    "赵钱孙李周吴郑王冯陈褚卫蒋沈韩杨朱秦许何吕张孔曹严华金魏陶姜"
    "戚谢邹喻柏水窦章云苏潘葛范彭鲁韦昌马苗凤花方俞任袁柳鲍史唐薛"
    "雷贺倪汤罗毕郝安常乐于时傅皮卞齐康伍余元顾孟平黄和穆萧尹姚邵"
    "汪祁毛禹狄米贝明计伏成戴谈宋茅庞熊纪舒屈项祝董梁杜阮蓝闵席季"
    "麻强贾路江童颜郭钟徐邱骆高夏蔡田樊胡凌霍虞万柯卢莫房裘缪解应"
    "宗丁宣邓郁单杭洪包诸左石崔吉龚程邢裴陆荣翁荀羊惠甄曲家封芮羿"
    "储靳汲邴糜松井段巫焦巴弓牧隗山谷车侯宓蓬全郗班仰秋仲伊宫宁仇"
    "栾暴甘钭厉戎祖武符刘景詹束龙叶幸司韶郜黎蓟薄印宿白怀蒲邰从鄂"
    "索卓蔺屠蒙池乔阴胥能苍双闻谭贡劳逄姬申扶堵冉宰郦雍桑桂濮牛寿"
    "通边扈燕冀郫浦尚农温别庄柴瞿阎充慕连茹习宦艾鱼容向古易慎戈廖"
    "庾终暨居衡步都耿满弘匡国文寇广禄阙东欧殳沃利蔚越夔隆师巩厍聂"
    "晁敖融冷訾辛阚简饶曾毋沙乜养鞠须丰巢关蒯相查后荆红游竺权逯盖"
    "益桓公"
)

COMPOUND_SURNAMES = {
    "欧阳", "司马", "上官", "东方", "独孤", "南宫",
    "诸葛", "慕容", "夏侯", "尉迟",
}

ORG_SUFFIXES = (
    "宗", "门", "派", "宫", "阁", "山庄", "学院",
    "大学", "公司", "集团", "堂", "盟", "教", "会",
    "帮", "组织", "团", "部", "科", "局",
)

LOCATION_SUFFIXES = (
    "山", "峰", "谷", "城", "镇", "村", "州", "郡",
    "海", "湖", "殿", "域", "区", "国", "岭", "河",
    "岛", "林", "原",
)

REALM_TERMS = (
    "炼气", "练气", "筑基", "金丹", "元婴", "化神",
    "炼虚", "合体", "大乘", "渡劫",
)

PUNCT_RE = re.compile(
    "[，。！？；：\u201c\u201d\u2018\u2019、（）《》〈〉【】…,.!?;:\\s]+"
)


# ─── Data Structures ────────────────────────────────────────────────────────

@dataclass
class EntityCandidate:
    """A detected entity candidate from source text."""
    source: str
    entity_type: str
    count: int
    confidence: float
    evidence: list[str]


# ─── Text Helpers ───────────────────────────────────────────────────────────

def is_cjk(ch: str) -> bool:
    """Check if a character is in CJK Unified Ideographs range."""
    return "\u4e00" <= ch <= "\u9fff"


# ─── Name Scanner ───────────────────────────────────────────────────────────

def scan_person_names(
    text: str, min_hits: int = 2
) -> list[EntityCandidate]:
    """Scan text for Chinese person names using surname heuristics."""
    counts: Counter[str] = Counter()
    evidence: dict[str, list[str]] = {}

    for idx in range(len(text)):
        surname_len = 0
        if text[idx:idx + 2] in COMPOUND_SURNAMES:
            surname_len = 2
        elif text[idx] in COMMON_SURNAMES:
            surname_len = 1
        if not surname_len:
            continue

        for total_len in (surname_len + 1, surname_len + 2):
            cand = text[idx:idx + total_len]
            if len(cand) != total_len:
                continue
            if not all(is_cjk(ch) for ch in cand):
                continue

            # Check character after name for boundary
            after = text[idx + total_len:idx + total_len + 1]
            if after and after not in "，。！？；：""''、（） 《》\n\t 说问看道":
                continue

            counts[cand] += 1
            snippet = text[max(0, idx - 10):min(len(text), idx + total_len + 10)]
            evidence.setdefault(cand, []).append(snippet)

    results = []
    for name, count in counts.items():
        if count < min_hits:
            continue
        conf = 0.70 if len(name) == 2 else 0.82
        results.append(EntityCandidate(
            name, "person", count, conf,
            evidence.get(name, [])[:3]
        ))
    return sorted(results, key=lambda x: (-x.count, x.source))


# ─── Suffix-based Entity Scanner ────────────────────────────────────────────

def scan_entities_by_suffix(
    text: str,
    suffixes: Iterable[str],
    entity_type: str,
    min_len: int = 2,
) -> list[EntityCandidate]:
    """Scan text for entities ending with specific suffixes."""
    found: Counter[str] = Counter()
    evidence: dict[str, list[str]] = {}
    tokens = [t for t in PUNCT_RE.split(text) if t]

    for token in tokens:
        if len(token) >= min_len and any(token.endswith(s) for s in suffixes):
            found[token] += 1

    for token in found:
        pos = text.find(token)
        if pos >= 0:
            evidence[token] = [
                text[max(0, pos - 10):min(len(text), pos + len(token) + 10)]
            ]

    return sorted(
        [
            EntityCandidate(
                token, entity_type, count, 0.78,
                evidence.get(token, [])
            )
            for token, count in found.items()
        ],
        key=lambda x: (-x.count, x.source),
    )


# ─── Known Term Scanner ─────────────────────────────────────────────────────

def scan_known_terms(text: str) -> dict[str, list[str]]:
    """Detect known realm/cultivation terms and technique patterns."""
    realms = [t for t in REALM_TERMS if t in text]
    techniques = sorted({
        m.group(0) for m in re.finditer(
            r"[\u4e00-\u9fff]{2,8}(?:诀|法|掌|拳|剑|刀|印|步|阵|经)",
            text,
        )
    })
    return {"realms": realms, "techniques": techniques[:50]}


# ─── Report Builder ─────────────────────────────────────────────────────────

def build_scan_report(branch_name: str, chapter: int) -> dict[str, Any]:
    """Build a complete scan report for a source chapter.

    Args:
        branch_name: Project branch name (e.g. 'Linh Hon Negary_Hu Minh')
        chapter: Chapter number

    Returns:
        Scan report dict with detected entities
    """
    chapter_path = get_source_chapter_path(branch_name, chapter)
    if chapter_path is None or not chapter_path.exists():
        raise FileNotFoundError(
            f"Source chapter not found: branch={branch_name}, chapter={chapter}"
        )

    text = normalize_text(chapter_path.read_text(encoding="utf-8"))

    # Known state is hard evidence. Heuristic output remains review-only.
    branch_dir = resolve_branch_dir(branch_name)
    glossary = load_json(
        branch_dir / "glossary.json", default={"entries": []}
    ) or {"entries": []}
    glossary_terms = {
        e.get("source"): e.get("target")
        for e in glossary.get("entries", [])
        if e.get("source")
    }
    locked_terms = {
        e.get("source"): e.get("target")
        for e in glossary.get("entries", [])
        if e.get("source") and e.get("locked") is True
    }
    characters_payload = load_json(
        branch_dir / "characters.json", default={"characters": []}
    ) or {"characters": []}
    worldbuilding_payload = load_json(
        branch_dir / "worldbuilding.json", default={}
    ) or {}
    manifest = build_source_manifest(branch_name, chapter, text, chapter_path)

    known_characters = []
    for item in characters_payload.get("characters", []):
        source = (
            item.get("name_source")
            or item.get("source")
            or item.get("name_original")
            or item.get("zh_name")
        )
        if source and source in text:
            known_characters.append(item)

    known_worldbuilding = []
    for section, items in worldbuilding_payload.items():
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            source = item.get("source") or item.get("name_source") or item.get("system_name")
            if source and source in text:
                known_worldbuilding.append({"section": section, **item})

    # Scan for entities
    characters = scan_person_names(text)
    orgs = scan_entities_by_suffix(text, ORG_SUFFIXES, "organization")
    locations = scan_entities_by_suffix(text, LOCATION_SUFFIXES, "location")
    terms = scan_known_terms(text)

    return {
        "schema_version": "2.0",
        "branch": branch_name,
        "chapter": chapter,
        "source_file": str(chapter_path),
        "source_char_count": len(text),
        "source_hash": manifest["source_hash"],
        "source_manifest_hash": manifest["source_manifest_hash"],
        "source_segments": manifest["source_segments"],
        "known_characters": known_characters,
        "known_worldbuilding": known_worldbuilding,
        "heuristic_candidates": {
            "characters": [asdict(x) for x in characters],
            "organizations": [asdict(x) for x in orgs],
            "locations": [asdict(x) for x in locations],
            "techniques": terms["techniques"],
        },
        "realms": terms["realms"],
        "matched_glossary_terms": [
            {"source": s, "target": t}
            for s, t in glossary_terms.items()
            if s in text
        ],
        "matched_locked_terms": [
            {"source": s, "target": t}
            for s, t in locked_terms.items()
            if s in text
        ],
        "structural_hints": {
            "has_dialogue": any(quote in text for quote in ["\"", "“", "”", "「", "」"]),
            "has_western_names": bool(re.search(r"·", text)),
            "estimated_segments": text.count("。") + text.count("！") + text.count("？")
        },
        "generated_at": now_iso(),
    }


def write_scan_report(branch_name: str, chapter: int, report: dict) -> Path:
    """Write scan report to runtime/manifests/."""
    branch_dir = resolve_branch_dir(branch_name)
    target = branch_dir / "runtime" / "manifests" / f"chapter_{chapter:04d}.scan.json"
    save_json_atomic(target, report)
    write_source_manifest(
        branch_name,
        chapter,
        {
            "schema_version": report["schema_version"],
            "branch": report["branch"],
            "chapter": report["chapter"],
            "chapter_id": f"chapter_{chapter:04d}",
            "source_file": report["source_file"],
            "source_hash": report["source_hash"],
            "source_manifest_hash": report["source_manifest_hash"],
            "source_segments": report["source_segments"],
        },
    )
    return target


# ─── CLI ────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Rule-based source analyzer for Dichtrung"
    )
    parser.add_argument(
        "--branch", required=True,
        help="Project branch name (e.g. 'Linh Hon Negary_Hu Minh')"
    )
    parser.add_argument(
        "--chapter", required=True, type=int,
        help="Chapter number to scan"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print report to stdout without writing file"
    )
    args = parser.parse_args()

    report = build_scan_report(args.branch, args.chapter)

    if args.dry_run:
        import json as _json
        sys.stdout.reconfigure(encoding="utf-8")
        print(_json.dumps(report, ensure_ascii=False, indent=2))
    else:
        target = write_scan_report(args.branch, args.chapter, report)
        LOGGER.info("Wrote scan report: %s", target)

    LOGGER.info(
        "Chapter %d: %d chars, %d characters, %d orgs, %d locations, "
        "%d realms, %d techniques, %d locked terms matched",
        args.chapter,
        report["source_char_count"],
        len(report["heuristic_candidates"]["characters"]),
        len(report["heuristic_candidates"]["organizations"]),
        len(report["heuristic_candidates"]["locations"]),
        len(report["realms"]),
        len(report["heuristic_candidates"]["techniques"]),
        len(report["matched_locked_terms"]),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
