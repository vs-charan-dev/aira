import { useEffect, useRef, useState } from 'react';
import { taskRequest, type CodingReport, type Job } from '../components/companion/TaskBoard';
import { CodingLog } from '../components/companion/CodingLog';
import { openLocalSession } from '../services/localSession';
import './invoiceDemo.css';

type Demo = {ready:boolean;path:string;generation:string|null;version:string|null;nodeInstalled:boolean;repairMode:'deterministic'|'agent'};
type Evaluation = {version:string;total:number;expected:number;matches:boolean;command:string};
type Snapshot = {jobs:Job[];project:{path:string;runner:string};workerInstalled:boolean};
type DemoReport = CodingReport & {demoVersion?:string;executionMethod?:string};
const normalize=(path:string)=>path.replaceAll('\\','/').toLowerCase();
const money=(value:number)=>new Intl.NumberFormat('en-IN',{style:'currency',currency:'INR',maximumFractionDigits:2}).format(value);

export function InvoiceWorkbenchPage() {
  const [demo,setDemo]=useState<Demo|null>(null);
  const [snapshot,setSnapshot]=useState<Snapshot|null>(null);
  const [input,setInput]=useState({price:200,discount:10});
  const [applied,setApplied]=useState(input);
  const [evaluation,setEvaluation]=useState<Evaluation|null>(null);
  const [previewError,setPreviewError]=useState('');
  const [error,setError]=useState('');
  const [pollError,setPollError]=useState('');
  const [pending,setPending]=useState(false);
  const [report,setReport]=useState<DemoReport|null>(null);
  const [reload,setReload]=useState(0);
  const busyRef=useRef(false);
  const job=snapshot?.jobs.find(row=>row.lane==='coding' && row.demoGeneration===demo?.generation && normalize(row.project?.path||'')===normalize(demo?.path||''));
  const active=snapshot?.jobs.some(row=>row.lane==='coding' && ['queued','running'].includes(row.status))||false;
  const selected=!!(demo?.ready && snapshot && normalize(snapshot.project.path)===normalize(demo.path) && snapshot.project.runner==='node');
  const currentEvaluation=evaluation?.version===demo?.version?evaluation:null;
  const verified=!!(report?.verified && report.demoVersion===demo?.version && job?.status==='succeeded');

  useEffect(()=>{
    document.title='AIRA · Invoice Demo';
    let disposed=false;
    let timer:ReturnType<typeof setTimeout>;
    const controller=new AbortController();
    const refresh=async()=>{
      try {
        const [value,tasks]=await Promise.all([
          taskRequest<Demo>('/invoice-demo',undefined,'GET',controller.signal),
          taskRequest<Snapshot>('',undefined,'GET',controller.signal)]);
        if(!disposed) {setDemo(value);setSnapshot(tasks);setPollError('');}
      } catch(e) {if(!disposed) setPollError(e instanceof Error?e.message:'Could not load demo.');}
      finally {if(!disposed) timer=setTimeout(()=>void refresh(),1200);}
    };
    void refresh();
    return ()=>{disposed=true;clearTimeout(timer);controller.abort();};
  },[reload]);

  useEffect(()=>{
    setEvaluation(null);setPreviewError('');
    if(!demo?.ready || !demo.version) return;
    let disposed=false;
    const controller=new AbortController();
    void taskRequest<Evaluation>('/invoice-demo/evaluate',{...applied,version:demo.version},'POST',controller.signal)
      .then(value=>{if(!disposed) setEvaluation(value);})
      .catch(e=>{if(!disposed) setPreviewError(e instanceof Error?e.message:'Preview failed.');});
    return ()=>{disposed=true;controller.abort();};
  },[demo?.ready,demo?.version,applied]);

  useEffect(()=>{
    setReport(null);
    if(!job?.report) return;
    let disposed=false;
    const controller=new AbortController();
    void taskRequest<DemoReport>('/'+job.id+'/report',undefined,'GET',controller.signal)
      .then(value=>{if(!disposed) setReport(value);})
      .catch(e=>{if(!disposed) setError(e instanceof Error?e.message:'Report unavailable.');});
    return ()=>{disposed=true;controller.abort();};
  },[job?.id,job?.status,job?.report?.verified]);

  const perform=async(operation:()=>Promise<unknown>)=>{
    if(busyRef.current) return;
    busyRef.current=true;setPending(true);setError('');
    try {await operation();setReload(value=>value+1);}
    catch(e) {setError(e instanceof Error?e.message:'Operation failed.');}
    finally {busyRef.current=false;setPending(false);}
  };
  const prepare=(reset:boolean)=>perform(async()=>{
    const value=await taskRequest<Demo>('/invoice-demo/prepare',{reset});
    setDemo(value);setEvaluation(null);setReport(null);
  });

  return <main className="invoice-demo">
    <header className="invoice-demo-header"><a href="/">AIRA <span>/ Code &amp; tests</span></a><span className="invoice-local">LOCAL DEMO · E:</span></header>
    <section className="invoice-demo-intro"><div><p className="invoice-eyebrow">From voice to a verified fix</p><h1>Make the numbers right.</h1><p>A real invoice module. A visible bug. An independent test suite.</p></div><div className={`invoice-status ${verified?'good':''}`} role="status">{verified?'✓ Selected tests passed':active?'● Coding worker active':selected?'● Ready for your command':'Select the demo project'}</div></section>
    {(error||pollError) && <div className="invoice-error" role="alert">{error||pollError}{pollError.includes('session') && <button disabled={pending} onClick={()=>void perform(openLocalSession)}>Open local session</button>}</div>}
    <div className="invoice-demo-toolbar">
      <button disabled={pending || active} onClick={()=>void prepare(false)}>{selected?'Demo project selected':'Prepare & select demo project'}</button>
      <button className="invoice-primary" disabled={pending || active || !selected || !demo?.nodeInstalled || (demo?.repairMode==='agent' && !snapshot?.workerInstalled)} onClick={()=>void perform(()=>taskRequest('/invoice-demo/fix',{requestId:crypto.randomUUID(),generation:demo?.generation}))}>Ask AIRA to fix the bug</button>
      <button disabled={pending || !selected} onClick={()=>void perform(()=>taskRequest('',{tool:'show_coding_project',args:{},requestId:crypto.randomUUID()}))}>Show in VS Code</button>
      <button className="invoice-reset" disabled={pending || active || !demo?.ready} onClick={()=>void prepare(true)}>Reset demo to broken version</button>
    </div>
    <p className="invoice-muted">Invoice repair mode: {demo?.repairMode==='deterministic'?'configured known-bug script · no coding inference':'OpenCode agent'}. The independent tests run in both modes.</p>
    {snapshot && !snapshot.workerInstalled && demo?.repairMode==='agent' && <p className="invoice-error">Install the coding worker with scripts/Setup-Coding.ps1 before requesting a fix.</p>}
    {demo?.ready && !demo.nodeInstalled && <p className="invoice-error">Node.js is required for the preview and tests.</p>}
    <div className="invoice-demo-grid">
      <section className="invoice-preview"><div className="invoice-card-heading"><span>Invoice / INV-001</span><span>LIVE SOURCE</span></div>
        <h2>Design consultation</h2><p className="invoice-muted">A simple invoice with a percentage discount.</p>
        <form onSubmit={event=>{event.preventDefault();setApplied({...input});}}>
          <label>Subtotal (₹)<input type="number" min="0" max="1000000" step="0.01" required value={input.price} onChange={event=>setInput({...input,price:Number(event.target.value)})}/></label>
          <label>Discount (%)<input type="number" min="0" max="100" step="0.01" required value={input.discount} onChange={event=>setInput({...input,discount:Number(event.target.value)})}/></label>
          <button disabled={!demo?.ready || pending}>Calculate invoice</button>
        </form>
        <div className="invoice-total"><span>Total from invoice.js</span><strong>{currentEvaluation?money(currentEvaluation.total):'—'}</strong></div>
        <div className={`invoice-comparison ${currentEvaluation?.matches?'good':'bad'}`} role="status">
          {currentEvaluation?<><strong>{currentEvaluation.matches?'✓ This calculation matches':'Calculation mismatch'}</strong><p>{money(applied.price)} with {applied.discount}% off should be <b>{money(currentEvaluation.expected)}</b>.</p></>:<p>{!demo?.ready?'Prepare the demo to load its module.':previewError||'Refreshing from the current source…'}</p>}
        </div>
        <p className="invoice-muted">The preview refreshes when invoice.js changes. A matching example and a passing test suite are shown separately.</p>
        <code className="invoice-path">{demo?.path||'E: / AIRA demo project'}</code>
      </section>
      <section className="invoice-worker"><div className="invoice-card-heading"><span>Worker / observed execution</span><span>{job?`#${job.id}`:'READY'}</span></div>
        <h2>{job?.progress||'Your command starts the repair.'}</h2>
        <p className="invoice-voice">“Hey AIRA, fix the discount calculation in the selected project. Keep the tests unchanged.”</p>
        {job?<CodingLog jobId={job.id} status={job.status}/>:<div className="invoice-empty-log"><code>$ node --test<br/>$ opencode run …<br/>$ node --test</code><p>Observed command and test output will appear here after you start a task.</p></div>}
        {job && ['queued','running'].includes(job.status) && <button disabled={pending} onClick={()=>void perform(()=>taskRequest('/'+job.id+'/control',{action:'cancel'}))}>Cancel coding task</button>}
        <p className="invoice-muted">Windows and browser tasks can continue while this worker reads and edits the project. Pausing or cancelling preserves any edits already made.</p>
      </section>
    </div>
    {report && <section className="invoice-verification"><div className="invoice-card-heading"><span>Independent verification</span><span>{verified?'PASSED':'REVIEW'}</span></div><h2>{verified?'The selected tests pass on this source.':'Inspect the actual results.'}</h2>
      <p>{report.summary}</p>{report.executionMethod && <p>Execution: {report.executionMethod.replaceAll('_',' ')}</p>}<p>Changed files: <code>{report.changedFiles.join(', ')||'None'}</code></p>
      <div className="invoice-test-grid"><div><h3>Before · exit {report.beforeTests.exitCode??'not run'}</h3><pre>{report.beforeTests.output}</pre></div><div><h3>After · exit {report.tests.exitCode??'not run'}</h3><pre>{report.tests.output}</pre></div></div>
      <details open><summary>Source diff</summary><pre>{report.diff||'No captured source changes.'}</pre></details>
    </section>}
    <footer>One voice request → source change → independent tests → refreshed invoice.</footer>
  </main>;
}

