"""
存量笔记回填 Meilisearch 索引（一次性运维脚本，可重复执行）

用法（在 backend 目录下执行）：
    uv run python scripts/reindex_notes.py                 # 全量回填
    uv run python scripts/reindex_notes.py --dry-run       # 只统计，不写入
    uv run python scripts/reindex_notes.py --user-id 3     # 只回填指定用户
    uv run python scripts/reindex_notes.py --batch-size 500

前置条件：.env 中 MEILI_ENABLED=true 且 MEILI_URL 可达（compose 环境下为 http://search:7700）。
幂等性：按主键 id upsert，中断后直接重跑即可；不会产生重复文档。
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# 允许以 `python scripts/reindex_notes.py` 方式直接运行（补上 backend 根目录到导入路径）
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import func, select  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.database import SessionLocal, engine  # noqa: E402
from app.models.note import Note  # noqa: E402
from app.services.search_service import search_service  # noqa: E402

logger = logging.getLogger("reindex")


async def fetch_batch(last_id: int, user_id: int | None, size: int) -> list[Note]:
    """按 id 游标取一批笔记（keyset 分页，避免大偏移量扫描）"""
    async with SessionLocal() as db:
        stmt = select(Note).where(Note.id > last_id)
        if user_id is not None:
            stmt = stmt.where(Note.user_id == user_id)
        stmt = stmt.order_by(Note.id).limit(size)
        return list((await db.execute(stmt)).scalars().all())


async def count_notes(user_id: int | None) -> int:
    """待回填笔记总数"""
    async with SessionLocal() as db:
        stmt = select(func.count(Note.id))
        if user_id is not None:
            stmt = stmt.where(Note.user_id == user_id)
        return int((await db.execute(stmt)).scalar_one())


async def wait_index_ready(expected: int) -> int | None:
    """索引为异步处理，轮询等待文档数追平（最多 10 秒）"""
    for _ in range(10):
        docs = await search_service.stats()
        if docs is not None and docs >= expected:
            return docs
        await asyncio.sleep(1)
    return await search_service.stats()


async def run(args: argparse.Namespace) -> int:
    if not settings.meili_configured:
        logger.error(
            "搜索服务未启用：请在 .env 中设置 MEILI_ENABLED=true 与 MEILI_URL（当前 URL=%s）",
            settings.MEILI_URL,
        )
        return 1

    total = await count_notes(args.user_id)
    logger.info(
        "待回填笔记 %s 条（user_id=%s, batch=%s, dry_run=%s）",
        total, args.user_id or "全部", args.batch_size, args.dry_run,
    )
    if total == 0:
        return 0
    if args.dry_run:
        logger.info("dry-run 模式：未写入索引")
        return 0

    if not await search_service.ensure_index():
        logger.error("索引初始化失败，请检查 MEILI_URL / MEILI_MASTER_KEY 与网络连通性")
        return 1

    last_id = 0
    done = 0
    failed = 0
    while True:
        batch = await fetch_batch(last_id, args.user_id, args.batch_size)
        if not batch:
            break
        last_id = batch[-1].id
        if await search_service.index_notes(batch):
            done += len(batch)
        else:
            failed += len(batch)
        logger.info("进度 %s/%s（失败 %s）", done + failed, total, failed)

    # 索引异步落盘，等文档数追平后给出结论
    docs = await wait_index_ready(total if args.user_id is None else done)
    logger.info("回填完成：成功 %s 条，失败 %s 条，索引文档数 %s", done, failed, docs)

    if failed:
        logger.warning("存在失败批次，可修正网络后直接重跑（幂等）")
        return 1
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="存量笔记回填 Meilisearch 索引")
    parser.add_argument("--batch-size", type=int, default=200, help="每批写入条数（默认 200）")
    parser.add_argument("--user-id", type=int, default=None, help="仅回填指定用户的笔记")
    parser.add_argument("--dry-run", action="store_true", help="只统计数量，不写入索引")
    parser.add_argument("--verbose", action="store_true", help="输出调试日志")
    return parser.parse_args()


async def main() -> int:
    args = parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    try:
        return await run(args)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(main()))
    except KeyboardInterrupt:
        logger.warning("已被手动中断，重跑即可补齐")
        sys.exit(130)
