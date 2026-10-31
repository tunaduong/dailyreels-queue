"""Client Telegram Bot API tối giản (long polling, nút bấm inline, gửi video)."""
import os, json, logging, requests

log = logging.getLogger("telegram")
BASE = os.environ.get("TELEGRAM_BASE", "https://api.telegram.org")

class TG:
    def __init__(self, token): self.url = f"{BASE}/bot{token}"

    def call(self, method, files=None, timeout=60, **params):
        for k, v in list(params.items()):
            if isinstance(v, (dict, list)): params[k] = json.dumps(v, ensure_ascii=False)
        r = requests.post(f"{self.url}/{method}", data=params, files=files, timeout=timeout)
        js = r.json()
        if not js.get("ok"): log.warning("Telegram %s lỗi: %s", method, js); raise RuntimeError(js.get("description", "telegram error"))
        return js["result"]

    @staticmethod
    def kb(rows): return {"inline_keyboard": [[{"text": t, "callback_data": d} for t, d in row] for row in rows]}

    def send(self, chat, text, buttons=None):
        out = None
        for i in range(0, len(text), 3900):    # giới hạn 4096 ký tự/tin
            part = text[i:i + 3900]; last = i + 3900 >= len(text)
            p = {"chat_id": chat, "text": part, "parse_mode": "HTML", "disable_web_page_preview": True}
            if buttons and last: p["reply_markup"] = self.kb(buttons)
            out = self.call("sendMessage", **p)
        return out

    def video(self, chat, path, caption="", buttons=None, thumb=None):
        p = {"chat_id": chat, "caption": caption[:1000], "parse_mode": "HTML", "supports_streaming": True, "width": 1080, "height": 1920}
        if buttons: p["reply_markup"] = self.kb(buttons)
        files = {"video": open(path, "rb")}
        if thumb: files["thumbnail"] = open(thumb, "rb")
        return self.call("sendVideo", files=files, timeout=600, **p)

    def audio(self, chat, path, caption="", buttons=None):
        p = {"chat_id": chat, "caption": caption[:1000], "parse_mode": "HTML"}
        if buttons: p["reply_markup"] = self.kb(buttons)
        return self.call("sendAudio", files={"audio": open(path, "rb")}, timeout=300, **p)

    def answer(self, cb_id, text=""):
        try: self.call("answerCallbackQuery", callback_query_id=cb_id, text=text[:190])
        except Exception: pass

    def clear_buttons(self, chat, msg_id):
        try: self.call("editMessageReplyMarkup", chat_id=chat, message_id=msg_id, reply_markup={"inline_keyboard": []})
        except Exception: pass

    def updates(self, offset, timeout=25):
        try:
            r = requests.get(f"{self.url}/getUpdates", timeout=timeout + 10,
                             params={"offset": offset, "timeout": timeout, "allowed_updates": json.dumps(["message", "callback_query"])})
            return r.json().get("result", [])
        except Exception as e:
            log.warning("getUpdates lỗi: %s", e); return []
