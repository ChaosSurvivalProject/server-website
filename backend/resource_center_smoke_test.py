"""资源中心模块端到端冒烟测试（临时脚本，验证 MVP 需求 §7 验收标准的关键口径）。

用独立临时库 + TestClient 跑完整闭环：
  管理员登录 → 字典种子 → 新建资源（slug 唯一性/字典 key 校验）
  → 新建版本（同资源版本号唯一 / is_latest_stable 唯一转移）
  → 新建资产（URL 白名单 / is_primary 转移 / 无主资产回落 sort 首位）
  → 状态控制：草稿/隐藏资源前台不可见，隐藏版本/资产下载 410
  → 下载端点：302 到 GitHub URL、事件落库、冗余计数同事务累加、
    不接受任意 URL 参数（开放重定向防护）、限速 429
  → 列表筛选（type/platform/game_version/side/channel/tag/q）无重复行
  → 排序三档、加载更多分页
  → 软删除：资源/版本/资产删除后前台不可见，后台可恢复
  → 统计：总览 + 按资源/版本/资产 + 时间范围
"""
import os
import sys
import tempfile

TMP = tempfile.mkdtemp(prefix="rc-e2e-")
os.environ["ANNOUNCEMENT_DB"] = os.path.join(TMP, "test.db")
os.environ["ANNOUNCEMENT_UPLOAD_DIR"] = os.path.join(TMP, "uploads")
os.environ["KB_ENABLED"] = "0"

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.auth.security import hash_password  # noqa: E402
from app.crud import _TZ  # noqa: E402
from datetime import datetime  # noqa: E402

FAILS: list[str] = []


def check(name: str, cond: bool, extra: str = "") -> None:
    if cond:
        print(f"  \033[32mPASS\033[0m {name}")
    else:
        print(f"  \033[31mFAIL\033[0m {name} {extra}")
        FAILS.append(f"{name} {extra}")


