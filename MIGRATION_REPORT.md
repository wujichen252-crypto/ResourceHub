# ResourceHub 数据库迁移报告

## 迁移完成时间
2026-09-20 10:59

## 迁移概述
✅ **成功** - 将本地 SQLite 数据库的所有数据迁移到远程 MySQL 数据库

## 迁移详情

### 源数据库
- **类型**: SQLite
- **位置**: 本地 `resourcehub.db`
- **状态**: 已备份（保留在本地）

### 目标数据库
- **类型**: MySQL 5.7
- **地址**: 162.14.111.9
- **数据库名**: resourcehub
- **字符集**: utf8mb4
- **用户**: resourcehub
- **密码**: km56iwexNjzyrGEd

### 迁移数据统计

| 数据类型 | 数量 | 状态 |
|---------|------|------|
| 👤 用户 (users) | 4 | ✅ 已迁移 |
| 📝 笔记 (notes) | 20 | ✅ 已迁移 |
| 📁 分类 (categories) | 61 | ✅ 已迁移 |
| 🤖 提示词 (prompts) | 1 | ✅ 已迁移 |
| 📦 提示词版本 (prompt_versions) | 1 | ✅ 已迁移 |
| ⚙️ 提示词预设 (prompt_presets) | 0 | - |
| 📊 使用日志 (prompt_usage_logs) | 0 | - |

### 迁移过程

1. **清空远程数据库** ✅
   - 禁用外键检查
   - 删除所有现有表
   - 重新启用外键检查

2. **创建表结构** ✅
   - 在远程 MySQL 中创建所有 SQLAlchemy 模型对应的表

3. **迁移数据** ✅
   - 按依赖关系顺序迁移：User → Category → Note → Prompt → (versions, presets, logs)
   - 保留所有原始数据和时间戳
   - 保留所有外键关系

4. **验证迁移** ✅
   - 确认所有数据成功写入
   - 验证数据完整性
   - 应用能正常连接并读取数据

## 配置信息

### 环境变量配置 (.env)
```
ENV=development
DEBUG=true
DATABASE_URL=mysql+aiomysql://resourceHub:rkTrsHSMKtyHNLKn@47.108.232.238/resourcehub
ACCESS_TOKEN_EXPIRE_MINUTES=120
REFRESH_TOKEN_EXPIRE_DAYS=7
CORS_ORIGINS=http://localhost:5173,http://localhost:80
```

### 后端连接测试
✅ 后端服务成功启动并连接到远程 MySQL
✅ 所有表成功创建
✅ 数据可正常查询

## 后续步骤

1. ✅ 后端应用已配置使用远程 MySQL
2. 📋 前端应用可继续使用现有配置（连接 http://127.0.0.1:8800）
3. 📋 可选：将本地 SQLite `resourcehub.db` 备份到安全位置后删除

## 迁移脚本

迁移脚本已保存至：`backend/migrate_to_remote.py`

如需再次迁移，可运行：
```bash
cd backend
uv run python migrate_to_remote.py
```

## 注意事项

- 远程数据库凭证已配置在 `.env` 文件中（已被 `.gitignore` 忽略，不会提交到版本控制）
- 生产环境务必通过环境变量（不是 .env 文件）设置敏感信息
- 本地 SQLite 数据库保留作为备份

## 问题排查

如遇到迁移问题，常见原因：
1. 远程 MySQL 连接失败 → 检查网络和防火墙
2. 主键冲突 → 确保远程数据库已清空（脚本已自动处理）
3. 字符编码问题 → 已配置 utf8mb4 支持中文

---
**生成工具**: migrate_to_remote.py  
**迁移状态**: ✅ 完成
