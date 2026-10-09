import { create } from 'zustand';
import type { Mode } from '../services/desktop';
export const useCompanionStore = create<{
  thinking: boolean; hiddenUntil: number; notice: string; pendingMode: Mode | null;
  update: (value: Partial<{ thinking: boolean; hiddenUntil: number; notice: string; pendingMode: Mode | null }>) => void;
}>(set => ({ thinking: false, hiddenUntil: 0, notice: '', pendingMode: null, update: value => set(value) }));
