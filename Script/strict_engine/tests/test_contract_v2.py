from __future__ import annotations

import hashlib
import json
import sys
from copy import deepcopy
from pathlib import Path

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import analysis_contract
import build_context_pack
import promote_reviewed
import sync_analysis_global
import update_analysis_state
import validate_translation
from utils import io


PROJECT = "Tu Chan Bon Van Nam_Ngoa Nguu Chan Nhan"


def _save(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _empty_candidates() -> dict:
    return {
        name: {"status": "no_evidence", "evidence_count": 0, "items": []}
        for name in analysis_contract.ANALYZER_NAMES
    }


def _base_result(manifest: dict, target: str = "Ban dich") -> dict:
    return {
        "schema_version": "2.0",
        "chapter_id": manifest["chapter_id"],
        "source_manifest_hash": manifest["source_manifest_hash"],
        "chapter_title_translated": "Tieu de",
        "segment_translations": [
            {
                "segment_ids": [item["segment_id"]],
                "target": target,
                "narrative_type": "narration",
            }
            for item in manifest["source_segments"]
        ],
        "new_terms_discovered": [],
        "new_characters_discovered": [],
        "chapter_summary": "",
        "worldbuilding_updates": {
            "factions": [],
            "locations": [],
            "techniques": [],
            "items": [],
            "cultivation_resources": [],
        },
        "timeline_entry": {
            "chapter": manifest["chapter"],
            "title": "",
            "summary": "",
            "characters": [],
            "plot_points": [],
        },
        "analysis_candidates": _empty_candidates(),
    }


@pytest.fixture
def temp_branch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[str, Path, dict]:
    monkeypatch.setattr(io, "OUTPUT_DIR", tmp_path / "Output")
    monkeypatch.setattr(io, "GLOBAL_STATE_DIR", tmp_path / "Global State")
    branch_name = "test_branch"
    branch_dir = io.resolve_branch_dir(branch_name)
    branch_dir.mkdir(parents=True)
    _save(branch_dir / "translation_config.json", {"sanitization": {"ban_cjk_in_output": True}})
    manifest = analysis_contract.build_source_manifest(branch_name, 1, "原文", "source.md")
    analysis_contract.write_source_manifest(branch_name, 1, manifest)
    _save(
        branch_dir / "runtime" / "context_packs" / "chapter_0001.context_pack.json",
        {"dynamic_glossary": {"locked_terms": []}, "chapter": {"source_text": "原文"}},
    )
    return branch_name, branch_dir, manifest


def test_manifest_uses_global_ids_and_source_hashes() -> None:
    manifest = analysis_contract.build_source_manifest("branch", 39, "甲\n\n乙", "source.md")
    assert [item["segment_id"] for item in manifest["source_segments"]] == [
        "chapter_0039:seg_0001",
        "chapter_0039:seg_0002",
    ]
    assert manifest["source_segments"][0]["source_hash"] == io.sha256_text("甲")
    assert "generated_at" not in manifest


def test_translation_schema_enforces_no_evidence_contract(temp_branch: tuple[str, Path, dict]) -> None:
    _, _, manifest = temp_branch
    schema = io.load_json(Path(__file__).parents[1] / "schemas" / "translation_result.schema.json")
    result = _base_result(manifest)
    jsonschema.validate(result, schema)
    broken = deepcopy(result)
    broken["analysis_candidates"]["term_occurrences"]["evidence_count"] = 1
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(broken, schema)


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda result: result.update(source_manifest_hash="0" * 64), "source_manifest_hash"),
        (lambda result: result["segment_translations"].append(deepcopy(result["segment_translations"][0])), "Duplicate"),
        (lambda result: result["segment_translations"][0].update(target="CJK 原"), "CJK"),
    ],
)
def test_translation_gate_rejects_integrity_failures(
    temp_branch: tuple[str, Path, dict],
    mutate,
    message: str,
) -> None:
    branch_name, branch_dir, manifest = temp_branch
    result = _base_result(manifest)
    mutate(result)
    _save(branch_dir / "runtime" / "chapter_0001.translation_result.json", result)
    report = validate_translation.run_validation(branch_name, 1, persist_hydrated=False)
    assert not report["passed"]
    assert any(message in error for error in report["errors"])


def test_locked_term_violation_is_error(temp_branch: tuple[str, Path, dict]) -> None:
    branch_name, branch_dir, manifest = temp_branch
    _save(
        branch_dir / "runtime" / "context_packs" / "chapter_0001.context_pack.json",
        {"dynamic_glossary": {"locked_terms": [{"source": "原文", "target": "Bat buoc"}]}},
    )
    _save(branch_dir / "runtime" / "chapter_0001.translation_result.json", _base_result(manifest))
    report = validate_translation.run_validation(branch_name, 1, persist_hydrated=False)
    assert not report["passed"]
    assert any("Locked term violation" in error for error in report["errors"])


