---
description: Dịch thuật chương/bài trong repo Dichtrung (override /translate gốc)
---

# WORKFLOW: /translate — Dịch Thuật Dichtrung v1.0

Override workflow `/translate` toàn cục cho cấu trúc mono-repo Dichtrung.

---

## ⚠️ PRIME DIRECTIVE

**TRƯỚC KHI DỊCH — ĐỌC THEO THỨ TỰ SAU:**

1. Đọc `d:\Dichtrung\Global State\global_config.json` → lấy quy tắc dịch
2. Xác định project branch hiện tại:
   - Nếu user chỉ định: `/translate [tên branch] [chapter]`
   - Nếu không: kiểm tra context → hỏi user chọn branch
3. **Working dir:** `d:\Dichtrung\Output\[Tên Project Branch]\`
4. **Source dir:** `d:\Dichtrung\Source\Source split\[Tên]\`
5. Load state files TỪ working dir: `translation_config.json`, `glossary.json`, `pronouns.json`, `characters.json`, `context.json`, `worldbuilding.json`, `progress.json`
6. Load global resources: `global_skills/skills/translation/SKILL.md`, `~/.gemini/antigravity/translation/global_pronouns.json`

---

## Thực Thi Dịch Thuật

**CHẠY ĐÚNG QUY TRÌNH `/translate` GỐC** (từ `global_workflows/translate.md`) với các điều chỉnh:

### Override Path

| Mục | Workflow gốc | Dichtrung |
|-----|-------------|-----------|
| Source | `[PROJECT]/source/` | `d:\Dichtrung\Source\Source split\[Tên]\` |
| Draft | `[PROJECT]/drafts/` | `d:\Dichtrung\Output\[Branch]\drafts\` |
| Output | `[PROJECT]/output/` | `d:\Dichtrung\Output\[Branch]\output\` |
| State files | `[PROJECT]/*.json` | `d:\Dichtrung\Output\[Branch]\*.json` |
| Logs | `[PROJECT]/logs/` | `d:\Dichtrung\Output\[Branch]\logs\` |
| Illustrations | `[PROJECT]/illustrations/` | `d:\Dichtrung\Output\[Branch]\illustrations\` |

---

## Bước Bổ Sung: Đồng Bộ Global State (SAU MỖI CHƯƠNG)

Sau khi hoàn thành GĐ 5 (Output & State Update) của workflow gốc, **BẮT BUỘC** thêm bước:

### 5.8: Sync Lên Global State

1. **Glossary Sync:**
   - Đọc `Output/[Branch]/glossary.json` → tìm entries có `pending_sync: true`
   - Merge vào `Global State/global_glossary.json`:
     - Nếu entry đã tồn tại (cùng `source_term`) → cập nhật `confidence` nếu cao hơn
     - Nếu entry mới → thêm vào, gắn `source_project: "[Tên Branch]"`
   - Đánh dấu `pending_sync: false` ở glossary cục bộ

2. **Characters Sync:**
   - Đọc `Output/[Branch]/characters.json` → tìm nhân vật mới/cập nhật
   - Merge vào `Global State/global_characters.json`:
     - Nếu nhân vật đã tồn tại (cùng `name_original` + `source_project`) → cập nhật
     - Nếu nhân vật mới → thêm vào, gắn `source_project: "[Tên Branch]"`

3. **Log kết quả:**
   ```
   "🔄 GLOBAL SYNC: +[X] thuật ngữ, +[Y] nhân vật → Global State"
   ```

---

## 🔒 Sanitization Bắt Buộc

**SAU MỖI CHƯƠNG, TRƯỚC KHI LƯU OUTPUT:**

Quét file `output/chapter_XXX.md` tìm ký tự CJK (Unicode range U+4E00-U+9FFF, U+3400-U+4DBF):
- ✅ **Không có CJK:** PASS
- ⛔ **Có CJK:** DỪNG. Liệt kê từng vị trí → Dịch/loại bỏ → Quét lại

**Đây là quy tắc TUYỆT ĐỐI từ `global_config.json`. KHÔNG có ngoại lệ.**

---

## Context Detection (Override)

- `/translate [branch] [chapter]` → Dịch chương cụ thể của branch
- `/translate [branch] next` → Dịch chương tiếp theo của branch
- `/translate [branch] all` → Batch mode cho branch
- `/translate next` → Dùng branch hiện tại từ context
- `/translate` → Hỏi user chọn branch + chương

---

## ⚠️ QUY TẮC VÀNG

1. ✅ **KHÔNG BAO GIỜ** đọc source từ `Output/` — source luôn ở `Source/Source split/`
2. ✅ **LUÔN** sync lên Global State sau mỗi chương
3. ✅ **LUÔN** quét CJK trước khi lưu output
4. ✅ **LUÔN** cập nhật `d:\Dichtrung\project_progress.json` (root) khi milestone thay đổi
5. ✅ **Tuân thủ đầy đủ** GĐ 1-6 của workflow `/translate` gốc
