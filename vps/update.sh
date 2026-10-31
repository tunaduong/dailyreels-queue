#!/usr/bin/env bash
# CẬP NHẬT NHANH (giữ nguyên khóa, cấu hình, dữ liệu):
#   cd /root/dailyreels-queue && git pull && bash vps/update.sh
set -e
SRC="$(cd "$(dirname "$0")" && pwd)"; APP=/opt/dailyreels
rsync -a --exclude .env --exclude config.yaml --exclude data/ --exclude .venv/ "$SRC"/ $APP/
$APP/.venv/bin/pip install -q -r $APP/requirements.txt
chown -R dailyreels:dailyreels $APP
systemctl restart dailyreels && sleep 2 && systemctl is-active dailyreels && echo "✅ Đã cập nhật và khởi động lại bot."
