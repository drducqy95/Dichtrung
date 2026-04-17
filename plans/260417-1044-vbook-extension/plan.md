# Plan: Vbook Extension Dichtrung

Created: 2026-04-17T10:44:00+07:00
Status: 🟡 In Progress

## Overview
Xây dựng Extension Vbook đọc truyện thông qua Raw Github CDN từ Repository Dichtrung. Triển khai kiến trúc tự động hóa sinh `toc.json` phía Dichtrung repo để Vbook Extension không gặp phải giới hạn Rate Limit của GitHub API, tăng tính ổn định tối đa cho người dùng.

## Tech Stack
- Frontend (vBook App): JavaScript ES6, Promise/Async/Fetch API
- Backend (Data Source): GitHub CDN (raw.githubusercontent.com)
- Dạng Dữ liệu: JSON, Markdown

## Phases

| Phase | Name | Status | Progress |
|-------|------|--------|----------|
| 01 | Cập nhật Dichtrung Workflow (toc.json) | ⬜ Pending | 0% |
| 02 | Khởi tạo Vbook Extension Project | ⬜ Pending | 0% |
| 03 | Xây dựng JS Handlers (home, detail, toc, chap) | ⬜ Pending | 0% |
| 04 | Testing và Export Plugin Vbook | ⬜ Pending | 0% |

## Quick Commands
- Start Phase 1: `/code phase-01`
- Check progress: `/next`
- Save context: `/save-brain`
