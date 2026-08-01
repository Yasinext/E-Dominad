#!/usr/bin/env bash
set -euo pipefail

systemctl is-active --quiet domainbot-bot.service
systemctl is-active --quiet domainbot-worker.service
systemctl is-active --quiet domainbot-scheduler.service
