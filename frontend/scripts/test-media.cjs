// Browser-device lifecycle tests with fake streams; no microphone or network.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const ts = require('typescript');
const path = require('node:path');

function load(file, globals) {
  const source = fs.readFileSync(path.join(__dirname, '../src/services', file), 'utf8');
  const js = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText;
  const exports = {};
  vm.runInNewContext(js, { exports, ...globals });
  return exports;
}

function deferred() {
  let resolve;
  const promise = new Promise(r => { resolve = r; });
  return { promise, resolve };
}

function stream() {
  const track = { stopped: false, ended: null, stop() { this.stopped = true; }, addEventListener(_, callback) { this.ended = callback; } };
  return { track, getTracks: () => [track], getVideoTracks: () => [track], getAudioTracks: () => [track] };
}

test('late microphone permission cannot reopen a stopped session', async () => {
  const pending = deferred();
  const { AudioStreamer } = load('audioCapture.ts', { navigator: { mediaDevices: { getUserMedia: () => pending.promise } } });
  const capture = new AudioStreamer();
  const started = capture.start(() => { assert.fail('audio must not be sent'); });
  capture.stop();
  const raw = stream();
  pending.resolve(raw);
  await started;
  assert.equal(raw.track.stopped, true);
  assert.equal(capture.isStreaming, false);
});

test('late screen permission releases tracks after cancellation', async () => {
  const pending = deferred();
  const { MediaCapture } = load('mediaCapture.ts', { navigator: { mediaDevices: { getDisplayMedia: () => pending.promise } } });
  const capture = new MediaCapture();
  const started = capture.start({ source: 'screen_share' });
  capture.stop();
  const raw = stream();
  pending.resolve(raw);
  await started;
  assert.equal(raw.track.stopped, true);
  assert.equal(capture.getStream(), null);
  assert.equal(capture.isRecording, false);
});

test('ending screen sharing triggers input cleanup', async () => {
  const raw = stream();
  let interval, intervalCleared = false, reported = false;
  const { MediaCapture } = load('mediaCapture.ts', {
    navigator: { mediaDevices: { getDisplayMedia: async () => raw } },
    document: { createElement: tag => tag === 'video' ? { play: async () => {}, videoWidth: 100, videoHeight: 100 } : {} },
    setInterval: callback => { interval = callback; return 1; },
    clearInterval: () => { intervalCleared = true; },
  });
  const capture = new MediaCapture();
  await capture.start({ source: 'screen_share', onError: () => { reported = true; capture.stop(); } });
  assert.equal(typeof interval, 'function');
  raw.track.ended();
  assert.equal(reported, true);
  assert.equal(raw.track.stopped, true);
  assert.equal(intervalCleared, true);
  assert.equal(capture.isRecording, false);
});

test('microphone disconnect stops its worklet and releases the stream', async () => {
  const raw = stream();
  let closed = false;
  const { AudioStreamer } = load('audioCapture.ts', {
    navigator: { mediaDevices: { getUserMedia: async () => raw } },
    AudioContext: class {
      audioWorklet = { addModule: async () => {} };
      createMediaStreamSource() { return { connect() {} }; }
      close() { closed = true; }
    },
    AudioWorkletNode: class { port = {}; disconnect() {} },
  });
  const capture = new AudioStreamer();
  let reported = false;
  await capture.start(() => {}, undefined, () => { reported = true; capture.stop(); });
  raw.track.ended();
  assert.equal(reported, true);
  assert.equal(closed, true);
  assert.equal(raw.track.stopped, true);
  assert.equal(capture.isStreaming, false);
});
