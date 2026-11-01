"""Hai bộ nhận diện: ChainFolk (bản tin, khung 16:9 giữa) và TND GEMS (video tràn trên, bảng tiêu đề dưới)."""
import os
from PIL import Image, ImageDraw, ImageFilter
from .core import *

class Theme:
    name = ""; P = {}
    def static(self, script): ...
    def compose(self, t, content, tape): ...

# ======================= ChainFolk =======================
class ChainFolk(Theme):
    name = "chainfolk"
    BG = (3, 7, 26); CY = (0, 229, 245); BL = (40, 120, 255); PU = (138, 43, 226)
    GRAD = [(0, CY), (0.5, BL), (1, PU)]
    P = dict(bg=(6, 12, 34), text=(244, 246, 255), muted=(140, 152, 196), accent=(0, 229, 245), good=(0, 214, 160),
             bad=(255, 84, 112), ice=(0, 229, 245), tint=(20, 34, 72), edge=(0, 229, 245), bad_tint=(30, 18, 40),
             good_tint=(14, 40, 44), ice_tint=(20, 34, 72), grid=(22, 34, 66), net=(0, 229, 245), tape_bg=(4, 10, 28), tape_line=(40, 56, 100), glow=(40, 120, 255), accent2=(138, 43, 226))
    TOP, BH, LT = 390, 608, 72
    WIN = (1080, 608 - 72)          # vùng nội dung (trên dải chữ chạy)
    TAPE = 54
    BOX = (24, 70, 905, 526)        # vùng an toàn để vẽ template (trong WIN)
    handle_safe_right = 905

    def __init__(self):
        self.mark = Image.open(os.path.join(LOGO_DIR, "chainfolk_mark.png")).convert("RGBA")
        self.word = Image.open(os.path.join(LOGO_DIR, "chainfolk_word.png")).convert("RGBA")

    def static(self, s):
        P = self.P; im = Image.new("RGBA", (W, H), self.BG + (255,))
        glow_blob(im, (240, 150, 840, 380), self.BL, 28, 80)
        mk = self.mark.resize((int(self.mark.width * 120 / self.mark.height), 120), Image.LANCZOS)
        wm = self.word.resize((int(self.word.width * 74 / self.word.height), 74), Image.LANCZOS)
        tw = mk.width + 24 + wm.width; x0 = (W - tw) // 2
        im.alpha_composite(mk, (x0, 205)); im.alpha_composite(wm, (x0 + mk.width + 24, 229))
        d = ImageDraw.Draw(im); ly = self.TOP + self.BH - self.LT
        d.rectangle([0, ly, W, self.TOP + self.BH], fill=(245, 247, 255, 255))
        d.rectangle([0, ly, 210, self.TOP + self.BH], fill=self.CY + (255,))
        d.text((26, ly + 16), "TIN NHANH", font=F("InterDisplay-Bold", 30), fill=self.BG)
        lt = (s.get("ticker_line") or "").upper()
        d.text((232, ly + 16), lt, font=fit(d, lt, "InterDisplay-Bold", 30, 660, 20), fill=self.BG)
        y = self.TOP + self.BH + 64
        d.text((90, y), "Ngày đăng: " + s.get("date", ""), font=F("InterDisplay-MediumItalic", 36), fill=P["muted"]); y += 70
        segs = [(t, self.CY if tone == "accent" else P["text"]) for t, tone in s["headline"]]
        size = 72
        while size > 52 and count_lines(segs, F("InterDisplay-Bold", size), 820) > 3: size -= 4
        y, n = wrap_head(im, 90, y, segs, F("InterDisplay-Bold", size), int(size * 1.28), 820)
        d.text((90, y + 20), s.get("source", ""), font=fit(d, s.get("source", ""), "Inter-Regular", 32, 820, 22), fill=P["muted"])
        self.base = im; self.last_text_y = y + 60
        self.win_bg = Image.new("RGBA", self.WIN, P["bg"] + (255,)); self.net = NodeNet(*self.WIN, seed=3, col=P["net"])
        return im

    def logo_for_cta(self): return self.mark

    def compose(self, t, content, tape):
        win = self.win_bg.copy(); win.alpha_composite(self.net.draw(t, .8)); win.alpha_composite(hex_rain(*self.WIN, t, alpha=20))
        win.alpha_composite(content)
        if tape is not None: win.alpha_composite(tape)
        im = self.base.copy(); im.alpha_composite(win, (0, self.TOP)); return im

