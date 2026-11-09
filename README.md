# ORCHESTRA

A local-first AI engineering command center for coordinating Claude Code agents on macOS.

> **Status:** Phase 4 — foundation scaffold. The dashboard and API foundation are being built; Claude Code process orchestration, persistent agent execution, live terminal streaming, and recovery are not yet implemented.

## Product direction

ORCHESTRA uses a Supervisor (AI CTO) to inspect a project, prepare a plan, request approval, coordinate named agents, and verify work. The user remains the final authority for scope changes, sensitive actions, merges, and releases.

## Architecture

- **Frontend:** Next.js, TypeScript, Tailwind CSS
- **Backend:** Python, FastAPI, asyncio
- **Live updates:** WebSockets
- **Execution workers:** Claude Code CLI (integration pending)
- **Persistence:** JSON state and JSONL event history; no SQL database
- **Source control:** Git with isolated worktrees and protected main-branch workflow
- **Runtime:** Localhost-first macOS controller

## Design

Dark cinematic command center with an immersive overview and clean engineering workspaces. Agents have persistent human-style names and explicit roles; multiple agents may share a role.

## Development principles

1. The controller owns orchestration and project state; Claude Code sessions are execution workers.
2. Plans are approved before execution.
3. Progress is distinguished as agent-reported or independently verified.
4. Risky, destructive, out-of-scope, and release actions require approval.
5. Recovery is bounded and evidence-based; no infinite retries.
6. Dashboard monitoring should not consume model-inference tokens.

## Repository layout

```
frontend/   Next.js dashboard
backend/    FastAPI local controller
docs/       Architecture and implementation notes
```

## Current foundation

The initial scaffold establishes the visual dashboard, illustrative agent/activity data, basic FastAPI state and agent endpoints, a WebSocket endpoint, and JSON/JSONL persistence. Demo agent activity is illustrative only; it does not represent live Claude Code processes.

## Local development

See the frontend and backend directories for their respective setup instructions. Claude Code integration and end-to-end runtime validation are upcoming implementation tasks.
