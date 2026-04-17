---
description: Khởi tạo project dịch thuật mới trong repo Dichtrung (override /translate-setup gốc)
---

# WORKFLOW: /translate-setup — Dichtrung Setup v1.0

Override workflow `/translate-setup` toàn cục cho cấu trúc mono-repo Dichtrung.

---

## ⚠️ PRIME DIRECTIVE

1. Đọc `global_skills/skills/translation/SKILL.md` → hiểu kiến trúc
2. Đọc `d:\Dichtrung\Global State\global_config.json` → quy tắc mặc định
3. Đọc `d:\Dichtrung\Global State\global_glossary.json` → thuật ngữ có sẵn
4. Đọc `d:\Dichtrung\Global State\global_characters.json` → nhân vật đã biết
5. Đọc `~/.gemini/antigravity/translation/global_pronouns.json` → common pronouns

---

## Quy Trình

### Bước 0: Nhận Input

```
User: /translate-setup [Tên truyện]
→ Tìm source split trong Source/Source split/[Tên]/
→ Nếu chưa có → gợi ý chạy /init-branch trước

User: /translate-setup
→ Liệt kê các project branch đã có trong Output/
→ Hoặc liệt kê source chưa setup → hỏi user chọn
```

### Bước 1: Thu Thập Thông Tin

Giống workflow gốc, hỏi user:
- Tên project, ngôn ngữ nguồn/đích, thể loại, sub-genre
- Xử lý tên riêng, thư mục nguồn

**Mặc định từ `global_config.json`:**
- `target_language`: vi
- `name_setting`: phien_am (cho eastern_fiction)
- `pronoun_mode`: hybrid
- `sanitization.ban_cjk_in_output`: true

### Bước 2: Tạo Project Branch

**Thư mục:** `d:\Dichtrung\Output\[Tên Project Branch]\`

Tạo đầy đủ cấu trúc state files + thư mục con (y hệt workflow gốc).

**KHÁC BIỆT:**
- KHÔNG tạo `source/` trong project branch
- Source tham chiếu: `d:\Dichtrung\Source\Source split\[Tên]\`
- Thêm field `source_ref` trong `translation_config.json`:
  ```json
  {
    "source_ref": {
      "full": "Source/Source full/[tên file].html",
      "split": "Source/Source split/[Tên]/",
      "description": "Source nằm ở thư mục gốc, KHÔNG copy vào branch"
    }
  }
  ```

### Bước 3: Import Từ Global State

1. **Glossary:** Import từ `Global State/global_glossary.json` (lọc theo `source_language` + `category`)
2. **Characters:** Import nhân vật đã biết từ `Global State/global_characters.json` (nếu cùng source)
3. **Pronouns:** Import từ `~/.gemini/antigravity/translation/global_pronouns.json`

### Bước 4: Pre-Scan Source

Giống workflow gốc — quét `Source/Source split/[Tên]/` bằng `source_analyzer.py`.

### Bước 5: Báo Cáo

Giống workflow gốc + thêm:
```
📂 Source: Source/Source split/[Tên]/ (THAM CHIẾU, không copy)
📂 Branch: Output/[Tên Project Branch]/
🔄 Global Import: [X] thuật ngữ, [Y] nhân vật
```

---

## ⚠️ QUY TẮC VÀNG

1. ✅ **KHÔNG** tạo thư mục `source/` trong project branch
2. ✅ **LUÔN** import từ Global State thay vì global_skills glossary
3. ✅ **LUÔN** thêm `source_ref` vào `translation_config.json`
4. ✅ **LUÔN** áp dụng quy tắc từ `global_config.json`
