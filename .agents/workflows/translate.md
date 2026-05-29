---
description: Dịch thuật chương/bài trong repo Dichtrung (override /translate gốc)
---

# WORKFLOW: /translate — Dịch Thuật Dichtrung v1.0

Override workflow `/translate` toàn cục cho cấu trúc mono-repo Dichtrung.

---

## ⚠️ BẮT BUỘC SỬ DỤNG STRICT TRANSLATION ENGINE

Từ giờ trở đi, quy trình dịch thuật trong Dichtrung **KHÔNG** sử dụng cách tiếp cận đọc/ghi file thủ công bằng Agent nữa. Mọi thao tác phải thông qua Pipeline Python của **Strict Translation Engine**.

**Quy trình chuẩn khi nhận lệnh `/translate [branch] [chapter]`:**

### Bước 1: Giai Đoạn Chuẩn Bị (Preflight)
Agent (Antigravity) CHỈ chạy duy nhất lệnh sau qua Terminal:
```bash
python "Script/strict_engine/translation_runner.py" preflight --branch "[Tên Branch]" --chapter [Số Chương]
```
- ⛔ **Nếu lệnh báo FAIL:** Agent phải DỪNG NGAY LẬP TỨC và báo cáo lỗi cho User biết (do trùng lặp dữ liệu, thiếu file config...). Không được phép đi tiếp.
- ✅ **Nếu lệnh PASS:** Chuyển sang Bước 2.

### Bước 2: Dịch Thuật Cốt Lõi (AI Translation)
1. Agent đọc file `Output/[Branch]/runtime/context_packs/chapter_[XXXX].context_pack.json` bằng công cụ `view_file` hoặc `read_file`.
2. Phân tích `hard_constraints`, `dynamic_glossary`, `relationship_graph` và `source_text`.
3. Tiến hành dịch thuật văn bản (Đây là nhiệm vụ cốt lõi của Agent).
4. Đóng gói kết quả đầu ra theo ĐÚNG định dạng JSON Schema `translation_result.schema.json`.
5. Agent dùng lệnh `write_to_file` để lưu kết quả vào:
   `Output/[Branch]/runtime/chapter_[XXXX].translation_result.json`

### Bước 3: Giai Đoạn Hậu Kỳ (Postflight)
Sau khi ghi xong JSON, Agent chạy lệnh:
```bash
python "Script/strict_engine/translation_runner.py" postflight --branch "[Tên Branch]" --chapter [Số Chương]
```
- Lệnh này sẽ tự động: Validate JSON, check CJK, ghi file Markdown, cập nhật Glossary, Characters và Progress.
- ⛔ **Nếu lệnh báo FAIL:** Agent báo cáo lỗi cho User (VD: Không tuân thủ CJK ban, lỗi Schema).
- ✅ **Nếu lệnh PASS:** Việc dịch chương đã hoàn tất thành công hoàn hảo.

---

## 🔒 Các Quy Tắc Bất Di Bất Dịch
1. **Dữ liệu duy nhất:** AI KHÔNG ĐƯỢC tự đọc Source file hay Glossary. Dữ liệu duy nhất AI được phép đọc để dịch là `context_pack.json`.
2. **Output duy nhất:** AI KHÔNG ĐƯỢC tự viết file Markdown. Nhiệm vụ của AI là xuất ra `translation_result.json`. Python sẽ lo việc ghi file.
3. **Tuân thủ Gate:** Không bao giờ bypass các Gate lỗi. Nếu Python báo lỗi ở Precheck hay Statecheck, AI phải yêu cầu User can thiệp sửa Data gốc.

## Context Detection
- `/translate [branch] [chapter]` → Dịch chương cụ thể của branch bằng Strict Engine.
- `/translate` → Yêu cầu user cung cấp Branch và Chapter.
