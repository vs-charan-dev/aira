import { useEffect, useState } from 'react';
import type { HostState } from '../../services/desktop';
import { AudioOutputControls } from './AudioOutputControls';
import { DesktopActionControls } from './DesktopActionControls';
import { desktopStatus } from '../../services/desktopStatus';
export function DesktopControls({ stop }: { stop: () => void }) {
  const [host, setHost] = useState<HostState | null>(null);
  const [hotkey, setHotkey] = useState('Control+Alt+A');
  const [error, setError] = useState('');
  useEffect(() => {
    const desktop = window.airaDesktop;
    if (!desktop) return;
    const unsub = desktop.onHost(value => { setHost(value); setHotkey(value.hotkey); });
    desktop.ready();
    return unsub;
  }, []);
  if (!window.airaDesktop || window.airaDesktop.role !== 'owner') return null;
  const configure = async (value: { hotkey?: string; wakeEnabled?: boolean; wakeSensitivity?: 'normal' | 'sensitive'; controlEnabled?: boolean }) => {
    try { setError(''); setHost(await window.airaDesktop!.configure(value)); } catch (err) { setError(err instanceof Error ? err.message : 'Could not update settings'); }
  };
  const testWake = async () => {
    try { setError(''); setHost(await window.airaDesktop!.testWake()); } catch (err) { setError(err instanceof Error ? err.message : 'Could not test wake recognition'); }
  };
  return <details className="aira-desktop-controls"><summary>{desktopStatus(host)}</summary>
    <p>Ctrl+Alt+A activates AIRA from any app.</p>
    <label>Global shortcut <input aria-label="Global AIRA hotkey" value={hotkey} onChange={event => setHotkey(event.target.value)} /></label>
    <button onClick={() => void configure({ hotkey })}>Save shortcut</button>
    {host && !host.hotkeyRegistered && <p role="alert">Shortcut unavailable. Choose another shortcut.</p>}
    <button onClick={() => void configure({ wakeEnabled: !host?.wakeEnabled })}>{host?.wakeEnabled ? 'Disable Hey AIRA' : 'Enable Hey AIRA'}</button>
    <p>Wake recognition stays on this computer. Enabling it keeps the microphone open while idle; it pauses during conversation and capture.</p>
    <p>Stop ends the current conversation, capture and actions; it keeps your desktop-control and Hey AIRA preferences. Ctrl+Alt+A starts another conversation. Say “Look at this Notion page” for a single screen view, or “Capture my screen” for continuous memory capture. The Windows app uses the monitor under your cursor without another chooser; screen images are sent to Gemini.</p>
    <p role="status">{host?.wakeStatus}</p>
    <p role="status">Local stop command: {host?.interruptStatus === 'listening' ? 'Ready · say “Stop AIRA” or “Cancel AIRA”' : host?.interruptStatus?.startsWith('ERROR:') ? 'Unavailable · use Ctrl+Alt+Escape' : host?.interruptStatus === 'starting' ? 'Starting' : 'Arms during conversation or desktop work'}. This ends the session and cancels desktop input without waiting for Gemini. Recognition can miss speech; Ctrl+Alt+Escape remains the immediate stop.</p>
    <button onClick={() => { if (host?.wakeTesting) void configure({ wakeEnabled: host.wakeEnabled }); stop(); }}>Stop conversation / capture</button>
    <label>Wake sensitivity <select aria-label="AIRA wake sensitivity" value={host?.wakeSensitivity || 'normal'} onChange={event => void configure({ wakeSensitivity: event.target.value as 'normal' | 'sensitive' })}>
      <option value="normal">Normal · fewer false activations</option><option value="sensitive">More sensitive · easier to activate</option>
    </select></label>
    <button onClick={() => host?.wakeTesting ? void configure({ wakeEnabled: host.wakeEnabled }) : void testWake()}>{host?.wakeTesting ? 'Cancel wake test' : 'Test wake phrase · no API usage'}</button>
    <p>The test listens locally for 20 seconds without opening Gemini. Say “Hey AIRA” a few times; try “Hey eye-rah” or “Hey air-ah”. Stop conversation first.</p>
    {host?.wakeDiagnostic && <div aria-label="Wake recognition diagnostics">
      <label>Wake microphone level <meter min={0} max={100} value={host.wakeDiagnostic.level} /> {host.wakeDiagnostic.level}%</label>
      <p>Recognizer: {host.wakeDiagnostic.culture}. Speech detections: {host.wakeDiagnostic.speechCount}. Rejected: {host.wakeDiagnostic.rejectedCount}.</p>
      {host.wakeDiagnostic.phrase && <p>Grammar match: “{host.wakeDiagnostic.phrase}” · confidence {Math.round(host.wakeDiagnostic.confidence * 100)}% · {host.wakeDiagnostic.matched ? 'wake phrase matched' : 'below cutoff'}.</p>}
      {host.wakeDiagnostic.signal && <p>Input warning: {host.wakeDiagnostic.signal}</p>}
    </div>}
    {host?.wakeTestResult && <p role="status">{host.wakeTestResult}</p>}
    <AudioOutputControls />
    <DesktopActionControls host={host} configure={configure} />
    {error && <p role="alert">{error}</p>}
  </details>;
}
