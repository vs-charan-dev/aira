import type { DesktopActionResult } from './desktop';
import type { AIRAWebSocket, ServerMessage } from './websocket';

/** One owner only; transport loss/unmount abort native work. No replay on reconnect. */
export function wireDesktopActions(ws: AIRAWebSocket, isCurrent: (message: Extract<ServerMessage, { type: 'desktop_action' }>) => boolean) {
  const seen = new Set<string>();
  const active = new Map<string, { source: 'recall' | 'capture' | 'job'; sessionId: string | null }>();
  let disposed = false;
  let transportGeneration = 0;
  const desktop = window.airaDesktop?.role === 'owner' ? window.airaDesktop : undefined;
  const stopAll = () => { for (const id of active.keys()) void desktop?.stopAction(id); active.clear(); };
  const unsubscribe = ws.on('desktop_action', async message => {
    if (seen.has(message.requestId) || disposed) return;
    seen.add(message.requestId); if (seen.size > 100) seen.delete(seen.values().next().value!);
    if (!desktop || (message.source !== 'job' && !isCurrent(message))) {
      ws.sendDesktopActionResult(message.requestId, { status: 'failed', message: desktop ? 'The originating voice session has stopped.' : 'Launch Start-AIRA-Desktop.cmd to control Windows.' });
      return;
    }
    active.set(message.requestId, { source: message.source, sessionId: message.sessionId });
    const generation = transportGeneration;
    let result: DesktopActionResult;
    try { result = await desktop.runAction(message.action, message.requestId); }
    catch { result = { status: 'failed', message: 'Desktop controller unavailable.' }; }
    active.delete(message.requestId);
    if (!disposed && generation === transportGeneration) ws.sendDesktopActionResult(message.requestId, result);
  });
  const cancel = ws.on('desktop_action_cancel', message => { if (active.has(message.requestId)) void desktop?.stopAction(message.requestId); });
  const interruptRecall = ws.on('live_interrupted', () => { for (const [id, origin] of active) if (origin.source === 'recall') void desktop?.stopAction(id); });
  const interruptCapture = ws.on('capture_interrupted', message => { for (const [id, origin] of active) if (origin.source === 'capture' && origin.sessionId === message.sessionId) void desktop?.stopAction(id); });
  const transport = ws.on('transport_closed', () => { transportGeneration++; stopAll(); });
  const progress = desktop?.onHost?.(host => {
    const action = host.desktopAction;
    if (action?.running && active.get(action.requestId)?.source === 'job') ws.sendDesktopProgress(action.requestId, action.label);
  });
  return () => { disposed = true; stopAll(); unsubscribe(); cancel(); transport(); interruptRecall(); interruptCapture(); progress?.(); };
}