// The application shown to the audience contains no expected answer, repair
// buttons, source code, tests, or instructions to the agent.
export function InvoiceDemoPage() {
  const [demo,setDemo]=useState<Demo|null>(null);
  const [input,setInput]=useState({price:200,discount:10});
  const [applied,setApplied]=useState(input);
  const [evaluation,setEvaluation]=useState<Evaluation|null>(null);
  const [error,setError]=useState('');
  const [calculationError,setCalculationError]=useState('');
  const [sessionRequired,setSessionRequired]=useState(false);
  const [retry,setRetry]=useState(0);
  useEffect(()=>{
    document.title='Invoice Studio';
    let disposed=false;
    let timer:ReturnType<typeof setTimeout>;
    const controller=new AbortController();
    const refresh=async()=>{
      try {
        let info=await taskRequest<Demo>('/invoice-demo',undefined,'GET',controller.signal);
        if(!info.ready) info=await taskRequest<Demo>('/invoice-demo/prepare',{reset:false},'POST',controller.signal);
        if(!disposed) {setDemo(info);setSessionRequired(false);setError('');}
      } catch(e) {
        if(!disposed) {
          const message=e instanceof Error?e.message:'';
          if(message.includes('session')) {
            try {await openLocalSession();if(!disposed) {setSessionRequired(false);setError('');setRetry(value=>value+1);}}
            catch {if(!disposed) {setSessionRequired(true);setError('This invoice is temporarily unavailable.');}}
          } else {setSessionRequired(false);setError('This invoice is temporarily unavailable.');}
        }
      } finally {if(!disposed) timer=setTimeout(()=>void refresh(),1200);}
    };
    void refresh();
    return ()=>{disposed=true;clearTimeout(timer);controller.abort();};
  },[retry]);
  useEffect(()=>{
    if(!demo?.version) return;
    let disposed=false;
    const controller=new AbortController();
    void taskRequest<Evaluation>('/invoice-demo/evaluate',{...applied,version:demo.version},'POST',controller.signal)
      .then(value=>{if(!disposed) {setEvaluation(value);setCalculationError('');}})
      .catch(()=>{if(!disposed) {setEvaluation(null);setCalculationError('Unable to calculate this invoice.');}});
    return ()=>{disposed=true;controller.abort();};
  },[demo?.version,applied]);
  const total=evaluation && evaluation.version===demo?.version?evaluation.total:null;
  return <main className="invoice-app">
    <header><div className="invoice-app-brand"><span>i</span> Invoice Studio</div><nav><b>Invoices</b><span>Clients</span><span>Overview</span></nav><div className="invoice-app-avatar">C</div></header>
    <section className="invoice-app-title"><div><p>INVOICES / INV-001</p><h1>Invoice details</h1></div><span className="invoice-app-draft">Draft</span></section>
    <div className="invoice-app-layout"><section className="invoice-app-document">
      <div className="invoice-app-document-heading"><div><h2>Design consultation</h2><p>Invoice #INV-001</p></div><div className="invoice-app-logo">NS.</div></div>
      <div className="invoice-app-parties"><div><small>BILL TO</small><strong>Northstar Design</strong><p>Product design &amp; consulting</p></div><div><small>PAYMENT TERMS</small><strong>Due on receipt</strong><p>Currency: INR</p></div></div>
      <div className="invoice-app-line"><span>Description</span><span>Amount</span></div><div className="invoice-app-line item"><span>Design consultation <small>1 service · project fee</small></span><b>{money(applied.price)}</b></div>
      <div className="invoice-app-summary"><p><span>Subtotal</span><b>{money(applied.price)}</b></p><p><span>Discount ({applied.discount}%)</span><b>{total===null?'—':'− '+money(applied.price-total)}</b></p><p className="invoice-app-grand"><span>Total due</span><strong aria-live="polite">{total===null?'—':money(total)}</strong></p></div>
      <div className="invoice-app-note"><small>NOTE</small><p>Thank you for working with us.</p></div>
    </section><aside className="invoice-app-settings"><h2>Invoice settings</h2><p>Update the amount and discount for this invoice.</p><form onSubmit={event=>{event.preventDefault();setApplied({...input});}}><label>Service amount (₹)<input type="number" min="0" max="1000000" step="0.01" required value={input.price} onChange={event=>setInput({...input,price:Number(event.target.value)})}/></label><label>Discount (%)<input type="number" min="0" max="100" step="0.01" required value={input.discount} onChange={event=>setInput({...input,discount:Number(event.target.value)})}/></label><button disabled={!demo?.ready}>Update invoice</button></form><div className="invoice-app-private"><span>◈</span><p>Draft invoice<br/><small>Your changes appear on this invoice.</small></p></div></aside></div>
    {(error||calculationError) && <p className="invoice-app-error" role="alert">{error||calculationError}{sessionRequired && <button onClick={()=>void openLocalSession().then(()=>setRetry(value=>value+1)).catch(()=>setError('Could not open the local session.'))}>Open local session</button>}</p>}
  </main>;
}
