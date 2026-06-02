#!/usr/bin/env python3
"""
Translation Runner Orchestrator — Central CLI for the Strict Translation Engine.
Coordinates the infrastructure scripts around the AI Node.

Commands:
- preflight:  Runs source_analyzer -> build_context_pack -> precheck.
- postflight: Runs validate_translation -> update_state -> state_validator.
- status:     Shows current state of a chapter in the pipeline.

Adapted for Antigravity: The actual "translate" action is performed by the
agent reading the context_pack and writing the translation_result, so this
runner orchestrates the "before" and "after" phases.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from utils.io import get_logger, file_lock, resolve_branch_dir, load_json  # noqa: E402
from source_analyzer import build_scan_report, write_scan_report  # noqa: E402
from build_context_pack import build_context_pack, write_context_pack  # noqa: E402
from precheck import run_precheck, write_precheck_report  # noqa: E402
from validate_translation import run_validation, write_postcheck_report  # noqa: E402
from build_translation_analysis import build_translation_analysis  # noqa: E402
from validate_analysis import validate_analysis  # noqa: E402
from update_analysis_state import update_analysis_state  # noqa: E402
from update_state import update_state  # noqa: E402
from state_validator import run_state_verification, write_statecheck_report  # noqa: E402
from ai_translate import run_ai_translation, test_connection  # noqa: E402

LOGGER = get_logger("runner")


def run_preflight(branch_name: str, chapter: int) -> bool:
    """Run all pre-translation tasks."""
    branch_dir = resolve_branch_dir(branch_name)
    lock_file = branch_dir / "runtime" / "locks" / f"chapter_{chapter:04d}.lock"
    
    with file_lock(lock_file):
        LOGGER.info("Starting PREFLIGHT for chapter %d...", chapter)
        
        # 1. Source Analyzer
        LOGGER.info("1/3 Running Source Analyzer...")
        try:
            scan_report = build_scan_report(branch_name, chapter)
            write_scan_report(branch_name, chapter, scan_report)
        except Exception as e:
            LOGGER.error("Source Analyzer failed: %s", e)
            return False
            
        # 2. Context Pack Builder
        LOGGER.info("2/3 Building Context Pack...")
        try:
            pack = build_context_pack(branch_name, chapter)
            write_context_pack(branch_name, chapter, pack)
        except Exception as e:
            LOGGER.error("Context Pack Builder failed: %s", e)
            return False
            
        # 3. Precheck Gate
        LOGGER.info("3/3 Running Precheck Gate...")
        try:
            precheck_report = run_precheck(branch_name, chapter)
            write_precheck_report(branch_name, chapter, precheck_report)
            
            if not precheck_report.get("passed"):
                LOGGER.error("PREFLIGHT FAILED at Precheck Gate:")
                for err in precheck_report.get("errors", []):
                    LOGGER.error(" - %s", err)
                return False
        except Exception as e:
            LOGGER.error("Precheck Gate failed: %s", e)
            return False
            
        LOGGER.info("PREFLIGHT SUCCESS: Context pack is ready for AI.")
        return True


def run_postflight(branch_name: str, chapter: int) -> bool:
    """Run all post-translation tasks."""
    branch_dir = resolve_branch_dir(branch_name)
    lock_file = branch_dir / "runtime" / "locks" / f"chapter_{chapter:04d}.lock"
    
    with file_lock(lock_file):
        LOGGER.info("Starting POSTFLIGHT for chapter %d...", chapter)
        
        # 1. Validate Translation Core
        LOGGER.info("1/5 Running Translation Core Validation...")
        try:
            postcheck_report = run_validation(branch_name, chapter)
            write_postcheck_report(branch_name, chapter, postcheck_report)
            
            if not postcheck_report.get("passed"):
                LOGGER.error("POSTFLIGHT FAILED at Validation Gate:")
                for err in postcheck_report.get("errors", []):
                    LOGGER.error(" - %s", err)
                return False
            
            for warn in postcheck_report.get("warnings", []):
                LOGGER.warning(" Validation Warning: %s", warn)
        except Exception as e:
            LOGGER.error("Validation Gate failed: %s", e)
            return False
            
        # 2. Build and validate independent analysis before mutating story state.
        LOGGER.info("2/5 Building and validating Analysis Artifact...")
        try:
            build_translation_analysis(branch_name, chapter)
            analysis_report = validate_analysis(branch_name, chapter)
            if not analysis_report.get("passed"):
                LOGGER.error("POSTFLIGHT FAILED at Analysis Gate:")
                for err in analysis_report.get("errors", []):
                    LOGGER.error(" - %s", err)
                return False
        except Exception as e:
            LOGGER.error("Analysis Gate failed: %s", e)
            return False

        # 3. Update State
        LOGGER.info("3/5 Updating Project State...")
        try:
            success = update_state(branch_name, chapter)
            if not success:
                LOGGER.error("POSTFLIGHT FAILED: State update aborted.")
                return False
        except Exception as e:
            LOGGER.error("State Updater failed: %s", e)
            return False
            
        # 4. Rebuild derived analysis state idempotently.
        LOGGER.info("4/5 Rebuilding Derived Analysis State...")
        try:
            if not update_analysis_state(branch_name, chapter):
                LOGGER.error("POSTFLIGHT FAILED: Derived analysis rebuild aborted.")
                return False
        except Exception as e:
            LOGGER.error("Derived Analysis Rebuild failed: %s", e)
            return False

        # 5. State Validator
        LOGGER.info("5/5 Running State Verification Gate...")
        try:
            statecheck_report = run_state_verification(branch_name, chapter)
            write_statecheck_report(branch_name, chapter, statecheck_report)
            
            if not statecheck_report.get("passed"):
                LOGGER.error("POSTFLIGHT FAILED at State Verification Gate:")
                for err in statecheck_report.get("errors", []):
                    LOGGER.error(" - %s", err)
                return False
        except Exception as e:
            LOGGER.error("State Verification Gate failed: %s", e)
            return False
            
        LOGGER.info("POSTFLIGHT SUCCESS: Chapter %d is fully processed and merged.", chapter)
        return True

def run_translate(branch_name: str, chapter: int, dry_run: bool = False) -> bool:
    """Call AI to generate translation_result.json from context_pack."""
    LOGGER.info("Starting TRANSLATE for chapter %d...", chapter)
    result = run_ai_translation(branch_name, chapter, dry_run=dry_run)
    if result:
        LOGGER.info("TRANSLATE SUCCESS: Chapter %d translation generated.", chapter)
        return True
    else:
        LOGGER.error("TRANSLATE FAILED: Chapter %d could not be translated.", chapter)
        return False


def run_full(branch_name: str, chapter: int) -> bool:
    """Full pipeline: preflight -> translate -> postflight."""
    LOGGER.info("="*60)
    LOGGER.info("FULL PIPELINE: Chapter %d", chapter)
    LOGGER.info("="*60)

    # Step 1: Preflight
    if not run_preflight(branch_name, chapter):
        return False

    # Step 2: AI Translate
    if not run_translate(branch_name, chapter):
        return False

    # Step 3: Postflight
    if not run_postflight(branch_name, chapter):
        return False

    LOGGER.info("FULL PIPELINE SUCCESS: Chapter %d completed end-to-end.", chapter)
    return True


def run_batch(
    branch_name: str,
    from_chapter: int,
    to_chapter: int,
) -> bool:
    """Batch pipeline: run full pipeline for a range of chapters."""
    LOGGER.info("BATCH START: Chapters %d-%d", from_chapter, to_chapter)
    results: dict[int, bool] = {}

    for ch in range(from_chapter, to_chapter + 1):
        ok = run_full(branch_name, ch)
        results[ch] = ok
        if not ok:
            LOGGER.error("BATCH: Chapter %d FAILED, continuing...", ch)

    # Summary
    passed = [ch for ch, ok in results.items() if ok]
    failed = [ch for ch, ok in results.items() if not ok]

    LOGGER.info("BATCH COMPLETE: %d passed, %d failed", len(passed), len(failed))
    if passed:
        LOGGER.info("  Passed: %s", passed)
    if failed:
        LOGGER.error("  Failed: %s", failed)

    return len(failed) == 0


def get_status(branch_name: str, chapter: int) -> None:
    """Print the pipeline status of a chapter."""
    branch_dir = resolve_branch_dir(branch_name)
    rt_dir = branch_dir / "runtime"
    
    def check(path: Path) -> str:
        return "YES" if path.exists() else "NO "
        
    print(f"Status for '{branch_name}' Chapter {chapter}:")
    print(f"  Source Manifest:  {check(rt_dir / 'manifests' / f'chapter_{chapter:04d}.scan.json')}")
    print(f"  Segment Manifest: {check(rt_dir / 'manifests' / f'chapter_{chapter:04d}.source_segments.json')}")
    print(f"  Context Pack:     {check(rt_dir / 'context_packs' / f'chapter_{chapter:04d}.context_pack.json')}")
    
    pre = load_json(rt_dir / "gates" / f"chapter_{chapter:04d}.precheck.json")
    if pre:
        print(f"  Precheck Gate:    {'PASS' if pre.get('passed') else 'FAIL'}")
    else:
        print(f"  Precheck Gate:    NO ")
        
    print(f"  AI Result JSON:   {check(rt_dir / f'chapter_{chapter:04d}.translation_result.json')}")
    
    post = load_json(rt_dir / "gates" / f"chapter_{chapter:04d}.postcheck.json")
    if post:
        print(f"  Postcheck Gate:   {'PASS' if post.get('passed') else 'FAIL'}")
    else:
        print(f"  Postcheck Gate:   NO ")

    analysis = rt_dir / "analysis" / f"chapter_{chapter:04d}.analysis_result.json"
    print(f"  Analysis Result:  {check(analysis)}")
        
    state = load_json(rt_dir / "gates" / f"chapter_{chapter:04d}.statecheck.json")
    if state:
        print(f"  State Check Gate: {'PASS' if state.get('passed') else 'FAIL'}")
    else:
        print(f"  State Check Gate: NO ")


def main() -> int:
    parser = argparse.ArgumentParser(description="Strict Translation Engine Runner")
    parser.add_argument(
        "command",
        choices=["preflight", "postflight", "auto-translate", "auto-full", "auto-batch", "status", "test-connection"],
        help="Command to run (auto-* commands use the secondary OpenGateway AI pipeline)",
    )
    parser.add_argument("--branch", required=False, help="Project branch name")
    parser.add_argument("--chapter", required=False, type=int, help="Chapter number")
    parser.add_argument("--from-chapter", type=int, dest="from_ch", help="Start chapter (batch)")
    parser.add_argument("--to-chapter", type=int, dest="to_ch", help="End chapter (batch)")
    parser.add_argument("--dry-run", action="store_true", help="Don't save result (auto-translate)")
    
    args = parser.parse_args()

    if args.command == "test-connection":
        return 0 if test_connection() else 1
    
    if args.command == "auto-batch":
        if not args.branch or args.from_ch is None or args.to_ch is None:
            parser.error("auto-batch requires --branch, --from-chapter, --to-chapter")
        return 0 if run_batch(args.branch, args.from_ch, args.to_ch) else 1

    if not args.branch or args.chapter is None:
        parser.error(f"{args.command} requires --branch and --chapter")

    if args.command == "status":
        get_status(args.branch, args.chapter)
        return 0
    elif args.command == "preflight":
        return 0 if run_preflight(args.branch, args.chapter) else 1
    elif args.command == "auto-translate":
        return 0 if run_translate(args.branch, args.chapter, args.dry_run) else 1
    elif args.command == "auto-full":
        return 0 if run_full(args.branch, args.chapter) else 1
    elif args.command == "postflight":
        return 0 if run_postflight(args.branch, args.chapter) else 1
        
    return 1


if __name__ == "__main__":
    sys.exit(main())
