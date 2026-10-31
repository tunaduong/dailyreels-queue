# SỔ TAY VIẾT KỊCH BẢN — dành cho Claude

Kho này là hàng đợi giữa **Claude** (viết kịch bản) và **bot trên VPS** (giọng ElevenLabs, dựng video, gửi Telegram duyệt, đăng TikTok nháp + Facebook Reels).

## Luồng
- `inbox/` — Claude đẩy kịch bản JSON vào. Mỗi file là **1 video cho 1 kênh**. Tên file: `YYYYMMDD-HHMM-<channel>.json` (giờ Việt Nam), ví dụ `20261031-0730-chainfolk.json`. **Không sửa hoặc xóa file đã đẩy**, muốn làm lại thì tạo file mới.
- `requests/` — bot ghi yêu cầu của chủ kênh:
  - `*-topic.json` `{type: "topic", text, links}`: làm video từ nội dung này cho **cả 2 kênh** (mỗi kênh một góc).
  - `*-feedback.json` `{type: "feedback", job, channel, note, script}`: viết lại `script` theo `note`, chỉ cho kênh `channel`. File mới đặt tên `...-<channel>-v2.json`.
  - Xử lý xong thì **chuyển file sang `requests/done/`** (tạo file cùng tên trong done/, xóa file gốc).
- `plan/` — lịch tuần chủ kênh gửi qua bot (`/lich`), file `YYYY-Www-*.md`, mỗi dòng 1 ngày (T2…CN). Lấy file mới nhất của tuần hiện tại.
- `samples/` — 2 kịch bản mẫu chuẩn (vụ Binance 30/10/2026). Đọc trước khi viết.

## Hai kênh
- **chainfolk** (ChainFolk): bản tin crypto tổng quan, giọng kiểu bản tin truyền hình, chậm rãi, nghiêm túc. Tập trung vào chuyện gì xảy ra, con số chính, phản ứng thị trường, ảnh hưởng tới người dùng. Có `ticker_line` (dải chữ chạy, ≤40 ký tự).
- **tndgems** (TND GEMS): góc on-chain: dòng tiền, ví cá voi, giao dịch, mốc thời gian chính xác. Giọng nhanh, dồn dập, kiểu điều tra; mở đầu bằng một con số hoặc chi tiết gây tò mò. Tiêu đề sẽ được viết HOA tự động.
- Cùng một tin thì 2 kênh phải có **góc khác nhau**, không trùng câu chữ.

## Mỗi lượt chạy (theo giờ, 8:00–22:00 giờ VN) làm theo thứ tự
1. **Lượt sáng** (nếu hôm nay chưa có file nào trong `inbox/` mang ngày hôm nay): xem `plan/` của tuần này; nếu có mục cho hôm nay thì làm chủ đề đó, nếu không thì tự chọn tin (mục dưới). Viết **2 file**, mỗi kênh 1 file, rồi đẩy vào `inbox/`.
2. Xử lý mọi file trong `requests/` (không tính `done/`): topic → 2 file inbox; feedback → 1 file inbox `-v2` (hoặc `-v3`…). Xong thì chuyển sang `requests/done/`.
3. Không có việc gì thì kết thúc ngay, không tạo file.
4. Trước khi commit: dựng ảnh xem nhanh cho từng file mới (xem CLAUDE.md) và sửa tới khi hiển thị sạch.
5. Commit message ngắn, ví dụ `kịch bản 20261031 chainfolk`. Push lên nhánh `main`.

## Chọn tin hằng ngày
Tìm tin crypto nổi bật trong 24 giờ qua (web search), có con số rõ ràng, nhiều người quan tâm, đã có ≥2 nguồn uy tín xác nhận. Loại tin đồn, tin quảng cáo dự án, tin đã làm trong `inbox/` 3 ngày gần nhất.

## Định dạng JSON (xem samples/)
```json
{"channel": "chainfolk|tndgems", "date": "DD.MM.YYYY",
 "headline": [["đoạn thường", "normal"], ["con số nóng", "accent"]],
 "ticker_line": "chỉ chainfolk", "source": "Nguồn: ...",
 "beats": [{"voice": "câu đọc", "visual": {"type": "...", "...": "..."}}],
 "post": {"title": "≤90 ký tự", "caption": "2-3 câu", "hashtags": ["khongdau"], "sources": ["url"]}}
```
Câu kêu gọi theo dõi ở cuối do máy tự thêm, **không viết vào beats**.


