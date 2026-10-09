const test = require('node:test');
const assert = require('node:assert/strict');
const { EventEmitter } = require('node:events');
const { DesktopActions, validateAction } = require('../actions.cjs');
test('Maps requests keep literal places and recover generic Chrome search routing', () => {
  assert.deepEqual(validateAction({kind:'open_maps'}),{kind:'open_maps'});
  assert.deepEqual(validateAction({kind:'search_maps',query:' Café & Park, Hyderabad '}),{kind:'search_maps',query:'Café & Park, Hyderabad'});
  for (const task of ['Search Google Maps for Hyderabad','Search for Hyderabad on Maps','Go to Google Chrome, go to Maps and search for Hyderabad']) {
    assert.deepEqual(validateAction({kind:'desktop_task',appName:'Chrome',task}),{kind:'search_maps',query:'Hyderabad'});
  }
  assert.deepEqual(validateAction({kind:'desktop_task',appName:'Chrome',task:'Go to Maps'}),{kind:'open_maps'});
  for (const query of ['', ' ', 'x'.repeat(251), 'Hyderabad\n', null]) assert.throws(()=>validateAction({kind:'search_maps',query}));
});
function harness() {
  const children = [], states = [];
  const controller = new DesktopActions({ root: 'E:\\Havetobuild\\AIRA', onState: state => states.push(state), spawnProcess: (exe,args,options) => {
    const child = new EventEmitter(); child.stdout = new EventEmitter(); child.stdout.setEncoding = () => {};
    child.stderr = new EventEmitter(); child.stdin = new EventEmitter(); child.stdin.write = (text,callback) => { child.input = JSON.parse(text); callback?.(); };
    child.kill = () => { child.killed = true; setImmediate(() => child.emit('close',null)); };
    Object.assign(child,{exe,args,options}); children.push(child); setImmediate(() => child.stdout.emit('data',JSON.stringify({type:'ready'})+'\n')); return child;
  } });
  controller.writeTiming = () => {}; // Fixtures never write app timing history.
  const line = (child,value) => child.stdout.emit('data',JSON.stringify({requestId:child.input?.requestId,...value,...(value.type==='result' ? {timings:{executionMs:1}} : {})})+'\n');
  const ready = () => new Promise(resolve => setImmediate(resolve));
  return { controller,children,states,line,ready };
}
test('rejects shell names, arguments, network/device paths and unsupported actions before spawning', async () => {
  const h=harness();
  for (const value of [{kind:'shell',command:'calc'}, {kind:'open_app',appName:'powershell'}, {kind:'open_app',appName:'Notion; calc'}, {kind:'open_folder',path:'\\\\server\\folder'}, {kind:'open_folder',path:'E:\\file:stream'}, {kind:'open_folder',path:'E:\\x\nnotepad'}]) {
    assert.equal((await h.controller.run(value)).status,'failed');
  }
  assert.equal(h.children.length,0);
  assert.equal(validateAction({kind:'open_app',appName:' Notion '}).appName,'Notion');
});

test('source presentation preserves only the fixed invoice file without shell arguments', () => {
  assert.deepEqual(validateAction({kind:'show_project',path:'E:\\Demo',file:'invoice.js'}),{kind:'show_project',path:'E:\\Demo',file:'invoice.js'});
  for(const file of ['../secrets.txt','invoice.js; calc','E:\\other.js','invoice.js\n']) assert.throws(()=>validateAction({kind:'show_project',path:'E:\\Demo',file}));
});

test('invoice browser and terminal actions have fixed bounded targets', () => {
  assert.deepEqual(validateAction({kind:'show_invoice_demo',url:'http://127.0.0.1:8000/invoice-demo'}),{kind:'show_invoice_demo',url:'http://127.0.0.1:8000/invoice-demo'});
  for(const url of ['https://example.com/invoice-demo','http://localhost:8000/palace','http://user@localhost:8000/invoice-demo','http://localhost:8000/invoice-demo?command=calc']) assert.throws(()=>validateAction({kind:'show_invoice_demo',url}));
  assert.deepEqual(validateAction({kind:'run_invoice_tests',runId:'a'.repeat(32),command:'ignored'}),{kind:'run_invoice_tests',runId:'a'.repeat(32)});
  for(const runId of ['../bad','a'.repeat(33),'calc;']) assert.throws(()=>validateAction({kind:'run_invoice_tests',runId}));
});
test('uses JSON stdin, publishes progress and returns only verified completion', async () => {
  const h=harness(), pending=h.controller.run({kind:'open_app',appName:'Notion'},'one'), child=h.children[0];
  await h.ready();
  assert.equal(child.input.appName,'Notion'); assert.ok(child.exe.endsWith('python.exe')); assert.ok(child.args.every(arg => !arg.includes('Notion'))); assert.equal(child.options.windowsHide,true);
  assert.ok(child.options.env.TEMP.startsWith('E:'));
  h.line(child,{type:'progress',label:'Opening Notion'}); h.line(child,{type:'result',status:'succeeded',message:'Notion verified.'});
  assert.equal((await pending).status,'succeeded'); assert.equal(h.states.at(-1).running,false);
});
test('serializes actions, ignores unrelated cancellation, and cancellation wins over late success', async () => {
  const h=harness(), first=h.controller.run({kind:'open_app',appName:'Notion'},'one');
  const queued=h.controller.run({kind:'open_app',appName:'Calculator'},'two');
  assert.equal(h.children.length,1);
  assert.equal(h.controller.stop('two'),true);
  assert.equal((await queued).status,'cancelled');
  assert.equal(h.controller.stop('other'),false); assert.equal(h.controller.stop('one'),true);
  h.line(h.children[0],{type:'result',status:'succeeded',message:'late'});
  assert.equal((await first).status,'cancelled'); assert.equal(h.controller.active,null);
});

