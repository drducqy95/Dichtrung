#!/usr/bin/env python3
"""
Retroactive Analysis Runner
Runs the analysis module on already-translated chapters to backfill the analysis state.
This simulates the AI generating analysis_result.json based on existing source and output texts.
"""

import argparse
import logging
from pathlib import Path
import json

from utils import io
from validate_analysis import validate_analysis
from update_analysis_state import update_analysis_state

logger = io.get_logger("retroactive_analysis")

def run_retroactive(branch_name: str, start: int, end: int, dry_run: bool = False):
    """
    Simulates the AI's post-flight analysis step for chapters that have already
    been translated but lacked the new analysis pipeline.
    """
    branch_dir = io.resolve_branch_dir(branch_name)
    runtime_dir = branch_dir / "runtime"
    analysis_dir = runtime_dir / "analysis"
    
    if not dry_run:
        io.ensure_dir(analysis_dir)

    success_count = 0
    
    for chapter in range(start, end + 1):
        trans_file = runtime_dir / f"chapter_{chapter:04d}.translation_result.json"
        
        if not trans_file.exists():
            logger.warning(f"Chapter {chapter} translation not found. Skipping.")
            continue
            
        logger.info(f"Processing Chapter {chapter}...")
        
        if dry_run:
            logger.info(f"[DRY-RUN] Would analyze {trans_file.name}")
            continue
            
        # In a real environment, we would call the Antigravity AI here, passing:
        # 1. context_pack.json
        # 2. source.md
        # 3. translation_result.json
        # and asking it to output analysis_result.json.
        
        # Since we are setting up the scaffolding, we generate a mock valid analysis file 
        # to ensure the pipeline runs. 
        # IN PRODUCTION: The AI tool call goes here.
        
        mock_analysis = {
            "schema_version": "1.0",
            "branch": branch_name,
            "chapter": chapter,
            "aligned_segments": [],
            "term_occurrences": [],
            "entity_mentions": [],
            "phrase_patterns": [],
            "grammar_rule_candidates": [],
            "quality_audit": {
                "segment_coverage": 1.0,
                "locked_term_hit_rate": 1.0,
                "cjk_residue_count": 0,
                "paragraph_drift_ratio": 0.0,
                "pronoun_consistency_score": 1.0,
                "warnings": []
            }
        }
        
        analysis_out = analysis_dir / f"chapter_{chapter:04d}.analysis_result.json"
        io.save_json_atomic(analysis_out, mock_analysis)
        
        # Now run the same pipeline steps as in translation_runner
        report = validate_analysis(branch_name, chapter)
        if report.get("passed"):
            update_analysis_state(branch_name, chapter)
            success_count += 1
        else:
            logger.error(f"Validation failed for Chapter {chapter}: {report.get('errors')}")

    logger.info(f"Retroactive analysis complete. Successfully processed {success_count} chapters.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--branch", required=True)
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--end", type=int, required=True)
    parser.add_argument("--dry-run", action="store_true")
    
    args = parser.parse_args()
    run_retroactive(args.branch, args.start, args.end, args.dry_run)
