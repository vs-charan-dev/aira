import { useEffect, useRef } from 'react';
import { useWS } from './useWS';
import { useCaptureStore } from '../stores/captureStore';
import { AudioPlayback } from '../services/audioPlayback';
import { stopCapture } from './useCapture';
import { useCompanionStore } from '../stores/companionStore';
import type { CaptureAckMessage, CaptureAudioMessage, CaptureSessionStartedMessage, CaptureSessionEndedMessage, CaptureTextMessage, CaptureToolEventMessage, CaptureUserTextMessage } from '../services/websocket';

/**
 * Hook to handle capture session WebSocket messages.
 * Listens for capture-related messages and updates the capture store.
 */
export function useCaptureWS() {
  const ws = useWS();
  const playbackRef = useRef<AudioPlayback | null>(null);
  // Buffered capture tool event — flushed after AIRA's first text arrives so
  // the spoken message always appears before the "Captured: ..." badge.
  const pendingCaptureEventRef = useRef<{ text: string; toolName: string } | null>(null);
  const {
    addToolEvent,
    appendAIRAText,
    appendUserText,
    setShowPanel,
    setStatus,
    clearMessages,
  } = useCaptureStore();

  useEffect(() => {
    const unsubscribers: Array<() => void> = [];

    // Own AudioPlayback instance for capture — decoupled from the recall session's playback
    playbackRef.current = new AudioPlayback();

    // Session started
    unsubscribers.push(
      ws.on('capture_session_started', (msg: CaptureSessionStartedMessage) => {
        if (msg.sessionId !== useCaptureStore.getState().sessionId) return;
        if (useCaptureStore.getState().status !== 'capturing') return;
        useCaptureStore.getState().setReady(true);
        setStatus('capturing');
        setShowPanel(true);
        clearMessages();
        console.log('[useCaptureWS] Capture session started:', msg.sessionId);
      })
    );

    // Session ended — keep panel open so the user can review what was captured
    unsubscribers.push(
      ws.on('capture_session_ended', (msg: CaptureSessionEndedMessage) => {
        if (msg.sessionId !== useCaptureStore.getState().sessionId) return;
        stopCapture();
        setStatus('complete');
        console.log('[useCaptureWS] Capture session ended:', msg.sessionId);
      })
    );

    // Capture acknowledgment (concept extracted).
    // Buffer the tool badge — it will be flushed after AIRA's first spoken text
    // so the message always appears before the "Captured: ..." badge.
    unsubscribers.push(
      ws.on('capture_ack', (msg: CaptureAckMessage) => {
        if (msg.sessionId !== useCaptureStore.getState().sessionId) return;
        const { extraction, voiceResponse } = msg;
        pendingCaptureEventRef.current = {
          text: `Captured: ${extraction.concept} (${Math.round(extraction.confidence * 100)}%)`,
          toolName: 'capture_concept',
        };
        if (voiceResponse) {
          appendAIRAText(voiceResponse);
        }
        console.log('[useCaptureWS] Concept extracted:', extraction.concept);
      })
    );

    // Text transcription from AIRA — flush any buffered capture badge first so
    // AIRA's message always precedes the "Captured: ..." tool event.
    unsubscribers.push(
      ws.on('capture_text', (msg: CaptureTextMessage) => {
        appendAIRAText(msg.text);
        if (pendingCaptureEventRef.current) {
          addToolEvent(pendingCaptureEventRef.current.text, pendingCaptureEventRef.current.toolName);
          pendingCaptureEventRef.current = null;
        }
      })
    );

    // Text transcription from User — shown in ResponsePanel
    unsubscribers.push(
      ws.on('capture_user_text', (msg: CaptureUserTextMessage) => {
        if (useCaptureStore.getState().status !== 'capturing') return;
        useCompanionStore.getState().update({ thinking: true });
        appendUserText(msg.text);
      })
    );

    // Audio from AIRA — played via a dedicated AudioPlayback instance for capture
    unsubscribers.push(
      ws.on('capture_audio', (msg: CaptureAudioMessage) => {
        if (useCaptureStore.getState().status !== 'capturing') return;
        useCompanionStore.getState().update({ thinking: false });
        if (playbackRef.current) void playbackRef.current.enqueue(msg.data);
      })
    );

    unsubscribers.push(ws.on('capture_interrupted', msg => {
      if (msg.sessionId !== useCaptureStore.getState().sessionId) return;
      playbackRef.current?.stop();
      useCompanionStore.getState().update({ thinking: false });
    }));
    unsubscribers.push(ws.on('capture_turn_complete', msg => {
      if (msg.sessionId === useCaptureStore.getState().sessionId) useCompanionStore.getState().update({ thinking: false });
    }));

    // Tool events — badge in the left panel for every agent action
    unsubscribers.push(
      ws.on('capture_tool_event', (msg: CaptureToolEventMessage) => {
        addToolEvent(msg.label, msg.tool);
      })
    );

    return () => {
      unsubscribers.forEach(unsub => unsub());
      playbackRef.current?.stop();
      playbackRef.current = null;
    };
  }, [ws, addToolEvent, appendAIRAText, setShowPanel, setStatus, clearMessages]);
}
