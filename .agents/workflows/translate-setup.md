---
description: Khởi tạo project Dichtrung tương thích Strict Translation Engine Contract V2
---

# WORKFLOW: /translate-setup - Contract V2

## State chuẩn

Branch nằm tại `Output/[Branch]/` và tham chiếu source qua `translation_config.json`:

```json
{
  "source_ref": {
    "full": "Source/Source full/[file].html",
    "split": "Source/Source split/[Story]/"
  }
}
```

Không copy source vào branch.

Tạo các thư mục:

```text
runtime/
  analysis/
  context_packs/
  gates/
  locks/
  manifests/
analysis/
  audit/
```

Tạo các state file Gold Schema:

- `glossary.json`: entry dùng `source/target`; chỉ mapping manual hoặc reviewed mới có `locked=true`.
- `characters.json`: character dùng `name_source/name_target`.
- `pronouns.json`: hỗ trợ `project_pronouns` và fallback templates trong `pronouns`.
- `worldbuilding.json`, `context.json`, `progress.json`, `Story-TimeLine.jsonl`.

## Global State

- Global glossary giữ shape `source_term/target_term`.
- Import global state vào branch phải đổi shape rõ ràng; không ghi trực tiếp shape global vào branch.
- Auto-sync chỉ nhận tri thức đã promotion qua distinct-chapter evidence.
- Mapping xung đột hoặc ambiguity đi vào review queue; không tự ghi đè manual lock.

## Kiểm tra ban đầu

```powershell
python "Script/strict_engine/translation_runner.py" preflight --branch "[Branch]" --chapter 1
```

Xác nhận có cả scan report, source segment manifest, context pack và precheck PASS trước khi dịch.

## Backfill branch cũ

```powershell
python "Script/strict_engine/backfill_analysis_v2.py" --branch "[Branch]" --from-chapter 1 --to-chapter [LastChapter]
```

Backfill sao lưu artifact cũ, giữ nguyên Markdown đã dịch, dựng manifest mới, alignment monotonic DP, strict analysis artifact và derived JSONL idempotent.

