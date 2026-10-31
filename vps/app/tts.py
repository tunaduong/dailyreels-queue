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
        else:
            body = {"text": txt, "model_id": voice.get("model_id", "eleven_multilingual_v2"),
                    "voice_settings": {"stability": voice.get("stability", 0.43), "similarity_boost": voice.get("similarity_boost", 0.96),
                                       "style": voice.get("style", 0.0), "use_speaker_boost": True, "speed": voice.get("speed", 1.03)}}
            mid = str(body["model_id"])   # chỉ model turbo/flash v2.5 nhận language_code
            if voice.get("language_code") and ("turbo" in mid or "flash" in mid): body["language_code"] = voice["language_code"]
            if i > 0: body["previous_text"] = texts[i - 1]
            if i < len(texts) - 1: body["next_text"] = texts[i + 1]
            for attempt in range(3):
                r = requests.post(f"{BASE}/v1/text-to-speech/{voice['voice_id']}", params={"output_format": "mp3_44100_128"},
                                  headers={"xi-api-key": api_key, "Content-Type": "application/json", "Accept": "audio/mpeg"}, json=body, timeout=120)
                if r.status_code == 200: open(path, "wb").write(r.content); break
                log.warning("ElevenLabs %s: %s", r.status_code, r.text[:300])
                if r.status_code in (400, 401, 403, 422) or attempt == 2: raise RuntimeError(f"ElevenLabs lỗi {r.status_code}: {r.text[:300]}")
        out.append(path)
    return out

def _fake(txt, path):
    """giọng giả (im lặng) để chạy thử không tốn credit: ~4.3 âm tiết/giây"""
    syl = len(re.findall(r"\w+", txt)); dur = max(1.5, syl / 4.3)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"sine=frequency=220:duration={dur:.2f}", "-af", "volume=0.02",
                    "-ar", "44100", "-ac", "1", "-b:a", "128k", path], check=True)
