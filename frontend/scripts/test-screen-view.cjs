const test=require('node:test'), assert=require('node:assert/strict'), fs=require('node:fs'), path=require('node:path'), vm=require('node:vm'), ts=require('typescript');
function load(name,globals={}) {
  const exports={};
  const code=ts.transpileModule(fs.readFileSync(path.join(__dirname,'../src/services',name+'.ts'),'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2020}}).outputText;
  vm.runInNewContext(code,{exports,Set,...globals});return exports;
}
function harness(native=true) {
  const listeners={},results=[],calls=[];let resolve,current=true;
  const ws={on:(type,fn)=>{listeners[type]=fn;return()=>delete listeners[type];},sendScreenViewResult:(...args)=>results.push(args)};
  const desktop={role:'owner',screenSnapshot:()=>{calls.push(1);return new Promise(yes=>resolve=yes);}};
  const dispose=load('screenView',{window:native?{airaDesktop:desktop}:{}}).wireScreenViews(ws,()=>current);
  return {listeners,results,calls,dispose,resolve:data=>resolve(data),stop:()=>current=false,message:{requestId:'one',source:'recall',sessionId:null}};
}
test('one direct request yields one transient snapshot with no mode switch or replay',async()=>{
  const h=harness(),pending=h.listeners.screen_view_request(h.message);
  await h.listeners.screen_view_request(h.message);assert.equal(h.calls.length,1);
  h.resolve('jpeg');await pending;assert.deepEqual(h.results,[['one','jpeg']]);h.dispose();
});
test('stop, connection replacement and unmount suppress late screen delivery',async()=>{
  for(const event of ['stop','transport','dispose']) {
    const h=harness(),pending=h.listeners.screen_view_request(h.message);
    if(event==='stop')h.stop();else if(event==='transport')h.listeners.transport_closed();else h.dispose();
    h.resolve('jpeg');await pending;assert.equal(h.results.length,0);h.dispose();
  }
});
test('browser returns no image and never attempts native capture',async()=>{
  const h=harness(false);await h.listeners.screen_view_request(h.message);assert.deepEqual(h.results,[['one',null]]);h.dispose();
});
test('desktop control and wake listening are separate statuses',()=>{
  const status=load('desktopStatus').desktopStatus;
  const host={controlEnabled:true,wakeEnabled:false,wakeStatus:'disabled'};
  assert.equal(status(host),'Desktop · Controls on · Hey AIRA off');
  assert.equal(status({...host,wakeEnabled:true,wakeStatus:'paused'}),'Desktop · Controls on · Hey AIRA paused during activity');
  assert.match(status({...host,controlEnabled:false}),/Controls off/);
});
