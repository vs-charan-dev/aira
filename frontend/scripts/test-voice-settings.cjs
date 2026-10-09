// Exercise preview cancellation in the real component without Gemini or audio hardware.
const test = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');
const ts = require('typescript');
const tick = () => new Promise(resolve => setImmediate(resolve));
function deferred() { let resolve; const promise = new Promise(done => { resolve = done; }); return { promise, resolve }; }
function harness() {
  const slots = [], requests = [], players = [], saves = [], timers = new Map();
  let index = 0, effects = [], tree, voiceStatus = 'disconnected';
  const React = {
    useState(value) { const i = index++; slots[i] ??= { value }; return [slots[i].value, next => { slots[i].value = typeof next === 'function' ? next(slots[i].value) : next; }]; },
    useRef(value) { const i = index++; slots[i] ??= { current: value }; return slots[i]; },
    useEffect(fn, deps) { const i = index++, old = slots[i]; if (!old || deps.some((v, n) => v !== old.deps[n])) effects.push(() => { old?.cleanup?.(); slots[i] = { deps, cleanup: fn() }; }); },
  };
  class Player {
    constructor() { players.push(this); this.isPlaying = false; this.chunks = []; }
    async activate() {}
    async enqueue(audio) { this.chunks.push(audio); this.isPlaying = true; }
    stop() { this.stopped = true; this.isPlaying = false; }
  }
  const settingsApi = {
    getSettings: async () => ({ voiceName: 'Aoede', voices: [{name:'Aoede',description:'Breezy'}, {name:'Kore',description:'Firm'}] }),
    previewVoice(name, signal) { const request = { ...deferred(), name, signal }; requests.push(request); return request.promise; },
    async saveVoice(name) { saves.push(name); },
  };
  const jsx = (type, props) => ({ type, props });
  const imports = { react: React, 'react/jsx-runtime': { jsx, jsxs: jsx }, '../../services/settingsApi': { settingsApi }, '../../services/audioPlayback': { AudioPlayback: Player }, '../../services/audioOutput': { getAudioOutputState: () => ({error:''}) }, '../../stores/voiceStore': { useVoiceStore: fn => fn({status:voiceStatus}) }, '../../stores/captureStore': { useCaptureStore: fn => fn({status:'idle'}) } };
  const exports = {};
  const source = fs.readFileSync(path.join(__dirname, '../src/components/hud/VoiceSettings.tsx'), 'utf8');
  const js = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX } }).outputText;
  vm.runInNewContext(js, { exports, AbortController, require: name => imports[name], setTimeout(fn) { const id = timers.size + 1; timers.set(id, fn); return id; }, clearTimeout(id) { timers.delete(id); } });
  function render() { index = 0; effects = []; tree = exports.VoiceSettings(); effects.forEach(fn => fn()); return tree; }
  function nodes(node) { return Array.isArray(node) ? node.flatMap(nodes) : node && typeof node === 'object' ? [node, ...nodes(node.props?.children)] : []; }
  function text(node) { return Array.isArray(node) ? node.map(text).join('') : node && typeof node === 'object' ? text(node.props.children) : node == null || node === false ? '' : String(node); }
  const button = starts => nodes(tree).find(node => node.type === 'button' && text(node).startsWith(starts));
  const select = () => nodes(tree).find(node => node.type === 'select');
  render();
  return { async flush() { await tick(); render(); }, button, select, players, requests, saves, text: () => text(tree), finish(name='Aoede') { requests.at(-1).resolve({voiceName:name, text:'Hi Charan.', audio:'fake-pcm', sampleRate:24000,durationSeconds:.2,cached:true}); }, cleanup() { slots.forEach(slot => slot?.cleanup?.()); }, busy() { voiceStatus = 'connected'; render(); }, timers };
}
test('closing settings during preview prevents late speech', async () => {
  const h = harness(); await h.flush();
  h.button('▶').props.onClick(); await h.flush();
  h.cleanup(); assert.ok(h.requests[0].signal.aborted); h.finish(); await tick();
  assert.equal(h.players[0].chunks.length, 0); assert.ok(h.players[0].stopped);
});
test('changing voice cancels the old preview, and saving is separate from previewing', async () => {
  const h = harness(); await h.flush();
  h.button('▶').props.onClick(); await h.flush();
  h.select().props.onChange({target:{value:'Kore'}}); h.finish(); await h.flush();
  assert.equal(h.players[0].chunks.length, 0); assert.equal(h.saves.length, 0);
  h.button('▶').props.onClick(); await h.flush(); assert.equal(h.requests[1].name, 'Kore');
  h.finish('Kore'); await h.flush(); assert.deepEqual(h.players[1].chunks, ['fake-pcm']); assert.ok(h.text().includes('local cached preview'));
  h.button('Save voice').props.onClick(); await h.flush(); assert.deepEqual(h.saves, ['Kore']); assert.ok(h.players[1].stopped);
  h.cleanup();
});
test('starting a conversation cancels a pending preview and disables previewing', async () => {
  const h = harness(); await h.flush(); h.button('▶').props.onClick(); await h.flush();
  h.busy(); h.finish(); await h.flush();
  assert.equal(h.players[0].chunks.length, 0); assert.ok(h.requests[0].signal.aborted); assert.ok(h.button('▶').props.disabled);
  h.cleanup();
});
