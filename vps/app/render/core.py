"""Hàm vẽ dùng chung: font, easing, panel kính, glow, icon, token, nền node, băng giá, biểu đồ nến."""
import math, random, os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FONTS = os.path.join(ROOT, "assets", "fonts")
LOGO_DIR = os.path.join(ROOT, "assets", "logos")
W, H, FPS = 1080, 1920, 30

_fc = {}
def F(name, size):
    size = max(8, int(size)); k = (name, size)
    if k not in _fc: _fc[k] = ImageFont.truetype(os.path.join(FONTS, name + ".otf"), size)
    return _fc[k]

def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def ease(x): x = clamp(x); return 1 - (1 - x) ** 3
def prog(t, a, b): return ease((t - a) / (b - a)) if b > a else float(t >= a)
def lerp(a, b, u): return a + (b - a) * u
def mix(c1, c2, u): return tuple(int(lerp(c1[i], c2[i], u)) for i in range(3))
def A(c, a): return tuple(c[:3]) + (int(255 * clamp(a)),)
def layer(w, h): return Image.new("RGBA", (int(w), int(h)), (0, 0, 0, 0))

def safe_comp(L, img, x, y):
    x, y = int(x), int(y); sx, sy = max(0, -x), max(0, -y); x2, y2 = max(0, x), max(0, y)
    w = min(img.width - sx, L.width - x2); h = min(img.height - sy, L.height - y2)
    if w > 0 and h > 0: L.alpha_composite(img.crop((sx, sy, sx + w, sy + h)), (x2, y2))

def with_alpha(img, a):
    if a >= 1: return img
    img = img.copy(); img.putalpha(img.split()[3].point(lambda v: int(v * clamp(a)))); return img

def fade_paste(dst, img, a, xy):
    if a > 0: safe_comp(dst, with_alpha(img, a), xy[0], xy[1])

class BD:
    """ImageDraw trộn alpha đúng trên ảnh RGBA."""
    def __init__(self, L): self.L = L; self.d = ImageDraw.Draw(L)
    def textlength(self, *a, **k): return self.d.textlength(*a, **k)
    def textbbox(self, *a, **k): return self.d.textbbox(*a, **k)
    def __getattr__(self, name):
        fn = getattr(self.d, name)
        def call(*a, **k):
            cols = [c for c in (k.get("fill"), k.get("outline")) if c is not None]
            if any(isinstance(c, tuple) and len(c) == 4 and c[3] < 255 for c in cols):
                if all(isinstance(c, tuple) and len(c) == 4 and c[3] == 0 for c in cols): return
                tmp = layer(self.L.width, self.L.height); getattr(ImageDraw.Draw(tmp), name)(*a, **k); self.L.alpha_composite(tmp)
            else: fn(*a, **k)
        return call

def text_c(d, cx, y, s, font, fill):
    w = d.textlength(s, font=font); d.text((cx - w / 2, y), s, font=font, fill=fill); return w

def fit(d, s, fname, size, maxw, minsize=18):
    while size > minsize and d.textlength(s, font=F(fname, size)) > maxw: size -= 2
    return F(fname, size)

def wrap(d, s, font, maxw):
    words, lines, cur = s.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if cur and d.textlength(t, font=font) > maxw: lines.append(cur); cur = w
        else: cur = t
    if cur: lines.append(cur)
    return lines

def grad(w, h, stops, horiz=True):
    w, h = max(1, int(w)), max(1, int(h)); g = Image.new("RGB", (w, h)); d = ImageDraw.Draw(g); n = w if horiz else h
    for i in range(n):
        t = i / max(1, n - 1); c = stops[-1][1]
        for k in range(len(stops) - 1):
            t0, c0 = stops[k]; t1, c1 = stops[k + 1]
            if t0 <= t <= t1: c = mix(c0, c1, (t - t0) / (t1 - t0) if t1 > t0 else 0); break
        d.line([(i, 0), (i, h)] if horiz else [(0, i), (w, i)], fill=c)
    return g

