import json
import os
import sys

project_dir = r'd:\Dichtrung\Output\Phi Pham Hong Hoang_Nga Tu Phi Pham'
progress_path = os.path.join(project_dir, 'progress.json')

with open(progress_path, 'r', encoding='utf-8') as f:
    progress = json.load(f)

for chapter_data in progress['chapters']:
    ch_num = chapter_data['chapter']
    title = chapter_data['title']
    
    # Safe title
    safe_title = title.replace(':', '').replace('/', '').replace('\\', '').replace('?', '').replace('*', '').replace('"', '').replace('<', '').replace('>', '').replace('|', '').strip()
    
    old_name = f'chapter_{ch_num:04d}.md'
    new_name = f'Chương {ch_num:04d} - {safe_title}.md'
    
    for folder in ['output', 'drafts']:
        old_path = os.path.join(project_dir, folder, old_name)
        new_path = os.path.join(project_dir, folder, new_name)
        
        if os.path.exists(old_path):
            os.rename(old_path, new_path)
            
sys.exit(0)
