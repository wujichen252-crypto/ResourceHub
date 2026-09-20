"""
数据库迁移脚本：从本地 SQLite 迁移到远程 MySQL
执行步骤：
1. 在远程 MySQL 中创建所有表
2. 从本地 SQLite 读取数据
3. 写入到远程 MySQL
"""

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import inspect, select, MetaData, Table, text
from sqlalchemy.pool import NullPool

from app.core.database import Base
from app.core.config import settings
from app.models.user import User
from app.models.note import Note
from app.models.category import Category
from app.models.prompt import Prompt, PromptVersion, PromptPreset, PromptUsageLog


async def clear_remote_database():
    """清空远程 MySQL 中的所有表"""
    print("🗑️  清空远程数据库...")

    remote_engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        connect_args={"connect_timeout": 10},
        pool_size=10,
        max_overflow=20,
    )

    try:
        async with remote_engine.begin() as conn:
            # 禁用外键检查以便删除表
            await conn.execute(text("SET FOREIGN_KEY_CHECKS=0"))

            # 删除所有表
            await conn.run_sync(Base.metadata.drop_all)

            # 重新启用外键检查
            await conn.execute(text("SET FOREIGN_KEY_CHECKS=1"))
        print("✅ 远程数据库已清空")
    except Exception as e:
        print(f"❌ 清空表失败: {e}")
        raise
    finally:
        await remote_engine.dispose()


async def create_remote_tables():
    """在远程 MySQL 中创建所有表"""
    print("📋 开始在远程数据库创建表...")

    # 连接到远程 MySQL
    remote_engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        connect_args={"connect_timeout": 10},
        pool_size=10,
        max_overflow=20,
    )

    try:
        async with remote_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("✅ 远程数据库表创建成功")
    except Exception as e:
        print(f"❌ 创建表失败: {e}")
        raise
    finally:
        await remote_engine.dispose()