def glow_blob(img, box, color, alpha, blur):
    g = layer(img.width, img.height); ImageDraw.Draw(g).ellipse(box, fill=tuple(color) + (alpha,))
    img.alpha_composite(g.filter(ImageFilter.GaussianBlur(blur)))

# ---------- hiệu ứng ----------
def glass(L, box, a=1.0, tint=(20, 34, 72), edge=(0, 229, 245), radius=22, shadow=True):
    x0, y0, x1, y1 = [int(v) for v in box]
    if a <= 0 or x1 <= x0 or y1 <= y0: return
    if shadow:
        pad = 40; g = layer(x1 - x0 + 2 * pad, y1 - y0 + 2 * pad)
        ImageDraw.Draw(g).rounded_rectangle([pad, pad + 10, pad + x1 - x0, pad + y1 - y0 + 14], radius, fill=(0, 0, 0, int(160 * a)))
        safe_comp(L, g.filter(ImageFilter.GaussianBlur(14)), x0 - pad, y0 - pad)
    p = layer(x1 - x0, y1 - y0); pd = ImageDraw.Draw(p); top = tuple(min(255, v + 18) for v in tint)
    for i in range(y1 - y0): pd.line([(0, i), (x1 - x0, i)], fill=mix(top, tint, i / (y1 - y0)) + (int(225 * a),))
    m = Image.new("L", p.size, 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, p.width - 1, p.height - 1], radius, fill=255)
    p.putalpha(Image.composite(p.split()[3], m, m)); safe_comp(L, p, x0, y0)
    d = BD(L)
    d.rounded_rectangle([x0, y0, x1, y1], radius, outline=A(edge, .43 * a), width=2)
    d.line([(x0 + radius, y0 + 1), (x1 - radius, y0 + 1)], fill=(255, 255, 255, int(60 * a)), width=2)

def glow_text(L, xy, s, font, col, a=1.0, blur=10, strength=180):
    if a <= 0: return
    d0 = ImageDraw.Draw(L); bb = d0.textbbox(xy, s, font=font); pad = blur * 3
    g = layer(bb[2] - bb[0] + 2 * pad, bb[3] - bb[1] + 2 * pad)
    ImageDraw.Draw(g).text((xy[0] - bb[0] + pad, xy[1] - bb[1] + pad), s, font=font, fill=tuple(col) + (int(strength * a),))
    safe_comp(L, g.filter(ImageFilter.GaussianBlur(blur)), bb[0] - pad, bb[1] - pad)
    BD(L).text(xy, s, font=font, fill=A(col, a))

def soft_dot(L, x, y, r, col, a=1.0, blur=8):
    if a <= 0: return
    r = int(r); pad = blur * 3; g = layer(2 * (r + pad), 2 * (r + pad))
    ImageDraw.Draw(g).ellipse([pad, pad, pad + 2 * r, pad + 2 * r], fill=tuple(col) + (int(150 * clamp(a)),))
    safe_comp(L, g.filter(ImageFilter.GaussianBlur(blur)), x - r - pad, y - r - pad)

def warn_icon(d, cx, cy, s, col, bg):
    d.polygon([(cx, cy - s), (cx + s * 1.1, cy + s * .8), (cx - s * 1.1, cy + s * .8)], fill=col)
    d.rectangle([cx - s * .09, cy - s * .45, cx + s * .09, cy + s * .25], fill=bg)
    d.ellipse([cx - s * .1, cy + s * .38, cx + s * .1, cy + s * .58], fill=bg)

