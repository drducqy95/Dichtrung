---
description: Khởi tạo project branch dịch thuật mới trong repo Dichtrung
---

# WORKFLOW: /init-branch — Khởi Tạo Project Branch

Bạn là **Dichtrung Branch Manager**. Nhiệm vụ: Tạo project branch mới từ source HTML đã có sẵn.

---

## ⚠️ BẮT BUỘC

1. Đọc `d:\Dichtrung\Global State\global_config.json` → lấy quy tắc mặc định
2. Đọc `d:\Dichtrung\Global State\global_glossary.json` → chuẩn bị import thuật ngữ
3. Đọc `d:\Dichtrung\Global State\global_characters.json` → kiểm tra nhân vật đã biết

---

## Bước 1: Xác Định Source

```
User: /init-branch [Tên truyện]
→ Tìm file HTML tương ứng trong Source/Source full/
→ Nếu không tìm thấy → Hỏi user chọn file

User: /init-branch
→ Liệt kê tất cả source trong Source/Source full/
→ Hỏi user chọn
```

---

## Bước 2: Tách Chương (Nếu Chưa Có)

Kiểm tra `Source/Source split/[Tên an toàn]/` đã tồn tại chưa:

- **Đã có:** Skip bước này
- **Chưa có:** Chạy tách chương:
  ```powershell
  python "d:\Dichtrung\Script\Tachchuong.py" --file "[path đến HTML]"
  ```
  Hoặc nếu script chưa hỗ trợ CLI → tách thủ công bằng BeautifulSoup + regex (theo logic trong Tachchuong.py)

Kết quả: Các file `.md` đã tách nằm trong `Source/Source split/[Tên an toàn]/`

---

## Bước 3: Tạo Project Branch

Tạo thư mục trong `Output/`:

```
d:\Dichtrung\Output\[Tên Project Branch]\
├── translation_config.json
├── glossary.json
├── pronouns.json
├── characters.json
├── context.json
├── worldbuilding.json
├── progress.json
├── drafts\
├── output\
├── illustrations\
│   ├── characters\
│   ├── diagrams\
│   └── maps\
├── logs\
└── ebook\
```

---

## Bước 4: Chạy /translate-setup

Gọi workflow `/translate-setup` gốc từ `global_workflows/` nhưng với các override:

- **Project dir:** `d:\Dichtrung\Output\[Tên Project Branch]\`
- **Source dir:** `d:\Dichtrung\Source\Source split\[Tên]\`
- **Import glossary từ:** `d:\Dichtrung\Global State\global_glossary.json` (THAY VÌ `global_skills/skills/translation/resources/global_glossary.json`)
- **Import characters từ:** `d:\Dichtrung\Global State\global_characters.json`

---

## Bước 5: Cập Nhật project_progress.json

Thêm milestone mới vào `d:\Dichtrung\project_progress.json`:

```json
{
  "id": "M[N]",
  "title": "[Tên Project Branch]",
  "status": "INITIALIZED",
  "source_file": "Source/Source full/[tên file].html",
  "source_split": "Source/Source split/[Tên]/",
  "output_dir": "Output/[Tên Project Branch]/",
  "total_chapters": 0,
  "completed_chapters": 0
}
```

---

## Bước 6: Báo Cáo

```
"✅ PROJECT BRANCH ĐÃ KHỞI TẠO!

📁 Branch: [Tên Project Branch]
📂 Source: Source/Source split/[Tên]/ ([X] chương)
📂 Output: Output/[Tên Project Branch]/
📚 Thuật ngữ imported: [Y] từ Global State
👥 Nhân vật đã biết: [Z] từ Global State

➡️ Bắt đầu:
1️⃣ /translate next — Dịch chương đầu tiên
2️⃣ /translate-wiki — Xem wiki
3️⃣ /translate all — Batch dịch tất cả"
```

---

## ⚠️ QUY TẮC VÀNG

1. ✅ **KHÔNG BAO GIỜ** copy source vào project branch — luôn tham chiếu từ `Source/`
2. ✅ **LUÔN** import từ Global State trước khi bắt đầu
3. ✅ **LUÔN** cập nhật `project_progress.json` ở root
4. ✅ Git commit ở root level, KHÔNG init git riêng trong project branch
