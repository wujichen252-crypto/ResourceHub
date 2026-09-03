"""数据库迁移脚本"""
import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), "resourcehub.db")
if not os.path.exists(db_path):
    print("数据库文件不存在，跳过迁移")
    exit(0)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# === prompt_versions 表 ===
cursor.execute("PRAGMA table_info(prompt_versions)")
cols = {row[1] for row in cursor.fetchall()}
print("prompt_versions 列:", cols)

if "message" not in cols:
    cursor.execute("ALTER TABLE prompt_versions ADD COLUMN message VARCHAR(500)")
    print("✅ 已添加 message 列")
if "labels" not in cols:
    cursor.execute("ALTER TABLE prompt_versions ADD COLUMN labels VARCHAR(500)")
    print("✅ 已添加 labels 列")
if "branch_name" not in cols:
    cursor.execute("ALTER TABLE prompt_versions ADD COLUMN branch_name VARCHAR(100) DEFAULT 'main'")
    print("✅ 已添加 branch_name 列")

# === prompts 表 ===
cursor.execute("PRAGMA table_info(prompts)")
cols = {row[1] for row in cursor.fetchall()}
print("prompts 列:", cols)

if "tags" not in cols:
    cursor.execute("ALTER TABLE prompts ADD COLUMN tags VARCHAR(500)")
    print("✅ 已添加 tags 列")

conn.commit()
conn.close()
print("\n迁移完成")