def shield_icon(d, cx, cy, s, col, bg, check=1.0):
    d.polygon([(cx, cy - s), (cx + s * .85, cy - s * .65), (cx + s * .75, cy + s * .25), (cx, cy + s), (cx - s * .75, cy + s * .25), (cx - s * .85, cy - s * .65)], fill=col)
    p1, p2, p3 = (cx - s * .38, cy), (cx - s * .08, cy + s * .3), (cx + s * .42, cy - s * .3); w = int(s * .16)
    if check > 0:
        u = clamp(check * 2); d.line([p1, (lerp(p1[0], p2[0], u), lerp(p1[1], p2[1], u))], fill=bg, width=w)
    if check > .5:
        v = clamp((check - .5) * 2); d.line([p2, (lerp(p2[0], p3[0], v), lerp(p2[1], p3[1], v))], fill=bg, width=w)

def lock_icon(d, cx, cy, s, col, bg):
    w = int(s * .18)
    d.arc([cx - s * .45, cy - s * 1.05, cx + s * .45, cy - s * .15], 180, 360, fill=col, width=w)
    d.line([(cx - s * .36, cy - s * .6), (cx - s * .36, cy - s * .2)], fill=col, width=w)
    d.line([(cx + s * .36, cy - s * .6), (cx + s * .36, cy - s * .2)], fill=col, width=w)
    d.rounded_rectangle([cx - s * .7, cy - s * .3, cx + s * .7, cy + s * .7], int(s * .15), fill=col)
    d.ellipse([cx - s * .12, cy + s * .05, cx + s * .12, cy + s * .29], fill=bg)

def chart_icon(d, cx, cy, s, col, bg):
    for i, hgt in enumerate([.5, .8, .35, 1.0]):
        x = cx - s * .75 + i * s * .5; d.rectangle([x - s * .14, cy + s * .6 - s * 1.2 * hgt, x + s * .14, cy + s * .6], fill=col)

def stamp(size_wh, text, col, font, angle=-8):
    w, h = size_wh; L = layer(w + 40, h + 40); d = ImageDraw.Draw(L)
    d.rounded_rectangle([20, 20, 20 + w, 20 + h], 12, outline=tuple(col) + (255,), width=6)
    tw = d.textlength(text, font=font); bb = d.textbbox((0, 0), text, font=font)
    d.text((20 + (w - tw) / 2, 20 + (h - (bb[3] - bb[1])) / 2 - bb[1]), text, font=font, fill=tuple(col) + (255,))
    return L.rotate(angle, resample=Image.BICUBIC, expand=True)

TOKEN_COL = {"BTC": (247, 147, 26), "ETH": (98, 126, 234), "USDT": (38, 161, 123), "USDC": (39, 117, 202), "BNB": (240, 185, 11),
             "SOL": (153, 69, 255), "XRP": (35, 41, 47), "TRX": (235, 0, 41), "DOGE": (194, 166, 51), "TON": (0, 136, 204),
             "ADA": (0, 51, 173), "AVAX": (232, 65, 66), "LINK": (42, 90, 218), "ARB": (40, 160, 240), "OP": (255, 4, 32), "SUI": (77, 162, 255)}
LOGOS = {}   # SYM/SÀN -> ảnh RGBA thật (engine nạp trước khi dựng)

def paste_logo(L, img, cx, cy, r, a=1.0):
    im = img.copy(); im.thumbnail((int(2 * r), int(2 * r)), Image.LANCZOS)
    safe_comp(L, with_alpha(im, a), cx - im.width / 2, cy - im.height / 2)

def token_badge(d, cx, cy, r, sym):
    img = LOGOS.get(str(sym).upper())
    if img is not None and hasattr(d, "L"): paste_logo(d.L, img, cx, cy, r); return
    sym = str(sym)[:5]; c = TOKEN_COL.get(sym.upper(), (110, 116, 140))
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=c + (255,))
    f = F("Inter-ExtraBold", r * (0.9 if len(sym) <= 3 else 0.62)); tw = d.textlength(sym, font=f); bb = d.textbbox((0, 0), sym, font=f)
    d.text((cx - tw / 2, cy - (bb[3] - bb[1]) / 2 - bb[1]), sym, font=f, fill=(255, 255, 255, 255))

