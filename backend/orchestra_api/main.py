from __future__ import annotations

import asyncio
import shutil
import uuid
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .config import settings
from .store import append_event, read_events, read_state, write_state, now_iso

app = FastAPI(title="ORCHESTRA Local Controller", version="0.3.0")

from .api import router as orchestration_router
from .runtime import recover_interrupted
app.include_router(orchestration_router)

@app.on_event("startup")
async def recover_after_restart() -> None:
    recover_interrupted()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Content-Type"],
)


class AgentCreate(BaseModel):
    name: str = Field(min_length=2, max_length=40)
    role: str = Field(min_length=2, max_length=80)
    specialization: str = Field(default="", max_length=240)
    instructions: str = Field(default="", max_length=8000)


class TaskCreate(BaseModel):
    title: str = Field(min_length=3, max_length=180)
    description: str = Field(default="", max_length=12000)
    role: str = Field(default="General Engineer", max_length=80)
    agent_id: str | None = None
    priority: Literal["low", "normal", "high", "critical"] = "normal"
    approval_required: bool = True


class ProjectConnect(BaseModel):
    path: str
    game_spec_path: str | None = None


class ApprovalDecision(BaseModel):
    decision: Literal["approved", "rejected"]
    note: str = Field(default="", max_length=2000)


class ConnectionManager:
    def __init__(self) -> None:
        self.connections: set[WebSocket] = set()
        self.lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self.lock:
            self.connections.add(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self.lock:
            self.connections.discard(websocket)

    async def broadcast(self, payload: dict[str, Any]) -> None:
        async with self.lock:
            connections = list(self.connections)
        stale = []
        for connection in connections:
            try:
                await connection.send_json(payload)
            except Exception:
                stale.append(connection)
        for connection in stale:
            await self.disconnect(connection)


manager = ConnectionManager()


async def publish(kind: str, message: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
    event = append_event(kind, message, data)
    await manager.broadcast({"type": kind, "event": event})
    return event


def ensure_state() -> dict[str, Any]:
    state = read_state()
    state.setdefault("version", 1)
    state.setdefault("agents", [])
    state.setdefault("tasks", [])
    state.setdefault("approvals", [])
    state.setdefault("project", None)
    return state


@app.get("/health")
async def health() -> dict[str, Any]:
    cli = shutil.which(settings.claude_cli_path) or (settings.claude_cli_path if Path(settings.claude_cli_path).exists() else None)
    return {"status": "ok", "service": "orchestra-controller", "time": now_iso(),
            "claude_cli_detected": bool(cli), "project_connected": settings.project_path is not None}


@app.get("/api/v1/state")
async def get_state() -> dict[str, Any]:
    state = ensure_state()
    state["events"] = read_events(60)
    return state


@app.get("/api/v1/events")
async def get_events(limit: int = 100) -> list[dict[str, Any]]:
    return read_events(limit)


@app.get("/api/v1/agents")
async def get_agents() -> list[dict[str, Any]]:
    return ensure_state()["agents"]


@app.post("/api/v1/agents", status_code=201)
async def create_agent(payload: AgentCreate) -> dict[str, Any]:
    state = ensure_state()
    if any(a["name"].casefold() == payload.name.casefold() for a in state["agents"]):
        raise HTTPException(409, "Agent names must be unique. Roles may be shared.")
    agent = {"id": f"agent-{uuid.uuid4().hex[:10]}", **payload.model_dump(),
             "status": "idle", "created_at": now_iso(), "current_task_id": None}
    state["agents"].append(agent)
    write_state(state)
    await publish("agent.created", f"{agent['name']} joined as {agent['role']}", {"agent": agent})
    return agent


@app.patch("/api/v1/agents/{agent_id}")
async def update_agent(agent_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    allowed = {"status", "specialization", "instructions"}
    if set(payload) - allowed:
        raise HTTPException(400, "Only status, specialization and instructions can be updated here.")
    state = ensure_state()
    agent = next((a for a in state["agents"] if a["id"] == agent_id), None)
    if not agent:
        raise HTTPException(404, "Agent not found")
    agent.update(payload)
    write_state(state)
    await publish("agent.updated", f"{agent['name']} updated", {"agent": agent})
    return agent


@app.get("/api/v1/tasks")
async def get_tasks() -> list[dict[str, Any]]:
    return ensure_state()["tasks"]


@app.post("/api/v1/tasks", status_code=201)
async def create_task(payload: TaskCreate) -> dict[str, Any]:
    state = ensure_state()
    if payload.agent_id and not any(a["id"] == payload.agent_id for a in state["agents"]):
        raise HTTPException(404, "Assigned agent not found")
    task = {"id": f"task-{uuid.uuid4().hex[:10]}", **payload.model_dump(),
            "status": "queued", "created_at": now_iso(), "updated_at": now_iso(),
            "evidence": [], "retry_count": 0}
    state["tasks"].append(task)
    if payload.approval_required:
        approval = {"id": f"approval-{uuid.uuid4().hex[:10]}", "kind": "task_execution",
                    "task_id": task["id"], "status": "pending", "created_at": now_iso()}
        state["approvals"].append(approval)
        task["approval_id"] = approval["id"]
    write_state(state)
    await publish("task.created", f"Task created: {task['title']}", {"task": task})
    return task


@app.patch("/api/v1/tasks/{task_id}")
async def update_task(task_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    allowed = {"status", "agent_id", "priority", "evidence", "description"}
    if set(payload) - allowed:
        raise HTTPException(400, "Unsupported task fields")
    state = ensure_state()
    task = next((t for t in state["tasks"] if t["id"] == task_id), None)
    if not task:
        raise HTTPException(404, "Task not found")
    if payload.get("status") == "running" and task.get("approval_required") and task.get("approval_id"):
        approval = next((a for a in state["approvals"] if a["id"] == task["approval_id"]), None)
        if approval and approval["status"] != "approved":
            raise HTTPException(403, "Task requires approval before execution")
    task.update(payload)
    task["updated_at"] = now_iso()
    write_state(state)
    await publish("task.updated", f"Task updated: {task['title']}", {"task": task})
    return task


@app.get("/api/v1/approvals")
async def get_approvals() -> list[dict[str, Any]]:
    return ensure_state()["approvals"]


@app.post("/api/v1/approvals/{approval_id}/decision")
async def decide_approval(approval_id: str, payload: ApprovalDecision) -> dict[str, Any]:
    state = ensure_state()
    approval = next((a for a in state["approvals"] if a["id"] == approval_id), None)
    if not approval:
        raise HTTPException(404, "Approval not found")
    if approval["status"] != "pending":
        raise HTTPException(409, "Approval has already been decided")
    approval.update({"status": payload.decision, "note": payload.note, "decided_at": now_iso()})
    task = next((t for t in state["tasks"] if t["id"] == approval.get("task_id")), None)
    if task and payload.decision == "rejected":
        task["status"] = "blocked"
    write_state(state)
    await publish("approval.decided", f"Approval {payload.decision}", {"approval": approval, "task": task})
    return approval


@app.post("/api/v1/project/connect")
async def connect_project(payload: ProjectConnect) -> dict[str, Any]:
    project_path = Path(payload.path).expanduser().resolve()
    if not project_path.exists() or not project_path.is_dir():
        raise HTTPException(400, "Project path must be an existing directory")
    spec = Path(payload.game_spec_path).expanduser().resolve() if payload.game_spec_path else None
    if spec and not spec.is_file():
        raise HTTPException(400, "Game specification file does not exist")
    project = {"path": str(project_path), "name": project_path.name,
               "game_spec_path": str(spec) if spec else None, "connected_at": now_iso()}
    state = ensure_state()
    state["project"] = project
    write_state(state)
    await publish("project.connected", f"Connected project {project['name']}", {"project": project})
    return project


@app.get("/api/v1/system/capabilities")
async def capabilities() -> dict[str, Any]:
    cli = shutil.which(settings.claude_cli_path)
    return {"claude_cli": {"available": bool(cli), "path": cli},
            "project": {"configured": bool(settings.project_path and settings.project_path.exists()),
                        "path": str(settings.project_path) if settings.project_path else None},
            "limits": {"max_concurrent_agents": settings.max_concurrent_agents,
                       "max_retries": settings.max_retries,
                       "task_timeout_seconds": settings.task_timeout_seconds},
            "execution_enabled": False,
            "execution_note": "Agent process execution is intentionally gated until the CLI adapter and permission contract pass local validation."}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await manager.connect(websocket)
    try:
        await websocket.send_json({"type": "connected", "state": ensure_state()})
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
