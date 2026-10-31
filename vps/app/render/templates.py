"""Thư viện mẫu cảnh. Mỗi mẫu vẽ vào box (vùng an toàn) theo tiến độ t (giây) trong beat dài dur.
Chữ ký: fn(L, box, P, v, t, dur, ctx). v = dict tham số từ kịch bản."""
from .core import *

def _rv(t, i, dur, step=.35, length=.35):
    st = min(.1 + step * i, max(0.0, dur * .6)); return prog(t, st, st + length)

def _tone(P, tone):
    return {"bad": P["bad"], "alert": P["bad"], "good": P["good"], "ice": P["ice"], "accent": P["accent"]}.get(tone, P["text"])

def _tint(P, tone):
    return {"bad": P["bad_tint"], "alert": P["bad_tint"], "good": P["good_tint"], "ice": P["ice_tint"]}.get(tone, P["tint"])

def _edge(P, tone):
    return {"bad": P["bad"], "alert": P["bad"], "good": P["good"], "ice": P["ice"]}.get(tone, P["edge"])

def _num(v, k=1.0):
    try: return float(v) * k
    except Exception: return None

def _fmtv(val, dec, k=1.0, prefix="", suffix=""):
    x = _num(val, k)
    if x is None: return f"{prefix}{val}{suffix}"
    return f"{prefix}{fmt_num(x, int(dec or 0))}{suffix}"

def _S(box): return min(1.15, (box[3] - box[1]) / 456)

# ------------------------------------------------------------------ hero
def hero(L, box, P, v, t, dur, ctx):
    x0, y0, x1, y1 = box; s = _S(box); tone = v.get("tone", "alert"); col = _tone(P, tone)
    icon = v.get("icon", "warn"); a = prog(t, 0, .35); d = BD(L)
    cx0 = x0
    if v.get("logo"):
        icx, icy = x0 + 140 * s, (y0 + y1) / 2
        if tone in ("alert", "bad"):
            for k in range(3):
                u = (t * .6 + k / 3) % 1; r = 60 + 220 * u * s
                d.ellipse([icx - r, icy - r, icx + r, icy + r], outline=A(col, .47 * (1 - u) * a), width=4)
        soft_dot(L, icx, icy, 110 * s, col, .35 * a, blur=40); d = BD(L)
        img = LOGOS.get(str(v["logo"]).upper())
        if img is not None: paste_logo(L, img, icx, icy + 12 * (1 - a), 105 * s, a)
        else: token_badge(d, icx, icy, 90 * s, v["logo"])
        d = BD(L); icon = "none"; cx0 = x0 + 290 * s
    if icon != "none":
        icx, icy = x0 + 140 * s, (y0 + y1) / 2
        if tone in ("alert", "bad"):
            for k in range(3):
                u = (t * .6 + k / 3) % 1; r = 40 + 230 * u * s
                d.ellipse([icx - r, icy - r, icx + r, icy + r], outline=A(col, .47 * (1 - u) * a), width=4)
        soft_dot(L, icx, icy, 100 * s, col, .3 * a, blur=36); d = BD(L)
        sz = 80 * s
        if icon == "warn": warn_icon(d, icx, icy, sz, A(col, a), A(P["bg"], 1))
        elif icon == "shield": shield_icon(d, icx, icy, sz * 1.5, A(col, a), A(P["bg"], 1), check=prog(t, .4, 1.4))
        elif icon == "lock": lock_icon(d, icx, icy + 10, sz * 1.1, A(col, a), A(P["bg"], 1))
        elif icon == "chart": chart_icon(d, icx, icy, sz, A(col, a), A(P["bg"], 1))
        cx0 = x0 + 290 * s
    glass(L, (cx0, y0 + 40 * s, x1, y1 - 40 * s), a, tint=_tint(P, tone), edge=_edge(P, tone)); d = BD(L)
    px = cx0 + 30; mw = x1 - px - 30; y = y0 + 70 * s
    if v.get("kicker"):
        kf = F("Inter-ExtraBold", 26 * s); kw = d.textlength(v["kicker"], font=kf); p = .5 + .5 * math.sin(t * 7)
        kc = mix(_tint(P, tone), col, .6 + .4 * p) if tone in ("alert", "bad") else col
        d.rounded_rectangle([px, y, px + kw + 44, y + 46 * s], 22, fill=A(kc, a)); d.text((px + 22, y + 7 * s), v["kicker"], font=kf, fill=A((255, 255, 255) if tone in ("alert", "bad") else P["bg"], a))
        y += 70 * s
    title = str(v.get("title", "")); tf = F("InterDisplay-Bold", 92 * s)
    lines = [title] if d.textlength(title, font=tf) <= mw else wrap(d, title, F("InterDisplay-Bold", 62 * s), mw)[:2]
    f = tf if len(lines) == 1 and d.textlength(title, font=tf) <= mw else F("InterDisplay-Bold", 62 * s)
    if len(lines) == 1: f = fit(d, lines[0], "InterDisplay-Bold", 92 * s, mw)
    for ln in lines:
        glow_text(L, (px, y), ln, f, P["text"] if tone != "good" else P["good"], a, blur=12, strength=100); y += f.size * 1.18
    d = BD(L)
    if v.get("subtitle"):
        b = _rv(t, 2, dur); sf = F("Inter-Medium", 32 * s)
        for ln in wrap(d, v["subtitle"], sf, mw)[:2]: d.text((px, y + 8), ln, font=sf, fill=A(P["muted"], b)); y += sf.size * 1.3
    toks = v.get("tokens") or []
    if toks:
        b = _rv(t, 3, dur)
        if b > 0:
            for i, sym in enumerate(toks[:5]): token_badge(d, px + 26 + i * 62, min(y + 50 * s, y1 - 70 * s), 24 * s, sym)

