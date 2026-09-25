"""员工名片到期检查 CLI（定时批量路径，规格 §8.4 / 落地方案 §4.5、§6.8）。

用法（在 backend/ 下执行）：
  python3 staff_expire.py              # 全表到期回写，输出刷新行数
  python3 staff_expire.py --dry-run    # 只统计将刷新的行数，不写库

crontab 每日一次（漏挂不影响核验正确性——判定权威是 valid_to，
公开验证接口查询时懒更新会兜底回写，见 app/staff.py::expire_due）：
  0 4 * * * cd /path/to/backend && /usr/bin/python3 staff_expire.py >> ../logs/staff_expire.log 2>&1

与查询路径共用同一个函数 app.staff_core.expire_due（规格 §4.5 硬规则：语义唯一；
从 staff_core 而非 app.staff import —— 后者是完整 APIRouter，import 即构建全部
pydantic/fastapi 路由 schema，生产机（122MB 内存）实测 CLI 冷 import 33s、
内存紧张时分钟级；staff_core 纯 SQLAlchemy，秒级）。
本脚本是独立进程写同一个 SQLite 文件：init_db 已设 WAL + busy_timeout。
"""
import argparse
import asyncio
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND_DIR))

from app.database import async_session_maker, init_db  # noqa: E402
from app.staff_core import STAFF_STATUS_ACTIVE, _TZ, expire_due  # noqa: E402
from datetime import datetime  # noqa: E402


async def main(dry_run: bool) -> int:
    await init_db()
    now = datetime.now(_TZ).strftime("%Y-%m-%dT%H:%M:%S")
    async with async_session_maker() as session:
        if dry_run:
            from sqlalchemy import func, select
            from app.database import Staff

            total = (
                await session.execute(
                    select(func.count())
                    .select_from(Staff)
                    .where(Staff.status == STAFF_STATUS_ACTIVE, Staff.valid_to < now)
                )
            ).scalar_one()
            print(f"[dry-run] {now} 将到期回写 {total} 条（未写库）")
            return 0
        changed = await expire_due(session)
        print(f"{now} 到期回写完成：刷新 {changed} 条")
        return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="员工名片到期检查（active 且 now > valid_to → revoked/'expired'）")
    parser.add_argument("--dry-run", action="store_true", help="只统计，不写库")
    args = parser.parse_args()
    sys.exit(asyncio.run(main(args.dry_run)))