async def migrate_data():
    """迁移所有数据"""
    print("🔄 开始数据迁移...")

    # 本地 SQLite 引擎
    local_url = "sqlite+aiosqlite:///./resourcehub.db"
    local_engine = create_async_engine(
        local_url,
        echo=False,
        poolclass=NullPool,
    )

    # 远程 MySQL 引擎
    remote_engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        connect_args={"connect_timeout": 10},
        pool_size=10,
        max_overflow=20,
    )

    # 创建会话工厂
    LocalSession = async_sessionmaker(local_engine, class_=AsyncSession, expire_on_commit=False)
    RemoteSession = async_sessionmaker(remote_engine, class_=AsyncSession, expire_on_commit=False)

    try:
        # 迁移顺序：User -> Category -> Note -> Prompt -> (PromptVersion, PromptPreset, PromptUsageLog)

        # 1. 迁移用户
        print("\n👤 迁移用户数据...")
        async with LocalSession() as local_session:
            users = await local_session.execute(select(User))
            users_data = users.scalars().all()
            user_count = len(users_data)
            print(f"   找到 {user_count} 个用户")

            if user_count > 0:
                async with RemoteSession() as remote_session:
                    for user in users_data:
                        # 创建新的用户对象（避免会话绑定问题）
                        new_user = User(
                            id=user.id,
                            username=user.username,
                            email=user.email,
                            password_hash=user.password_hash,
                            avatar=user.avatar,
                            created_at=user.created_at,
                            updated_at=user.updated_at,
                        )
                        remote_session.add(new_user)
                    await remote_session.commit()
                print(f"   ✅ 已迁移 {user_count} 个用户")

        # 2. 迁移分类
        print("\n📁 迁移分类数据...")
        async with LocalSession() as local_session:
            categories = await local_session.execute(select(Category))
            categories_data = categories.scalars().all()
            category_count = len(categories_data)
            print(f"   找到 {category_count} 个分类")

            if category_count > 0:
                async with RemoteSession() as remote_session:
                    for category in categories_data:
                        new_category = Category(
                            id=category.id,
                            user_id=category.user_id,
                            name=category.name,
                            type=category.type,
                            parent_id=category.parent_id,
                            sort_order=category.sort_order,
                            created_at=category.created_at,
                        )
                        remote_session.add(new_category)
                    await remote_session.commit()
                print(f"   ✅ 已迁移 {category_count} 个分类")

        # 3. 迁移笔记
        print("\n📝 迁移笔记数据...")
        async with LocalSession() as local_session:
            notes = await local_session.execute(select(Note))
            notes_data = notes.scalars().all()
            note_count = len(notes_data)
            print(f"   找到 {note_count} 篇笔记")

            if note_count > 0:
                async with RemoteSession() as remote_session:
                    for note in notes_data:
                        new_note = Note(
                            id=note.id,
                            user_id=note.user_id,
                            title=note.title,
                            content=note.content,
                            category_id=note.category_id,
                            tags=note.tags,
                            is_pinned=note.is_pinned,
                            created_at=note.created_at,
                            updated_at=note.updated_at,
                        )
                        remote_session.add(new_note)
                    await remote_session.commit()
                print(f"   ✅ 已迁移 {note_count} 篇笔记")

        # 4. 迁移提示词
        print("\n🤖 迁移提示词数据...")
        async with LocalSession() as local_session:
            prompts = await local_session.execute(select(Prompt))
            prompts_data = prompts.scalars().all()
            prompt_count = len(prompts_data)
            print(f"   找到 {prompt_count} 个提示词")

            if prompt_count > 0:
                async with RemoteSession() as remote_session:
                    for prompt in prompts_data:
                        new_prompt = Prompt(
                            id=prompt.id,
                            user_id=prompt.user_id,
                            title=prompt.title,
                            description=prompt.description,
                            content=prompt.content,
                            category_id=prompt.category_id,
                            variables=prompt.variables,
                            tags=prompt.tags,
                            is_favorite=prompt.is_favorite,
                            usage_count=prompt.usage_count,
                            created_at=prompt.created_at,
                            updated_at=prompt.updated_at,
                        )
                        remote_session.add(new_prompt)
                    await remote_session.commit()
                print(f"   ✅ 已迁移 {prompt_count} 个提示词")

        # 5. 迁移提示词版本
        print("\n📦 迁移提示词版本...")
        async with LocalSession() as local_session:
            versions = await local_session.execute(select(PromptVersion))
            versions_data = versions.scalars().all()
            version_count = len(versions_data)
            print(f"   找到 {version_count} 个版本")

            if version_count > 0:
                async with RemoteSession() as remote_session:
                    for version in versions_data:
                        new_version = PromptVersion(
                            id=version.id,
                            prompt_id=version.prompt_id,
                            version_number=version.version_number,
                            title=version.title,
                            description=version.description,
                            content=version.content,
                            variables=version.variables,
                            tags=version.tags,
                            message=version.message,
                            labels=version.labels,
                            branch_name=version.branch_name,
                            created_at=version.created_at,
                        )
                        remote_session.add(new_version)
                    await remote_session.commit()
                print(f"   ✅ 已迁移 {version_count} 个版本")

        # 6. 迁移提示词预设
        print("\n⚙️  迁移提示词预设...")
        async with LocalSession() as local_session:
            presets = await local_session.execute(select(PromptPreset))
            presets_data = presets.scalars().all()
            preset_count = len(presets_data)
            print(f"   找到 {preset_count} 个预设")

            if preset_count > 0:
                async with RemoteSession() as remote_session:
                    for preset in presets_data:
                        new_preset = PromptPreset(
                            id=preset.id,
                            prompt_id=preset.prompt_id,
                            name=preset.name,
                            values=preset.values,
                            created_at=preset.created_at,
                        )
                        remote_session.add(new_preset)
                    await remote_session.commit()
                print(f"   ✅ 已迁移 {preset_count} 个预设")

        # 7. 迁移使用日志
        print("\n📊 迁移使用日志...")
        async with LocalSession() as local_session:
            logs = await local_session.execute(select(PromptUsageLog))
            logs_data = logs.scalars().all()
            log_count = len(logs_data)
            print(f"   找到 {log_count} 条日志")

            if log_count > 0:
                async with RemoteSession() as remote_session:
                    for log in logs_data:
                        new_log = PromptUsageLog(
                            id=log.id,
                            prompt_id=log.prompt_id,
                            user_id=log.user_id,
                            used_at=log.used_at,
                        )
                        remote_session.add(new_log)
                    await remote_session.commit()
                print(f"   ✅ 已迁移 {log_count} 条日志")

        print("\n" + "="*50)
        print("🎉 数据迁移完成！")
        print("="*50)

    except Exception as e:
        print(f"\n❌ 迁移过程中出错: {e}")
        raise
    finally:
        await local_engine.dispose()
        await remote_engine.dispose()


async def verify_migration():
    """验证迁移结果"""
    print("\n🔍 验证迁移数据...")

    remote_engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        connect_args={"connect_timeout": 10},
    )

    try:
        RemoteSession = async_sessionmaker(remote_engine, class_=AsyncSession, expire_on_commit=False)

        async with RemoteSession() as session:
            user_count = await session.execute(select(User))
            note_count = await session.execute(select(Note))
            category_count = await session.execute(select(Category))
            prompt_count = await session.execute(select(Prompt))

            print(f"\n远程数据库中的数据统计:")
            print(f"  👤 用户: {len(user_count.scalars().all())}")
            print(f"  📝 笔记: {len(note_count.scalars().all())}")
            print(f"  📁 分类: {len(category_count.scalars().all())}")
            print(f"  🤖 提示词: {len(prompt_count.scalars().all())}")
    except Exception as e:
        print(f"❌ 验证失败: {e}")
        raise
    finally:
        await remote_engine.dispose()


async def main():
    """主迁移流程"""
    print("🚀 ResourceHub 数据库迁移工具")
    print("=" * 50)
    print(f"源: 本地 SQLite (resourcehub.db)")
    print(f"目标: 远程 MySQL ({settings.DATABASE_URL.split('@')[1]})")
    print("=" * 50)

    try:
        # 第一步：清空远程数据库
        await clear_remote_database()

        # 第二步：在远程创建表
        await create_remote_tables()

        # 第三步：迁移数据
        await migrate_data()

        # 第四步：验证数据
        await verify_migration()

        print("\n✨ 全部完成！现在可以启动应用连接远程数据库了。")

    except Exception as e:
        print(f"\n💥 迁移失败: {e}")
        import traceback
        traceback.print_exc()
        exit(1)


if __name__ == "__main__":
    asyncio.run(main())
