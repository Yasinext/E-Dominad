#!/usr/bin/env bash
set -euo pipefail

APP_DIR=${APP_DIR:-/opt/domainbot/app}
VENV_DIR=${VENV_DIR:-/opt/domainbot/venv}

git -C "$APP_DIR" diff --quiet
git -C "$APP_DIR" fetch --prune
git -C "$APP_DIR" pull --ff-only origin main

"$VENV_DIR/bin/pip" install -e "$APP_DIR"
"$VENV_DIR/bin/alembic" -c "$APP_DIR/alembic.ini" upgrade head

systemctl restart domainbot-worker.service
systemctl restart domainbot-btk-worker.service
systemctl restart domainbot-scheduler.service
systemctl restart domainbot-bot.service

"$APP_DIR/deploy/scripts/healthcheck.sh"
