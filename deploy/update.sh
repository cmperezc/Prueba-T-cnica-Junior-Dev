#!/usr/bin/env bash
# Actualiza la app en el servidor. Lo ejecuta GitHub Actions vía SSM (como root) después de `git pull`.
set -euo pipefail
cd /opt/pymedesk

sudo -u ubuntu .venv/bin/pip install -q -r requirements-prod.txt

cp deploy/pymedesk.service /etc/systemd/system/pymedesk.service
systemctl daemon-reload
systemctl restart pymedesk

cp deploy/nginx.conf /etc/nginx/sites-available/pymedesk
nginx -t
systemctl reload nginx

sleep 2
systemctl is-active pymedesk
git log --oneline -1