class NodeNet:
    def __init__(self, w, h, n=34, seed=1, col=(0, 229, 245)):
        r = random.Random(seed); self.w, self.h, self.col = w, h, tuple(col)
        self.p = [(r.uniform(0, w), r.uniform(0, h), r.uniform(-14, 14), r.uniform(-10, 10)) for _ in range(n)]
    def draw(self, t, alpha=1.0):
        L = layer(self.w, self.h); d = ImageDraw.Draw(L)
        P = [((x + vx * t) % self.w, (y + vy * t) % self.h) for x, y, vx, vy in self.p]
        for i in range(len(P)):
            for j in range(i + 1, len(P)):
                dist = math.hypot(P[i][0] - P[j][0], P[i][1] - P[j][1])
                if dist < 210: d.line([P[i], P[j]], fill=self.col + (int((1 - dist / 210) * 70 * alpha),), width=1)
        for x, y in P: d.ellipse([x - 3, y - 3, x + 3, y + 3], fill=self.col + (int(120 * alpha),))
        return L

def hex_rain(w, h, t, seed=2, col=(0, 229, 245), alpha=20):
    r = random.Random(seed); L = layer(w, h); d = ImageDraw.Draw(L); f = F("Inter-Medium", 18)
    for c in range(0, w, 120):
        sp = r.uniform(30, 70); off = r.uniform(0, 400); s = "".join(r.choice("0123456789abcdef") for _ in range(40))
        for k in range(int(h / 26) + 2):
            y = (k * 26 + off + t * sp) % (h + 60) - 30
            d.text((c + 10, y), s[k % 40] + s[(k + 7) % 40], font=f, fill=tuple(col) + (alpha,))
    return L

def ticker_tape(w, t, items, h=54, bg=(4, 10, 28), speed=70, up=(0, 214, 160), dn=(255, 84, 112), txt=(230, 236, 255), line=(40, 56, 100)):
    L = layer(w, h); d = ImageDraw.Draw(L); d.rectangle([0, 0, w, h], fill=tuple(bg) + (235,)); d.line([(0, h - 1), (w, h - 1)], fill=tuple(line) + (255,))
    if not items: return L
    f1, f2 = F("Inter-Bold", 26), F("Inter-SemiBold", 26); segs = []
    for sym, px, ch in items:
        segs += [(sym + " ", txt, f1), (px + " ", txt, f2),
                 (("▲ " if ch >= 0 else "▼ ") + f"{abs(ch):.2f}%".replace(".", ",") + "      ", up if ch >= 0 else dn, f1)]
    total = sum(d.textlength(s, font=f) for s, _, f in segs); x = -((t * speed) % total)
    while x < w:
        for s, c, f in segs: d.text((x, 12), s, font=f, fill=tuple(c) + (255,)); x += d.textlength(s, font=f)
    return L

def fmt_num(v, decimals=0):
    s = f"{v:,.{decimals}f}"; return s.replace(",", "§").replace(".", ",").replace("§", ".")

def fmt_price(v):
    if v >= 1000: return fmt_num(v, 0)
    if v >= 1: return fmt_num(v, 2)
    return fmt_num(v, 4)

def synth_ohlc(n, start, end, vol=0.0035, seed=5):
    r = random.Random(seed); out = []; p = start
    for i in range(n):
        target = start + (end - start) * ((i + 1) / n) ** 1.4; o = p
        c = o + (target - o) * 0.5 + r.gauss(0, start * vol)
        hi = max(o, c) + abs(r.gauss(0, start * vol * .7)); lo = min(o, c) - abs(r.gauss(0, start * vol * .7))
        out.append((o, hi, lo, c, r.uniform(.3, 1) * (1 + 2.5 * abs(c - o) / (start * vol * 2)))); p = c
    o, hi, lo, c, v = out[-1]; out[-1] = (o, max(hi, end), min(lo, end), end, v); return out

