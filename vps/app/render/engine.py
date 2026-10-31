"""Ghép kịch bản JSON + các đoạn giọng đọc -> video MP4 1080x1920 30fps (H.264 + AAC 48kHz)."""
import subprocess, json, logging, os
from .core import *
from .themes import THEMES
from .templates import TEMPLATES
from .. import market

log = logging.getLogger("engine")
LEAD, GAP, TAIL, XF = 0.15, 0.25, 0.9, 0.35

def probe_duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path], capture_output=True, text=True)
    return float(out.stdout.strip())

def build_audio(paths, out_wav):
    """nối các đoạn giọng với khoảng lặng GAP, chèn LEAD ở đầu -> (wav, [(start, dur)])"""
    durs = [probe_duration(p) for p in paths]; starts = []; t = LEAD
    for d in durs: starts.append(t); t += d + GAP
    inputs = []; filt = []; ld = int(LEAD * 1000)
    for i, p in enumerate(paths):
        inputs += ["-i", p]; pre = f"adelay={ld}|{ld}," if i == 0 else ""
        filt.append(f"[{i}:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,{pre}apad=pad_dur={GAP}[a{i}]")
    filt.append("".join(f"[a{i}]" for i in range(len(paths))) + f"concat=n={len(paths)}:v=0:a=1,apad=pad_dur={TAIL}[out]")
    subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", ";".join(filt), "-map", "[out]", "-ar", "48000", "-ac", "2", out_wav], check=True)
    return out_wav, list(zip(starts, durs)), t - GAP + TAIL

class Video:
    def __init__(self, script, channel_cfg, beat_audio, workdir, market_cfg=None, offline=False):
        self.s = script; self.cfg = channel_cfg; self.work = workdir; os.makedirs(workdir, exist_ok=True)
        self.theme = THEMES[channel_cfg["theme"]](); self.theme.static(script); self.P = self.theme.P
        self.beats = list(script["beats"]) + [{"voice": channel_cfg["cta_voice"], "visual": {"type": "cta", "title": channel_cfg["cta_title"],
                                                  "subtitle": channel_cfg["cta_subtitle"], "disclaimer": channel_cfg["disclaimer"]}}]
        assert len(beat_audio) == len(self.beats), f"số đoạn giọng ({len(beat_audio)}) != số beat ({len(self.beats)})"
        self.wav, self.times, self.total = build_audio(beat_audio, os.path.join(workdir, "voice_mix.wav"))
        mc = market_cfg or {}; key = mc.get("coingecko_key")
        self.tape = [] if offline or self.theme.TAPE is None else market.ticker(mc.get("ticker", ["BTC", "ETH", "BNB", "SOL", "XRP"]), key)
        self.ctx = []
        fg = None
        for b in self.beats:
            v = b.get("visual", {}); c = {}
            if v.get("type") == "price_chart":
                data = None if offline else market.ohlc(v.get("symbol", "BTC"), v.get("days", 1), key)
                c = {"ohlc": data, "illustrative": data is None}
            if v.get("type") == "gauge" and v.get("auto") == "fear_greed":
                if fg is None and not offline: fg = market.fear_greed()
                c = {"fear_greed": fg}
            if v.get("type") == "cta": c = {"logo": self.theme.logo_for_cta()}
            self.ctx.append(c)
        self.box = self.theme.BOX

    def _beat_at(self, t):
        idx = 0
        for i, (st, d) in enumerate(self.times):
            if t >= st - GAP / 2: idx = i
        return idx

    def _content(self, i, lt):
        b = self.beats[i]; v = b.get("visual") or {}; fn = TEMPLATES.get(v.get("type"))
        if fn is None: fn = TEMPLATES["bullets"]; v = {"title": "", "items": [{"text": b.get("voice", "")[:120], "tone": "accent"}]}
        L = layer(*self.theme.WIN); dur = self.times[i][1]
        try: fn(L, self.box, self.P, v, lt, dur, self.ctx[i])
        except Exception as e: log.exception("lỗi vẽ beat %d (%s): %s", i, v.get("type"), e)
        return L

    def frame(self, t):
        i = self._beat_at(t); st = self.times[i][0] - GAP / 2; lt = t - self.times[i][0]
        cur = self._content(i, max(0.0, lt))
        if i > 0 and t - st < XF:
            u = ease((t - st) / XF); prev = self._content(i - 1, self.times[i - 1][1] + GAP / 2)
            out = layer(*self.theme.WIN); safe_comp(out, with_alpha(prev, 1 - u), -80 * u, 0); safe_comp(out, with_alpha(cur, u), 80 * (1 - u), 0); cur = out
        tape = None
        if self.theme.TAPE:
            tape = ticker_tape(self.theme.WIN[0], t, self.tape, h=self.theme.TAPE, bg=self.P["tape_bg"], up=self.P["good"], dn=self.P["bad"], txt=self.P["text"], line=self.P["tape_line"]) if self.tape else None
        return self.theme.compose(t, cur, tape)

    def render(self, out_mp4, preview_png=None):
        n = int(self.total * FPS)
        cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
               "-i", self.wav, "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "veryfast", "-crf", "19", "-g", str(FPS * 2),
               "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", "-shortest", "-movflags", "+faststart", out_mp4]
        p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        for k in range(n):
            im = self.frame(k / FPS)
            if preview_png and k == int(FPS * 1.5): im.convert("RGB").save(preview_png)
            p.stdin.write(im.convert("RGB").tobytes())
            if k % 300 == 0: log.info("render %s %d/%d", os.path.basename(out_mp4), k, n)
        p.stdin.close(); rc = p.wait()
        if rc: raise RuntimeError("ffmpeg lỗi khi xuất video")
        return out_mp4
