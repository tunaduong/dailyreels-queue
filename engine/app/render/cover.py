"""Ảnh bìa 1080x1920 cho từng video (TikTok / Reels / Telegram) — phong cách TikTok: ít chữ, số thật to, khối màu nổi bật.
Đọc trường tùy chọn `cover` trong kịch bản:
  {"kicker": "≤18 ký tự", "big": {"text": "> 40", "unit": "TRIỆU USD"}, "lines": [["đoạn", "normal|accent"], ...],
   "tokens": ["BTC", ...], "logo": "BINANCE", "tone": "alert|good|neutral"}
Không có `cover` thì lấy headline của kịch bản.
Vùng an toàn: lưới trang cá nhân TikTok cắt bìa 3:4 ở giữa (y 240–1680) → nội dung chính nằm trong y 330–1580, x 80–1000;
khối chính căn giữa quanh y ≈ 960 để vừa cả bìa lưới lẫn khung đầu video."""
import os
from PIL import Image, ImageDraw, ImageFilter
from .core import *

SAFE = (80, 330, 1000, 1580)
INK = (8, 10, 16)

def _spec(s, ch):
    c = dict(s.get("cover") or {})
    if not c.get("lines"): c["lines"] = [list(x) for x in s.get("headline", [])]
    c.setdefault("kicker", "TIN NÓNG" if ch == "chainfolk" else "ON-CHAIN")
    c.setdefault("tone", "alert")
    return c

def _words(lines):
    out = []
    for t, tone in lines:
        for w in str(t).upper().split():
            if out and out[-1][0] in (">", "<", "~", "≈", "+", "-", "$") and out[-1][1] == tone: out[-1] = (out[-1][0] + " " + w, tone)
            else: out.append((w, tone))
    return out

def _layout(d, words, font, maxw):
    rows = [[]]; cur = 0; sp = d.textlength(" ", font=font)
    for w, tone in words:
        ww = d.textlength(w, font=font)
        if rows[-1] and cur + sp + ww > maxw: rows.append([]); cur = 0
        cur += (sp if rows[-1] else 0) + ww; rows[-1].append((w, tone))
    return rows

def _fit_lines(d, words, fname, maxw, size, small=62, max_rows=3):
    first = None
    while size > small:
        f = F(fname, size); rows = _layout(d, words, f, maxw)
        if len(rows) <= max_rows:
            if len(rows) == 1 or len(rows[-1]) > 1 or len(words) < 3: return f, rows   # tránh 1 chữ đứng lẻ dòng cuối
            first = first or (f, rows)
            if size <= first[0].size * .85: return first
        size -= 4
    if first: return first
    f = F(fname, small); return f, _layout(d, words, f, maxw)

def _stroke_text(L, xy, s, font, fill, sw, glow=None):
    """chữ đậm có viền đen dày + bóng đổ — đọc được ở cỡ ảnh nhỏ trên lưới"""
    x, y = xy; sh = layer(L.width, L.height)
    ImageDraw.Draw(sh).text((x + 6, y + 12), s, font=font, fill=(0, 0, 0, 200), stroke_width=sw, stroke_fill=(0, 0, 0, 200))
    L.alpha_composite(sh.filter(ImageFilter.GaussianBlur(10)))
    if glow:
        g = layer(L.width, L.height); ImageDraw.Draw(g).text((x, y), s, font=font, fill=tuple(glow) + (150,))
        L.alpha_composite(g.filter(ImageFilter.GaussianBlur(28)))
    ImageDraw.Draw(L).text((x, y), s, font=font, fill=tuple(fill) + (255,), stroke_width=sw, stroke_fill=INK + (255,))