def pro_chart(w, h, data, k, title, P):
    up, dn, grid, txt = P["good"], P["bad"], P["grid"], P["muted"]
    L = layer(w, h); d = ImageDraw.Draw(L); ax = 120; pw = w - ax; ph_ = int(h * .74); vh = h - ph_ - 34
    n = max(1, int(len(data) * k)); vis = data[:n]
    lo = min(x[2] for x in data); hi = max(x[1] for x in data); pad = (hi - lo) * .08 or 1; lo -= pad; hi += pad
    Y = lambda v: 40 + (hi - v) / (hi - lo) * (ph_ - 40); fa = F("Inter-Medium", 20)
    for i in range(6):
        v = lo + (hi - lo) * i / 5; y = Y(v); d.line([(0, y), (pw, y)], fill=tuple(grid) + (255,))
        d.text((pw + 10, y - 12), fmt_price(v), font=fa, fill=tuple(txt) + (255,))
    cw = pw / len(data); bw = max(3, cw * .62); vmax = max(x[4] for x in data) or 1
    ma = [sum(x[3] for x in vis[max(0, i - 9):i + 1]) / len(vis[max(0, i - 9):i + 1]) for i in range(n)]
    for i, (o, hh, ll, c, v) in enumerate(vis):
        x = i * cw + cw / 2; col = tuple(up if c >= o else dn)
        d.line([(x, Y(hh)), (x, Y(ll))], fill=col + (255,), width=2)
        y0, y1 = sorted([Y(o), Y(c)]); d.rectangle([x - bw / 2, y0, x + bw / 2, max(y1, y0 + 2)], fill=col + (255,))
        vy = h - 30 - v / vmax * vh; d.rectangle([x - bw / 2, vy, x + bw / 2, h - 30], fill=col + (90,))
    if n > 1: d.line([(i * cw + cw / 2, Y(m)) for i, m in enumerate(ma)], fill=(255, 196, 70, 230), width=3)
    c = vis[-1][3]; y = Y(c); col = tuple(up if c >= vis[0][0] else dn)
    for xx in range(0, int(pw), 16): d.line([(xx, y), (xx + 8, y)], fill=col + (200,), width=2)
    lab = fmt_price(c); tw = d.textlength(lab, font=F("Inter-Bold", 22))
    d.rounded_rectangle([pw + 2, y - 18, pw + 14 + tw, y + 18], 6, fill=col + (255,)); d.text((pw + 8, y - 13), lab, font=F("Inter-Bold", 22), fill=(255, 255, 255, 255))
    d.text((10, 6), title, font=F("Inter-Bold", 24), fill=tuple(txt) + (255,))
    tl = d.textlength(title, font=F("Inter-Bold", 24)); d.text((tl + 30, 9), "MA10", font=F("Inter-Bold", 20), fill=(255, 196, 70, 255))
    d.text((10, h - 26), "Vol", font=F("Inter-Medium", 18), fill=tuple(txt) + (255,))
    return L

def wrap_head(img, x, y, segs, font, lh, maxw):
    """segs: [(text, color)] -> vẽ tiêu đề tự xuống dòng; trả (y_cuối, số_dòng)"""
    d = ImageDraw.Draw(img); words = [(w, c) for t, c in segs for w in str(t).split()]
    lines = [[]]; cur = 0; sp = d.textlength(" ", font=font)
    for w, c in words:
        ww = d.textlength(w, font=font)
        if lines[-1] and cur + sp + ww > maxw: lines.append([]); cur = 0
        cur += (sp if lines[-1] else 0) + ww; lines[-1].append((w, c))
    for ln in lines:
        cx = x
        for i, (w, c) in enumerate(ln):
            s = w + (" " if i < len(ln) - 1 else ""); d.text((cx, y), s, font=font, fill=c); cx += d.textlength(s, font=font)
        y += lh
    return y, len(lines)

def count_lines(segs, font, maxw):
    tmp = Image.new("RGB", (10, 10)); return wrap_head(Image.new("RGB", (2000, 2000)), 0, 0, segs, font, 1, maxw)[1]

def key_logo(path):
    return Image.open(path).convert("RGBA")
