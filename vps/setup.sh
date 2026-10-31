#!/usr/bin/env bash
# =====================================================================
#  CÀI ĐẶT 1 LỆNH:   bash setup.sh
#  Chạy lại bất cứ lúc nào để cập nhật code mới (giữ nguyên khóa, cấu hình, dữ liệu).
# =====================================================================
set -e
if [ "$(id -u)" != "0" ]; then echo "Hãy chạy bằng root:  sudo bash setup.sh"; exit 1; fi
SRC="$(cd "$(dirname "$0")" && pwd)"; APP=/opt/dailyreels

echo "==> [1/4] Cài phần mềm hệ thống (python, ffmpeg)…"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq && apt-get install -y -qq python3 python3-venv python3-pip ffmpeg tzdata rsync >/dev/null

echo "==> [2/4] Chép chương trình vào $APP…"
id -u dailyreels >/dev/null 2>&1 || useradd -r -m -s /bin/bash dailyreels
mkdir -p $APP
EXCL="--exclude .env --exclude data/ --exclude .venv/"
[ -f $APP/config.yaml ] && EXCL="$EXCL --exclude config.yaml"
rsync -a $EXCL "$SRC"/ $APP/
mkdir -p $APP/data/tokens $APP/data/logs

echo "==> [3/4] Cài thư viện Python…"
[ -d $APP/.venv ] || python3 -m venv $APP/.venv
$APP/.venv/bin/pip install -q --upgrade pip >/dev/null
$APP/.venv/bin/pip install -q -r $APP/requirements.txt
cp $APP/deploy/dailyreels.service /etc/systemd/system/ && systemctl daemon-reload

echo "==> [4/4] Thiết lập khóa và giọng đọc…"
systemctl stop dailyreels 2>/dev/null || true
$APP/.venv/bin/python $APP/scripts/wizard.py
chown -R dailyreels:dailyreels $APP

systemctl enable --now dailyreels >/dev/null 2>&1
sleep 3
if systemctl is-active --quiet dailyreels; then
  echo ""; echo "✅ BOT ĐANG CHẠY. Mở Telegram, gõ /tin để thử."
  echo "   Xem log:  journalctl -u dailyreels -f"
else
  echo "❌ Bot chưa chạy được. Log:"; journalctl -u dailyreels -n 30 --no-pager
fi
