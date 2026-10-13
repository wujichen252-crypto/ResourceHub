# ResourceHub × 1Panel 部署实操指导

> 本文指导你在**装有 1Panel 的服务器**上从零部署 ResourceHub，按顺序执行、每步带验证点。
> 技术细节与故障速查见 [DEPLOYMENT_GUIDE.md](../DEPLOYMENT_GUIDE.md)，本文侧重 1Panel 环境下的操作路径与避坑。

## 前置准备清单

| 项目 | 要求 | 检查方式 |
|------|------|---------|
| Docker + Compose v2 | 1Panel 安装时已自带 | 1Panel 面板 → 容器 → 确认能显示容器列表 |
| 服务器端口空闲 | `80`、`8000` 未被占用 | 见「第 1 步」的端口检查 |
| MySQL 数据库 | 二选一，见下 | — |
| GitHub 仓库可访问 | 代码能 clone 到服务器 | `git clone` 成功 |

### 数据库二选一

- **方案 A（复用现有远端 MySQL，推荐）**：继续使用 162.14.111.9 上的 `resourcehub` 库（与本地开发连接的是同一个库），数据现成、无需迁移。
  前提：在 MySQL 侧把**新服务器公网 IP** 加入 `resourcehub` 账号白名单。
- **方案 B（新服务器用 1Panel 应用商店装 MySQL）**：面板 → 应用商店 → 安装 MySQL，再建 `resourcehub` 库。
  如需带走旧数据：本地 `cd backend`，把 `.env` 的 `DATABASE_URL` 临时指向新库，运行 `uv run python migrate_to_remote.py`（详见 docs/database-migration.md）。

## 第 1 步：端口占用检查

本项目 compose 实际映射：**前端 9200**（容器内 nginx 80）、**后端 8000**。1Panel 的 OpenResty 占用 80 与本部署**不冲突**。

面板 → 主机 → 终端（或 SSH），执行：

```bash
ss -tlnp | grep -E ':(9200|8000)\s'
docker ps   # 查看是否有旧部署残留容器
```

- **8000 或 9200 被旧 resourcehub 容器占用**（常见：之前试验性部署过）→ 先清理：
  ```bash
  docker rm -f resourcehub-backend resourcehub-frontend 2>/dev/null
  ```
- **被其他无关容器占用** → 编辑 `docker-compose.yml` 改宿主机侧映射（如 `"8001:8000"`），并把 `deploy.sh` 健康检查中的 8000 同步改掉。
- 若希望用 80 直接访问：保持 compose 不动，在 1Panel 网站中用 OpenResty 反向代理到 `127.0.0.1:9200` 即可。

✅ 验证：`ss -tlnp` 中 9200、8000 无残留占用。

## 第 2 步：拉取代码

```bash
sudo mkdir -p /opt && cd /opt
git clone https://github.com/wujichen252-crypto/ResourceHub.git
cd ResourceHub
```

✅ 验证：`ls` 能看到 `docker-compose.yml`、`backend/`、`frontend/`、`scripts/deploy/`。

## 第 3 步：创建 .env.production（缺了它 compose 直接报错）

```bash
cd /opt/ResourceHub
# 生成 JWT 密钥
docker run --rm python:3.10-slim python -c "import secrets; print(secrets.token_hex(32))"
```

```bash
cat > .env.production << 'EOF'
DATABASE_URL=mysql+aiomysql://resourcehub:<你的密码>@<MySQL地址>:3306/resourcehub?charset=utf8mb4
SECRET_KEY=<上一步生成的64位hex>
EOF
chmod 600 .env.production
```

MySQL 地址怎么填：
- 方案 A：填远端 MySQL 的 IP（`162.14.111.9`）
- 方案 B（本机 1Panel MySQL）：填服务器**内网 IP**（面板 → 主机 → 信息），不要用 `localhost`——容器内的 localhost 不是宿主机

✅ 验证：`cat .env.production` 两项都已填真实值；先测连通：
```bash
python3 -c "import socket; socket.create_connection(('<MySQL地址>', 3306), 5); print('MySQL 可达')"
```

## 第 4 步：构建并启动

两种路径任选（推荐终端，报错信息更完整）：

**终端方式**：
```bash
cd /opt/ResourceHub
sudo docker compose --env-file .env.production up -d --build
```

**面板方式**：容器 → Compose → 创建 Compose → 项目路径 `/opt/ResourceHub`、编排内容粘贴 `docker-compose.yml` 全文 → 启动。

✅ 验证（约 1-2 分钟后）：
```bash
sudo docker compose ps
# backend 应为 Up (healthy)；若 unhealthy，先 docker compose logs backend 看原因
```

## 第 5 步：初始化数据库表结构（生产环境不自动建表，漏了这步接口全 404）

```bash
cd /opt/ResourceHub
# 空库（方案 B 新库）：
sudo docker compose exec backend alembic upgrade head
# 已有完整表（方案 A 旧库）：只需打版本标记
# sudo docker compose exec backend alembic stamp head

sudo docker compose exec backend alembic current   # 输出 head 即成功
```

## 第 6 步：端到端验收

```bash
curl http://127.0.0.1:9200/health            # 经前端 nginx 反代到后端，返回 JSON 即通
```

浏览器打开 `http://<服务器IP>:9200`：
- [ ] 登录页正常渲染（黑白极简界面）
- [ ] 注册或登录成功
- [ ] Dashboard 统计图表、笔记/提示词列表能加载出旧数据（方案 A）

全部通过 = 部署成功 🎉

## 日常更新

本地 `git push` 后，在服务器执行：

```bash
cd /opt/ResourceHub && sudo bash scripts/deploy/deploy-server.sh
# 若更新包含数据库变更，补：
sudo docker compose exec backend alembic upgrade head
```

## 常见报错速查

| 报错 | 原因 | 解决 |
|------|------|------|
| `port is already allocated` | 80/8000 被 1Panel 组件占用 | 回第 1 步改映射 |
| `env file .env.production not found` | 第 3 步未做 | 创建文件 |
| backend 反复重启 + `生产环境必须设置 SECRET_KEY` | SECRET_KEY 为空 | 补第 3 步 |
| backend 日志 `Can't connect to MySQL server` | 白名单/地址/防火墙问题 | 检查 MySQL 授权与第 3 步地址 |
| 页面 502 | backend 没起来 | `docker compose logs backend` |
| 登录 200 但列表空/404 | 没跑迁移 | 第 5 步 |
