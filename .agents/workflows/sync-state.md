---
description: Đồng bộ state cục bộ từ project branch lên Global State
---

# WORKFLOW: /sync-state — Đồng Bộ State Dichtrung v1.0

Quy trình đứng riêng để đồng bộ state files từ project branch lên Global State. Được gọi tự động sau mỗi chương trong `/translate`, hoặc thủ công bởi user.

---

## ⚠️ PRIME DIRECTIVE

**Script chính thức:** `D:\Dichtrung\Script\sync_state.py`

Luôn dùng script Python thay vì thực hiện thủ công. Script đã xử lý:
- Cả hai format glossary (dict với `entries` key, hoặc array thuần)
- Cả hai format characters (dict với `characters` key, hoặc array thuần)
- Deduplication, confidence ranking, locked entry protection
- Ghi log tự động vào `Output/[Branch]/logs/`

---

## Lệnh Thực Thi

### Sync tất cả branch

// turbo
```bash
python "D:\Dichtrung\Script\sync_state.py"
```

### Sync branch cụ thể

// turbo
```bash
python "D:\Dichtrung\Script\sync_state.py" --branch "[BRANCH_NAME]"
```

Ví dụ:
```bash
python "D:\Dichtrung\Script\sync_state.py" --branch "Linh Hon Negary_Hu Minh"
```

### Kết hợp scaffold + sync (khuyến nghị sau mỗi phiên dịch)

// turbo
```bash
python "D:\Dichtrung\Script\branch_scaffold.py" --all && python "D:\Dichtrung\Script\sync_state.py"
```

---

## Quy Tắc Merge (được xử lý tự động bởi script)

### Glossary
- Entry mới (source_term chưa tồn tại) → THÊM VÀO, gắn source_project
- Entry đã tồn tại, cùng source_project → CẬP NHẬT nếu confidence cao hơn
- Entry đã tồn tại, KHÁC source_project → GIỮ NGUYÊN entry cũ
- Entry có locked=true ở global → KHÔNG GHI ĐÈ

### Characters
- Nhân vật mới → THÊM VÀO, gắn source_project + ghi chú đầy đủ
- Nhân vật cùng tên, cùng project → CẬP NHẬT thông tin mới nhất
- Nhân vật cùng tên, KHÁC project → THÊM RIÊNG (có thể trùng tên ở truyện khác)

---

## Báo Cáo Mẫu

```
🔄 GLOBAL STATE SYNC HOÀN TẤT

📖 Branch: Linh Hon Negary_Hu Minh
📚 Glossary: +50 mới, ~35 cập nhật, =153 giữ nguyên
👥 Characters: +8 mới, ~12 cập nhật

✅ Global State đã nhất quán.
Global glossary: 883 entries | Global characters: 269 characters
```

---

## ⚠️ QUY TẮC VÀNG

1. ✅ **APPEND ONLY** cho global_characters — không xóa nhân vật
2. ✅ **MERGE SMART** cho global_glossary — không ghi đè locked entries
3. ✅ **VALIDATE JSON** sau mỗi lần ghi (script tự xử lý)
4. ✅ **LOG** kết quả sync vào `Output/[Branch]/logs/sync-state-*.log`
5. ✅ **DUAL FORMAT SUPPORT** — script xử lý cả array thuần lẫn dict với key
