"""Chạy thử engine KHÔNG cần API: python -m scripts.render_sample samples/chainfolk_binance.json [--full] [--offline]
- mặc định: xuất ảnh xem nhanh các beat (sheet PNG)
- --full: xuất cả video với giọng giả (im lặng)"""
import sys, os, json, logging
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import yaml
from PIL import Image
from app import tts
from app.render.engine import Video

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
path = sys.argv[1]; full = "--full" in sys.argv; offline = "--offline" in sys.argv
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
cfg = yaml.safe_load(open(os.path.join(root, "config.yaml"), encoding="utf-8"))
script = json.load(open(path, encoding="utf-8")); ch = cfg["channels"][script["channel"]]
name = os.path.splitext(os.path.basename(path))[0]; work = os.path.join(root, "data", "test", name)
texts = [b["voice"] for b in script["beats"]] + [ch["cta_voice"]]
audio = tts.synth_beats(texts, ch["voice"], os.path.join(work, "voice"), None, fake=True)
v = Video(script, ch, audio, work, cfg.get("market"), offline=offline)
if full:
    print(v.render(os.path.join(work, name + ".mp4"), os.path.join(work, "preview.png")))
else:
    ts = [st + d * .75 for st, d in v.times]
    sheet = Image.new("RGB", (360 * len(ts), 640))
    for i, t in enumerate(ts): sheet.paste(v.frame(t).convert("RGB").resize((360, 640)), (i * 360, 0))
    out = os.path.join(work, "sheet.png"); sheet.save(out); print(out, "tổng thời lượng %.1fs" % v.total)
