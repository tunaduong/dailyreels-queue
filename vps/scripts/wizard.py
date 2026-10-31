"""Trình thiết lập hỏi-đáp: kiểm tra từng khóa ngay khi nhập, tự lấy Chat ID, chọn giọng theo số thứ tự.
Chạy lại để đổi khóa:  sudo /opt/dailyreels/.venv/bin/python /opt/dailyreels/scripts/wizard.py"""
import os, sys, re, time, getpass, requests
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TG = os.environ.get("TELEGRAM_BASE", "https://api.telegram.org")
EL = os.environ.get("ELEVENLABS_BASE", "https://api.elevenlabs.io")
ENV, CFG = os.path.join(ROOT, ".env"), os.path.join(ROOT, "config.yaml")

def read_env():
    d = {}
    if os.path.exists(ENV):
        for line in open(ENV, encoding="utf-8"):
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1); d[k.strip()] = v.split(" #")[0].strip()
    return d

def write_env(d):
    tpl = open(os.path.join(ROOT, ".env.example"), encoding="utf-8").read().splitlines(); out = []; seen = set()
    for line in tpl:
        m = re.match(r"^([A-Z_]+)=", line)
        if m: k = m.group(1); seen.add(k); out.append(f"{k}={d.get(k, '')}")
        else: out.append(line)
    out += [f"{k}={v}" for k, v in d.items() if k not in seen]
    open(ENV, "w", encoding="utf-8").write("\n".join(out) + "\n"); os.chmod(ENV, 0o600)

def ask(prompt, cur="", secret=False):
    hint = f" [Enter = giữ {'••••' + cur[-4:] if secret else cur}]" if cur else ""
    while True:
        v = (getpass.getpass if secret and sys.stdin.isatty() else input)(f"{prompt}{hint}: ").strip()
        if v or cur: return v or cur

def hr(t): print("\n" + "─" * 60 + f"\n {t}\n" + "─" * 60)

