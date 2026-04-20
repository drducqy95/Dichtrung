# -*- coding: utf-8 -*-
import os
import re

output_dir = r"d:\Dichtrung\Output\Hong Hoang Lich_Zhttty\output"

regex_en_parens = re.compile(r'(?<!\])\s*\([A-Za-z][A-Za-z0-9\s\-/\:]+\)')

print("Starting to clean files in:", output_dir)
count = 0
for file in os.listdir(output_dir):
    if file.endswith(".md"):
        filepath = os.path.join(output_dir, file)
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Remove English parentheses
        content = regex_en_parens.sub('', content)
        
        # Remove translation note blocks
        content = re.sub(r'\s*\(Chú thích.*?\)', '', content, flags=re.IGNORECASE)
        content = re.sub(r'\s*\(Tác giả.*?\)', '', content, flags=re.IGNORECASE)
        content = re.sub(r'\s*\(Lời giải thích.*?\)', '', content, flags=re.IGNORECASE)
        content = re.sub(r'\s*\(Giải thích.*?\)', '', content, flags=re.IGNORECASE)
        content = re.sub(r'\s*\(ps:.*?\)', '', content, flags=re.IGNORECASE)
        
        # Remove empty lines if we deleted a whole line that just had a note
        content = re.sub(r'\n[ \t]+\n', '\n\n', content)
        # Squeeze 3+ newlines to 2
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        if content != original_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            count += 1
            print("Cleaned a file")

print(f"Done. Cleaned {count} files.")
