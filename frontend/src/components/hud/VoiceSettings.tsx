import { useEffect, useRef, useState } from 'react';
import { settingsApi } from '../../services/settingsApi';
import { AudioPlayback } from '../../services/audioPlayback';
import { useVoiceStore } from '../../stores/voiceStore';
import { useCaptureStore } from '../../stores/captureStore';
import { getAudioOutputState } from '../../services/audioOutput';

export function VoiceSettings() {
  const [voices, setVoices] = useState<Array<{ name: string; description: string }>>([]);
  const [chosen, setChosen] = useState('Aoede');
  const [saved, setSaved] = useState('Aoede');
  const [saving, setSaving] = useState(false);
  const [previewing, setPreviewing] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const voiceStatus = useVoiceStore(s => s.status);
  const captureStatus = useCaptureStore(s => s.status);
  const busy = !['disconnected', 'error'].includes(voiceStatus) || captureStatus === 'capturing';
  const player = useRef<AudioPlayback | null>(null);
  const request = useRef<AbortController | null>(null);
  const generation = useRef(0);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const mounted = useRef(true);

  const stopPreview = () => {
    ++generation.current;
    request.current?.abort(); request.current = null;
    player.current?.stop(); player.current = null;
    if (timer.current) clearTimeout(timer.current);
    timer.current = null;
    setPreviewing(false);
  };
  useEffect(() => {
    mounted.current = true;
    settingsApi.getSettings().then(s => {
      if (!mounted.current) return;
      setVoices(s.voices); setChosen(s.voiceName); setSaved(s.voiceName);
    }).catch(err => { if (mounted.current) setError(err instanceof Error ? err.message : 'Could not load voices.'); });
    return () => { mounted.current = false; ++generation.current; request.current?.abort(); player.current?.stop(); if (timer.current) clearTimeout(timer.current); };
  }, []);
  useEffect(() => { if (busy) stopPreview(); }, [busy]);

  const preview = async () => {
    if (busy) return;
    stopPreview();
    const current = generation.current;
    const controller = new AbortController(); request.current = controller;
    const audio = new AudioPlayback(); player.current = audio;
    setPreviewing(true); setError(''); setMessage(`Loading ${chosen}…`);
    try {
      // Unlock output on the click; never request microphone permission.
      await audio.activate();
      if (current !== generation.current || !mounted.current) return;
      const sample = await settingsApi.previewVoice(chosen, controller.signal);
      if (current !== generation.current || !mounted.current) return;
      if (sample.sampleRate !== 24000) throw new Error('Unsupported preview audio format.');
      await audio.enqueue(sample.audio);
      if (current !== generation.current || !mounted.current) return;
      if (!audio.isPlaying) throw new Error(getAudioOutputState().error || 'Preview was interrupted. Try again.');
      setMessage(`${sample.voiceName}: “${sample.text}” · ${sample.cached ? 'local cached preview, no new Gemini call' : 'generated with Gemini and cached on E'}.`);
      timer.current = setTimeout(() => { if (current === generation.current) { audio.stop(); player.current = null; setPreviewing(false); } }, sample.durationSeconds * 1000 + 250);
    } catch (err) {
      if (current !== generation.current || !mounted.current) return;
      audio.stop(); player.current = null; setPreviewing(false); setMessage('');
      setError(err instanceof Error ? err.message : 'Could not preview this voice.');
    }
  };
  const save = async () => {
    stopPreview(); setSaving(true); setError('');
    const name = chosen;
    try {
      await settingsApi.saveVoice(name);
      if (mounted.current) { setSaved(name); setMessage(`Saved ${name}. AIRA uses it for the next conversation, capture or narration.`); }
    } catch (err) { if (mounted.current) setError(err instanceof Error ? err.message : 'Could not save voice.'); }
    finally { if (mounted.current) setSaving(false); }
  };
  return <section className="flex flex-col gap-2" aria-label="AIRA voice settings">
    <h3 className="text-sm font-semibold">AIRA voice</h3>
    <p className="text-xs text-text-muted">Current voice: {saved}. Choose and preview any voice, then save your favourite.</p>
    <select aria-label="AIRA voice" className="w-full px-3 py-2 rounded-xl border border-border bg-glass text-text-primary text-sm" value={chosen} disabled={!voices.length || saving} onChange={event => { stopPreview(); setChosen(event.target.value); setMessage(''); setError(''); }}>
      {voices.map(voice => <option key={voice.name} value={voice.name}>{voice.name} · {voice.description}</option>)}
    </select>
    <div className="flex gap-2">
      <button className="flex-1 px-3 py-2 rounded-xl border border-border text-sm disabled:opacity-40" disabled={busy || !voices.length || saving} onClick={() => previewing ? (stopPreview(), setMessage('Preview stopped.')) : void preview()}>{previewing ? 'Stop preview' : '▶ Preview “Hi Charan”'}</button>
      <button className="px-3 py-2 rounded-xl bg-primary text-white text-sm disabled:opacity-40" disabled={saving || !voices.length || chosen === saved} onClick={() => void save()}>{saving ? 'Saving…' : 'Save voice'}</button>
    </div>
    <p className="text-xs text-text-muted">Stop conversation/capture before previewing. The first preview of each voice uses Gemini quota or credits; replays use its local cache on E. Changing the selection alone does not change AIRA’s voice.</p>
    {message && <p role="status" className="text-xs text-text-muted">{message}</p>}
    {error && <p role="alert" className="text-xs text-error">{error}</p>}
  </section>;
}
