"""论坛回收站超期清理 CLI（定时批量路径，回收站 PRD §5.3 / §1.3）。

用法（在 backend/ 下执行）：
  python3 forum_purge.py              # 物理清除超 30 天的回收站帖，输出清理条数
  python3 forum_purge.py --dry-run    # 只统计将清除的条数，不写库

crontab 每日一次（漏挂不影响正确性——判定权威是 deleted_at，恢复接口自校验 +
回收站列表自过滤，超期帖用户看不到也恢复不了，数据只是多留几天，与员工名片
valid_to 同款口径；见 for-deploy/crontab）：
  0 5 * * * cd /path/to/backend && /usr/bin/python3 forum_purge.py >> ../logs/forum_purge.log 2>&1

与"作者彻底删除"共用 app.forum_core.purge_due → cascade_delete_article（语义唯一）。
刻意从 forum_core 而非 app.forum import：后者顶部是完整 APIRouter，import 即构建
全部 pydantic/fastapi 路由 schema，生产机实测 CLI 冷 import 33s 起——
与 staff_expire.py 走 app/staff_core.py 是同一条理由，见 forum_core.py 头注释。
本脚本是独立进程写同一个 SQLite 文件：database.init_db 已设 WAL + busy_timeout
（PRAGMA 挂引擎 "connect" 事件，每条新连接都有）。
"""
import argparse
import asyncio
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND_DIR))

from app.database import async_session_maker, init_db  # noqa: E402
from app.forum_core import RECYCLE_DAYS, _now_iso, purge_due  # noqa: E402


async def main(dry_run: bool) -> int:
    await init_db()
    now = _now_iso()
    async with async_session_maker() as session:
        if dry_run:
            from app.forum_core import due_recycle_ids

            ids = await due_recycle_ids(session, now)
            print(
                f"[dry-run] {now} 将物理清除超 {RECYCLE_DAYS} 天的回收站帖 {len(ids)} 条"
                f"（ids={ids}，未写库）"
            )
            return 0
        changed, ids = await purge_due(session, now=now)
        print(f"{now} 回收站超期清理完成：物理清除 {changed} 条（ids={ids}）")
        return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=(
            f"论坛回收站超期清理：status=4 且 deleted_at 早于 {RECYCLE_DAYS} 天前 → "
            "物理删除 + 级联（不可恢复）"
        )
    )
    parser.add_argument("--dry-run", action="store_true", help="只统计，不写库")
    args = parser.parse_args()
    sys.exit(asyncio.run(main(args.dry_run)))