def _draw_rows(L, rows, font, y, cx, txt, hl, hl_ink):
    """dòng chữ IN HOA; đoạn accent = chữ tối trên khối màu (kiểu bút dạ quang)"""
    d = ImageDraw.Draw(L); lh = int(font.size * 1.34); sp = d.textlength(" ", font=font)
    asc = d.textbbox((0, 0), "ÂĐG", font=font)
    for row in rows:
        groups = []
        for w, tone in row:
            if groups and groups[-1][1] == tone: groups[-1][0].append(w)
            else: groups.append(([w], tone))
        segs = [(" ".join(ws), tone) for ws, tone in groups]
        padx = int(font.size * .22)
        widths = [d.textlength(s, font=font) + (2 * padx if t == "accent" else 0) for s, t in segs]
        tw = sum(widths) + sp * (len(segs) - 1); x = cx - tw / 2
        for (s, tone), ww in zip(segs, widths):
            if tone == "accent":
                box = [x, y + asc[1] - font.size * .14, x + ww, y + asc[3] + font.size * .1]
                sh = layer(L.width, L.height); ImageDraw.Draw(sh).rounded_rectangle([box[0] + 6, box[1] + 12, box[2] + 6, box[3] + 12], 14, fill=(0, 0, 0, 170))
                L.alpha_composite(sh.filter(ImageFilter.GaussianBlur(10)))
                ImageDraw.Draw(L).rounded_rectangle(box, 14, fill=tuple(hl) + (255,))
                ImageDraw.Draw(L).text((x + padx, y), s, font=font, fill=tuple(hl_ink) + (255,))
            else:
                _stroke_text(L, (x, y), s, font, txt, max(4, font.size // 14))
            x += ww + sp
        y += lh
    return y

def _sticker(L, cx, y, text, font, bg, fg, angle=-4):
    """nhãn kicker dạng sticker nghiêng nhẹ"""
    d = ImageDraw.Draw(L); tw = d.textlength(text, font=font); bb = d.textbbox((0, 0), text, font=font)
    pw, ph = int(tw + 64), int(bb[3] - bb[1] + 36)
    S = layer(pw + 40, ph + 40); sd = ImageDraw.Draw(S)
    sd.rounded_rectangle([20, 20, 20 + pw, 20 + ph], 16, fill=tuple(bg) + (255,), outline=(255, 255, 255, 255), width=5)
    sd.text((20 + 32, 20 + 18 - bb[1]), text, font=font, fill=tuple(fg) + (255,))
    S = S.rotate(angle, resample=Image.BICUBIC, expand=True)
    sh = layer(S.width, S.height); sh.paste((0, 0, 0, 160), mask=S.split()[3]); sh = sh.filter(ImageFilter.GaussianBlur(10))
    safe_comp(L, sh, cx - S.width / 2 + 6, y + 10); safe_comp(L, S, cx - S.width / 2, y)
    return y + S.height

def _unit_block(L, cx, y, text, font, bg, fg):
    d = ImageDraw.Draw(L); tw = d.textlength(text, font=font); bb = d.textbbox((0, 0), text, font=font)
    box = [cx - tw / 2 - 30, y, cx + tw / 2 + 30, y + bb[3] - bb[1] + 34]
    ImageDraw.Draw(L).rectangle(box, fill=tuple(bg) + (255,))
    ImageDraw.Draw(L).text((cx - tw / 2, y + 17 - bb[1]), text, font=font, fill=tuple(fg) + (255,))
    return box[3]

def _logo_badge(L, name, cx, cy, r, ring):
    soft_dot(L, cx, cy, r * 1.25, ring, .55, blur=40); d = BD(L)
    d.ellipse([cx - r - 10, cy - r - 10, cx + r + 10, cy + r + 10], fill=(255, 255, 255, 255))
    d.ellipse([cx - r - 4, cy - r - 4, cx + r + 4, cy + r + 4], fill=INK + (255,))
    img = LOGOS.get(str(name).upper())
    if img is not None: paste_logo(L, img, cx, cy, r * .86)
    else: token_badge(d, cx, cy, r * .92, name)

def _tokens(L, toks, cx, cy, r):
    toks = [t for t in (toks or []) if t][:4]
    gap = r * 2 + 22; x = cx - gap * (len(toks) - 1) / 2
    for t in toks:
        d = BD(L); d.ellipse([x - r - 6, cy - r - 6, x + r + 6, cy + r + 6], fill=(255, 255, 255, 255))
        token_badge(BD(L), x, cy, r, t); x += gap

def _main(c, maxw, num_col, txt, hl, hl_ink, tone_col, unit_fg, fname="Inter-ExtraBold", k=1.0):
    """dựng khối chính (logo, số, đơn vị, dòng chữ, token) trên lớp riêng → (layer, chiều cao). k: hệ số thu nhỏ"""
    L = layer(W, 2600); cx = W // 2; d = ImageDraw.Draw(L); y = 0
    if c.get("logo"): r = int(100 * k); _logo_badge(L, c["logo"], cx, r + 10, r, tone_col); y = int(250 * k)
    big = c.get("big")
    if big:
        txt_big = str(big.get("text", "")); f = fit(d, txt_big, fname, int(400 * k), maxw - 40, 150)
        bb = d.textbbox((0, 0), txt_big, font=f); tw = bb[2] - bb[0]
        _stroke_text(L, (cx - tw / 2 - bb[0], y - bb[1]), txt_big, f, num_col, 12, glow=num_col); y += bb[3] - bb[1] + int(46 * k)
        if big.get("unit"):
            unit = str(big["unit"]).upper(); uf = fit(d, unit, fname, int(76 * k), maxw - 60, 44)
            y = _unit_block(L, cx, y, unit, uf, tone_col, unit_fg) + 44
    if c.get("lines"):
        f, rows = _fit_lines(d, _words(c["lines"]), fname, maxw * .9, int((96 if big else 128) * k))
        y = _draw_rows(L, rows, f, y, cx, txt, hl, hl_ink) + 10
    if c.get("tokens"): r = int(48 * k); _tokens(L, c["tokens"], cx, y + r + 22, r); y += 2 * r + 54
    return L, y

def _vignette(im, strength=200):
    v = layer(W, H); vd = ImageDraw.Draw(v)
    for i in range(40):
        a = int(strength * (i / 40) ** 2.2); vd.rectangle([i * 9, i * 14, W - i * 9, H - i * 14], outline=(0, 0, 0, 0))
    m = Image.new("L", (W, H), 0); md = ImageDraw.Draw(m); md.ellipse([-260, 160, W + 260, H - 160], fill=255)
    m = m.filter(ImageFilter.GaussianBlur(220)); dark = Image.new("RGBA", (W, H), (0, 0, 0, strength))
    dark.putalpha(Image.eval(m, lambda p: int(strength * (1 - p / 255)))); im.alpha_composite(dark)

def _compose(im, c, kicker_bg, kicker_fg, main_kw, brand):
    x0, y0, x1, y1 = SAFE; cx = W // 2
    brand(im, y0)                                                  # logo kênh nhỏ trên cùng
    K = layer(W, 400); kh = _sticker(K, cx, 0, str(c["kicker"]).upper(), F("Inter-ExtraBold", 50), kicker_bg, kicker_fg)
    gap = 56; room = y1 - (y0 + 130) - kh - gap
    for k in (1.0, .92, .84, .76, .68, .6):                     # thu nhỏ tới khi vừa vùng an toàn
        M, mh = _main(c, x1 - x0, k=k, **main_kw)
        if mh <= room: break
    total = kh + gap + mh
    top = max(y0 + 130, min(960 - total / 2, y1 - total))          # căn giữa quanh y 960, không vượt vùng an toàn
    safe_comp(im, K.crop((0, 0, W, kh)), 0, top); safe_comp(im, M.crop((0, 0, W, mh)), 0, top + kh + gap)

def _footer(im, text, col):
    d = ImageDraw.Draw(im); f = fit(d, text, "Inter-Bold", 32, SAFE[2] - SAFE[0], 20)
    text_c(d, W // 2, SAFE[3] + 6, text, f, col)

# ----------------------------------------------------------------- ChainFolk
def _chainfolk(s, theme):
    c = _spec(s, "chainfolk"); P = theme.P; CY, BL, PU = theme.CY, theme.BL, theme.PU
    im = grad(W, H, [(0, (6, 10, 38)), (.5, (10, 16, 58)), (1, (4, 6, 22))], horiz=False).convert("RGBA")
    glow_blob(im, (-300, 200, 800, 1100), BL, 70, 220); glow_blob(im, (400, 900, 1500, 1900), PU, 70, 220)
    glow_blob(im, (190, 620, 890, 1320), CY, 26, 200)
    im.alpha_composite(NodeNet(W, H, n=40, seed=11, col=P["net"]).draw(3.0, .35)); _vignette(im, 170)
    tone_col = {"alert": P["bad"], "bad": P["bad"], "good": P["good"]}.get(c["tone"], CY)
    unit_fg = (255, 255, 255) if tone_col != CY else theme.BG

    def brand(im, y):
        mk = theme.mark.resize((int(theme.mark.width * 70 / theme.mark.height), 70), Image.LANCZOS)
        wm = theme.word.resize((int(theme.word.width * 44 / theme.word.height), 44), Image.LANCZOS)
        tw = mk.width + 16 + wm.width; lx = W // 2 - tw // 2
        im.alpha_composite(mk, (lx, y)); im.alpha_composite(wm, (lx + mk.width + 16, y + 14))
    _compose(im, c, tone_col, unit_fg, dict(num_col=CY, txt=P["text"], hl=CY, hl_ink=theme.BG, tone_col=tone_col, unit_fg=unit_fg), brand)
    _footer(im, s.get("date", "").replace(".", "/"), P["muted"])
    return im

# ----------------------------------------------------------------- TND GEMS
def _tndgems(s, theme):
    c = _spec(s, "tndgems"); P = theme.P; MINT, WH = theme.MINT, theme.WH
    im = grad(W, H, [(0, (3, 12, 9)), (.5, (8, 30, 21)), (1, (2, 6, 5))], horiz=False).convert("RGBA")
    im.alpha_composite(theme._facets(W, H, seed=9)); glow_blob(im, (60, 520, 1020, 1400), MINT, 46, 220)
    im.alpha_composite(NodeNet(W, H, n=36, seed=13, col=P["net"]).draw(2.0, .3)); _vignette(im, 190)
    tone_col = {"alert": P["bad"], "bad": P["bad"]}.get(c["tone"], MINT)
    unit_fg = (255, 255, 255) if tone_col != MINT else INK

    def brand(im, y):
        d = ImageDraw.Draw(im); f = F("Inter-ExtraBold", 38)
        mk = theme.mark.resize((int(theme.mark.width * 54 / theme.mark.height), 54), Image.LANCZOS)
        tw = mk.width + 14 + d.textlength("TND GEMS", font=f); pw, ph = int(tw + 56), 76; px = W // 2 - pw // 2
        d.rounded_rectangle([px, y, px + pw, y + ph], ph // 2, fill=(0, 0, 0), outline=MINT, width=3)
        im.alpha_composite(mk, (px + 28, y + 11)); d = ImageDraw.Draw(im); tx = px + 28 + mk.width + 14
        d.text((tx, y + 16), "TND", font=f, fill=WH); d.text((tx + d.textlength("TND ", font=f), y + 16), "GEMS", font=f, fill=MINT)
    _compose(im, c, tone_col, unit_fg, dict(num_col=MINT, txt=WH, hl=MINT, hl_ink=INK, tone_col=tone_col, unit_fg=unit_fg), brand)
    _footer(im, s.get("date", "").replace(".", "/"), P["muted"])
    return im

BUILDERS = {"chainfolk": _chainfolk, "tndgems": _tndgems}

def make_cover(script, theme, out_png, thumb_jpg=None):
    """vẽ ảnh bìa -> out_png (1080x1920). thumb_jpg: bản nhỏ 320px (<200KB) cho Telegram."""
    im = BUILDERS[theme.name](script, theme).convert("RGB")
    os.makedirs(os.path.dirname(os.path.abspath(out_png)), exist_ok=True); im.save(out_png)
    if thumb_jpg:
        t = im.copy(); t.thumbnail((320, 320), Image.LANCZOS); t.save(thumb_jpg, "JPEG", quality=85)
    return im
