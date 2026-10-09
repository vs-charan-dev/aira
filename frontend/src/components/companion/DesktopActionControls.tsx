import { useState } from 'react';
import type { DesktopAction, HostState } from '../../services/desktop';
export function DesktopActionControls({ host, configure }: { host: HostState | null; configure: (value: { controlEnabled: boolean }) => Promise<void> }) {
  const [apps, setApps] = useState<string[]>([]), [appName, setAppName] = useState('Notion');
  const [folder, setFolder] = useState('E:\\Havetobuild\\AIRA');
  const [title, setTitle] = useState('AIRA demo note'), [content, setContent] = useState('Prepare the Memory Palace demo.');
  const [targetApp, setTargetApp] = useState('Notion'), [task, setTask] = useState('Inspect the current Notion page.');
  const [quickText,setQuickText] = useState('Hi Charan');
  const [calculation,setCalculation] = useState('78*87');
  const [place,setPlace] = useState('Hyderabad');
  const [loading, setLoading] = useState(false), [notice, setNotice] = useState('');
  const desktop = window.airaDesktop!;
  const refresh = async () => {
    setLoading(true);
    try { const names = await desktop.listApps(); setApps(names); setAppName(previous => names.includes(previous) ? previous : names[0] || ''); setNotice('Installed apps loaded.'); }
    catch (error) { setNotice(error instanceof Error ? error.message : 'Could not load apps.'); }
    finally { setLoading(false); }
  };
  const run = async (action: DesktopAction) => {
    setLoading(true); setNotice('Starting desktop action…');
    try { const result = await desktop.runAction(action); setNotice(result.message); }
    catch { setNotice('Desktop controller unavailable.'); }
    finally { setLoading(false); }
  };
  const busy = loading || !!host?.desktopAction?.running;
  return <section className="aira-desktop-actions" aria-label="AIRA desktop actions">
    <strong>Desktop actions</strong>
    <p>Say “Close Calculator” or “Go to Chrome, open Google Maps and search for Hyderabad”. You can also open apps and folders, or calculate in Calculator.</p>
    <label><input type="checkbox" checked={host?.controlEnabled ?? true} onChange={event => void configure({ controlEnabled: event.target.checked })} /> Enable desktop actions</label>
    <p>Ctrl+Alt+Escape stops actions and conversation immediately.</p>
    {host && !host.stopHotkeyRegistered && <p role="alert">Stop shortcut unavailable. Actions are blocked until it is available.</p>}
    <button disabled={busy} onClick={() => void refresh()}>Refresh installed apps</button>
    <label>App <select aria-label="App to open" value={appName} onChange={event => setAppName(event.target.value)}>
      {!apps.length && <option value="Notion">Notion</option>}{apps.map(name => <option key={name} value={name}>{name}</option>)}
    </select></label>
    <button disabled={busy || !host?.controlEnabled || !host?.stopHotkeyRegistered || !appName} onClick={() => void run({ kind: 'open_app', appName })}>Open app visibly · no API usage</button>
    <button disabled={busy || !host?.controlEnabled || !host?.stopHotkeyRegistered || !appName} onClick={() => void run({ kind: 'close_app', appName })}>Close window · direct · no API usage</button>
    <label>Place or address<input aria-label="Google Maps place" maxLength={250} value={place} onChange={event => setPlace(event.target.value)} /></label>
    <button disabled={busy || !host?.controlEnabled || !host?.stopHotkeyRegistered} onClick={() => void run({kind:'open_maps'})}>Open Google Maps in Chrome</button>
    <button disabled={busy || !host?.controlEnabled || !host?.stopHotkeyRegistered || !place.trim()} onClick={() => void run({kind:'search_maps',query:place})}>Search Google Maps</button>
    <label>Folder <input aria-label="Folder to open" value={folder} onChange={event => setFolder(event.target.value)} /></label>
    <button disabled={busy || !host?.controlEnabled || !host?.stopHotkeyRegistered} onClick={() => void run({ kind: 'open_folder', path: folder })}>Open folder · no API usage</button>
    <label>Text to append to the current editable Notion page<input aria-label="Direct Notion text" maxLength={2000} value={quickText} onChange={event => setQuickText(event.target.value)} /></label>
    <button disabled={busy || !host?.controlEnabled || !host?.stopHotkeyRegistered || !quickText} onClick={() => void run({kind:'type_in_app',appName:'Notion',text:quickText})}>Append in Notion · no API usage</button>
    <p>Open the intended editable Notion page first. Direct entry appends plain text and checks readback. Notion handles its own sync; AIRA does not independently confirm it.</p>
    <label>Calculator expression<input aria-label="Direct Calculator expression" maxLength={80} value={calculation} onChange={event => setCalculation(event.target.value)} /></label>
    <button disabled={busy || !host?.controlEnabled || !host?.stopHotkeyRegistered || !calculation.trim()} onClick={() => void run({kind:'calculate_in_app',expression:calculation})}>Calculate visibly · no API usage</button>
    <p>Two nonnegative numbers with +, −, × or ÷. The displayed result is checked against an independent calculation.</p>
    <p>Notion: open a page in your signed-in workspace first. AIRA creates a new note in the selected workspace. Notion uses its own account and sync service.</p>
    <label>Note title <input aria-label="Notion note title" maxLength={160} value={title} onChange={event => setTitle(event.target.value)} /></label>
    <label>Note content <textarea aria-label="Notion note content" maxLength={2000} value={content} onChange={event => setContent(event.target.value)} /></label>
    <button disabled={busy || !host?.controlEnabled || !host?.stopHotkeyRegistered || !title.trim() || !content.trim()} onClick={() => void run({ kind: 'create_notion_note', title, content })}>Create Notion note · no Gemini usage</button>
    <strong>Windows-Use GUI task</strong>
    <label>Target app <input aria-label="Windows-Use target app" maxLength={80} value={targetApp} onChange={event => setTargetApp(event.target.value)} /></label>
    <label>Task <textarea aria-label="Windows-Use task" maxLength={2000} value={task} onChange={event => setTask(event.target.value)} /></label>
    <button disabled={busy || !host?.controlEnabled || !host?.stopHotkeyRegistered || !targetApp.trim() || !task.trim()} onClick={() => void run({ kind: 'desktop_task', appName: targetApp, task })}>Run Windows-Use task · uses Gemini</button>
    <p>Say “In Notion, append Hi Charan” or request a specific setting in Settings. This sends desktop interface context to Gemini using your saved key. Tasks and action metadata are saved locally on E. Shell/file tools, dragging, installation and destructive tasks are blocked. GUI control is not a sandbox.</p>
    <button onClick={() => void desktop.stopAction()}>Stop desktop action</button>
    <p role="status">{host?.desktopAction?.running ? host.desktopAction.label : notice || host?.desktopAction?.label}</p>
    {!host?.desktopAction?.running && host?.desktopAction?.timings?.totalMs != null && <p>Last desktop command: {(host.desktopAction.timings.totalMs/1000).toFixed(1)} s{host.desktopAction.timings.firstInputMs != null ? ` · first input ${(host.desktopAction.timings.firstInputMs/1000).toFixed(1)} s` : ''}. Timing starts when the desktop receives the command; voice recognition is separate.</p>}
    <p>Say “Create a Notion note titled Demo checklist with content Prepare the Memory Palace demo.” Plain text only. Stop or failure may leave partial changes; check before retrying. Closing an app never force-kills it or discards unsaved work. A tray/background process may remain.</p>
  </section>;
}
