const test=require('node:test'), assert=require('node:assert/strict'), fs=require('node:fs'), path=require('node:path'), vm=require('node:vm'), ts=require('typescript');
function harness(native=true,current=true) {
  const listeners={}, results=[], stops=[], calls=[];
  let resolve; const promise=new Promise(yes=>resolve=yes);
  const ws={on:(type,fn)=>{listeners[type]=fn;return()=>delete listeners[type];},sendDesktopActionResult:(id,result)=>results.push({id,result})};
  const desktop={role:'owner',runAction:(...args)=>{calls.push(args);return promise;},stopAction:id=>stops.push(id)};
  const exports={}; const source=fs.readFileSync(path.join(__dirname,'../src/services/desktopActions.ts'),'utf8');
  const code=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2020}}).outputText;
  vm.runInNewContext(code,{exports,window:native?{airaDesktop:desktop}:{},Set});
  const dispose=exports.wireDesktopActions(ws,()=>current);
  const message={type:'desktop_action',requestId:'one',source:'recall',sessionId:null,action:{kind:'open_app',appName:'Notion'}};
  return {listeners,results,stops,calls,resolve,dispose,message};
}
test('browser or stopped originating voice fails without native execution', async()=>{
  for(const [native,current] of [[false,true],[true,false]]) { const h=harness(native,current); await h.listeners.desktop_action(h.message); assert.equal(h.calls.length,0);assert.equal(h.results[0].result.status,'failed');h.dispose(); }
});
test('deduplicates and sends verified native result to the waiting tool',async()=>{
  const h=harness(), first=h.listeners.desktop_action(h.message); await h.listeners.desktop_action(h.message);assert.equal(h.calls.length,1); assert.equal(h.results.length,0);
  h.resolve({status:'succeeded',message:'verified'});await first;assert.equal(h.results[0].result.message,'verified');h.dispose();
});
test('cancel is scoped, transport loss stops native input, and unmount suppresses late replies',async()=>{
  const h=harness(), first=h.listeners.desktop_action(h.message);
  h.listeners.desktop_action_cancel({requestId:'other'});assert.equal(h.stops.length,0);
  h.listeners.desktop_action_cancel({requestId:'one'});assert.equal(h.stops[0],'one');h.listeners.transport_closed();assert.equal(h.stops.length,2);
  h.dispose();h.resolve({status:'cancelled',message:'stopped'});await first;assert.equal(h.results.length,0);
});

test('late action results are not sent through a replacement connection',async()=>{
  const h=harness(), first=h.listeners.desktop_action(h.message);
  h.listeners.transport_closed();h.resolve({status:'cancelled',message:'stopped'});
  await first;assert.equal(h.results.length,0);assert.deepEqual(h.stops,['one']);h.dispose();
});

test('voice interruptions stop only the matching voice-owned action ID',async()=>{
  const h=harness(),pending=h.listeners.desktop_action(h.message);
  h.listeners.capture_interrupted({sessionId:'old-capture'});assert.equal(h.stops.length,0);
  h.listeners.live_interrupted({});assert.deepEqual(h.stops,['one']);
  h.resolve({status:'cancelled',message:'stopped'});await pending;h.dispose();
});

test('accepted background job survives speech interruption but scoped cancel stops it',async()=>{
  const h=harness(true,false),message={...h.message,source:'job',sessionId:'job-id'};
  const pending=h.listeners.desktop_action(message);
  assert.equal(h.calls.length,1);
  h.listeners.live_interrupted({});h.listeners.capture_interrupted({sessionId:'job-id'});
  assert.equal(h.stops.length,0);
  h.listeners.desktop_action_cancel({requestId:'one'});assert.deepEqual(h.stops,['one']);
  h.resolve({status:'cancelled',message:'job cancelled'});await pending;
  assert.equal(h.results[0].result.status,'cancelled');h.dispose();
});
