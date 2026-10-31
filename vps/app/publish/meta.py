"""Instagram Reels + Facebook Page Reels qua Graph API (upload resumable file trên máy)."""
import os, time, requests

GRAPH = os.environ.get("GRAPH_BASE", "https://graph.facebook.com")
RUP = os.environ.get("RUPLOAD_BASE", "https://rupload.facebook.com")

def _ok(r, what):
    try: js = r.json()
    except Exception: js = {"raw": r.text[:300]}
    if r.status_code >= 400 or "error" in js: raise RuntimeError(f"{what} {r.status_code}: {js}")
    return js

def instagram(video, meta, pcfg, ver, label_ai=True):
    tok = os.environ[pcfg["token_env"]]; ig = pcfg["ig_user_id"]; size = os.path.getsize(video)
    js = _ok(requests.post(f"{GRAPH}/{ver}/{ig}/media", timeout=60, headers={"Authorization": f"Bearer {tok}"},
                           data={"media_type": "REELS", "upload_type": "resumable", "caption": meta["caption"], "share_to_feed": "true",
                                 "thumb_offset": "1500", **({"is_ai_generated": "true"} if label_ai else {})}), "IG tạo container")
    cid = js["id"]
    with open(video, "rb") as f:
        _ok(requests.post(f"{RUP}/ig-api-upload/{ver}/{cid}", data=f, timeout=1800,
                          headers={"Authorization": f"OAuth {tok}", "offset": "0", "file_size": str(size)}), "IG upload")
    for _ in range(90):
        st = _ok(requests.get(f"{GRAPH}/{ver}/{cid}", params={"fields": "status_code,status", "access_token": tok}, timeout=30), "IG trạng thái")
        if st.get("status_code") == "FINISHED": break
        if st.get("status_code") == "ERROR": raise RuntimeError(f"IG xử lý lỗi: {st}")
        time.sleep(5)
    pub = _ok(requests.post(f"{GRAPH}/{ver}/{ig}/media_publish", data={"creation_id": cid}, headers={"Authorization": f"OAuth {tok}"}, timeout=60), "IG publish")
    try:
        pl = requests.get(f"{GRAPH}/{ver}/{pub['id']}", params={"fields": "permalink", "access_token": tok}, timeout=30).json().get("permalink")
    except Exception: pl = None
    return pl or f"Instagram: đã đăng (id {pub['id']})"

def facebook(video, meta, pcfg, ver, label_ai=True):
    tok = os.environ[pcfg["token_env"]]; page = pcfg["page_id"]; size = os.path.getsize(video)
    js = _ok(requests.post(f"{GRAPH}/{ver}/{page}/video_reels", json={"upload_phase": "start", "access_token": tok}, timeout=60), "FB start")
    vid = js["video_id"]
    with open(video, "rb") as f:
        _ok(requests.post(f"{RUP}/video-upload/{ver}/{vid}", data=f, timeout=1800,
                          headers={"Authorization": f"OAuth {tok}", "offset": "0", "file_size": str(size), "Content-Type": "application/octet-stream"}), "FB upload")
    for _ in range(60):
        st = _ok(requests.get(f"{GRAPH}/{ver}/{vid}", params={"fields": "status", "access_token": tok}, timeout=30), "FB trạng thái").get("status", {})
        if (st.get("uploading_phase") or {}).get("status") == "complete" or st.get("video_status") in ("ready", "upload_complete"): break
        if st.get("video_status") == "error": raise RuntimeError(f"FB xử lý lỗi: {st}")
        time.sleep(3)
    _ok(requests.post(f"{GRAPH}/{ver}/{page}/video_reels", timeout=60, params={"access_token": tok, "video_id": vid, "upload_phase": "finish",
                       "video_state": "PUBLISHED", "description": meta["description"], "title": meta["title"], **({"is_ai_generated": "true"} if label_ai else {})}), "FB finish")
    return f"https://www.facebook.com/reel/{vid}"
