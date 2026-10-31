"""TikTok Content Posting API.
mode=inbox  : đẩy video vào hộp nháp TikTok (chủ kênh bấm Đăng trong app) — dùng được khi app chưa qua kiểm duyệt.
mode=direct : đăng thẳng (cần app đã qua kiểm duyệt TikTok, nếu không chỉ đăng được chế độ riêng tư)."""
import os, json, time, math, requests

BASE = os.environ.get("TIKTOK_BASE", "https://open.tiktokapis.com")

def _token(path):
    tok = json.load(open(path))
    if time.time() > tok.get("expires_at", 0) - 300:
        r = requests.post(f"{BASE}/v2/oauth/token/", timeout=30, headers={"Content-Type": "application/x-www-form-urlencoded"},
                          data={"client_key": tok["client_key"], "client_secret": tok["client_secret"], "grant_type": "refresh_token", "refresh_token": tok["refresh_token"]})
        js = r.json()
        if "access_token" not in js: raise RuntimeError(f"TikTok refresh lỗi: {js}")
        tok.update(access_token=js["access_token"], refresh_token=js.get("refresh_token", tok["refresh_token"]), expires_at=time.time() + int(js.get("expires_in", 86400)))
        json.dump(tok, open(path, "w"))
    return tok["access_token"]

def _post(path, at, body):
    r = requests.post(f"{BASE}{path}", json=body, timeout=60, headers={"Authorization": f"Bearer {at}", "Content-Type": "application/json; charset=UTF-8"})
    js = r.json()
    if js.get("error", {}).get("code") not in (None, "ok"): raise RuntimeError(f"TikTok {path}: {js['error']}")
    return js.get("data", {})

def upload(video, meta, pcfg, label_ai=True):
    at = _token(pcfg["token_file"]); size = os.path.getsize(video)
    chunk = size if size <= 64 * 1024 * 1024 else 10 * 1024 * 1024; n = max(1, size // chunk)
    src = {"source": "FILE_UPLOAD", "video_size": size, "chunk_size": chunk, "total_chunk_count": n}
    if pcfg.get("mode", "inbox") == "direct":
        info = _post("/v2/post/publish/creator_info/query/", at, {})
        opts = info.get("privacy_level_options", ["SELF_ONLY"])
        priv = "PUBLIC_TO_EVERYONE" if "PUBLIC_TO_EVERYONE" in opts else opts[0]
        data = _post("/v2/post/publish/video/init/", at, {"post_info": {"title": meta["title"], "privacy_level": priv, "disable_duet": False,
                     "disable_stitch": False, "disable_comment": False, "video_cover_timestamp_ms": 1500, "is_aigc": bool(label_ai)}, "source_info": src})
    else:
        data = _post("/v2/post/publish/inbox/video/init/", at, {"source_info": src})
    url, pid = data["upload_url"], data["publish_id"]
    with open(video, "rb") as f:
        for i in range(n):
            start = i * chunk; end = size - 1 if i == n - 1 else start + chunk - 1; f.seek(start); buf = f.read(end - start + 1)
            r = requests.put(url, data=buf, timeout=600, headers={"Content-Type": "video/mp4", "Content-Length": str(len(buf)), "Content-Range": f"bytes {start}-{end}/{size}"})
            if r.status_code not in (200, 201, 206): raise RuntimeError(f"TikTok upload {r.status_code}: {r.text[:300]}")
    for _ in range(60):
        st = _post("/v2/post/publish/status/fetch/", at, {"publish_id": pid}); s = st.get("status", "")
        if s in ("PUBLISH_COMPLETE", "SEND_TO_USER_INBOX"):
            return "TikTok: đã vào hộp nháp — mở app TikTok để bấm Đăng" if s == "SEND_TO_USER_INBOX" else "TikTok: đã đăng ✓"
        if s == "FAILED": raise RuntimeError(f"TikTok xử lý lỗi: {st.get('fail_reason')}")
        time.sleep(5)
    return f"TikTok: đang xử lý (publish_id {pid})"
