/**
 * useVoice — persistent streaming voice session via Gemini Live API.
 *
 * Lifecycle: disconnected → connecting → connected (always streaming) → disconnected
 *
 * Explicit connect acquires the device, then opens Live and streams PCM.
 * Stop, replacement, disconnect and sign-out release input/playback.
 * The desktop overlay observes this owner; it never opens another session.
 *
 * The hook exposes a mute/unmute toggle (pauses sending chunks, keeps session open).
 */

import { useCallback, useRef } from 'react';
import { AudioStreamer } from '../services/audioCapture';
import { useVoiceStore } from '../stores/voiceStore';
import { usePalaceStore } from '../stores/palaceStore';
import { useCaptureStore } from '../stores/captureStore';
import { useWS } from './useWS';
import { stopCapture } from './useCapture';
import { stopAllPlayback } from '../services/audioPlayback';
import { canSendMicrophoneAudio, getAllowSpeechInterruption } from '../services/audioInteraction';
import { useCompanionStore } from '../stores/companionStore';

// ── Module-level singletons ──────────────────────────────────────────────────
// Shared across all hook instances so connect/disconnect work regardless of
// which component calls them.
let _streamer: AudioStreamer | null = null;
let _started = false;
let _muted = false;
/** True while the proactive greeting turn is in progress — audio is held back
 *  so the VAD does not interrupt AIRA mid-sentence. Cleared by the first
 *  live_turn_complete or by a safety timeout. */
let _holdAudio = false;
let _holdAudioTimer: ReturnType<typeof setTimeout> | null = null;
let _healthTimer: ReturnType<typeof setInterval> | null = null;
let _recoveryTimer: ReturnType<typeof setTimeout> | null = null;
let _restart: (() => Promise<void>) | null = null;
let _recoveries = 0;

/** Called by useWS when the first live_turn_complete fires after connect. */
export function releaseAudioHold(): void {
    _holdAudio = false;
    if (_holdAudioTimer !== null) {
        clearTimeout(_holdAudioTimer);
        _holdAudioTimer = null;
    }
}

/** Stop the voice session from outside the hook (e.g. when the server initiates close). */
export function stopVoiceSession(): void {
    if (_recoveryTimer) clearTimeout(_recoveryTimer);
    _recoveryTimer = null;
    _restart = null;
    stopAllPlayback();
    const wasStarted = _started;
    releaseAudioHold();
    if(_healthTimer) clearInterval(_healthTimer);
    _healthTimer=null;
    _streamer?.stop();
    _streamer = null;
    const voiceStore = useVoiceStore.getState();
    voiceStore.setStatus('disconnected');
    voiceStore.setMuted(false);
    voiceStore.setSessionId(null);
    voiceStore.setToolActivity(null);
    useCompanionStore.getState().update({ thinking: false });
    if (wasStarted) voiceStore.addToolEvent('Session Ended', 'session_end');
    _started = false;
    _muted = false;
}

/** Recover one broken transport per explicit activation; never bypass limits. */
export function handleVoiceSessionEnded(reason: string, label: string): void {
    const restart = _restart;
    const transient = ['connection_error', 'audio_send_timeout', 'start_timeout'].includes(reason);
    const retry = transient && _started && restart && _recoveries < 1;
    stopVoiceSession();
    if (retry) {
        _recoveries++;
        useVoiceStore.getState().setStatus('connecting');
        useCompanionStore.getState().update({ thinking: false, notice: 'Reconnecting voice once… Desktop tasks stay available.' });
        _recoveryTimer = setTimeout(() => { _recoveryTimer = null; void restart(); }, 1500);
    } else {
        useVoiceStore.getState().addToolEvent(label, 'session_end');
        useCompanionStore.getState().update({ thinking: false, notice: label });
        if (transient) useVoiceStore.getState().setError(label);
    }
}

