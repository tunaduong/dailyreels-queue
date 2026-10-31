"""Khởi động bot:  python3 run.py
Bot nhận kịch bản từ kho GitHub, dựng video, gửi Telegram duyệt, đăng TikTok (nháp) + Facebook Reels."""
import os, sys, logging, yaml
ROOT = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, ROOT)

def load_env(path):
    env = dict(os.environ)
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1); v = v.split(" #")[0]; env[k.strip()] = v.strip().strip('"').strip("'"); os.environ.setdefault(k.strip(), env[k.strip()])
    return env

if __name__ == "__main__":
    os.makedirs(os.path.join(ROOT, "data", "logs"), exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s",
                        handlers=[logging.StreamHandler(), logging.FileHandler(os.path.join(ROOT, "data", "logs", "bot.log"), encoding="utf-8")])
    env = load_env(os.path.join(ROOT, ".env"))
    from app.bot import Bot
    cfg = yaml.safe_load(open(os.path.join(ROOT, "config.yaml"), encoding="utf-8"))
    missing = [k for k in ("TELEGRAM_BOT_TOKEN", "GITHUB_TOKEN") if not env.get(k)]
    if not env.get("FAKE_VOICE") == "1" and not env.get("ELEVENLABS_API_KEY"): missing.append("ELEVENLABS_API_KEY")
    if missing: sys.exit("Thiếu khóa trong .env: " + ", ".join(missing) + "  →  chạy lại setup.sh")
    Bot(cfg, ROOT, env, offline="--offline" in sys.argv).loop()
