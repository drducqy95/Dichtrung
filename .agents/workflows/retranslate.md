---
description: Dịch lại các đoạn lỗi trong bản dịch Dichtrung (override /retranslate gốc)
---

# WORKFLOW: /retranslate — Dichtrung Patch Translation v1.0

Override workflow `/retranslate` toàn cục cho cấu trúc mono-repo Dichtrung.

---

## ⚠️ PRIME DIRECTIVE

**TRƯỚC KHI LÀM BẤT CỨ ĐIỀU GÌ — ĐỌC THEO THỨ TỰ SAU:**

1. Đọc `d:\Dichtrung\Global State\global_config.json` → lấy quy tắc dịch toàn cục
2. Xác định project branch hiện tại:
   - Nếu user chỉ định: `/retranslate [tên branch] [chapter_range] [yêu cầu]`
   - Nếu không: kiểm tra context → hỏi user chọn branch
3. **Working dir:** `d:\Dichtrung\Output\[Tên Project Branch]\`
4. **Source dir:** `d:\Dichtrung\Source\Source split\[Tên]\`
5. Load state files TỪ working dir:
   - `translation_config.json` → quy tắc dịch cục bộ
   - `glossary.json` → bảng thuật ngữ (⚡ NGUỒN SỰ THẬT CHÍNH)
   - `characters.json` → tên nhân vật, xưng hô
   - `pronouns.json` → quy tắc xưng hô
   - `progress.json` → biết chương nào đã dịch
   - `Story-TimeLine.jsonl` → diễn biến cốt truyện để duy trì sự nhất quán
6. Đọc yêu cầu cụ thể của user → **QUYỀN ƯU TIÊN CAO NHẤT**

---

## Thực Thi

**CHẠY ĐÚNG QUY TRÌNH `/restranslate` GỐC** (từ `global_workflows/restranslate.md`) với các điều chỉnh:

### Override Path

| Mục | Workflow gốc | Dichtrung |
|-----|-------------|-----------|
| Output | `output/chapter_XXX.md` | `d:\Dichtrung\Output\[Branch]\output\Chương XXXX - [Tên].md` |
| State files | `*.json` | `d:\Dichtrung\Output\[Branch]\*.json` |
| Source (tham chiếu) | `source/` | `d:\Dichtrung\Source\Source split\[Tên]\` |
| Logs | `logs/` | `d:\Dichtrung\Output\[Branch]\logs\` |

### Override Filename Pattern

File output trong Dichtrung tuân theo pattern:
```
Chương {chapter:04d} - {title}.md
```
Ví dụ: `Chương 0021 - Tân sinh không thuộc về mình.md`

Khi quét phạm vi chương, liệt kê tất cả file trong `output/` matching pattern `Chương 00XX*`.

---

## Context Detection (Override)

```
/restranslate [branch] [range]           → Quét và sửa các chương trong phạm vi
/restranslate [branch] [range] [yêu cầu] → Quét theo yêu cầu cụ thể
/restranslate [range]                    → Dùng branch hiện tại từ context
/restranslate all                        → Quét tất cả chương đã dịch
/restranslate                            → Hỏi user: "Sửa chương nào? Yêu cầu gì?"
```

---

## Bước Bổ Sung: Sanitization Bắt Buộc

**SAU MỖI CHƯƠNG ĐƯỢC SỬA, TRƯỚC KHI KẾT THÚC:**

Quét file output đã sửa tìm ký tự CJK (Unicode range U+4E00-U+9FFF, U+3400-U+4DBF):
- ✅ **Không có CJK:** PASS
- ⛔ **Có CJK:** DỪNG. Liệt kê từng vị trí → Sửa → Quét lại

**Đây là quy tắc TUYỆT ĐỐI từ `global_config.json`. KHÔNG có ngoại lệ.**

---

## 🚫 Quy Tắc Kỹ Thuật

### KHÔNG sử dụng Python/Script

Tất cả các bước quét lỗi và sửa lỗi PHẢI thực hiện bằng:
- Tool `view_file` → đọc file output
- Tool `grep_search` → tìm pattern lỗi
- Tool `replace_file_content` hoặc `multi_replace_file_content` → sửa lỗi
- KHÔNG chạy `run_command` với Python/PowerShell để sửa nội dung file

### Quy Trình Quét Không Dùng Script

1. **Đọc glossary** → Build danh sách thuật ngữ cần kiểm tra (trong bộ nhớ)
2. **Đọc characters** → Build danh sách tên nhân vật cần kiểm tra
3. **Đọc Story-TimeLine** → Nắm bắt diễn biến và các chi tiết cốt truyện quan trọng để đảm bảo việc sửa lỗi không làm sai lệch logic truyện.
3. **Đọc từng file output** bằng `view_file`
4. **So sánh thủ công** từng dòng với bảng quy tắc
5. **Dùng `grep_search`** khi cần tìm pattern cụ thể trong nhiều file
6. **Sửa bằng tool edit** — `replace_file_content` cho lỗi đơn lẻ, `multi_replace_file_content` cho nhiều lỗi cùng file

---

## ⚠️ QUY TẮC VÀNG

1. ✅ **LOAD CONFIG TRƯỚC** — Đọc glossary, characters, config TRƯỚC khi quét
2. ✅ **CHỈ SỬA ĐOẠN LỖI** — KHÔNG dịch lại toàn bộ chương
3. ✅ **KHÔNG PYTHON** — Dùng trực tiếp tool edit, không chạy script
4. ✅ **XÁC MINH SAU SỬA** — Quét lại file sau mỗi lần sửa
5. ✅ **ƯU TIÊN USER** — Yêu cầu user > glossary > config mặc định
6. ✅ **BẢO TOÀN VĂN PHONG** — Giữ nguyên mạch văn của phần không lỗi
7. ✅ **CJK-FREE** — Quét CJK sau mỗi lần sửa
8. ✅ **ĐÚNG PATH** — Source ở `Source/Source split/`, output ở `Output/[Branch]/output/`