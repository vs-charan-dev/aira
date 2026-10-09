import { useEffect, useRef, useState } from 'react';
import { callReminderApi, type CallReminder, type CallSettings } from '../../services/callReminderApi';
import './phoneReminders.css';

const at = (value: string) => new Intl.DateTimeFormat('en-IN', {
  timeZone: 'Asia/Kolkata', month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit',
}).format(new Date(value));

export function CallReminderList() {
  const [rows, setRows] = useState<CallReminder[]>([]);
  const [error, setError] = useState('');
  const [pending, setPending] = useState<string | null>(null);
  const alive = useRef(false);
  useEffect(() => {
    alive.current = true;
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    async function refresh() {
      try {
        const value = await callReminderApi.list(controller.signal);
        if (alive.current) { setRows(value.reminders); setError(''); }
      } catch (e) {
        if (alive.current) setError(e instanceof Error ? e.message : 'Could not load reminders.');
      } finally {
        if (alive.current) timer = setTimeout(() => void refresh(), 2000);
      }
    }
    void refresh();
    return () => { alive.current = false; controller.abort(); clearTimeout(timer); };
  }, []);
  async function cancel(id: string) {
    if (pending) return;
    setPending(id);
    try {
      const result = await callReminderApi.cancel(id);
      if (alive.current) setRows(current => current.map(row => row.id === id ? result : row));
    } catch (e) {
      if (alive.current) setError(e instanceof Error ? e.message : 'Could not cancel reminder.');
    } finally { if (alive.current) setPending(null); }
  }
  return <div className="aira-phone-list">
    <h4>Phone reminders</h4>
    {error && <p role="alert" className="aira-phone-error">{error}</p>}
    {!error && rows.length === 0 && <p>No phone reminders yet. Set up calling in Settings, then ask “Call me in one minute.”</p>}
    {rows.slice(0, 10).map(row => <article key={row.id}>
      <div><strong>{row.message}</strong><span>{at(row.dueAt)} IST · Your number {row.recipientPreview}{row.callMode === 'trial-demo' ? ' · Trial demo audio' : ''}</span></div>
      <div className="aira-phone-outcome"><b>{row.callStatus || row.status}</b>
        {row.status === 'pending' && <button disabled={!!pending} onClick={() => void cancel(row.id)}>{pending === row.id ? 'Cancelling…' : 'Cancel reminder'}</button>}
      </div>
      <p>{row.detail}</p>
    </article>)}
  </div>;
}

