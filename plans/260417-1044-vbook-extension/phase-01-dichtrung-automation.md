# Phase 01: Cập nhật Dichtrung Workflow (toc.json)

Status: ⬜ Pending
Dependencies: None

## Objective
Thay vì để Vbook Extension load danh sách chapter từ Github Contents API (bị giới hạn rate limit 60 request/h), ta cần tự động hoá Repository `drducqy95/Dichtrung` sao cho mỗi branch truyện sẽ luôn có một file `toc.json` được sinh tự động.

## Requirements

### Functional
- [ ] Phân tích file script `Script/branch_scaffold.py` hoặc luồng Workflow đang quản lý Dichtrung.
- [ ] Thêm logic: Mỗi khi project được "save-brain" hoặc "/ebook", tự cập nhật/tạo file `toc.json` vào folder `Output/[Tên Truyện]/toc.json`.
- [ ] File `toc.json` cần có định dạng đơn giản lưu tên chương và đường dẫn tương đối (hoặc chỉ tên file `.md`).
- [ ] Áp dụng tự động sinh `toc.json` cho tất cả các truyện (`M1` -> `M7`) hiện tại để test Extension.

### Non-Functional
- [ ] Code Python hiệu quả, chạy tự động theo file `project_progress.json`.

## Implementation Steps
1. [ ] Đọc và sửa script build hiện tại (chẳng hạn `D:\Dichtrung\Script\branch_scaffold.py`).
2. [ ] Thêm hàm `generate_toc_json(branch, output_dir)`.
3. [ ] Cập nhật file `toc.json` cho 7 bộ truyện đang có.

## Files to Create/Modify
- `Script/branch_scaffold.py` (hoặc script quản lý tương ứng) - Thêm logic sinh `toc.json`

## Test Criteria
- [ ] `Output/Ac Linh Quoc Gia/toc.json` tồn tại và chứa cấu trúc JSON hợp lệ.

---
Next Phase: phase-02-extension-setup.md
