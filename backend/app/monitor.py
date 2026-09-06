"""Minimal server monitor endpoint.

The homepage OnlineCounter widget calls GET /monitor/server-info/{id}.
Until a full monitoring backend (player counts, history charts) exists,
this endpoint probes the Minecraft server with a plain TCP connect check
and reports a real online/offline status, so the widget never 404s.

Admin endpoints for server address management are also defined here
(single source of truth for game server addresses, per AGENTS.md).
"""
import asyncio

from fastapi import APIRouter, Depends, HTTPException, status

from .auth.deps import require_admin

router = APIRouter()

# 游戏服务器注册表：官网展示与在线探测的唯一数据源（由后端维护）。
# 每个服务器可包含 is_primary 标识，全表最多一个主服务器。
SERVERS = {
    1: {"name": "主服务器", "address": "serverone.codeyun.com", "port": 12000, "is_primary": True},
}

PROBE_TIMEOUT = 3.0  # seconds


def _get_primary_id() -> int | None:
    """返回当前主服务器 ID；无主服务器时返回 None。"""
    for sid, cfg in SERVERS.items():
        if cfg.get("is_primary"):
            return sid
    return None


def _next_server_id() -> int:
    """生成下一个可用的服务器 ID。"""
    return max(SERVERS.keys()) + 1 if SERVERS else 1


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


# ── 管理员：服务器地址管理 ────────────────────────────────────────
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

    new_id = _next_server_id()

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

    if name is not None:
        if not name.strip():
            raise HTTPException(status_code=400, detail="服务器名称不能为空")
        server["name"] = name.strip()
    if address is not None:
        if not address.strip():
            raise HTTPException(status_code=400, detail="服务器地址不能为空")
        server["address"] = address.strip()
    if port is not None:
        if not isinstance(port, int) or port < 1 or port > 65535:
            raise HTTPException(status_code=400, detail="端口必须为 1-65535 的整数")
        server["port"] = port
    if is_primary is not None:
        if is_primary:
            # 清除其他服务器的主标记
            for sid, cfg in SERVERS.items():
                if sid != server_id:
                    cfg["is_primary"] = False
        server["is_primary"] = is_primary

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

    del SERVERS[server_id]
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

    # 清除其他服务器的主标记，设置当前服务器为主
    for sid, cfg in SERVERS.items():
        cfg["is_primary"] = (sid == server_id)

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