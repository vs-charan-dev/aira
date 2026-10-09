import { useAuthStore } from '../stores/authStore';

let pending: Promise<void> | null = null;
export function openLocalSession(): Promise<void> {
  if (pending) return pending;
  pending = (async () => {
    const response = await fetch('/api/v1/local-session', { method: 'POST' });
    if (!response.ok) throw new Error('Could not open AIRA. Check that the local backend is running.');
    const session = await response.json();
    useAuthStore.getState().setUser({
      uid: session.userId, displayName: session.displayName, email: '', photoURL: null,
      getIdToken: async () => session.token,
    });
    useAuthStore.getState().setLoading(false);
  })().finally(() => { pending = null; });
  return pending;
}

export async function closeLocalSession() {
  await fetch('/api/v1/local-session', { method: 'DELETE' });
  useAuthStore.getState().setUser(null);
  window.location.assign('/login');
}
