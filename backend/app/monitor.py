"""Server monitor endpoints + game server address registry (persistent).

The homepage OnlineCounter widget calls GET /monitor/server-info/{id}.
Until a full monitoring backend (player counts, history charts) exists,
this endpoint probes the Minecraft server with a plain TCP connect check
and reports a real online/offline status, so the widget never 404s.

Admin endpoints for server address management are also defined here
(single source of truth for game server addresses, per AGENTS.md).

持久化（智能客服 P0 引入，方案 §5.8）：
- DB（servers 表）为唯一权威，内存字典 SERVERS 为读缓存；
- 启动时 load_servers() 读 DB 填充内存；表为空时用 _DEFAULT_SERVERS 做种子，
  保证升级后行为不变；
- 所有管理接口改内存后同步全量落库（先 commit 再返回），失败回滚内存改动；
- 对外行为（/monitor/servers、/monitor/server-info/{id} 响应结构）保持不变
  （首页 OnlineCounter 依赖它）。
⚠️ 该改造改变了"重启后地址丢失"的旧行为，属修 bug（README 变更说明已写明）。
"""
import asyncio
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select

from .auth.deps import require_admin
from .crud import _TZ as BEIJING_TZ
from .database import ServerRecord, async_session_maker

logger = logging.getLogger("uvicorn.error")

router = APIRouter()

# 游戏服务器默认注册表：servers 表为空时作为种子写入（升级后行为不变）。
# 每个服务器可包含 is_primary 标识，全表最多一个主服务器。
_DEFAULT_SERVERS = {
    1: {"name": "主服务器", "address": "serverone.codeyun.com", "port": 12000, "is_primary": True},
}

# 内存读缓存：{id: {name, address, port, is_primary}}，结构与改造前保持一致（最小改动）
SERVERS: dict[int, dict] = {}

PROBE_TIMEOUT = 3.0  # seconds


def _now_iso() -> str:
    return datetime.now(BEIJING_TZ).strftime("%Y-%m-%dT%H:%M:%S")


def _get_primary_id() -> int | None:
    """返回当前主服务器 ID；无主服务器时返回 None。"""
    for sid, cfg in SERVERS.items():
        if cfg.get("is_primary"):
            return sid
    return None


def get_primary_id() -> int | None:
    """_get_primary_id 的公开别名（kb 状态注入使用）。"""
    return _get_primary_id()


async def load_servers() -> None:
    """启动时从 DB 加载服务器地址（DB 唯一权威，内存读缓存）。

    servers 表为空（首次升级启动）时，用 _DEFAULT_SERVERS 做种子写入，
    保证改造前后行为等价。
    """
    async with async_session_maker() as db:
        rows = (
            await db.execute(select(ServerRecord).order_by(ServerRecord.id))
        ).scalars().all()
        if not rows:
            now = _now_iso()
            for sid, cfg in _DEFAULT_SERVERS.items():
                db.add(
                    ServerRecord(
                        id=sid,
                        name=cfg["name"],
                        address=cfg["address"],
                        port=cfg["port"],
                        is_primary=1 if cfg.get("is_primary") else 0,
                        create_time=now,
                        update_time=now,
                    )
                )
            await db.commit()
            logger.info("servers 表为空，已写入默认服务器注册表作为种子（行为与改造前一致）")
            rows = (
                await db.execute(select(ServerRecord).order_by(ServerRecord.id))
            ).scalars().all()
    loaded = {
        row.id: {
            "name": row.name,
            "address": row.address,
            "port": row.port,
            "is_primary": bool(row.is_primary),
        }
        for row in rows
    }
    SERVERS.clear()
    SERVERS.update(loaded)
    logger.info("已从数据库加载 %d 个游戏服务器地址", len(loaded))


async def _next_server_id() -> int:
    """生成下一个可用的服务器 ID：取 max(DB id, 内存 id) + 1。"""
    async with async_session_maker() as db:
        max_db_id = (await db.execute(select(func.max(ServerRecord.id)))).scalar_one()
    return max(max_db_id or 0, max(SERVERS.keys(), default=0)) + 1