def test_gold_name_source_and_pronoun_templates_are_hydrated() -> None:
    active = build_context_pack.detect_active_characters(
        "李耀登场",
        {"characters": [{"name_source": "李耀", "name_target": "Ly Dieu"}]},
    )
    assert len(active) == 1
    graph = build_context_pack.resolve_pronouns(
        "李耀登场",
        {"pronouns": [{"id": "neutral", "self_form": "toi", "other_form": "anh"}]},
        active,
    )
    assert graph["pronoun_templates"] == [
        {
            "id": "neutral",
            "self_form": "toi",
            "other_form": "anh",
            "relationship": "neutral",
            "contexts": [],
            "priority": 0,
        }
    ]


def test_rebuild_analysis_state_is_idempotent(
    temp_branch: tuple[str, Path, dict],
) -> None:
    branch_name, branch_dir, _ = temp_branch
    _save(
        branch_dir / "runtime" / "analysis" / "chapter_0001.analysis_result.json",
        {
            "chapter": 1,
            "aligned_segments": [{"chapter_id": "chapter_0001", "alignment_id": "a"}],
            "term_occurrences": [],
            "entity_mentions": [],
            "name_analysis": {"name_mentions": []},
            "phrase_patterns": [],
            "grammar_rule_candidates": [],
            "review_queue": [],
            "quality_audit": {"segment_coverage": 1.0},
        },
    )
    update_analysis_state.rebuild_analysis_state(branch_name)
    path = branch_dir / "analysis" / "aligned_segments.jsonl"
    first = hashlib.sha256(path.read_bytes()).hexdigest()
    update_analysis_state.rebuild_analysis_state(branch_name)
    second = hashlib.sha256(path.read_bytes()).hexdigest()
    assert first == second
    assert len(path.read_text(encoding="utf-8").splitlines()) == 1


def test_term_promotion_counts_distinct_chapters() -> None:
    row = {
        "source_term": "甲",
        "target_term": "A",
        "chapter_id": "chapter_0001",
        "present_in_target": True,
    }
    reviewed, _ = promote_reviewed.aggregate_terms([row, row, row])
    assert reviewed == []
    reviewed, _ = promote_reviewed.aggregate_terms(
        [row, {**row, "chapter_id": "chapter_0002"}]
    )
    assert reviewed[0]["evidence_count"] == 2


def test_sync_blocks_conflicting_manual_global_lock(
    temp_branch: tuple[str, Path, dict],
) -> None:
    branch_name, branch_dir, _ = temp_branch
    _save(
        io.GLOBAL_STATE_DIR / "global_glossary.json",
        {"entries": [{"source_term": "甲", "target_term": "Old", "locked": True}]},
    )
    (branch_dir / "analysis").mkdir(exist_ok=True)
    (branch_dir / "analysis" / "reviewed_terms.jsonl").write_text(
        json.dumps({"source": "甲", "target": "New"}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    report = sync_analysis_global.sync_analysis_to_global(branch_name)
    glossary = io.load_json(io.GLOBAL_STATE_DIR / "global_glossary.json")
    assert report["conflicts"]
    assert glossary["entries"] == [{"source_term": "甲", "target_term": "Old", "locked": True}]


def _real_branch() -> Path:
    branch = io.DICHTRUNG_ROOT / "Output" / PROJECT
    if not branch.exists():
        pytest.skip("Tu Chan Bon Van Nam regression branch is not available")
    return branch


@pytest.mark.parametrize("chapter", [23, 34, 39])
def test_regression_source_is_manifest_owned(chapter: int) -> None:
    branch = _real_branch()
    manifest = io.load_json(
        branch / "runtime" / "manifests" / f"chapter_{chapter:04d}.source_segments.json"
    )
    analysis = io.load_json(
        branch / "runtime" / "analysis" / f"chapter_{chapter:04d}.analysis_result.json"
    )
    by_id = {item["segment_id"]: item["source"] for item in manifest["source_segments"]}
    assert analysis["quality_audit"]["invalid_ref_count"] == 0
    assert analysis["quality_audit"]["source_hash_match"] is True
    assert analysis["quality_audit"]["segment_coverage"] == 1.0
    for segment in analysis["aligned_segments"]:
        assert segment["source"] == "\n\n".join(by_id[item] for item in segment["segment_ids"])


def test_regression_chapter_40_context_detects_active_characters() -> None:
    branch = _real_branch()
    pack = io.load_json(branch / "runtime" / "context_packs" / "chapter_0040.context_pack.json")
    assert pack["macro_context"]["active_characters"]
    assert all(item["name_source"] for item in pack["macro_context"]["active_characters"])
