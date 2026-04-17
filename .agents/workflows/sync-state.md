---
description: Đồng bộ state cục bộ từ project branch lên Global State
---

# WORKFLOW: /sync-state — Đồng Bộ State Dichtrung v1.0

Quy trình đứng riêng để đồng bộ state files từ project branch lên Global State. Được gọi tự động sau mỗi chương trong `/translate`, hoặc thủ công bởi user.

---

## ⚠️ PRIME DIRECTIVE

1. Xác định project branch:
   - `/sync-state [branch]` → branch cụ thể
   - `/sync-state all` → sync tất cả branch
   - `/sync-state` → branch hiện tại từ context
2. **Working dir:** `d:\Dichtrung\Output\[Branch]\`
3. **Target:** `d:\Dichtrung\Global State\`

---

## Quy Trình Đồng Bộ

### 1. Sync Glossary

```
Source: Output/[Branch]/glossary.json
Target: Global State/global_glossary.json

Quy tắc:
- Entry mới (source_term chưa tồn tại) → THÊM VÀO, gắn source_project
- Entry đã tồn tại, cùng source_project → CẬP NHẬT nếu confidence cao hơn
- Entry đã tồn tại, KHÁC source_project → GIỮ NGUYÊN entry cũ, thêm note cross-ref
- Entry có locked=true ở global → KHÔNG GHI ĐÈ
```

### 2. Sync Characters

```
Source: Output/[Branch]/characters.json
Target: Global State/global_characters.json

Quy tắc:
- Nhân vật mới → THÊM VÀO, gắn source_project + ghi chú đầy đủ
- Nhân vật cùng tên, cùng project → CẬP NHẬT thông tin mới nhất
- Nhân vật cùng tên, KHÁC project → THÊM RIÊNG (có thể trùng tên ở truyện khác)
- Ghi chú: tên gốc, tên dịch, giới tính, vai trò, mô tả ngắn, chương xuất hiện
```

### 3. Cross-Check

```
- Kiểm tra không có entry trùng key trong global_glossary
- Kiểm tra không có nhân vật trùng ID trong global_characters
- Kiểm tra JSON hợp lệ sau mỗi lần ghi
```

### 4. Báo Cáo

```
"🔄 GLOBAL STATE SYNC HOÀN TẤT

📖 Branch: [Tên]
📚 Glossary: +[X] mới, ~[Y] cập nhật, =[Z] giữ nguyên
👥 Characters: +[A] mới, ~[B] cập nhật

✅ Global State đã nhất quán."
```

---

## Sync All Mode

Khi `/sync-state all`:
1. Liệt kê tất cả branch trong `Output/`
2. Sync từng branch theo thứ tự
3. Sau cùng: cross-check toàn bộ Global State
4. Báo cáo tổng hợp

---

## ⚠️ QUY TẮC VÀNG

1. ✅ **APPEND ONLY** cho global_characters — không xóa nhân vật
2. ✅ **MERGE SMART** cho global_glossary — không ghi đè locked entries
3. ✅ **VALIDATE JSON** sau mỗi lần ghi
4. ✅ **LOG** kết quả sync vào `Output/[Branch]/logs/`