async def _persist_all() -> None:
    """把内存 SERVERS 全量同步进 DB（管理操作频度极低、表极小，全量同步最稳）。"""
    async with async_session_maker() as db:
        rows = (await db.execute(select(ServerRecord))).scalars().all()
        by_id = {row.id: row for row in rows}
        now = _now_iso()
        for sid, cfg in SERVERS.items():
            row = by_id.get(sid)
            if row is None:
                db.add(
                    ServerRecord(
                        id=sid,
                        name=cfg["name"],
                        address=cfg["address"],
                        port=cfg["port"],
                        is_primary=1 if cfg.get("is_primary") else 0,
                        create_time=now,
                        update_time=now,
                    )
                )
            else:
                row.name = cfg["name"]
                row.address = cfg["address"]
                row.port = cfg["port"]
                row.is_primary = 1 if cfg.get("is_primary") else 0
                row.update_time = now
        for sid, row in by_id.items():
            if sid not in SERVERS:
                await db.delete(row)
        await db.commit()


def _snapshot() -> dict[int, dict]:
    return {sid: dict(cfg) for sid, cfg in SERVERS.items()}


def _restore(snapshot: dict[int, dict]) -> None:
    SERVERS.clear()
    SERVERS.update(snapshot)


async def _persist_or_rollback(snapshot: dict[int, dict]) -> None:
    """落库；失败回滚内存改动并抛 500（先 commit 再返回的失败路径）。"""
    try:
        await _persist_all()
    except Exception:
        _restore(snapshot)
        logger.exception("服务器地址持久化失败，已回滚内存改动")
        raise HTTPException(status_code=500, detail="服务器地址写入数据库失败，操作未生效")


async def probe_tcp(address: str, port: int) -> bool:
    """TCP connect check: True if the server accepts a connection."""
    try:
        _reader, writer = await asyncio.wait_for(
            asyncio.open_connection(address, port), timeout=PROBE_TIMEOUT
        )
        writer.close()
        await writer.wait_closed()
        return True
    except (asyncio.TimeoutError, OSError):
        return False


async def query_status(server_id: int) -> dict | None:
    """只读状态查询（客服实时状态注入用）：{online, address, port, name}。

    仍用 probe_tcp，不引 mcstatus（真实玩家人数进 P1）；
    server_id 不存在时返回 None。
    """
    cfg = SERVERS.get(server_id)
    if cfg is None:
        return None
    online = await probe_tcp(cfg["address"], cfg["port"])
    return {
        "online": online,
        "address": cfg["address"],
        "port": cfg["port"],
        "name": cfg["name"],
    }


# ── 公开：服务器列表（前端展示的唯一来源） ────────────────────────
@router.get("/monitor/servers")
async def list_servers():
    """游戏服务器地址列表（前端展示的唯一来源）。

    Response: {code, message, data: {servers: [{id, name, address, port, display, isPrimary}], primary}}
    """
    primary_id = _get_primary_id()
    servers = [
        {
            "id": server_id,
            "name": cfg["name"],
            "address": cfg["address"],
            "port": cfg["port"],
            "display": f"{cfg['address']}:{cfg['port']}",
            "isPrimary": cfg.get("is_primary", False),
        }
        for server_id, cfg in SERVERS.items()
    ]
    return {
        "code": 0,
        "message": "success",
        "data": {"servers": servers, "primary": primary_id},
    }


@router.get("/monitor/server-info/{server_id}")
async def server_info(
    server_id: int,
    start_time: str = "",
    end_time: str = "",
    time_period: int = 1,
):
    """Return server status for the homepage OnlineCounter widget.

    Response shape matches what the frontend expects:
    {code, message, data: {status, ping, onlinePlayers, maxPlayers, info, historyStatusList}}
    """
    server = SERVERS.get(server_id)
    if server is None:
        raise HTTPException(status_code=404, detail="server not found")

    online = await probe_tcp(server["address"], server["port"])
    return {
        "code": 0,
        "message": "success",
        "data": {
            "status": "online" if online else "offline",
            "ping": 0,
            "onlinePlayers": 0,
            "maxPlayers": 0,
            "info": {"address": server["address"], "port": server["port"]},
            "historyStatusList": [],
        },
    }


# ── 管理员：服务器地址管理（改内存后同步落库，失败回滚内存） ──────
@router.get("/monitor/admin/servers")
async def admin_list_servers(_admin=Depends(require_admin)):
    """管理员：获取所有服务器列表（含主服务器标记）。"""
    primary_id = _get_primary_id()
    servers = [
        {
            "id": server_id,
            "name": cfg["name"],
            "address": cfg["address"],
            "port": cfg["port"],
            "isPrimary": cfg.get("is_primary", False),
        }
        for server_id, cfg in SERVERS.items()
    ]
    return {
        "code": 0,
        "message": "success",
        "data": {"servers": servers, "primary": primary_id},
    }


