#!/usr/bin/env bash
set -Eeuo pipefail

# 脚本位于 scripts/deploy/，回到仓库根目录执行 git 与 docker compose
cd "$(dirname "$0")/../.."
git fetch origin main
git checkout main
git reset --hard origin/main
# 显式指定生产环境文件，避免依赖默认 .env 查找
docker compose --env-file .env.production up -d --build --remove-orphans
docker compose ps
curl --fail --silent --show-error http://127.0.0.1:9200/health >/dev/null
echo "ResourceHub 部署完成"
