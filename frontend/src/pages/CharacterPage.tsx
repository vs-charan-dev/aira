import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, ArrowUpRight, AudioLines, Eye, RotateCcw, Sparkles, Volume2 } from 'lucide-react';
import { AiraCharacter, type CharacterMood } from '../components/companion/AiraCharacter';
import { AudioPlayback } from '../services/audioPlayback';
import './characterPage.css';

export function CharacterPage() {
  const [mood, setMood] = useState<CharacterMood>('idle');
  const [blink, setBlink] = useState(0);
  const [hidden, setHidden] = useState(false);
  const [remaining, setRemaining] = useState(0);
  const [demo, setDemo] = useState<'idle' | 'loading' | 'playing'>('idle');
  const [error, setError] = useState('');
  const player = useRef<AudioPlayback | null>(null);
  const until = useRef(0);
  const demoGeneration = useRef(0);
  const request = useRef<AbortController | null>(null);
  const speechTimer = useRef<ReturnType<typeof setTimeout>>();
  const hideTimer = useRef<ReturnType<typeof setTimeout>>();
  const restore = () => {
    clearTimeout(hideTimer.current);
    until.current = 0; setHidden(false); setRemaining(0);
  };
  useEffect(() => {
    const refresh = () => {
      if (!until.current) return;
      const left = Math.max(0, Math.ceil((until.current - Date.now()) / 1000));
      setRemaining(left);
      if (!left) { until.current = 0; setHidden(false); }
    };
    const timer = setInterval(refresh, 200);
    document.addEventListener('visibilitychange', refresh);
    return () => {
      clearInterval(timer); clearTimeout(hideTimer.current); clearTimeout(speechTimer.current);
      document.removeEventListener('visibilitychange', refresh);
      demoGeneration.current += 1; request.current?.abort(); player.current?.stop();
    };
  }, []);
  const disappear = () => {
    clearTimeout(hideTimer.current);
    setHidden(true); setRemaining(10);
    // The ten-second hidden interval starts after the downward animation.
    until.current = Date.now() + 10_650;
    hideTimer.current = setTimeout(restore, 10_650);
  };
  const stopDemo = () => {
    demoGeneration.current += 1; request.current?.abort(); player.current?.stop();
    clearTimeout(speechTimer.current); setDemo('idle');
  };
  const playDemo = async () => {
    if (demo !== 'idle') { stopDemo(); return; }
    setError(''); setDemo('loading');
    const generation = ++demoGeneration.current;
    const controller = new AbortController(); request.current = controller;
    const audio = new AudioPlayback(); player.current = audio;
    try {
      await audio.activate();
      if (generation !== demoGeneration.current) return;
      const response = await fetch('/character/hello.pcm', { signal: controller.signal });
      if (!response.ok) throw new Error('The local voice sample could not load.');
      const bytes = new Uint8Array(await response.arrayBuffer());
      if (generation !== demoGeneration.current) return;
      let binary = '';
      for (let start = 0; start < bytes.length; start += 8192) binary += String.fromCharCode(...bytes.subarray(start, start + 8192));
      await audio.enqueue(btoa(binary));
      if (generation !== demoGeneration.current) { audio.stop(); return; }
      setDemo('playing');
      const finish = () => {
        if (generation !== demoGeneration.current) return;
        if (audio.isPlaying) { speechTimer.current = setTimeout(finish, 100); return; }
        audio.stop(); setDemo('idle');
      };
      speechTimer.current = setTimeout(finish, 100);
    } catch (err) {
      if (generation !== demoGeneration.current) return;
      audio.stop();
      setDemo('idle'); setError(err instanceof Error ? err.message : 'Voice preview failed.');
    }
  };
  return (
    <div className="character-studio">
      <header className="character-header">
        <Link to="/palace" className="character-brand"><span className="brand-mark">a</span><strong>AIRA</strong><span className="brand-divider" /><span>Companion studio</span></Link>
        <Link to="/palace" className="palace-link">Memory Palace <ArrowUpRight size={15} /></Link>
      </header>
      <main className="character-main">
        <div className="character-intro"><span className="character-eyebrow"><span /> MEET YOUR COMPANION</span><h1>A little face.<br /><span>A familiar presence.</span></h1><p>Curious eyes. A voice you know. AIRA is taking shape.</p></div>
        <div className="character-workbench">
          <section className="character-stage" aria-label="Interactive character preview">
            <div className="stage-heading"><span className="stage-status"><span /> LOCAL PREVIEW</span><span>Move your cursor. I’m watching.</span></div>
            <div className="stage-greeting" aria-live="polite">{hidden ? 'I’ll be right back.' : demo === 'playing' ? 'Hi, I’m AIRA.' : mood === 'thinking' ? 'Let me think…' : mood === 'listening' ? 'You have my attention.' : 'Oh, hello there.'}</div>
            <div className="character-dock">
              <div className={`character-reveal ${hidden ? 'character-reveal--hidden' : ''}`} aria-hidden={hidden}><AiraCharacter mood={demo === 'playing' ? 'speaking' : mood} blinkSignal={blink} /></div>
            </div>
            <div className="preview-taskbar" aria-label="Illustrative taskbar"><span className="taskbar-windows"><i /><i /><i /><i /></span><span className="taskbar-search">⌕</span><span className="taskbar-app" /><span className="taskbar-aira">a</span><span className="taskbar-caption">Your desktop, with a little company.</span></div>
          </section>
          <aside className="character-controls">
            <span className="control-eyebrow">AIRA / 01</span><h2>Made to feel alive.</h2><p className="control-description">Try the little things that give AIRA its personality.</p>
            <div className="control-group"><label>PERSONALITY</label><div className="mood-options">{(['idle', 'listening', 'thinking'] as const).map(value => <button key={value} aria-pressed={mood === value} className={mood === value ? 'selected' : ''} onClick={() => setMood(value)}>{value === 'idle' ? 'At rest' : value === 'listening' ? 'Listening' : 'Thinking'}</button>)}</div></div>
            <button className="character-control-row" onClick={() => setBlink(value => value + 1)}><span className="control-icon"><Eye size={19} /></span><span><strong>A little blink</strong><small>It also happens naturally.</small></span><span className="control-arrow">↗</span></button>
            <button className="character-control-row" onClick={playDemo}><span className="control-icon"><Volume2 size={19} /></span><span><strong>{demo === 'loading' ? 'Loading sample…' : demo === 'playing' ? 'Stop voice sample' : 'Hear me say hello'}</strong><small>Offline sample · mouth follows the audio</small></span><span className="control-arrow">{demo === 'playing' ? '■' : '▶'}</span></button>
            <button className="character-control-row" onClick={hidden ? restore : disappear}><span className="control-icon">{hidden ? <RotateCcw size={19} /> : <Sparkles size={19} />}</span><span><strong>{hidden ? 'Bring AIRA back now' : 'Disappear for 10 seconds'}</strong><small>{hidden ? `Returning in ${remaining}s` : 'Slide down. Pop back up.'}</small></span><span className="control-arrow">{hidden ? '↑' : '↓'}</span></button>
            {error && <p role="alert" className="character-error">{error}</p>}
            <div className="character-note"><AudioLines size={17} /><p>The mouth listens to AIRA’s playback, including pauses. This sample uses a local Windows voice, not Gemini.</p></div>
          </aside>
        </div>
        <footer className="character-footer"><span><span className="footer-dot" /> Animated locally. No AI calls for this preview.</span><Link to="/palace"><ArrowLeft size={14} /> Back to the palace</Link></footer>
        <p className="character-scope">Character preview inside AIRA. Windows desktop placement, spoken hide commands, and hand tracking come next.</p>
      </main>
    </div>
  );
}
