# ResourceHub 部署指南（1Panel 服务器）

适用场景：在全新安装了 1Panel（自带 Docker + docker compose v2）的服务器上部署本项目。
按顺序执行即可一次成功；每步末尾有验证点，验证通过再进行下一步。

## 0. 部署前检查（服务器上）

```bash
docker --version && docker compose version   # 需要 compose v2
```

- [ ] 安全组/防火墙放行：`9200`（前端对外端口）、`9000`（可选 webhook）；`8000` 无需公网暴露
- [ ] MySQL 可达：远端 MySQL 需允许本服务器 IP 连接（在 MySQL 侧授权 `resourcehub` 账号）
- [ ] 端口连通性预检（把 host/3306 换成你的实际值）：
  ```bash
  python3 -c "import socket; socket.create_connection(('<mysql-host>', 3306), 5); print('MySQL 可达')"
  ```

## 1. 拉取代码

```bash
sudo mkdir -p /opt && cd /opt
git clone https://github.com/wujichen252-crypto/ResourceHub.git
cd ResourceHub
```

## 2. 创建生产环境变量文件 `.env.production`

> ⚠️ 仓库根目录的 `docker-compose.yml` 通过 `env_file: .env.production` 读取该文件，**不存在则 compose 直接启动失败**。

```bash
cd /opt/ResourceHub
cat > .env.production << 'EOF'
# 数据库（必填）：把 host/端口/账号/密码换成你的实际值，保留 charset
DATABASE_URL=mysql+aiomysql://resourcehub:<密码>@<mysql-host>:3306/resourcehub?charset=utf8mb4

# JWT 密钥（必填）：生成方式见下
SECRET_KEY=<32字节hex>
EOF
chmod 600 .env.production
```

生成 SECRET_KEY：

```bash
docker run --rm python:3.10-slim python -c "import secrets; print(secrets.token_hex(32))"
```

说明：
- `ENV=production`、`DEBUG=false`、token 过期时间已在 compose 中注入，无需写入
- **CORS 无需配置**：前端 API 走同域 nginx 反代（`/api/ → backend:8000`），浏览器不产生跨域请求
- 生产环境 `SECRET_KEY` 缺失时后端会直接拒绝启动（fail-fast，属预期行为）

## 3. 构建并启动

```bash
sudo docker compose --env-file .env.production up -d --build
sudo docker compose ps
```

验证点：两个容器均为 `Up`，backend 状态约 30 秒后变为 `Up (healthy)`。

```bash
# 健康检查（compose 内置 healthcheck 已改用 python urllib，slim 镜像无 curl）
sudo docker compose exec backend python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/health').read().decode())"
```

## 4. 初始化数据库 schema（Alembic）

生产环境后端启动时**不会**自动建表，schema 由 Alembic 管辖，首次部署必须执行：

```bash
# 全新空库：
sudo docker compose exec backend alembic upgrade head

# 若目标库已有完整表结构（如从旧库迁移的数据），只打版本标记不重复建表：
sudo docker compose exec backend alembic stamp head
```

验证：`sudo docker compose exec backend alembic current` 输出 `head`。

## 5. 端到端验证

```bash
curl http://127.0.0.1:9200/health          # 经前端 nginx 反代到后端
curl http://127.0.0.1:9200/api/auth/login  # 预期 405/422（路由存在即通），非 502
```

浏览器打开 `http://<服务器IP>:9200`：登录页正常渲染，注册/登录成功即部署完成。

## 6. 日常更新

推送代码到 GitHub `main` 后：

```bash
cd /opt/ResourceHub && sudo bash scripts/deploy/deploy-server.sh
```

该脚本执行 git 拉取 + 重建容器。若本次更新包含新的 Alembic 迁移，更新后补跑：

```bash
sudo docker compose exec backend alembic upgrade head
```

### （可选）GitHub Webhook 自动部署

```bash
# webhook 服务指向 scripts/deploy/deploy.sh；服务器上首次启用：
sudo cp scripts/deploy/webhook-deploy.py /opt/ResourceHub/scripts/deploy/
# 配置 systemd 服务（WorkingDirectory=/opt/ResourceHub，Environment=GITHUB_WEBHOOK_SECRET=...），
# 并在 GitHub 仓库 Settings → Webhooks 添加 http://<服务器IP>:9000/webhook/deploy（push 事件）
```

## 故障速查

| 症状 | 原因 | 处理 |
|------|------|------|
| compose 报 `env file .env.production not found` | 第 2 步未完成 | 创建文件后重试 |
| backend 启动即退出，日志 `生产环境必须设置 SECRET_KEY` | SECRET_KEY 为空 | 补 `.env.production` |
| backend 反复重启，日志数据库连接超时 | MySQL 白名单/防火墙未放行本服务器 IP | 授权后 `docker compose restart backend` |
| 页面能开但接口 502 | backend 容器未起来 | `docker compose logs backend` |
| 接口 404/数据为空 | 未跑迁移 | 执行第 4 步 |
| MySQL 连不上 | 白名单未放行本服务器 IP | 在 162.14.111.9 的 MySQL 上授权新服务器 IP |
