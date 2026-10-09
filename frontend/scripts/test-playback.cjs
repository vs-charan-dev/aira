// Actual playback lifecycle and output metering, with no devices or Gemini calls.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');

function load(name, globals) {
  const source = fs.readFileSync(path.join(__dirname, '../src/services', name), 'utf8');
  const js = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText;
  const exports = {};
  vm.runInNewContext(js, { exports, console, ...globals });
  return exports;
}
function fixture({ delayedDecode = false, suspended = false, interrupted = false, sinkFailure = false } = {}) {
  const meter = load('playbackMeter.ts', {});
  let devices = [{ kind: 'audiooutput', deviceId: 'default', label: 'Default - Bluetooth', groupId: 'bt' }, { kind: 'audiooutput', deviceId: 'bt', label: 'Headphones', groupId: 'bt' }];
  const events = new Map();
  const mediaDevices = { enumerateDevices: async () => devices, addEventListener: (name, fn) => events.set(name, fn), removeEventListener: name => events.delete(name) };
  const output = load('audioOutput.ts', { navigator: { mediaDevices } });
  let resolveResume, now = 1000;
  const decodes = [];
  const sources = [];
  const nodes = [];
  const contexts = [];
  class Context {
    state = interrupted ? 'interrupted' : suspended ? 'suspended' : 'running'; currentTime = 1; destination = {};
    constructor(options) { this.options = options; contexts.push(this); }
    setSinkId(id) { this.sink = id; return sinkFailure ? Promise.reject(new Error('Speaker unavailable')) : Promise.resolve(); }
    createAnalyser() {
      const node = { fftSize: 256, level: .05, connect() {}, disconnect() { this.level = 0; }, getFloatTimeDomainData(data) { data.fill(this.level); } };
      nodes.push(node); return node;
    }
    decodeAudioData() { return delayedDecode ? new Promise(resolve => { decodes.push(resolve); }) : Promise.resolve({ duration: .25 }); }
    resume() { return new Promise(resolve => { resolveResume = () => { this.state = 'running'; resolve(); }; }); }
    createBufferSource() { const source = { connect() {}, start(at) { this.at = at; }, stop() { this.stopped = true; }, onended: null }; sources.push(source); return source; }
    close() { this.state = 'closed'; return Promise.resolve(); }
  }
  const playback = load('audioPlayback.ts', { Date: { now: () => now }, AudioContext: Context, atob: value => Buffer.from(value, 'base64').toString('binary'), require: name => {
    if (name === './playbackMeter') return meter;
    assert.equal(name, './audioOutput'); return output;
  } });
  return { ...playback, meter, output, events, contexts, sources, nodes, decodes, changeDevices: value => { devices = value; }, decode: () => decodes.shift()({ duration: .25 }), resume: () => resolveResume(), advance: ms => { now += ms; } };
}

test('mouth meter measures output and releases on stop; chunks schedule sequentially', async () => {
  const f = fixture();
  const audio = new f.AudioPlayback();
  await audio.enqueue('AAAA'); await audio.enqueue('AAAA');
  assert.ok(f.meter.getPlaybackEnergy() > .3);
  assert.equal(f.sources[1].at, f.sources[0].at + .25);
  assert.equal(audio.isPlaying, true);
  f.nodes[0].level = 0;
  assert.equal(f.meter.getPlaybackEnergy(), 0, 'silence closes the mouth while playback remains open');
  audio.stop(); audio.stop();
  assert.ok(f.sources.every(source => source.stopped));
  assert.equal(audio.isPlaying, false);
  assert.equal(f.meter.getPlaybackEnergy(), 0);
  assert.equal(f.contexts[0].state, 'closed');
});

test('interrupt during decoding cannot restart speech or reopen mouth', async () => {
  const f = fixture({ delayedDecode: true });
  const audio = new f.AudioPlayback();
  const pending = audio.enqueue('AAAA');
  await new Promise(resolve => setImmediate(resolve));
  audio.stop(); f.decode(); await pending;
  assert.equal(f.sources.length, 0);
  assert.equal(f.meter.getPlaybackEnergy(), 0);
});

test('Bluetooth removal releases stale queued speech and next reply opens current default output', async () => {
  const f = fixture();
  const release = f.output.watchAudioOutputs();
  await f.output.refreshAudioOutputs();
  const audio = new f.AudioPlayback();
  await audio.enqueue('AAAA');
  f.changeDevices([{ kind: 'audiooutput', deviceId: 'default', label: 'Default - Speakers', groupId: 'internal' }]);
  f.events.get('devicechange')();
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(f.contexts[0].state, 'closed');
  assert.equal(f.sources[0].stopped, true);
  await audio.enqueue('AAAA');
  assert.equal(f.contexts.length, 2);
  assert.equal(f.contexts[1].options, undefined, 'use hardware sample rate, while WAV still carries PCM rate');
  assert.equal(audio.isPlaying, true);
  audio.stop(); release(); assert.equal(f.events.size, 0);
});

