"""Claude API (có web search): đề xuất tin crypto hằng ngày + viết kịch bản JSON cho từng kênh."""
import os, json, re, logging, datetime, requests

log = logging.getLogger("research")
BASE = os.environ.get("ANTHROPIC_BASE", "https://api.anthropic.com")

TEMPLATE_DOC = r"""
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
"""

SCRIPT_RULES = """
QUY TẮC BẮT BUỘC:
1. Chỉ dùng dữ kiện đã kiểm chứng bằng web search, ưu tiên ≥2 nguồn độc lập. Nguồn lệch nhau thì nêu khoảng ước tính và ghi tên nguồn. KHÔNG bịa số, KHÔNG bịa địa chỉ ví/tx hash (dùng "0x••••").
2. Lời đọc (voice) tiếng Việt tự nhiên, câu ngắn, viết số bằng CHỮ (vd "bảy mươi bảy nghìn đô", "EIP bảy nghìn bảy trăm linh hai"), không dùng ký hiệu %, $, viết tắt khó đọc.
3. 5–8 beat, tổng lời đọc ≈ {secs} giây (~4,3 âm tiết/giây). Beat đầu là hook mạnh. KHÔNG viết câu kêu gọi theo dõi (máy tự thêm).
4. Mỗi beat chọn đúng 1 mẫu hình khớp nội dung câu đọc. Dùng ký hiệu token chuẩn (BTC, ETH, USDT, USDC, BNB, SOL…) và tên sàn IN HOA (BINANCE, OKX, BYBIT, COINBASE…) ở các trường token/tokens/sym/logo để máy tự gắn LOGO THẬT. Mỗi video nên có ≥1 cảnh logo (hero có logo) và ≥1 cảnh dẫn nguồn (quote hoặc news_card); con số trên hình phải khớp lời đọc. Đa dạng mẫu, không lặp 1 mẫu quá 2 lần.
5. Không khuyên mua/bán, không dự đoán giá chắc chắn. Giọng trung lập.
6. headline: 2–4 đoạn [text, "normal"|"accent"], tổng ≤ 75 ký tự, có 1 đoạn accent là con số/điểm nóng.
7. source: "Nguồn: ..." ≤ 45 ký tự. ticker_line ≤ 40 ký tự.
8. post.hashtags: 4–6 hashtag không dấu, không có ký tự #.
"""

