from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

APP_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = APP_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
STATE_FILE = DATA_DIR / "state.json"
EVENTS_FILE = DATA_DIR / "events.jsonl"

app = FastAPI(title="ORCHESTRA Local Controller", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

class AgentIdentity(BaseModel):
    id: str
    name: str
    role: str
    specialization: str = ""
    status: str = "idle"

class Event(BaseModel):
    type: str
    message: str
    data: dict[str, Any] = Field(default_factory=dict)

class ConnectionManager:
    def __init__(self) -> None:
        self.connections: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.connections.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self.connections.discard(websocket)

    async def broadcast(self, payload: dict[str, Any]) -> None:
        stale = []
        for connection in self.connections:
            try:
                await connection.send_json(payload)
            except Exception:
                stale.append(connection)
        for connection in stale:
            self.disconnect(connection)

manager = ConnectionManager()

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

def read_state() -> dict[str, Any]:
    if not STATE_FILE.exists():
        return {"schema_version": 1, "project": None, "agents": [], "tasks": [], "updated_at": utc_now()}
    return json.loads(STATE_FILE.read_text(encoding="utf-8"))

def write_state(state: dict[str, Any]) -> None:
    state["updated_at"] = utc_now()
    temp = STATE_FILE.with_suffix(".json.tmp")
    temp.write_text(json.dumps(state, indent=2), encoding="utf-8")
    temp.replace(STATE_FILE)

def append_event(event: dict[str, Any]) -> None:
    with EVENTS_FILE.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"timestamp": utc_now(), **event}) + "\n")

@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "orchestra-controller", "time": utc_now()}

@app.get("/api/v1/state")
async def get_state() -> dict[str, Any]:
    return read_state()

@app.get("/api/v1/agents")
async def get_agents() -> list[dict[str, Any]]:
    return read_state().get("agents", [])

@app.post("/api/v1/agents")
async def register_agent(agent: AgentIdentity) -> dict[str, Any]:
    state = read_state()
    agents = state.setdefault("agents", [])
    if any(existing.get("id") == agent.id for existing in agents):
        return {"created": False, "reason": "agent_id_already_exists"}
    record = agent.model_dump()
    agents.append(record)
    write_state(state)
    append_event({"type": "agent.registered", "agent_id": agent.id, "name": agent.name, "role": agent.role})
    await manager.broadcast({"type": "agent.registered", "agent": record})
    return {"created": True, "agent": record}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await manager.connect(websocket)
    try:
        await websocket.send_json({"type": "connected", "state": read_state()})
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
