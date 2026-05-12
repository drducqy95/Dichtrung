import json
import datetime
import os

path = r'd:\Dichtrung\Output\Linh Hon Negary_Hu Minh\progress.json'
with open(path, 'r', encoding='utf-8') as f:
    data = json.load(f)

now = datetime.datetime.now().isoformat()
existing_nums = {c['chapter_number'] for c in data['chapters']}

for i in range(52, 81):
    if i not in existing_nums:
        # We need the real titles if possible, but for progress tracking 'Audit DONE' is fine
        # Or better, I can try to extract titles from files
        title = f"Chương {i:04d}"
        file_name = f"Chương {i:04d} - "
        output_path = r'd:\Dichtrung\Output\Linh Hon Negary_Hu Minh\output'
        for f_name in os.listdir(output_path):
            if f_name.startswith(file_name):
                title = f_name.replace(file_name, "").replace(".md", "")
                break
        
        data['chapters'].append({
            'chapter_number': i,
            'title': title,
            'status': 'DONE',
            'last_updated': now
        })
    else:
        for c in data['chapters']:
            if c['chapter_number'] == i:
                c['status'] = 'DONE'
                c['last_updated'] = now

data['completed_chapters'] = max(data['completed_chapters'], 80)
data['chapters'].sort(key=lambda x: x['chapter_number'])

with open(path, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