test('explicit speaker selection applies to playback and falls back after disconnection', async () => {
  const f = fixture();
  await f.output.refreshAudioOutputs();
  f.output.selectAudioOutput('bt');
  const audio = new f.AudioPlayback();
  await audio.enqueue('AAAA');
  assert.equal(f.contexts[0].sink, 'bt');
  f.changeDevices([{ kind: 'audiooutput', deviceId: 'default', label: 'Speakers', groupId: 'internal' }]);
  await f.output.refreshAudioOutputs(true);
  assert.equal(f.output.getAudioOutputState().deviceId, '');
  assert.equal(f.contexts[0].state, 'closed');
  await audio.enqueue('AAAA');
  assert.equal(f.contexts[1].sink, undefined);
  audio.stop();
});

test('same speaker inventory does not cut off speech when a camera changes', async () => {
  const f = fixture();
  await f.output.refreshAudioOutputs();
  const audio = new f.AudioPlayback();
  await audio.enqueue('AAAA');
  await f.output.refreshAudioOutputs(true);
  assert.equal(f.contexts[0].state, 'running');
  assert.equal(f.sources[0].stopped, undefined);
  audio.stop();
});

test('output reset during decoding prevents stale speech and permits the next reply', async () => {
  const f = fixture({ delayedDecode: true });
  const audio = new f.AudioPlayback();
  const pending = audio.enqueue('AAAA');
  await new Promise(resolve => setImmediate(resolve));
  f.output.resetAudioOutput(); f.decode(); await pending;
  assert.equal(f.sources.length, 0);
  assert.equal(f.meter.getPlaybackEnergy(), 0);
  const next = audio.enqueue('AAAA');
  await new Promise(resolve => setImmediate(resolve));
  f.decode(); await next;
  assert.equal(f.sources.length, 1);
  audio.stop();
});

test('interrupted output resumes before scheduling speech', async () => {
  const f = fixture({ interrupted: true });
  const audio = new f.AudioPlayback();
  const pending = audio.enqueue('AAAA');
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(f.sources.length, 0);
  f.resume(); await pending;
  assert.equal(f.sources.length, 1);
  audio.stop();
});

test('speaker routing failures are visible and do not claim playback', async () => {
  const f = fixture({ sinkFailure: true });
  await f.output.refreshAudioOutputs();
  f.output.selectAudioOutput('bt');
  const audio = new f.AudioPlayback();
  await audio.enqueue('AAAA');
  assert.match(f.output.getAudioOutputState().error, /Speaker unavailable/);
  assert.equal(audio.isPlaying, false);
  assert.equal(f.sources.length, 0);
  audio.stop(); f.output.resetAudioOutput();
  assert.equal(f.output.getAudioOutputState().error, '');
});

test('interrupt during audio resume cannot schedule a stale chunk', async () => {
  const f = fixture({ suspended: true });
  const audio = new f.AudioPlayback();
  const pending = audio.enqueue('AAAA');
  await new Promise(resolve => setImmediate(resolve));
  audio.stop(); f.resume(); await pending;
  assert.equal(f.sources.length, 0);
  assert.equal(f.meter.getPlaybackEnergy(), 0);
});
test('simultaneous chunks decode in arrival order and microphone gate includes output tail', async () => {
  const f=fixture({delayedDecode:true}), audio=new f.AudioPlayback();
  const first=audio.enqueue('AAAA'), second=audio.enqueue('AQAB');
  assert.equal(f.isPlaybackBlockingInput(),true,'gate closes before asynchronous decoding');
  await new Promise(resolve=>setImmediate(resolve)); assert.equal(f.decodes.length,1);
  f.decode(); await first; await new Promise(resolve=>setImmediate(resolve)); assert.equal(f.decodes.length,1);
  f.decode(); await second;
  assert.equal(f.sources[0].at,1.08); assert.equal(f.sources[1].at,f.sources[0].at+.25);
  f.sources.forEach(source=>source.onended());
  assert.equal(f.isPlaybackActive(),false); assert.equal(f.isPlaybackBlockingInput(),true);
  f.advance(251); assert.equal(f.isPlaybackBlockingInput(),false); audio.stop();
});
test('stopping detaches old decode queue so a new reply does not wait or play stale audio', async () => {
  const f=fixture({delayedDecode:true}), audio=new f.AudioPlayback();
  const first=audio.enqueue('AAAA'), stale=audio.enqueue('AQAB');
  await new Promise(resolve=>setImmediate(resolve)); audio.stop();
  const fresh=audio.enqueue('AgAC'); await new Promise(resolve=>setImmediate(resolve));
  assert.equal(f.decodes.length,2);
  f.decodes.pop()({duration:.25}); await fresh; assert.equal(f.sources.length,1);
  f.decode(); await Promise.all([first,stale]); assert.equal(f.sources.length,1); audio.stop();
});
test('speech-interruption defaults off, persists explicit opt-in and permits intentional barge-in', () => {
  const data=new Map(), f=fixture();
  const preferences=load('audioInteraction.ts',{localStorage:{getItem:key=>data.get(key),setItem:(key,value)=>data.set(key,value)},require:()=>f});
  const audio=new f.AudioPlayback(); const pending=audio.enqueue('AAAA');
  assert.equal(preferences.canSendMicrophoneAudio(),false);
  preferences.setAllowSpeechInterruption(true); assert.equal(preferences.canSendMicrophoneAudio(),true);
  assert.equal(data.get('aira.allow-speech-interruption.v2'),'true');
  preferences.setAllowSpeechInterruption(false); assert.equal(preferences.canSendMicrophoneAudio(),false);
  audio.stop(); return pending;
});

