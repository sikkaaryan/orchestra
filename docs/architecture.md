# ORCHESTRA architecture baseline

## Trust boundaries
The Next.js frontend is a localhost UI. The FastAPI controller owns durable state, process lifecycle, permissions and event history. Claude Code is an execution worker, not the source of truth.

## Core domains
- Project: repository path, branch, game specification, milestones and configuration.
- Agent identity: stable ID, human-style name, role, specialization and performance history. Role is not unique.
- Assignment: task, scope, allowed paths, worktree, acceptance criteria and approval reference.
- Event log: append-only JSONL record of lifecycle and verification events.
- Project Brain: versioned JSON documents for architecture, decisions, requirements, risks, bugs and verified knowledge.

## Safety invariants
1. No agent launches before an approved plan.
2. Every agent runs with an explicit assignment and scope.
3. Destructive or sensitive operations require explicit approval.
4. Main branch is protected; no silent merge or release.
5. Agent claims and verified evidence are represented separately.
6. Restart recovery reconciles controller state, process state and Git state before resuming work.
7. The controller binds to loopback by default.
8. Credentials are never scraped or persisted.

## Integration milestones
1. Validate installed Claude Code CLI capabilities and company policy.
2. Implement a supervised process adapter with bounded output capture.
3. Add lifecycle, pause/stop and crash reconciliation.
4. Add isolated Git worktree management.
5. Add approval-gated Supervisor planning and execution.
6. Add QA, game execution and independent verification adapters.