# ======================= TND GEMS =======================
class TndGems(Theme):
    name = "tndgems"
    MINT = (45, 232, 154); WH = (245, 245, 245)
    P = dict(bg=(10, 14, 14), text=(245, 245, 245), muted=(150, 175, 165), accent=(45, 232, 154), good=(45, 232, 154),
             bad=(255, 84, 112), ice=(150, 225, 255), tint=(14, 30, 24), edge=(45, 232, 154), bad_tint=(40, 16, 22),
             good_tint=(14, 40, 30), ice_tint=(14, 30, 40), grid=(24, 40, 34), net=(45, 232, 154), tape_bg=(4, 12, 10), tape_line=(30, 60, 48), glow=(45, 232, 154), accent2=(150, 225, 255))
    # Bố cục theo vùng an toàn TikTok/Reels: tránh thanh tìm kiếm phía trên (~240px)
    # và phần chú thích phía dưới (~380px), nội dung + bảng tiêu đề nằm giữa màn hình.
    VH, PY = 1040, 1040
    WIN = (1080, 1040)
    TAPE = None
    BOX = (50, 262, 905, 950)

    def __init__(self):
        self.mark = Image.open(os.path.join(LOGO_DIR, "tndgems_mark.png")).convert("RGBA")

    def _facets(self, w, h, seed=3):
        import random
        r = random.Random(seed); lay = layer(w, h); d = ImageDraw.Draw(lay); step = 120; pts = {}
        for gy in range(-1, h // step + 2):
            for gx in range(-1, w // step + 2): pts[(gx, gy)] = (gx * step + r.randint(-40, 40), gy * step + r.randint(-40, 40))
        for gy in range(-1, h // step + 1):
            for gx in range(-1, w // step + 1):
                a, b, c, e = pts[(gx, gy)], pts[(gx + 1, gy)], pts[(gx, gy + 1)], pts[(gx + 1, gy + 1)]
                for tri in ([a, b, e], [a, e, c]): d.polygon(tri, fill=self.MINT + (r.randint(0, 5),), outline=self.MINT + (9,))
        return lay

    def static(self, s):
        P = self.P; py = self.PY
        im = Image.new("RGBA", (W, H), (0, 0, 0, 255))
        panel = grad(W, H - py + 120, [(0, (8, 24, 18)), (1, (2, 8, 6))], horiz=False).convert("RGBA")
        panel.alpha_composite(self._facets(W, H - py + 120))
        mask = Image.new("L", panel.size, 255); md = ImageDraw.Draw(mask)
        for i in range(120): md.line([(0, i), (W, i)], fill=int(255 * i / 120))
        im.paste(panel, (0, py - 120), mask); d = ImageDraw.Draw(im)
        d.rectangle([0, py - 1, W, py + 1], fill=self.MINT)
        pw, ph = 380, 86; px, pyy = 40, py - ph // 2
        d.rounded_rectangle([px, pyy, px + pw, pyy + ph], ph // 2, fill=(0, 0, 0), outline=self.MINT, width=4)
        mk = self.mark.resize((int(self.mark.width * 64 / self.mark.height), 64), Image.LANCZOS); im.alpha_composite(mk, (px + 24, pyy + 11))
        d = ImageDraw.Draw(im); tx = px + 24 + mk.width + 16; f = F("Inter-ExtraBold", 44)
        d.text((tx, pyy + 17), "TND", font=f, fill=self.WH); d.text((tx + d.textlength("TND ", font=f), pyy + 17), "GEMS", font=f, fill=self.MINT)
        y = py + 68
        d.text((90, y + 8), "NGÀY ĐĂNG: " + s.get("date", "").replace(".", "/"), font=F("Inter-Bold", 30), fill=self.MINT); y += 72
        segs = [(str(t).upper(), self.MINT if tone == "accent" else self.WH) for t, tone in s["headline"]]
        size = 62
        while size > 46 and count_lines(segs, F("Inter-ExtraBold", size), 820) > 3: size -= 4
        y, n = wrap_head(im, 90, y, segs, F("Inter-ExtraBold", size), int(size * 1.29), 820)
        d.text((90, y + 26), s.get("source", ""), font=fit(d, s.get("source", ""), "Inter-Medium", 32, 820, 22), fill=P["muted"])
        self.last_text_y = y + 66
        a = Image.new("L", im.size, 255); ad = ImageDraw.Draw(a); hole_b = py - 120
        ad.rectangle([0, 0, W, hole_b], fill=0)
        for i in range(120): ad.line([(0, hole_b + i), (W, hole_b + i)], fill=int(255 * i / 120))
        im.putalpha(a); self.ov = im
        self.win_bg = Image.new("RGBA", self.WIN, P["bg"] + (255,)); self.net = NodeNet(*self.WIN, seed=7, col=P["net"])
        return im

    def logo_for_cta(self): return self.mark

    def compose(self, t, content, tape):
        v = self.win_bg.copy(); v.alpha_composite(self.net.draw(t, .7)); v.alpha_composite(hex_rain(*self.WIN, t, seed=5, col=self.P["net"], alpha=18))
        v.alpha_composite(content)
        im = Image.new("RGBA", (W, H), (0, 0, 0, 255)); im.alpha_composite(v); im.alpha_composite(self.ov); return im

THEMES = {"chainfolk": ChainFolk, "tndgems": TndGems}
