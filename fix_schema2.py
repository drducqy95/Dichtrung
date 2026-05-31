import json
from pathlib import Path

def process_chapter(branch, chapter):
    branch_dir = Path("Output") / branch
    trans_file = branch_dir / "runtime" / f"chapter_{chapter:04d}.translation_result.json"
    analysis_file = branch_dir / "runtime" / "analysis" / f"chapter_{chapter:04d}.analysis_result.json"
    
    with open(analysis_file, encoding='utf-8') as f:
        analysis = json.load(f)
    
    with open(trans_file, encoding='utf-8') as f:
        trans = json.load(f)
        
    for key in ['term_occurrences', 'entity_mentions', 'phrase_patterns', 'grammar_rule_candidates', 'quality_audit']:
        trans[key] = analysis.get(key, [] if key != 'quality_audit' else {})
        
    with open(trans_file, 'w', encoding='utf-8') as f:
        json.dump(trans, f, ensure_ascii=False, indent=2)
        
    print(f"Chapter {chapter} updated translation_result.json with analysis fields.")

for ch in range(23, 34):
    process_chapter('Tu Chan Bon Van Nam_Ngoa Nguu Chan Nhan', ch)
