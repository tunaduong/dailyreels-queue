"""Kiểm tra cấu hình trước khi chạy: python3 scripts/check_setup.py
Gọi thử từng API (không đăng bài) và báo cái nào đã sẵn sàng."""
import os, sys, json, yaml, shutil, requests
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, ROOT)
from run import load_env
env = load_env(os.path.join(ROOT, ".env")); cfg = yaml.safe_load(open(os.path.join(ROOT, "config.yaml"), encoding="utf-8"))
ok = lambda b, m: print(("✅ " if b else "❌ ") + m)
ok(shutil.which("ffmpeg") is not None, "ffmpeg đã cài")
try:
    r = requests.get(f"https://api.telegram.org/bot{env.get('TELEGRAM_BOT_TOKEN')}/getMe", timeout=15).json(); ok(r.get("ok"), f"Telegram bot: {r.get('result', {}).get('username', r)}")
except Exception as e: ok(False, f"Telegram: {e}")
ok(bool(env.get("ALLOWED_CHAT_IDS")), "ALLOWED_CHAT_IDS đã điền")
try:
    r = requests.post("https://api.anthropic.com/v1/messages", timeout=60, headers={"x-api-key": env.get("ANTHROPIC_API_KEY", ""), "anthropic-version": "2023-06-01", "content-type": "application/json"},
                      json={"model": cfg["claude"]["model"], "max_tokens": 10, "messages": [{"role": "user", "content": "ping"}]})
    ok(r.status_code == 200, f"Claude API ({cfg['claude']['model']}): {r.status_code} {'' if r.status_code == 200 else r.text[:150]}")
except Exception as e: ok(False, f"Claude: {e}")
try:
    r = requests.get("https://api.elevenlabs.io/v1/voices", headers={"xi-api-key": env.get("ELEVENLABS_API_KEY", "")}, timeout=20)
    ids = {v["voice_id"]: v["name"] for v in r.json().get("voices", [])} if r.status_code == 200 else {}
    ok(r.status_code == 200, f"ElevenLabs: {r.status_code}")
    for ch, c in cfg["channels"].items(): ok(c["voice"]["voice_id"] in ids, f"  giọng {ch}: {ids.get(c['voice']['voice_id'], c['voice']['voice_id'] + ' (không thấy trong tài khoản)')}")
except Exception as e: ok(False, f"ElevenLabs: {e}")
for ch, c in cfg["channels"].items():
    for p, pc in c["platforms"].items():
        if not pc.get("enabled"): continue
        if "token_file" in pc: ok(os.path.exists(os.path.join(ROOT, pc["token_file"])), f"{ch}/{p}: file token {pc['token_file']}")
        if "token_env" in pc: ok(bool(env.get(pc["token_env"])), f"{ch}/{p}: biến {pc['token_env']}")
        for k in ("ig_user_id", "page_id"):
            if k in pc: ok(not str(pc[k]).startswith("ĐIỀN"), f"{ch}/{p}: {k}")
