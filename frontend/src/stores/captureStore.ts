import { create } from 'zustand';
import type { CaptureAckMessage, CaptureCompleteMessage, RoomSuggestionMessage } from '../services/websocket';

function needsSpace(prev: string, next: string): boolean {
  if (!prev || !next) return false;
  const lastChar = prev[prev.length - 1];
  const firstChar = next[0];
  if (/\s/.test(lastChar) || /\s/.test(firstChar)) return false;
  if (/[.,!?;:'")\]\-]/.test(firstChar)) return false;
  return true;
}

export type CaptureStatus = 'idle' | 'capturing' | 'processing' | 'complete' | 'error';
export type CapturePace = 'selective' | 'balanced' | 'thorough';

interface CaptureState {
  ready: boolean;
  setReady: (ready: boolean) => void;
  sessionId: string | null;
  status: CaptureStatus;
  sourceType: 'webcam' | 'screen_share' | 'upload' | 'text_input' | 'voice';
  capturePace: CapturePace;
  concepts: CaptureAckMessage['extraction'][];
  summary: CaptureCompleteMessage['summary'] | null;
  roomSuggestion: RoomSuggestionMessage | null;
  /** Resolves when the user responds to a room suggestion */
  roomSuggestionResolver: ((choice: RoomSuggestionChoice) => void) | null;
  error: string | null;
  activeStream: MediaStream | null;
  /** Chat conversation messages (user + aira turns) */
  messages: ChatMessage[];
  /** Whether conversation panel is visible */
  showPanel: boolean;

  setSessionId: (id: string | null) => void;
  setStatus: (status: CaptureStatus) => void;
  setSourceType: (type: CaptureState['sourceType']) => void;
  setCapturePace: (pace: CapturePace) => void;
  addConcept: (extraction: CaptureAckMessage['extraction']) => void;
  setSummary: (summary: CaptureCompleteMessage['summary']) => void;
  setRoomSuggestion: (
    msg: RoomSuggestionMessage | null,
    resolver?: (choice: RoomSuggestionChoice) => void,
  ) => void;
  setError: (error: string | null) => void;
  setActiveStream: (stream: MediaStream | null) => void;
  /** Add an inline tool-call event to conversation log */
  addToolEvent: (text: string, toolName: string) => void;
  /** Append text to the last aira message, or create a new one */
  appendAIRAText: (text: string) => void;
  /** Append text to the last user message, or create a new one */
  appendUserText: (text: string) => void;
  setShowPanel: (show: boolean) => void;
  /** Clear all messages from conversation log */
  clearMessages: () => void;
  reset: () => void;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'aira' | 'tool';
  text: string;
  toolName?: string;
}

export interface RoomSuggestionChoice {
  action: 'accept' | 'reject' | 'edit';
  editedName?: string;
  editedStyle?: string;
}

const defaultState = {
  ready: false,
  sessionId: null,
  status: 'idle' as CaptureStatus,
  sourceType: 'webcam' as const,
  capturePace: 'balanced' as CapturePace,
  concepts: [],
  summary: null,
  roomSuggestion: null,
  roomSuggestionResolver: null,
  error: null,
  activeStream: null,
  messages: [] as ChatMessage[],
  showPanel: false,
};

export const useCaptureStore = create<CaptureState>((set) => ({
  ...defaultState,
  setReady: (ready) => set({ ready }),

  setSessionId: (sessionId) => set({ sessionId }),
  setStatus: (status) => set({ status }),
  setSourceType: (sourceType) => set({ sourceType }),
  setCapturePace: (capturePace) => set({ capturePace }),
  addConcept: (extraction) =>
    set((state) => ({ concepts: [...state.concepts, extraction] })),
  setSummary: (summary) => set({ summary }),
  setRoomSuggestion: (roomSuggestion, roomSuggestionResolver = undefined) =>
    set({ roomSuggestion, roomSuggestionResolver: roomSuggestionResolver ?? null }),
  setError: (error) => set({ error }),
  setActiveStream: (activeStream) => set({ activeStream }),
  addToolEvent: (text, toolName) =>
    set((state) => ({
      messages: [...state.messages, { id: `tool-${Date.now()}`, role: 'tool', text, toolName }],
    })),
  appendAIRAText: (text) =>
    set((state) => {
      const msgs = [...state.messages];
      const last = msgs[msgs.length - 1];
      if (last && last.role === 'aira') {
        const sep = needsSpace(last.text, text) ? ' ' : '';
        msgs[msgs.length - 1] = { ...last, text: last.text + sep + text };
      } else {
        msgs.push({ id: `aira-${Date.now()}`, role: 'aira', text });
      }
      return { messages: msgs };
    }),
  appendUserText: (text) =>
    set((state) => {
      const msgs = [...state.messages];
      const last = msgs[msgs.length - 1];
      if (last && last.role === 'user') {
        const sep = needsSpace(last.text, text) ? ' ' : '';
        msgs[msgs.length - 1] = { ...last, text: last.text + sep + text };
      } else {
        msgs.push({ id: `user-${Date.now()}`, role: 'user', text });
      }
      return { messages: msgs };
    }),
  setShowPanel: (showPanel) => set({ showPanel }),
  clearMessages: () => set({ messages: [] }),
  reset: () => set(defaultState),
}));
