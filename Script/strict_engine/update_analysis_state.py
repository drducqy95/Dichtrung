#!/usr/bin/env python3
"""
Updates the branch's analysis state by appending data from analysis_result.json
into continuous JSONL files.
"""

import json
from pathlib import Path
from utils import io

logger = io.get_logger("update_analysis_state")

def append_jsonl(filepath: Path, items: list[dict]):
    """Appends a list of dicts to a JSONL file."""
    if not items:
        return
    io.ensure_dir(filepath.parent)
    with filepath.open("a", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

def update_analysis_state(branch_name: str, chapter: int) -> bool:
    """
    Reads the chapter's analysis result and appends its contents to the
    project's persistent JSONL analysis logs.
    """
    branch_dir = io.resolve_branch_dir(branch_name)
    analysis_runtime_dir = branch_dir / "runtime" / "analysis"
    analysis_file = analysis_runtime_dir / f"chapter_{chapter:04d}.analysis_result.json"

    if not analysis_file.exists():
        logger.warning(f"No analysis result found for {branch_name} chapter {chapter}")
        return False

    data = io.load_json(analysis_file)
    if not data:
        logger.error(f"Failed to load analysis result for {branch_name} chapter {chapter}")
        return False

    output_analysis_dir = branch_dir / "analysis"
    io.ensure_dir(output_analysis_dir)

    # Append arrays to their respective JSONL files
    if "aligned_segments" in data:
        append_jsonl(output_analysis_dir / "aligned_segments.jsonl", data["aligned_segments"])
    
    if "term_occurrences" in data:
        append_jsonl(output_analysis_dir / "term_occurrences.jsonl", data["term_occurrences"])

    if "entity_mentions" in data:
        append_jsonl(output_analysis_dir / "entity_mentions.jsonl", data["entity_mentions"])

    if "phrase_patterns" in data:
        append_jsonl(output_analysis_dir / "phrase_patterns.jsonl", data["phrase_patterns"])

    if "grammar_rule_candidates" in data:
        append_jsonl(output_analysis_dir / "grammar_rules.jsonl", data["grammar_rule_candidates"])

    # Write quality audit as a standalone JSON file per chapter
    if "quality_audit" in data:
        audit_dir = output_analysis_dir / "audit"
        io.ensure_dir(audit_dir)
        audit_file = audit_dir / f"chapter_{chapter:04d}.json"
        io.save_json_atomic(audit_file, data["quality_audit"])
    
    logger.info(f"Updated analysis state for {branch_name} chapter {chapter}")

    # Trigger promotion if chapter is a multiple of 10
    if chapter % 10 == 0:
        logger.info(f"Chapter {chapter} is a multiple of 10. Triggering promote_reviewed.")
        try:
            import promote_reviewed
            promote_reviewed.promote_reviewed(branch_name, chapter)
            
            # Sync to global state after promotion
            try:
                import sync_analysis_global
                sync_analysis_global.sync_analysis_to_global(branch_name)
            except ImportError:
                logger.warning("sync_analysis_global module not yet implemented or importable.")
        except ImportError:
            logger.warning("promote_reviewed module not yet implemented or importable.")
        except Exception as e:
            logger.error(f"Error during promote_reviewed: {e}")

    return True

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--branch", required=True)
    parser.add_argument("--chapter", type=int, required=True)
    args = parser.parse_args()
    
    success = update_analysis_state(args.branch, args.chapter)
    print(f"State update success: {success}")
