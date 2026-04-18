import os
import re

# Define replacement map
replacements = {
    r"Gien Tỏa": "Khóa Gen",
    r"Thương nghiệp Liên minh": "Liên Minh Thương Nghiệp",
    r"Xí Thiên Sứ": "Sí Thiên Sứ",
    r"Ngải Bỉ Tư": "Ebis",
    r"Lorikk Kim Nhãn": "Lorikk Mắt Vàng",
    r"Pháp sư ngũ hoàn": "Pháp sư 5 vòng",
    r"Lô Ti \(.*?\)": "Los",             # Flexible replacement
    r"Lô Ti": "Los",                     # Standalone replacement
    r"Lạc Ti": "Los",                    # Standalone replacement
    r"Trì Tra \(.*?\)": "Trì Tra",       # Flexible replacement
    r"Xa Can \(.*?\)": "Xa Can",         # Flexible replacement
    r"Cốt \(.*?\)": "Cốt",               # Flexible replacement
    r"Ngô Minh \(.*?\)": "Ngô Minh",     # Flexible replacement
    r"Trịnh Xá \(.*?\)": "Trịnh Xá",     # Flexible replacement
    r"Sở Hiên \(.*?\)": "Sở Hiên",       # Flexible replacement
    r"Lý Minh \(.*?\)": "Lý Minh",       # Flexible replacement
    r"Gia lùn": "Gnome",
    r"Cao tháp Ghi chép": "Tòa tháp Ghi chép",
    r"5th Ring Mage": "pháp sư 5 vòng",
    r"Ngài Lorikk": "Ngài Lorikk Mắt Vàng",
    r"Thương nghiệp liên minh": "Liên Minh Thương Nghiệp", # Case variation
    r"Trúc cơ": "Trúc Cơ",               # Standardization to proper noun capitalization
}

# Special handling for "Lorikk Kim Nhãn" variants
# If we see "Lorikk Kim Nhãn (Lạc Lý Khắc Kim Nhãn)", replace entirely
complex_replacements = [
    (r"Lorikk Kim Nhãn \(Lạc Lý Khắc Kim Nhãn\)", "Lorikk Mắt Vàng"),
    (r"Ebis \(Ngải Bỉ Tư\)", "Ebis"),
    (r"tộc Gnome \(Gnome\)", "tộc Gnome"), # Fix potential double naming
    (r"tộc Gia lùn \(Gnome\)", "tộc Gnome"),
]

output_dir = r"D:\Dichtrung\Output\Hong Hoang Lich_Zhttty\output"

def process_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Apply complex replacements first
    for pattern, repl in complex_replacements:
        content = re.sub(pattern, repl, content)
    
    # Apply simple replacements
    for pattern, repl in replacements.items():
        content = re.sub(pattern, repl, content)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

if __name__ == "__main__":
    files = [f for f in os.listdir(output_dir) if f.endswith(".md")]
    for filename in files:
        # Avoid printing Vietnamese characters to a CP1252 console
        process_file(os.path.join(output_dir, filename))
    print("Nomenclature update completed successfully.")
