#!/usr/bin/env python3
"""
Synchronizes reviewed items from a project branch back to the Global State.
This handles cross-project knowledge sharing while enforcing strict boundaries
between experimental (candidates) and verified (reviewed) knowledge.
"""

import json
import logging
from pathlib import Path
from utils import io

logger = io.get_logger("sync_analysis_global")

def sync_analysis_to_global(branch_name: str) -> dict:
    """
    Sync policy:
    ✅ Sync: rules status=reviewed, terms auto-locked
    ❌ Block: candidates, ambiguity_cases, single-chapter patterns
    """
    branch_dir = io.resolve_branch_dir(branch_name)
    analysis_dir = branch_dir / "analysis"
    
    global_dir = io.GLOBAL_STATE_DIR
    io.ensure_dir(global_dir)
    
    global_rules_file = global_dir / "global_grammar_rules.jsonl"
    global_glossary_file = global_dir / "global_glossary.json"
    
    report = {"synced_rules": 0, "synced_terms": 0}
    
    # 1. Sync Rules
    reviewed_rules_file = analysis_dir / "reviewed_rules.jsonl"
    if reviewed_rules_file.exists():
        with reviewed_rules_file.open("r", encoding="utf-8") as f:
            branch_rules = [json.loads(line) for line in f if line.strip()]
            
        if branch_rules:
            with io.file_lock(global_rules_file.with_suffix(".lock")):
                existing_rules = {}
                if global_rules_file.exists():
                    with global_rules_file.open("r", encoding="utf-8") as gf:
                        for line in gf:
                            if not line.strip(): continue
                            try:
                                r = json.loads(line)
                                if "alias" in r:
                                    existing_rules[r["alias"]] = r
                            except Exception:
                                pass
                
                new_or_updated = []
                for rule in branch_rules:
                    alias = rule.get("alias")
                    if not alias: continue
                    # Update if new or if score is higher
                    existing_score = existing_rules[alias].get("score", 0) if alias in existing_rules else -1
                    if rule.get("score", 0) > existing_score:
                        existing_rules[alias] = rule
                        new_or_updated.append(rule)
                
                if new_or_updated:
                    with global_rules_file.open("a", encoding="utf-8") as gf:
                        for rule in new_or_updated:
                            gf.write(json.dumps(rule, ensure_ascii=False) + "\n")
                    report["synced_rules"] = len(new_or_updated)
                    logger.info(f"Synced {len(new_or_updated)} new/updated rules to global state.")
            
    # 2. Sync Terms to Global Glossary
    reviewed_terms_file = analysis_dir / "reviewed_terms.jsonl"
    if reviewed_terms_file.exists():
        with reviewed_terms_file.open("r", encoding="utf-8") as f:
            branch_terms = [json.loads(line) for line in f if line.strip()]
            
        if branch_terms:
            with io.file_lock(global_glossary_file.with_suffix(".lock")):
                global_glossary = io.load_json(global_glossary_file, default={"entries": []})
                
                # Deduplicate by source
                existing_sources = {e["source"] for e in global_glossary.get("entries", [])}
                new_entries = []
                for t in branch_terms:
                    if t["source"] not in existing_sources:
                        new_entries.append({
                            "source": t["source"],
                            "target": t["target"],
                            "branch_origin": branch_name,
                            "type": "auto_locked"
                        })
                        existing_sources.add(t["source"])
                        
                if new_entries:
                    global_glossary["entries"].extend(new_entries)
                    io.save_json_atomic(global_glossary_file, global_glossary)
                    report["synced_terms"] = len(new_entries)
                    logger.info(f"Synced {len(new_entries)} new terms to global glossary.")
                    
    return report

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--branch", required=True)
    args = parser.parse_args()
    
    res = sync_analysis_to_global(args.branch)
    print(json.dumps(res, indent=2))
