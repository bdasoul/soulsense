import asyncio
import json
from typing import Set

from aiohttp import web, WSMsgType

from motion import MotionEngine
from sources import run_pipeline


class SoulsenseServer:
    def __init__(self, source, engine: MotionEngine, static_dir: str):
        self.source = source
        self.engine = engine
        self.static_dir = static_dir
        self.clients: Set[web.WebSocketResponse] = set()
        self.status = {"connected": False}

    async def _broadcast(self, msg: dict) -> None:
        if not self.clients:
            return
        data = json.dumps(msg)
        dead = []
        for ws in self.clients:
            try:
                await ws.send_str(data)
            except ConnectionResetError:
                dead.append(ws)
        for ws in dead:
            self.clients.discard(ws)

    def _pipeline_blocking(self, loop: asyncio.AbstractEventLoop, queue: asyncio.Queue) -> None:
        def set_status(connected: bool):
            self.status["connected"] = connected
            loop.call_soon_threadsafe(
                queue.put_nowait, {"type": "status", "connected": connected}
            )

        self.source.on_status = set_status

        for msg in run_pipeline(self.source, self.engine):
            msg["type"] = "csi"
            loop.call_soon_threadsafe(queue.put_nowait, msg)

    async def _broadcaster(self, queue: asyncio.Queue) -> None:
        last_csi = 0.0
        while True:
            msg = await queue.get()
            if msg.get("type") == "csi":
                now = loop_time()
                if now - last_csi < (1 / 15):
                    continue
                last_csi = now
            await self._broadcast(msg)

    async def on_startup(self, app: web.Application) -> None:
        loop = asyncio.get_event_loop()
        queue: asyncio.Queue = asyncio.Queue()
        app["queue"] = queue
        app["broadcaster"] = loop.create_task(self._broadcaster(queue))
        app["pipeline"] = loop.run_in_executor(
            None, self._pipeline_blocking, loop, queue
        )

    async def on_cleanup(self, app: web.Application) -> None:
        if hasattr(self.source, "stop"):
            self.source.stop()
        app["broadcaster"].cancel()

    async def index(self, request: web.Request) -> web.FileResponse:
        return web.FileResponse(f"{self.static_dir}/index.html")

    async def websocket(self, request: web.Request) -> web.WebSocketResponse:
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        self.clients.add(ws)
        await ws.send_str(
            json.dumps({"type": "status", "connected": self.status["connected"]})
        )
        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                    except json.JSONDecodeError:
                        continue
                    if data.get("type") == "params":
                        self.engine.set_params(
                            window_size=data.get("window_size"),
                            smoothing=data.get("smoothing"),
                        )
        finally:
            self.clients.discard(ws)
        return ws

    def build_app(self) -> web.Application:
        app = web.Application()
        app.router.add_get("/", self.index)
        app.router.add_get("/ws", self.websocket)
        app.router.add_static("/static/", self.static_dir)
        app.on_startup.append(self.on_startup)
        app.on_cleanup.append(self.on_cleanup)
        return app


def loop_time() -> float:
    try:
        return asyncio.get_event_loop().time()
    except RuntimeError:
        return 0.0
