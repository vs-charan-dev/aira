import { useState } from 'react';
import { openLocalSession } from '../../services/localSession';

export function LocalSession() {
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  return <div className="flex flex-col items-center gap-3 w-full">
    <button className="w-full px-5 py-3 rounded-xl bg-indigo-600 text-white font-semibold"
      disabled={loading} onClick={async () => {
        setLoading(true); setError('');
        try { await openLocalSession(); } catch (e) { setError(e instanceof Error ? e.message : 'Unable to open session'); }
        finally { setLoading(false); }
      }}>{loading ? 'Opening…' : 'Open AIRA Memory Palace'}</button>
    <p className="text-xs text-indigo-200/60 text-center">Stored on this computer. Gemini features require your API key.</p>
    {error && <p className="text-xs text-red-400">{error}</p>}
  </div>;
}
