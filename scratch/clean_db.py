import json
from pathlib import Path

branch_dir = Path("Output/Linh Hon Negary_Hu Minh")
glossary_path = branch_dir / "glossary.json"
char_path = branch_dir / "characters.json"

# Clean Glossary
if glossary_path.exists():
    with open(glossary_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    seen = set()
    cleaned = []
    dupes = []
    for entry in data.get("entries", []):
        src = entry.get("source")
        if src:
            src_clean = src.strip()
            if src_clean not in seen:
                seen.add(src_clean)
                cleaned.append(entry)
            else:
                dupes.append(src)
        else:
            cleaned.append(entry)
    data["entries"] = cleaned
    with open(glossary_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Cleaned {len(dupes)} glossary duplicates: {dupes}")

# Clean Characters
if char_path.exists():
    with open(char_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    seen_ids = set()
    seen_names = set()
    cleaned = []
    dupe_ids = []
    dupe_names = []
    for char in data.get("characters", []):
        char_id = char.get("id")
        name = char.get("source") or char.get("name_original")
        
        # Check ID
        if char_id:
            char_id_clean = char_id.strip()
            if char_id_clean in seen_ids:
                dupe_ids.append(char_id)
                continue
            seen_ids.add(char_id_clean)
            
        # Check Name
        if name:
            name_clean = name.strip()
            if name_clean in seen_names:
                dupe_names.append(name)
                continue
            seen_names.add(name_clean)
            
        cleaned.append(char)
        
    data["characters"] = cleaned
    with open(char_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Cleaned {len(dupe_ids)} duplicate character IDs: {dupe_ids}")
    print(f"Cleaned {len(dupe_names)} duplicate character names: {dupe_names}")
