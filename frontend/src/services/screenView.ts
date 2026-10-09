import type { AIRAWebSocket, ServerMessage } from './websocket';

/** Snapshot only on a current voice tool request; never replay on reconnect. */
export function wireScreenViews(ws: AIRAWebSocket, isCurrent: (message: Extract<ServerMessage, { type: 'screen_view_request' }>) => boolean) {
  let disposed = false, generation = 0;
  const seen = new Set<string>();
  const unsubscribe = ws.on('screen_view_request', async message => {
    if (disposed || seen.has(message.requestId)) return;
    seen.add(message.requestId);
    if (seen.size > 100) seen.delete(seen.values().next().value!);
    const current = generation;
    let data: string | null = null;
    try {
      if (isCurrent(message) && window.airaDesktop?.role === 'owner') data = await window.airaDesktop.screenSnapshot();
    } catch { /* Return a failure without screen content in diagnostics. */ }
    if (!disposed && current === generation && isCurrent(message)) ws.sendScreenViewResult(message.requestId, data);
  });
  const transport = ws.on('transport_closed', () => { generation++; });
  return () => { disposed = true; unsubscribe(); transport(); };
}
