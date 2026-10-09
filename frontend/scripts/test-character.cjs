// Exercise actual character effects through state changes without a browser/device.
const test=require('node:test'), assert=require('node:assert/strict'), vm=require('node:vm'), fs=require('node:fs'), path=require('node:path'), ts=require('typescript');
function harness() {
  const slots=[], events=new Map(), frames=new Map(); let index=0,effects=[],now=0,id=0,tree,subscriptions=0,cancelled=0;
  const React={useId:()=> 'character', useRef(value){const i=index++; slots[i]??={current:value}; return slots[i];},useEffect(fn,deps){const i=index++,old=slots[i];if(!old||deps.some((v,n)=>v!==old.deps[n]))effects.push(()=>{old?.cleanup?.(); slots[i]={deps,cleanup:fn()};});}};
  const node=()=>({attrs:{},setAttribute(name,value){this.attrs[name]=value;},getBoundingClientRect:()=>({left:0,top:0,width:480,height:270})});
  const jsx=(type,props)=>{if(props.ref&&!props.ref.current)props.ref.current=node();return{type,props};};
  const exports={}, code=ts.transpileModule(fs.readFileSync(path.join(__dirname,'../src/components/companion/AiraCharacter.tsx'),'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX}}).outputText;
  vm.runInNewContext(code,{exports,performance:{now:()=>now},requestAnimationFrame(fn){frames.set(++id,fn);return id;},cancelAnimationFrame(i){cancelled++;frames.delete(i);},window:{matchMedia:()=>({matches:false}),addEventListener:(name,fn)=>events.set(name,fn),removeEventListener:name=>events.delete(name),airaDesktop:{onCursor(fn){subscriptions++;events.set('cursor',fn);return()=>events.delete('cursor');}}},document:{documentElement:{addEventListener(){},removeEventListener(){}}},require:name=>name==='react'?React:name==='react/jsx-runtime'?{jsx,jsxs:jsx}:name.includes('playbackMeter')?{getPlaybackEnergy:()=>0}:{} });
  function render(mood){index=0;effects=[];tree=exports.AiraCharacter({mood,desktopGaze:true});effects.forEach(fn=>fn());}
  function nodes(value){return Array.isArray(value)?value.flatMap(nodes):value&&typeof value==='object'?[value,...nodes(value.props?.children)]:[];}
  render('idle');
  return {render, cursor:point=>events.get('cursor')(point), advance(n=1){for(let i=0;i<n;i++){now+=60;const [key,fn]=frames.entries().next().value;frames.delete(key);fn(now);}}, pupils:()=>nodes(tree).filter(n=>n.type==='g'&&n.props.ref?.current.attrs.transform?.startsWith('translate(')&&n.props.children?.[0]?.type==='ellipse'&&n.props.children[0].props.cy==='146').map(n=>n.props.ref.current.attrs.transform), counts:()=>({subscriptions,cancelled}),cleanup(){slots.forEach(slot=>slot?.cleanup?.());}};
}
test('listening/speaking face viewer and state changes preserve one gaze/blink animation loop',()=>{
  const h=harness();h.cursor({x:1600,y:600});h.advance(8);
  assert.ok(h.pupils().some(value=>!value.includes('translate(0 0)')));
  for(const mood of ['speaking','listening','capturing']){
    h.render(mood);h.cursor({x:1600,y:600});h.advance(20);
    assert.equal(h.pupils().length,2);
    for(const value of h.pupils()){const values=value.slice(value.indexOf('(')+1,-1).split(' ').map(Number);assert.ok(Math.abs(values[0])<.001&&Math.abs(values[1])<.001,value);}
  }
  assert.deepEqual(h.counts(),{subscriptions:1,cancelled:0});
  h.render('idle');h.cursor({x:1800,y:600});h.advance(8);assert.ok(h.pupils().some(value=>!value.includes('translate(0 0)')));
  h.cleanup();assert.equal(h.counts().cancelled,1);
});
