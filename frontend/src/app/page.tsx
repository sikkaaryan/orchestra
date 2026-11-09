'use client';
import { useState } from 'react';
import { Activity, BrainCircuit, ChartNoAxesCombined, CheckCircle2, ChevronRight, CircleHelp, Clock3, Code2, Command, FileText, GitBranch, Layers3, LayoutDashboard, ListChecks, MessageSquare, Search, ShieldCheck, Sparkles, Users, Workflow, Zap } from 'lucide-react';
import { agents, activity } from '@/lib/demo-data';

const nav = [
  ['Command Center', LayoutDashboard], ['Supervisor', MessageSquare], ['Agents', Users],
  ['Workflow', Workflow], ['Code Workspace', Code2], ['Project Brain', BrainCircuit],
  ['QA & Testing', ShieldCheck], ['Reports & Analytics', ChartNoAxesCombined]
] as const;
function Metric({ icon: Icon, value, label, tone }: { icon: any; value: string; label: string; tone: string }) {
  return <div className="metric"><div className={`metric-icon ${tone}`}><Icon size={21}/></div><div><strong>{value}</strong><span>{label}</span></div></div>;
}
export default function Home() {
  const [active, setActive] = useState('Command Center');
  return <main className="shell">
    <aside className="sidebar">
      <div className="brand"><div className="brand-orb"/><div><b>ORCHESTRA</b><small>AI Engineering Command Center</small></div></div>
      <nav>{nav.map(([label, Icon]) => <button key={label} onClick={() => setActive(label)} className={active === label ? 'selected' : ''}><Icon size={18}/>{label}</button>)}</nav>
      <div className="project-chip"><div className="game-icon"><Command size={21}/></div><div><b>Game Project</b><small>Connected workspace</small><em>Local project not connected</em></div></div>
      <div className="user-chip"><div className="avatar">AS</div><div><b>Project Owner</b><small>Administrator</small></div></div>
    </aside>
    <section className="content">
      <header className="topbar"><div className="search"><Search size={16}/> Search project, agents, tasks… <kbd>⌘ K</kbd></div><div className="top-status"><span className="dot green"/> Controller UI preview <span className="divider"/> <span className="pill">V1 FOUNDATION</span></div></header>
      <div className="hero"><div className="eyebrow">ORCHESTRA / COMMAND CENTER</div><h1>{active}</h1><p>Your engineering command center. Plan, delegate, monitor, verify and deliver.</p><div className="hero-glow"/></div>
      <div className="notice"><CircleHelp size={17}/><span><b>Foundation preview:</b> displayed agent names and metrics are illustrative demo data; no Claude agents are running yet.</span></div>
      <div className="metrics">
        <Metric icon={Zap} value="—" label="Active agents" tone="purple"/><Metric icon={ListChecks} value="—" label="Tasks in progress" tone="green"/><Metric icon={CheckCircle2} value="—" label="Verified today" tone="blue"/><Metric icon={Clock3} value="—" label="Delivery estimate" tone="amber"/>
      </div>
      <div className="grid-main">
        <section className="panel project-panel"><div className="panel-head"><div><span className="eyebrow">CURRENT PROJECT</span><h2>Connect a game repository</h2></div><span className="status neutral">Awaiting setup</span></div><p className="muted">ORCHESTRA will inspect your repository and game specification before the Supervisor proposes an execution plan.</p><div className="project-actions"><button className="primary"><GitBranch size={16}/> Connect repository</button><button><FileText size={16}/> Add game specification</button></div><div className="progress-line"><span style={{width:'8%'}}/></div><div className="progress-meta"><span>Workspace setup</span><b>Not configured</b></div></section>
        <section className="panel supervisor"><div className="panel-head"><div className="section-title"><Sparkles size={18}/> <h2>Supervisor (AI CTO)</h2></div><span className="status neutral">Not connected</span></div><div className="supervisor-message"><div className="orb-small"/><div><b>Ready to understand your project.</b><p>Once a repository is connected, I can inspect its structure, identify the required specialists and prepare a plan for your approval.</p></div></div><button className="wide"><MessageSquare size={16}/> Open Supervisor workspace <ChevronRight size={16}/></button></section>
      </div>
      <div className="grid-bottom">
        <section className="panel"><div className="panel-head"><div className="section-title"><Users size={18}/><h2>Agent roster</h2></div><span className="muted small">Persistent identities · multiple agents per role</span></div><div className="agent-list">{agents.map(a=><div className="agent-row" key={a.id}><div className="avatar agent-avatar">{a.name.slice(0,1)}</div><div className="agent-info"><b>{a.name}</b><small>{a.role}</small></div><div className="agent-task">{a.task}</div><span className={`status ${a.status.toLowerCase()}`}>{a.status}</span><div className="bar"><span style={{width:`${a.progress}%`}}/></div></div>)}</div><p className="footnote">Illustrative roster only — agents are not launched by this preview.</p></section>
        <section className="panel"><div className="panel-head"><div className="section-title"><Activity size={18}/><h2>Activity stream</h2></div><span className="status neutral">Demo</span></div><div className="timeline">{activity.map((item,i)=><div className="event" key={i}><span className="event-dot"/><div>{item}<small>{i+2} min ago · sample event</small></div></div>)}</div><div className="panel-head subhead"><div className="section-title"><Layers3 size={17}/><h2>Execution lifecycle</h2></div></div><div className="lifecycle"><span>Plan</span><i/><span>Approve</span><i/><span>Execute</span><i/><span>Verify</span></div></section>
      </div>
      <footer>ORCHESTRA <span>Local-first · Evidence-led · Human-approved</span><span>Phase 4 · Foundation scaffold</span></footer>
    </section>
  </main>;
}