# ------------------------------------------------------------------ big_number
def big_number(L, box, P, v, t, dur, ctx):
    x0, y0, x1, y1 = box; s = _S(box); a = prog(t, 0, .35); d = BD(L); col = _tone(P, v.get("tone", "bad"))
    has_left = bool(v.get("caption") or v.get("kicker"))
    if has_left:
        lx1 = x0 + (x1 - x0) * .56; glass(L, (x0, y0 + 30 * s, lx1, y1 - 30 * s), a, tint=P["tint"], edge=P["edge"]); d = BD(L)
        px = x0 + 30; y = y0 + 60 * s; mw = lx1 - px - 24
        if v.get("kicker"): d.text((px, y), str(v["kicker"]).upper(), font=fit(d, str(v["kicker"]).upper(), "Inter-Bold", 26 * s, mw), fill=A(P["muted"], a)); y += 50 * s
        cf = F("InterDisplay-Bold", 70 * s)
        lines = wrap(d, str(v.get("caption", "")), cf, mw)
        if len(lines) > 3: cf = F("InterDisplay-Bold", 50 * s); lines = wrap(d, str(v.get("caption", "")), cf, mw)[:4]
        for ln in lines: glow_text(L, (px, y), ln, cf, P["accent"], a, blur=12); y += cf.size * 1.15
        d = BD(L)
        for i, sym in enumerate((v.get("tokens") or [])[:4]): token_badge(d, px + 26 + i * 64, min(y + 40 * s, y1 - 70 * s), 24 * s, sym)
        cx = (lx1 + x1) / 2
    else: cx = (x0 + x1) / 2
    cy = (y0 + y1) / 2; r = min((x1 - x0) * (.2 if has_left else .3), (y1 - y0) * .32); k = prog(t, .3, max(.8, min(3.5, dur * .7)))
    val = _num(v.get("value"), 1) or 0; rmax = _num(v.get("ring_max")) or val or 1; frac = clamp(val / rmax) * k
    for i in range(40):
        ang = math.radians(-90 + i * 9); r0 = r + 20; r1 = r + (32 if i % 5 == 0 else 26)
        d.line([(cx + r0 * math.cos(ang), cy + r0 * math.sin(ang)), (cx + r1 * math.cos(ang), cy + r1 * math.sin(ang))], fill=A(col if i < 40 * frac else P["grid"], 1), width=3)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=A(P["grid"], 1), width=int(16 * s))
    if frac > 0: d.arc([cx - r, cy - r, cx + r, cy + r], -90, -90 + 360 * frac, fill=A(col, 1), width=int(16 * s))
    n = _fmtv(val, v.get("decimals", 0), k, v.get("prefix", "")); nf = fit(d, n, "InterDisplay-Bold", r * .78, r * 1.6)
    glow_text(L, (cx - d.textlength(n, font=nf) / 2, cy - nf.size * .72), n, nf, P["text"], 1, blur=10, strength=90); d = BD(L)
    if v.get("suffix"): text_c(d, cx, cy + nf.size * .42, str(v["suffix"]).upper(), fit(d, str(v["suffix"]).upper(), "Inter-Bold", 30 * s, r * 1.5), A(P["muted"], 1))

# ------------------------------------------------------------------ stat_cards
def stat_cards(L, box, P, v, t, dur, ctx):
    x0, y0, x1, y1 = box; s = _S(box); cards = (v.get("cards") or [])[:3]; n = max(1, len(cards)); gap = 30
    total = v.get("total"); ch = (y1 - y0) * (.62 if total else .8); cw = (x1 - x0 - gap * (n - 1)) / n
    off = 0
    if n == 1: cw = min(cw, 640); off = (x1 - x0 - cw) / 2
    for i, c in enumerate(cards):
        a = _rv(t, i, dur, .7); cx = x0 + off + i * (cw + gap); top = y0 + 20 * s
        if a <= 0: continue
        tone = c.get("tone", "neutral"); glass(L, (cx, top, cx + cw, top + ch), a, tint=_tint(P, tone), edge=_edge(P, tone)); d = BD(L)
        px = cx + 26; mw = cw - 52; y = top + 26 * s
        if c.get("token"): token_badge(d, px + 24 * s, y + 24 * s, 24 * s, c["token"]); lx = px + 60 * s
        else: lx = px
        lab = str(c.get("label", "")).upper(); d.text((lx, y + 6 * s), lab, font=fit(d, lab, "Inter-Bold", 28 * s, mw - (lx - px)), fill=A(P["muted"], a)); y += 70 * s
        k = prog(t, .2 + i * .7, 1.1 + i * .7); val = _fmtv(c.get("value", ""), c.get("decimals", 0), k, c.get("prefix", ""))
        vf = fit(d, val, "InterDisplay-Bold", 72 * s if n < 3 else 56 * s, mw); d.text((px, y), val, font=vf, fill=A(P["text"], a)); y += vf.size * 1.25
        if c.get("unit"): d.text((px, y), str(c["unit"]), font=fit(d, str(c["unit"]), "Inter-Bold", 34 * s, mw * .5), fill=A(P["accent"], a))
        if c.get("stamp"):
            sa = _rv(t, i * 2 + 1.5, dur, .35, .3)
            if sa > 0:
                sf = F("Inter-ExtraBold", 24 * s); sw = BD(L).textlength(c["stamp"], font=sf) + 30
                sp = stamp((int(sw), int(54 * s)), str(c["stamp"]).upper(), _tone(P, "ice" if tone == "ice" else "accent"), sf)
                sz = 1 + .6 * (1 - sa); sp = sp.resize((int(sp.width * sz), int(sp.height * sz)))
                fade_paste(L, sp, sa, (cx + cw - sp.width + 10, top - 14))
    if total:
        b = _rv(t, n * 2, dur)
        if b > 0:
            ty = y0 + 20 * s + ch + 30 * s; glass(L, (x0 + 60, ty, x1 - 60, ty + 76 * s), b, edge=P["accent"]); d = BD(L)
            lab = str(total.get("label", "")); lf = F("Inter-Bold", 30 * s); d.text((x0 + 90, ty + 20 * s), lab, font=lf, fill=A(P["text"], b))
            tx = x0 + 110 + d.textlength(lab, font=lf); val = str(total.get("text", ""))
            glow_text(L, (tx, ty + 12 * s), val, fit(d, val, "InterDisplay-Bold", 42 * s, x1 - 90 - tx), P["accent"], b, blur=10)

