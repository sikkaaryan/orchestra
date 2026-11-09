from __future__ import annotations

import asyncio
import json
import os
import shutil
import signal
import uuid
from pathlib import Path
from typing import Any

from .config import settings
from .store import append_event, read_state, write_state, now_iso

ROOT_MARKERS = {".git", "package.json", "pyproject.toml", "Cargo.toml", "game.project", "project.godot"}


def _state() -> dict[str, Any]:
    value = read_state()
    for key, default in (("agents", []), ("tasks", []), ("approvals", []), ("project", None), ("brain", {}), ("qa_runs", [])):
        value.setdefault(key, default)
    return value


def _save(state: dict[str, Any]) -> None:
    write_state(state)


def _emit(kind: str, message: str, metadata: dict[str, Any] | None = None) -> None:
    append_event(kind, message, metadata or {})


class AgentRuntime:
    """Owns Claude CLI child processes; workers are never detached from the controller."""
    def __init__(self) -> None:
        self.processes: dict[str, asyncio.subprocess.Process] = {}
        self.tasks: dict[str, asyncio.Task] = {}
        self.output_locks: dict[str, asyncio.Lock] = {}
        self.semaphore = asyncio.Semaphore(settings.max_concurrent_agents)

    def capabilities(self) -> dict[str, Any]:
        cli = shutil.which(settings.claude_cli_path)
        return {
            "claude_cli": {"available": bool(cli), "path": cli},
            "max_concurrent_agents": settings.max_concurrent_agents,
            "running_processes": len(self.processes),
            "permission_mode": settings.permission_mode,
            "approval_for_commands": settings.require_approval_for_commands,
            "destructive_commands_allowed": settings.allow_destructive_commands,
        }

    async def launch(self, task_id: str) -> dict[str, Any]:
        state = _state()
        task = next((item for item in state["tasks"] if item["id"] == task_id), None)
        if not task:
            raise ValueError("Task not found")
        if task_id in self.tasks and not self.tasks[task_id].done():
            raise ValueError("Task is already running")
        if len(self.processes) >= settings.max_concurrent_agents:
            raise ValueError("Maximum concurrent agent capacity reached")
        approval_id = task.get("approval_id")
        if task.get("approval_required", True):
            approval = next((a for a in state["approvals"] if a["id"] == approval_id), None)
            if not approval or approval["status"] != "approved":
                raise PermissionError("Owner approval is required before launching this task")
        project = state.get("project")
        if not project or not Path(project["path"]).is_dir():
            raise ValueError("Connect a valid local project before launching agents")
        cli = shutil.which(settings.claude_cli_path)
        if not cli:
            raise RuntimeError("Claude Code CLI was not found on PATH. Set CLAUDE_CLI_PATH if installed elsewhere.")
        agent = next((a for a in state["agents"] if a["id"] == task.get("agent_id")), None)
        if not agent:
            agent = next((a for a in state["agents"] if a["role"].casefold() == task["role"].casefold() and a.get("status") == "idle"), None)
        if not agent:
            raise ValueError("Assign an idle agent with the required role before launching")
        worktree = self._create_worktree(Path(project["path"]), task_id)
        prompt = self._prompt(task, agent, project)
        args = [cli, "-p", prompt, "--output-format", "stream-json", "--verbose", "--permission-mode", settings.permission_mode]
        if settings.claude_model:
            args += ["--model", settings.claude_model]
        process = await asyncio.create_subprocess_exec(
            *args, cwd=str(worktree), stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
            start_new_session=(os.name != "nt"),
        )
        self.processes[task_id] = process
        self.output_locks[task_id] = asyncio.Lock()
        task.update({"status": "running", "pid": process.pid, "worktree": str(worktree), "started_at": now_iso(), "updated_at": now_iso()})
        agent.update({"status": "working", "current_task_id": task_id})
        _save(state)
        _emit("agent.started", f"{agent['name']} started {task['title']}", {"task_id": task_id, "agent_id": agent["id"], "pid": process.pid, "worktree": str(worktree)})
        self.tasks[task_id] = asyncio.create_task(self._monitor(task_id, process, agent["id"]))
        return {"task_id": task_id, "agent": agent, "pid": process.pid, "worktree": str(worktree), "status": "running"}

    def _create_worktree(self, repo: Path, task_id: str) -> Path:
        if not (repo / ".git").exists():
            raise ValueError("Connected project must be a Git repository to launch isolated agents")
        base = repo / ".orchestra" / "worktrees"
        base.mkdir(parents=True, exist_ok=True)
        target = base / task_id
        branch = "orchestra/" + task_id
        if target.exists():
            raise ValueError("Worktree directory already exists; inspect it before retrying")
        import subprocess
        result = subprocess.run(["git", "-C", str(repo), "worktree", "add", "-b", branch, str(target), "HEAD"], capture_output=True, text=True, timeout=30)
        if result.returncode:
            raise RuntimeError("Could not create isolated Git worktree: " + result.stderr[-1500:])
        return target

    def _prompt(self, task: dict[str, Any], agent: dict[str, Any], project: dict[str, Any]) -> str:
        spec = project.get("game_spec_path")
        spec_note = f"Game specification: {spec}" if spec else "No separate game specification is configured."
        return (
            f"You are {agent['name']}, acting as {agent['role']} in ORCHESTRA.\n"
            f"Specialization: {agent.get('specialization','')}\n"
            f"Additional instructions: {agent.get('instructions','')}\n"
            f"Project: {project['name']}\n{spec_note}\n"
            f"TASK: {task['title']}\nDETAILS: {task.get('description','')}\n"
            "Work only within this task's scope and this isolated Git worktree. Do not merge, push, release, "
            "delete user data, change credentials, or perform destructive operations. Run relevant tests. "
            "Summarize files changed, tests run, results, remaining risks, and commit hash if you create a commit. "
            "Do not claim verification you did not perform."
        )

    async def _monitor(self, task_id: str, process: asyncio.subprocess.Process, agent_id: str) -> None:
        output_file = settings.data_dir / "terminals" / f"{task_id}.jsonl"
        output_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            assert process.stdout is not None
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                raw = line.decode("utf-8", errors="replace").rstrip()
                record = {"at": now_iso(), "stream": "stdout", "text": raw}
                async with self.output_locks[task_id]:
                    with output_file.open("a", encoding="utf-8") as handle:
                        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
                _emit("agent.output", raw[:500], {"task_id": task_id})
            code = await process.wait()
            state = _state()
            task = next((t for t in state["tasks"] if t["id"] == task_id), None)
            agent = next((a for a in state["agents"] if a["id"] == agent_id), None)
            if task:
                task.update({"status": "completed" if code == 0 else "failed", "exit_code": code, "finished_at": now_iso(), "updated_at": now_iso()})
            if agent:
                agent.update({"status": "idle", "current_task_id": None})
            _save(state)
            _emit("agent.finished", f"Agent process exited with code {code}", {"task_id": task_id, "exit_code": code})
        except asyncio.CancelledError:
            if process.returncode is None:
                process.terminate()
                await process.wait()
            raise
        finally:
            self.processes.pop(task_id, None)

    async def stop(self, task_id: str) -> dict[str, Any]:
        process = self.processes.get(task_id)
        if not process:
            raise ValueError("No live process for this task")
        if process.returncode is None:
            if os.name != "nt":
                try:
                    os.killpg(process.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
            else:
                process.terminate()
        try:
            await asyncio.wait_for(process.wait(), timeout=8)
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
        monitor = self.tasks.get(task_id)
        if monitor and not monitor.done():
            await monitor
        return {"task_id": task_id, "status": "stopped"}

    def terminal(self, task_id: str, limit: int = 200) -> list[dict[str, Any]]:
        path = settings.data_dir / "terminals" / f"{task_id}.jsonl"
        if not path.exists():
            return []
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()[-max(1, min(limit, 1000)):]
        result = []
        for line in lines:
            try:
                result.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return result


runtime = AgentRuntime()


def recover_interrupted() -> dict[str, Any]:
    state = _state()
    interrupted = []
    for task in state["tasks"]:
        if task.get("status") == "running":
            task.update({"status": "interrupted", "interrupted_at": now_iso(), "recovery_note": "Controller restarted; previous child process cannot be safely resumed automatically."})
            interrupted.append(task["id"])
    for agent in state["agents"]:
        if agent.get("status") == "working":
            agent.update({"status": "interrupted", "current_task_id": None})
    if interrupted:
        _save(state)
        _emit("recovery.interrupted", f"Marked {len(interrupted)} task(s) interrupted after controller restart", {"task_ids": interrupted})
    return {"interrupted_tasks": interrupted, "recovered_at": now_iso()}


def build_brain() -> dict[str, Any]:
    state = _state()
    project = state.get("project")
    snapshot: dict[str, Any] = {
        "updated_at": now_iso(), "project": project, "agents": state["agents"],
        "tasks": state["tasks"], "approvals": state["approvals"],
        "decisions": state.get("decisions", []), "risks": [], "milestones": [],
    }
    if project and Path(project["path"]).is_dir():
        root = Path(project["path"])
        files = []
        for path in root.rglob("*"):
            if any(part in {".git", "node_modules", ".next", ".venv", ".orchestra"} for part in path.parts):
                continue
            if path.is_file():
                try:
                    files.append(str(path.relative_to(root)))
                except ValueError:
                    pass
            if len(files) >= 500:
                break
        snapshot["repository"] = {"file_count_sampled": len(files), "files": files, "git_branch": _git_branch(root)}
        snapshot["game_spec_excerpt"] = None
        spec = project.get("game_spec_path")
        if spec and Path(spec).is_file():
            snapshot["game_spec_excerpt"] = Path(spec).read_text(encoding="utf-8", errors="replace")[:12000]
    return snapshot


def _git_branch(root: Path) -> str | None:
    import subprocess
    result = subprocess.run(["git", "-C", str(root), "branch", "--show-current"], capture_output=True, text=True, timeout=5)
    return result.stdout.strip() if result.returncode == 0 else None


def create_qa_debate(task_id: str, evidence: str = "") -> dict[str, Any]:
    state = _state()
    task = next((t for t in state["tasks"] if t["id"] == task_id), None)
    if not task:
        raise ValueError("Task not found")
    roles = [
        ("Correctness Reviewer", "Check requirements, logic, edge cases and correctness."),
        ("Test Engineer", "Check test coverage, reproducibility and regression risks."),
        ("Security Reviewer", "Check trust boundaries, permissions, secrets and destructive behavior."),
        ("Architecture Reviewer", "Check maintainability, coupling, compatibility and scope."),
        ("Independent Challenger", "Try to falsify the claims and identify missing evidence."),
    ]
    findings = []
    for role, remit in roles:
        findings.append({"reviewer": role, "remit": remit, "status": "not_run", "finding": None, "evidence": evidence})
    run = {"id": "qa-" + uuid.uuid4().hex[:10], "task_id": task_id, "status": "awaiting_reviewers", "created_at": now_iso(), "reviewers": findings, "fixes": [], "note": "Five independent review slots created. Findings must be supplied by actual reviewers; no synthetic pass is assumed."}
    state.setdefault("qa_runs", []).append(run)
    _save(state)
    _emit("qa.created", f"Five-reviewer QA debate created for {task['title']}", {"qa_id": run["id"], "task_id": task_id})
    return run
