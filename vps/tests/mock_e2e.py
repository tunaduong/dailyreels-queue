"""Kiểm thử trọn luồng (kho GitHub -> dựng -> Telegram -> đăng) với máy chủ giả lập.  python3 tests/mock_e2e.py"""
import os, sys, json, time, threading, re, shutil, base64, http.server, socketserver, urllib.parse
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, ROOT)
PORT = 8899; B = f"http://127.0.0.1:{PORT}"
for k, v in {"TELEGRAM_BASE": B, "GITHUB_API": B, "TIKTOK_BASE": B, "GRAPH_BASE": B, "RUPLOAD_BASE": B, "NO_PROXY": "127.0.0.1"}.items(): os.environ[k] = v
for k in ("HTTPS_PROXY", "HTTP_PROXY", "https_proxy", "http_proxy"): os.environ.pop(k, None)

REPO = {}   # path -> text
for c in ("chainfolk", "tndgems"):
    s = json.load(open(os.path.join(ROOT, "samples", f"{c}_binance.json"), encoding="utf-8")); s["beats"] = s["beats"][:3]
    REPO[f"inbox/20261031-0730-{c}.json"] = json.dumps(s, ensure_ascii=False)
UPD, SENT = [], []; mid = {"n": 100}

class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _b(self): n = int(self.headers.get("Content-Length") or 0); return self.rfile.read(n) if n else b""
    def j(self, o, c=200):
        b = json.dumps(o).encode(); self.send_response(c); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        p = urllib.parse.urlparse(self.path); path = p.path
        if path.endswith("/getUpdates"): out = list(UPD); UPD.clear(); return self.j({"ok": True, "result": out})
        m = re.match(r"/repos/o/q(/contents/(.*))?$", path)
        if m:
            if not m.group(1): return self.j({"private": True, "permissions": {"push": True}})
            fp = m.group(2)
            if fp in REPO: return self.j({"content": base64.b64encode(REPO[fp].encode()).decode()})
            items = [{"name": k.split("/")[-1], "path": k, "type": "file"} for k in REPO if k.rsplit("/", 1)[0] == fp]
            return self.j(items) if items else self.j({"message": "Not Found"}, 404)
        if "/fbvid" in path: return self.j({"status": {"video_status": "ready"}})
        return self.j({}, 404)
    def do_PUT(self):
        raw = self._b(); m = re.match(r"/repos/o/q/contents/(.*)$", self.path)
        if m: REPO[m.group(1)] = base64.b64decode(json.loads(raw)["content"]).decode(); return self.j({"content": {}}, 201)
        return self.j({}, 201)
    def do_POST(self):
        p = urllib.parse.urlparse(self.path); raw = self._b()
        if "/bot" in p.path:
            meth = p.path.rsplit("/", 1)[-1]; data = {} if "multipart" in self.headers.get("Content-Type", "") else dict(urllib.parse.parse_qsl(raw.decode()))
            SENT.append((meth, data)); mid["n"] += 1; return self.j({"ok": True, "result": {"message_id": mid["n"]} if meth.startswith("send") else True})
        if p.path == "/v2/post/publish/inbox/video/init/": return self.j({"data": {"publish_id": "p1", "upload_url": B + "/ttput"}, "error": {"code": "ok"}})
        if p.path == "/v2/post/publish/status/fetch/": return self.j({"data": {"status": "SEND_TO_USER_INBOX"}, "error": {"code": "ok"}})
        if p.path == "/v2/oauth/token/": return self.j({"access_token": "a", "refresh_token": "r", "expires_in": 86400})
        if p.path.endswith("/video_reels"):
            try: body = json.loads(raw)
            except Exception: body = {}
            return self.j({"video_id": "fbvid", "upload_url": "x"} if body.get("upload_phase") == "start" else {"success": True})
        if p.path.startswith("/video-upload/"): return self.j({"success": True})
        return self.j({"error": p.path}, 404)

class TS(socketserver.ThreadingMixIn, http.server.HTTPServer): daemon_threads = True

