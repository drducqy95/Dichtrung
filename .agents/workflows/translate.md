---
description: Dịch chương trong repo Dichtrung bằng Strict Translation Engine Contract V2
---

# WORKFLOW: /translate - Strict Translation Engine V2

## Nguyên tắc bắt buộc

- AI chỉ đọc `runtime/context_packs/chapter_XXXX.context_pack.json`.
- Source là dữ liệu bất biến trong `chapter.source_segments`; không echo, sửa hoặc tự phân đoạn lại source.
- AI chỉ ghi `runtime/chapter_XXXX.translation_result.json` theo schema `translation_result.v2`.
- AI không tự ghi Markdown, glossary, character state hoặc analysis JSONL.
- Không bypass gate. Postflight fail thì dừng và sửa artifact đầu vào.

## Bước 1: Preflight

```powershell
python "Script/strict_engine/translation_runner.py" preflight --branch "[Branch]" --chapter [Chapter]
```

Preflight tạo:

- `runtime/manifests/chapter_XXXX.scan.json`
- `runtime/manifests/chapter_XXXX.source_segments.json`
- `runtime/context_packs/chapter_XXXX.context_pack.json`
- `runtime/gates/chapter_XXXX.precheck.json`

Manifest dùng ID toàn cục `chapter_XXXX:seg_XXXX` và SHA-256 source.

## Bước 2: Translation Result V2

AI trả một lượt hybrid:

```json
{
  "schema_version": "2.0",
  "chapter_id": "chapter_0040",
  "source_manifest_hash": "...",
  "segment_translations": [
    {
      "segment_ids": ["chapter_0040:seg_0001"],
      "target": "Bản dịch tiếng Việt",
      "narrative_type": "narration"
    }
  ],
  "analysis_candidates": {
    "term_occurrences": {"status": "no_evidence", "evidence_count": 0, "items": []},
    "entity_mentions": {"status": "no_evidence", "evidence_count": 0, "items": []},
    "name_mentions": {"status": "no_evidence", "evidence_count": 0, "items": []},
    "phrase_patterns": {"status": "no_evidence", "evidence_count": 0, "items": []},
    "grammar_rule_candidates": {"status": "no_evidence", "evidence_count": 0, "items": []}
  }
}
```

Điền thêm đầy đủ các field schema yêu cầu: title, summary, timeline, worldbuilding, term mới và character mới.

Quy tắc:

- Dịch mới dùng một `segment_id` cho mỗi target.
- Candidate chỉ tham chiếu stable segment ID.
- Analyzer không có bằng chứng phải ghi `status=no_evidence`, `evidence_count=0`, `items=[]`.
- Không đưa source vào JSON kết quả.

## Bước 3: Postflight

```powershell
python "Script/strict_engine/translation_runner.py" postflight --branch "[Branch]" --chapter [Chapter]
```

Thứ tự strict:

1. Validate translation core và source manifest.
2. Dựng `runtime/analysis/chapter_XXXX.analysis_result.json`.
3. Chạy strict analysis gate.
4. Chỉ khi analysis pass mới ghi Markdown và cập nhật state.
5. Rebuild derived analysis JSONL idempotent.
6. Chạy statecheck.

Gate chặn: thiếu/trùng/lạ segment ID, hash sai, ref hỏng, CJK còn sót, locked-term violation, analyzer report thiếu hoặc `no_evidence` sai contract.

