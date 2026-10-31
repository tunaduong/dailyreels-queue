"""Giọng đọc ElevenLabs: mỗi beat một đoạn (dùng previous_text/next_text để giọng liền mạch)."""
import os, re, subprocess, logging, requests

log = logging.getLogger("tts")
BASE = os.environ.get("ELEVENLABS_BASE", "https://api.elevenlabs.io")

def synth_beats(texts, voice, workdir, api_key, fake=False):
    """texts: [str]; voice: dict(voice_id, model_id, stability, similarity_boost, style, speed, language_code)
    -> [mp3 path]"""
    os.makedirs(workdir, exist_ok=True); out = []
    for i, txt in enumerate(texts):
        path = os.path.join(workdir, f"beat_{i:02d}.mp3")
        if fake: _fake(txt, path)
        else: _synth_one(txt, voice, path, api_key, texts[i - 1] if i > 0 else None, texts[i + 1] if i < len(texts) - 1 else None)
        out.append(path)
    return out

def _fake(txt, path):
    """giọng giả (im lặng) để chạy thử không tốn credit: ~4.3 âm tiết/giây"""
    syl = len(re.findall(r"\w+", txt)); dur = max(1.5, syl / 4.3)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"sine=frequency=220:duration={dur:.2f}", "-af", "volume=0.02",
                    "-ar", "44100", "-ac", "1", "-b:a", "128k", path], check=True)

VI_MODELS = ("eleven_v4", "eleven_flash_v2_5")   # model hỗ trợ tiếng Việt (multilingual_v2 KHÔNG hỗ trợ)

def pick_model(m):
    return "eleven_v4" if (not m or m in ("eleven_multilingual_v2", "eleven_multilingual_v1", "eleven_monolingual_v1")) else m

def _synth_one(txt, voice, path, api_key, prev=None, nxt=None):
    """thử lần lượt các biến thể tham số: model mới có thể chưa nhận vài tham số -> bỏ dần cho tới khi thành công"""
    model = pick_model(voice.get("model_id")); vs = {"stability": voice.get("stability", 0.5), "similarity_boost": voice.get("similarity_boost", 0.9),
                                                    "style": voice.get("style", 0.0), "use_speaker_boost": True, "speed": voice.get("speed", 1.0)}
    variants = [
        dict(model_id=model, voice_settings=vs, language_code="vi", previous_text=prev, next_text=nxt),
        dict(model_id=model, voice_settings=vs, language_code="vi"),
        dict(model_id=model, voice_settings=vs),
        dict(model_id=model, voice_settings={"stability": 0.5, "similarity_boost": vs["similarity_boost"]}),
        dict(model_id=model),
        dict(model_id="eleven_flash_v2_5", voice_settings=vs, language_code="vi"),
    ]
    last = ""
    for v in variants:
        body = {"text": txt, **{k: x for k, x in v.items() if x is not None}}
        for attempt in range(3):
            r = requests.post(f"{BASE}/v1/text-to-speech/{voice['voice_id']}", params={"output_format": "mp3_44100_128"}, timeout=180,
                              headers={"xi-api-key": api_key, "Content-Type": "application/json", "Accept": "audio/mpeg"}, json=body)
            if r.status_code == 200: open(path, "wb").write(r.content); return body["model_id"]
            last = f"{r.status_code}: {r.text[:300]}"
            if r.status_code in (401, 403): raise RuntimeError(f"ElevenLabs từ chối khóa ({last})")
            if r.status_code in (400, 422): break          # tham số không hợp lệ -> thử biến thể kế
            import time; time.sleep(3 * (attempt + 1))     # 429/5xx -> thử lại
        log.warning("ElevenLabs biến thể %s lỗi %s", list(v.keys()), last)
    raise RuntimeError(f"ElevenLabs lỗi {last}")
