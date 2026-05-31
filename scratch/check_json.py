import os
import json

target_dir = r"d:\Dichtrung\Output\Vu Su Tu Thai Duong Chi Tu"
for root, dirs, files in os.walk(target_dir):
    for file in files:
        if file.endswith('.json'):
            path = os.path.join(root, file)
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    json.load(f)
            except Exception as e:
                print(f"Error in {path}: {e}")
