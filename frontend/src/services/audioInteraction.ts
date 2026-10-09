import { isPlaybackBlockingInput } from './audioPlayback';

// New default intentionally replaces the old, noise-sensitive preference.
const STORAGE_KEY = 'aira.allow-speech-interruption.v2';
let allowInterruption = false;
try { allowInterruption = localStorage.getItem(STORAGE_KEY) === 'true'; } catch { /* Explicit stop phrases are the default. */ }
const listeners = new Set<() => void>();
export const getAllowSpeechInterruption = (): boolean => allowInterruption;
export function subscribeSpeechInterruption(listener: () => void): () => void {
    listeners.add(listener);
    return () => { listeners.delete(listener); };
}
export function setAllowSpeechInterruption(value: boolean): void {
    allowInterruption = value;
    try { localStorage.setItem(STORAGE_KEY, String(value)); } catch { /* Current session still uses the choice. */ }
    for (const listener of listeners) listener();
}
/** By default, do not send AIRA's speaker output back as a new user utterance. */
export function canSendMicrophoneAudio(): boolean {
    return allowInterruption || !isPlaybackBlockingInput();
}
