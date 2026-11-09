from __future__ import annotations

from typing import Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from .runtime import runtime, recover_interrupted, build_brain, create_qa_debate, _state, _save, _emit
from .store import now_iso

router = APIRouter(prefix='/api/v1')

class QAReview(BaseModel):
    reviewer: str = Field(min_length=3, max_length=80)
    status: str = Field(pattern='^(pass|needs_fixes|blocked)$')
    finding: str = Field(min_length=3, max_length=8000)
    evidence: str = Field(default='', max_length=8000)

class PlanRequest(BaseModel):
    objective: str = Field(min_length=5, max_length=4000)

@router.get('/system/runtime')
async def runtime_capabilities() -> dict[str, Any]:
    return runtime.capabilities()

@router.post('/tasks/{task_id}/launch')
async def launch_task(task_id: str) -> dict[str, Any]:
    try: return await runtime.launch(task_id)
    except PermissionError as exc: raise HTTPException(403, str(exc))
    except ValueError as exc: raise HTTPException(400, str(exc))
    except RuntimeError as exc: raise HTTPException(503, str(exc))

@router.post('/tasks/{task_id}/stop')
async def stop_task(task_id: str) -> dict[str, Any]:
    try: return await runtime.stop(task_id)
    except ValueError as exc: raise HTTPException(404, str(exc))

@router.get('/tasks/{task_id}/terminal')
async def task_terminal(task_id: str, limit: int = 200) -> list[dict[str, Any]]:
    return runtime.terminal(task_id, limit)

@router.get('/brain')
async def project_brain() -> dict[str, Any]:
    return build_brain()

@router.post('/supervisor/plan')
async def supervisor_plan(payload: PlanRequest) -> dict[str, Any]:
    state = _state()
    project = state.get('project')
    if not project: raise HTTPException(400, 'Connect a project before planning')
    brain = build_brain()
    proposal = {'id': 'plan-' + __import__('uuid').uuid4().hex[:10], 'objective': payload.objective,
        'project': project, 'repository_context': brain.get('repository', {}),
        'existing_task_count': len(state.get('tasks', [])),
        'suggested_roles': ['Game Developer', 'QA Engineer', 'Code Reviewer', 'Math Verification'],
        'execution_policy': 'Planning never launches tasks. Create tasks and obtain owner approval first.',
        'status': 'proposed', 'created_at': now_iso()}
    state.setdefault('plans', []).append(proposal); _save(state)
    _emit('supervisor.plan_created', 'Supervisor planning proposal created', {'plan_id': proposal['id']})
    return proposal

@router.post('/qa/tasks/{task_id}/debate')
async def start_qa_debate(task_id: str, payload: dict[str, str] | None = None) -> dict[str, Any]:
    try: return create_qa_debate(task_id, (payload or {}).get('evidence', ''))
    except ValueError as exc: raise HTTPException(404, str(exc))

@router.post('/qa/{qa_id}/review')
async def submit_qa_review(qa_id: str, payload: QAReview) -> dict[str, Any]:
    state = _state(); run = next((item for item in state.get('qa_runs', []) if item['id'] == qa_id), None)
    if not run: raise HTTPException(404, 'QA run not found')
    reviewer = next((item for item in run['reviewers'] if item['reviewer'] == payload.reviewer), None)
    if not reviewer: raise HTTPException(404, 'Reviewer slot not found')
    reviewer.update({'status': payload.status, 'finding': payload.finding, 'evidence': payload.evidence, 'submitted_at': now_iso()})
    statuses = [item['status'] for item in run['reviewers']]
    run['status'] = 'complete' if all(s != 'not_run' for s in statuses) else 'in_review'
    if 'needs_fixes' in statuses: run['recommendation'] = 'fixes_required'
    elif 'blocked' in statuses: run['recommendation'] = 'blocked'
    elif all(s == 'pass' for s in statuses): run['recommendation'] = 'review_passed_not_release_approval'
    _save(state); _emit('qa.review_submitted', payload.reviewer + ' submitted QA findings', {'qa_id': qa_id, 'status': payload.status})
    return run

@router.get('/qa')
async def list_qa() -> list[dict[str, Any]]:
    return _state().get('qa_runs', [])

@router.get('/recovery')
async def recovery_status() -> dict[str, Any]:
    state = _state()
    return {'interrupted_tasks': [t for t in state['tasks'] if t.get('status') == 'interrupted'],
        'active_process_ids': {key: process.pid for key, process in runtime.processes.items()},
        'policy': 'Interrupted Claude sessions are not resumed blindly. Reconcile worktree and Git state, then explicitly relaunch an approved task.'}
