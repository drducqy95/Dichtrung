# Phase 04: Testing và Export Plugin

Status: ⬜ Pending
Dependencies: phase-03-extension-logic.md

## Objective
Đảm bảo tất cả tính năng hoạt động liền mạch và build ra bundle zip cuối cùng để cài vào điện thoại (hoặc up lên Github Release).

## Requirements

### Functional
- [ ] Khởi chạy vitest hoặc vbook-vscode-tester để test trực tiếp vào các link truyện.
- [ ] Fake Request hoặc mở Extension Maker lên điện thoại check UI.
- [ ] Đảm bảo text markdown sau khi build ko bị vỡ hoặc sót mã HTML lạ (đặc biệt CSS Darkmode phải mượt).
- [ ] Nén plugin thành `.zip`.

## Implementation Steps
1. [ ] Cài đặt các scripts test (nếu cần mock `fetch`).
2. [ ] Render DOM bằng VS Code Extension.
3. [ ] Mở VBook, thêm URL dev mode hoặc nạp zip.
4. [ ] Khắc phục lỗi font hoặc khoảng trắng.

## Files to Create/Modify
- `ext-dichtrung.zip`

## Test Criteria
- [ ] Đọc thử thành công chapter đầu tiên của "Ác Linh Quốc Gia" trên vBook.

---
Plan Complete!
