export type AgentStatus = 'Working' | 'Testing' | 'Review' | 'Idle';
export type Agent = { id: string; name: string; role: string; task: string; status: AgentStatus; progress: number };
export const agents: Agent[] = [
  { id: 'ag-01', name: 'Alex', role: 'Game Developer', task: 'Implement game mechanics', status: 'Working', progress: 78 },
  { id: 'ag-02', name: 'Maya', role: 'Game Developer', task: 'Build UI and animations', status: 'Working', progress: 64 },
  { id: 'ag-03', name: 'Isha', role: 'QA Engineer', task: 'Run regression suite', status: 'Testing', progress: 52 },
  { id: 'ag-04', name: 'Dev', role: 'QA Engineer', task: 'Verify edge cases', status: 'Testing', progress: 47 },
  { id: 'ag-05', name: 'Karan', role: 'Code Reviewer', task: 'Review implementation', status: 'Review', progress: 90 },
  { id: 'ag-06', name: 'Rohan', role: 'Math Verification', task: 'Verify payout calculations', status: 'Working', progress: 68 }
];
export const activity = [
  'Isha completed a regression test batch',
  'Alex pushed changes to the feature worktree',
  'Karan submitted a code review',
  'Supervisor prepared the next execution plan'
];