# ------------------------------------------------------------------ flow
def flow(L, box, P, v, t, dur, ctx):
    x0, y0, x1, y1 = box; s = _S(box); w = x1 - x0; cw = w * .34; top = y0 + 40 * s; bot = y1 - 90 * s
    fr, to = v.get("from", {}), v.get("to", {}); a = prog(t, 0, .35); a2 = _rv(t, 1.5, dur); dr = prog(t, .8, max(1.5, dur * .85))
    glass(L, (x0, top, x0 + cw, bot), a, tint=_tint(P, fr.get("tone", "neutral")), edge=_edge(P, fr.get("tone", "neutral")))
    glass(L, (x1 - cw, top, x1, bot), a2, tint=_tint(P, to.get("tone", "bad")), edge=_edge(P, to.get("tone", "bad"))); d = BD(L)
    def card(px, node, al, tcol):
        y = top + 22 * s; mw = cw - 52
        if node.get("kicker"): d.text((px, y), str(node["kicker"]).upper(), font=F("Inter-Bold", 22 * s), fill=A(P["muted"], al)); y += 34 * s
        tt = str(node.get("title", "")); tf = fit(d, tt, "InterDisplay-Bold", 40 * s, mw); d.text((px, y), tt, font=tf, fill=A(tcol, al)); y += tf.size * 1.3
        if node.get("sub"):
            for ln in wrap(d, str(node["sub"]), F("Inter-Medium", 22 * s), mw)[:2]: d.text((px, y), ln, font=F("Inter-Medium", 22 * s), fill=A(P["muted"], al)); y += 30 * s
        return y
    y = card(x0 + 26, fr, a, P["text"]); toks = (fr.get("tokens") or v.get("tokens") or ["ETH", "USDT", "USDC"])[:4]
    for i, sym in enumerate(toks):
        if dr < .3 + i * .2: token_badge(d, x0 + 50 + i * 60 * s, y + 30 * s, 22 * s, sym)
    by = bot - 50 * s; d.rounded_rectangle([x0 + 26, by, x0 + cw - 26, by + 24 * s], 12, fill=A(P["grid"], a))
    if dr < .97: d.rounded_rectangle([x0 + 26, by, x0 + 26 + (cw - 52) * (1 - dr), by + 24 * s], 12, fill=A(P["good"] if dr < .5 else P["bad"], a))
    y2 = card(x1 - cw + 26, to, a2, _tone(P, to.get("tone", "bad")))
    am = v.get("amount")
    if am and a2 > 0:
        txt = _fmtv(am.get("value"), am.get("decimals", 1), dr, am.get("prefix", "~"), " " + str(am.get("suffix", "")))
        d.text((x1 - cw + 26, max(y2 + 10 * s, bot - 110 * s)), txt, font=fit(d, txt, "InterDisplay-Bold", 40 * s, cw - 52), fill=A(P["text"], a2))
    sx, ex, cy = x0 + cw, x1 - cw, (top + bot) / 2
    pts = [(sx + (ex - sx) * u, cy - 80 * s * math.sin(math.pi * u)) for u in [i / 40 for i in range(41)]]
    d.line(pts, fill=A(P["grid"], a), width=4)
    if .02 < dr < .99:
        for k in range(5):
            u = (t * .45 + k / 5) % 1; x, y = sx + (ex - sx) * u, cy - 80 * s * math.sin(math.pi * u)
            soft_dot(L, x, y, 22 * s, P["accent"], .7); d = BD(L); token_badge(d, x, y, 19 * s, toks[k % len(toks)])
    if v.get("caption"):
        c = _rv(t, 3, dur); cap = str(v["caption"]); d.text((x0 + 10, y1 - 50 * s), cap, font=fit(d, cap, "Inter-SemiBold", 26 * s, w - 20), fill=A(P["muted"], c))

