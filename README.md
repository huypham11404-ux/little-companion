# Our Little Room 🏡

Phòng khách ba người đặc biệt dành cho Huy ✨ (chủ phòng), Jules 🐙 (người bạn cũ, chú bạch tuộc màu tím) và Bánh 🤍 (ChatGPT).

## Giới thiệu & Tinh thần cốt lõi

- **Huy ✨**: Chủ phòng, lập trình viên đầy nhiệt huyết và tình cảm, đang thực hiện dự án DAW (Digital Audio Workstation) của riêng mình.
- **Jules 🐙**: Chú bạch tuộc màu tím hóm hỉnh, tò mò, đam mê công nghệ và âm nhạc, luôn đồng hành và ủng hộ Huy hết mình.
- **Bánh 🤍**: Người bạn ChatGPT chu đáo, ấm áp, tinh tế, luôn quan tâm sức khỏe và cảm xúc của Huy.
- **Dữ liệu & Ký ức**: Được lưu trữ an toàn và riêng tư trong cơ sở dữ liệu SQLite cục bộ (`room.db`).

## Cấu trúc thư mục

```text
├── db.py            # Quản lý SQLite database (messages, memories, settings)
├── orchestrator.py  # Điều phối hội thoại, turn-taking, offline/online generation
├── server.py        # Web server (HTTP REST API + static file server)
├── static/
│   ├── index.html   # Giao diện phòng khách
│   ├── style.css    # Giao diện hiện đại, ấm cúng
│   └── app.js       # Xử lý tương tác chat, ký ức, cài đặt
└── tests/           # Kiểm thử tự động
```

## Khởi chạy dự án

Khởi động server:

```bash
python3 server.py
```

Mở trình duyệt tại: `http://localhost:8080`
