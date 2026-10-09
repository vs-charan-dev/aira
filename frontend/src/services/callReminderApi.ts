export interface CallSettings {
  configured: boolean;
  accountSid: string;
  fromNumber: string;
  toNumber: string;
  storageError: string | null;
  timezoneLabel: string;
}

export interface CallReminder {
  id: string;
  message: string;
  dueAt: string;
  dueLocal: string;
  status: string;
  recipientPreview: string;
  callStatus: string | null;
  callSid: string | null;
  callMode: 'reminder' | 'trial-demo' | null;
  detail: string;
}

async function request<T>(path: string, method = 'GET', body?: unknown, signal?: AbortSignal): Promise<T> {
  const response = await fetch('/api/v1/call-reminders' + path, {
    method, signal, credentials: 'same-origin', headers: { 'Content-Type': 'application/json' },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  });
  if (!response.ok) {
    if (response.status === 404) throw new Error('Restart AIRA to load the phone reminder service, then reopen Settings.');
    const value = await response.json().catch(() => ({}));
    throw new Error(typeof value.detail === 'string' ? value.detail : 'Phone reminders unavailable. Open AIRA and try again.');
  }
  return response.json();
}

export const callReminderApi = {
  settings: (signal?: AbortSignal) => request<CallSettings>('/settings', 'GET', undefined, signal),
  save: (body: { accountSid: string; authToken: string; fromNumber: string; toNumber: string }) => request<CallSettings>('/settings', 'PUT', body),
  remove: () => request<CallSettings>('/settings', 'DELETE'),
  list: (signal?: AbortSignal) => request<{ reminders: CallReminder[] }>('', 'GET', undefined, signal),
  schedule: (body: { message: string; after_seconds?: number; local_time?: string; local_date?: string; requestId: string }) => request<CallReminder>('', 'POST', body),
  cancel: (id: string) => request<CallReminder>('/' + encodeURIComponent(id) + '/cancel', 'POST', {}),
};
