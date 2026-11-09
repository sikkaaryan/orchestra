# ORCHESTRA

Local-first AI engineering command center for coordinating Claude Code agents on macOS.

## Current implementation

The dashboard, local controller, approval queue, Claude CLI launch adapter, Git worktree isolation, terminal event capture, project brain snapshot, restart recovery marking and five-reviewer QA workflow are implemented. Run the automated checks before relying on it for production work.

Important limitations: Supervisor planning currently creates a structured deterministic proposal from repository context; it is not an autonomous LLM CTO. QA creates five independent review slots and does not fabricate reviewer results. A reviewer must submit evidence. Controller restart marks prior running tasks interrupted; it does not silently resume stale Claude sessions.

## Requirements

- macOS or Linux
- Python 3.10+
- Node.js 20+ and npm
- Git
- Claude Code CLI installed and authenticated (`claude` works in Terminal)

## Quick start

```bash
git clone https://github.com/sikkaaryan/orchestra.git
cd orchestra
python3 setup.py --check
python3 setup.py
```

The setup script creates a virtual environment, installs dependencies, creates a local .env, and starts the dashboard at http://127.0.0.1:3000 and API docs at http://127.0.0.1:8787/docs. Press Ctrl+C to stop both services. Data is stored under backend/data/ and is ignored by Git.

## First use

1. Connect a local Git repository from the dashboard.
2. Register agents with unique names. Roles may be shared.
3. Create a task and assign an idle agent.
4. Approve the task in the approval queue.
5. Launch with POST /api/v1/tasks/{task_id}/launch.
6. Inspect output at GET /api/v1/tasks/{task_id}/terminal.
7. Stop with POST /api/v1/tasks/{task_id}/stop.

The CLI adapter uses the configured Claude Code permission mode and does not pass permission-bypass flags. Claude may request interactive permissions; unattended execution requires an explicitly configured and reviewed permission policy. Workers execute in dedicated Git worktrees under .orchestra/worktrees/. They do not merge, push or release.

## API routes

- GET /health and GET /api/v1/system/runtime
- GET /api/v1/state and GET /api/v1/brain
- POST /api/v1/supervisor/plan
- POST /api/v1/tasks, POST /api/v1/tasks/{id}/launch, POST /api/v1/tasks/{id}/stop
- GET /api/v1/tasks/{id}/terminal
- POST /api/v1/qa/tasks/{id}/debate and POST /api/v1/qa/{qa_id}/review

## Safety and recovery

Execution is approval-gated by default. Worktree isolation requires a Git repository. Concurrency and timeout settings are configurable. On restart, previously running tasks become interrupted; reconcile their worktree and Git state before relaunching. Never configure permission bypass for convenience. No automatic merge, push, release or destructive operation is performed.

## Tests

```bash
cd backend
../.venv/bin/python -m pytest -q
cd ../frontend
npm run build
```

The current UI exposes project connection, agent registration, task creation, approvals and activity. Terminal, Supervisor planning and QA reviewer workspaces are API-backed and remain to be integrated into the UI.
