# 🚀 ResourceHub 自动部署配置

## ✅ 已完成的配置

- ✅ 生成了 `SECRET_KEY`: `55fa634c358079103e1830722b96b29152c6cc5b95e7437668f7606108732c99`
- ✅ 创建了 `.env.production` 文件
  - `SERVER_IP=162.14.111.9`
  - `DOMAIN=162.14.111.9`
- ✅ 创建了自动部署脚本: `/opt/ResourceHub/deploy.sh`
- ✅ 创建了 GitHub Webhook 接收服务: `/opt/ResourceHub/webhook-deploy.py`
- ✅ 启动了 Webhook 服务 (监听端口 9000)

## 📝 需要在 GitHub 中配置的步骤

### 第一步：生成 GitHub Webhook Secret

在服务器上生成一个 Webhook Secret：
```bash
python3 -c "import secrets; print(secrets.token_hex(16))"
```

### 第二步：配置 GitHub Webhook

1. 访问 GitHub 仓库: https://github.com/wujichen252-crypto/ResourceHub/settings/hooks
2. 点击 **Add webhook**
3. 填写以下信息：

```
Payload URL: http://162.14.111.9:9000/webhook/deploy
Content type: application/json
Secret: [从第一步生成的 Secret]
Which events would you like to trigger this webhook?
  ☑ Just the push event
☑ Active
```

4. 点击 **Add webhook**

### 第三步：在服务器更新 Webhook Secret

替换 `/etc/systemd/system/resourcehub-webhook.service` 中的 Secret：

```bash
sudo nano /etc/systemd/system/resourcehub-webhook.service
```

找到这一行：
```
Environment="GITHUB_WEBHOOK_SECRET=webhook-secret-change-me"
```

改为你生成的 Secret，然后重启：
```bash
sudo systemctl daemon-reload
sudo systemctl restart resourcehub-webhook
```

## 📊 在 1Panel 中配置项目管理

现在需要在 1Panel 中添加应用：

1. **访问 1Panel**: http://162.14.111.9
2. **导航**: 应用 → 应用编排 → 新建编排
3. **填写信息**：
   - **名称**: ResourceHub
   - **Git 仓库**: https://github.com/wujichen252-crypto/ResourceHub.git
   - **分支**: main
   - **部署路径**: /opt/ResourceHub
   - **Docker Compose 文件**: docker-compose.yml

4. **环境变量**: 选择使用本地 `.env.production` 文件

## 🔍 查看部署日志

```bash
# Webhook 日志
sudo tail -f /var/log/webhook-deploy.log

# 部署日志
sudo tail -f /var/log/resourcehub-deploy.log

# Systemd 日志
sudo journalctl -u resourcehub-webhook -f
```

## 🧪 测试自动部署

### 测试完整流程
推送一个空提交到 main：
```bash
cd /opt/ResourceHub
git commit --allow-empty -m "test webhook trigger"
git push origin main
```

然后查看日志确认自动部署是否触发。

---

**配置完成后，每次 push 到 main 分支都会自动触发部署！🎉**
