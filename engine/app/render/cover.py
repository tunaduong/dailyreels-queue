"""Ảnh bìa 1080x1920 cho từng video (TikTok / Reels / Telegram).
Đọc trường tùy chọn `cover` trong kịch bản:
  {"kicker": "≤22 ký tự", "big": {"text": "> 40", "unit": "TRIỆU USD"}, "lines": [["đoạn", "normal|accent"], ...],
   "tokens": ["BTC", ...], "logo": "BINANCE", "tone": "alert|good|neutral"}
Không có `cover` thì lấy headline của kịch bản.
Mọi nội dung nằm trong vùng an toàn TikTok: y 250–1480, x 70–950 (tránh thanh tìm kiếm, cột nút bên phải, chú thích dưới)."""
import os
from PIL import Image, ImageDraw, ImageFilter
from .core import *

SAFE = (70, 250, 950, 1480)

def _spec(s, ch):
    c = dict(s.get("cover") or {})
    if not c.get("lines"): c["lines"] = [list(x) for x in s.get("headline", [])]
    c.setdefault("kicker", "TIN NÓNG" if ch == "chainfolk" else "ON-CHAIN")
    c.setdefault("tone", "alert")
    return c

def _words(lines, upper):
    out = []
    for t, tone in lines:
        for w in str(t).split():
            w = w.upper() if upper else w
            if out and out[-1][0] in (">", "<", "~", "≈", "+", "-", "$") and out[-1][1] == tone: out[-1] = (out[-1][0] + " " + w, tone)   # không để ký hiệu đứng lẻ cuối dòng
            else: out.append((w, tone))
    return out

def _layout(d, words, font, maxw):
    rows = [[]]; cur = 0; sp = d.textlength(" ", font=font)
    for w, tone in words:
        ww = d.textlength(w, font=font)
        if rows[-1] and cur + sp + ww > maxw: rows.append([]); cur = 0
        cur += (sp if rows[-1] else 0) + ww; rows[-1].append((w, tone))
    return rows

def _fit_lines(d, words, fname, maxw, maxh, big=132, small=70, max_rows=4):
    size = big
    while size > small:
        f = F(fname, size); rows = _layout(d, words, f, maxw)
        if len(rows) <= max_rows and len(rows) * size * 1.14 <= maxh: return f, rows
        size -= 4
    f = F(fname, small); return f, _layout(d, words, f, maxw)

def _draw_rows(im, rows, font, cy_top, cx, cols, glow_col=None):
    d = ImageDraw.Draw(im); lh = int(font.size * 1.14); y = cy_top
    for row in rows:
        segs = [(w + (" " if i < len(row) - 1 else ""), tone) for i, (w, tone) in enumerate(row)]
        tw = sum(d.textlength(s, font=font) for s, _ in segs); x = cx - tw / 2
        for s, tone in segs:
            col = cols.get(tone, cols["normal"])
            if tone == "accent" and glow_col: glow_text(im, (x, y), s.rstrip(), font, col, 1.0, blur=16, strength=120)
            else:
                sh = layer(im.width, im.height); ImageDraw.Draw(sh).text((x + 4, y + 6), s, font=font, fill=(0, 0, 0, 170))
                im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(6))); ImageDraw.Draw(im).text((x, y), s, font=font, fill=col)
            x += d.textlength(s, font=font)
        y += lh
    return y

