---
description: Build ebook (EPUB/PDF/HTML) cho project branch trong Dichtrung (override /ebook gốc)
---

# WORKFLOW: /ebook — Dichtrung Ebook Builder v1.0

Override workflow `/ebook` toàn cục cho cấu trúc mono-repo Dichtrung.

---

## ⚠️ PRIME DIRECTIVE

1. Xác định project branch:
   - `/ebook [branch]` → branch cụ thể
   - `/ebook` → hỏi user chọn branch
2. Kiểm tra `Output/[Branch]/progress.json` → xác nhận tất cả chương đã dịch xong
3. Nếu chưa xong → Cảnh báo: "⚠️ Branch [X] còn [Y] chương chưa dịch. Tiếp tục build?"

---

## Bước 1: Kiểm Tra Source

- **Source path:** `d:\Dichtrung\Output\[Branch]\output\` (bản dịch cuối)
- **Output path:** `d:\Dichtrung\Output\[Branch]\ebook\`
- **Metadata:** Lấy từ `Output/[Branch]/translation_config.json`:
  - `project_name` → title
  - Tác giả → lấy từ tên file HTML gốc (phần sau dấu `_`)
  - `target_language` → language (luôn là `vi`)

---

## Bước 2: Build Ebook

```powershell
python "C:\Users\vanki\.gemini\antigravity\global_skills\skills\ebook-publisher\scripts\build_book.py" "d:\Dichtrung\Output\[Branch]\output" --title "[Tên Sách]" --author "[Tác Giả]" --language "vi" --formats "epub,pdf,html" --output "d:\Dichtrung\Output\[Branch]\ebook"
```

---

## Bước 3: Validate

Theo workflow `/ebook` gốc:
- Kiểm tra build manifest
- Kiểm tra missing tools
- Kiểm tra layout

---

## Bước 4: Báo Cáo

```
"📚 EBOOK ĐÃ BUILD XONG!

📖 Sách: [Tên]
✍️ Tác giả: [Tên]
🌐 Ngôn ngữ: Tiếng Việt
📄 Chương: [X] chương

📂 Output:
  - EPUB: Output/[Branch]/ebook/[tên].epub
  - PDF: Output/[Branch]/ebook/[tên].pdf
  - HTML: Output/[Branch]/ebook/[tên].html

⚠️ Cảnh báo (nếu có): [danh sách]"
```

---

## Bước 5: Cập Nhật Progress

Đánh dấu project branch là `COMPLETED` trong `d:\Dichtrung\project_progress.json`:

```json
{
  "status": "COMPLETED",
  "ebook_built": true,
  "ebook_formats": ["epub", "pdf", "html"],
  "completed_at": "[timestamp]"
}
```

---

## ⚠️ QUY TẮC VÀNG

1. ✅ **CHỈ BUILD** khi tất cả chương đã dịch xong (hoặc user xác nhận)
2. ✅ **SOURCE = output/** (bản dịch cuối, KHÔNG phải source gốc)
3. ✅ **LANGUAGE = vi** luôn luôn
4. ✅ **Ebook output** nằm trong `Output/[Branch]/ebook/`
