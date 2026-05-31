import json
from pathlib import Path

def process_chapter(branch, chapter):
    branch_dir = Path("Output") / branch
    trans_file = branch_dir / "runtime" / f"chapter_{chapter:04d}.translation_result.json"
    
    with open(trans_file, encoding='utf-8') as f:
        trans = json.load(f)
        
    if 'translated_text' in trans:
        del trans['translated_text']
        
    with open(trans_file, 'w', encoding='utf-8') as f:
        json.dump(trans, f, ensure_ascii=False, indent=2)

for ch in range(23, 34):
    process_chapter('Tu Chan Bon Van Nam_Ngoa Nguu Chan Nhan', ch)