def main():
    threading.Thread(target=TS(("127.0.0.1", PORT), H).serve_forever, daemon=True).start()
    import yaml, logging; logging.basicConfig(level=logging.WARNING)
    from app.bot import Bot
    root = os.path.join(ROOT, "data", "e2e"); shutil.rmtree(root, ignore_errors=True); os.makedirs(os.path.join(root, "data", "tokens"))
    cfg = yaml.safe_load(open(os.path.join(ROOT, "config.yaml"), encoding="utf-8"))
    for c, ch in cfg["channels"].items():
        ch["platforms"]["tiktok"]["enabled"] = True; ch["platforms"]["facebook"].update(enabled=True, page_id="PAGE1")
        json.dump({"client_key": "k", "client_secret": "s", "access_token": "a", "refresh_token": "r", "expires_at": 0}, open(os.path.join(root, f"data/tokens/tiktok_{c}.json"), "w"))
    os.environ["FB_PAGE_TOKEN_CHAINFOLK"] = os.environ["FB_PAGE_TOKEN_TNDGEMS"] = "f"
    cfg["github"]["poll_seconds"] = 1
    bot = Bot(cfg, root, {"TELEGRAM_BOT_TOKEN": "T", "ALLOWED_CHAT_IDS": "42", "GITHUB_TOKEN": "g", "GITHUB_REPO": "o/q", "FAKE_VOICE": "1"}, offline=True)
    threading.Thread(target=bot.watch_inbox, daemon=True).start()
    def msg(t, chat=42): UPD.append({"update_id": 1000 + len(SENT) + len(UPD), "message": {"chat": {"id": chat}, "text": t}})
    def cb(d): UPD.append({"update_id": 5000 + len(SENT) + len(UPD), "callback_query": {"id": "c", "data": d, "message": {"chat": {"id": 42}, "message_id": 1}}})
    def wait(cond, to=900):
        t0 = time.time()
        while not cond() and time.time() - t0 < to: bot.loop(once=True) if UPD else time.sleep(.5)
        assert cond(), "quá thời gian chờ"
    J = lambda: bot.st.d["jobs"]
    wait(lambda: len(J()) == 2 and all(j.get("stage") == "review" for j in J().values()))
    assert sum(m == "sendVideo" for m, _ in SENT) == 2; print("✓ nhận 2 kịch bản từ GitHub, dựng 2 video, gửi Telegram")
    msg("/start", 7); bot.loop(once=True); assert "Chat ID" in SENT[-1][1].get("text", ""); print("✓ chặn chat lạ")
    jc, jt = sorted(J())
    cb(f"pub|{jc}"); wait(lambda: J()[jc].get("stage") == "done"); print("✓ đăng ChainFolk:", J()[jc]["results"])
    cb(f"ed|{jt}"); bot.loop(once=True); msg("Mở đầu bằng con số 2,3 tỷ"); wait(lambda: any(k.endswith("feedback.json") for k in REPO))
    fb = json.loads(next(v for k, v in REPO.items() if k.endswith("feedback.json"))); assert fb["channel"] == "tndgems" and fb["script"]["beats"]; print("✓ góp ý sửa ghi vào requests/:", fb["note"])
    msg("Làm video về ETF Solana https://example.com/sol"); wait(lambda: any(k.endswith("topic.json") for k in REPO)); print("✓ yêu cầu tin mới ghi vào requests/")
    v2 = json.loads(REPO["inbox/20261031-0730-tndgems.json"]); v2["beats"] = v2["beats"][:3]; REPO["inbox/20261031-1015-tndgems-v2.json"] = json.dumps(v2, ensure_ascii=False)
    wait(lambda: len(J()) == 3 and J().get("20261031-1015-tndgems-v2", {}).get("stage") == "review"); print("✓ bản sửa v2 tự về Telegram")
    cb("done|20261031-1015-tndgems-v2"); bot.loop(once=True); msg("/trangthai"); bot.loop(once=True)
    print(re.sub(r"<[^>]+>", "", SENT[-1][1]["text"])); print("TẤT CẢ BƯỚC OK")

if __name__ == "__main__": main()