test('completed requests reuse the warm worker and stop-all drops the remaining queue', async () => {
  const h=harness(), first=h.controller.run({kind:'open_app',appName:'Notion'},'one');
  const second=h.controller.run({kind:'show_project',path:'E:/demo'},'two');
  assert.equal(h.children.length,1);
  await h.ready();
  h.line(h.children[0],{type:'result',status:'succeeded',message:'first'});
  assert.equal(h.children.length,1);
  await first;await h.ready();
  assert.equal(h.children.length,1);assert.equal(h.children[0].input.requestId,'two');
  const third=h.controller.run({kind:'open_app',appName:'Calculator'},'three');
  h.controller.stop();
  assert.equal((await third).status,'cancelled');assert.equal((await second).status,'cancelled');
});
test('process failure cannot become success and inventory is isolated from action progress', async () => {
  const h=harness(), first=h.controller.run({kind:'open_app',appName:'Notion'}); h.children[0].emit('error',new Error('raw secret')); assert.equal((await first).status,'failed');
  const inventory=h.controller.listApps();await h.ready(); h.line(h.children[1],{type:'result',status:'succeeded',message:'loaded',apps:['Notion',null,'Calculator']});
  assert.deepEqual(await inventory,['Notion','Calculator']); assert.ok(!JSON.stringify(h.states).includes('raw secret'));
});

test('note payload stays literal JSON and rejects empty, oversized and control-character content', async () => {
  const h = harness();
  for (const action of [{title:'',content:'Body'}, {title:'T\nX',content:'Body'}, {title:'T',content:'x'.repeat(2001)}, {title:'T',content:'\u0000bad'}]) assert.equal((await h.controller.run({kind:'create_notion_note',...action})).status,'failed');
  assert.equal(h.children.length,0);
  const pending=h.controller.run({kind:'create_notion_note',title:' Demo ',content:'Text $(calc)\nSecond paragraph'});
  await h.ready();
  const child=h.children[0];assert.equal(child.input.title,'Demo');assert.equal(child.input.content,'Text $(calc)\nSecond paragraph');
  assert.ok(!child.args.some(arg=>arg.includes('calc')));
  h.controller.stop(); assert.equal((await pending).status,'cancelled');
});
test('Windows-Use uses isolated Python, bounded literal task input, and scoped cancellation', async () => {
  const h=harness();
  for(const value of [{kind:'desktop_task',appName:'Notepad',task:''},{kind:'close_app',appName:'PowerShell'}])assert.equal((await h.controller.run(value)).status,'failed');
  assert.equal(h.children.length,0);
  const pending=h.controller.run({kind:'desktop_task',appName:'Notepad',task:'Type $(literal) text'},'worker-one');
  await h.ready();
  const child=h.children[0];assert.ok(child.exe.includes('.runtime'));assert.ok(child.args[1].endsWith('action_server.py'));assert.ok(child.args.includes('--gui'));assert.equal(child.input.requestId,'worker-one');assert.equal(child.input.task,'Type $(literal) text');assert.equal(child.options.env.ANONYMIZED_TELEMETRY,'false');
  assert.ok(!child.args.some(arg=>arg.includes('literal')));h.controller.stop('worker-one');assert.equal((await pending).status,'cancelled');
});

test('study exports keep full literal content and destination result through IPC',async()=>{
  const h=harness();
  const action={kind:'export_summary_to_notion',destination:'existing',title:'Summary',pageName:'Project Docs',content:'All points\n'+('word '.repeat(600))+'\nCaveats',studyTaskId:'a'.repeat(10),videoUrl:'https://youtu.be/abcdefghijk'};
  const pending=h.controller.run(action,'export-one');await h.ready();const child=h.children[0];
  assert.equal(child.input.content,action.content);assert.equal(child.input.pageName,'Project Docs');
  h.line(child,{type:'result',status:'succeeded',message:'Matched after reload',data:{notionPageId:'b'.repeat(32),destinationTitle:'Project Docs'}});
  const result=await pending;assert.equal(result.data.notionPageId,'b'.repeat(32));assert.equal(result.data.destinationTitle,'Project Docs');
  for(const invalid of [{...action,content:'x'.repeat(20001)},{...action,destination:'replace'},{...action,destination:'new'},{...action,studyTaskId:'../secret'}]) assert.throws(()=>validateAction(invalid));
});

test('NotebookLM validates URLs and retains a partial notebook link without claiming success',async()=>{
  const h=harness(), action={kind:'notebooklm_mindmap',newNotebook:true,videoUrl:'https://youtu.be/abcdefghijk'};
  for(const notebookUrl of ['https://evil.test/notebook/abc','https://accounts.google.com/','https://notebook.google.com.evil.test/notebook/abc']) assert.throws(()=>validateAction({...action,newNotebook:false,notebookUrl}));
  assert.throws(()=>validateAction({...action,notebookUrl:'https://notebook.google.com/notebook/abc'}));
  const pending=h.controller.run(action,'notebook-one');await h.ready();
  h.line(h.children[0],{type:'result',status:'failed',message:'Generation not verified',data:{notebookUrl:'https://notebook.google.com/notebook/abc',videoUrl:action.videoUrl}});
  const result=await pending;assert.equal(result.status,'failed');assert.equal(result.data.notebookUrl,'https://notebook.google.com/notebook/abc');
});
