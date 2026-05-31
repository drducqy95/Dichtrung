import json

with open(r"d:\Dichtrung\Output\Vu Su Tu Thai Duong Chi Tu\glossary.json", "r", encoding="utf-8") as f:
    data = json.load(f)

results = []
for idx, entry in enumerate(data.get("entries", [])):
    src = entry.get("source", "")
    tgt = entry.get("target", "")
    if src or tgt:
        if "克洛" in src or "克洛" in tgt or "极限" in src or "极限" in tgt or "冥想" in src or "冥想" in tgt:
            results.append(f"Index {idx}: {src} -> {tgt} ({entry.get('category')})")

with open(r"d:\Dichtrung\scratch\glossary_search_results.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(results))
