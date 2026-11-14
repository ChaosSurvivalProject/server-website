"""GitHub Release 批量同步 CLI（定时批量路径，PRD §3.1「定时触发」）。

用法（在 backend/ 下执行）：
  python3 github_sync.py              # 全量扫描：遍历已发布且有合法 GitHub 仓库地址的资源
  python3 github_sync.py --resource 3 # 只同步单个资源（手动排障用）
  python3 github_sync.py --dry-run    # 只统计会扫描哪些资源，不请求 GitHub 不写库

crontab（backend/crontab → /etc/cron.d/xqly-jobs，北京时间 03:30，避开既有任务）：
  30 3 * * * root cd /app && python backend/github_sync.py >> /proc/1/fd/1 2>&1

与查询路径共用 app.resource_sync_core.sync_resource_batch（双轨口径唯一：
批量只增不改、按 Tag 判存跳过，幂等；漏跑/重跑都不会写坏数据——
重复执行最多多拉几次 GitHub API，本地已有的 Tag 全部跳过）。
本脚本是独立进程写同一个 SQLite 文件：init_db 已设 WAL + busy_timeout。

注意：**不 import app.resource_center**（那是完整 APIRouter，import 即构建全部
pydantic/fastapi 路由 schema，生产机内存紧张时 CLI 冷 import 分钟级——
staff_expire.py 注释同款教训）；只 import 纯 SQLAlchemy 的 resource_sync_core。
"""
import argparse
import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

BACKEND_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import select  # noqa: E402

from app.database import (  # noqa: E402
    Resource,
    async_session_maker,
    init_db,
)
from app.resource_sync_core import (  # noqa: E402
    GitHubNotFoundError,
    GitHubRateLimitError,
    GitHubSyncError,
    parse_github_repo,
    sync_resource_batch,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("github_sync")

_TZ = ZoneInfo("Asia/Shanghai")

# 空跑安全：单资源失败不中断整批（限流时后续必然也失败，提前停省配额）
MAX_CONSECUTIVE_FAILURES = 3


def _now_iso() -> str:
    return datetime.now(_TZ).strftime("%Y-%m-%dT%H:%M:%S")


async def main(resource_id: int | None, dry_run: bool) -> int:
    await init_db()
    now = _now_iso()
    async with async_session_maker() as session:
        stmt = select(Resource).where(
            Resource.status == "published",
            Resource.deleted_at == "",
        )
        if resource_id is not None:
            stmt = stmt.where(Resource.id == resource_id)
        stmt = stmt.order_by(Resource.id)
        resources = (await session.execute(stmt)).scalars().all()

        # 只扫有合法仓库地址的（PRD §3.1）；dry-run 只列名单，不请求 GitHub
        targets = [r for r in resources if parse_github_repo(r.github_repo_url)]
        skipped_no_repo = len(resources) - len(targets)
        logger.info(
            "%s 批量同步开始：已发布资源 %d 个，含合法 GitHub 仓库地址 %d 个（无地址跳过 %d 个）",
            now, len(resources), len(targets), skipped_no_repo,
        )
        if dry_run:
            for r in targets:
                logger.info("[dry-run] 将同步：#%d %s (%s)", r.id, r.name, r.github_repo_url)
            return 0

        added_total = skipped_total = failed = consec_fail = 0
        for r in targets:
            try:
                async with async_session_maker() as s2:  # 每资源独立事务，失败不影响其他资源
                    result = await sync_resource_batch(s2, r, now=_now_iso())
                    await s2.commit()
                added_total += result.added
                skipped_total += result.skipped
                consec_fail = 0
                for w in result.warnings:
                    logger.warning("资源 #%d %s：%s", r.id, r.name, w)
                logger.info(
                    "资源 #%d %s：新增 %d，跳过 %d（拉取 %d 条）",
                    r.id, r.name, result.added, result.skipped, result.fetched,
                )
            except GitHubRateLimitError as e:
                failed += 1
                logger.error("资源 #%d %s：%s（限流，提前结束本轮）", r.id, r.name, e)
                break
            except (GitHubNotFoundError, GitHubSyncError) as e:
                failed += 1
                consec_fail += 1
                logger.error("资源 #%d %s：同步失败：%s", r.id, r.name, e)
                if consec_fail >= MAX_CONSECUTIVE_FAILURES:
                    logger.error("连续失败 %d 次，提前结束本轮（GitHub 可能不可达）", consec_fail)
                    break

        logger.info(
            "批量同步完成：新增 %d，跳过 %d，失败 %d（共 %d 个资源）",
            added_total, skipped_total, failed, len(targets),
        )
        return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GitHub Release 批量同步（只增不改，幂等）")
    parser.add_argument("--resource", type=int, default=None, help="只同步指定资源 ID")
    parser.add_argument("--dry-run", action="store_true", help="只列出将扫描的资源，不请求 GitHub")
    args = parser.parse_args()
    sys.exit(asyncio.run(main(args.resource, args.dry_run)))
