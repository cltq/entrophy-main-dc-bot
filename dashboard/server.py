import os
import asyncio
import json
import datetime
from aiohttp import web
from typing import List
from utils.log_buffer import LOG_BUFFER
from collections import deque


def uptime_str(launch_time: datetime.datetime) -> str:
    if not launch_time:
        return "Unknown"
    delta = datetime.datetime.now(datetime.timezone.utc) - launch_time
    days = delta.days
    hours, rem = divmod(delta.seconds, 3600)
    minutes, seconds = divmod(rem, 60)
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    parts.append(f"{seconds}s")
    return " ".join(parts)


async def api_status(request: web.Request) -> web.Response:
    bot = request.app["bot"]
    data = {
        "name": str(bot.user) if bot.user else "-",
        "id": getattr(bot.user, "id", "-"),
        "uptime": uptime_str(getattr(bot, "launch_time", None)),
        "guild_count": len(bot.guilds) if bot.guilds is not None else 0,
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
    }
    # include a few recent logs
    recent_logs = list(LOG_BUFFER)[-10:]
    data["recent_logs"] = recent_logs[::-1]
    return web.json_response(data)


async def api_logs(request: web.Request) -> web.Response:
    # full logs: read the log file if present, else return buffer
    log_file = os.path.join(os.getcwd(), "logs", "entrophy.log")
    if os.path.exists(log_file):
        try:
            with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.read().splitlines()[-2000:]
        except Exception:
            lines = list(LOG_BUFFER)
    else:
        lines = list(LOG_BUFFER)
    return web.json_response({"logs": lines[::-1]})


def _check_token(request: web.Request) -> bool:
    """Check DASHBOARD_TOKEN if set; allow when token matches or when no token configured."""
    cfg = os.getenv('DASHBOARD_TOKEN')
    if not cfg:
        return True
    # token may be provided in header 'X-DASH-TOKEN' or query param 'token'
    token = request.headers.get('X-DASH-TOKEN') or request.query.get('token')
    return token == cfg


async def api_shutdown(request: web.Request) -> web.Response:
    if not _check_token(request):
        return web.json_response({'ok': False, 'error': 'unauthorized'}, status=401)
    bot = request.app['bot']

    async def _do_shutdown():
        try:
            await asyncio.sleep(0.2)
            await bot.close()
        except Exception:
            pass

    request.app.loop.create_task(_do_shutdown())
    return web.json_response({'ok': True, 'action': 'shutdown'})


async def api_restart(request: web.Request) -> web.Response:
    if not _check_token(request):
        return web.json_response({'ok': False, 'error': 'unauthorized'}, status=401)
    bot = request.app['bot']

    async def _do_restart():
        try:
            # write restart info to file if provided by header
            info = {
                'requested_by': request.headers.get('X-REQUESTED-BY', 'dashboard'),
                'timestamp': datetime.datetime.utcnow().isoformat() + 'Z'
            }
            try:
                with open('restart_info.json', 'w') as f:
                    import json
                    json.dump(info, f)
            except Exception:
                pass
            await asyncio.sleep(0.3)
            # attempt graceful close then exec
            try:
                await bot.close()
            except Exception:
                pass
            # Re-exec the process
            try:
                import sys
                os.execv(sys.executable, [sys.executable] + sys.argv)
            except Exception:
                pass
        except Exception:
            pass

    request.app.loop.create_task(_do_restart())
    return web.json_response({'ok': True, 'action': 'restart'})


async def api_redeploy(request: web.Request) -> web.Response:
    """Trigger a tree.sync() to redeploy app commands and return sync result."""
    if not _check_token(request):
        return web.json_response({'ok': False, 'error': 'unauthorized'}, status=401)
    bot = request.app['bot']
    try:
        synced = await bot.tree.sync()
        return web.json_response({'ok': True, 'synced': len(synced)})
    except Exception as e:
        return web.json_response({'ok': False, 'error': str(e)})


async def sse_stream(request: web.Request) -> web.StreamResponse:
    """Server-Sent Events stream for live updates (status + recent logs)."""
    resp = web.StreamResponse(
        status=200,
        reason='OK',
        headers={
            'Content-Type': 'text/event-stream',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
        }
    )
    await resp.prepare(request)

    bot = request.app['bot']

    try:
        while True:
            data = {
                'timestamp': datetime.datetime.utcnow().isoformat() + 'Z',
                'name': str(bot.user) if bot.user else '-',
                'id': getattr(bot.user, 'id', '-'),
                'uptime': uptime_str(getattr(bot, 'launch_time', None)),
                'guild_count': len(bot.guilds) if bot.guilds is not None else 0,
                'recent_logs': list(LOG_BUFFER)[-20:][::-1],
                'requests_per_sec': list(request.app.get('req_counts', []))
            }
            payload = f"data: {json.dumps(data)}\n\n"
            await resp.write(payload.encode('utf-8'))
            await resp.drain()
            await asyncio.sleep(1.0)
    except asyncio.CancelledError:
        pass
    except ConnectionResetError:
        pass
    finally:
        try:
            await resp.write_eof()
        except Exception:
            pass
    return resp


async def index(request: web.Request) -> web.Response:
    p = os.path.join(os.path.dirname(__file__), "static", "index.html")
    return web.FileResponse(p)


async def logs_page(request: web.Request) -> web.Response:
    p = os.path.join(os.path.dirname(__file__), "static", "logs.html")
    return web.FileResponse(p)


async def start_dashboard(bot, host: str = "0.0.0.0", port: int = 8080):
    app = web.Application()
    app["bot"] = bot
    # request counting: maintain a deque of recent per-second counts
    app['req_counts'] = deque(maxlen=120)
    app['req_current'] = 0

    @web.middleware
    async def _count_middleware(request, handler):
        try:
            # increment current request counter for dashboard activity
            app['req_current'] = app.get('req_current', 0) + 1
        except Exception:
            pass
        return await handler(request)

    app.middlewares.append(_count_middleware)
    app.add_routes([
        web.get('/', index),
        web.get('/logs.html', logs_page),
        web.get('/api/status', api_status),
        web.get('/api/logs', api_logs),
        web.get('/api/stream', sse_stream),
        web.post('/api/shutdown', api_shutdown),
        web.post('/api/restart', api_restart),
        web.post('/api/redeploy', api_redeploy),
    ])

    static_dir = os.path.join(os.path.dirname(__file__), "static")
    app.router.add_static('/static/', static_dir, show_index=False)

    runner = web.AppRunner(app)
    await runner.setup()
    # If running on a platform like Render, prefer PORT env variable
    env_port = int(os.getenv('PORT') or port)
    site = web.TCPSite(runner, host, env_port)
    await site.start()
    # start a background task to roll per-second counters into the deque
    async def _ticker():
        try:
            while True:
                cur = app.get('req_current', 0)
                app['req_counts'].append(cur)
                app['req_current'] = 0
                await asyncio.sleep(1.0)
        except asyncio.CancelledError:
            pass

    asyncio.create_task(_ticker())
    print(f"Dashboard running on http://{host}:{env_port}")
