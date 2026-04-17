import json
import sys

try:
    with open('d:/Dichsach/Aclinhquocdo/context.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    print("=== SUMMARY OF CHUNKS ===")
    chapters = data.get('chapter_summaries', [])
    with open('d:/Dichsach/Aclinhquocdo/chapters.txt', 'w', encoding='utf-8') as out:
        for c in chapters:
            ch = c.get('chapter', 0)
            # only print for chapters > 90
            if int(ch) >= 100 and int(ch) % 10 == 0:
                out.write(f"Chap {ch}: {c.get('title', '')} - {c.get('summary', '')[:80]}...\n")
except Exception as e:
    print("Error:", e)