def main():
    env = read_env(); cfg_txt = open(CFG, encoding="utf-8").read()
    print("\n🎬  THIẾT LẬP BOT VIDEO CRYPTO — nhập từng mục, bot kiểm tra ngay.\n")

    # 1. Telegram ----------------------------------------------------------
    hr("1/3  BOT TELEGRAM  (nhắn @BotFather → /newbot → copy token)")
    while True:
        tok = ask("Token bot", env.get("TELEGRAM_BOT_TOKEN", ""), secret=True)
        try: me = requests.get(f"{TG}/bot{tok}/getMe", timeout=15).json()
        except Exception as e: me = {"description": str(e)}
        if me.get("ok"): env["TELEGRAM_BOT_TOKEN"] = tok; break
        print("   ❌ Token không đúng:", me.get("description")); env.pop("TELEGRAM_BOT_TOKEN", None)
    bot = me["result"]["username"]; print(f"   ✅ Bot: @{bot}")
    if env.get("ALLOWED_CHAT_IDS") and input(f"   Giữ Chat ID hiện tại ({env['ALLOWED_CHAT_IDS']})? [Y/n]: ").strip().lower() != "n": pass
    else:
        requests.get(f"{TG}/bot{tok}/deleteWebhook", timeout=15)
        off = 0
        for u in requests.get(f"{TG}/bot{tok}/getUpdates", params={"timeout": 0}, timeout=15).json().get("result", []): off = u["update_id"] + 1
        print(f"\n   👉 Mở Telegram, vào https://t.me/{bot} và gửi /start  (đang chờ tối đa 5 phút…)")
        chat = None; t0 = time.time()
        while not chat and time.time() - t0 < 300:
            for u in requests.get(f"{TG}/bot{tok}/getUpdates", params={"offset": off, "timeout": 20}, timeout=30).json().get("result", []):
                off = u["update_id"] + 1; m = u.get("message") or {}
                if m.get("chat"): chat = m["chat"]; break
        if not chat: sys.exit("   ❌ Không nhận được /start. Chạy lại setup.")
        requests.get(f"{TG}/bot{tok}/getUpdates", params={"offset": off, "timeout": 0}, timeout=15)
        env["ALLOWED_CHAT_IDS"] = str(chat["id"])
        name = chat.get("first_name") or chat.get("title") or ""
        requests.post(f"{TG}/bot{tok}/sendMessage", data={"chat_id": chat["id"], "text": "✅ Đã kết nối! Bot sẽ chỉ nhận lệnh từ bạn."}, timeout=15)
        print(f"   ✅ Đã nhận Chat ID {chat['id']} ({name})")

    # 2. GitHub ------------------------------------------------------------
    hr("2/3  KHO GITHUB  (nơi Claude gửi kịch bản sang)")
    print("   Token: github.com → Settings → Developer settings → Fine-grained tokens → Generate,")
    print("   chọn đúng kho, quyền Contents = Read and write.")
    sys.path.insert(0, ROOT); from app.queue import Repo
    while True:
        repo = ask("Tên kho (dạng taikhoan/dailyreels-queue)", env.get("GITHUB_REPO", ""))
        k = ask("GitHub token", env.get("GITHUB_TOKEN", ""), secret=True)
        ok, info = Repo(k, repo).check()
        if ok: env["GITHUB_TOKEN"], env["GITHUB_REPO"] = k, repo; print(f"   ✅ Kết nối kho {repo} ({info})"); break
        print(f"   ❌ Không ghi được vào kho: {info}"); env.pop("GITHUB_TOKEN", None)
    cfg_txt = re.sub(r'repo: "[^"]*"', f'repo: "{repo}"', cfg_txt, count=1)

    # 3. ElevenLabs ---------------------------------------------------------
    hr("3/3  ELEVENLABS  (elevenlabs.io → Profile → API Keys)")
    while True:
        k = ask("ElevenLabs API key", env.get("ELEVENLABS_API_KEY", ""), secret=True)
        r = requests.get(f"{EL}/v1/voices", headers={"xi-api-key": k}, timeout=30)
        if r.status_code == 200: env["ELEVENLABS_API_KEY"] = k; break
        print(f"   ❌ Lỗi {r.status_code}: {r.text[:200]}"); env.pop("ELEVENLABS_API_KEY", None)
    voices = r.json().get("voices", []); print(f"   ✅ ElevenLabs OK — {len(voices)} giọng trong tài khoản:")
    for i, v in enumerate(voices, 1): print(f"     {i:>2}. {v['name']}  ({v.get('category', '')})")
    for key, label in (("CHAINFOLK", "ChainFolk"), ("TNDGEMS", "TND GEMS")):
        while True:
            s = input(f"   Chọn số giọng cho {label}: ").strip()
            if s.isdigit() and 1 <= int(s) <= len(voices):
                vid = voices[int(s) - 1]["voice_id"]
                cfg_txt = cfg_txt.replace(f'"ĐIỀN_VOICE_ID_{key}"', f'"{vid}"', 1) if f"ĐIỀN_VOICE_ID_{key}" in cfg_txt else _set_voice(cfg_txt, label, vid)
                print(f"     → {voices[int(s) - 1]['name']}"); break
    env["FAKE_VOICE"] = "0"

    write_env(env); open(CFG, "w", encoding="utf-8").write(cfg_txt)
    print("\n✅ Đã lưu cấu hình.\n")

def _set_voice(txt, label, vid):
    """đổi voice_id của kênh đã có giá trị (chạy wizard lần 2)"""
    blk = txt.find(f'display_name: "{label}"'); i = txt.find("voice_id:", blk)
    j = txt.find("\n", i); return txt[:i] + f'voice_id: "{vid}"' + txt[j:]

if __name__ == "__main__":
    try: main()
    except KeyboardInterrupt: sys.exit("\nĐã hủy.")
