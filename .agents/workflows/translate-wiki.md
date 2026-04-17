---
description: Xem wiki data thế giới quan cho project branch trong Dichtrung (override /translate-wiki gốc)
---

# WORKFLOW: /translate-wiki — Dichtrung Wiki Viewer v1.0

Override workflow `/translate-wiki` toàn cục cho cấu trúc mono-repo Dichtrung.

---

## ⚠️ PRIME DIRECTIVE

1. Đọc `global_skills/skills/translation/SKILL.md`
2. Đọc `global_skills/skills/translation/worldbuilding-tracker.md`
3. Xác định project branch:
   - `/translate-wiki [branch] [lệnh]` → branch cụ thể
   - `/translate-wiki [lệnh]` → branch hiện tại từ context
4. Load data TỪ `d:\Dichtrung\Output\[Branch]\`:
   - `characters.json`, `worldbuilding.json`, `context.json`

---

## Override Dispatch

Tất cả lệnh giống workflow gốc, chỉ đổi data source:

| Lệnh | Data Source |
|-------|-----------|
| `/translate-wiki [branch] character all` | `Output/[Branch]/characters.json` |
| `/translate-wiki [branch] faction all` | `Output/[Branch]/worldbuilding.json` |
| `/translate-wiki [branch] weapon all` | `Output/[Branch]/worldbuilding.json` |
| `/translate-wiki global character` | `Global State/global_characters.json` |
| `/translate-wiki global glossary` | `Global State/global_glossary.json` |
| ... | ... |

## Tính Năng Bổ Sung: Xem Liên Project

```
/translate-wiki global character → Xem tất cả nhân vật từ mọi project
/translate-wiki global glossary → Xem tất cả thuật ngữ từ mọi project
```

---

## Quy Trình Dispatch

1. Nhận input → xác định branch + lệnh
2. Đọc template từ `global_workflows/wiki-templates/[template].md`
3. Load data từ `Output/[Branch]/` hoặc `Global State/`
4. Render output → artifact markdown
5. Kiểm tra illustration triggers

---

## ⚠️ QUY TẮC VÀNG

1. ✅ **LUÔN** load data từ `Output/[Branch]/` (không phải root project)
2. ✅ **HỖ TRỢ** xem liên project qua `global` keyword
3. ✅ **ĐÚNG TEMPLATE** — đọc template trước khi render
4. ✅ **KHÔNG PHỎNG ĐOÁN** — chỉ hiển thị data đã có
