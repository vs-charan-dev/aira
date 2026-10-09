import { useEffect, useRef, useState, useSyncExternalStore } from 'react';
import { AudioPlayback } from '../../services/audioPlayback';
import { getAudioOutputState, subscribeAudioOutput, watchAudioOutputs, refreshAudioOutputs, selectAudioOutput, resetAudioOutput } from '../../services/audioOutput';
import { useVoiceStore } from '../../stores/voiceStore';
import { useCaptureStore } from '../../stores/captureStore';
import { getAllowSpeechInterruption, subscribeSpeechInterruption, setAllowSpeechInterruption } from '../../services/audioInteraction';

export function AudioOutputControls() {
    const output = useSyncExternalStore(subscribeAudioOutput, getAudioOutputState);
    const allowInterruption = useSyncExternalStore(subscribeSpeechInterruption, getAllowSpeechInterruption);
    const voiceStatus = useVoiceStore(state => state.status);
    const captureStatus = useCaptureStore(state => state.status);
    const busy = !['disconnected', 'error'].includes(voiceStatus) || captureStatus === 'capturing';
    const [testing, setTesting] = useState(false);
    const [testMessage, setTestMessage] = useState('');
    const player = useRef<AudioPlayback | null>(null);
    const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
    useEffect(() => {
        const release = watchAudioOutputs();
        return () => { release(); player.current?.stop(); player.current = null; if (timer.current) clearTimeout(timer.current); };
    }, []);
    useEffect(() => { if (busy) { player.current?.stop(); player.current = null; if (timer.current) clearTimeout(timer.current); setTesting(false); } }, [busy]);
    const testSound = async () => {
        player.current?.stop();
        if (timer.current) clearTimeout(timer.current);
        const test = new AudioPlayback();
        player.current = test;
        setTesting(true); setTestMessage('');
        try {
            await test.activate();
            if (player.current !== test) return;
            // Two gentle tones through the same PCM playback path as Gemini.
            const samples = new Int16Array(24000 * .6);
            for (let i = 0; i < samples.length; i++) {
                const t = i / 24000, offset = t < .3 ? t : t - .3;
                const envelope = Math.max(0, Math.min(1, offset / .015, (.22 - offset) / .025));
                samples[i] = Math.round(Math.sin(2 * Math.PI * (t < .3 ? 523 : 659) * t) * envelope * 5000);
            }
            let binary = '';
            for (const byte of new Uint8Array(samples.buffer)) binary += String.fromCharCode(byte);
            await test.enqueue(btoa(binary));
            if (player.current !== test) return;
            setTestMessage(test.isPlaying ? 'Two test tones sent. If silent, check Windows output and AIRA volume in Volume mixer.' : 'Test audio was interrupted or could not play. Reset output and try again.');
            timer.current = setTimeout(() => { test.stop(); if (player.current === test) setTesting(false); }, 900);
        } catch (error) {
            test.stop(); if (player.current !== test) return; setTesting(false);
            setTestMessage(error instanceof Error ? error.message : 'Speaker test failed.');
        }
    };
    return <div className="aira-audio-controls">
        <label>Speaker <select aria-label="AIRA speaker" value={output.deviceId} onChange={event => { selectAudioOutput(event.target.value); setTestMessage(''); }}>
            <option value="">Windows default output</option>
            {output.devices.filter(device => !['default', 'communications'].includes(device.deviceId)).map((device, index) => <option key={device.deviceId} value={device.deviceId}>{device.label || `Speaker ${index + 1}`}</option>)}
        </select></label>
        <button onClick={() => void refreshAudioOutputs()}>Refresh speakers</button>
        <button onClick={resetAudioOutput}>Reset audio output</button>
        <button disabled={busy || testing} onClick={() => void testSound()}>Test speaker · no API usage</button>
        <label><input type="checkbox" checked={allowInterruption} onChange={event => setAllowSpeechInterruption(event.target.checked)} /> Allow speech to interrupt replies</label>
        <p>{allowInterruption ? 'Optional speech interruption uses less sensitive detection. Ordinary speech does not cancel desktop jobs. Changes to this setting take full effect after restarting the conversation.' : 'Explicit stop phrases are the default. Say “Hey AIRA, stop doing the work that you are doing” or “Stop AIRA” to stop the conversation and desktop jobs. Short words and background sounds do not interrupt replies. For another instruction, wait until AIRA finishes. Ctrl+Alt+Escape always stops AIRA.'}</p>
        {busy && <p>Stop conversation / capture to run the speaker test.</p>}
        {output.notice && <p role="status">{output.notice}</p>}
        {testMessage && <p role="status">{testMessage}</p>}
        {output.error && <p role="alert">{output.error}</p>}
    </div>;
}
