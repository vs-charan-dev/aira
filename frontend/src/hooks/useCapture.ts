import { useCallback } from 'react';
import { v4 as uuidv4 } from 'uuid';
import { MediaCapture } from '../services/mediaCapture';
import { AudioStreamer } from '../services/audioCapture';
import { useCaptureStore } from '../stores/captureStore';
import { useWS } from './useWS';
import type { RoomSuggestionChoice } from '../stores/captureStore';

import { stopVoiceSession } from './useVoice';
import { stopAllPlayback } from '../services/audioPlayback';
import { canSendMicrophoneAudio, getAllowSpeechInterruption } from '../services/audioInteraction';
import { useCompanionStore } from '../stores/companionStore';

let _captureInstance: MediaCapture | null = null;
let _audioStreamer: AudioStreamer | null = null;

/** Standalone stop function to be called from other hooks to ensure exclusivity. */
export function stopCapture() {
  const { sessionId, status } = useCaptureStore.getState();
  stopAllPlayback();
  _captureInstance?.stop();
  _captureInstance = null;

  _audioStreamer?.stop();
  _audioStreamer = null;

  if (sessionId && status === 'capturing') useCaptureStore.getState().setStatus('processing');
  useCaptureStore.getState().setReady(false);
  useCaptureStore.getState().setActiveStream(null);
  useCompanionStore.getState().update({ thinking: false });
}

export function useCapture() {
  const ws = useWS();
  const store = useCaptureStore();

  const startCapture = useCallback(
    async (source: 'webcam' | 'screen_share' | 'voice' = 'webcam') => {
      const previous = useCaptureStore.getState();
      if (previous.status === 'capturing' && previous.sourceType === source) return;
      if (previous.status === 'capturing' && previous.sessionId) ws.sendCaptureEnd(previous.sessionId, true);
      stopCapture();

      // Ensure mutual exclusivity
      ws.sendLiveSessionEnd();
      stopVoiceSession();

      const sessionId = uuidv4();
      store.reset();
      store.setSessionId(sessionId);
      store.setSourceType(source);
      store.setStatus('capturing');

      const capture = new MediaCapture();
      const streamer = new AudioStreamer();
      _captureInstance = capture;
      _audioStreamer = streamer;
      const active = () => useCaptureStore.getState().sessionId === sessionId && useCaptureStore.getState().status === 'capturing';
      const failed = (err: Error) => {
        const wasActive = active();
        capture.stop(); streamer.stop();
        ws.sendCaptureEnd(sessionId);
        if (wasActive) {
          store.setActiveStream(null);
          store.setError(err.message);
          store.setStatus('error');
        }
      };
      try {
        await window.airaDesktop?.prepareAudio();
        if (!active()) return;
        if (source !== 'voice') {
          await capture.start({ source,
            onFrame: (data, index, timestamp) => {
              if (active()) ws.sendVideoFrame(sessionId, index, data, timestamp);
            }, onError: failed,
          });
        }
        if (!active()) { capture.stop(); return; }
        store.setActiveStream(capture.getStream());
        await streamer.start((base64Pcm) => {
          if (active() && useCaptureStore.getState().ready && canSendMicrophoneAudio()) ws.sendCaptureVoiceChunk(sessionId, base64Pcm);
        }, capture.getStream() ?? undefined, failed);
        if (!active()) { capture.stop(); streamer.stop(); return; }
        await ws.waitUntilReady();
        if (!active()) { capture.stop(); streamer.stop(); return; }
        ws.sendCaptureStart(sessionId, source, useCaptureStore.getState().capturePace, getAllowSpeechInterruption());
      } catch (err) {
        failed(err instanceof Error ? err : new Error('Capture device access failed.'));
      }
    },
    [ws, store],
  );

  const handleStop = useCallback(() => {
    const { sessionId } = useCaptureStore.getState();
    if (!sessionId) return;

    const ready = useCaptureStore.getState().ready;
    stopCapture();
    ws.sendCaptureEnd(sessionId);
    if (!ready) store.setStatus('complete');
  }, [ws, store]);

  /** Returns a promise that resolves when the user responds to the modal. */
  const waitForRoomSuggestionResponse = useCallback(
    (): Promise<RoomSuggestionChoice> =>
      new Promise((resolve) => {
        const { roomSuggestion } = useCaptureStore.getState();
        if (!roomSuggestion) {
          resolve({ action: 'accept' });
          return;
        }
        store.setRoomSuggestion(roomSuggestion, resolve);
      }),
    [store],
  );

  return { startCapture, stopCapture: handleStop, waitForRoomSuggestionResponse };
}
