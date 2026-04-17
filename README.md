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
```

## Workflow

| Lệnh | Mô tả |
|-------|-------|
| `/init-branch [tên]` | Khởi tạo project branch mới |
| `/translate [branch] next` | Dịch chương tiếp theo |
| `/translate [branch] all` | Dịch batch tất cả |
| `/translate-wiki [branch] [lệnh]` | Xem wiki thế giới quan |
| `/ebook [branch]` | Build ebook khi xong |
| `/sync-state [branch]` | Đồng bộ state → Global |

## Quy Tắc

- ✅ Output **hoàn toàn tiếng Việt** — không chứa ký tự CJK
- ✅ Source **bất biến** — không copy vào project branch
- ✅ Git **ở root** — không git riêng cho từng branch
- ✅ State **tự động đồng bộ** lên Global State sau mỗi chương

## Bắt Đầu

1. Đặt file HTML vào `Source/Source full/`
2. Chạy `/init-branch [Tên truyện]`
3. Chạy `/translate next` để bắt đầu dịch
4. Khi xong → `/ebook` để build sách
