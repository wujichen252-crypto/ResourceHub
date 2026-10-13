# 更新服务器代码指南（日常部署）

> 适用场景：本地代码改好并 `git push` 到 GitHub `main` 后，如何把服务器（162.14.111.9，1Panel 环境）更新到最新版本。
> 首次部署见 [1panel-deployment-guide.md](./1panel-deployment-guide.md)，本文只讲**日常更新**。

## 更新流程（三步）

### 第 1 步：本地推送

```powershell
cd d:\大学就业指导\项目相关\项目落地（全栈）\ResourceHub
git add -A
git commit -m "描述本次改动"
git push origin main
```

### 第 2 步：服务器执行更新脚本

SSH 登录服务器（或通过 1Panel 面板 → 主机 → 终端），执行：

```bash
cd /opt/ResourceHub && sudo bash scripts/deploy/deploy-server.sh
```

该脚本自动完成：`git fetch` → 重置到 `origin/main` → `docker compose up -d --build`（前端有改动时自动重新 `npm run build`）→ 健康检查。

看到 `ResourceHub 部署完成` 即成功。

### 第 3 步：验证

```bash
cd /opt/ResourceHub
sudo docker compose ps          # backend 应为 Up (healthy)，约 30 秒后
curl -s http://127.0.0.1:9200/health   # 预期 {"code":200,...}
```

浏览器打开 `https://resourcehub.wujichen.online` 确认页面功能正常。

## ⚠️ 含数据库变更的更新（多一步）

如果本次改动**新增/修改了 Alembic 迁移**（`backend/migrations/versions/` 下有变化，或 AGENTS 会话里提到加了字段/表），更新脚本跑完后必须补执行：

```bash
cd /opt/ResourceHub
sudo docker compose exec backend alembic upgrade head
```

漏掉的典型症状：接口 500、日志出现 `Unknown column ...`。

不确定是否有迁移时，跑一次 `alembic upgrade head` 无害（已是最新则直接提示成功）。

## 何时需要 `--force-recreate`

以下情况 compose 的常规重建不够，需要强制重建容器：

```bash
sudo docker compose --env-file .env.production up -d --build --force-recreate
```

- 修改了 `docker-compose.yml`（端口、环境变量、挂载等）
- 修改了 `.env.production`（如轮换 SECRET_KEY、数据库密码）
- 容器行为诡异想彻底重来

## 更新失败回退

```bash
cd /opt/ResourceHub
git log --oneline -5                 # 找到上一个正常的提交
git reset --hard <正常提交的哈希>
sudo docker compose --env-file .env.production up -d --build
```

回退后记得在本地修复问题再重新推送，避免下次更新又带回故障。

## 常见更新故障速查

| 症状 | 原因 | 处理 |
|------|------|------|
| `git reset` 报冲突/失败 | 服务器上有手改文件 | `git checkout -- . && git clean -fd`（会丢弃服务器手改，慎用）后重试 |
| build 阶段报 Python 语法/API 错误 | 新代码用了 3.10 不支持的 API | 本地先跑 `uv run pytest`（本地也是 3.10）再推送 |
| backend 起不来，日志 `Can't connect to MySQL` | MySQL 容器重启过、ufw 规则丢失 | `sudo ufw allow from 172.16.0.0/12 to any port 3306 proto tcp` |
| 页面正常但接口 500 | 漏跑迁移 | `alembic upgrade head` |
| 前端改动不生效 | 浏览器缓存 | Ctrl+F5 强刷；确认 compose build 没有全部 CACHED（全部 CACHED 说明代码没拉新） |
| `port is already allocated` | 旧容器没退干净 | `sudo docker compose down` 后再 `up -d --build` |

## 备注

- `.env.production` 在服务器本地、不入库，`git reset --hard` 不会动它
- 数据卷 `backend-data` 跨更新保留，上传的文件不会丢
- 若以后配置了 GitHub Webhook 自动部署（`scripts/deploy/webhook-deploy.py`），第 2 步可省略，push 即部署；手动流程随时可用，两者不冲突
