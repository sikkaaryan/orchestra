'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { Activity, BrainCircuit, Check, CircleAlert, Code2, GitBranch, LayoutDashboard, ListChecks, MessageSquare, Plus, RefreshCw, ShieldCheck, Users, Workflow, X } from 'lucide-react';

const API = process.env.NEXT_PUBLIC_ORCHESTRA_API_URL || 'http://127.0.0.1:8787';
type Agent = { id: string; name: string; role: string; specialization?: string; status: string; current_task_id?: string | null };
type Task = { id: string; title: string; description: string; role: string; agent_id?: string | null; status: string; priority: string; approval_id?: string; approval_required: boolean };
type Approval = { id: string; kind: string; task_id?: string; status: string; created_at: string };
type State = { agents: Agent[]; tasks: Task[]; approvals: Approval[]; project: {name:string;path:string;game_spec_path?:string|null}|null; events: {id:string;at:string;kind:string;message:string}[] };
const empty: State = { agents: [], tasks: [], approvals: [], project: null, events: [] };
const nav = [['Command Center',LayoutDashboard],['Supervisor',MessageSquare],['Agents',Users],['Workflow',Workflow],['Code Workspace',Code2],['Project Brain',BrainCircuit],['QA & Testing',ShieldCheck]] as const;

export default function Home() {
  const [active,setActive] = useState('Command Center');
  const [state,setState] = useState<State>(empty);
  const [online,setOnline] = useState(false);
  const [error,setError] = useState('');
  const [busy,setBusy] = useState(false);
  const [projectPath,setProjectPath] = useState('');
  const [specPath,setSpecPath] = useState('');
  const [agentName,setAgentName] = useState('');
  const [agentRole,setAgentRole] = useState('Game Developer');
  const [taskTitle,setTaskTitle] = useState('');
  const [taskDescription,setTaskDescription] = useState('');
  const [taskRole,setTaskRole] = useState('Game Developer');
  const [taskAgent,setTaskAgent] = useState('');
  const [showAgent,setShowAgent] = useState(false);
  const [showTask,setShowTask] = useState(false);
  const [objective,setObjective] = useState('');
  const [plan,setPlan] = useState<any>(null);
  const [terminal,setTerminal] = useState<any>(null);
  const [qaRuns,setQaRuns] = useState<any[]>([]);

  const refresh = useCallback(async () => {
    try {
      const response = await fetch(API + '/api/v1/state',{cache:'no-store'});
      if (!response.ok) throw new Error('Controller returned ' + response.status);
      setState({...empty,...await response.json()});
      setOnline(true); setError('');
    } catch (e) { setOnline(false); setError(e instanceof Error ? e.message : 'Controller unavailable'); }
  },[]);
  useEffect(() => { void refresh(); const timer=setInterval(()=>void refresh(),3000); return ()=>clearInterval(timer); },[refresh]);

  async function request(path:string,method='POST',body?:unknown) {
    setBusy(true); setError('');
    try {
      const response=await fetch(API+path,{method,headers:{'Content-Type':'application/json'},body:body?JSON.stringify(body):undefined});
      const data=await response.json().catch(()=>({}));
      if(!response.ok) throw new Error(data.detail || 'Request failed ('+response.status+')');
      await refresh(); return data;
    } catch(e) {setError(e instanceof Error?e.message:'Request failed'); return null;}
    finally {setBusy(false);}
  }
  const pending=state.approvals.filter(a=>a.status==='pending');
  const activeTasks=state.tasks.filter(t=>['running','in_progress'].includes(t.status));
  const grouped=useMemo(()=>state.agents.reduce<Record<string,Agent[]>>((acc,a)=>{(acc[a.role]??=[]).push(a);return acc;},{}),[state.agents]);

  return <main className="shell">
    <aside className="sidebar">
      <div className="brand"><div className="brand-orb"/><div><b>ORCHESTRA</b><small>AI Engineering Command Center</small></div></div>
      <nav>{nav.map(([label,Icon])=><button key={label} onClick={()=>setActive(label)} className={active===label?'selected':''}><Icon size={18}/>{label}</button>)}</nav>
      <div className="project-chip"><div className="game-icon"><GitBranch size={21}/></div><div><b>{state.project?.name||'No project connected'}</b><small>Local workspace</small><em>{state.project?'Connected':'Awaiting setup'}</em></div></div>
      <div className="user-chip"><div className="avatar">OR</div><div><b>Project Owner</b><small>Administrator</small></div></div>
    </aside>
    <section className="content">
      <header className="topbar"><div className="search"><Activity size={16}/> Local controller · {API}</div><div className="top-status"><span className={'dot '+(online?'green':'amber')}/>{online?'Controller connected':'Controller offline'} <button className="icon-button" onClick={()=>void refresh()} aria-label="Refresh"><RefreshCw size={14}/></button></div></header>
      <div className="hero"><div className="eyebrow">ORCHESTRA / LOCAL COMMAND CENTER</div><h1>{active}</h1><p>Plan, delegate, monitor and verify your engineering work.</p><div className="hero-glow"/></div>
      {error&&<div className="notice error"><CircleAlert size={17}/>{error}</div>}
      {!online&&<div className="notice"><CircleAlert size={17}/><span>Start the local controller with <code>python3 setup.py</code>. The dashboard will reconnect automatically.</span></div>}
      <div className="metrics">
        <Metric icon={Users} value={String(state.agents.length)} label="Registered agents" tone="purple"/>
        <Metric icon={ListChecks} value={String(activeTasks.length)} label="Active tasks" tone="green"/>
        <Metric icon={ShieldCheck} value={String(pending.length)} label="Pending approvals" tone="amber"/>
        <Metric icon={Check} value={String(state.tasks.filter(t=>t.status==='completed').length)} label="Completed tasks" tone="blue"/>
      </div>
      <div className="grid-main">
        <section className="panel project-panel"><div className="panel-head"><div><span className="eyebrow">CURRENT PROJECT</span><h2>{state.project?.name||'Connect a local repository'}</h2></div><span className={'status '+(state.project?'working':'neutral')}>{state.project?'Connected':'Not configured'}</span></div>
          <p className="muted">{state.project?.path||'Enter the absolute path to a local game repository. The controller validates and stores the path on this Mac.'}</p>
          {!state.project&&<div className="form-stack"><input value={projectPath} onChange={e=>setProjectPath(e.target.value)} placeholder="/Users/you/projects/my-game"/><input value={specPath} onChange={e=>setSpecPath(e.target.value)} placeholder="Optional game specification path"/><button className="primary" disabled={!online||busy||!projectPath.trim()} onClick={()=>void request('/api/v1/project/connect','POST',{path:projectPath,game_spec_path:specPath||null})}><GitBranch size={16}/> Connect local project</button></div>}
          {state.project&&<div className="project-actions"><button onClick={()=>setProjectPath(state.project?.path||'')}>Path: {state.project.path}</button><button onClick={()=>setShowTask(true)}><Plus size={15}/> New task</button></div>}
        </section>
        <section className="panel supervisor"><div className="panel-head"><div className="section-title"><MessageSquare size={18}/><h2>Supervisor (AI CTO)</h2></div><span className="status neutral">Planning workspace</span></div><div className="supervisor-message"><div className="orb-small"/><div><b>Execution stays approval-gated.</b><p>Connect a project, register specialists and create tasks. Proposals are reviewable; workers start only after explicit approval.</p></div></div><div className="form-stack"><textarea value={objective} onChange={e=>setObjective(e.target.value)} placeholder="Describe the engineering objective..."/><button className="primary" disabled={!online||busy||objective.trim().length<5} onClick={async()=>{const r=await request('/api/v1/supervisor/plan','POST',{objective});if(r)setPlan(r);}}>Prepare plan proposal</button></div>{plan&&<div className="plan-preview"><b>Proposal · {plan.id}</b><p>{plan.objective}</p><small>{plan.suggested_roles?.join(', ')}</small><p>{plan.execution_policy}</p></div>}<button className="wide" onClick={()=>setActive('Project Brain')}>View project state <span>→</span></button></section>
      </div>
      <div className="grid-bottom">
        <section className="panel"><div className="panel-head"><div className="section-title"><Users size={18}/><h2>Agent roster</h2></div><button className="small-action" onClick={()=>setShowAgent(v=>!v)}><Plus size={14}/> Add agent</button></div>
          {showAgent&&<div className="inline-form"><input value={agentName} onChange={e=>setAgentName(e.target.value)} placeholder="Unique agent name"/><input value={agentRole} onChange={e=>setAgentRole(e.target.value)} placeholder="Role (roles can repeat)"/><button disabled={!online||busy||agentName.trim().length<2} onClick={async()=>{const r=await request('/api/v1/agents','POST',{name:agentName,role:agentRole});if(r){setAgentName('');setShowAgent(false);}}}>Create</button></div>}
          {state.agents.length===0?<p className="muted">No agents registered yet. Add named specialists; multiple agents may share a role.</p>:Object.entries(grouped).map(([role,list])=><div className="role-group" key={role}><div className="role-heading">{role} · {list.length}</div>{list.map(a=><div className="agent-row" key={a.id}><div className="avatar agent-avatar">{a.name.slice(0,1).toUpperCase()}</div><div className="agent-info"><b>{a.name}</b><small>{a.specialization||role}</small></div><span className={'status '+(a.status==='working'?'working':'neutral')}>{a.status}</span></div>)}</div>)}
        </section>
        <section className="panel"><div className="panel-head"><div className="section-title"><ListChecks size={18}/><h2>Task board</h2></div><button className="small-action" onClick={()=>setShowTask(v=>!v)}><Plus size={14}/> New task</button></div>
          {showTask&&<div className="form-stack"><input value={taskTitle} onChange={e=>setTaskTitle(e.target.value)} placeholder="Task title"/><textarea value={taskDescription} onChange={e=>setTaskDescription(e.target.value)} placeholder="Describe the expected outcome"/><input value={taskRole} onChange={e=>setTaskRole(e.target.value)} placeholder="Required role"/><select value={taskAgent} onChange={e=>setTaskAgent(e.target.value)}><option value="">Unassigned</option>{state.agents.map(a=><option key={a.id} value={a.id}>{a.name} · {a.role}</option>)}</select><button className="primary" disabled={!online||busy||taskTitle.trim().length<3} onClick={async()=>{const r=await request('/api/v1/tasks','POST',{title:taskTitle,description:taskDescription,role:taskRole,agent_id:taskAgent||null,approval_required:true});if(r){setTaskTitle('');setTaskDescription('');setShowTask(false);}}}>Create approval-gated task</button></div>}
          {state.tasks.length===0?<p className="muted">No tasks yet. Create a task to add it to the local board.</p>:state.tasks.slice().reverse().map(t=><div className="task-card" key={t.id}><div className="task-row"><div><b>{t.title}</b><small>{t.role} · {t.priority}</small></div><span className="status neutral">{t.status}</span></div><div className="task-tools">{t.status==='queued'&&<button disabled={busy||!online} onClick={()=>void request('/api/v1/tasks/'+t.id+'/launch')}>Launch</button>}{t.status==='running'&&<button onClick={()=>void request('/api/v1/tasks/'+t.id+'/stop')}>Stop</button>}<button onClick={async()=>{const r=await fetch(API+'/api/v1/tasks/'+t.id+'/terminal');setTerminal({id:t.id,lines:await r.json()});}}>Terminal</button><button onClick={async()=>{const r=await request('/api/v1/qa/tasks/'+t.id+'/debate','POST',{evidence:'Review the task diff and test output.'});if(r)setQaRuns(a=>[r,...a]);}}>5-reviewer QA</button></div></div>)}
        </section>
      </div>
      <section className="panel approvals-panel"><div className="panel-head"><div className="section-title"><ShieldCheck size={18}/><h2>Approval queue</h2></div><span className="status review">{pending.length} pending</span></div>
        {pending.length===0?<p className="muted">No pending approvals.</p>:pending.map(a=>{const task=state.tasks.find(t=>t.id===a.task_id);return <div className="approval-row" key={a.id}><div><b>{task?.title||a.kind}</b><small>Task execution · created {new Date(a.created_at).toLocaleString()}</small></div><div className="approval-actions"><button disabled={busy} onClick={()=>void request('/api/v1/approvals/'+a.id+'/decision','POST',{decision:'approved',note:'Approved by project owner'})}><Check size={14}/> Approve</button><button className="reject" disabled={busy} onClick={()=>void request('/api/v1/approvals/'+a.id+'/decision','POST',{decision:'rejected',note:'Rejected by project owner'})}><X size={14}/> Reject</button></div></div>})}
      </section>
      {terminal&&<section className="panel activity-panel"><div className="panel-head"><h2>Terminal · {terminal.id}</h2><button onClick={()=>setTerminal(null)}>Close</button></div><pre className="terminal-output">{terminal.lines.map((x:any)=>x.text).join('\n')||'No output yet'}</pre></section>}
      {qaRuns.map(run=><section className="panel activity-panel" key={run.id}><b>QA · {run.task_id}</b><p>{run.status} · {run.recommendation||'Awaiting reviewers'}</p><small>{run.reviewers?.map((x:any)=>x.reviewer+': '+x.status).join(' · ')}</small></section>)}
      <section className="panel activity-panel"><div className="panel-head"><div className="section-title"><Activity size={18}/><h2>Live activity</h2></div><span className="muted small">Auto-refresh · 3 seconds</span></div>{state.events.length===0?<p className="muted">Activity will appear here as you use the controller.</p>:state.events.slice().reverse().slice(0,12).map(e=><div className="event" key={e.id}><span className="event-dot"/><div>{e.message}<small>{e.kind} · {new Date(e.at).toLocaleString()}</small></div></div>)}</section>
      <footer>ORCHESTRA <span>Local-first · Evidence-led · Human-approved</span><span>Phase 4 · Connected dashboard</span></footer>
    </section>
  </main>;
}

function Metric({icon:Icon,value,label,tone}:{icon:any;value:string;label:string;tone:string}) {
  return <div className="metric"><div className={'metric-icon '+tone}><Icon size={20}/></div><div><strong>{value}</strong><span>{label}</span></div></div>;
}
