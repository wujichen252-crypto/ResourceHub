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

- **方案 A（复用现有远端 MySQL，推荐）**：继续使用 47.108.232.238 上的 `resourcehub` 库，数据现成、无需迁移。
  前提：在 MySQL 侧把**新服务器公网 IP** 加入 `resourcehub` 账号白名单（1Panel 旧服务器若也装了 MySQL 同理）。
- **方案 B（新服务器用 1Panel 应用商店装 MySQL）**：面板 → 应用商店 → 安装 MySQL，再建 `resourcehub` 库。
  如需带走旧数据：本地 `cd backend`，把 `.env` 的 `DATABASE_URL` 临时指向新库，运行 `uv run python migrate_to_remote.py`（详见 docs/database-migration.md）。

## 第 1 步：端口冲突检查（1Panel 环境最容易踩的坑）

1Panel 的 OpenResty（网站功能）默认占用 **80/443**，而本项目 compose 的 frontend 也要映射 80，直接启动会报 `port is already allocated`。

面板 → 主机 → 终端（或 SSH），执行：

```bash
ss -tlnp | grep -E ':(80|8000)\s'
```

- **80 被 OpenResty 占用且你要用网站功能** → 改端口映射：编辑 `/opt/ResourceHub/docker-compose.yml`，把 frontend 的 `ports` 改为 `- "8080:80"`，之后通过 1Panel 网站反向代理或直接用 `http://IP:8080` 访问。
- **80 空闲** → 保持原样，部署后用 `http://IP` 访问。
- 8000 同理，被占就把 backend 映射改成 `127.0.0.1:8001:8000`（后端无需公网暴露，仅供前端反代）。

✅ 验证：记下最终对外端口（下文用 `<WEB_PORT>` 指代，默认 80）。

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
- 方案 A：填远端 MySQL 的 IP（如 `47.108.232.238`）
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
curl http://127.0.0.1:<WEB_PORT>/health            # 经 nginx 反代到后端，返回 JSON 即通
```

浏览器打开 `http://<服务器IP>:<WEB_PORT>`：
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
