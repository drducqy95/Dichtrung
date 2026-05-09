import re
from pathlib import Path

INPUT_DIR = Path(r"d:\Dichtrung\Output\Ta Trong Binh Vu Tru_Tam Bach Can Dich Vi Tieu\output")

# List of words containing "anh" to exclude from replacement
EXCLUDES = [
    "anh hùng", "anh minh", "tinh anh", "anh tuấn", "anh dũng", "anh kiệt", 
    "anh linh", "anh hoa", "anh tài", "anh khí", "tiếng Anh", "nước Anh", "anh quốc",
    "anh em", "anh trai", "anh họ", "anh rể", "đàn anh", "người anh", 
    "các anh", "những anh", "mấy anh", "anh chị", "chị anh", "hai anh", "ba anh"
]

def apply_replacements(text: str) -> str:
    # 1. Normalize characters' names (globally within the narrator block)
    replacements = {
        "Tô San Ni": "Suzanne",
        "Y Lợi Ti": "Elise",
        "Âu Nhược Lạp": "Aurora",
        "Hi La Đa Đức": "Herodotus",
        "Tây Nhĩ Phù": "Sylph",
        "Oa Đốn": "Walton",
        "Asol": "Athol",
        "Gell-Hans": "Gerhans",
        "Đồ Khắc Tư": "Tukasi"
    }
    for k, v in replacements.items():
        text = text.replace(k, v)

    # 2. Exclude common words from 'anh' replacement
    placeholder_map = {}
    for word in EXCLUDES:
        pattern = re.compile(rf'\b({word})\b', re.IGNORECASE)
        def repl(m):
            ph = f"__EXC_{len(placeholder_map)}__"
            placeholder_map[ph] = m.group(1)
            return ph
        text = pattern.sub(repl, text)

    # 3. Apply pronoun replacements
    # "Của anh" -> "Của hắn"
    text = re.sub(r'\bcủa anh\b', 'của hắn', text)
    text = re.sub(r'\bCủa anh\b', 'Của hắn', text)
    
    # "anh ta" / "anh ấy" -> "hắn"
    text = re.sub(r'\banh (ta|ấy)\b', 'hắn', text)
    text = re.sub(r'\bAnh (ta|ấy)\b', 'Hắn', text)
    
    # "cô ấy" -> "cô ta"
    text = re.sub(r'\bcô ấy\b', 'cô ta', text)
    text = re.sub(r'\bCô ấy\b', 'Cô ta', text)

    # Standalone "anh" -> "hắn"
    text = re.sub(r'\banh\b', 'hắn', text)
    text = re.sub(r'\bAnh\b', 'Hắn', text)

    # 4. Restore excluded words
    for ph, word in placeholder_map.items():
        text = text.replace(ph, word)
        
    return text

def fix_pronouns_in_text(text: str) -> str:
    # Split text into dialog and non-dialog blocks.
    # We assume dialogs are enclosed in "..." or “...”
    # This regex splits keeping the delimiters and the dialog content.
    parts = re.split(r'(["“].+?["”])', text, flags=re.DOTALL)
    
    for i in range(len(parts)):
        # Even indices are non-dialog, odd indices are dialog
        if i % 2 == 0:
            parts[i] = apply_replacements(parts[i])
            
    return "".join(parts)

def main():
    files = list(INPUT_DIR.glob("Chương *.md"))
    print(f"Found {len(files)} chapters.")
    changed_count = 0
    for f in files:
        try:
            original_text = f.read_text(encoding="utf-8")
            new_text = fix_pronouns_in_text(original_text)
            if new_text != original_text:
                f.write_text(new_text, encoding="utf-8")
                changed_count += 1
        except Exception as e:
            print(f"Error processing {f.name}: {e}")
            
    print(f"Updated {changed_count} files.")

if __name__ == "__main__":
    main()