# ------------------------------------------------------------------ range
def range_bar(L, box, P, v, t, dur, ctx):
    x0, y0, x1, y1 = box; s = _S(box); a = prog(t, 0, .35)
    glass(L, (x0, y0 + 20 * s, x1, y1), a, tint=P["tint"], edge=P["edge"]); d = BD(L)
    d.text((x0 + 30, y0 + 40 * s), str(v.get("title", "")).upper(), font=fit(d, str(v.get("title", "")).upper(), "Inter-Bold", 26 * s, x1 - x0 - 60), fill=A(P["muted"], a))
    lo, hi = _num(v.get("min", 0)) or 0, _num(v.get("max", 1)) or 1; unit = str(v.get("unit", ""))
    marks = sorted(v.get("markers") or [], key=lambda m: _num(m.get("value")) or 0)[:4]
    bx0, bx1 = x0 + 50, x1 - 50; yb = y0 + 210 * s; X = lambda val: bx0 + (clamp((val - lo) / (hi - lo)) if hi > lo else .5) * (bx1 - bx0)
    d.rounded_rectangle([bx0, yb, bx1, yb + 22], 11, fill=A(P["grid"], 1))
    if marks:
        k = prog(t, .3, 2.0); m0, m1 = _num(marks[0]["value"]), _num(marks[-1]["value"]); gw = int((X(m1) - X(m0)) * k)
        if gw > 2:
            g = grad(gw, 22, [(0, P["accent"]), (1, P.get("accent2", P["bad"]))]).convert("RGBA"); m = Image.new("L", g.size, 0)
            ImageDraw.Draw(m).rounded_rectangle([0, 0, gw - 1, 21], 11, fill=255); g.putalpha(m); safe_comp(L, g, X(m0), yb); d = BD(L)
    for val, lab in [(lo, fmt_num(lo, 0) + " " + unit), (hi, fmt_num(hi, 0) + " " + unit)]:
        d.line([(X(val), yb + 30), (X(val), yb + 42)], fill=A(P["muted"], 1), width=2); text_c(d, X(val), yb + 48, lab, F("Inter-Medium", 22 * s), A(P["muted"], 1))
    for i, m in enumerate(marks):
        b = prog(t, .8 + i * .7, 1.15 + i * .7)
        if b <= 0: continue
        x = X(_num(m["value"])); above = i % 2 == 0; soft_dot(L, x, yb + 11, 14, P["accent"], b); d = BD(L)
        d.ellipse([x - 9, yb + 2, x + 9, yb + 20], fill=(255, 255, 255, int(255 * b)))
        lab, who = str(m.get("label", "")), str(m.get("who", ""))
        if above:
            d.line([(x, yb - 8), (x, yb - 40)], fill=A(P["accent"], .8 * b), width=2)
            text_c(d, x, yb - 110 * s, lab, F("InterDisplay-Bold", 38 * s), A(P["text"], b)); text_c(d, x, yb - 62 * s, who, F("Inter-SemiBold", 22 * s), A(P["muted"], b))
        else:
            d.line([(x, yb + 28), (x, yb + 44)], fill=A(P["accent"], .8 * b), width=2)
            text_c(d, x, yb + 50 * s, lab, F("InterDisplay-Bold", 34 * s), A(P["text"], b)); text_c(d, x, yb + 92 * s, who, F("Inter-SemiBold", 22 * s), A(P["muted"], b))
    c = _rv(t, len(marks) * 2 + 1, dur); y = yb + 130 * s
    for note in (v.get("notes") or [])[:2]:
        d.text((x0 + 30, y), str(note), font=fit(d, str(note), "Inter-Medium", 24 * s, x1 - x0 - 60), fill=A(P["muted"], c)); y += 36 * s

# ------------------------------------------------------------------ price_chart
def price_chart(L, box, P, v, t, dur, ctx):
    x0, y0, x1, y1 = box; s = _S(box); a = prog(t, 0, .3); k = prog(t, .1, max(1.0, dur * .85))
    data = ctx.get("ohlc"); illus = ctx.get("illustrative", True)
    if not data: data = synth_ohlc(48, _num(v.get("start", 100)) or 100, _num(v.get("end", 95)) or 95); illus = True
    cw = (x1 - x0) * .72; title = f"{v.get('symbol', 'BTC')}/USD · {v.get('timeframe_label', '')}" + (" · minh họa" if illus else " · CoinGecko")
    ch = pro_chart(int(cw), int(y1 - y0 - 10), data, max(.03, k), title, P); fade_paste(L, ch, a, (x0, y0 + 10))
    sx = x0 + cw + 20; glass(L, (sx, y0 + 20, x1, y1 - 20), a, tint=P["tint"], edge=P["edge"]); d = BD(L); px = sx + 20; mw = x1 - px - 16
    n = max(1, int(len(data) * max(.03, k))); cur = data[n - 1][3]; first = data[0][0]; chg = (cur - first) / first * 100 if first else 0
    col = P["good"] if chg >= 0 else P["bad"]; y = y0 + 40
    d.text((px, y), str(v.get("symbol", "")), font=F("Inter-Bold", 30 * s), fill=A(P["muted"], a)); y += 48 * s
    pr = fmt_price(cur); glow_text(L, (px, y), pr, fit(d, pr, "InterDisplay-Bold", 50 * s, mw), col, a, blur=12); d = BD(L); y += 64 * s
    d.text((px, y), ("▲ " if chg >= 0 else "▼ ") + f"{abs(chg):.2f}%".replace(".", ","), font=F("Inter-Bold", 26 * s), fill=A(col, a)); y += 50 * s
    d.line([(px, y), (x1 - 20, y)], fill=A(P["grid"], a), width=2); y += 16
    for st in (v.get("side") or [])[:2]:
        lab, val = str(st.get("label", "")), str(st.get("value", ""))
        d.text((px, y), lab, font=fit(d, lab, "Inter-Medium", 20 * s, mw), fill=A(P["muted"], a)); y += 28 * s
        d.text((px, y), val, font=fit(d, val, "Inter-Bold", 28 * s, mw), fill=A(_tone(P, st.get("tone", "neutral")), a)); y += 46 * s