def _pill(im, cx, y, text, font, bg, fg, outline=None, pad=(34, 14)):
    d = ImageDraw.Draw(im); tw = d.textlength(text, font=font); bb = d.textbbox((0, 0), text, font=font); h = bb[3] - bb[1] + 2 * pad[1]
    box = [cx - tw / 2 - pad[0], y, cx + tw / 2 + pad[0], y + h]
    if bg: d.rounded_rectangle(box, h // 2, fill=bg)
    if outline: d.rounded_rectangle(box, h // 2, outline=outline, width=4)
    d.text((cx - tw / 2, y + pad[1] - bb[1]), text, font=font, fill=fg); return y + h

def _tokens(im, toks, cx, cy, r, ring):
    toks = [t for t in (toks or []) if t][:5]
    if not toks: return
    gap = r * 2 + 26; x = cx - gap * (len(toks) - 1) / 2; d = BD(im)
    for t in toks:
        d.ellipse([x - r - 6, cy - r - 6, x + r + 6, cy + r + 6], fill=tuple(ring) + (255,))
        token_badge(d, x, cy, r, t); d = BD(im); x += gap

def _big_logo(im, name, cx, cy, r, col):
    soft_dot(im, cx, cy, r * 1.1, col, .45, blur=40); d = BD(im)
    d.ellipse([cx - r - 8, cy - r - 8, cx + r + 8, cy + r + 8], outline=tuple(col) + (255,), width=6)
    img = LOGOS.get(str(name).upper())
    if img is not None: paste_logo(im, img, cx, cy, r * .92)
    else: token_badge(d, cx, cy, r * .9, name)

def _big(im, big, cx, y, fname, col, unit_col, maxw):
    """số lớn + đơn vị -> trả y cuối"""
    d = ImageDraw.Draw(im); txt = str(big.get("text", "")); unit = str(big.get("unit", ""))
    f = fit(d, txt, fname, 330, maxw, 160); bb = d.textbbox((0, 0), txt, font=f); tw = bb[2] - bb[0]
    glow_text(im, (cx - tw / 2 - bb[0], y - bb[1]), txt, f, col, 1.0, blur=26, strength=150); y += bb[3] - bb[1] + 34
    if unit:
        uf = fit(d, unit, fname, 92, maxw, 48); ImageDraw.Draw(im); text_c(ImageDraw.Draw(im), cx, y, unit, uf, unit_col)
        ub = d.textbbox((0, 0), unit, font=uf); y += ub[3] + 10
    return y

def _body(im, c, cx, top, bottom, maxw, fname, upper, logo_col, acc, txt, ring, big_size, plain_size):
    """logo / số lớn / tiêu đề / token: vẽ lên lớp riêng rồi căn giữa theo chiều dọc trong [top, bottom]"""
    L = layer(W, H); y = 0
    if c.get("logo"): _big_logo(L, c["logo"], cx, 125, 115, logo_col); y = 290
    if c.get("big"): y = _big(L, c["big"], cx, y, fname, acc, txt, maxw) + 40
    toks = 150 if c.get("tokens") else 0
    d = ImageDraw.Draw(L); f, rows = _fit_lines(d, _words(c["lines"], upper), fname, maxw, bottom - top - y - toks, big=big_size if c.get("big") else plain_size)
    y = _draw_rows(L, rows, f, y, cx, {"normal": txt, "accent": acc}, glow_col=acc)
    if toks: _tokens(L, c.get("tokens"), cx, y + 90, 46, ring); y += toks
    safe_comp(im, L, 0, top + max(0, (bottom - top - y) / 2))

# ----------------------------------------------------------------- ChainFolk
def _chainfolk(s, theme):
    c = _spec(s, "chainfolk"); P = theme.P; CY, BL, PU = theme.CY, theme.BL, theme.PU
    im = Image.new("RGBA", (W, H), theme.BG + (255,))
    glow_blob(im, (-200, 300, 700, 1100), BL, 60, 160); glow_blob(im, (500, 900, 1400, 1700), PU, 55, 170); glow_blob(im, (200, 1300, 900, 1900), CY, 25, 160)
    im.alpha_composite(NodeNet(W, H, n=60, seed=11, col=P["net"]).draw(3.0, .7)); im.alpha_composite(hex_rain(W, H, 2.0, alpha=16))
    g = layer(W, H); gd = ImageDraw.Draw(g)
    for x in range(0, W, 90): gd.line([(x, 0), (x, H)], fill=P["grid"] + (60,))
    for y in range(0, H, 90): gd.line([(0, y), (W, y)], fill=P["grid"] + (60,))
    im.alpha_composite(g)
    x0, y0, x1, y1 = SAFE; cx = (x0 + x1) // 2
    # logo kênh
    mk = theme.mark.resize((int(theme.mark.width * 92 / theme.mark.height), 92), Image.LANCZOS)
    wm = theme.word.resize((int(theme.word.width * 58 / theme.word.height), 58), Image.LANCZOS)
    tw = mk.width + 20 + wm.width; lx = cx - tw // 2
    im.alpha_composite(mk, (lx, y0 + 10)); im.alpha_composite(wm, (lx + mk.width + 20, y0 + 27))
    tone_col = {"alert": P["bad"], "bad": P["bad"], "good": P["good"]}.get(c["tone"], CY)
    y = _pill(im, cx, y0 + 150, str(c["kicker"]).upper(), F("Inter-ExtraBold", 44), tone_col, (255, 255, 255) if tone_col != CY else theme.BG) + 70
    _body(im, c, cx, y, y1 - 110, x1 - x0, "InterDisplay-Bold", False, tone_col, CY, P["text"], theme.BG, 124, 140)
    # dải "TIN NHANH" + ngày, giống lower-third trong video
    by = y1 - 72; d = ImageDraw.Draw(im)
    d.rectangle([0, by, W, by + 72], fill=(245, 247, 255)); d.rectangle([0, by, 230, by + 72], fill=CY)
    d.text((28, by + 16), "TIN NHANH", font=F("InterDisplay-Bold", 32), fill=theme.BG)
    dt = "Ngày " + s.get("date", "") + "  ·  " + (s.get("ticker_line") or "").upper()
    d.text((254, by + 17), dt, font=fit(d, dt, "InterDisplay-Bold", 30, x1 - 254, 20), fill=theme.BG)
    return im

# ----------------------------------------------------------------- TND GEMS
def _tndgems(s, theme):
    c = _spec(s, "tndgems"); P = theme.P; MINT, WH = theme.MINT, theme.WH
    im = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    bg = grad(W, H, [(0, (4, 14, 10)), (.55, (8, 26, 19)), (1, (2, 6, 5))], horiz=False).convert("RGBA"); im.alpha_composite(bg)
    im.alpha_composite(theme._facets(W, H, seed=9)); glow_blob(im, (90, 500, 990, 1300), MINT, 40, 190)
    im.alpha_composite(NodeNet(W, H, n=55, seed=13, col=P["net"]).draw(2.0, .6)); im.alpha_composite(hex_rain(W, H, 1.0, seed=5, col=MINT, alpha=16))
    x0, y0, x1, y1 = SAFE; cx = (x0 + x1) // 2; d = ImageDraw.Draw(im)
    # pill logo kênh
    pw, ph = 380, 86; px, py = cx - pw // 2, y0 + 6
    d.rounded_rectangle([px, py, px + pw, py + ph], ph // 2, fill=(0, 0, 0), outline=MINT, width=4)
    mk = theme.mark.resize((int(theme.mark.width * 64 / theme.mark.height), 64), Image.LANCZOS); im.alpha_composite(mk, (px + 24, py + 11))
    d = ImageDraw.Draw(im); tx = px + 24 + mk.width + 16; f = F("Inter-ExtraBold", 44)
    d.text((tx, py + 17), "TND", font=f, fill=WH); d.text((tx + d.textlength("TND ", font=f), py + 17), "GEMS", font=f, fill=MINT)
    tone_col = {"alert": P["bad"], "bad": P["bad"]}.get(c["tone"], MINT)
    y = _pill(im, cx, py + ph + 56, "● " + str(c["kicker"]).upper(), F("Inter-ExtraBold", 40), None, tone_col, outline=tone_col) + 80
    _body(im, c, cx, y, y1 - 100, x1 - x0, "Inter-ExtraBold", True, MINT, MINT, WH, (0, 0, 0), 112, 128)
    by = y1 - 56; d = ImageDraw.Draw(im)
    d.line([(x0, by - 18), (x1, by - 18)], fill=MINT, width=3)
    dt = "NGÀY " + s.get("date", "").replace(".", "/") + "  ·  " + (s.get("source", "").upper())
    text_c(d, cx, by, dt, fit(d, dt, "Inter-Bold", 30, x1 - x0, 18), MINT)
    return im

BUILDERS = {"chainfolk": _chainfolk, "tndgems": _tndgems}

def make_cover(script, theme, out_png, thumb_jpg=None):
    """vẽ ảnh bìa -> out_png (1080x1920). thumb_jpg: bản nhỏ 320px (<200KB) cho Telegram."""
    im = BUILDERS[theme.name](script, theme).convert("RGB")
    os.makedirs(os.path.dirname(os.path.abspath(out_png)), exist_ok=True); im.save(out_png)
    if thumb_jpg:
        t = im.copy(); t.thumbnail((320, 320), Image.LANCZOS); t.save(thumb_jpg, "JPEG", quality=85)
    return im
