"""论坛模块端到端冒烟测试（临时脚本，验证 PRD §10.2b / §10.3 的关键口径）。

用独立临时库 + TestClient 跑完整闭环：
  注册两个用户 → 发帖（待审核）→ 公开列表不可见 → 管理员通过 → 公开可见
  → 点赞/收藏切换 → 顶层评论 + 两级回复 + 评论点赞 → 后台删顶层评论连带回复
  → 作者编辑重提（use_count 只扣一次、互动数据保留、resubmit 累加）
  → 管理员下架（作者编辑被 400 拦住）→ 恢复 → 硬删除级联
  → 禁言 → 发帖/评论 403 → 解禁恢复
"""
import os
import sys
import tempfile

TMP = tempfile.mkdtemp(prefix="forum-e2e-")
os.environ["ANNOUNCEMENT_DB"] = os.path.join(TMP, "test.db")
os.environ["ANNOUNCEMENT_UPLOAD_DIR"] = os.path.join(TMP, "uploads")
# 知识库要连 embedding 服务，这里关掉避免测试时卡住网络
os.environ["KB_ENABLED"] = "0"

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.auth.security import hash_password  # noqa: E402
from app.crud import _TZ  # noqa: E402
from datetime import datetime, timedelta  # noqa: E402
from sqlalchemy import select  # noqa: E402

FAILS: list[str] = []


def check(name: str, cond: bool, extra: str = "") -> None:
    if cond:
        print(f"  \033[32mPASS\033[0m {name}")
    else:
        print(f"  \033[31mFAIL\033[0m {name} {extra}")
        FAILS.append(f"{name} {extra}")