# ------------------------------------------------------------------ gauge
def _fg_label(x):
    return "Cực kỳ sợ hãi" if x < 25 else "Sợ hãi" if x < 45 else "Trung lập" if x <= 55 else "Tham lam" if x <= 75 else "Cực kỳ tham lam"

def gauge(L, box, P, v, t, dur, ctx):
    x0, y0, x1, y1 = box; s = _S(box); a = prog(t, 0, .35)
    fg = ctx.get("fear_greed") if v.get("auto") == "fear_greed" else None
    v0 = (fg or {}).get("prev", _num(v.get("from", 50)) or 50); v1 = (fg or {}).get("now", _num(v.get("to", 50)) or 50)
    glass(L, (x0, y0, x1, y1), a, tint=P["tint"], edge=P["edge"]); d = BD(L)
    title = str(v.get("title", "Chỉ số Sợ hãi & Tham lam")).upper(); d.text((x0 + 30, y0 + 20), title, font=fit(d, title, "Inter-Bold", 26 * s, x1 - x0 - 60), fill=A(P["muted"], a))
    r = min((x1 - x0) * .3, (y1 - y0) * .55); cx, cy = x0 + 40 + r, y1 - 50 * s
    segs = [(P["bad"], 180, 216), ((255, 150, 90), 216, 252), ((230, 210, 90), 252, 288), ((140, 210, 110), 288, 324), (P["good"], 324, 360)]
    for c, s0, s1 in segs: d.arc([cx - r, cy - r, cx + r, cy + r], s0 + 1.5, s1 - 1.5, fill=A(c, a), width=int(34 * s))
    val = lerp(v0, v1, prog(t, .4, min(2.6, dur * .7))); ang = math.radians(180 + 1.8 * val)
    tip = (cx + (r - 54) * math.cos(ang), cy + (r - 54) * math.sin(ang)); col = P["bad"] if val < 45 else P["good"] if val > 55 else (230, 210, 90)
    soft_dot(L, tip[0], tip[1], 14, col, a); d = BD(L)
    d.line([(cx, cy), tip], fill=A(P["text"], a), width=8); d.ellipse([cx - 16, cy - 16, cx + 16, cy + 16], fill=A(P["text"], a))
    rx = cx + r + 60 * s; mw = x1 - rx - 20
    d.text((rx, y0 + 90 * s), str(v.get("from_label", "Trước đó")), font=F("Inter-Medium", 24 * s), fill=A(P["muted"], a))
    d.text((rx, y0 + 122 * s), f"{int(v0)} · {_fg_label(v0)}", font=fit(d, f"{int(v0)} · {_fg_label(v0)}", "Inter-Bold", 30 * s, mw), fill=A(P["muted"], a))
    d.text((rx, y0 + 190 * s), str(v.get("to_label", "Hiện tại")), font=F("Inter-Medium", 24 * s), fill=A(P["muted"], a))
    glow_text(L, (rx, y0 + 222 * s), str(int(round(val))), F("InterDisplay-Bold", 92 * s), col, a, blur=14); d = BD(L)
    d.text((rx + 4, y0 + 330 * s), _fg_label(val), font=fit(d, _fg_label(val), "Inter-Bold", 34 * s, mw), fill=A(col, prog(t, 2.0, 2.5)))

# ------------------------------------------------------------------ timeline
def timeline(L, box, P, v, t, dur, ctx):
    x0, y0, x1, y1 = box; s = _S(box); a = prog(t, 0, .35); evs = (v.get("events") or [])[:4]; n = max(1, len(evs))
    glass(L, (x0, y0, x1, y1), a, tint=P["tint"], edge=P["edge"]); d = BD(L)
    if v.get("title"): d.text((x0 + 30, y0 + 20), str(v["title"]).upper(), font=fit(d, str(v["title"]).upper(), "Inter-Bold", 26 * s, x1 - x0 - 60), fill=A(P["muted"], a))
    lx = x0 + 70; top = y0 + 80 * s; step = (y1 - top - 30) / n; lp = prog(t, 0, max(1, dur * .8))
    d.line([(lx, top + 30), (lx, top + 30 + (n - 1) * step * lp)], fill=A(P["grid"], 1), width=6)
    for i, e in enumerate(evs):
        st = (dur * .75) * i / n; b = prog(t, st, st + .35); yy = top + i * step
        if b <= 0: continue
        col = _tone(P, e.get("tone", "accent")); soft_dot(L, lx, yy + 30, 18, col, b); d = BD(L)
        d.ellipse([lx - 12, yy + 18, lx + 12, yy + 42], fill=A(col, b))
        tf = F("InterDisplay-Bold", min(52 * s, step * .42)); d.text((lx + 40, yy), str(e.get("time", "")), font=tf, fill=A(P["text"], b))
        tw = d.textlength(str(e.get("time", "")), font=tf)
        if e.get("badge"):
            bf = F("Inter-Bold", 24 * s); bw = d.textlength(str(e["badge"]), font=bf)
            d.rounded_rectangle([lx + 60 + tw, yy + 8, lx + 88 + tw + bw, yy + 8 + 40 * s], 10, fill=A(mix(P["bg"], col, .3), b)); d.text((lx + 74 + tw, yy + 13), str(e["badge"]), font=bf, fill=A(col, b))
        tx = lx + 40
        if e.get("token"): token_badge(d, lx + 56, yy + tf.size * 1.2 + 18 * s, 16 * s, e["token"]); tx = lx + 82
        txt = str(e.get("text", "")); d.text((tx, yy + tf.size * 1.2), txt, font=fit(d, txt, "Inter-Medium", 30 * s, x1 - tx - 30), fill=A(P["muted"], b))

