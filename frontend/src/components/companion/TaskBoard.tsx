import { useEffect, useRef, useState } from 'react';
import './taskBoard.css';
import { useTaskState } from '../../stores/taskState';
import type { DesktopTimings } from '../../services/desktop';
import { YouTubeControls, VideoStudyResult, type VideoModels, type StudyReport } from './YouTubeControls';
import { CodingLog } from './CodingLog';
import { CallReminderList } from '../hud/PhoneReminders';

export type Job = { id: string; tool: string; lane: 'desktop' | 'coding' | 'study'; mode: string; title: string; status: string; progress: string; revisions: string[]; project?:{path:string;runner:string}; demoGeneration?:string|null; telegramNotification?:{status:'sending'|'sent'|'unconfirmed'|'rejected'|'configuration_required'}; timings?: DesktopTimings; report: {kind?:'youtube'|'browser'|'destination'; summary: string; changedFiles: string[]; verified: boolean;notebookUrl?:string;notionPageId?:string;destinationTitle?:string;videos?:{index:number;title:string;videoUrl:string}[];videoUrl?:string;assets?:Record<string,string> } | null };
type Project = { path: string; runner: string };
type Snapshot = { jobs: Job[]; project: Project; workerInstalled: boolean;videoModels?:VideoModels };
export type CodingReport = {kind?:never; summary: string; changedFiles: string[]; diff: string; beforeTests: { exitCode: number | null; output: string }; tests: { exitCode: number | null; output: string; command: string | null }; verified: boolean; tokens: Record<string, number> };
type DestinationReport={kind:'destination';summary:string;verified:boolean;notebookUrl?:string;notionPageId?:string;destinationTitle?:string;sourceTitle?:string;mindMapTitle?:string};
type Report=CodingReport|StudyReport|DestinationReport;

export async function taskRequest<T>(path = '', body?: unknown, method = 'POST', signal?: AbortSignal): Promise<T> {
  const response = await fetch('/api/v1/tasks' + path, { method: body === undefined ? 'GET' : method, credentials: 'same-origin', signal,
    headers: { 'Content-Type': 'application/json' }, ...(body === undefined ? {} : { body: JSON.stringify(body) }) });
  if (!response.ok) { const value = await response.json().catch(() => ({})); throw new Error(typeof value.detail === 'string' ? value.detail : 'Task service unavailable. Open Memory Palace and try again.'); }
  return response.json();
}

