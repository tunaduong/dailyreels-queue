"""Bot VPS: nhận kịch bản từ Claude (qua GitHub) -> giọng + dựng -> gửi Telegram duyệt -> đăng TikTok (nháp) + Facebook Reels."""
import os, re, json, time, logging, threading, datetime, traceback, html, zoneinfo
from concurrent.futures import ThreadPoolExecutor
from .telegram import TG
from . import tts, captions
from .research import validate
from .queue import Repo
from .logos import Logos
from .render.engine import Video
from .publish import youtube, tiktok, meta

log = logging.getLogger("bot")
E = html.escape

class State:
    def __init__(self, path):
        self.path = path; self.lock = threading.RLock()
        self.d = json.load(open(path, encoding="utf-8")) if os.path.exists(path) else {}
        for k, v in {"offset": 0, "jobs": {}, "seen": [], "awaiting": {}}.items(): self.d.setdefault(k, v)
    def save(self):
        with self.lock:
            tmp = self.path + ".tmp"; json.dump(self.d, open(tmp, "w", encoding="utf-8"), ensure_ascii=False, indent=1); os.replace(tmp, self.path)

class Bot:
    def __init__(self, cfg, root, env, offline=False):
        self.cfg, self.root, self.env, self.offline = cfg, root, env, offline
        self.tg = TG(env["TELEGRAM_BOT_TOKEN"])
        self.allowed = {int(x) for x in re.split(r"[,\s]+", env.get("ALLOWED_CHAT_IDS", "")) if x.strip().lstrip("-").isdigit()}
        g = cfg.get("github", {}); self.repo = Repo(env["GITHUB_TOKEN"], env.get("GITHUB_REPO") or g["repo"], g.get("branch", "main"))
        self.poll = int(g.get("poll_seconds", 60))
        os.makedirs(os.path.join(root, "data", "jobs"), exist_ok=True)
        self.st = State(os.path.join(root, "data", "state.json"))
        self.pool = ThreadPoolExecutor(max_workers=1)
        self.fake_voice = env.get("FAKE_VOICE", "0") == "1"
        self.tz = zoneinfo.ZoneInfo(cfg.get("timezone", "Asia/Ho_Chi_Minh"))
        self.st.d.setdefault("settings", {}).setdefault("model", {})
        self.logos = Logos(root, env.get("COINGECKO_KEY"))

    def chname(self, ch): return self.cfg["channels"][ch]["display_name"]
    def jobdir(self, jid): p = os.path.join(self.root, "data", "jobs", jid); os.makedirs(p, exist_ok=True); return p
    def owner(self): return next(iter(self.allowed), None)

    def run_bg(self, chat, label, fn, *a):
        def wrap():
            try: fn(*a)
            except Exception as e:
                log.error("%s lỗi: %s\n%s", label, e, traceback.format_exc())
                if chat: self.tg.send(chat, f"⚠️ <b>{E(label)} lỗi</b>\n<code>{E(str(e))[:900]}</code>")
        self.pool.submit(wrap)

    # ------------------------------------------------------------ nhận kịch bản từ GitHub
    def watch_inbox(self):
        while True:
            try:
                for f in sorted(self.repo.list("inbox"), key=lambda x: x["name"]):
                    if not f["name"].endswith(".json") or f["name"] in self.st.d["seen"]: continue
                    with self.st.lock: self.st.d["seen"].append(f["name"]); self.st.d["seen"] = self.st.d["seen"][-500:]; self.st.save()
                    self.run_bg(self.owner(), f"Kịch bản {f['name']}", self.ingest, f["name"], self.repo.get(f["path"]))
            except Exception as e: log.warning("đọc inbox lỗi: %s", e)
            time.sleep(self.poll)

    def ingest(self, name, raw):
        s = json.loads(raw); ch = s.get("channel")
        if ch not in self.cfg["channels"]: raise ValueError(f"kênh không hợp lệ: {ch}")
        s = validate(s, ch); jid = name[:-5]
        with self.st.lock: self.st.d["jobs"][jid] = {"ch": ch, "stage": "producing", "script": s, "created": time.time(), "note": s.get("note", "")}; self.st.save()
        json.dump(s, open(os.path.join(self.jobdir(jid), "script.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        head = " ".join(x[0] for x in s["headline"])
        self.tg.send(self.owner(), f"📥 Kịch bản mới từ Claude — <b>{E(self.chname(ch))}</b>\n{E(head)}\n🎙️ Đang tạo giọng đọc…")
        self.safe_produce(jid)

    def safe_produce(self, jid):
        try: self.produce(jid)
        except Exception as e:
            log.error("dựng %s lỗi: %s\n%s", jid, e, traceback.format_exc())
            with self.st.lock: self.st.d["jobs"][jid]["stage"] = "lỗi dựng"; self.st.save()
            self.tg.send(self.owner(), f"⚠️ <b>Dựng video lỗi</b> <code>{E(jid)}</code>\n<code>{E(str(e))[:900]}</code>", [[("🔁 Làm lại", f"rr|{jid}")]])

    # ------------------------------------------------------------ giọng + dựng
    def produce(self, jid):
        job = self.st.d["jobs"][jid]; s = job["script"]; ch = job["ch"]; c = self.cfg["channels"][ch]; work = self.jobdir(jid); chat = self.owner()
        voice = self.voice_for(ch)
        texts = [b["voice"] for b in s["beats"]] + [c["cta_voice"]]
        audio = tts.synth_beats(texts, voice, os.path.join(work, "voice"), self.env.get("ELEVENLABS_API_KEY"), fake=self.fake_voice)
        self.tg.send(chat, f"🎞️ {E(self.chname(ch))}: đã có giọng, đang dựng video (5–8 phút)…")
        mk = dict(self.cfg.get("market", {})); mk["coingecko_key"] = self.env.get("COINGECKO_KEY")
        v = Video(s, c, audio, work, mk, offline=self.offline, logos=self.logos)
        out = os.path.join(work, f"{jid}.mp4"); prev = os.path.join(work, "preview.png"); v.render(out, prev)
        caps = captions.build(s, c)
        with self.st.lock: job.update(stage="review", video=out, captions=caps); self.st.save()
        plats = self.platforms(ch)
        cap = (f"🎬 <b>{E(self.chname(ch))}</b> · {v.total:.0f}s\n\n<b>Caption:</b>\n{E(caps['tiktok']['title'][:700])}\n\n"
               f"<b>Lời đọc:</b>\n" + E(" ".join(b["voice"] for b in s["beats"]))[:400] + "…")
        first = [("✅ Đăng: " + " + ".join(PNAME[p] for p in plats), f"pub|{jid}")] if plats else [("✅ Xong — tôi tự đăng", f"done|{jid}")]
        self.tg.video(chat, out, cap, [first, [("✏️ Sửa", f"ed|{jid}"), ("❌ Bỏ", f"dr|{jid}")]])
        if not plats:
            self.tg.send(chat, f"📋 <b>Caption để copy:</b>\n<code>{E(caps['tiktok']['title'])}</code>\n<i>Nhớ bật nhãn “Nội dung AI” khi đăng.</i>")

    def voice_for(self, ch):
        v = dict(self.cfg["channels"][ch]["voice"])
        v["model_id"] = self.st.d["settings"]["model"].get(ch) or v.get("model_id") or self.cfg.get("elevenlabs", {}).get("model_id")
        return v

    def voice_test(self, chat):
        line = "Xin chào, đây là bản tin crypto. Bitcoin vừa giảm về quanh mức bảy mươi bảy nghìn đô, trong khi chỉ số sợ hãi và tham lam rơi xuống ba mươi."
        self.tg.send(chat, "🎧 Đang tạo giọng mẫu với 2 model hỗ trợ tiếng Việt cho từng kênh…")
        for ch in self.cfg["channels"]:
            for m in tts.VI_MODELS:
                v = self.voice_for(ch); v["model_id"] = m; p = os.path.join(self.root, "data", f"voice_test_{ch}_{m}.mp3")
                used = tts._synth_one(line, v, p, self.env.get("ELEVENLABS_API_KEY"))
                cur = " ✅ (đang dùng)" if tts.pick_model(self.voice_for(ch)["model_id"]) == m else ""
                self.tg.audio(chat, p, f"<b>{E(self.chname(ch))}</b> · model <code>{used}</code>{cur}", [[(f"Dùng model này cho {self.chname(ch)}", f"gm|{ch}|{m}")]])

    def platforms(self, ch): return [p for p, pc in self.cfg["channels"][ch]["platforms"].items() if pc.get("enabled")]

    # ------------------------------------------------------------ đăng
    def publish(self, jid, only=None):
        job = self.st.d["jobs"][jid]; ch = job["ch"]; c = self.cfg["channels"][ch]; caps = job["captions"]; video = job["video"]
        ai = self.cfg.get("publish", {}).get("label_ai_content", True); ver = self.cfg.get("publish", {}).get("graph_api_version", "v26.0")
        res = dict(job.get("results", {}))
        for p in self.platforms(ch):
            if only and p not in only: continue
            pc = dict(c["platforms"][p])
            if "token_file" in pc and not os.path.isabs(pc["token_file"]): pc["token_file"] = os.path.join(self.root, pc["token_file"])
            try:
                if p == "tiktok": res[p] = tiktok.upload(video, caps["tiktok"], pc, ai)
                elif p == "facebook": res[p] = meta.facebook(video, caps["facebook"], pc, ver, ai)
                elif p == "instagram": res[p] = meta.instagram(video, caps["instagram"], pc, ver, ai)
                elif p == "youtube": res[p] = youtube.upload(video, caps["youtube"], pc, ai)
            except Exception as e:
                log.error("đăng %s lỗi: %s", p, e); res[p] = "❌ " + str(e)[:300]
        failed = [p for p, r in res.items() if str(r).startswith("❌")]
        with self.st.lock: job.update(stage="done" if not failed else "lỗi đăng", results=res); self.st.save()
        self.tg.send(self.owner(), f"📤 <b>{E(self.chname(ch))}</b>\n" + "\n".join(f"• <b>{PNAME.get(p, p)}</b>: {E(str(r))}" for p, r in res.items())
                     + ("" if failed else "\n\n✅ Xong việc!"), [[("🔁 Thử lại", f"rp|{jid}")]] if failed else None)

    # ------------------------------------------------------------ gửi yêu cầu cho Claude
    def request(self, kind, payload):
        ts = datetime.datetime.now(self.tz).strftime("%Y%m%d-%H%M%S")
        self.repo.put(f"requests/{ts}-{kind}.json", json.dumps({"type": kind, "created": ts, **payload}, ensure_ascii=False, indent=1), f"yêu cầu {kind} {ts}")

    # ------------------------------------------------------------ Telegram
    def on_callback(self, cb):
        chat = cb["message"]["chat"]["id"]; self.tg.answer(cb["id"], "Đã nhận")
        if chat not in self.allowed: return
        parts = cb.get("data", "").split("|"); kind, jid = (parts + [""])[:2]
        if kind == "gm":
            with self.st.lock: self.st.d["settings"]["model"][parts[1]] = parts[2]; self.st.save()
            self.tg.send(chat, f"✅ {E(self.chname(parts[1]))} sẽ dùng model <code>{E(parts[2])}</code> từ video kế tiếp."); return
        job = self.st.d["jobs"].get(jid)
        if not job: return
        self.tg.clear_buttons(chat, cb["message"]["message_id"])
        if kind == "rr":
            with self.st.lock: job["stage"] = "producing"; self.st.save()
            self.tg.send(chat, "🔁 Đang làm lại video…"); self.pool.submit(self.safe_produce, jid); return
        if kind == "pub": self.tg.send(chat, "🚀 Đang đăng…"); self.run_bg(chat, "Đăng bài", self.publish, jid)
        elif kind == "rp": self.run_bg(chat, "Đăng lại", self.publish, jid, [p for p, r in job.get("results", {}).items() if str(r).startswith("❌")])
        elif kind == "done":
            with self.st.lock: job["stage"] = "done (đăng tay)"; self.st.save()
            self.tg.send(chat, "👍 Xong việc!")
        elif kind == "dr":
            with self.st.lock: job["stage"] = "bỏ"; self.st.save()
            self.tg.send(chat, "Đã bỏ video này.")
        elif kind == "ed":
            with self.st.lock: self.st.d["awaiting"][str(chat)] = jid; self.st.save()
            self.tg.send(chat, "✏️ Gõ yêu cầu sửa (vd: “mở đầu bằng con số 2,3 tỷ, bỏ đoạn biểu đồ”):")

    def on_message(self, m):
        chat = m["chat"]["id"]; text = (m.get("text") or m.get("caption") or "").strip()
        if chat not in self.allowed:
            self.tg.send(chat, f"Chat ID của bạn: <code>{chat}</code>"); return
        if text.startswith(("/start", "/help")) or not text: self.tg.send(chat, HELP); return
        if text.startswith("/trangthai"): self.tg.send(chat, self.status_text()); return
        if text.startswith("/giong"): self.run_bg(chat, "Thử giọng", self.voice_test, chat); return
        if text.startswith("/lich"):
            body = text[5:].strip()
            if not body: self.tg.send(chat, LICH_HELP); return
            wk = datetime.datetime.now(self.tz).strftime("%G-W%V")
            self.repo.put(f"plan/{wk}-{datetime.datetime.now(self.tz):%H%M%S}.md", body, f"lịch tuần {wk}")
            self.tg.send(chat, f"🗓️ Đã lưu lịch tuần {wk}. Mỗi sáng Claude sẽ làm theo lịch này (ngày nào không có trong lịch thì Claude tự chọn tin)."); return
        jid = self.st.d["awaiting"].pop(str(chat), None); self.st.save()
        if jid and jid in self.st.d["jobs"]:
            job = self.st.d["jobs"][jid]
            self.request("feedback", {"job": jid, "channel": job["ch"], "note": text, "script": job["script"]})
            with self.st.lock: job["stage"] = "chờ Claude sửa"; self.st.save()
            self.tg.send(chat, f"📨 Đã gửi yêu cầu sửa cho Claude. {WAIT}"); return
        self.request("topic", {"text": text, "links": re.findall(r"https?://\S+", text)})
        self.tg.send(chat, f"📨 Đã gửi yêu cầu làm video cho Claude:\n<i>{E(text[:300])}</i>\n{WAIT}")

    def status_text(self):
        rows = ["📋 <b>Video gần đây</b>"]
        for jid, j in sorted(self.st.d["jobs"].items(), key=lambda x: -x[1]["created"])[:10]:
            rows.append(f"• {E(self.chname(j['ch']))} <code>{jid}</code>: {E(j.get('stage', ''))}")
        return "\n".join(rows)

    def resume(self):
        for jid, j in list(self.st.d["jobs"].items()):
            if j.get("stage") == "producing":
                self.tg.send(self.owner(), f"♻️ Bot vừa khởi động lại — làm tiếp video dở <code>{E(jid)}</code>…"); self.pool.submit(self.safe_produce, jid)

    def loop(self, once=False):
        if not once:
            try: self.resume()
            except Exception as e: log.warning("resume lỗi: %s", e)
            threading.Thread(target=self.watch_inbox, daemon=True).start()
        log.info("Bot đang chạy. Kho: %s. Chat: %s", self.repo.repo, self.allowed)
        while True:
            for u in self.tg.updates(self.st.d.get("offset", 0)):
                self.st.d["offset"] = u["update_id"] + 1; self.st.save()
                try:
                    if "callback_query" in u: self.on_callback(u["callback_query"])
                    elif "message" in u: self.on_message(u["message"])
                except Exception as e: log.error("xử lý update lỗi: %s\n%s", e, traceback.format_exc())
            if once: break

PNAME = {"tiktok": "TikTok (nháp)", "facebook": "Facebook Reels", "instagram": "Instagram Reels", "youtube": "YouTube Shorts"}
WAIT = "Claude sẽ xử lý ở lượt kiểm tra kế tiếp (mỗi giờ, 8:00–22:00). Muốn nhanh hơn: nhắn thẳng cho Claude trong app."
HELP = """🤖 <b>Bot video crypto</b>
• 8:00 mỗi sáng Claude chọn tin (hoặc theo lịch tuần bạn gửi) → bot gửi video về đây.
• /lich — gửi danh sách tin cả tuần.
• Gửi nội dung/link bất kỳ → chuyển cho Claude làm video.
• Mỗi video có nút: ✅ Đăng (TikTok nháp + Facebook Reels) · ✏️ Sửa · ❌ Bỏ
• /giong — nghe thử giọng & chọn model đọc tiếng Việt.
• /trangthai — xem tiến độ."""
LICH_HELP = """🗓️ Gửi lịch tuần theo mẫu (mỗi dòng 1 ngày, có thể kèm link):
/lich
T2: Bitcoin ETF dòng tiền tuần qua
T3: Vụ hack Binance — cập nhật bồi thường
T4: https://link-bai-bao
T5: Solana nâng cấp mạng
T6: Tổng kết tuần
Ngày nào để trống thì Claude tự chọn tin nóng."""
