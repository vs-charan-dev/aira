import { useEffect, useRef, useState } from 'react';
import { useVoice } from './useVoice';
import { useCapture } from './useCapture';
import { useWS } from './useWS';
import { useVoiceStore } from '../stores/voiceStore';
import { useCaptureStore } from '../stores/captureStore';
import { useCompanionStore } from '../stores/companionStore';
import { getPlaybackEnergy } from '../services/playbackMeter';
import { isPlaybackActive } from '../services/audioPlayback';
import type { CompanionCommand, CompanionState, Mode } from '../services/desktop';
import { wireDesktopActions } from '../services/desktopActions';
import { wireScreenViews } from '../services/screenView';
import { useTaskState } from '../stores/taskState';

/** The palace is the single voice owner. The native overlay only observes. */
export function useCompanion() {
  const voice = useVoice(), capture = useCapture(), ws = useWS();
  const update = useCompanionStore(s => s.update);
  const actionRef = useRef<(value: CompanionCommand) => Promise<void>>(async () => {});
  const seen = useRef(new Set<string>());
  const [state, setState] = useState<CompanionState>({ mood: 'idle', label: 'Ready', busy: false, energy: 0, hiddenUntil: 0 });
  actionRef.current = async command => {
    if (command.action === 'hide') { update({ hiddenUntil: Date.now() + Math.min(3600, Math.max(1, command.seconds)) * 1000 + 650 }); return; }
    if (command.action === 'show') { update({ hiddenUntil: 0 }); return; }
    update({ hiddenUntil: 0, pendingMode: null, notice: '' });
    const currentCapture = useCaptureStore.getState();
    if (command.action === 'activate' && (currentCapture.status === 'capturing' || !['disconnected','error'].includes(useVoiceStore.getState().status))) return;
    const mode = command.action === 'activate' ? 'recall' : command.mode;
    if (mode === 'stop') { ws.stopAllTasks(); void window.airaDesktop?.stopAction(); voice.disconnect(); capture.stopCapture(); update({ thinking: false, notice: 'Conversation, screen and jobs stopped. Enabled local wake listening resumes.' }); return; }
    if (mode === 'recall') {
      await voice.connect();
      return;
    }
    const source = { capture_voice: 'voice', capture_screen: 'screen_share', capture_camera: 'webcam' }[mode] as 'voice' | 'screen_share' | 'webcam';
    if (currentCapture.status === 'capturing' && currentCapture.sourceType === source) return;
    // Browsers require a real click for display capture. Keep the request visibly pending.
    if (source === 'screen_share' && !window.airaDesktop) {
      update({ pendingMode: mode, notice: 'AIRA needs you to choose the screen to share.' });
      return;
    }
    await capture.startCapture(source);
  };
  useEffect(() => {
    const unsubscribeScreen = wireScreenViews(ws, message => message.source === 'capture'
      ? message.sessionId === useCaptureStore.getState().sessionId && useCaptureStore.getState().status === 'capturing'
      : !['disconnected','error'].includes(useVoiceStore.getState().status));
    const unsubscribeActions = wireDesktopActions(ws, message => message.source === 'capture'
      ? message.sessionId === useCaptureStore.getState().sessionId && useCaptureStore.getState().status === 'capturing'
      : !['disconnected','error'].includes(useVoiceStore.getState().status));
    const unsubscribeCommand = ws.on('companion_command', message => {
      if (seen.current.has(message.requestId)) return;
      if (message.source === 'capture' && (message.sessionId !== useCaptureStore.getState().sessionId || useCaptureStore.getState().status !== 'capturing')) return;
      if (message.source === 'recall' && ['disconnected','error'].includes(useVoiceStore.getState().status)) return;
      seen.current.add(message.requestId);
      if (seen.current.size > 100) seen.current.delete(seen.current.values().next().value!);
      void actionRef.current(message);
    });
    const desktop = window.airaDesktop;
    const unsubscribeDesktop = desktop?.onCommand(value => { void actionRef.current(value); });
    desktop?.ready();
    let last = '';
    const timer = setInterval(() => {
      const v = useVoiceStore.getState(), c = useCaptureStore.getState(), companion = useCompanionStore.getState();
      const jobs = useTaskState.getState();
      const energy = getPlaybackEnergy();
      const speaking = isPlaybackActive();
      const voiceActive = !['disconnected','error'].includes(v.status), captureActive = c.status === 'capturing';
      let mood: CompanionState['mood'] = 'idle', label = 'Ready';
      if (speaking) { mood = 'speaking'; label = 'Speaking'; }
      else if (voiceActive || captureActive) {
        if (v.status === 'connecting' || (captureActive && !c.ready)) { mood = 'thinking'; label = 'Starting · waiting for permission/connection'; }
        else if (companion.thinking || v.toolActivity) { mood = 'thinking'; label = 'Working'; }
        else if (captureActive) { mood = 'capturing'; label = c.sourceType === 'screen_share' ? 'Screen capture on' : c.sourceType === 'webcam' ? 'Camera capture on' : 'Memory capture on'; }
        else if (v.muted) { mood = 'idle'; label = 'Microphone muted · session open'; }
        else if(Date.now()-v.lastMicChunkAt>3000) { mood='error';label='Microphone stream paused · reactivate AIRA'; }
        else if(Date.now()-v.lastMicSentAt>3000) { mood='idle';label='Microphone input paused'; }
        else { mood = 'listening'; label = jobs.active ? 'Listening · desktop commands queue' : 'Listening'; }
      } else if (c.status === 'processing') { mood = 'thinking'; label = 'Saving captured memories'; }
      else if (v.error || c.status === 'error') { mood = 'error'; label = v.error || c.error || 'Could not start'; }
      else if (jobs.active) { mood = 'thinking'; label = jobs.label; }
      if (companion.pendingMode) label = 'Choose a screen to share';
      const next = { mood, label, busy: voiceActive || captureActive || speaking, energy, hiddenUntil: companion.hiddenUntil };
      desktop?.publish(next);
      const key = JSON.stringify({ ...next, energy: 0 });
      if (last !== key) { last = key; setState(next); }
    }, 80);
    return () => { clearInterval(timer); unsubscribeCommand(); unsubscribeDesktop?.(); unsubscribeActions(); unsubscribeScreen(); };
  }, [ws]);
  const approveScreen = async () => {
    update({ pendingMode: null, notice: '' });
    await capture.startCapture('screen_share');
  };
  return { state, approveScreen, cancelScreen: () => update({ pendingMode: null, notice: 'Screen request cancelled.' }), requestMode: (mode: Mode) => actionRef.current({ action: 'switch_mode', mode }) };
}