@router.post("/monitor/admin/servers")
async def admin_create_server(
    req: dict,
    _admin=Depends(require_admin),
):
    """管理员：添加新服务器。

    Body: {name: str, address: str, port: int, isPrimary?: bool}
    """
    name = (req.get("name") or "").strip()
    address = (req.get("address") or "").strip()
    port = req.get("port")
    is_primary = req.get("isPrimary", False)

    if not name:
        raise HTTPException(status_code=400, detail="服务器名称不能为空")
    if not address:
        raise HTTPException(status_code=400, detail="服务器地址不能为空")
    if not isinstance(port, int) or port < 1 or port > 65535:
        raise HTTPException(status_code=400, detail="端口必须为 1-65535 的整数")

    new_id = await _next_server_id()
    snapshot = _snapshot()

    # 如果设置为主服务器，先清除其他服务器的主标记
    if is_primary:
        for cfg in SERVERS.values():
            cfg["is_primary"] = False

    SERVERS[new_id] = {
        "name": name,
        "address": address,
        "port": port,
        "is_primary": is_primary,
    }
    await _persist_or_rollback(snapshot)

    return {
        "code": 0,
        "message": "success",
        "data": {
            "id": new_id,
            "name": name,
            "address": address,
            "port": port,
            "isPrimary": is_primary,
        },
    }


@router.put("/monitor/admin/servers/{server_id}")
async def admin_update_server(
    server_id: int,
    req: dict,
    _admin=Depends(require_admin),
):
    """管理员：更新服务器信息。

    Body: {name?: str, address?: str, port?: int, isPrimary?: bool}
    """
    server = SERVERS.get(server_id)
    if server is None:
        raise HTTPException(status_code=404, detail="服务器不存在")

    name = req.get("name")
    address = req.get("address")
    port = req.get("port")
    is_primary = req.get("isPrimary")

    if name is not None and not name.strip():
        raise HTTPException(status_code=400, detail="服务器名称不能为空")
    if address is not None and not address.strip():
        raise HTTPException(status_code=400, detail="服务器地址不能为空")
    if port is not None and (not isinstance(port, int) or port < 1 or port > 65535):
        raise HTTPException(status_code=400, detail="端口必须为 1-65535 的整数")

    snapshot = _snapshot()
    if name is not None:
        server["name"] = name.strip()
    if address is not None:
        server["address"] = address.strip()
    if port is not None:
        server["port"] = port
    if is_primary is not None:
        if is_primary:
            # 清除其他服务器的主标记
            for sid, cfg in SERVERS.items():
                if sid != server_id:
                    cfg["is_primary"] = False
        server["is_primary"] = is_primary
    await _persist_or_rollback(snapshot)

    return {
        "code": 0,
        "message": "success",
        "data": {
            "id": server_id,
            "name": server["name"],
            "address": server["address"],
            "port": server["port"],
            "isPrimary": server.get("is_primary", False),
        },
    }


@router.delete("/monitor/admin/servers/{server_id}")
async def admin_delete_server(
    server_id: int,
    _admin=Depends(require_admin),
):
    """管理员：删除服务器。

    不能删除主服务器。
    """
    server = SERVERS.get(server_id)
    if server is None:
        raise HTTPException(status_code=404, detail="服务器不存在")

    if server.get("is_primary"):
        raise HTTPException(status_code=400, detail="不能删除主服务器，请先设置其他服务器为主服务器")

    snapshot = _snapshot()
    del SERVERS[server_id]
    await _persist_or_rollback(snapshot)
    return {"code": 0, "message": "success"}


@router.post("/monitor/admin/servers/{server_id}/primary")
async def admin_set_primary(
    server_id: int,
    _admin=Depends(require_admin),
):
    """管理员：设置指定服务器为主服务器。"""
    server = SERVERS.get(server_id)
    if server is None:
        raise HTTPException(status_code=404, detail="服务器不存在")

    snapshot = _snapshot()
    # 清除其他服务器的主标记，设置当前服务器为主
    for sid, cfg in SERVERS.items():
        cfg["is_primary"] = (sid == server_id)
    await _persist_or_rollback(snapshot)

    return {
        "code": 0,
        "message": "success",
        "data": {
            "id": server_id,
            "name": server["name"],
            "address": server["address"],
            "port": server["port"],
            "isPrimary": True,
        },
    }
