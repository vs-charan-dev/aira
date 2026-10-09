/** Output routing only: never acquires a microphone or starts Gemini. */
export interface AudioOutputState {
    deviceId: string;
    devices: { deviceId: string; label: string; groupId: string }[];
    error: string;
    notice: string;
}
let state: AudioOutputState = { deviceId: '', devices: [], error: '', notice: '' };
const listeners = new Set<() => void>();
const routingListeners = new Set<() => void>();
let watchers = 0;
let refreshGeneration = 0;
let signature: string | null = null;
function update(value: Partial<AudioOutputState>): void {
    state = { ...state, ...value };
    for (const listener of listeners) listener();
}
export const getAudioOutputState = (): AudioOutputState => state;
export function subscribeAudioOutput(listener: () => void): () => void {
    listeners.add(listener);
    return () => { listeners.delete(listener); };
}
export function onAudioRoutingChange(listener: () => void): () => void {
    routingListeners.add(listener);
    return () => { routingListeners.delete(listener); };
}
export function reportAudioOutputError(error: unknown): void {
    update({ error: `Could not play AIRA audio: ${error instanceof Error ? error.message : String(error)}. Check the speaker selection and Windows volume, then reset audio.` });
}
export function resetAudioOutput(): void {
    for (const listener of [...routingListeners]) listener();
    update({ error: '', notice: 'Audio output reset. Ask AIRA to repeat any interrupted reply.' });
}
export function selectAudioOutput(deviceId: string): void {
    if (deviceId && !state.devices.some(device => device.deviceId === deviceId)) throw new Error('Speaker is no longer available. Refresh the list.');
    update({ deviceId });
    resetAudioOutput();
}
export async function refreshAudioOutputs(deviceChanged = false): Promise<void> {
    const generation = ++refreshGeneration;
    if (typeof navigator === 'undefined' || !navigator.mediaDevices?.enumerateDevices) return;
    try {
        const all = await navigator.mediaDevices.enumerateDevices();
        if (generation !== refreshGeneration) return;
        const devices = all.filter(device => device.kind === 'audiooutput').map(({ deviceId, label, groupId }) => ({ deviceId, label, groupId }));
        const nextSignature = JSON.stringify(devices.map(device => [device.deviceId, device.label, device.groupId]).sort());
        const missing = state.deviceId !== '' && !devices.some(device => device.deviceId === state.deviceId);
        const changed = deviceChanged && (signature === null || signature !== nextSignature);
        signature = nextSignature;
        update({ devices, ...(missing ? { deviceId: '' } : {}) });
        if (changed || missing) {
            resetAudioOutput();
            update({ notice: missing ? 'Selected speaker disconnected. Using Windows default output. Ask AIRA to repeat.' : 'Audio devices changed. Output refreshed; ask AIRA to repeat any interrupted reply.' });
        }
    } catch (error) {
        if (generation === refreshGeneration) update({ error: `Could not list speakers: ${error instanceof Error ? error.message : String(error)}` });
    }
}
const deviceChanged = () => { void refreshAudioOutputs(true); };
export function watchAudioOutputs(): () => void {
    if (watchers++ === 0) {
        navigator.mediaDevices?.addEventListener('devicechange', deviceChanged);
        void refreshAudioOutputs();
    }
    return () => {
        if (--watchers === 0) {
            navigator.mediaDevices?.removeEventListener('devicechange', deviceChanged);
            refreshGeneration++;
            signature = null;
        }
    };
}
