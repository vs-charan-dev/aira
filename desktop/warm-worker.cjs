const { spawn } = require('node:child_process');
const path = require('node:path');

class WarmWorker {
  constructor(root, gui, spawnProcess = spawn) {
    this.root = root; this.gui = gui; this.spawn = spawnProcess;
    this.instance = null; this.pending = null; this.closed = false;
  }
  async prepare() {
    if (this.closed) throw new Error('Desktop worker is shut down.');
    if (this.instance?.closing) await this.instance.exited;
    if (this.closed) throw new Error('Desktop worker is shut down.');
    if (this.instance) return this.instance.ready;
    let readyResolve, readyReject, exitResolve;
    const instance = { child: null, buffer: '', closing: false,
      ready: new Promise((resolve,reject) => { readyResolve=resolve; readyReject=reject; }),
      exited: new Promise(resolve => { exitResolve=resolve; }), readyDone: false };
    // Startup failures during proactive warming must not produce unhandled rejections.
    instance.ready.catch(() => {});
    this.instance = instance;
    const fail = () => {
      if (!instance.readyDone) { instance.readyDone=true; readyReject(new Error('Desktop worker unavailable.')); }
      if (this.pending?.instance === instance) {
        const pending=this.pending; this.pending=null;
        pending.resolve({status:'failed',message:'Desktop worker stopped. Completion was not verified; inspect partial changes.'});
      }
    };
    const exited = () => {
      clearTimeout(instance.startTimer); fail();
      if (this.instance === instance) this.instance=null;
      exitResolve();
    };
    try {
      const exe=path.join(this.root,this.gui ? '.runtime/windows-use' : '.venv','Scripts','python.exe');
      instance.child=this.spawn(exe,['-u',path.join(this.root,'desktop','action_server.py'),...(this.gui ? ['--gui'] : [])], {
        cwd:this.root,windowsHide:true,stdio:['pipe','pipe','pipe'],
        env:{...process.env,AIRA_CONTROL_DIAGNOSTICS:'0',ANONYMIZED_TELEMETRY:'false',TEMP:path.join(this.root,'.cache','tmp'),TMP:path.join(this.root,'.cache','tmp'),PYTHONPYCACHEPREFIX:path.join(this.root,'.cache','pycache')},
      });
      instance.child.stdout.setEncoding('utf8');
      instance.child.stdout.on('data',chunk => {
        instance.buffer+=chunk;
        if(instance.buffer.length>128000) { void this.stop(); return; }
        let index;
        while((index=instance.buffer.indexOf('\n'))>=0) {
          const line=instance.buffer.slice(0,index); instance.buffer=instance.buffer.slice(index+1);
          let message; try { message=JSON.parse(line); } catch { continue; }
          if(message.type==='ready' && !instance.closing && !instance.readyDone) {
            instance.readyDone=true; clearTimeout(instance.startTimer); readyResolve();
          } else if(message.type==='unavailable') { void this.stop(); }
          else if(this.pending?.instance===instance && message.requestId===this.pending.id && !instance.closing) {
            if(message.type==='result') {
              const pending=this.pending; this.pending=null; pending.resolve(message);
            } else this.pending.onMessage(message);
          }
        }
      });
      instance.child.stderr.on('data',() => {});
      instance.child.stdin.on('error',() => { void this.stop(); });
      instance.child.once('error',exited); instance.child.once('close',exited);
      instance.startTimer=setTimeout(() => { void this.stop(); },45000);
      instance.startTimer.unref?.();
    } catch { exited(); }
    return instance.ready;
  }
  async run(action,id,onMessage,onReady = () => {}) {
    await this.prepare();
    const instance=this.instance;
    if(!instance || instance.closing || this.pending) throw new Error('Desktop worker is unavailable or busy.');
    onReady();
    return new Promise(resolve => {
      this.pending={instance,id,onMessage,resolve};
      try { instance.child.stdin.write(JSON.stringify({...action,requestId:id})+'\n',error => { if(error) void this.stop(); }); }
      catch { void this.stop(); }
    });
  }
  async stop() {
    const instance=this.instance;
    if(!instance) return;
    instance.closing=true;
    instance.child?.kill();
    // Never let another action start while the previous process could still inject input.
    await instance.exited;
  }
  shutdown() { this.closed=true; return this.stop(); }
}
module.exports={WarmWorker};
