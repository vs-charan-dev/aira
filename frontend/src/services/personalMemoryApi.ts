import { apiGet, apiPatch, apiPost } from './api';

export type MemoryStatus = 'active' | 'outdated' | 'uncertain' | 'superseded';
export type MemoryKind = 'fact' | 'inference' | 'unknown';
export interface PersonalMemory {
  id: string; room: string; room_id: string; category: string; title: string; memory: string;
  importance: string; tags: string[]; source: string; source_file: string; source_line: number;
  question: string; created_at: string; as_of: string; event_date: string | null;
  kind: MemoryKind; status: MemoryStatus; version: number; updated_at?: string;
  semantic_key: string; history: Omit<PersonalMemory, 'history'>[];
}
export interface MemoryRoom { id: string; prefix: string; name: string; icon: string; style: string }
export interface MemoryAnswer {
  answer: string; kind: MemoryKind; references: PersonalMemory[];
  conflicts: { key: string; memory_ids: string[] }[]; retrieval: string;
}
export const personalMemoryApi = {
  list: () => apiGet<{ rooms: MemoryRoom[]; memories: PersonalMemory[] }>('/personal-memories'),
  ask: (query: string) => apiPost<MemoryAnswer>('/personal-memories/query', { query }),
  search: (query: string) => apiGet<{ memories: PersonalMemory[] }>(`/personal-memories/search?query=${encodeURIComponent(query)}`),
  correct: (id: string, changes: { expected_version: number; memory: string; status: MemoryStatus; kind: MemoryKind; event_date: string | null }) =>
    apiPatch<{ memory: PersonalMemory }>(`/personal-memories/${encodeURIComponent(id)}`, changes),
};
