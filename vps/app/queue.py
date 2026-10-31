"""Hàng đợi qua kho GitHub riêng tư:
  inbox/      Claude đẩy kịch bản JSON vào  -> VPS đọc, dựng video
  requests/   VPS ghi yêu cầu của bạn (tin mới / góp ý sửa) -> Claude đọc ở lượt kiểm tra kế tiếp"""
import os, base64, json, logging, requests

log = logging.getLogger("queue")
API = os.environ.get("GITHUB_API", "https://api.github.com")

class Repo:
    def __init__(self, token, repo, branch="main"):
        self.repo, self.branch = repo, branch
        self.h = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}

    def check(self):
        r = requests.get(f"{API}/repos/{self.repo}", headers=self.h, timeout=20)
        if r.status_code != 200: return False, f"{r.status_code} {r.text[:150]}"
        js = r.json(); return bool(js.get("permissions", {}).get("push")), ("riêng tư" if js.get("private") else "CÔNG KHAI (nên đổi sang Private)")

    def list(self, path):
        r = requests.get(f"{API}/repos/{self.repo}/contents/{path}", headers=self.h, params={"ref": self.branch}, timeout=30)
        if r.status_code == 404: return []
        r.raise_for_status(); js = r.json()
        return [x for x in js if x.get("type") == "file"] if isinstance(js, list) else []

    def get(self, path):
        r = requests.get(f"{API}/repos/{self.repo}/contents/{path}", headers=self.h, params={"ref": self.branch}, timeout=30)
        r.raise_for_status(); return base64.b64decode(r.json()["content"]).decode("utf-8")

    def put(self, path, text, message):
        body = {"message": message, "content": base64.b64encode(text.encode("utf-8")).decode(), "branch": self.branch}
        r = requests.put(f"{API}/repos/{self.repo}/contents/{path}", headers=self.h, json=body, timeout=30)
        if r.status_code not in (200, 201): raise RuntimeError(f"GitHub ghi {path} lỗi {r.status_code}: {r.text[:200]}")
        return True
