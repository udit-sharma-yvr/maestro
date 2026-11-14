"""FastAPI server: task kickoff, WebSocket event stream, and the dashboard."""

import asyncio
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .runtime import Runtime

runtime = Runtime()
tasks: dict[str, asyncio.Queue] = {}

DASHBOARD_DIR = Path(__file__).resolve().parent.parent / "dashboard"


@asynccontextmanager
async def lifespan(app: FastAPI):
    await runtime.start()
    yield


app = FastAPI(title="Maestro", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=DASHBOARD_DIR), name="static")


@app.get("/")
async def index():
    return FileResponse(DASHBOARD_DIR / "index.html")


@app.get("/health")
async def health():
    return {"status": "ok", "ready": runtime.orchestrator is not None}


@app.post("/run")
async def run(payload: dict):
    prompt = (payload.get("prompt") or "").strip()
    if not prompt:
        return {"error": "prompt is required"}
    task_id = str(uuid.uuid4())
    tasks[task_id] = asyncio.Queue()
    asyncio.create_task(_worker(task_id, prompt))
    return {"task_id": task_id}


async def _worker(task_id: str, prompt: str) -> None:
    q = tasks[task_id]
    try:
        async for ev in runtime.run_task(task_id, prompt):
            await q.put(ev)
    except Exception as e:  # defensive: never leave a client waiting forever
        await q.put({"type": "error", "message": f"{type(e).__name__}: {e}"})
    finally:
        await q.put(None)  # sentinel: stream is finished


@app.websocket("/stream/{task_id}")
async def stream(ws: WebSocket, task_id: str):
    await ws.accept()
    q = tasks.get(task_id)
    if q is None:
        await ws.send_json({"type": "error", "message": "unknown task_id"})
        await ws.close()
        return
    try:
        while True:
            ev = await q.get()
            if ev is None:
                break
            await ws.send_json(ev)
    except WebSocketDisconnect:
        pass
    finally:
        tasks.pop(task_id, None)