# ------------------------------------------------------------------ tx_card
def tx_card(L, box, P, v, t, dur, ctx):
    x0, y0, x1, y1 = box; s = _S(box); a = prog(t, 0, .35)
    glass(L, (x0, y0, x1, y1), a, tint=P["tint"], edge=P["edge"]); d = BD(L)
    tt = str(v.get("title", "Transaction Details")); d.text((x0 + 30, y0 + 20), tt, font=fit(d, tt, "Inter-Bold", 28 * s, x1 - x0 - 220), fill=A(P["muted"], a))
    rows = (v.get("rows") or [])[:5]; toks = (v.get("tokens") or [])[:4]; nb = len(rows) + len(toks) + 2
    span = dur * .8; at = lambda i: prog(t, span * i / nb, span * i / nb + .35)
    if v.get("status"):
        sb = at(len(rows)); st = "✓ " + str(v["status"]); sf = F("Inter-Bold", 22 * s); sw = d.textlength(st, font=sf)
        d.rounded_rectangle([x1 - sw - 60, y0 + 18, x1 - 30, y0 + 18 + 40 * s], 10, fill=A(mix(P["bg"], P["good"], .35), sb)); d.text((x1 - sw - 45, y0 + 24), st, font=sf, fill=A(P["good"], sb))
    y = y0 + 75 * s; rh = min(46 * s, (y1 - y0 - 140 * s) / max(1, nb))
    for i, r in enumerate(rows):
        b = at(i)
        if b > 0:
            col = _tone(P, r.get("tone", "neutral"))
            if r.get("tone") == "bad": soft_dot(L, x0 + 400, y + 16, 30, col, .4 * b, blur=16); d = BD(L)
            d.text((x0 + 30, y), str(r.get("k", "")), font=F("Inter-Medium", 24 * s), fill=A(P["muted"], b))
            vv = str(r.get("v", "")); d.text((x0 + 200 + 30 * (1 - b), y), vv, font=fit(d, vv, "Inter-Bold", 26 * s, x1 - x0 - 240), fill=A(col, b))
        y += rh
    if toks:
        d.line([(x0 + 30, y + 4), (x1 - 30, y + 4)], fill=A(P["grid"], a), width=2); y += 18
        hb = at(len(rows) + 1); tt2 = str(v.get("tokens_title", "Token chuyển đi")); d.text((x0 + 30, y), tt2, font=fit(d, tt2, "Inter-Bold", 24 * s, x1 - x0 - 60), fill=A(P["muted"], hb)); y += rh
        for i, tk in enumerate(toks):
            b = at(len(rows) + 2 + i)
            if b > 0:
                token_badge(d, x0 + 52, y + 16, 17 * s, tk.get("sym", "?"))
                am = str(tk.get("amount", "")); d.text((x0 + 86, y), am, font=fit(d, am, "Inter-Bold", 26 * s, (x1 - x0) * .45), fill=A(P["text"], b))
                nt = str(tk.get("note", "")); d.text((x0 + (x1 - x0) * .55, y + 2), nt, font=fit(d, nt, "Inter-Medium", 24 * s, (x1 - x0) * .42), fill=A(P["muted"], b))
            y += rh

