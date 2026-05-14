import json
import os
from datetime import datetime

BRANCH_DIR = r"d:\Dichtrung\Output\Linh Hon Negary_Hu Minh"
GLOBAL_DIR = r"d:\Dichtrung\Global State"

def sync_glossary():
    local_path = os.path.join(BRANCH_DIR, "glossary.json")
    global_path = os.path.join(GLOBAL_DIR, "global_glossary.json")
    
    if not os.path.exists(local_path) or not os.path.exists(global_path):
        print("Glossary files missing.")
        return

    with open(local_path, "r", encoding="utf-8") as f:
        local_data = json.load(f)
    with open(global_path, "r", encoding="utf-8") as f:
        global_data = json.load(f)

    synced_count = 0
    global_terms = {e["source_term"]: e for e in global_data["entries"]}
    
    for entry in local_data["entries"]:
        if entry.get("pending_sync"):
            source = entry["source"]
            target = entry["target"]
            note = entry.get("note", "")
            
            if source in global_terms:
                # Update if needed (simplified)
                global_terms[source]["target_term"] = target
                global_terms[source]["notes"] = note
            else:
                new_id = f"GTERM_{len(global_data['entries']) + synced_count + 1:04d}"
                new_entry = {
                    "id": new_id,
                    "source_term": source,
                    "target_term": target,
                    "category": "terminology",
                    "source_project": "Linh Hon Negary_Hu Minh",
                    "confidence": "high",
                    "notes": note,
                    "locked": False
                }
                global_data["entries"].append(new_entry)
            
            entry["pending_sync"] = False
            synced_count += 1

    if synced_count > 0:
        global_data["metadata"]["last_updated"] = datetime.now().isoformat()
        global_data["metadata"]["total_entries"] = len(global_data["entries"])
        
        with open(global_path, "w", encoding="utf-8") as f:
            json.dump(global_data, f, ensure_ascii=False, indent=2)
        with open(local_path, "w", encoding="utf-8") as f:
            json.dump(local_data, f, ensure_ascii=False, indent=2)
        print(f"Synced {synced_count} glossary terms.")
    else:
        print("No glossary terms to sync.")

def sync_characters():
    local_path = os.path.join(BRANCH_DIR, "characters.json")
    global_path = os.path.join(GLOBAL_DIR, "global_characters.json")
    
    if not os.path.exists(local_path) or not os.path.exists(global_path):
        print("Character files missing.")
        return

    with open(local_path, "r", encoding="utf-8") as f:
        local_data = json.load(f)
    with open(global_path, "r", encoding="utf-8") as f:
        global_data = json.load(f)

    synced_count = 0
    global_chars = {}
    for c in global_data["characters"]:
        name = c.get("name_original") or c.get("name_source")
        if name:
            global_chars[(name, c.get("source_project"))] = c
    
    for char in local_data["characters"]:
        if char.get("pending_sync"):
            name_orig = char.get("name_original") or char.get("name_source")
            name_trans = char.get("name_translated") or char.get("name_target")
            
            if not name_orig:
                continue

            key = (name_orig, "Linh Hon Negary_Hu Minh")
            if key in global_chars:
                global_chars[key]["name_translated"] = name_trans
                global_chars[key]["description"] = char.get("description", "")
            else:
                new_char = {
                    "id": f"GCHAR_{len(global_data['characters']) + synced_count + 1:04d}",
                    "name_original": name_orig,
                    "name_translated": name_trans,
                    "gender": char.get("gender", ""),
                    "role": char.get("role", ""),
                    "description": char.get("description", ""),
                    "source_project": "Linh Hon Negary_Hu Minh",
                    "first_appearance": "",
                    "notes": char.get("notes", "")
                }
                global_data["characters"].append(new_char)
            
            char["pending_sync"] = False
            synced_count += 1

    if synced_count > 0:
        global_data["metadata"]["last_updated"] = datetime.now().isoformat()
        
        with open(global_path, "w", encoding="utf-8") as f:
            json.dump(global_data, f, ensure_ascii=False, indent=2)
        with open(local_path, "w", encoding="utf-8") as f:
            json.dump(local_data, f, ensure_ascii=False, indent=2)
        print(f"Synced {synced_count} characters.")
    else:
        print("No characters to sync.")

if __name__ == "__main__":
    sync_glossary()
    sync_characters()
