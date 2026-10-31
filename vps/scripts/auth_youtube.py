"""Lấy refresh token YouTube cho 1 kênh. CHẠY TRÊN MÁY TÍNH CÁ NHÂN (có trình duyệt), rồi copy file json lên VPS.
python3 auth_youtube.py client_secret.json youtube_chainfolk.json
- client_secret.json: tải từ Google Cloud Console > APIs & Services > Credentials > OAuth client ID (loại Desktop app)
- Khi trình duyệt hỏi, đăng nhập đúng tài khoản Google sở hữu kênh và CHỌN ĐÚNG KÊNH."""
import sys, json, webbrowser, urllib.parse, http.server, requests

cs = json.load(open(sys.argv[1])); cs = cs.get("installed") or cs.get("web"); out = sys.argv[2]
PORT = 8765; redirect = f"http://localhost:{PORT}"
url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode({
    "client_id": cs["client_id"], "redirect_uri": redirect, "response_type": "code", "access_type": "offline", "prompt": "consent",
    "scope": "https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube.readonly"})
code = {}
class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query); code["c"] = q.get("code", [None])[0]
        self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.end_headers()
        self.wfile.write("Xong! Quay lại cửa sổ dòng lệnh.".encode())
    def log_message(self, *a): pass
print("Mở link sau nếu trình duyệt không tự bật:\n", url); webbrowser.open(url)
srv = http.server.HTTPServer(("localhost", PORT), H)
while "c" not in code: srv.handle_request()
r = requests.post("https://oauth2.googleapis.com/token", data={"code": code["c"], "client_id": cs["client_id"], "client_secret": cs["client_secret"],
                                                           "redirect_uri": redirect, "grant_type": "authorization_code"}).json()
if "refresh_token" not in r: sys.exit(f"Lỗi: {r}")
json.dump({"client_id": cs["client_id"], "client_secret": cs["client_secret"], "refresh_token": r["refresh_token"]}, open(out, "w"))
ch = requests.get("https://www.googleapis.com/youtube/v3/channels", params={"part": "snippet", "mine": "true"}, headers={"Authorization": "Bearer " + r["access_token"]}).json()
print("Đã lưu", out, "— kênh:", [i["snippet"]["title"] for i in ch.get("items", [])])