# ------------------------------------------------------------------ graph
def graph(L, box, P, v, t, dur, ctx):
    x0, y0, x1, y1 = box; s = _S(box); a = prog(t, 0, .35); d = BD(L)
    if v.get("title"): text_c(d, (x0 + x1) / 2, y0, str(v["title"]), fit(d, str(v["title"]), "Inter-Bold", 38 * s, x1 - x0), A(P["text"], a))
    br = (v.get("branches") or [])[:4]; n = max(1, len(br)); cx, cy = (x0 + x1) / 2, y0 + 150 * s
    pos = [(x0 + 120 + (x1 - x0 - 240) * (i / (n - 1) if n > 1 else .5), y1 - 90 * s - (40 * s if i % 2 else 0)) for i in range(n)]
    for i, b in enumerate(br):
        st = .4 + (dur * .6) * i / n; k = prog(t, st, st + .8); col = _tone(P, b.get("tone", "ice")); px, py = pos[i]
        if k <= 0: continue
        d.line([(cx, cy + 50 * s), (lerp(cx, px, k), lerp(cy + 50 * s, py - 50 * s, k))], fill=A(col, .8), width=5)
        if b.get("tone") == "bad" and k > .2:
            for j in range(3):
                u = ((t * .7 + j / 3) % 1) * k; x, y = lerp(cx, px, u), lerp(cy + 50 * s, py - 50 * s, u)
                soft_dot(L, x, y, 12, col, 1, blur=6); d = BD(L); d.ellipse([x - 6, y - 6, x + 6, y + 6], fill=A(col, 1))
    glass(L, (cx - 120 * s, cy - 50 * s, cx + 120 * s, cy + 50 * s), a, tint=_tint(P, "bad"), edge=P["bad"]); d = BD(L)
    c = v.get("center", {}); text_c(d, cx, cy - 36 * s, str(c.get("title", "")), fit(d, str(c.get("title", "")), "Inter-Bold", 30 * s, 220 * s), A(P["bad"], a))
    text_c(d, cx, cy + 6 * s, str(c.get("sub", "")), F("Inter-Medium", 22 * s), A(P["muted"], a))
    bw = min(250 * s, (x1 - x0) / n - 10)
    for i, b in enumerate(br):
        st = .4 + (dur * .6) * i / n; k = prog(t, st + .6, st + 1.0); tone = b.get("tone", "ice"); col = _tone(P, tone); px, py = pos[i]
        if k <= 0: continue
        glass(L, (px - bw / 2, py - 50 * s, px + bw / 2, py + 55 * s), k, tint=_tint(P, tone), edge=col); d = BD(L)
        tx = px - bw / 2 + 20
        if tone == "ice": lock_icon(d, tx + 18 * s, py + 6, 24 * s, A(col, k), A(_tint(P, tone), 1)); tx += 44 * s
        elif b.get("token"): token_badge(d, tx + 18 * s, py, 18 * s, b["token"]); tx += 44 * s
        lab = str(b.get("label", "")); d.text((tx, py - 36 * s), lab, font=fit(d, lab, "Inter-ExtraBold", 26 * s, px + bw / 2 - tx - 10), fill=A(col, k))
        sub = str(b.get("sub", "")); d.text((tx, py + 6 * s), sub, font=fit(d, sub, "Inter-Bold", 21 * s, px + bw / 2 - tx - 10), fill=A(P["text"], k))

# ------------------------------------------------------------------ bullets
def bullets(L, box, P, v, t, dur, ctx):
    x0, y0, x1, y1 = box; s = _S(box); a = prog(t, 0, .35); items = (v.get("items") or [])[:4]; n = max(1, len(items))
    glass(L, (x0, y0, x1, y1), a, tint=P["tint"], edge=P["edge"]); d = BD(L); y = y0 + 26 * s
    if v.get("title"):
        tt = str(v["title"]); tf = fit(d, tt, "InterDisplay-Bold", 46 * s, x1 - x0 - 60); glow_text(L, (x0 + 30, y), tt, tf, P["accent"], a, blur=10); d = BD(L); y += tf.size * 1.5
    step = min(92 * s, (y1 - y - 20) / n)
    for i, it in enumerate(items):
        b = prog(t, (dur * .7) * i / n, (dur * .7) * i / n + .35)
        if b <= 0: continue
        tone = it.get("tone", "accent"); col = _tone(P, tone); cy = y + i * step + 22 * s; cx = x0 + 52
        if tone == "good": d.ellipse([cx - 18, cy - 18, cx + 18, cy + 18], fill=A(col, b)); d.line([(cx - 8, cy), (cx - 2, cy + 7), (cx + 9, cy - 7)], fill=A(P["bg"], 1), width=4)
        elif tone in ("bad", "alert"): d.ellipse([cx - 18, cy - 18, cx + 18, cy + 18], fill=A(col, b)); d.line([(cx - 7, cy - 7), (cx + 7, cy + 7)], fill=A(P["bg"], 1), width=4); d.line([(cx - 7, cy + 7), (cx + 7, cy - 7)], fill=A(P["bg"], 1), width=4)
        elif tone == "ice": lock_icon(d, cx, cy + 4, 20, A(col, b), A(P["bg"], 1))
        else: d.ellipse([cx - 10, cy - 10, cx + 10, cy + 10], fill=A(col, b))
        f = F("Inter-Bold", 32 * s); lines = wrap(d, str(it.get("text", "")), f, x1 - cx - 60)[:2]
        for j, ln in enumerate(lines): d.text((cx + 40 + 20 * (1 - b), cy - 20 * s + j * 40 * s), ln, font=f, fill=A(P["text"], b))

# ------------------------------------------------------------------ cta
def cta(L, box, P, v, t, dur, ctx):
    x0, y0, x1, y1 = box; s = _S(box); a = prog(t, 0, .45); cx = (x0 + x1) / 2
    glass(L, (x0 + 60, y0 + 10, x1 - 60, y1 - 10), a, tint=P["tint"], edge=P["edge"]); d = BD(L)
    logo = ctx.get("logo"); y = y0 + 40 * s
    if logo is not None:
        hgt = int(130 * s); mk = logo.resize((int(logo.width * hgt / logo.height), hgt)); soft_dot(L, cx, y + hgt / 2, 70 * s, P["glow"], .45 * a, blur=30)
        fade_paste(L, mk, a, (cx - mk.width / 2, y + 14 * (1 - a))); d = BD(L); y += hgt + 24 * s
    t1 = str(v.get("title", "")); text_c(d, cx, y, t1, fit(d, t1, "InterDisplay-Bold", 56 * s, x1 - x0 - 160), A(P["text"], a)); y += 74 * s
    t2 = str(v.get("subtitle", "")); text_c(d, cx, y, t2, fit(d, t2, "Inter-Medium", 30 * s, x1 - x0 - 160), A(P["accent"], prog(t, .4, .9))); y += 56 * s
    b = prog(t, .7, 1.1); p = .5 + .5 * math.sin(t * 5); bw = 240 * s
    d.rounded_rectangle([cx - bw / 2, y, cx + bw / 2, y + 56 * s], 28, fill=A(mix(P["accent"], (255, 255, 255), p * .25), b))
    text_c(d, cx, y + 10 * s, "+ THEO DÕI", F("Inter-ExtraBold", 28 * s), A(P["bg"], b)); y += 76 * s
    t3 = str(v.get("disclaimer", "")); text_c(d, cx, y, t3, fit(d, t3, "Inter-Medium", 22 * s, x1 - x0 - 160), A(P["muted"], prog(t, 1.0, 1.4)))

