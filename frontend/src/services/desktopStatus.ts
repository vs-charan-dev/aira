import type { HostState } from './desktop';
export function desktopStatus(host: HostState | null): string {
  if (!host) return 'Desktop · starting';
  const actions = host.controlEnabled ? 'Controls on' : 'Controls off';
  const wake = host.wakeTesting ? 'Testing Hey AIRA' : !host.wakeEnabled ? 'Hey AIRA off'
    : host.wakeStatus === 'listening' ? 'Hey AIRA ready'
    : host.wakeStatus === 'paused' ? 'Hey AIRA paused during activity'
    : host.wakeStatus.startsWith('ERROR:') ? 'Hey AIRA needs attention' : 'Hey AIRA starting';
  return `Desktop · ${actions} · ${wake}`;
}
