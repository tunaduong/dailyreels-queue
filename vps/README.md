# Bot video crypto — ChainFolk & TND GEMS

## Ai làm gì
| | Việc |
|---|---|
| **Claude** (gói Pro của bạn, lịch tự động) | 8:00 mỗi sáng chọn tin (hoặc làm theo lịch tuần bạn gửi), kiểm chứng nguồn, viết kịch bản theo mẫu 2 kênh. Mỗi giờ (8:00–22:00) xử lý yêu cầu mới / yêu cầu sửa của bạn |
| **Kho GitHub riêng tư** | Đường chuyền kịch bản giữa Claude và VPS |
| **VPS (bot này)** | Nhận kịch bản → giọng ElevenLabs → dựng video theo khung kênh → gửi Telegram → bạn bấm ✅ → đăng **TikTok (nháp)** + **Facebook Reels** → báo kết quả |
| **Bạn** | Xem video trên Telegram: **✅ Đăng** · **✏️ Sửa** (gõ yêu cầu) · **❌ Bỏ** |

Lệnh trên Telegram:
- Gửi nội dung hoặc link: nhờ Claude làm video về nội dung đó.
- `/lich`: gửi danh sách tin cho cả tuần.
- `/trangthai`: xem tiến độ.

---

## Cài đặt (1 lần)

### Bước 1: chuẩn bị 3 thứ
1. **Bot Telegram:** nhắn @BotFather, gõ `/newbot`, đặt tên, rồi copy token.
2. **Kho GitHub:**
   - Đăng ký github.com (miễn phí) và tạo kho **Private** tên `dailyreels-queue`.
   - Vào Settings → Developer settings → **Fine-grained tokens** → Generate. Chọn *Only select repositories*, chọn `dailyreels-queue`, đặt quyền **Contents: Read and write**, rồi copy token.
3. **ElevenLabs API key:** vào elevenlabs.io → Profile → API Keys.

### Bước 2: đưa lên VPS và chạy cài đặt
```bash
# trên máy tính (PowerShell):
scp $HOME\Downloads\dailyreels.zip root@IP_VPS:/root/
# trong terminal VPS:
apt-get install -y unzip && cd /root && unzip -o dailyreels.zip && cd dailyreels && bash setup.sh
```
`setup.sh` hỏi lần lượt: token Telegram (rồi bảo bạn nhắn `/start` cho bot để tự lấy Chat ID), tên kho và token GitHub, khóa ElevenLabs, và cho bạn **chọn giọng cho từng kênh** theo số thứ tự. Mỗi mục được kiểm tra ngay khi nhập. Xong là bot chạy.

Lúc này bot đã gửi video về Telegram, nút là **"✅ Xong — tôi tự đăng"** (kèm caption để copy). Khi muốn bot tự đăng, làm tiếp Bước 3.

### Bước 3: kết nối nền tảng đăng (làm lúc nào cũng được)
**TikTok (đăng vào hộp nháp):**
1. Vào developers.tiktok.com, tạo App, thêm *Login Kit* và *Content Posting API* (scope `video.upload`), khai báo một Redirect URI dạng https.
2. Trên VPS, chạy cho từng kênh:
   ```bash
   cd /opt/dailyreels && .venv/bin/python scripts/auth_tiktok.py CLIENT_KEY CLIENT_SECRET https://redirect-cua-ban/ data/tokens/tiktok_chainfolk.json
   ```

**Facebook Reels:**
1. Vào developers.facebook.com, tạo App Business với các quyền `pages_show_list`, `pages_read_engagement`, `pages_manage_posts`.
2. Lấy **Page access token dài hạn** cho từng Fanpage và điền vào `/opt/dailyreels/.env` (`FB_PAGE_TOKEN_CHAINFOLK`, `FB_PAGE_TOKEN_TNDGEMS`).
3. Điền `page_id` vào `config.yaml`.

Sau đó, trong `/opt/dailyreels/config.yaml`, đổi `enabled: false` thành `enabled: true` cho nền tảng đã kết nối, rồi chạy `systemctl restart dailyreels`. Nút trên Telegram sẽ đổi thành **"✅ Đăng: TikTok (nháp) + Facebook Reels"**.

---

## Lệnh hữu ích trên VPS
| | |
|---|---|
| Xem log | `journalctl -u dailyreels -f` |
| Khởi động lại | `systemctl restart dailyreels` |
| Đổi khóa / giọng | `systemctl stop dailyreels && /opt/dailyreels/.venv/bin/python /opt/dailyreels/scripts/wizard.py && systemctl start dailyreels` |
| Cập nhật code mới | giải nén bản mới, chạy lại `bash setup.sh` (giữ nguyên khóa và dữ liệu) |
| Xem thử khung hình | `/opt/dailyreels/.venv/bin/python /opt/dailyreels/scripts/render_sample.py /opt/dailyreels/samples/chainfolk_binance.json` |

## Lưu ý
- **TikTok để chế độ nháp (`mode: inbox`):** bạn bấm Đăng trong app trên điện thoại. Cách này tránh bị TikTok xếp kênh vào nhóm nước ngoài, vì VPS đặt ở Malaysia, và không cần qua kiểm duyệt app.
- **Facebook:** giới hạn 30 Reels đăng qua API cho mỗi Page trong 24 giờ.
- **Nhãn nội dung AI** được bật sẵn.
- **Khi CoinGecko lỗi:** nếu không lấy được dữ liệu, biểu đồ tự chuyển sang dạng minh họa và có ghi chú trên hình.
- **Mã nguồn còn kèm module YouTube và Instagram** (`app/publish/`) nếu sau này muốn mở thêm.