const active = (job: Job) => ['running','queued'].includes(job.status);
export function TaskBoard({ floating = false }: { floating?: boolean }) {
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [project, setProject] = useState<Project>({ path: '', runner: 'node' });
  const [error, setError] = useState('');
  const [pending, setPending] = useState(false);
  const [expanded, setExpanded] = useState(floating);
  const [task, setTask] = useState('Investigate the failing test in the selected project.');
  const [tool, setTool] = useState('coding_task');
  const [codingMode, setCodingMode] = useState('investigate');
  const [modes, setModes] = useState<Record<string,string>>({});
  const [app, setApp] = useState('Notion');
  const [followUp, setFollowUp] = useState<Record<string, string>>({});
  const [report, setReport] = useState<Report | null>(null);
  const [videoUrl,setVideoUrl]=useState('');
  const initialized = useRef(false);
  const alive = useRef(true);
  useEffect(() => {
    alive.current = true;
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    const refresh = async () => {
      try {
        const value = await taskRequest<Snapshot>('', undefined, 'GET', controller.signal);
        if (!alive.current) return;
        setSnapshot(value);
        useTaskState.getState().update(value.jobs.filter(active).length, value.jobs.find(job => job.status === 'running')?.progress || 'Tasks queued');
        if (!initialized.current) { initialized.current = true; setProject(value.project); }
      } catch (e) { if (alive.current) setError(e instanceof Error ? e.message : 'Could not load tasks.'); }
      finally { if (alive.current) timer = setTimeout(() => void refresh(), 1200); }
    };
    void refresh();
    return () => { alive.current = false; controller.abort(); clearTimeout(timer); useTaskState.getState().update(0, ''); };
  }, []);
  const perform = async (operation: () => Promise<unknown>) => {
    if (pending) return;
    setPending(true); setError('');
    try { await operation(); if (alive.current) setSnapshot(await taskRequest<Snapshot>()); }
    catch (e) { if (alive.current) setError(e instanceof Error ? e.message : 'Task failed.'); }
    finally { if (alive.current) setPending(false); }
  };
  const control = (job: Job, action: string) => perform(() => taskRequest('/' + job.id + '/control', { action, instruction: followUp[job.id], ...(job.lane === 'coding' && action === 'update' ? {mode: modes[job.id] || job.mode} : {}) }));
  const jobs = snapshot?.jobs || [];
  const latestSummary=jobs.find(job=>job.status==='succeeded' && job.report?.kind==='youtube' && job.report.assets?.summary);
  return <section className={`aira-task-board ${floating ? 'aira-task-board--floating' : ''}`} aria-label="AIRA task board">
    <header><button className="aira-task-toggle" onClick={() => setExpanded(!expanded)} aria-expanded={expanded}>Tasks <span>{latestSummary ? 'Summary ready' : `${jobs.filter(active).length} active`}</span></button>
      {!floating && window.airaDesktop && <button onClick={() => window.airaDesktop?.showTasks()}>Float board</button>}
    </header>
    {expanded && <div className="aira-task-body">
      <p className="aira-task-intro">Desktop actions take turns. Coding and video study run alongside them.</p>
      <CallReminderList />
      {report?.kind==='youtube' && <VideoStudyResult report={report} close={()=>setReport(null)} pending={pending} submit={(selectedTool,args)=>void perform(()=>taskRequest('',{tool:selectedTool,args,requestId:crypto.randomUUID()}))} openSource={url=>void perform(()=>taskRequest('',{tool:'open_youtube_video',args:{video_url:url},requestId:crypto.randomUUID()}))} />}
      {report?.kind==='destination' && <aside className="aira-job-report"><button onClick={()=>setReport(null)}>Close result</button><h3>{report.verified?'Destination verified':'Review needed'}</h3><p>{report.summary}</p>{report.destinationTitle && <p>Notion page: {report.destinationTitle}</p>}{report.notebookUrl && <a href={report.notebookUrl} target="_blank" rel="noreferrer">Open NotebookLM notebook</a>}</aside>}
      {latestSummary && <div className="aira-job-report" role="status"><strong>Your latest video summary is ready</strong>
        <p>{latestSummary.report?.summary}</p>
        <button disabled={pending} onClick={()=>void perform(async()=>setReport(await taskRequest<Report>('/'+latestSummary.id+'/report')))}>Read latest summary</button>
        <a className="aira-study-download" href={latestSummary.report!.assets!.summary} download>Download summary</a>
      </div>}
      <div className="aira-task-lanes">{(['desktop','coding','study'] as const).map(lane => <div key={lane}><span>{lane === 'desktop' ? 'Desktop' : lane==='study' ? 'Video study' : 'Code & tests'}</span><strong>{jobs.find(j => j.lane === lane && j.status === 'running')?.progress || 'Ready'}</strong></div>)}</div>
      <YouTubeControls pending={pending} models={snapshot?.videoModels} url={videoUrl} onUrl={setVideoUrl}
        submit={(selectedTool,args)=>void perform(()=>taskRequest('',{tool:selectedTool,args,requestId:crypto.randomUUID()}))}
        saveModels={value=>void perform(()=>taskRequest('/video-models',value,'PUT'))} />
      <details><summary>Coding project</summary>
        <label>Folder on E:<input aria-label="Coding project folder" value={project.path} onChange={e => setProject({ ...project, path: e.target.value })} /></label>
        <label>Verification<select value={project.runner} onChange={e => setProject({ ...project, runner: e.target.value })}><option value="node">Node · node --test</option><option value="unittest">Python · unittest discover</option><option value="none">Diagnosis only · no tests</option></select></label>
        <p>Use a trusted project. Tests execute its code. Project context is sent to Gemini; files and history stay local.</p>
        <button disabled={pending} onClick={() => void perform(() => taskRequest('/project', project, 'PUT'))}>Save project</button>
        <button disabled={pending} onClick={() => void perform(() => taskRequest('', { tool: 'show_coding_project', args: {}, requestId: crypto.randomUUID() }))}>Show in VS Code</button>
        {window.airaDesktop ? <button disabled={pending} onClick={() => void perform(() => window.airaDesktop!.showInvoiceDemo())}>Open invoice demo</button> : <a className="aira-study-download" href="/invoice-demo" target="_blank" rel="noreferrer">Open invoice demo</a>}
        {snapshot && !snapshot.workerInstalled && <p role="alert">Run scripts/Setup-Coding.ps1 to install OpenCode.</p>}
      </details>
      <details><summary>Start a task</summary>
        <label>Worker<select value={tool} onChange={e => setTool(e.target.value)}><option value="coding_task">Coding</option><option value="desktop_task">Desktop</option></select></label>
        {tool === 'desktop_task' && <label>Application<input value={app} onChange={e => setApp(e.target.value)} /></label>}
        {tool === 'coding_task' && <label>Code changes<select value={codingMode} onChange={e => setCodingMode(e.target.value)}><option value="investigate">Investigate · no edits</option><option value="fix">Fix · allow source edits</option></select></label>}
        <label>Instructions<textarea aria-label="New task instructions" value={task} onChange={e => setTask(e.target.value)} maxLength={2000} /></label>
        <button disabled={pending || !task.trim()} onClick={() => void perform(() => taskRequest('', { tool, args: tool === 'coding_task' ? { task, mode: codingMode } : { task, app_name: app }, requestId: crypto.randomUUID() }))}>Start task</button>
      </details>
      <div className="aira-job-list">{jobs.length === 0 && <p>No tasks yet. Ask AIRA to open an app, navigate to a folder or investigate your selected project.</p>}
        {jobs.map(job => <article key={job.id} className={`aira-job aira-job--${job.status}`}>
          <div className="aira-job-heading"><span>{job.lane}</span><span>{job.status.replaceAll('_',' ')}</span></div>
          <h3>{job.title}</h3><p role="status">{job.progress}</p><small>#{job.id}{job.revisions.length > 0 ? ` · ${job.revisions.length} update(s) waiting for a checkpoint` : ''}</small>
          {job.lane==='coding' && active(job) && <CodingLog jobId={job.id} status={job.status}/>}
          {job.timings?.totalMs != null && <p>Desktop execution: {(job.timings.totalMs/1000).toFixed(1)} s{job.timings.firstInputMs != null ? ` · first input ${(job.timings.firstInputMs/1000).toFixed(1)} s` : ''}. Voice and task scheduling time are separate.</p>}
          <div className="aira-job-buttons">
            {active(job) && <button disabled={pending} onClick={() => void control(job, 'pause')}>Pause</button>}
            {['paused','needs_attention'].includes(job.status) && <button disabled={pending} onClick={() => void control(job, 'resume')}>Resume</button>}
            {job.status !== 'cancelled' && <button disabled={pending} onClick={() => void control(job, 'cancel')}>Cancel</button>}
            {job.report && job.report.kind!=='browser' && <button disabled={pending} onClick={() => void perform(async () => setReport(await taskRequest<Report>('/' + job.id + '/report')))}>{job.report.kind==='youtube'?'Read video result':job.report.kind==='destination'?'Read destination result':'Tests & diff'}</button>}
          </div>
          {job.report?.videos?.map(video=><div className="aira-video-result" key={video.videoUrl}><p>{video.index}. {video.title}</p>
            <button disabled={pending} onClick={()=>{setVideoUrl(video.videoUrl);void perform(()=>taskRequest('',{tool:'open_youtube_video',args:{video_url:video.videoUrl},requestId:crypto.randomUUID()}));}}>Open & select</button>
          </div>)}
          {job.report?.videoUrl && <button onClick={()=>setVideoUrl(job.report!.videoUrl!)}>Select this video for study</button>}
          {job.report?.notebookUrl && <a href={job.report.notebookUrl} target="_blank" rel="noreferrer">NotebookLM mind map</a>}
          {job.telegramNotification && <p>Telegram: {{sending:'sending notification',sent:'message sent',unconfirmed:'delivery unconfirmed; inspect Telegram',rejected:'message rejected; check bot/chat settings',configuration_required:'run Configure-Telegram.cmd'}[job.telegramNotification.status]}</p>}
          {job.report?.destinationTitle && <p>Notion destination: {job.report.destinationTitle}</p>}
          {job.report?.assets?.infographic && <img className="aira-infographic-preview" src={job.report.assets.infographic} alt="Generated infographic based on video captions" />}
          {job.status !== 'cancelled' && ['desktop_task','create_notion_note','coding_task'].includes(job.tool) && <details><summary>Change this task</summary><textarea aria-label={`Follow-up for ${job.id}`} value={followUp[job.id] || ''} onChange={e => setFollowUp({ ...followUp, [job.id]: e.target.value })} maxLength={2000} placeholder="For example: change the existing note title to Demo Plan" />
            {job.lane === 'coding' && <label>Code changes<select value={modes[job.id] || job.mode} onChange={e => setModes({ ...modes, [job.id]: e.target.value })}><option value="investigate">Investigate · no edits</option><option value="fix">Fix · allow source edits</option></select></label>}
            <button disabled={pending || !followUp[job.id]?.trim()} onClick={() => void control(job, 'update')}>Queue follow-up</button>
          </details>}
        </article>)}
      </div>
      {report && report.kind!=='youtube' && report.kind!=='destination' && <aside className="aira-job-report" aria-label="Coding verification report"><button onClick={() => setReport(null)}>Close report</button><h3>{report.verified ? 'Selected tests passed' : 'Review needed'}</h3><p>{report.summary}</p><p>Changed files: {report.changedFiles.join(', ') || 'None'}</p><p>{report.tests.command || 'No tests'} · exit {report.tests.exitCode ?? 'not run'}</p><pre>{report.tests.output}</pre><details><summary>Before tests</summary><pre>{report.beforeTests.output}</pre></details><details open><summary>Local diff</summary><pre>{report.diff || 'No captured text changes.'}</pre></details></aside>}
      <button className="aira-stop-jobs" disabled={pending || !jobs.some(active)} onClick={() => void perform(() => taskRequest('/stop-all', {}))}>Stop all tasks</button>
      <p className="aira-task-footnote">Pause/cancel stops future work. Existing changes remain. Ctrl+Alt+Escape stops AIRA and both workers.</p>
    </div>}
    {error && <p className="aira-task-error" role="alert">{error}</p>}
  </section>;
}
