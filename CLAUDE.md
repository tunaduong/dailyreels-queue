# Hướng dẫn cho Claude trong kho này
Đây là hàng đợi kịch bản video cho 2 kênh ChainFolk & TND GEMS. **Đọc `SCRIPT_GUIDE.md` trước khi làm bất cứ việc gì** — trong đó có luồng xử lý, danh mục mẫu hình và quy tắc.

Trước khi đẩy kịch bản, LUÔN dựng thử ảnh xem nhanh và tự soát lỗi hiển thị:
```
python3 engine/scripts/render_sample.py inbox/<file>.json --offline
```
Mở `engine/data/test/<tên>/sheet.png` (ô đầu tiên là ảnh bìa, ảnh gốc ở `cover.png`), kiểm tra: chữ tràn/chồng, số trên hình khớp lời đọc, không có cảnh trống; ảnh bìa chữ to, không tràn, đọc được ở cỡ nhỏ. Sửa kịch bản rồi dựng lại tới khi sạch. `engine/data/` không commit.