DANH MỤC MẪU HÌNH (visual.type) — chỉ dùng các mẫu sau, đúng tham số:
- hero: {logo?: "BINANCE|BTC|ETH|USDT|..." (logo THẬT của sàn/token, ưu tiên dùng khi tin nói về 1 sàn/token cụ thể), icon: warn|shield|lock|chart|none, tone: alert|good|ice|neutral, kicker: "≤22 ký tự IN HOA", title: "≤24 ký tự", subtitle: "≤60 ký tự", tokens?: ["BTC",...]}
- big_number: {value: số, ring_max?: số, decimals?: 0-3, prefix?: "~|>", suffix: "đơn vị ngắn (phút, %, tỷ USD)", kicker?: "...", caption?: "≤20 ký tự nổi bật", tokens?: [...], tone: bad|good|accent}
- stat_cards: {cards: [1-3 × {label, value: số, decimals?, prefix?, unit, token?: "USDT", stamp?: "≤14 ký tự", tone?: ice|good|bad|neutral}], total?: {label, text}}
- flow: {from: {kicker, title, sub, tokens: [...]}, to: {kicker, title, sub, tone: bad|good|neutral}, amount?: {value: số, decimals, prefix, suffix}, caption?: "mốc thời gian"}
- range: {title, min: số, max: số, unit: "tỷ", markers: [2-4 × {value: số, label: "~3,5 tỷ", who: "tên nguồn"}], notes?: [≤2 câu ngắn]}
- price_chart: {symbol: "BTC|ETH|...", days: 1|7|30, timeframe_label: "30m|4h|1D", start: giá đầu, end: giá cuối, side?: [≤2 × {label, value, tone?}]}   (máy sẽ tự lấy nến thật từ CoinGecko)
- gauge: {title, auto: "fear_greed"} hoặc {title, from: số, to: số, from_label, to_label}
- timeline: {title, events: [2-4 × {time: "04:01", text: "≤45 ký tự", badge?: "+37 phút", tone?: good|bad|ice|accent, token?: "USDT"}]}
- tx_card: {title, status?: "Success", rows: [≤5 × {k, v, tone?: bad|good}], tokens_title?, tokens?: [≤4 × {sym, amount, note}]}
- graph: {title, center: {title, sub}, branches: [2-4 × {label, sub, tone: ice|bad|good, token?}]}
- quote: {who: "Binance | CZ | ...", role: "chức danh · ngày (lược dịch)", text: "phát ngôn ≤120 ký tự, dịch sát nghĩa từ nguồn chính thức", logo?: "BINANCE", tone?: good|bad|neutral}   (CHỈ dùng phát ngôn có thật, ghi rõ nguồn)
- news_card: {title?: "Báo chí quốc tế đưa tin", items: [1-3 × {outlet: "Bloomberg", date: "30/10/2026", headline: "tiêu đề GỐC đúng nguyên văn của bài báo"}]}   (dẫn nguồn uy tín, tăng độ tin cậy)
- bullets: {title, items: [2-4 × {text: "≤45 ký tự", tone: good|bad|ice|accent}]}

QUY TẮC BẮT BUỘC:
1. Chỉ dùng dữ kiện đã kiểm chứng bằng web search, ưu tiên ≥2 nguồn độc lập. Nguồn lệch nhau thì nêu khoảng ước tính và ghi tên nguồn. KHÔNG bịa số, KHÔNG bịa địa chỉ ví/tx hash (dùng "0x••••").
2. Lời đọc (voice) tiếng Việt tự nhiên, câu ngắn, viết số bằng CHỮ (vd "bảy mươi bảy nghìn đô", "EIP bảy nghìn bảy trăm linh hai"), không dùng ký hiệu %, $, viết tắt khó đọc.
3. 5–8 beat, tổng lời đọc ≈ 45 giây (~4,3 âm tiết/giây). Beat đầu là hook mạnh. KHÔNG viết câu kêu gọi theo dõi (máy tự thêm).
4. Mỗi beat chọn đúng 1 mẫu hình khớp nội dung câu đọc. Dùng ký hiệu token chuẩn (BTC, ETH, USDT, USDC, BNB, SOL…) và tên sàn IN HOA (BINANCE, OKX, BYBIT, COINBASE…) ở các trường token/tokens/sym/logo để máy tự gắn LOGO THẬT. Mỗi video nên có ≥1 cảnh logo (hero có logo) và ≥1 cảnh dẫn nguồn (quote hoặc news_card); con số trên hình phải khớp lời đọc. Đa dạng mẫu, không lặp 1 mẫu quá 2 lần.
5. Không khuyên mua/bán, không dự đoán giá chắc chắn. Giọng trung lập.
6. headline: 2–4 đoạn [text, "normal"|"accent"], tổng ≤ 75 ký tự, có 1 đoạn accent là con số/điểm nóng.
7. source: "Nguồn: ..." ≤ 45 ký tự. ticker_line ≤ 40 ký tự.
8. post.hashtags: 4–6 hashtag không dấu, không có ký tự #.
9. Kiểm tra JSON hợp lệ trước khi đẩy (`python3 -c "import json;json.load(open('file'))"`).
