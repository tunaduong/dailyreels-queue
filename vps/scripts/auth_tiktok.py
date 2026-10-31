"""Lấy token TikTok cho 1 kênh.
python3 auth_tiktok.py CLIENT_KEY CLIENT_SECRET https://redirect-cua-ban/ data/tokens/tiktok_chainfolk.json
1) Mở link in ra, đăng nhập đúng tài khoản TikTok của kênh, bấm Cho phép.
2) Trình duyệt chuyển tới redirect URI (trang có thể báo lỗi, không sao) — copy NGUYÊN địa chỉ trên thanh địa chỉ dán vào đây."""
import sys, json, time, secrets, urllib.parse, requests

key, secret, redirect, out = sys.argv[1:5]; state = secrets.token_hex(8)
url = "https://www.tiktok.com/v2/auth/authorize/?" + urllib.parse.urlencode({
    "client_key": key, "scope": "user.info.basic,video.upload,video.publish", "response_type": "code", "redirect_uri": redirect, "state": state})
print("Mở link:\n", url)
back = input("\nDán địa chỉ sau khi cho phép: ").strip()
code = urllib.parse.parse_qs(urllib.parse.urlparse(back).query)["code"][0]
r = requests.post("https://open.tiktokapis.com/v2/oauth/token/", headers={"Content-Type": "application/x-www-form-urlencoded"},
                  data={"client_key": key, "client_secret": secret, "code": code, "grant_type": "authorization_code", "redirect_uri": redirect}).json()
if "access_token" not in r: sys.exit(f"Lỗi: {r}")
json.dump({"client_key": key, "client_secret": secret, "access_token": r["access_token"], "refresh_token": r["refresh_token"],
           "expires_at": time.time() + int(r.get("expires_in", 86400)), "open_id": r.get("open_id")}, open(out, "w"))
print("Đã lưu", out)
