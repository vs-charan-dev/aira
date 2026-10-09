import { create } from 'zustand';
export const useTaskState = create<{ active: number; label: string; update: (active: number, label: string) => void }>(set => ({ active: 0, label: '', update: (active, label) => set({ active, label }) }));