export function useVoice() {
    const ws = useWS();
    const wsRef = useRef(ws);
    wsRef.current = ws;

    const store = useVoiceStore();

    /** Start the live session and audio streaming.
     *  Pass focusedArtifactId to pre-load a specific artifact into AIRA's context. */
    const connect = useCallback(async (focusedArtifactId: string | null = null, recovering = false) => {
        if (_started) return;
        if (_recoveryTimer) clearTimeout(_recoveryTimer);
        _recoveryTimer = null;
        if (!recovering) _recoveries = 0;
        _restart = () => connect(focusedArtifactId, true);

        // Ensure mutual exclusivity
        const previousCapture = useCaptureStore.getState();
        if (previousCapture.sessionId && previousCapture.status === 'capturing') {
            wsRef.current.sendCaptureEnd(previousCapture.sessionId, true);
        }
        stopCapture();

        _started = true;

        const voiceStore = useVoiceStore.getState();
        voiceStore.setError(null);
        voiceStore.setStatus('connecting');
        voiceStore.setMuted(false);
        voiceStore.setShowPanel(true);
        const sessionId=crypto.randomUUID();
        voiceStore.setSessionId(sessionId);

        // Send live_session_start with the room the user is currently in
        const currentRoomId = usePalaceStore.getState().currentRoomId;

        // Start audio capture
        const streamer = new AudioStreamer();
        _streamer = streamer;

        // Hold audio until the greeting turn completes (avoids VAD interrupting AIRA).
        // Safety valve: release unconditionally after 10 seconds.
        _holdAudio = true;
        _holdAudioTimer = setTimeout(releaseAudioHold, 10_000);

        try {
            await window.airaDesktop?.prepareAudio();
            if (!_started || _streamer !== streamer) return;
            await streamer.start((base64Pcm) => {
                if(_started && _streamer===streamer) {
                    const ready=['connected','responding'].includes(useVoiceStore.getState().status);
                    const sending=ready && !_muted && (!_holdAudio || getAllowSpeechInterruption()) && canSendMicrophoneAudio();
                    useVoiceStore.getState().markMicChunk(sending);
                    if(sending) wsRef.current.sendAudioChunk(base64Pcm,sessionId);
                }
            }, undefined, (err) => {
                if (_streamer === streamer) {
                    wsRef.current.sendLiveSessionEnd();
                    stopVoiceSession();
                    voiceStore.setError(err.message);
                }
            });
            if (_started && _streamer === streamer && streamer.isStreaming) {
                await wsRef.current.waitUntilReady();
                if (!_started || _streamer !== streamer) { streamer.stop(); return; }
                releaseAudioHold();
                _holdAudio = true;
                _holdAudioTimer = setTimeout(releaseAudioHold, 10_000);
                wsRef.current.sendLiveSessionStart({ currentRoomId, focusedArtifactId, allowSpeechInterruption:getAllowSpeechInterruption() },sessionId);
                _healthTimer=setInterval(() => {
                    const current=useVoiceStore.getState();
                    if(_started && _streamer===streamer && current.sessionId===sessionId && ['connected','responding'].includes(current.status)) wsRef.current.checkLiveSession(sessionId);
                },3000);
            } else {
                streamer.stop();
            }
        } catch (err) {
            streamer.stop();
            if (_streamer === streamer) {
                wsRef.current.sendLiveSessionEnd();
                stopVoiceSession();
                voiceStore.setError(err instanceof Error ? err.message : 'Microphone access denied');
            }
        }
    }, []);

    /** Close the live session and stop streaming. */
    const disconnect = useCallback(() => {
        stopAllPlayback();
        if (_started) wsRef.current.sendLiveSessionEnd();
        stopVoiceSession();
    }, []);

    /** Toggle mute — pauses sending audio chunks but keeps session alive. */
    const toggleMute = useCallback(() => {
        const voiceStore = useVoiceStore.getState();
        const newMuted = !voiceStore.muted;
        _muted = newMuted;
        voiceStore.setMuted(newMuted);
    }, []);



    return {
        status: store.status,
        muted: store.muted,
        transcript: store.transcript,
        diagrams: store.diagrams,
        currentNarration: store.currentNarration,
        error: store.error,
        toggleMute,

        connect,
        disconnect,
    };
}
