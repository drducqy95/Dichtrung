# Dichtrung — Repo Dịch Thuật Tổng Hợp

Mono-repo chứa **39+ source truyện** với hệ thống workflow dịch thuật tích hợp.

## Cấu Trúc

```
Dichtrung/
├── Source/
│   ├── Source full/          ← File HTML gốc (bất biến)
│   └── Source split/         ← Chương đã tách (MD)
├── Global State/
│   ├── global_config.json    ← Quy tắc dịch chung
│   ├── global_characters.json← Nhân vật tổng hợp
│   └── global_glossary.json  ← Thuật ngữ tổng hợp
├── Output/
│   └── [Project Branch]/     ← Mỗi truyện = 1 branch
│       ├── *.json            ← State files
│       ├── drafts/           ← Bản nháp
│       ├── output/           ← Bản dịch cuối
│       └── ebook/            ← EPUB/PDF/HTML
└── Script/
    └── Tachchuong.py         ← Tool tách chương
    └── strict_engine/        ← Động cơ dịch thuật lõi thép (Python)
```

## ⚙️ Strict Translation Engine

Kể từ v2.0, Dichtrung sử dụng **Strict Translation Engine** — một State-machine viết bằng Python để quản lý toàn bộ vòng đời dịch thuật. AI không còn tự do đọc/ghi file tùy ý, mà phải tuân thủ nghiêm ngặt quy trình 3 bước (Orchestrated Pipeline):

1. **Preflight (Chuẩn bị):** Quét file gốc, trích xuất từ vựng, đóng gói thành `context_pack.json`. Kiểm tra tính vẹn toàn dữ liệu (Precheck Gate).
2. **AI Translation:** AI chỉ được phép đọc `context_pack.json` và trả về kết quả dịch dưới định dạng JSON (`translation_result.schema.json`).
3. **Postflight (Hậu kỳ):** Validate JSON, chặn CJK (Hán tự), cảnh báo độ dài, ghi file Markdown an toàn (Atomic Write), và cập nhật State/Progress (Postcheck & Statecheck Gates).

*Mọi thao tác dịch thuật đều bị khoá bằng File Locking để chống Race Condition.*

## 🚀 Workflow Lệnh (Slash Commands)

Các lệnh dưới đây đã được tích hợp chặt chẽ với Strict Translation Engine:

| Lệnh | Mô tả |
|-------|-------|
| `/translate-setup [tên]` | Khởi tạo project branch mới (Tự động tạo thư mục `runtime/` cho Engine) |
| `/translate [branch] [chapter]` | Dịch một chương cụ thể (Tự động gọi Preflight → Dịch → Postflight) |
| `/translate next` | Dịch chương tiếp theo của truyện đang active |
| `/translate-wiki [branch]` | Xem wiki thế giới quan của truyện |
| `/ebook [branch]` | Build ebook (EPUB/PDF/HTML) khi hoàn thành |
| `/sync-state [branch]` | Cập nhật từ vựng từ nhánh cục bộ lên Global State |

## ⚠️ Quy Tắc Vàng (Prime Directives)

- ✅ Output **hoàn toàn tiếng Việt** — không chứa ký tự CJK (Kiểm soát cứng bởi Postflight Gate).
- ✅ Source **bất biến** — không copy vào project branch (Chỉ lưu ở thư mục gốc).
- ✅ Dữ liệu dịch thuật **chỉ đọc từ Context Pack** — AI không tự mò mẫm các file JSON khác.
- ✅ State **tự động cập nhật** an toàn thông qua Atomic Write.

## 🏁 Bắt Đầu Dịch Thuật

1. Đặt file HTML vào `Source/Source full/` và dùng `Tachchuong.py` để tách.
2. Chạy `/translate-setup [Tên truyện]` để khởi tạo môi trường (hoặc `/init-branch` nếu chỉ setup repo).
3. Chạy `/translate next` để AI bắt đầu quá trình dịch (AI sẽ tự kích hoạt Engine).
4. Khi dịch xong các chương, chạy `/sync-state` để đồng bộ từ vựng lên máy chủ cục bộ.
5. Cuối cùng, chạy `/ebook` để xuất bản.
