// Exercise the real hooks with delayed devices and fake transport, without AI or microphone access.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');
const deferred = () => { let resolve, reject; const promise = new Promise((yes, no) => { resolve = yes; reject = no; }); return { promise, resolve, reject }; };
function harness() {
  const events = [], microphones = [], screens = [], cache = {};
  let playbackBlocked = false, allowInterruption = false;
  const voice = { status: 'disconnected', muted: false, error: null, setStatus(v) { this.status = v; }, setMuted(v) { this.muted = v; }, setShowPanel() {}, setError(v) { this.error = v; this.status = 'error'; }, addToolEvent() {} };
  const capture = { sessionId: null, status: 'idle', sourceType: 'voice', ready: false, capturePace: 'balanced', setSessionId(v) { this.sessionId = v; }, setStatus(v) { this.status = v; }, setSourceType(v) { this.sourceType = v; }, setActiveStream(v) { this.activeStream = v; }, setReady(v) { this.ready = v; }, setError(v) { this.error = v; }, reset() { this.sessionId = null; this.status = 'idle'; this.ready = false; this.error = null; } };
  function store(state) { const hook = () => state; hook.getState = () => state; return hook; }
  const ws = new Proxy({ waitUntilReady: async () => {}, sendLiveSessionStart: () => { events.push('recall-start'); voice.status = 'connected'; }, sendCaptureStart: (id, source) => { events.push(`capture-start:${source}`); capture.ready = true; } }, { get: (obj, name) => obj[name] || ((...args) => events.push([name, ...args])) });
  class Mic {
    constructor() { this.permission = deferred(); microphones.push(this); this.isStreaming = false; }
    async start(callback, _stream, onError) { this.onError = onError; await this.permission.promise; if (this.stopped) return; this.isStreaming = true; this.callback = callback; }
    stop() { this.stopped = true; this.isStreaming = false; }
  }
  class Screen {
    constructor() { this.permission = deferred(); screens.push(this); }
    async start() { await this.permission.promise; }
    stop() { this.stopped = true; }
    getStream() { return {}; }
  }
  const imports = {
    react: { useCallback: fn => fn, useRef: value => ({ current: value }) }, uuid: { v4: (() => { let id = 0; return () => `session-${++id}`; })() },
    '../services/audioCapture': { AudioStreamer: Mic }, '../services/mediaCapture': { MediaCapture: Screen },
    '../stores/voiceStore': { useVoiceStore: store(voice) }, '../stores/captureStore': { useCaptureStore: store(capture) },
    '../stores/palaceStore': { usePalaceStore: store({ currentRoomId: null }) },
    '../stores/companionStore': { useCompanionStore: store({ update() {} }) },
    '../services/audioPlayback': { stopAllPlayback: () => events.push('playback-stopped') }, './useWS': { useWS: () => ws },
    '../services/audioInteraction': { canSendMicrophoneAudio: () => allowInterruption || !playbackBlocked, getAllowSpeechInterruption: () => allowInterruption },
  };
  function load(name) {
    if (cache[name]) return cache[name];
    const exports = {}; cache[name] = exports;
    const source = fs.readFileSync(path.join(__dirname, '../src/hooks', name + '.ts'), 'utf8');
    const js = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS } }).outputText;
    vm.runInNewContext(js, { exports, window: {}, setTimeout, clearTimeout, require: value => imports[value] || load(value.replace('./', '')) });
    return exports;
  }
  const recall = load('useVoice'), cap = load('useCapture');
  return { recall: recall.useVoice(), releaseAudioHold: recall.releaseAudioHold, cap: cap.useCapture(), events, microphones, screens, voice, capture, blockPlayback(value) { playbackBlocked = value; }, allowInterruption(value) { allowInterruption = value; } };
}
const tick = () => new Promise(resolve => setImmediate(resolve));
test('recall → screen → recall releases input/playback and starts only the selected backend mode', async () => {
  const h = harness();
  const first = h.recall.connect(); await tick();
  assert.equal(h.voice.status, 'connecting');
  assert.ok(!h.events.includes('recall-start'));
  h.microphones[0].permission.resolve(); await first;
  assert.equal(h.voice.status, 'connected');
  const second = h.cap.startCapture('screen_share'); await tick();
  assert.ok(h.microphones[0].stopped);
  assert.equal(h.voice.status, 'disconnected');
  assert.ok(!h.events.includes('capture-start:screen_share'));
  h.screens[0].permission.resolve(); await tick();
  h.microphones[1].permission.resolve(); await second;
  assert.ok(h.events.includes('capture-start:screen_share'));
  const third = h.recall.connect(); await tick();
  assert.ok(h.screens[0].stopped && h.microphones[1].stopped);
  h.microphones[2].permission.resolve(); await third;
  assert.equal(h.voice.status, 'connected');
  h.recall.disconnect();
  assert.ok(h.microphones[2].stopped);
  assert.ok(h.events.filter(event => event === 'playback-stopped').length >= 3);
});
test('rapid mode replacement cancels late screen permission and cannot open a stale capture', async () => {
  const h = harness();
  const pending = h.cap.startCapture('screen_share'); await tick();
  const recall = h.recall.connect(); await tick();
  h.microphones[1].permission.resolve(); await recall;
  h.screens[0].permission.resolve(); await pending;
  assert.ok(!h.events.includes('capture-start:screen_share'));
  assert.ok(h.screens[0].stopped);
  assert.equal(h.voice.status, 'connected');
  h.recall.disconnect();
});
test('late microphone denial after a replacement does not stop or error the new voice session', async () => {
  const h = harness();
  const first = h.recall.connect(); await tick(); h.recall.disconnect();
  const second = h.recall.connect(); await tick();
  h.microphones[1].permission.resolve(); await second;
  h.microphones[0].permission.reject(new Error('old prompt denied')); await first;
  assert.equal(h.voice.status, 'connected'); assert.equal(h.voice.error, null);
  h.recall.disconnect();
});
test('permission failure opens no paid capture and duplicate requests acquire only one microphone', async () => {
  const h = harness();
  const first = h.cap.startCapture('screen_share'); await tick();
  await h.cap.startCapture('screen_share');
  assert.equal(h.microphones.length, 1);
  h.screens[0].permission.reject(new Error('cancelled')); await first;
  assert.equal(h.capture.status, 'error');
  assert.ok(!h.events.includes('capture-start:screen_share'));
  h.cap.stopCapture();
});
test('recall and capture suppress microphone transmission during output, then resume without reopening devices', async () => {
  const h = harness();
  const recall = h.recall.connect(); await tick(); h.microphones[0].permission.resolve(); await recall;
  h.releaseAudioHold(); h.blockPlayback(true); h.microphones[0].callback('echo');
  assert.ok(!h.events.some(event => Array.isArray(event) && event[1] === 'echo'));
  h.blockPlayback(false); h.microphones[0].callback('user');
  assert.ok(h.events.some(event => event[0] === 'sendAudioChunk' && event[1] === 'user'));
  const capture = h.cap.startCapture('voice'); await tick(); h.microphones[1].permission.resolve(); await capture;
  h.blockPlayback(true); h.microphones[1].callback('echo');
  assert.ok(!h.events.some(event => Array.isArray(event) && event.includes('echo')));
  h.blockPlayback(false); h.microphones[1].callback('capture-user');
  assert.ok(h.events.some(event => event[0] === 'sendCaptureVoiceChunk' && event[2] === 'capture-user'));
  h.cap.stopCapture();
});

test('enabled interruption sends user speech during the greeting hold and current playback',async()=>{
  const h=harness();h.allowInterruption(true);
  const pending=h.recall.connect();await tick();h.microphones[0].permission.resolve();await pending;
  h.blockPlayback(true);h.microphones[0].callback('interrupt-greeting');
  assert.ok(h.events.some(event=>event[0]==='sendAudioChunk'&&event[1]==='interrupt-greeting'));
  h.recall.disconnect();
});

test('Stop releases playback even without an active Live session',()=>{
  const h=harness();h.recall.disconnect();assert.ok(h.events.includes('playback-stopped'));
});
