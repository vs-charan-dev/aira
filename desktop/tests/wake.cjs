const { test } = require('node:test');
const assert = require('node:assert/strict');
const { EventEmitter } = require('node:events');
const { WakeListener } = require('../wake.cjs');
function fakeChild() {
  const child = new EventEmitter();
  child.stdout = new EventEmitter(); child.stderr = new EventEmitter();
  child.kill = () => { child.killed = true; setImmediate(() => child.emit('exit', 0)); };
  return child;
}
test('wake is emitted only after local microphone process exits; split lines and repeats are handled', async () => {
  let spawned = 0, activated = 0;
  const child = fakeChild(), statuses = [];
  const wake = new WakeListener({ root: 'E:/AIRA', spawnProcess: () => { spawned++; return child; }, onStatus: value => statuses.push(value), onWake: () => { assert.ok(child.killed); activated++; } });
  wake.start(); wake.start();
  assert.equal(spawned, 1);
  child.stdout.emit('data', 'REA'); child.stdout.emit('data', 'DY\nWAKE\nWAKE\n');
  assert.equal(activated, 0);
  await wake.stop();
  assert.equal(activated, 1);
  assert.deepEqual(statuses, ['starting', 'listening']);
});
test('disabled/stopped listener cannot wake and repeated stop waits for release', async () => {
  const child = fakeChild();
  const wake = new WakeListener({ root: 'E:/AIRA', spawnProcess: () => child, onStatus: () => {}, onWake: () => assert.fail('stale wake') });
  wake.start();
  const first = wake.stop(), second = wake.stop();
  child.stdout.emit('data', 'WAKE\n');
  await Promise.all([first, second]);
  assert.equal(wake.child, null);
});
test('recognizer failure is reported and does not enter a respawn loop', async () => {
  let count = 0;
  const child = fakeChild(), statuses = [];
  const wake = new WakeListener({ root: 'E:/AIRA', spawnProcess: () => { count++; return child; }, onStatus: v => statuses.push(v), onWake: () => {} });
  wake.start(); child.stdout.emit('data', 'ERROR:Microphone unavailable\n'); child.emit('exit', 1);
  wake.start(); assert.equal(count, 1); assert.equal(statuses.at(-1), 'ERROR:Microphone unavailable');
  wake.retry(); wake.start(); assert.equal(count, 2); await wake.stop();
});
test('local test reports sanitized diagnostics, never activates Gemini, and completes after microphone release', async () => {
  const child = fakeChild(), diagnostics = [];
  let completed = 0, args;
  const wake = new WakeListener({ root: 'E:/AIRA', spawnProcess: (_, value) => { args = value; return child; }, onStatus: () => {}, onWake: () => assert.fail('test must not activate'), onDiagnostics: value => diagnostics.push(value), onTestComplete: () => { assert.ok(child.killed); completed++; } });
  wake.start({ test: true, threshold: 0.55 });
  assert.equal(args.at(-1), '20');
  assert.equal(args[args.indexOf('-ConfidenceThreshold') + 1], '0.55');
  child.stdout.emit('data', 'READY\nDIAG:{"level":42,"speechCount":1,"rejectedCount":0,"phrase":"hey eye rah","confidence":0.61,"matched":true,"culture":"en-US"}\nWAKE\n');
  assert.equal(wake.child, child);
  assert.equal(diagnostics[0].phrase, 'hey eye rah'); assert.equal(diagnostics[0].level, 42);
  child.stdout.emit('data', 'DIAG:not-json\nDIAG:{"level":500,"phrase":"private conversation","culture":"arbitrary","signal":"Too Loud!"}\nDONE\n');
  assert.equal(completed, 0);
  await wake.stop();
  assert.equal(completed, 1); assert.equal(diagnostics.length, 2);
  assert.equal(diagnostics[1].phrase, ''); assert.equal(diagnostics[1].level, 100); assert.equal(diagnostics[1].culture, '');
});
test('late diagnostics and completion from a cancelled test are ignored', async () => {
  const child = fakeChild();
  const wake = new WakeListener({ root: 'E:/AIRA', spawnProcess: () => child, onStatus: () => {}, onWake: () => assert.fail('stale activation'), onDiagnostics: () => assert.fail('stale diagnostics'), onTestComplete: () => assert.fail('stale test completion') });
  wake.start({ test: true }); const released = wake.stop();
  child.stdout.emit('data', 'DIAG:{"level":10}\nDONE\nWAKE\n');
  await released;
});

test('local stop triggers cancellation immediately, only in interrupt mode, without waiting for microphone exit', async () => {
  let interrupts=0, wakes=0, args;
  const child=fakeChild(), statuses=[];
  const wake=new WakeListener({root:'E:/AIRA',spawnProcess:(_,value)=>{args=value;return child;},onStatus:value=>statuses.push(value),onWake:()=>wakes++,onInterrupt:()=>interrupts++});
  wake.start({interrupt:true,threshold:.85});
  assert.ok(args.includes('-InterruptMode'));
  child.stdout.emit('data','READY\nWAKE\nINTERRUPT\nINTERRUPT\n');
  assert.equal(interrupts,1);assert.equal(wakes,0);assert.equal(child.killed,true);
  assert.deepEqual(statuses,['interrupt:starting','interrupt:listening']);
  await wake.stop();
  const other=fakeChild();
  const idle=new WakeListener({root:'E:/AIRA',spawnProcess:()=>other,onStatus:()=>{},onWake:()=>{},onInterrupt:()=>assert.fail('idle stop event')});
  idle.start();other.stdout.emit('data','INTERRUPT\n');await idle.stop();
});