def _call(api_key, cfg, system, user, max_tokens=8000):
    tools = [{"type": cfg["claude"].get("web_search_tool", "web_search_20250305"), "name": "web_search", "max_uses": cfg["claude"].get("max_searches", 8)}]
    messages = [{"role": "user", "content": user}]
    for _ in range(6):
        r = requests.post(f"{BASE}/v1/messages", timeout=600,
                          headers={"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
                          json={"model": cfg["claude"]["model"], "max_tokens": max_tokens, "system": system, "tools": tools, "messages": messages})
        if r.status_code != 200: raise RuntimeError(f"Claude API {r.status_code}: {r.text[:400]}")
        js = r.json()
        if js.get("stop_reason") == "pause_turn":
            messages.append({"role": "assistant", "content": js["content"]}); continue
        text = "".join(b.get("text", "") for b in js["content"] if b.get("type") == "text")
        cites = sorted({c["url"] for b in js["content"] if b.get("type") == "text" for c in (b.get("citations") or []) if c.get("url")})
        return text, cites
    raise RuntimeError("Claude API dừng giữa chừng quá nhiều lần")

def _json(text):
    m = re.search(r"```(?:json)?\s*(\{.*\}|\[.*\])\s*```", text, re.S)
    raw = m.group(1) if m else text[text.find("{"): text.rfind("}") + 1]
    return json.loads(raw)

def today(cfg):
    import zoneinfo
    return datetime.datetime.now(zoneinfo.ZoneInfo(cfg.get("timezone", "Asia/Ho_Chi_Minh")))

def propose(api_key, cfg, hint=None):
    now = today(cfg); n = cfg.get("proposals_per_day", 5)
    system = "Bạn là biên tập viên tin tức crypto tiếng Việt, cực kỳ cẩn thận về độ chính xác. Luôn kiểm chứng bằng web search."
    user = f"""Hôm nay là {now:%d/%m/%Y %H:%M} (giờ Việt Nam). Tìm {n} tin crypto nổi bật nhất trong 24 giờ qua, phù hợp làm video ngắn 45 giây.
Ưu tiên: sự kiện lớn, có con số rõ ràng, có dữ liệu on-chain, nhiều người quan tâm. Loại bỏ tin đồn chưa xác nhận, quảng cáo dự án.
{('Gợi ý thêm của người dùng: ' + hint) if hint else ''}
Trả về DUY NHẤT một khối ```json``` dạng:
{{"topics": [{{"title": "tiêu đề tiếng Việt ≤80 ký tự", "summary": "2-3 câu", "key_facts": ["dữ kiện có số + nguồn"], "sources": ["url"], "confidence": "cao|trung bình", "onchain_angle": "1 câu: góc on-chain nếu có"}}]}}"""
    text, cites = _call(api_key, cfg, system, user)
    topics = _json(text).get("topics", [])[:n]
    for t in topics: t.setdefault("sources", cites[:4])
    return topics

def write_script(api_key, cfg, topic, channel_key, feedback=None, previous=None):
    ch = cfg["channels"][channel_key]; now = today(cfg)
    system = "Bạn là biên kịch video tin tức crypto ngắn (TikTok/Reels/Shorts) tiếng Việt. Chính xác tuyệt đối, hấp dẫn, nhịp nhanh."
    user = f"""Kênh: {ch['display_name']}. Phong cách: {ch['angle']}
Ngày đăng: {now:%d.%m.%Y}.
CHỦ ĐỀ: {json.dumps(topic, ensure_ascii=False)}
{TEMPLATE_DOC}
{SCRIPT_RULES.replace('{secs}', str(ch.get('target_seconds', 45)))}
{('KỊCH BẢN TRƯỚC: ' + json.dumps(previous, ensure_ascii=False)) if previous else ''}
{('YÊU CẦU SỬA CỦA NGƯỜI DUYỆT (ưu tiên cao nhất): ' + feedback) if feedback else ''}
Kiểm chứng lại dữ kiện bằng web search, rồi trả về DUY NHẤT một khối ```json```:
{{"channel": "{channel_key}", "date": "{now:%d.%m.%Y}", "headline": [["...", "normal"], ["...", "accent"]], "ticker_line": "...", "source": "Nguồn: ...",
 "beats": [{{"voice": "...", "visual": {{"type": "...", ...}}}}],
 "post": {{"title": "≤90 ký tự", "caption": "2-3 câu tóm tắt", "hashtags": ["..."], "sources": ["url"]}}}}"""
    text, cites = _call(api_key, cfg, system, user, max_tokens=10000)
    s = validate(_json(text), channel_key)
    s["post"].setdefault("sources", []); s["post"]["sources"] = list(dict.fromkeys(s["post"]["sources"] + cites))[:6]
    return s

KNOWN = {"quote", "news_card", "hero", "big_number", "stat_cards", "flow", "range", "price_chart", "gauge", "timeline", "tx_card", "graph", "bullets"}
def validate(s, channel_key):
    s["channel"] = channel_key
    if not s.get("headline"): raise ValueError("thiếu headline")
    s["headline"] = [[str(x[0]), x[1] if len(x) > 1 and x[1] in ("normal", "accent") else "normal"] for x in s["headline"]]
    beats = [b for b in s.get("beats", []) if str(b.get("voice", "")).strip()]
    if len(beats) < 3: raise ValueError("kịch bản quá ngắn")
    for b in beats:
        v = b.get("visual") or {}
        if v.get("type") not in KNOWN: b["visual"] = {"type": "bullets", "title": "", "items": [{"text": b["voice"][:60], "tone": "accent"}]}
    s["beats"] = beats[:9]
    s.setdefault("source", ""); s.setdefault("ticker_line", ""); s.setdefault("post", {})
    p = s["post"]; p.setdefault("title", " ".join(x[0] for x in s["headline"])); p.setdefault("caption", ""); p.setdefault("hashtags", [])
    p["hashtags"] = [re.sub(r"[^0-9A-Za-z_]", "", h) for h in p["hashtags"] if re.sub(r"[^0-9A-Za-z_]", "", h)]
    return s

def script_to_text(s, ch_name):
    """bản đọc duyệt trên Telegram (HTML đã escape)"""
    from html import escape as E
    head = E(" ".join(x[0] for x in s["headline"]))
    lines = [f"🎬 <b>{ch_name}</b>", f"<b>Tiêu đề:</b> {head}"]
    if s.get("ticker_line"): lines.append(f"<b>Chữ chạy:</b> {E(s['ticker_line'])}")
    lines.append(f"<b>{E(s.get('source', ''))}</b>\n")
    for i, b in enumerate(s["beats"], 1): lines.append(f"<b>[{i}] {E(str(b['visual'].get('type')))}</b>\n{E(b['voice'])}")
    lines.append("\n<b>Nguồn:</b>\n" + "\n".join(E(u) for u in s["post"].get("sources", [])[:5]))
    return "\n".join(lines)
