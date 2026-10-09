import { useEffect } from 'react';
import { useAuthStore } from '../stores/authStore';

export function useAuth() {
  const { user, loading, setLoading } = useAuthStore();
  useEffect(() => { setLoading(false); }, [setLoading]);
  return { user, loading };
}