export function PhoneReminders() {
  const [config, setConfig] = useState<CallSettings | null>(null);
  const [accountSid, setAccountSid] = useState('');
  const [authToken, setAuthToken] = useState('');
  const [fromNumber, setFromNumber] = useState('');
  const [toNumber, setToNumber] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [message, setMessage] = useState('Time to head out.');
  const [mode, setMode] = useState('delay');
  const [minutes, setMinutes] = useState('1');
  const [clock, setClock] = useState('');
  const [date, setDate] = useState('');
  const alive = useRef(false);
  const operation = useRef(false);
  // A retry of the same form submission must not schedule another paid call.
  const attempt = useRef<{ body: string; id: string } | null>(null);
  useEffect(() => {
    alive.current = true;
    const controller = new AbortController();
    callReminderApi.settings(controller.signal).then(value => {
      if (!alive.current) return;
      setConfig(value); setAccountSid(value.accountSid); setFromNumber(value.fromNumber); setToNumber(value.toNumber);
    }).catch(e => { if (alive.current) setError(e instanceof Error ? e.message : 'Could not load calling setup.'); });
    return () => { alive.current = false; controller.abort(); };
  }, []);
  async function perform(action: () => Promise<void>) {
    if (operation.current) return;
    operation.current = true;
    setBusy(true); setError(''); setNotice('');
    try { await action(); }
    catch (e) { if (alive.current) setError(e instanceof Error ? e.message : 'Phone reminder request failed.'); }
    finally { operation.current = false; if (alive.current) setBusy(false); }
  }
  return <section className="aira-phone-settings" aria-label="Phone reminders setup">
    <h3>Phone reminders</h3>
    <p>AIRA calls your saved number when a reminder is due. Trial accounts play Twilio demo audio; upgraded accounts speak your reminder. Keep AIRA running and your computer awake and online. Times use IST (UTC+05:30).</p>
    <details open={!config?.configured}>
      <summary>{config?.configured ? 'Calling setup saved · Edit Twilio settings' : 'Set up Twilio calling'}</summary>
      <form onSubmit={e => { e.preventDefault(); void perform(async () => {
        const value = await callReminderApi.save({ accountSid, authToken, fromNumber, toNumber });
        if (alive.current) { setConfig(value); setAuthToken(''); setNotice('Calling setup saved. Schedule a one-minute reminder to test your phone.'); }
      }); }}>
        <label>Twilio Account SID<input autoComplete="off" value={accountSid} onChange={e => setAccountSid(e.target.value)} placeholder="AC…" required /></label>
        <label>Twilio Auth Token<input type="password" autoComplete="new-password" value={authToken} onChange={e => setAuthToken(e.target.value)} placeholder={config?.configured ? 'Saved securely · leave blank to keep' : 'Auth Token'} required={!config?.configured} /></label>
        <label>Twilio calling number<input type="tel" value={fromNumber} onChange={e => setFromNumber(e.target.value)} placeholder="+1…" required /></label>
        <label>Your phone number<input type="tel" value={toNumber} onChange={e => setToNumber(e.target.value)} placeholder="+91…" required /></label>
        <p>Credentials are encrypted for your Windows account. Calls into India need a non-Indian calling number. Trial recipients must be verified in Twilio.</p>
        <button disabled={busy || !config} type="submit">{busy ? 'Working…' : 'Save calling setup'}</button>
      </form>
      {config?.configured && <button disabled={busy} type="button" onClick={() => void perform(async () => {
        const value = await callReminderApi.remove();
        if (alive.current) { setConfig(value); setAccountSid(''); setFromNumber(''); setToNumber(''); setAuthToken(''); setNotice('Calling setup removed and pending phone reminders cancelled. Calls already dispatched may continue.'); }
      })}>Remove calling setup & cancel pending reminders</button>}
      <a href="https://console.twilio.com/" target="_blank" rel="noreferrer">Open Twilio Console</a>
    </details>
    {config?.storageError && <p role="alert" className="aira-phone-error">{config.storageError}</p>}
    {config?.configured && <form onSubmit={e => { e.preventDefault(); void perform(async () => {
      const body = { message, ...(mode === 'delay' ? { after_seconds: Number(minutes) * 60 } : { local_time: clock, ...(date ? { local_date: date } : {}) }) };
      const signature = JSON.stringify(body);
      if (attempt.current?.body !== signature) attempt.current = { body: signature, id: crypto.randomUUID() };
      const value = await callReminderApi.schedule({ ...body, requestId: attempt.current!.id });
      attempt.current = null;
      if (alive.current) { setNotice(value.status === 'pending' ? `Scheduled for ${at(value.dueAt)} IST. Your number ends in ${value.recipientPreview.slice(1)}.` : `This request is already ${value.status}. ${value.detail}`); }
    }); }}>
      <h4>Try a reminder</h4>
      <label>Reminder message<textarea value={message} onChange={e => setMessage(e.target.value)} maxLength={500} required /></label>
      <label>When?<select value={mode} onChange={e => setMode(e.target.value)}><option value="delay">After a delay</option><option value="clock">At a time in IST</option></select></label>
      {mode === 'delay' ? <label>Minutes from now<input type="number" min="1" max="10080" step="1" value={minutes} onChange={e => setMinutes(e.target.value)} required /></label> : <>
        <label>Time in IST<input type="time" value={clock} onChange={e => setClock(e.target.value)} required /></label>
        <label>Date (blank means today)<input type="date" value={date} onChange={e => setDate(e.target.value)} /></label>
      </>}
      <p>This places a real phone call when due and may use Twilio credit. Calls can ring a few seconds after the scheduled time.</p>
      <button disabled={busy} type="submit">{busy ? 'Working…' : 'Schedule phone call'}</button>
    </form>}
    {error && <p role="alert" className="aira-phone-error">{error}</p>}
    {notice && <p role="status" className="aira-phone-notice">{notice}</p>}
    <CallReminderList />
  </section>;
}