def main() -> int:
    import asyncio

    from app.database import async_session_maker, init_db, ForumTag, ForumArticle, ForumCommentLike, User
    from app import forum as fm

    async def setup():
        await init_db()
        await fm.ensure_seeded()
        async with async_session_maker() as s:
            s.add_all([
                User(username="admin@test.com", nickname="服主", password_hash=hash_password("admin1234"),
                     role="admin", status=1, create_time=datetime.now(_TZ).strftime("%Y-%m-%dT%H:%M:%S")),
                User(username="alice@test.com", nickname="爱丽丝", password_hash=hash_password("alice1234"),
                     role="user", status=1, create_time=datetime.now(_TZ).strftime("%Y-%m-%dT%H:%M:%S")),
                User(username="bob@test.com", nickname="鲍勃", password_hash=hash_password("bob12345"),
                     role="user", status=1, create_time=datetime.now(_TZ).strftime("%Y-%m-%dT%H:%M:%S")),
            ])
            await s.commit()

    asyncio.run(setup())

    with TestClient(app) as client:
        def login(u: str, p: str) -> str:
            r = client.post("/api/auth/login", json={"username": u, "password": p})
            assert r.status_code == 200, r.text
            return r.json()["data"]["token"]

        def H(tok: str) -> dict:
            return {"Authorization": f"Bearer {tok}"}

        def like_rows(cid: int) -> int:
            """直接查库读某条评论的点赞行数（验证删除连带不留孤儿数据）。"""
            async def q():
                async with async_session_maker() as s:
                    r = await s.execute(
                        select(ForumCommentLike).where(ForumCommentLike.comment_id == cid))
                    return len(r.scalars().all())
            return asyncio.run(q())

        def tag_counts() -> dict:
            """直接查库读标签 use_count（冗余计数的最终判据，不看接口回显）。"""
            async def q():
                async with async_session_maker() as s:
                    r = await s.execute(select(ForumTag))
                    return {t.name: t.use_count for t in r.scalars().all()}
            return asyncio.run(q())

        admin = login("admin@test.com", "admin1234")
        alice = login("alice@test.com", "alice1234")
        bob = login("bob@test.com", "bob12345")

        print("\n[1] 种子数据与公开只读")
        cats = client.get("/api/forum/categories").json()["data"]
        check("8 个预置板块", len(cats) == 8, str(len(cats)))
        check("前两个是系统板块", [c["code"] for c in cats[:2]] == ["home", "recommend"])
        check("系统板块标记正确", all(c["isSystem"] == 1 for c in cats[:2]))
        cfg = client.get("/api/forum/config").json()["data"]
        check("配置只下发 5 个前台键", set(cfg) == {"bannerTitle", "bannerSubtitle", "bannerImage",
                                                 "defaultSort", "searchPlaceholder"}, str(set(cfg)))
        check("打赏预留键不下发", "rewardEnabled" not in cfg)
        st = client.get("/api/forum/stats").json()["data"]
        check("初始统计全 0", st == {"articleCount": 0, "viewCount": 0, "tagCount": 0}, str(st))

        print("\n[2] 发帖（先审后发）")
        cat_id = [c["id"] for c in cats if c["code"] == "guide"][0]
        sys_cat_id = [c["id"] for c in cats if c["code"] == "home"][0]
        r = client.post("/api/forum/articles", headers=H(alice), json={
            "categoryId": cat_id, "title": "红石密码门教程",
            "content": "# 标题\n\n这是一个 **红石** 密码门教程，附图：\n\n![示例](/api/announcement/uploads/forum/202601/x.png)\n\n```java\n// code\n```\n",
            "coverUrl": "", "tags": ["红石", "建筑", "新手"]})
        check("发帖成功", r.status_code == 200, r.text)
        aid = r.json()["data"]["id"]
        check("初始状态=0 待审核", r.json()["data"]["status"] == 0)
        check("未登录不可见", client.get(f"/api/forum/articles/{aid}").status_code == 404)
        check("他人不可见", client.get(f"/api/forum/articles/{aid}", headers=H(bob)).status_code == 404)
        check("作者可见", client.get(f"/api/forum/articles/{aid}", headers=H(alice)).status_code == 200)
        check("管理员可见", client.get(f"/api/forum/articles/{aid}", headers=H(admin)).status_code == 200)
        check("系统板块被拒", client.post("/api/forum/articles", headers=H(alice), json={
            "categoryId": sys_cat_id, "title": "不该成功", "content": "x" * 20}).status_code == 400)
        check("标签超 5 个被拒", client.post("/api/forum/articles", headers=H(alice), json={
            "categoryId": cat_id, "title": "标签测试", "content": "x" * 20,
            "tags": ["a", "b", "c", "d", "e", "f"]}).status_code == 400)

        detail = client.get(f"/api/forum/articles/{aid}", headers=H(alice)).json()["data"]
        check("摘要已自动截取", detail["summary"].startswith("标题"), detail["summary"][:30])
        check("摘要剔除图片与代码", "api/announcement" not in detail["summary"] and "code" not in detail["summary"])
        check("缩略图取正文首图", detail["thumbUrl"] == "/api/announcement/uploads/forum/202601/x.png",
              detail["thumbUrl"])
        check("公开列表不含未发布", client.get("/api/forum/articles").json()["data"]["total"] == 0)

        print("\n[3] 我的文章 + 驳回 + 理由")
        mine = client.get("/api/forum/my/articles", headers=H(alice)).json()["data"]
        check("我的文章可见待审核", mine["total"] == 1 and mine["items"][0]["status"] == 0)
        r = client.put(f"/api/forum/admin/articles/{aid}/review", headers=H(admin),
                       json={"status": 2, "reviewNote": "内容太短了"})
        check("驳回成功", r.status_code == 200, r.text)
        r = client.put(f"/api/forum/admin/articles/{aid}/review", headers=H(admin), json={"status": 2})
        check("非待审核不可再审核", r.status_code == 400)
        r = client.put(f"/api/forum/admin/articles/{aid}/review", headers=H(admin),
                       json={"status": 1, "reviewNote": ""})
        check("驳回必须填理由", r.status_code == 400)
        mine = client.get("/api/forum/my/articles", headers=H(alice)).json()["data"]
        check("作者看到驳回理由", mine["items"][0].get("reviewNote") == "内容太短了",
              str(mine["items"][0].get("reviewNote")))
        adminlist = client.get("/api/forum/admin/articles", headers=H(admin)).json()["data"]["items"]
        check("管理员列表可见 reviewNote", adminlist[0].get("reviewNote") == "内容太短了",
              str(adminlist[0].get("reviewNote")))

        print("\n[3b] 被驳回的文章必须由作者重提才能再审")
        r = client.put(f"/api/forum/articles/{aid}", headers=H(alice), json={
            "categoryId": cat_id, "title": "红石密码门教程",
            "content": "# 标题\n\n这是一个 **红石** 密码门教程，附图：\n\n![示例](/api/announcement/uploads/forum/202601/x.png)\n\n```java\n// code\n```\n",
            "tags": ["红石", "建筑", "新手"]})
        check("驳回后作者可编辑重提", r.status_code == 200, r.text)
        check("重提后 resubmit_count=1", r.json()["data"]["resubmitCount"] == 1)
        check("重提后 review_note 已清空",
              client.get(f"/api/forum/articles/{aid}/edit", headers=H(alice)
                         ).json()["data"]["reviewNote"] == "")
        tc_pre = tag_counts()
        check("未发布状态下 use_count 不变（不重复扣减）",
              all(v == 0 for v in tc_pre.values()), str(tc_pre))

        print("\n[4] 审核通过 + 标签 use_count")
        check("待审核时 use_count 全 0", all(v == 0 for v in tag_counts().values()), str(tag_counts()))
        r = client.put(f"/api/forum/admin/articles/{aid}/review", headers=H(admin), json={"status": 1})
        check("通过成功", r.status_code == 200, r.text)
        tc = tag_counts()
        check("通过后 3 个标签各 +1", tc.get("红石") == 1 and tc.get("建筑") == 1 and tc.get("新手") == 1, str(tc))
        lst = client.get("/api/forum/articles").json()["data"]
        check("公开列表出现", lst["total"] == 1 and lst["items"][0]["id"] == aid)
        check("publishTime 已写入", bool(lst["items"][0]["publishTime"]))
        check("公开列表 author 为作者", lst["items"][0]["author"]["name"] == "爱丽丝")
        check("普通用户作者无徽章", lst["items"][0]["author"]["badge"] is None)
        check("公开列表不含 reviewNote", "reviewNote" not in lst["items"][0])

        print("\n[5] 点赞 / 收藏幂等切换")
        a1 = client.post(f"/api/forum/articles/{aid}/like", headers=H(alice)).json()["data"]
        check("首次点赞 +1", a1 == {"liked": True, "likeCount": 1}, str(a1))
        a2 = client.post(f"/api/forum/articles/{aid}/like", headers=H(alice)).json()["data"]
        check("再点取消", a2 == {"liked": False, "likeCount": 0}, str(a2))
        a3 = client.post(f"/api/forum/articles/{aid}/like", headers=H(alice)).json()["data"]
        client.post(f"/api/forum/articles/{aid}/like", headers=H(bob))
        d = client.get(f"/api/forum/articles/{aid}", headers=H(bob)).json()["data"]
        check("刷新后 liked 状态保持（Alice+Bob 各赞一次 = 2）",
              d["liked"] is True and d["likeCount"] == 2, str(d["likeCount"]))
        da = client.get(f"/api/forum/articles/{aid}", headers=H(alice)).json()["data"]
        check("两人互不影响", da["liked"] is True, str(da["liked"]))
        f1 = client.post(f"/api/forum/articles/{aid}/favorite", headers=H(bob)).json()["data"]
        check("收藏切换", f1 == {"favorited": True, "favoriteCount": 1}, str(f1))

        print("\n[6] 浏览量（登录后单独计数）")
        v0 = client.get(f"/api/forum/articles/{aid}").json()["data"]["viewCount"]
        client.post(f"/api/forum/articles/{aid}/view", headers=H(alice))
        client.post(f"/api/forum/articles/{aid}/view", headers=H(alice))
        v2 = client.get(f"/api/forum/articles/{aid}").json()["data"]["viewCount"]
        check("详情不计数、view 接口 +1×2", v0 == 0 and v2 == 2, f"{v0}->{v2}")

        print("\n[7] 两级评论 + 评论点赞")
        c1 = client.post(f"/api/forum/articles/{aid}/comments", headers=H(bob),
                         json={"content": "顶楼评论 <script>alert(1)</script>"}).json()["data"]
        check("顶层评论成功", c1["id"] > 0 and c1["parentId"] == 0)
        c2 = client.post(f"/api/forum/articles/{aid}/comments", headers=H(alice),
                         json={"content": "回复顶楼", "parentId": c1["id"]}).json()["data"]
        check("回复挂顶层", c2["parentId"] == c1["id"])
        c3 = client.post(f"/api/forum/articles/{aid}/comments", headers=H(bob),
                         json={"content": "回复的回复", "parentId": c1["id"],
                               "replyToUserId": c2["author"]["id"]}).json()["data"]
        check("回复的回复仍挂顶层", c3["parentId"] == c1["id"], str(c3["parentId"]))
        check("记录被回复者", c3["replyToUserId"] == c2["author"]["id"])
        r = client.post(f"/api/forum/articles/{aid}/comments", headers=H(bob),
                        json={"content": "x", "parentId": c2["id"]})
        check("拒绝第三级（parentId 指向回复）", r.status_code == 400, r.text)
        d = client.get(f"/api/forum/articles/{aid}").json()["data"]
        check("comment_count=3（顶层+回复）", d["commentCount"] == 3, str(d["commentCount"]))

        cl = client.get(f"/api/forum/articles/{aid}/comments", headers=H(bob)).json()["data"]
        check("顶层评论带 replies", cl["total"] == 1 and len(cl["items"][0]["replies"]) == 2,
              f"total={cl['total']} replies={len(cl['items'][0]['replies'])}")
        check("回复按正序", [r["id"] for r in cl["items"][0]["replies"]] == [c2["id"], c3["id"]])
        check("回复带 replyToName", cl["items"][0]["replies"][1]["replyToName"] == "爱丽丝",
              str(cl["items"][0]["replies"][1].get("replyToName")))
        check("回复不再嵌套 replies", "replies" not in cl["items"][0]["replies"][0])
        check("匿名 liked 恒 false",
              all(c["liked"] is False for c in client.get(f"/api/forum/articles/{aid}/comments").json()["data"]["items"]))

        lk = client.post(f"/api/forum/comments/{c3['id']}/like", headers=H(alice)).json()["data"]
        check("评论点赞 +1", lk == {"liked": True, "likeCount": 1}, str(lk))
        lk2 = client.post(f"/api/forum/comments/{c3['id']}/like", headers=H(alice)).json()["data"]
        check("评论点赞取消", lk2 == {"liked": False, "likeCount": 0}, str(lk2))
        client.post(f"/api/forum/comments/{c3['id']}/like", headers=H(alice))  # 再赞一次
        cl = client.get(f"/api/forum/articles/{aid}/comments", headers=H(alice)).json()["data"]
        reply2 = [x for x in cl["items"][0]["replies"] if x["id"] == c3["id"]][0]
        check("回复已赞状态保持", reply2["liked"] is True and reply2["likeCount"] == 1, str(reply2["likeCount"]))
        cl2 = client.get(f"/api/forum/articles/{aid}/comments", headers=H(bob)).json()["data"]
        check("他人在同一回复上 liked=false", [x for x in cl2["items"][0]["replies"]
              if x["id"] == c3["id"]][0]["liked"] is False)

        print("\n[8] 越权与不可见性")
        check("非作者编辑回填 404",
              client.get(f"/api/forum/articles/{aid}/edit", headers=H(bob)).status_code == 404)
        check("非作者 PUT 404",
              client.put(f"/api/forum/articles/{aid}", headers=H(bob), json={
                  "categoryId": cat_id, "title": "劫持", "content": "y" * 20}).status_code == 404)
        check("未登录编辑回填 401",
              client.get(f"/api/forum/articles/{aid}/edit").status_code == 401)
        check("无 token 调 admin 401", client.get("/api/forum/admin/articles").status_code == 401)
        check("普通用户调 admin 403", client.get("/api/forum/admin/articles", headers=H(alice)).status_code == 403)

        print("\n[9] 作者编辑重提（§10.2b 专项）")
        before = client.get(f"/api/forum/articles/{aid}", headers=H(alice)).json()["data"]
        ed = client.get(f"/api/forum/articles/{aid}/edit", headers=H(alice)).json()["data"]
        check("编辑回填含标签", ed["tags"] == ["红石", "建筑", "新手"], str(ed["tags"]))
        check("回填 resubmitCount（[3b] 已重提过一次）", ed["resubmitCount"] == 1, str(ed["resubmitCount"]))
        r = client.put(f"/api/forum/articles/{aid}", headers=H(alice), json={
            "categoryId": cat_id, "title": "红石密码门教程（修订版）",
            "content": "修订后的正文内容，足够长度通过校验。", "tags": ["红石", "建筑"]})
        check("编辑保存成功", r.status_code == 200, r.text)
        check("resubmit_count 累加到 2", r.json()["data"]["resubmitCount"] == 2, str(r.json()["data"]))
        check("编辑后退出公开列表", client.get("/api/forum/articles").json()["data"]["total"] == 0)
        ed2 = client.get(f"/api/forum/articles/{aid}/edit", headers=H(alice)).json()["data"]
        check("状态回到 0 待审核", ed2["status"] == 0)
        check("publish_time 已清空", ed2["status"] == 0 and client.get(
            f"/api/forum/articles/{aid}", headers=H(alice)).json()["data"]["publishTime"] == "")
        check("review_note 已清空", ed2["reviewNote"] == "", repr(ed2["reviewNote"]))
        # 不变量：use_count = 被 status=1 文章引用的数量。文章退出已发布且摘掉「新手」，
        # 三个标签都不再有已发布文章引用 → 全部归零（不是"只扣一次"的叠加）
        tc = tag_counts()
        check("文章退出已发布后三个标签全部归零", all(v == 0 for v in tc.values()), str(tc))
        d = client.get(f"/api/forum/articles/{aid}", headers=H(alice)).json()["data"]
        check("浏览量保留", d["viewCount"] == before["viewCount"], f'{d["viewCount"]} vs {before["viewCount"]}')
        check("点赞保留", d["likeCount"] == before["likeCount"])
        check("收藏保留", d["favoriteCount"] == before["favoriteCount"])
        check("评论保留", d["commentCount"] == before["commentCount"] == 3, str(d["commentCount"]))
        check("摘要重算", d["summary"] == "修订后的正文内容，足够长度通过校验。", d["summary"])

        print("\n[10] 反复编辑 use_count 不累计扣减")
        for _ in range(2):
            client.put(f"/api/forum/articles/{aid}", headers=H(alice), json={
                "categoryId": cat_id, "title": "红石密码门教程（修订版）",
                "content": "修订后的正文内容，足够长度通过校验。", "tags": ["红石", "建筑"]})
        tc = tag_counts()
        check("反复编辑不产生累计扣减（仍全 0）", all(v == 0 for v in tc.values()), str(tc))
        ed3 = client.get(f"/api/forum/articles/{aid}/edit", headers=H(alice)).json()["data"]
        check("resubmit_count 累加到 4", ed3["resubmitCount"] == 4, str(ed3["resubmitCount"]))

        print("\n[11] 重新通过后 use_count 回位")
        client.put(f"/api/forum/admin/articles/{aid}/review", headers=H(admin), json={"status": 1})
        tc = tag_counts()
        check("重新通过后 红石/建筑 各回到 1、新手 仍 0（已被移除）",
              tc.get("红石") == 1 and tc.get("建筑") == 1 and tc.get("新手") == 0, str(tc))
        lst = client.get("/api/forum/articles").json()["data"]
        check("重新出现在列表", lst["total"] == 1)
        check("评论数据仍在", client.get(f"/api/forum/articles/{aid}/comments").json()["data"]["total"] == 1)

        print("\n[12] 管理员下架 / 恢复")
        r = client.post(f"/api/forum/admin/articles/{aid}/offline", headers=H(admin),
                        json={"reason": "内容违规"})
        check("下架成功", r.status_code == 200, r.text)
        check("下架后公开不可见", client.get(f"/api/forum/articles/{aid}").status_code == 404)
        check("作者仍可见", client.get(f"/api/forum/articles/{aid}", headers=H(alice)).status_code == 200)
        tc = tag_counts()
        check("下架后 use_count -1", tc.get("红石") == 0, str(tc))
        r = client.put(f"/api/forum/articles/{aid}", headers=H(alice), json={
            "categoryId": cat_id, "title": "绕过下架", "content": "试图绕过管理员下架的内容。"})
        check("管理员下架后作者编辑被 400 拦", r.status_code == 400, str(r.status_code))
        check("提示文案正确", "管理员下架" in r.json().get("detail", ""), r.text)
        r = client.get(f"/api/forum/articles/{aid}/edit", headers=H(alice))
        check("编辑回填也被 400 拦", r.status_code == 400, str(r.status_code))
        my = client.get("/api/forum/my/articles", headers=H(alice)).json()["data"]
        check("我的文章显示下架原因", my["items"][0]["removeBy"] == "admin"
              and my["items"][0]["reviewNote"] == "内容违规", str(my["items"][0]))
        r = client.post(f"/api/forum/admin/articles/{aid}/restore", headers=H(admin))
        check("恢复成功", r.status_code == 200, r.text)
        check("恢复后重新公开", client.get(f"/api/forum/articles/{aid}").status_code == 200)
        check("恢复后 removeBy 清空",
              client.get(f"/api/forum/articles/{aid}", headers=H(alice)).json()["data"]["removeBy"] == "")

        print("\n[13] 作者自删 → 可编辑重提")
        r = client.delete(f"/api/forum/articles/{aid}", headers=H(alice))
        check("自删成功", r.status_code == 200, r.text)
        check("自删后公开不可见", client.get(f"/api/forum/articles/{aid}").status_code == 404)
        ed4 = client.get(f"/api/forum/articles/{aid}/edit", headers=H(alice))
        check("作者自删的可编辑重提", ed4.status_code == 200, str(ed4.status_code))
        client.put(f"/api/forum/articles/{aid}", headers=H(alice), json={
            "categoryId": cat_id, "title": "重提的帖子", "content": "自删之后又重新提交的内容。"})
        check("重提后回到待审核",
              client.get(f"/api/forum/articles/{aid}", headers=H(alice)).json()["data"]["status"] == 0)

        print("\n[14] 置顶 / 加精 / 推荐 / 排序 / 搜索 / 标签过滤")
        client.put(f"/api/forum/admin/articles/{aid}/review", headers=H(admin), json={"status": 1})
        r2 = client.post("/api/forum/articles", headers=H(bob), json={
            "categoryId": cat_id, "title": "第二个帖子：红石与建筑", "content": "bob 发的第二篇正文内容。",
            "tags": ["红石"]})
        aid2 = r2.json()["data"]["id"]
        client.put(f"/api/forum/admin/articles/{aid2}/review", headers=H(admin), json={"status": 1})
        client.post(f"/api/forum/articles/{aid}/view", headers=H(bob))
        client.post(f"/api/forum/articles/{aid}/view", headers=H(bob))
        client.post(f"/api/forum/articles/{aid2}/view", headers=H(bob))
        lst = client.get("/api/forum/articles", params={"sort": "views"}).json()["data"]
        check("按浏览量排序：aid(2) > aid2(1)", [i["id"] for i in lst["items"]] == [aid, aid2],
              str([i["id"] for i in lst["items"]]))
        client.post(f"/api/forum/admin/articles/{aid2}/top", headers=H(admin))
        lst = client.get("/api/forum/articles", params={"sort": "views"}).json()["data"]
        check("置顶帖恒在最前", lst["items"][0]["id"] == aid2, str([i["id"] for i in lst["items"]]))
        client.post(f"/api/forum/admin/articles/{aid2}/feature", headers=H(admin))
        rec = client.get("/api/forum/articles", params={"category": "recommend"}).json()["data"]
        check("推荐=置顶∪加精", rec["total"] == 1 and rec["items"][0]["id"] == aid2, str(rec["total"]))
        s = client.get("/api/forum/articles", params={"q": "红石与建筑"}).json()["data"]
        check("标题+摘要搜索命中", s["total"] == 1 and s["items"][0]["id"] == aid2, str(s["total"]))
        s = client.get("/api/forum/articles", params={"q": "鲍勃"}).json()["data"]
        check("搜索不匹配作者名（§8-D3 只搜标题+摘要）", s["total"] == 0, str(s["total"]))
        s = client.get("/api/forum/articles", params={"q": "不存在的词"}).json()["data"]
        check("搜索无结果", s["total"] == 0)
        s = client.get("/api/forum/articles", params={"tag": "红石"}).json()["data"]
        # [13] 作者重提时未带标签，aid 已无标签；红石只在 aid2 上
        check("标签过滤只命中 aid2", s["total"] == 1 and s["items"][0]["id"] == aid2, str(s["total"]))
        s = client.get("/api/forum/articles", params={"category": "chat"}).json()["data"]
        check("空板块返回 0", s["total"] == 0)
        s = client.get("/api/forum/articles", params={"category": "nonexist"}).json()["data"]
        check("不存在的板块 code 返回空", s["total"] == 0)
        hot = client.get("/api/forum/tags/hot").json()["data"]
        check("热门标签返回", len(hot) >= 1 and hot[0]["name"] == "红石", str([t["name"] for t in hot]))
        st = client.get("/api/forum/stats").json()["data"]
        check("统计：2 篇文章", st["articleCount"] == 2, str(st))
        check("统计：标签去重 1 个", st["tagCount"] == 1, str(st))

        print("\n[15] 后台评论抽屉与级联删除")
        cl = client.get(f"/api/forum/admin/articles/{aid}/comments", headers=H(admin)).json()["data"]
        check("抽屉含顶层+回复", len(cl) == 1 and len(cl[0]["replies"]) == 2, str(len(cl[0]["replies"])))
        # 先给被删的回复 c2 点一个赞，才能验证"删评论会连带清掉它的点赞行"
        client.post(f"/api/forum/comments/{c2['id']}/like", headers=H(alice))
        check("被删回复已有 1 条点赞行", (like_rows(c2["id"])) == 1)
        r = client.delete(f"/api/forum/admin/comments/{c2['id']}", headers=H(admin))
        check("删单条回复只减 1", r.status_code == 200 and r.json()["data"]["replyCount"] == 0, r.text)
        d = client.get(f"/api/forum/articles/{aid}", headers=H(alice)).json()["data"]
        check("comment_count 3→2", d["commentCount"] == 2, str(d["commentCount"]))

        check("删回复清掉其点赞行（无孤儿）", (like_rows(c2["id"])) == 0)
        check("未删的兄弟回复点赞行不受影响", (like_rows(c3["id"])) == 1)
        # 顶层评论（此时已只剩 1 条回复）
        r = client.delete(f"/api/forum/admin/comments/{c1['id']}", headers=H(admin))
        check("删顶层成功", r.status_code == 200, r.text)
        check("顶层删除连带回复数=1", r.json()["data"]["replyCount"] == 1, r.text)
        d = client.get(f"/api/forum/articles/{aid}", headers=H(alice)).json()["data"]
        check("comment_count 2→0", d["commentCount"] == 0, str(d["commentCount"]))
        cl = client.get(f"/api/forum/articles/{aid}/comments").json()["data"]
        check("前台评论已清空", cl["total"] == 0)
        check("连带回复的点赞行也一并清掉", (like_rows(c3["id"])) == 0,
              str((like_rows(c3["id"]))))
        acl = client.get(f"/api/forum/admin/articles/{aid}/comments", headers=H(admin)).json()["data"]
        check("后台抽屉仍能列出已删除评论（含逐条删与连带删，共 2 条回复）",
              len(acl) == 1 and len(acl[0]["replies"]) == 2
              and all(c["status"] == 2 for c in [acl[0], *acl[0]["replies"]]), str(acl))
        check("已删除评论的 likeCount 归零（避免后台显示过期数字）",
              all(c["likeCount"] == 0 for c in [acl[0], *acl[0]["replies"]]),
              str([c["likeCount"] for c in acl[0]["replies"]]))

        print("\n[16] 后台改属性：状态不变")
        before_status = client.get(f"/api/forum/articles/{aid}", headers=H(alice)).json()["data"]["status"]
        r = client.put(f"/api/forum/admin/articles/{aid}", headers=H(admin), json={
            "title": "管理员改过的标题", "tags": ["红石", "教程"]})
        check("后台改属性成功", r.status_code == 200, r.text)
        after = client.get(f"/api/forum/articles/{aid}", headers=H(alice)).json()["data"]
        check("状态保持已发布不被踢回待审核", after["status"] == before_status == 1, str(after["status"]))
        check("标题已改", after["title"] == "管理员改过的标题")
        check("新标签已挂", [t["name"] for t in after["tags"]] == ["红石", "教程"], str(after["tags"]))
        r = client.put(f"/api/forum/admin/articles/{aid}", headers=H(admin), json={"categoryId": sys_cat_id})
        check("后台也不能归到系统板块", r.status_code == 400)

        print("\n[17] 板块 / 标签管理")
        r = client.post("/api/forum/admin/categories", headers=H(admin),
                        json={"name": "新板块", "code": "newbie", "color": "#123456", "sortOrder": 9})
        check("新增板块", r.status_code == 200, r.text)
        new_cat = r.json()["data"]["id"]
        check("code 重复被拒", client.post("/api/forum/admin/categories", headers=H(admin),
                                    json={"name": "x", "code": "newbie", "color": "#123456", "sortOrder": 9}).status_code == 400)
        check("非法颜色被拒", client.post("/api/forum/admin/categories", headers=H(admin),
                                   json={"name": "y", "code": "yyy", "color": "red", "sortOrder": 9}).status_code == 400)
        allcats = {c["id"]: c for c in client.get("/api/forum/admin/categories", headers=H(admin)).json()["data"]}
        check("后台板块列表含隐藏", len(allcats) == 9, str(len(allcats)))
        sys_cat = [c for c in allcats.values() if c["isSystem"] == 1][0]
        check("系统板块不可删",
              client.delete(f"/api/forum/admin/categories/{sys_cat['id']}", headers=H(admin)).status_code == 400)
        check("系统板块不可改名",
              client.put(f"/api/forum/admin/categories/{sys_cat['id']}", headers=H(admin),
                         json={"name": "新名字"}).status_code == 400)
        check("系统板块不可隐藏",
              client.put(f"/api/forum/admin/categories/{sys_cat['id']}", headers=H(admin),
                         json={"isHidden": 1}).status_code == 400)
        # 该板块有 2 篇已发布
        r = client.delete(f"/api/forum/admin/categories/{cat_id}", headers=H(admin))
        check("有文章的板块删除被拦", r.status_code == 400 and "篇" in r.json()["detail"], r.text)
        check("无文章板块可删",
              client.delete(f"/api/forum/admin/categories/{new_cat}", headers=H(admin)).status_code == 200)
        check("隐藏的板块不出现在前台", client.get("/api/forum/categories").json()["data"][0]["isHidden"] == 0)

        tags = {t["id"]: t for t in client.get("/api/forum/admin/tags", headers=H(admin)).json()["data"]}
        redstone = [t for t in tags.values() if t["name"] == "红石"][0]
        tutorial = [t for t in tags.values() if t["name"] == "教程"][0]
        newbie = [t for t in tags.values() if t["name"] == "新手"][0]
        r = client.put(f"/api/forum/admin/tags/{redstone['id']}", headers=H(admin), json={"name": "红石机制"})
        check("标签重命名", r.status_code == 200 and r.json()["data"]["name"] == "红石机制", r.text)
        r = client.post(f"/api/forum/admin/tags/{newbie['id']}/merge", headers=H(admin),
                        json={"targetTagId": tutorial["id"]})
        check("标签合并成功", r.status_code == 200, r.text)
        merged_now = {t["id"]: t for t in client.get("/api/forum/admin/tags", headers=H(admin)).json()["data"]}
        check("合并后目标标签 use_count 重算（新手 0 篇 → 仍为 1）",
              merged_now[tutorial["id"]]["useCount"] == 1, str(merged_now[tutorial["id"]]["useCount"]))
        merged = {t["name"] for t in client.get("/api/forum/admin/tags", headers=H(admin)).json()["data"]}
        check("源标签已消失", "新手" not in merged, str(merged))
        r = client.post(f"/api/forum/admin/tags/{tutorial['id']}/merge", headers=H(admin),
                        json={"targetTagId": tutorial["id"]})
        check("不能合并到自身", r.status_code == 400)
        usersrc = client.get("/api/forum/admin/tags", headers=H(admin), params={"source": "user"}).json()["data"]
        check("来源筛选可用", all(t["source"] == "user" for t in usersrc), str(len(usersrc)))

        print("\n[18] 社区配置")
        r = client.put("/api/forum/admin/config", headers=H(admin), json={
            "bannerTitle": "自定义标题", "searchPlaceholder": "找帖…", "defaultSort": "views"})
        check("配置保存成功", r.status_code == 200, r.text)
        pub = client.get("/api/forum/config").json()["data"]
        check("前台即时生效", pub["bannerTitle"] == "自定义标题" and pub["searchPlaceholder"] == "找帖…"
              and pub["defaultSort"] == "views", str(pub))
        check("非法 defaultSort 被拒", client.put("/api/forum/admin/config", headers=H(admin),
                                     json={"defaultSort": "nope"}).status_code == 400)
        adm = client.get("/api/forum/admin/config", headers=H(admin)).json()["data"]
        check("后台可读到打赏预留键", adm.get("rewardEnabled") == "0" and adm.get("rewardPresets") == "1,5,10",
              str(adm))
        check("封面图库可读", isinstance(client.get("/api/forum/admin/covers", headers=H(admin)).json()["data"], list))

        print("\n[19] 禁言 / 解禁")
        until = (datetime.now(_TZ) + timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%S")
        r = client.put("/api/auth/admin/users/2/mute", headers=H(admin), json={"muteUntil": until})
        check("禁言成功", r.status_code == 200 and r.json()["data"]["muteUntil"] == until, r.text)
        check("禁言后仍可登录浏览", client.get("/api/forum/categories").status_code == 200)
        r = client.post("/api/forum/articles", headers=H(alice), json={
            "categoryId": cat_id, "title": "禁言期间发帖", "content": "禁言期间不该成功的内容。"})
        check("禁言后发帖 403", r.status_code == 403, str(r.status_code))
        check("禁言提示明确", "禁言" in r.json().get("detail", ""), r.text)
        r = client.post(f"/api/forum/articles/{aid}/comments", headers=H(alice), json={"content": "禁言期间评论"})
        check("禁言后评论 403", r.status_code == 403)
        check("禁言后点赞仍可用（不属于写发言）",
              client.post(f"/api/forum/articles/{aid}/like", headers=H(alice)).status_code == 200)
        r = client.put("/api/auth/admin/users/2/mute", headers=H(admin), json={"muteUntil": ""})
        check("解禁成功", r.status_code == 200 and r.json()["data"]["muteUntil"] == "", r.text)
        check("解禁后发帖恢复", client.post("/api/forum/articles", headers=H(alice), json={
            "categoryId": cat_id, "title": "解禁后发帖", "content": "解禁之后就能正常发帖了。"}).status_code == 200)
        check("禁言时间格式校验", client.put("/api/auth/admin/users/2/mute", headers=H(admin),
                                   json={"muteUntil": "2027/01/01"}).status_code == 400)

        print("\n[20] 用户论坛数据 + 硬删除级联")
        us = client.get("/api/forum/admin/user-stats/2", headers=H(admin)).json()["data"]
        check("发帖数=已发布数", us["postCount"] == 1, str(us["postCount"]))
        check("粉丝数恒 0", us["followerCount"] == 0)
        check("最近 5 篇", len(us["recentPosts"]) <= 5)
        check("管理员查他人数据也返回", us["author"]["name"] == "爱丽丝")

        async def orphan_check() -> tuple:
            async with async_session_maker() as s:
                from app.database import ForumComment, ForumArticleLike, ForumArticleFavorite, ForumArticleTag
                cid = (await s.execute(select(ForumComment.id).where(ForumComment.article_id == aid))).scalars().all()
                return (len(cid), len((await s.execute(select(ForumArticleLike))).scalars().all()),
                        len((await s.execute(select(ForumArticleFavorite))).scalars().all()),
                        len((await s.execute(select(ForumArticleTag).where(
                            ForumArticleTag.article_id == aid))).scalars().all()))

        r = client.delete(f"/api/forum/admin/articles/{aid}", headers=H(admin))
        check("硬删除成功", r.status_code == 200, r.text)
        check("级联无孤儿（评论/点赞/收藏/标签关联全 0）",
              asyncio.run(orphan_check()) == (0, 0, 0, 0), str(asyncio.run(orphan_check())))
        check("删除后详情 404", client.get(f"/api/forum/articles/{aid}").status_code == 404)
        tc = tag_counts()
        check("删除后该文标签归零（红石机制仍被 aid2 引用故为 1）",
              tc.get("红石机制") == 1 and tc.get("建筑") == 0 and tc.get("教程") == 0, str(tc))

        print("\n[20b] 公开作者统计 / 浏览量回传 / 禁言列表字段")
        # Alice 的文章已在 [20] 硬删除，Bob 还留着 aid2
        us_bob = client.get("/api/forum/users/3/stats").json()["data"]
        check("匿名可查公开作者统计（有已发布文章）", us_bob["postCount"] >= 1, str(us_bob))
        us = client.get("/api/forum/users/2/stats").json()["data"]
        check("无已发布文章时计数为 0（不报错）", us["postCount"] == 0, str(us))
        check("公开统计不泄漏私有字段",
              set(us) == {"author", "postCount", "likeCount", "followerCount"}, str(set(us)))
        check("公开统计粉丝恒 0", us["followerCount"] == 0)
        check("查不存在的用户 404", client.get("/api/forum/users/99999/stats").status_code == 404)
        v0 = client.get(f"/api/forum/articles/{aid2}").json()["data"]["viewCount"]
        vr = client.post(f"/api/forum/articles/{aid2}/view", headers=H(bob)).json()["data"]
        check("view 接口回传新计数", vr["viewCount"] == v0 + 1, str(vr))
        check("未发布帖不能计浏览量",
              client.post(f"/api/forum/articles/{aid2}/view", headers=H(bob)).status_code == 200)
        me = client.get("/api/auth/me", headers=H(alice)).json()["data"]
        check("/auth/me 下发 id（前端判断是否本人依赖它）", isinstance(me.get("id"), int), str(me))
        lg = client.post("/api/auth/login", json={"username": "alice@test.com", "password": "alice1234"}).json()["data"]
        check("登录响应也下发 id", lg.get("id") == me["id"], str(lg.get("id")))
        ulist = client.get("/api/auth/admin/users", headers=H(admin)).json()["data"]["items"]
        check("用户列表含 muteUntil 字段", all("muteUntil" in u for u in ulist), str(ulist[0].keys()))

        print("\n[21] 作者其他帖子")
        aid3 = client.post("/api/forum/articles", headers=H(alice), json={
            "categoryId": cat_id, "title": "bob 视角的第一篇",
            "content": "第一篇已发布用于测试作者卡。"}).json()["data"]["id"]
        client.put(f"/api/forum/admin/articles/{aid3}/review", headers=H(admin), json={"status": 1})
        ap = client.get(f"/api/forum/articles/{aid3}/author-posts").json()["data"]
        check("作者其他帖子（当前帖排除）", all(p["id"] != aid3 for p in ap), str(ap))
        aid4 = client.post("/api/forum/articles", headers=H(alice), json={
            "categoryId": cat_id, "title": "bob 视角的第二篇",
            "content": "第二篇已发布用于测试作者卡。"}).json()["data"]["id"]
        client.put(f"/api/forum/admin/articles/{aid4}/review", headers=H(admin), json={"status": 1})
        ap = client.get(f"/api/forum/articles/{aid3}/author-posts").json()["data"]
        check("返回其它 1 篇", len(ap) == 1 and ap[0]["id"] == aid4, str(ap))

    print("\n" + "=" * 64)
    if FAILS:
        print(f"\033[31m{len(FAILS)} 项失败：\033[0m")
        for f in FAILS:
            print("  -", f)
        return 1
    print("\033[32m全部通过\033[0m")
    return 0


if __name__ == "__main__":
    sys.exit(main())
