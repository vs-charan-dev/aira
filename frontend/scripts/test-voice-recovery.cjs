// Real voice lifecycle with fake devices/transport/timers. No microphone or API.
const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const ts=require('typescript');
function fixture() {
  const timers=new Map(),events=[],mics=[];let timerId=0,sessionId=0;
  const voice={status:'disconnected',sessionId:null,error:null,muted:false,
    setStatus(value){this.status=value;},setSessionId(value){this.sessionId=value;},
    setError(value){this.error=value;this.status='error';},setMuted(value){this.muted=value;},
    setShowPanel(){},setToolActivity(){},addToolEvent(){},markMicChunk(){}};
  const store=state=>Object.assign(()=>state,{getState:()=>state});
  const ws={waitUntilReady:async()=>{},sendLiveSessionStart:(context,id)=>events.push(['start',id]),
    sendLiveSessionEnd:()=>events.push(['end']),sendAudioChunk:(_,id)=>events.push(['audio',id]),checkLiveSession(){}};
  class Mic {
    constructor(){mics.push(this);}
    async start(callback){this.callback=callback;this.isStreaming=true;}
    stop(){this.isStreaming=false;this.stopped=true;}
  }
  const imports={react:{useCallback:fn=>fn,useRef:value=>({current:value})},
    '../services/audioCapture':{AudioStreamer:Mic},'../stores/voiceStore':{useVoiceStore:store(voice)},
    '../stores/captureStore':{useCaptureStore:store({status:'idle',sessionId:null})},
    '../stores/palaceStore':{usePalaceStore:store({currentRoomId:null})},
    '../stores/companionStore':{useCompanionStore:store({update(){}})},
    './useWS':{useWS:()=>ws},'./useCapture':{stopCapture(){}},
    '../services/audioPlayback':{stopAllPlayback(){}},
    '../services/audioInteraction':{getAllowSpeechInterruption:()=>false,canSendMicrophoneAudio:()=>true}};
  const exports={};
  const code=ts.transpileModule(fs.readFileSync(path.join(__dirname,'../src/hooks/useVoice.ts'),'utf8'),
    {compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
  const clear=id=>timers.delete(id);
  vm.runInNewContext(code,{exports,window:{},crypto:{randomUUID:()=>`session-${++sessionId}`},
    setTimeout:(fn,ms)=>{timers.set(++timerId,{fn,ms});return timerId;},clearTimeout:clear,
    setInterval:()=>++timerId,clearInterval:clear,require:name=>{assert.ok(imports[name],name);return imports[name];}});
  return {api:exports.useVoice(),...exports,voice,events,mics,
    fireRecovery(){for(const[id,t]of timers)if(t.ms===1500){timers.delete(id);t.fn();}},
    pendingRecovery:()=>[...timers.values()].filter(t=>t.ms===1500).length};
}
const tick=()=>new Promise(resolve=>setImmediate(resolve));

test('connecting microphone never queues audio before the server handshake',async()=>{
  const f=fixture();await f.api.connect();f.releaseAudioHold();f.mics[0].callback('pcm');
  assert.equal(f.events.filter(e=>e[0]==='audio').length,0);
  f.voice.setStatus('connected');f.mics[0].callback('pcm');
  assert.equal(f.events.filter(e=>e[0]==='audio').length,1);f.api.disconnect();
});
test('transport failure recovers once with a fresh session, without replaying audio',async()=>{
  const f=fixture();await f.api.connect();f.voice.setStatus('connected');f.releaseAudioHold();
  f.mics[0].callback('old');f.handleVoiceSessionEnded('audio_send_timeout','network');
  assert.equal(f.pendingRecovery(),1);assert.equal(f.mics[0].stopped,true);
  f.mics[0].callback('stale');assert.equal(f.events.filter(e=>e[0]==='audio').length,1);
  f.fireRecovery();await tick();
  assert.deepEqual(f.events.filter(e=>e[0]==='start').map(e=>e[1]),['session-1','session-2']);
  f.voice.setStatus('connected');f.handleVoiceSessionEnded('connection_error','network');
  assert.equal(f.pendingRecovery(),0);assert.equal(f.voice.error,'network');f.api.disconnect();
});
test('explicit Stop cancels a pending automatic recovery',async()=>{
  const f=fixture();await f.api.connect();f.handleVoiceSessionEnded('connection_error','network');
  f.api.disconnect();f.fireRecovery();await tick();
  assert.equal(f.events.filter(e=>e[0]==='start').length,1);
  assert.equal(f.voice.status,'disconnected');
});
test('planned cost, idle and duration pauses never restart or display a transport error',async()=>{
  for(const reason of ['estimated_cost_limit','idle_limit','duration_limit']){
    const f=fixture();await f.api.connect();f.handleVoiceSessionEnded(reason,'planned pause');
    assert.equal(f.pendingRecovery(),0);assert.equal(f.voice.status,'disconnected');assert.equal(f.voice.error,null);
  }
});
