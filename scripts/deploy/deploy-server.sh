#!/usr/bin/env bash
set -Eeuo pipefail

cd "$(dirname "$0")"
git fetch origin main
git checkout main
git reset --hard origin/main
docker compose up -d --build --remove-orphans
docker compose ps
curl --fail --silent --show-error http://127.0.0.1/health >/dev/null
echo "ResourceHub 部署完成"
