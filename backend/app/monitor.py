"""Minimal server monitor endpoint.

The homepage OnlineCounter widget calls GET /monitor/server-info/{id}.
Until a full monitoring backend (player counts, history charts) exists,
this endpoint probes the Minecraft server with a plain TCP connect check
and reports a real online/offline status, so the widget never 404s.
"""
import asyncio

from fastapi import APIRouter, HTTPException

router = APIRouter()

# 游戏服务器注册表：官网展示与在线探测的唯一数据源（由后端维护，目前一个主地址）
SERVERS = {
    1: {"name": "主服务器", "address": "serverone.codeyun.com", "port": 12000},
}

PRIMARY_SERVER_ID = 1

PROBE_TIMEOUT = 3.0  # seconds


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


@router.get("/monitor/servers")
async def list_servers():
    """游戏服务器地址列表（前端展示的唯一来源）。

    Response: {code, message, data: {servers: [{id, name, address, port, display}], primary}}
    """
    servers = [
        {
            "id": server_id,
            "name": cfg["name"],
            "address": cfg["address"],
            "port": cfg["port"],
            "display": f"{cfg['address']}:{cfg['port']}",
        }
        for server_id, cfg in SERVERS.items()
    ]
    return {
        "code": 0,
        "message": "success",
        "data": {"servers": servers, "primary": PRIMARY_SERVER_ID},
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
