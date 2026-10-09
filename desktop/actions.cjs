const { spawn } = require('node:child_process');
const path = require('node:path');
const crypto = require('node:crypto');
const fs = require('node:fs');
const { performance } = require('node:perf_hooks');
const { WarmWorker } = require('./warm-worker.cjs');
const CHROME_NAMES = new Set(['chrome','google chrome','googlechrome','chrome browser','google chrome browser']);

function browserMapsTask(task) {
  const patterns = [
    /^(?:search|find)\s+(?:on\s+)?(?:google\s+)?maps\s+for\s+(.+)$/i,
    /^(?:search\s+for|find)\s+(.+?)\s+on\s+(?:google\s+)?maps[.!]?$/i,
    /^(?:(?:go\s+to|open)\s+(?:google\s+)?chrome\s*[,;]?\s*(?:and\s+)?)?(?:go\s+to|open)\s+(?:google\s+)?maps\s*[,;]?\s*(?:and\s+)?search\s+for\s+(.+)$/i,
  ];
  for (const pattern of patterns) { const match = pattern.exec(task.trim()); if (match) return match[1].trim().replace(/^["']|["']$/g,''); }
  return null;
}

function browserSearchTask(task) {
  const patterns = [
    /^(?:type|enter)\s+(['"])(.+?)\1\s+(?:into|in)\s+the\s+(?:youtube\s+)?search\s+box(?:\s+and\s+press\s+enter)?[.!]?$/i,
    /^search\s+(?:on\s+)?youtube\s+for\s+(['"])(.+?)\1[.!]?$/i,
    /^search\s+for\s+(['"])(.+?)\1\s+on\s+youtube[.!]?$/i,
    /^(?:go\s+to|open)\s+youtube\s+and\s+search\s+for\s+(['"])(.+?)\1[.!]?$/i,
  ];
  for (const pattern of patterns) { const match = pattern.exec(task.trim()); if (match) return match[2]; }
  return /^(?:search\s+(?:on\s+)?youtube\s+for|(?:go\s+to|open)\s+youtube\s+and\s+search\s+for)\s+([^\r\n]+)$/i.exec(task.trim())?.[1]?.trim() ?? null;
}

function browserVideoTask(task) {
  const match=/^(?:click(?:\s+on)?|open|play)\s+(?:the\s+)?(first|second|third|fourth|fifth|[1-5](?:st|nd|rd|th)?)\s+(?:youtube\s+)?(?:video|result)(?:\s+(?:on|in|from)\s+(?:the\s+)?(?:youtube\s+)?(?:search\s+)?results)?[.!]?$/i.exec(task.trim());
  if (!match) return null;
  const ordinal=match[1].toLowerCase();
  return /^[1-5]/.test(ordinal) ? Number(ordinal[0]) : ['first','second','third','fourth','fifth'].indexOf(ordinal)+1;
}

function validateAction(value) {
  if(value?.kind==='show_invoice_demo') {
    let uri; try { uri=new URL(value.url); } catch { throw new Error('Use the local invoice URL.'); }
    if(uri.protocol!=='http:' || !['127.0.0.1','localhost','[::1]'].includes(uri.hostname) || uri.username || uri.password || uri.pathname!=='/invoice-demo' || uri.search || uri.hash) throw new Error('Use the local invoice URL.');
    return {kind:value.kind,url:uri.href};
  }
  if(value?.kind==='run_invoice_tests' && /^[a-f0-9]{32}$/.test(value.runId||'')) return {kind:value.kind,runId:value.runId};
  if(value?.kind==='notebooklm_mindmap') {
    if(typeof value.newNotebook!=='boolean') throw new Error('Choose a new or existing notebook.');
    const action={kind:value.kind,newNotebook:value.newNotebook};
    if(value.videoUrl) action.videoUrl=validateAction({kind:'open_youtube_video',videoUrl:value.videoUrl}).videoUrl;
    else throw new Error('Provide an observed YouTube video link.');
    if(value.notebookUrl) {
      let uri; try { uri=new URL(value.notebookUrl); } catch { throw new Error('Provide a NotebookLM notebook link.'); }
      if(value.newNotebook || uri.protocol!=='https:' || !['notebooklm.google.com','notebook.google.com'].includes(uri.hostname) || uri.username || uri.password || (uri.port && uri.port!=='443') || !/^\/notebook\/[a-zA-Z0-9_-]{1,100}\/?$/.test(uri.pathname)) throw new Error('Choose a valid existing NotebookLM notebook link.');
      action.notebookUrl=uri.origin+uri.pathname;
    }
    return action;
  }
  if(value?.kind==='export_summary_to_notion') {
    if(!['new','existing'].includes(value.destination) || typeof value.title!=='string' || !value.title.trim() || value.title.length>160 || /[\x00-\x1f\x7f]/.test(value.title)) throw new Error('Choose a Notion destination and title.');
    if(typeof value.content!=='string' || !value.content.trim() || value.content.length>20000 || /[\x00-\x08\x0b-\x1f\x7f]/.test(value.content)) throw new Error('Export requires a complete saved summary, up to 20000 characters.');
    if(typeof value.pageName!=='string' || value.pageName.length>160 || /[\x00-\x1f\x7f]/.test(value.pageName) || (value.destination==='new' && value.pageName)) throw new Error('Use an exact existing page title or the selected page.');
    if(!/^[a-f0-9]{10}$/.test(value.studyTaskId||'')) throw new Error('Select a saved study task.');
    return {kind:value.kind,destination:value.destination,title:value.title.trim(),content:value.content,pageName:value.pageName.trim(),studyTaskId:value.studyTaskId,
      videoUrl:validateAction({kind:'open_youtube_video',videoUrl:value.videoUrl}).videoUrl};
  }
  if(value?.kind==='open_app' && typeof value.appName==='string' && CHROME_NAMES.has(value.appName.trim().toLowerCase())) return {kind:'open_browser'};
  if (['open_browser','open_maps','current_youtube_video'].includes(value?.kind)) return {kind:value.kind};
  if (value?.kind==='search_maps' && typeof value.query==='string' && value.query.trim() && value.query.length<=250 && !/[\x00-\x1f\x7f]/.test(value.query)) return {kind:value.kind,query:value.query.trim()};
  if (value?.kind==='search_youtube' && typeof value.query==='string' && value.query.trim() && value.query.length<=250 && !/[\x00-\x1f]/.test(value.query)) return {kind:value.kind,query:value.query.trim()};
  if(value?.kind==='open_youtube_video') {
    if(typeof value.videoUrl==='string' && value.videoUrl.length<=1000) {
      let uri; try { uri=new URL(value.videoUrl); } catch { throw new Error('Provide a YouTube video link.'); }
      const id=uri.hostname==='youtu.be' ? uri.pathname.slice(1) : ['youtube.com','www.youtube.com','m.youtube.com'].includes(uri.hostname) ? (uri.pathname==='/watch' ? uri.searchParams.get('v') : /^\/(shorts|live)\/([\w-]{11})\/?$/.exec(uri.pathname)?.[2]) : null;
      if(uri.protocol!=='https:' || uri.username || uri.password || !/^[\w-]{11}$/.test(id||'') || (uri.port && uri.port!=='443')) throw new Error('Choose a specific HTTPS YouTube video link.');
      return {kind:value.kind,videoUrl:'https://www.youtube.com/watch?v='+id};
    }
    if(Number.isInteger(value.resultNumber) && value.resultNumber>=1 && value.resultNumber<=5) return {kind:value.kind,resultNumber:value.resultNumber};
    throw new Error('Choose an observed video result number or a video link.');
  }
  if (value?.kind === 'type_in_app' && typeof value.appName === 'string' && value.appName.trim().toLowerCase() === 'notion' && typeof value.text === 'string' && value.text.length > 0 && value.text.length <= 2000 && !/[\x00-\x08\x0b-\x1f\x7f]/.test(value.text)) return {kind:'type_in_app',appName:'Notion',text:value.text};
  if (value?.kind === 'calculate_in_app' && typeof value.expression === 'string' && value.expression.length <= 80 && /^\s*\d{1,12}(?:\.\d{1,8})?\s*[+*/×÷−-]\s*\d{1,12}(?:\.\d{1,8})?\s*$/.test(value.expression)) return {kind:'calculate_in_app',expression:value.expression};
  if(value?.kind==='open_folder' && typeof value.path==='string' && ['desktop','documents','downloads'].includes(value.path.toLowerCase())) return {kind:'open_folder',path:value.path.toLowerCase()};
  if (value?.kind === 'show_project' && typeof value.path === 'string' && /^E:[\\/]/i.test(value.path) && value.path.length <= 500 && !/[\x00-\x1f<>"|?*]/.test(value.path) && !value.path.slice(2).includes(':')) {
    if(value.file!==undefined && value.file!=='invoice.js') throw new Error('Choose the invoice source file.');
    return {kind:'show_project',path:value.path,...(value.file?{file:value.file}:{})};
  }
  if (value?.kind === 'create_notion_note') {
    if (typeof value.title !== 'string' || !value.title.trim() || value.title.length > 160 || /[\x00-\x1f\x7f]/.test(value.title)) throw new Error('Provide a note title of 1–160 characters on one line.');
    if (typeof value.content !== 'string' || !value.content.trim() || value.content.length > 2000 || /[\x00-\x08\x0b-\x1f\x7f]/.test(value.content)) throw new Error('Provide plain-text note content of 1–2000 characters.');
    return { kind: 'create_notion_note', title: value.title.trim(), content: value.content.replace(/\r\n/g, '\n') };
  }
  if (['open_app','close_app','desktop_task'].includes(value?.kind) && typeof value.appName === 'string' && /^[\p{L}\p{N}_ .()&+\-]{1,80}$/u.test(value.appName.trim())) {
    const name = value.appName.trim();
    if (/powershell|command prompt|terminal|registry|regedit|task scheduler|disk management|computer management|wsl|security|run command/i.test(name)) throw new Error('This launcher supports ordinary apps. System administration and command shells are not supported.');
    if (value.kind === 'desktop_task') {
      if (typeof value.task !== 'string' || !value.task.trim() || value.task.length > 2000 || /[\x00-\x08\x0b-\x1f\x7f]/.test(value.task)) throw new Error('Provide a desktop task of 1–2000 characters.');
      if (CHROME_NAMES.has(name.toLowerCase())) {
        const maps = browserMapsTask(value.task);
        if (maps !== null) return validateAction({kind:'search_maps',query:maps});
        if (/^(?:go\s+to|open)\s+(?:google\s+)?maps[.!]?$/i.test(value.task.trim())) return {kind:'open_maps'};
        const query = browserSearchTask(value.task);
        if (query !== null) return validateAction({kind:'search_youtube',query});
        const index = browserVideoTask(value.task);
        if (index !== null) return validateAction({kind:'open_youtube_video',resultNumber:index});
        throw new Error('For AIRA Chrome, use the Maps or YouTube controls or ask AIRA to search with the exact topic.');
      }
      return { kind: value.kind, appName: name, task: value.task.trim() };
    }
    return { kind: value.kind, appName: name };
  }
  if (value?.kind === 'open_folder' && typeof value.path === 'string' && value.path.length <= 500 && /^[a-z]:[\\/]/i.test(value.path) && !/[\x00-\x1f<>"|?*]/.test(value.path) && !value.path.slice(2).includes(':')) return { kind: 'open_folder', path: value.path };
  throw new Error('Choose an installed app name or an absolute local folder path.');
}

function browserResultData(value) {
  // Preserve observed results through IPC, with the same bounded URL validation
  // used for opening a video. The backend also checks this data independently.
  if (!value || typeof value !== 'object') return {};
  const data = {};
  if(value.notebookUrl) data.notebookUrl=validateAction({kind:'notebooklm_mindmap',newNotebook:false,notebookUrl:value.notebookUrl,videoUrl:value.videoUrl}).notebookUrl;
  if(typeof value.notionPageId==='string' && /^[a-f0-9]{32}$/.test(value.notionPageId)) data.notionPageId=value.notionPageId;
  for(const field of ['destinationTitle','sourceTitle','mindMapTitle']) if(typeof value[field]==='string') data[field]=value[field].slice(0,250);
  if (value.videoUrl) {
    data.videoUrl = validateAction({kind:'open_youtube_video',videoUrl:value.videoUrl}).videoUrl;
    data.title = typeof value.title === 'string' ? value.title.slice(0,250) : '';
  }
  if (Array.isArray(value.videos)) data.videos = value.videos.slice(0,5).map((video,index) => ({
    index:index+1,
    title:typeof video?.title === 'string' ? video.title.slice(0,250) : '',
    videoUrl:validateAction({kind:'open_youtube_video',videoUrl:video?.videoUrl}).videoUrl,
  }));
  return data;
}

class DesktopActions {
  constructor({ root, onState = () => {}, spawnProcess = spawn }) {
    this.root = root; this.onState = onState; this.spawnProcess = spawnProcess;
    this.active = null; this.queue = []; this.draining = false; this.closed = false;
    this.native = new WarmWorker(root,false,spawnProcess);
    this.gui = new WarmWorker(root,true,spawnProcess);
    this.timingWrites = Promise.resolve();
  }
  warm() { if(!this.closed) { void this.native.prepare().catch(() => {}); void this.gui.prepare().catch(() => {}); } }
  async run(value, requestId = crypto.randomUUID()) {
    let action;
    if(this.closed) return {status:'failed',message:'Desktop controller is shut down.'};
    try { action = validateAction(value); } catch (error) { return { status: 'failed', message: error.message }; }
    if (this.queue.length >= 8) return { status: 'failed', message: 'Desktop queue is full.' };
    return new Promise(resolve => { this.queue.push({ action, requestId, resolve, receivedAt: performance.now() }); void this._drain(); });
  }
  async _drain() {
    if (this.draining || this.active || !this.queue.length) return;
    this.draining = true;
    const entry = this.queue.shift();
    try { entry.resolve(await this._start(entry.action, entry.requestId, false, entry.receivedAt)); }
    finally { this.draining = false; void this._drain(); }
  }
  async listApps() {
    if (this.active || this.draining || this.queue.length) throw new Error('Wait for the desktop action to finish.');
    const result = await this._start({ kind: 'list_apps' }, crypto.randomUUID(), true);
    if (result.status !== 'succeeded') throw new Error(result.message);
    return result.apps || [];
  }
  async _start(action, requestId, inventory = false, receivedAt = performance.now()) {
    const began=performance.now();
    const worker=action.kind==='desktop_task' ? this.gui : this.native;
    const task={requestId,worker,cancelled:false,timedOut:false};
    this.active=task;
    const timings={queueMs:Math.round(began-receivedAt),workerReadyMs:null,firstInputMs:null,executionMs:null,totalMs:null};
    const publish=label => { if(!inventory) this.onState({running:true,requestId,status:'running',label,timings:{...timings}}); };
    publish(action.kind==='desktop_task' ? 'Preparing Windows-Use' : 'Preparing direct Windows action');
    let result;
    const timeout=setTimeout(() => { task.timedOut=true; void worker.stop(); },['export_summary_to_notion','notebooklm_mindmap'].includes(action.kind) ? 300000 : action.kind==='desktop_task' ? 180000 : ['create_notion_note','open_browser','open_maps','search_maps','search_youtube','open_youtube_video','show_invoice_demo','run_invoice_tests'].includes(action.kind) ? 90000 : 45000);
    try {
      const message=await worker.run(action,requestId,value => {
        if(task.cancelled || task.timedOut) return;
        if(value.type==='action_started' && timings.firstInputMs===null) timings.firstInputMs=Math.round(performance.now()-receivedAt);
        if(value.type==='progress') publish(String(value.label).slice(0,160));
      },() => { timings.workerReadyMs=Math.round(performance.now()-began); });
      result=['succeeded','failed'].includes(message.status) ? {status:message.status,message:String(message.message).slice(0,400),...(Array.isArray(message.apps) ? {apps:message.apps.filter(name => typeof name==='string').slice(0,250)} : {})} : {status:'failed',message:'Desktop worker returned an invalid result. Completion was not verified.'};
      if ((message.status === 'succeeded' || message.data?.notebookUrl) && ['export_summary_to_notion','notebooklm_mindmap','open_browser','open_maps','search_maps','search_youtube','open_youtube_video','current_youtube_video'].includes(action.kind)) {
        try { result.data = browserResultData(message.data); }
        catch { result = {status:'failed',message:'The browser returned invalid video links. Inspect the page before retrying.'}; }
      }
      if(Number.isFinite(message.timings?.executionMs)) timings.executionMs=Math.round(message.timings.executionMs);
    } catch {
      result={status:'failed',message:'Desktop worker unavailable. Stop and restart AIRA; inspect partial changes before retrying.'};
    } finally {
      clearTimeout(timeout);
      if(task.cancelled || task.timedOut) await worker.stop();
      if(this.active===task) this.active=null;
    }
    if(task.cancelled) result={status:'cancelled',message:'Desktop action stopped. Partial changes may remain; inspect the app before retrying.'};
    else if(task.timedOut) result={status:'failed',message:'Windows action timed out. Completion was not verified; inspect partial changes.'};
    timings.totalMs=Math.round(performance.now()-receivedAt);
    result.timings=timings;
    if(!inventory) {
      this.writeTiming(action.kind,requestId,result.status,timings);
      // The server records real execution start/end. Only missing/cancelled results
      // need a repair record; this must never delay the returned desktop result.
      if((task.cancelled || task.timedOut || timings.executionMs===null) && this.spawnProcess===spawn) void this.recordResult(action,requestId,result);
      this.onState({running:false,requestId,status:result.status,label:result.message,timings});
    }
    return result;
  }
  writeTiming(kind,requestId,status,timings) {
    this.timingWrites=this.timingWrites.then(async () => {
      const directory=path.join(this.root,'.cache','desktop');
      await fs.promises.mkdir(directory,{recursive:true});
      const file=path.join(directory,'action-timings.jsonl');
      const stat=await fs.promises.stat(file).catch(() => null);
      if(stat?.size>5*1024*1024) await fs.promises.copyFile(file,path.join(directory,'action-timings.previous.jsonl')).then(() => fs.promises.writeFile(file,''));
      await fs.promises.appendFile(file,JSON.stringify({at:new Date().toISOString(),requestId,kind,status,...timings})+'\n');
    }).catch(() => {});
  }
  recordResult(action, requestId, result) {
    return new Promise(resolve => {
      const child = spawn(path.join(this.root,'.venv','Scripts','python.exe'), ['-u',path.join(this.root,'desktop','desktop_history.py')], { cwd:this.root, windowsHide:true, stdio:['pipe','ignore','ignore'], env:process.env });
      const timeout = setTimeout(() => { child.kill(); resolve(false); },3000);
      const done = ok => { clearTimeout(timeout); resolve(ok); };
      child.on('error',() => done(false)); child.on('close',code => done(code===0)); child.stdin.on('error',() => {});
      child.stdin.end(JSON.stringify({ requestId, action, ...result })+'\n');
    });
  }
  stop(requestId) {
    const removed = this.queue.filter(entry => !requestId || entry.requestId === requestId);
    this.queue = this.queue.filter(entry => requestId && entry.requestId !== requestId);
    for (const entry of removed) entry.resolve({ status: 'cancelled', message: 'Queued desktop action cancelled before it started.' });
    const task = this.active;
    if (!task || (requestId && requestId !== task.requestId)) return removed.length > 0;
    task.cancelled = true;
    // No held mouse buttons/keys: each SendInput call injects a complete down/up pair.
    if(task.worker) void task.worker.stop();
    else task.child?.kill();
    return true;
  }
  shutdown() {
    this.closed=true; this.stop();
    return Promise.all([this.native.shutdown(),this.gui.shutdown()]);
  }
}
module.exports = { DesktopActions, validateAction };
