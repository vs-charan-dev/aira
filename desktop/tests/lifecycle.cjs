const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
function harness() {
  const events={},handlers={},shortcuts={},windows=[],timers=new Map(),writes=[];
  let timerId=0,starts=0,stops=0,onAction; const modes=[];
  class Window {
    constructor() {
      this.messages=[];this.webContents={session:{setPermissionCheckHandler(){},setPermissionRequestHandler(){}},setWindowOpenHandler(){},on(){},isDestroyed:()=>false,send:(channel,value)=>this.messages.push({channel,value:{...value}}),getURL:()=> 'http://127.0.0.1:8000/palace'};
      windows.push(this);
    }
    isDestroyed(){return false;}setBounds(){}setIgnoreMouseEvents(){}setAlwaysOnTop(){}once(){}on(){}show(){}focus(){}hide(){}showInactive(){}loadURL(){return Promise.resolve();}
  }
  class Wake { constructor(options){this.options=options;}stop(){stops++;this.child=null;this.mode=null;return Promise.resolve();}start(options={}){starts++;this.mode=options.interrupt?'interrupt':'wake';modes.push(this.mode);this.child={};this.options.onStatus(options.interrupt?'interrupt:listening':'listening');}retry(){} }
  class Actions { constructor(options){onAction=options.onState;}stop(){} }
  const electron={app:{setPath(){},commandLine:{appendSwitch(){}},requestSingleInstanceLock:()=>true,on:(name,fn)=>events[name]=fn,whenReady:()=>Promise.resolve(),quit(){}},BrowserWindow:Window,Menu:{buildFromTemplate:x=>x},Tray:class{setContextMenu(){}setToolTip(){}on(){}},nativeImage:{createFromBitmap:()=>({})},globalShortcut:{register:(key,fn)=>{shortcuts[key]=fn;return true;},unregister(){},unregisterAll(){}},ipcMain:{on:(name,fn)=>events[name]=fn,handle:(name,fn)=>handlers[name]=fn},screen:{getCursorScreenPoint:()=>({x:0,y:0}),getDisplayNearestPoint:()=>({workArea:{x:0,y:0,width:1280,height:720}}),on(){}},powerMonitor:{on(){}},desktopCapturer:{}};
  const mockFs={mkdirSync(){},readFileSync:()=>JSON.stringify({wakeEnabled:true,controlEnabled:true}),writeFileSync:(file,value)=>writes.push(JSON.parse(value))};
  vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../main.cjs'),'utf8'),{require:name=>name==='electron'?electron:name==='node:fs'?mockFs:name==='./wake.cjs'?{WakeListener:Wake}:name==='./actions.cjs'?{DesktopActions:Actions}:require(name.startsWith('./')?path.join(__dirname,'..',name):name),process:{argv:[],env:{AIRA_ROOT:'E:\\Havetobuild\\AIRA'}},__dirname:path.join(__dirname,'..'),Buffer,URL,console,setInterval(){},setTimeout:fn=>{timers.set(++timerId,fn);return timerId;},clearTimeout:id=>timers.delete(id)});
  const tick=()=>new Promise(resolve=>setImmediate(resolve));
  const event=()=>({sender:windows[0].webContents,senderFrame:{url:'http://127.0.0.1:8000/palace'}});
  const host=()=>windows[0].messages.filter(m=>m.channel==='aira:host').at(-1).value;
  return {events,handlers,shortcuts,writes,modes,tick,event,host,setAction:value=>onAction(value),async fireTimer(){const list=[...timers.values()];timers.clear();for(const fn of list)await fn();},get starts(){return starts;},get stops(){return stops;}};
}
test('Stop/start retains desktop controls and enabled wake preference, rearming only while idle',async()=>{
  const h=harness();await h.tick();
  h.events['aira:ready'](h.event());await h.fireTimer();assert.equal(h.starts,1);
  const publish=busy=>h.events['aira:state'](h.event(),{busy,mood:busy?'listening':'idle'});
  publish(true);assert.equal(h.host().wakeStatus,'paused');assert.equal(h.host().controlEnabled,true);
  h.shortcuts['Control+Alt+Escape']();publish(false);await h.fireTimer();assert.equal(h.starts,2);
  assert.equal(h.host().wakeEnabled,true);assert.equal(h.host().controlEnabled,true);
  h.shortcuts['Control+Alt+A']();await h.tick();publish(true);await h.fireTimer();
  assert.equal(h.modes.at(-1),'interrupt');assert.equal(h.host().interruptStatus,'listening');assert.equal(h.host().wakeStatus,'paused');assert.equal(h.host().controlEnabled,true);
  assert.equal(h.writes.length,0,'Stop and activation must not persist a disabled preference');
});

test('audio preparation cannot leave the local stop listener disarmed during conversation',async()=>{
  const h=harness();await h.tick();h.events['aira:ready'](h.event());
  h.events['aira:state'](h.event(),{busy:true,mood:'listening'});
  await h.handlers['aira:prepare-audio'](h.event());await h.fireTimer();
  assert.equal(h.modes.at(-1),'interrupt');assert.equal(h.host().interruptStatus,'listening');
});

test('a desktop action beginning during wake-to-interrupt handoff cannot cancel the pending stop listener startup',async()=>{
  const h=harness();await h.tick();h.events['aira:ready'](h.event());await h.fireTimer();
  assert.equal(h.modes.at(-1),'wake');
  h.events['aira:state'](h.event(),{busy:true,mood:'listening'});
  h.setAction({running:true,label:'Working'});
  await h.fireTimer();assert.equal(h.modes.at(-1),'interrupt');assert.equal(h.host().interruptStatus,'listening');
});
