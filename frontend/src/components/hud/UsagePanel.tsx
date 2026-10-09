import { useEffect, useState } from 'react';
import { settingsApi, type UsageSummary } from '../../services/settingsApi';

function money(value: number | null) {
  if (value === null) return 'Unavailable';
  if (value > 0 && value < .0001) return '<$0.0001';
  return `$${value.toFixed(4)}`;
}

export function UsagePanel() {
  const [usage, setUsage] = useState<UsageSummary | null>(null);
  const [error, setError] = useState(false);
  useEffect(() => {
    let disposed = false;
    let busy = false;
    const refresh = async () => {
      if (busy) return;
      busy = true;
      try {
        const result = await settingsApi.getUsage();
        if (!disposed) { setUsage(result); setError(false); }
      } catch { if (!disposed) setError(true); }
      finally { busy = false; }
    };
    void refresh();
    const timer = setInterval(() => { void refresh(); }, 3000);
    return () => { disposed = true; clearInterval(timer); };
  }, []);
  return <section className="border-t border-border pt-4 flex flex-col gap-2 text-xs">
    <h3 className="font-semibold text-text-primary">API usage</h3>
    {error && <p className="text-error">Usage couldn’t refresh. Check the local backend.</p>}
    {!usage && !error && <p className="text-text-muted">Loading local usage…</p>}
    {usage && <>
      <p className="text-text-primary"><strong>{money(usage.estimatedUsd)}</strong> recorded token estimate · {usage.calls} calls · {usage.activeCalls} active</p>
      <p className="text-text-muted">Since this meter was installed. Standard paid-tier estimate, not your Google bill or balance. Free-tier allowances, missing usage, and search surcharges aren’t included. {usage.incompleteCalls > 0 && `${usage.incompleteCalls} calls have incomplete estimates.`}</p>
      <p className="text-text-muted">Live stops after {usage.limits.idleSeconds ? `${usage.limits.idleSeconds}s idle` : 'no idle limit'} or {usage.limits.maxSeconds ? `${usage.limits.maxSeconds}s total` : 'no duration limit'}{usage.limits.maxEstimatedUsd > 0 && `, or about ${money(usage.limits.maxEstimatedUsd)} in reported Live tokens`}. Usage can arrive late; the cost threshold is a soft limit.</p>
      <p className="text-text-muted">Live history is counted per turn by default. Estimates need comparison with Google usage; missing data never proves a call was free.</p>
      {usage.limits.maxEstimatedUsd===0 && <p className="text-text-muted">Estimated Live cost cap is disabled. Usage recording remains active.</p>}
      {usage.records.length === 0 ? <p className="text-text-muted">No recorded calls yet. Opening this panel makes no Gemini calls.</p> :
        <div className="flex flex-col gap-2 max-h-52 overflow-y-auto">
          {usage.records.map(record => <details key={record.id} className="rounded-lg border border-border p-2">
            <summary className="cursor-pointer text-text-primary">
              {record.feature.replaceAll('_', ' ')} · {record.kind === 'live' ? 'Live' : record.kind === 'embed_content' ? 'Embedding' : 'Inference'} · {money(record.estimatedUsd)}{record.estimatedUsd !== null && !record.estimateComplete ? ' (partial)' : ''}
            </summary>
            <p className="text-text-muted mt-2">{record.model} · {record.status} · {record.status === 'active' ? Math.max(0, Math.round((Date.now() - Date.parse(record.startedAt)) / 1000)) : record.elapsedSeconds}s · {new Date(record.startedAt).toLocaleString()}</p>
            {record.stopReason && <p className="text-text-muted">Stopped: {record.stopReason.replaceAll('_', ' ')}</p>}
            {!record.usageAvailable && <p className="text-text-muted">Provider token usage was not returned.</p>}
            {(['input', 'output', 'tool'] as const).map(direction => Object.entries(record.breakdown[direction]).length > 0 &&
              <p key={direction} className="text-text-muted">{direction}: {Object.entries(record.breakdown[direction]).map(([modality, count]) => `${modality.toLowerCase()} ${count}`).join(', ')} tokens</p>)}
            {record.breakdown.thoughts > 0 && <p className="text-text-muted">Thinking: {record.breakdown.thoughts} tokens</p>}
          </details>)}
        </div>}
      <a className="text-primary hover:underline" href={usage.rateSource} target="_blank" rel="noopener noreferrer">Google pricing · rates checked {usage.rateDate}</a>
    </>}
  </section>;
}
