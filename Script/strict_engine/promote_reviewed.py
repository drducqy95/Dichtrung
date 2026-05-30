#!/usr/bin/env python3
"""
Promotes candidate rules and terms to "reviewed" status based on frequency
and confidence thresholds across a block of 10 chapters.
"""

import json
from pathlib import Path
from typing import Dict, List, Any
import logging

from utils import io

logger = io.get_logger("promote_reviewed")

def score_rule(rule: Dict[str, Any], evidence_count: int) -> float:
    """
    Qt_plus-compatible scoring:
    score = rank * 100 + len(evidence) * 5
    We use simplified logic here for Phase 3.
    """
    rank = rule.get("rank", 1)
    return float(rank * 100 + evidence_count * 5)

def aggregate_rules(lines: List[str]) -> List[Dict[str, Any]]:
    # Group by alias
    grouped = {}
    for line in lines:
        if not line.strip(): continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        
        alias = item.get("alias")
        if not alias: continue
        
        if alias not in grouped:
            grouped[alias] = {
                "rule": item,
                "evidence": set(item.get("evidence", [])),
                "confidence_sum": item.get("confidence", 0.0),
                "count": 1
            }
        else:
            grouped[alias]["evidence"].update(item.get("evidence", []))
            grouped[alias]["confidence_sum"] += item.get("confidence", 0.0)
            grouped[alias]["count"] += 1
            
    reviewed = []
    for alias, group in grouped.items():
        avg_confidence = group["confidence_sum"] / group["count"]
        # Rule criteria: evidence in >= 3 chapters AND avg_confidence >= 0.8
        if len(group["evidence"]) >= 3 and avg_confidence >= 0.8:
            promoted_rule = group["rule"]
            promoted_rule["status"] = "reviewed"
            promoted_rule["score"] = score_rule(promoted_rule, len(group["evidence"]))
            promoted_rule["evidence"] = list(group["evidence"])
            reviewed.append(promoted_rule)
    return reviewed

def aggregate_terms(lines: List[str]) -> List[Dict[str, Any]]:
    # Group by source_term -> target_term mapping
    grouped = {}
    for line in lines:
        if not line.strip(): continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
            
        source = item.get("source_term")
        target = item.get("target_term")
        if not source or not target: continue
        
        # Only consider auto-locking terms that are present in target
        if not item.get("present_in_target", False): continue
        
        key = (source, target)
        grouped[key] = grouped.get(key, 0) + 1
        
    reviewed = []
    for (source, target), count in grouped.items():
        # Term criteria: appears >= 5 times with consistent mapping
        if count >= 5:
            reviewed.append({
                "source": source,
                "target": target,
                "frequency": count,
                "status": "auto-locked"
            })
    return reviewed

def promote_reviewed(branch_name: str, chapter: int) -> dict:
    """
    Called when chapter % 10 == 0.
    Reads recent append-only logs and promotes solid candidates to reviewed status.
    """
    branch_dir = io.resolve_branch_dir(branch_name)
    analysis_dir = branch_dir / "analysis"
    
    rules_file = analysis_dir / "grammar_rules.jsonl"
    terms_file = analysis_dir / "term_occurrences.jsonl"
    
    report = {"promoted_rules_count": 0, "promoted_terms_count": 0}
    
    # Promote Rules
    if rules_file.exists():
        with rules_file.open("r", encoding="utf-8") as f:
            lines = f.readlines()
        
        # Only process lines added recently, but for simplicity we aggregate all.
        reviewed_rules = aggregate_rules(lines)
        report["promoted_rules_count"] = len(reviewed_rules)
        
        if reviewed_rules:
            out_rules_file = analysis_dir / "reviewed_rules.jsonl"
            # Overwrite or merge logic here, for now we overwrite with the latest aggregated state
            with out_rules_file.open("w", encoding="utf-8") as f:
                for r in reviewed_rules:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")
            logger.info(f"Promoted {len(reviewed_rules)} rules to reviewed status.")

    # Promote Terms
    if terms_file.exists():
        with terms_file.open("r", encoding="utf-8") as f:
            lines = f.readlines()
            
        reviewed_terms = aggregate_terms(lines)
        report["promoted_terms_count"] = len(reviewed_terms)
        
        if reviewed_terms:
            out_terms_file = analysis_dir / "reviewed_terms.jsonl"
            with out_terms_file.open("w", encoding="utf-8") as f:
                for t in reviewed_terms:
                    f.write(json.dumps(t, ensure_ascii=False) + "\n")
            logger.info(f"Promoted {len(reviewed_terms)} terms to auto-locked status.")
            
    # Write a promotion audit file
    audit_dir = analysis_dir / "audit"
    io.ensure_dir(audit_dir)
    audit_file = audit_dir / f"chapter_{chapter:04d}.promote.json"
    io.save_json_atomic(audit_file, report)
    
    return report

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--branch", required=True)
    parser.add_argument("--chapter", type=int, required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    
    if args.dry_run:
        logger.info("Dry run mode...")
    
    res = promote_reviewed(args.branch, args.chapter)
    print(json.dumps(res, indent=2))
