#!/usr/bin/env bash
# Redeploy SAWALA: pull latest main, rebuild dashboard, reinstall Python
# deps if requirements.txt changed, then restart via PM2.
set -euo pipefail

cd "$(dirname "$0")/.."

echo "==> git pull"
git pull origin main

echo "==> pip install (kalau requirements.txt berubah)"
venv/bin/pip install -q -r requirements.txt

echo "==> build dashboard"
cd dashboard
npm ci --silent
npm run build
cd ..

echo "==> restart pm2"
pm2 restart sawala

echo "==> health check"
for i in 1 2 3 4 5 6 7 8; do
  if curl -sS -m 5 http://127.0.0.1:8000/api/health; then
    echo
    echo "==> done"
    exit 0
  fi
  sleep 3
done
echo "==> WARNING: health check tidak merespons setelah 24 detik, cek 'pm2 logs sawala'"
exit 1