# ------------------------------------------------------------------ quote (phát ngôn chính thức)
def quote(L, box, P, v, t, dur, ctx):
    x0, y0, x1, y1 = box; s = _S(box); a = prog(t, 0, .35); tone = v.get("tone", "neutral")
    glass(L, (x0, y0 + 20, x1, y1 - 20), a, tint=_tint(P, tone), edge=_edge(P, tone)); d = BD(L)
    glow_text(L, (x0 + 26, y0 + 10), "“", F("InterDisplay-Bold", 150 * s), P["accent"], a, blur=12, strength=90); d = BD(L)
    px = x0 + 40; mw = x1 - x0 - 80; y = y0 + 120 * s
    qf = F("InterDisplay-Bold", 46 * s); lines = wrap(d, str(v.get("text", "")), qf, mw)
    if len(lines) > 4: qf = F("InterDisplay-Bold", 36 * s); lines = wrap(d, str(v.get("text", "")), qf, mw)[:5]
    for i, ln in enumerate(lines):
        b = prog(t, .3 + i * .25, .6 + i * .25); d.text((px + 20 * (1 - b), y), ln, font=qf, fill=A(P["text"], b)); y += qf.size * 1.3
    b = _rv(t, len(lines) + 1, dur); y = max(y + 20 * s, y1 - 130 * s); lx = px
    if v.get("logo"):
        img = LOGOS.get(str(v["logo"]).upper())
        if img is not None: paste_logo(L, img, px + 32 * s, y + 34 * s, 32 * s, b)
        else: token_badge(d, px + 32 * s, y + 34 * s, 30 * s, v["logo"])
        d = BD(L); lx = px + 80 * s
    d.text((lx, y), str(v.get("who", "")), font=fit(d, str(v.get("who", "")), "Inter-Bold", 32 * s, x1 - lx - 40), fill=A(P["accent"], b))
    d.text((lx, y + 42 * s), str(v.get("role", "")), font=fit(d, str(v.get("role", "")), "Inter-Medium", 24 * s, x1 - lx - 40), fill=A(P["muted"], b))

# ------------------------------------------------------------------ news_card (các nguồn báo đưa tin)
def news_card(L, box, P, v, t, dur, ctx):
    x0, y0, x1, y1 = box; s = _S(box); items = (v.get("items") or [])[:3]; n = max(1, len(items)); d = BD(L)
    if v.get("title"): text_c(d, (x0 + x1) / 2, y0, str(v["title"]), fit(d, str(v["title"]), "Inter-Bold", 34 * s, x1 - x0), A(P["text"], prog(t, 0, .35)))
    top = y0 + (60 * s if v.get("title") else 0); gap = 18 * s; ch = (y1 - top - gap * (n - 1)) / n
    for i, it in enumerate(items):
        b = prog(t, (dur * .6) * i / n, (dur * .6) * i / n + .4); yy = top + i * (ch + gap) + 30 * (1 - b)
        if b <= 0: continue
        glass(L, (x0, yy, x1, yy + ch), b, tint=P["tint"], edge=P["edge"]); d = BD(L)
        px = x0 + 28; d.rounded_rectangle([px, yy + 20 * s, px + 8, yy + ch - 20 * s], 4, fill=A(P["accent"], b))
        out = str(it.get("outlet", "")).upper(); d.text((px + 28, yy + 18 * s), out, font=fit(d, out, "Inter-ExtraBold", 24 * s, (x1 - x0) * .6), fill=A(P["accent"], b))
        if it.get("date"):
            df = F("Inter-Medium", 22 * s); dw = d.textlength(str(it["date"]), font=df); d.text((x1 - 30 - dw, yy + 20 * s), str(it["date"]), font=df, fill=A(P["muted"], b))
        hf = F("Inter-Bold", 30 * s if n > 1 else 40 * s); hy = yy + 58 * s
        for ln in wrap(d, str(it.get("headline", "")), hf, x1 - px - 60)[:(2 if n > 1 else 4)]:
            d.text((px + 28, hy), ln, font=hf, fill=A(P["text"], b)); hy += hf.size * 1.28

TEMPLATES = {"hero": hero, "quote": quote, "news_card": news_card, "big_number": big_number, "stat_cards": stat_cards, "flow": flow, "range": range_bar,
             "price_chart": price_chart, "gauge": gauge, "timeline": timeline, "tx_card": tx_card, "graph": graph,
             "bullets": bullets, "cta": cta}
