# Phase 03: Xây dựng JS Handlers

Status: ⬜ Pending
Dependencies: phase-02-extension-setup.md

## Objective
Hoàn thiện logic của 4 script chính cho Vbook Extension: `home.js`, `detail.js`, `toc.js` và `chap.js` để lấy dữ liệu từ Dichtrung Repository.

## Requirements

### Functional
- [ ] `home.js`: Fetch `project_progress.json`, parse json, trả về danh sách các object (truyện) `[{name, link, cover, description}]`.
- [ ] `detail.js`: Nhận link (brand name), hiển thị chi tiết (lấy từ dữ liệu truyện đã có).
- [ ] `toc.js`: Fetch `toc.json` từ `Output/[BRANCH]/toc.json`. Parse JSON và trả về danh sách HTML/Chapter array.
- [ ] `chap.js`: Lấy đường dẫn file markdown, fetch nội dung `.md`, dùng regex đơn giản biến thành `<p>` text hoặc convert sang HTML chuẩn VBook.

### Non-Functional
- [ ] Code tuân thủ tiêu chuẩn bất đồng bộ với `async/await`.
- [ ] Xử lý try/catch đàng hoàng để tránh crash VBook.

## Implementation Steps
1. [ ] Viết hàm `home.js`.
2. [ ] Viết hàm `detail.js`.
3. [ ] Viết hàm `toc.js` (fetch `toc.json`).
4. [ ] Viết hàm `chap.js` (render text từ file *.md).

## Files to Create/Modify
- `d:\APP\ext-dichtrung\src\home.js`
- `d:\APP\ext-dichtrung\src\detail.js`
- `d:\APP\ext-dichtrung\src\toc.js`
- `d:\APP\ext-dichtrung\src\chap.js`
- `d:\APP\ext-dichtrung\src\search.js` (Tuỳ chọn: tìm kiếm truyện trong project_progress)

## Test Criteria
- [ ] Parsing logic không sinh ra lỗi Exception khi chạy bằng vscode tester.

---
Next Phase: phase-04-testing.md
