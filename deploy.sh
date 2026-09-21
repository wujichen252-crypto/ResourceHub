#!/bin/bash
# ResourceHub 自动部署脚本

PROJECT_DIR="/opt/ResourceHub"
LOG_FILE="/var/log/resourcehub-deploy.log"
ENV_FILE="$PROJECT_DIR/.env.production"

mkdir -p /var/log

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "========== 开始部署 =========="
log "拉取最新代码..."

cd "$PROJECT_DIR" || exit 1

git config --global --add safe.directory "$PROJECT_DIR"
git fetch origin || { log "❌ Git fetch 失败"; exit 1; }
git reset --hard origin/main || { log "❌ Git reset 失败"; exit 1; }

log "停止旧容器..."
sudo docker-compose -f docker-compose.yml down || true

log "启动新容器（带完整路径的环境变量）..."
sudo docker-compose --env-file "$ENV_FILE" -f docker-compose.yml up -d --build

if [ $? -ne 0 ]; then
    log "❌ Docker-compose 启动失败"
    exit 1
fi

log "等待服务启动..."
sleep 15

log "检查后端健康状态..."
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    log "✅ 后端服务已启动"
else
    log "⚠️  后端服务检查超时"
fi

log "检查前端服务..."
if curl -s http://localhost:9200 > /dev/null 2>&1; then
    log "✅ 前端服务已启动"
else
    log "⚠️  前端服务检查超时"
fi

log "========== 部署完成 =========="
