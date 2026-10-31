"""YouTube Shorts qua YouTube Data API v3 (OAuth refresh token, upload resumable)."""
import os, json, requests

TOKEN_URL = os.environ.get("GOOGLE_TOKEN_URL", "https://oauth2.googleapis.com/token")
UPLOAD = os.environ.get("YT_UPLOAD_BASE", "https://www.googleapis.com/upload/youtube/v3/videos")

def _access_token(tok):
    r = requests.post(TOKEN_URL, data={"client_id": tok["client_id"], "client_secret": tok["client_secret"],
                                       "refresh_token": tok["refresh_token"], "grant_type": "refresh_token"}, timeout=30)
    r.raise_for_status(); return r.json()["access_token"]

def upload(video, meta, pcfg, label_ai=True):
    tok = json.load(open(pcfg["token_file"])); at = _access_token(tok); size = os.path.getsize(video)
    body = {"snippet": {"title": meta["title"], "description": meta["description"], "tags": meta.get("tags", []), "categoryId": "25"},
            "status": {"privacyStatus": pcfg.get("privacy", "public"), "selfDeclaredMadeForKids": False, "containsSyntheticMedia": bool(label_ai)}}
    r = requests.post(UPLOAD, params={"uploadType": "resumable", "part": "snippet,status"}, json=body, timeout=60,
                      headers={"Authorization": f"Bearer {at}", "X-Upload-Content-Type": "video/mp4", "X-Upload-Content-Length": str(size)})
    if r.status_code != 200: raise RuntimeError(f"YouTube init {r.status_code}: {r.text[:300]}")
    loc = r.headers["Location"]
    with open(video, "rb") as f:
        r2 = requests.put(loc, data=f, headers={"Authorization": f"Bearer {at}", "Content-Type": "video/mp4", "Content-Length": str(size)}, timeout=1800)
    if r2.status_code not in (200, 201): raise RuntimeError(f"YouTube upload {r2.status_code}: {r2.text[:300]}")
    vid = r2.json()["id"]; return f"https://youtube.com/shorts/{vid}"