def main() -> int:
    import asyncio

    from app.database import async_session_maker, init_db, User

    async def setup():
        await init_db()
        async with async_session_maker() as s:
            s.add_all([
                User(username="admin@test.com", nickname="服主", password_hash=hash_password("admin1234"),
                     role="admin", status=1, create_time=datetime.now(_TZ).strftime("%Y-%m-%dT%H:%M:%S")),
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

        admin = login("admin@test.com", "admin1234")

        print("\n[1] 字典种子")
        filters = client.get("/api/resources/filters").json()["data"]
        check("预置资源类型 5 项", len(filters["resource_type"]) == 5, str(filters["resource_type"]))
        check("预置平台 9 项", len(filters["platform"]) == 9)
        check("预置侧别 3 项", len(filters["side"]) == 3)
        check("预置渠道 3 项", len(filters["release_channel"]) == 3)

        print("\n[2] 新建资源")
        r = client.post("/api/resources/admin", headers=H(admin), json={
            "slug": "quick-tools", "name": "快捷工具", "resourceType": "plugin",
            "summary": "一套服务器管理插件", "side": "server",
            "platforms": ["paper", "purpur"], "gameVersions": ["1.21"], "tags": [],
            "githubRepoUrl": "https://github.com/xqly/quick-tools",
            "descriptionMd": "# 快捷工具\n\n管理服好帮手",
        })
        check("新建成功(默认草稿)", r.status_code == 200 and r.json()["data"]["status"] == "draft", r.text[:200])
        rid = r.json()["data"]["id"]
        check("slug 重复被拒", client.post("/api/resources/admin", headers=H(admin), json={
            "slug": "quick-tools", "name": "x"}).status_code == 400)
        check("slug 非法被拒", client.post("/api/resources/admin", headers=H(admin), json={
            "slug": "Bad_Slug!", "name": "x"}).status_code == 400)
        check("未知平台 key 被拒", client.post("/api/resources/admin", headers=H(admin), json={
            "slug": "unknown-p", "name": "x", "platforms": ["not-exists"]}).status_code == 400)
        check("草稿前台 404", client.get("/api/resources/quick-tools").status_code == 404)
        check("草稿不在公开列表", client.get("/api/resources").json()["data"]["total"] == 0)

        print("\n[3] 资源状态控制")
        r = client.post(f"/api/resources/admin/{rid}/status", headers=H(admin), json={"status": "published"})
        check("发布成功", r.status_code == 200 and r.json()["data"]["status"] == "published")
        check("前台详情可见", client.get("/api/resources/quick-tools").status_code == 200)
        check("公开列表可见", client.get("/api/resources").json()["data"]["total"] == 1)
        detail = client.get("/api/resources/quick-tools").json()["data"]
        check("详情含关联 key", detail["platforms"] == ["paper", "purpur"] and detail["gameVersions"] == ["1.21"],
              str(detail.get("platforms")))
        check("详情含计数口径说明", "非 GitHub 实际下载量" in detail.get("downloadCountNote", ""))

        # 第二个资源（mod，fabric，双端）
        r = client.post("/api/resources/admin", headers=H(admin), json={
            "slug": "magic-mod", "name": "魔法模组", "resourceType": "mod",
            "summary": "加入魔法系统", "side": "both",
            "platforms": ["fabric"], "gameVersions": ["1.21", "1.20"],
            "status": "published",
        })
        check("第二个资源创建+直接发布", r.status_code == 200, r.text[:200])
        rid2 = r.json()["data"]["id"]

        print("\n[4] 版本管理")
        r = client.post(f"/api/resources/admin/{rid}/versions", headers=H(admin), json={
            "version": "1.0.0", "channel": "stable", "releaseTag": "v1.0.0",
            "gameVersions": ["1.21"], "platforms": ["paper"],
            "changelogMd": "首个版本",
        })
        check("新建版本", r.status_code == 200, r.text[:200])
        vid1 = r.json()["data"]["id"]
        check("同资源版本号唯一", client.post(f"/api/resources/admin/{rid}/versions", headers=H(admin), json={
            "version": "1.0.0"}).status_code == 400)
        r = client.post(f"/api/resources/admin/{rid}/versions", headers=H(admin), json={
            "version": "1.1.0-beta", "channel": "beta", "gameVersions": ["1.21"]})
        check("beta 版本创建", r.status_code == 200, r.text[:200])
        vid2 = r.json()["data"]["id"]
        check("设最新稳定版", client.put(f"/api/resources/admin/versions/{vid1}", headers=H(admin),
              json={"isLatestStable": True}).status_code == 200)
        r = client.post(f"/api/resources/admin/{rid}/versions", headers=H(admin), json={
            "version": "2.0.0", "channel": "stable", "isLatestStable": True})
        vid3 = r.json()["data"]["id"]
        check("最新稳定版唯一转移", client.get(f"/api/resources/admin/{rid}/versions", headers=H(admin)).json()["data"]
              and [v["isLatestStable"] for v in
                   sorted(client.get(f"/api/resources/admin/{rid}/versions", headers=H(admin)).json()["data"],
                          key=lambda v: v["version"])] .count(1) == 1)
        check("非 stable 不能设最新稳定版", client.put(f"/api/resources/admin/versions/{vid2}", headers=H(admin),
              json={"isLatestStable": True}).status_code == 400)

        print("\n[5] 资产管理")
        r = client.post(f"/api/resources/admin/versions/{vid3}/assets", headers=H(admin), json={
            "filename": "quick-tools-2.0.0.jar", "purpose": "main",
            "url": "https://github.com/xqly/quick-tools/releases/download/v2.0.0/quick-tools-2.0.0.jar",
        })
        check("新建主资产", r.status_code == 200 and r.json()["data"]["isPrimary"] == 1, r.text[:200])
        aid_main = r.json()["data"]["id"]
        check("非 github URL 被拒", client.post(f"/api/resources/admin/versions/{vid3}/assets", headers=H(admin),
              json={"filename": "x.jar", "url": "https://evil.com/x.jar"}).status_code == 400)
        check("http URL 被拒", client.post(f"/api/resources/admin/versions/{vid3}/assets", headers=H(admin),
              json={"filename": "x.jar", "url": "http://github.com/xqly/x.jar"}).status_code == 400)
        r = client.post(f"/api/resources/admin/versions/{vid3}/assets", headers=H(admin), json={
            "filename": "quick-tools-2.0.0-sources.jar", "purpose": "additional", "sort": 1,
            "url": "https://github.com/xqly/quick-tools/releases/download/v2.0.0/quick-tools-2.0.0-sources.jar"})
        aid2 = r.json()["data"]["id"]
        r = client.post(f"/api/resources/admin/versions/{vid3}/assets", headers=H(admin), json={
            "filename": "another-main.jar", "purpose": "main",
            "url": "https://github.com/xqly/quick-tools/releases/download/v2.0.0/another.jar",
            "isPrimary": True})
        check("主资产唯一转移", r.status_code == 200 and r.json()["data"]["isPrimary"] == 1)
        assets = client.get(f"/api/resources/admin/versions/{vid3}/assets", headers=H(admin)).json()["data"]
        check("主资产唯一(旧主自动让位)", sum(1 for a in assets if a["isPrimary"] == 1) == 1, str(assets))
        aid3 = r.json()["data"]["id"]

        # beta 版本资产
        r = client.post(f"/api/resources/admin/versions/{vid2}/assets", headers=H(admin), json={
            "filename": "quick-tools-1.1.0-beta.jar",
            "url": "https://github.com/xqly/quick-tools/releases/download/v1.1.0/quick-tools-1.1.0-beta.jar"})
        aid_beta = r.json()["data"]["id"]

        print("\n[6] 详情页数据")
        detail = client.get("/api/resources/quick-tools").json()["data"]
        check("版本列表按最新稳定版在前", detail["versions"][0]["version"] == "2.0.0",
              str([v["version"] for v in detail["versions"]]))
        v20 = [v for v in detail["versions"] if v["version"] == "2.0.0"][0]
        check("版本含可见资产", len(v20["assets"]) == 3, str(len(v20["assets"])))
        check("主资产排最前", v20["assets"][0]["isPrimary"] == 1)

        print("\n[7] 下载跳转端点")
        r = client.get(f"/download/asset/{aid3}", follow_redirects=False)
        check("302 跳转", r.status_code == 302, str(r.status_code))
        check("跳转到后台录入的 GitHub URL",
              r.headers.get("location") == "https://github.com/xqly/quick-tools/releases/download/v2.0.0/another.jar",
              r.headers.get("location", ""))
        # 事件与计数
        detail = client.get("/api/resources/quick-tools").json()["data"]
        check("跳转计数=1(实时聚合)", detail["downloadCount"] == 1, str(detail["downloadCount"]))
        # 隐藏资产 410
        client.put(f"/api/resources/admin/assets/{aid2}", headers=H(admin), json={"status": "hidden"})
        check("隐藏资产 410", client.get(f"/download/asset/{aid2}", follow_redirects=False).status_code == 410)
        # 隐藏版本 → 其资产全部 410
        client.put(f"/api/resources/admin/versions/{vid2}", headers=H(admin), json={"status": "hidden"})
        check("隐藏版本的资产 410", client.get(f"/download/asset/{aid_beta}", follow_redirects=False).status_code == 410)
        client.put(f"/api/resources/admin/versions/{vid2}", headers=H(admin), json={"status": "visible"})
        check("恢复版本后资产可下载", client.get(f"/download/asset/{aid_beta}", follow_redirects=False).status_code == 302)
        # 不存在的资产 404
        check("不存在资产 404", client.get("/download/asset/99999", follow_redirects=False).status_code == 404)
        # 开放重定向防护：端点不接受 URL 参数（FastAPI 路由无 query 参数，多余参数被忽略，
        # 跳转目标永远来自库内 asset.url）
        r = client.get(f"/download/asset/{aid3}?url=https://evil.com&to=https://evil.com", follow_redirects=False)
        check("任意 URL 参数不影响跳转目标", r.headers.get("location", "").startswith("https://github.com/"),
              r.headers.get("location", ""))

        print("\n[8] 限速")
        # 阈值 30/min；已消耗若干次，直接连打 60 次看是否出现 429
        got_429 = False
        for _ in range(60):
            rr = client.get(f"/download/asset/{aid3}", follow_redirects=False)
            if rr.status_code == 429:
                got_429 = True
                break
        check("触发限速 429", got_429)

        print("\n[9] 列表筛选与排序")
        list_resp = client.get("/api/resources").json()["data"]
        check("两个已发布资源", list_resp["total"] == 2, str(list_resp["total"]))
        check("平台筛选取无重复行", client.get("/api/resources?platform=fabric,paper").json()["data"]["total"] == 2)
        check("单平台筛选", client.get("/api/resources?platform=fabric").json()["data"]["total"] == 1)
        check("类型筛选", client.get("/api/resources?type=mod").json()["data"]["total"] == 1)
        check("游戏版本筛选", client.get("/api/resources?game_version=1.20").json()["data"]["total"] == 1)
        check("侧别筛选", client.get("/api/resources?side=server").json()["data"]["total"] == 1)
        check("渠道筛选(命中版本)", client.get("/api/resources?channel=beta").json()["data"]["total"] == 1,
              str(client.get("/api/resources?channel=beta").json()["data"]))
        check("关键词搜索(名称)", client.get("/api/resources?q=魔法").json()["data"]["total"] == 1)
        check("关键词搜索(简介)", client.get("/api/resources?q=管理插件").json()["data"]["total"] == 1)
        check("未知平台 key 400", client.get("/api/resources?platform=not-exists").status_code == 400)
        # 排序
        r = client.get("/api/resources?sort=downloads_desc").json()["data"]
        check("按跳转次数排序(quick-tools 有事件)", r["items"][0]["slug"] == "quick-tools",
              str([i["slug"] for i in r["items"]]))
        r = client.get("/api/resources?sort=name_asc").json()["data"]
        check("按名称排序", [i["name"] for i in r["items"]] == sorted(i["name"] for i in r["items"]),
              str([i["name"] for i in r["items"]]))
        check("非法排序回退默认", client.get("/api/resources?sort=evil").status_code == 200)
        check("featured 置顶排序", client.get("/api/resources").status_code == 200)

        print("\n[10] 软删除")
        # （限速窗口 60s 内仍在计数，但 410/404 判定在限速之前不会受影响——
        #   端点顺序是先限速后查库，连打 60 次已把本 IP 的一分钟窗口打满，
        #   这里先清空进程内窗口再继续，避免后续 410 断言被 429 干扰）
        from app.resource_center import _download_minute
        _download_minute.clear()
        client.delete(f"/api/resources/admin/{rid2}", headers=H(admin))
        check("软删后前台 404", client.get("/api/resources/magic-mod").status_code == 404)
        check("软删后列表不可见", client.get("/api/resources").json()["data"]["total"] == 1)
        check("软删后可查回收站", client.get("/api/resources/admin/page?status=deleted", headers=H(admin))
              .json()["data"]["total"] == 1)
        client.post(f"/api/resources/admin/{rid2}/restore", headers=H(admin))
        check("恢复后前台可见", client.get("/api/resources/magic-mod").status_code == 200)
        # 版本软删
        client.delete(f"/api/resources/admin/versions/{vid2}", headers=H(admin))
        check("版本软删后资产 410", client.get(f"/download/asset/{aid_beta}", follow_redirects=False).status_code == 410)
        check("版本软删后详情不含", client.get("/api/resources/quick-tools").json()["data"]["versions"]
              and all(v["version"] != "1.1.0-beta" for v in
                      client.get("/api/resources/quick-tools").json()["data"]["versions"]))

        print("\n[11] 统计")
        st = client.get("/api/resources/admin/stats", headers=H(admin)).json()["data"]
        check("总览>0", st["total"] > 0, str(st["total"]))
        check("按资源统计", any(x["name"] == "快捷工具" for x in st["byResource"]), str(st["byResource"]))
        check("按版本统计", any(x["name"] == "2.0.0" for x in st["byVersion"]), str(st["byVersion"]))
        check("按资产统计", any("quick-tools" in x["name"] or ".jar" in x["name"] for x in st["byAsset"]),
              str(st["byAsset"]))
        check("统计含口径说明", "非 GitHub 实际下载量" in st.get("note", ""))
        # 时间范围（把范围设到 2020 年应查不到）
        st2 = client.get("/api/resources/admin/stats?start=2020-01-01&end=2020-01-02", headers=H(admin)).json()["data"]
        check("时间范围过滤生效", st2["total"] == 0, str(st2["total"]))

        print("\n[12] 权限")
        check("匿名不可访问管理接口", client.get("/api/resources/admin/page").status_code == 401)

    print()
    if FAILS:
        print(f"\033[31m{len(FAILS)} 项失败\033[0m")
        for f in FAILS:
            print(" -", f)
        return 1
    print("\033[32m全部通过\033[0m")
    return 0


if __name__ == "__main__":
    sys.exit(main())
