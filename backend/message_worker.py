"""站内信异步任务 worker（CLI，供 crontab 每分钟轮询）。

实施依据：docs/站内信/站内信功能PRD.md §10。

定时触发（每分钟）
    ↓
SELECT * FROM tasks WHERE status = 0 ORDER BY created_at ASC LIMIT 10
    ↓
for task in tasks:
    UPDATE tasks SET status = 1 WHERE id = task.id
    try:
        process_task(task)
        UPDATE tasks SET status = 2 WHERE id = task.id
    except Exception as e:
        UPDATE tasks SET status = 3, error_message = e WHERE id = task.id

生产 crontab 条目：
    * * * * * /usr/bin/docker exec announcement-backend python backend/message_worker.py >> /var/log/message_worker.log 2>&1
"""
import json
import logging
import sys
from pathlib import Path

# 允许直接运行脚本时找到 backend 包
sys.path.insert(0, str(Path(__file__).resolve().parent))

from sqlalchemy.ext.asyncio import async_sessionmaker

from app.database import engine, async_session_maker
from app.crud import get_pending_tasks, update_task_status, _now_iso
from app.messages import process_task

logger = logging.getLogger("message_worker")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


async def run_once(limit: int = 10) -> None:
    """单次轮询处理待处理任务。"""
    async with async_session_maker() as session:
        tasks = await get_pending_tasks(session, limit=limit)
        if not tasks:
            logger.info("无待处理任务")
            return

        logger.info("获取 %s 条待处理任务", len(tasks))
        for task in tasks:
            logger.info("处理任务 id=%s type=%s", task.id, task.type)
            await update_task_status(session, task.id, 1)  # processing
            try:
                await process_task(session, task)
                await update_task_status(session, task.id, 2)  # done
                logger.info("任务 id=%s 处理完成", task.id)
            except Exception as e:
                await update_task_status(session, task.id, 3, error_message=str(e))
                logger.error("任务 id=%s 处理失败: %s", task.id, e)


async def main():
    await run_once()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
