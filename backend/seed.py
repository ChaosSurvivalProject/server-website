"""Seed the messages database with sample data."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.database import init_db, async_session_maker
from app.crud import create_message
from app.schemas import MessageCreate


SAMPLE_DATA = [
    {
        "type": "system_announcement",
        "category": "system",
        "title": "🎉 星穹旅驿服务器正式开服！",
        "content": "<p>亲爱的冒险家：</p><p>星穹旅驿服务器已于 <strong>2025年1月1日</strong> 正式开服！服务器版本为 <strong>1.21</strong>，支持 Java 版本 1.18 - 1.21.11。</p><p>欢迎各位冒险家来到星穹旅驿，开启你的奇幻冒险之旅！</p>",
        "is_broadcast": 1,
        "status": 1,
    },
    {
        "type": "system_announcement",
        "category": "system",
        "title": "🔧 服务器维护通知（2025年1月15日）",
        "content": "<p>各位冒险家：</p><p>为了提供更好的游戏体验，服务器将于 <strong>2025年1月15日 02:00 - 06:00</strong> 进行例行维护。</p><p>维护期间服务器将暂时关闭，请各位提前下线，以免数据丢失。</p><p>维护结束后将推出新版本内容，敬请期待！</p>",
        "is_broadcast": 1,
        "status": 1,
    },
    {
        "type": "system_announcement",
        "category": "system",
        "title": "🏆 新年活动：登录即领大奖",
        "content": "<p>新年活动来啦！</p><p>活动时间：<strong>2025年1月1日 - 1月7日</strong></p><p>活动内容：</p><ul><li>每日登录即可领取新年礼包</li><li>累计登录7天可获得限定坐骑</li><li>参与Boss挑战可赢取稀有材料</li></ul><p>快来参与吧！</p>",
        "is_broadcast": 1,
        "status": 1,
    },
    {
        "type": "system_announcement",
        "category": "system",
        "title": "📋 服务器规则（草稿）",
        "content": "<p>服务器规则草案，待审核发布。</p>",
        "is_broadcast": 1,
        "status": 0,
    },
]


async def main():
    await init_db()
    async with async_session_maker() as session:
        for item in SAMPLE_DATA:
            await create_message(session, MessageCreate(**item))
        print(f"✅ 已插入 {len(SAMPLE_DATA)} 条站内信数据")


if __name__ == "__main__":
    asyncio.run(main())
