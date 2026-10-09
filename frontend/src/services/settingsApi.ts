import { apiGet, apiPut, apiPost } from './api';

export interface UserSettings {
  hasGeminiKey: boolean;
  geminiApiKeyPreview: string | null;
  keyStorageError?: string | null;
  voiceName: string;
  voices: Array<{ name: string; description: string }>;
}
export interface VoicePreview { voiceName: string; text: string; audio: string; sampleRate: number; durationSeconds: number; cached: boolean }

export const settingsApi = {
  getUsage: () => apiGet<UsageSummary>('/usage'),
  testConnection: () => apiPost<{ results: Array<{ feature: string; ok: boolean | null; message: string }> }>('/settings/test'),
  getSettings: () => apiGet<UserSettings>('/settings'),
  saveSettings: (geminiApiKey: string | null) =>
    apiPut<{ ok: boolean }>('/settings', { geminiApiKey }),
  saveVoice: (voiceName: string) => apiPut<{ ok: boolean }>('/settings', { voiceName }),
  previewVoice: (voiceName: string, signal?: AbortSignal) => apiPost<VoicePreview>('/settings/voice-preview', { voiceName }, { signal }),
};

export interface UsageRecord {
  id: string; feature: string; kind: string; model: string; status: string;
  startedAt: string; elapsedSeconds: number; estimatedUsd: number | null;
  estimateComplete: boolean; usageAvailable: boolean; stopReason: string | null;
  breakdown: { input: Record<string, number>; output: Record<string, number>; tool: Record<string, number>; thoughts: number; cached: number };
}
export interface UsageSummary {
  estimatedUsd: number; calls: number; incompleteCalls: number; activeCalls: number;
  rateDate: string; rateSource: string; liveUsageMode: string; records: UsageRecord[];
  limits: { idleSeconds: number; maxSeconds: number; maxEstimatedUsd: number };
}
