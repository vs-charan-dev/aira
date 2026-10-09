import type { CharacterMood } from '../components/companion/AiraCharacter';
export type Mode = 'recall' | 'capture_voice' | 'capture_screen' | 'capture_camera' | 'stop';
export type CompanionCommand = { action: 'activate' } | { action: 'show' } | { action: 'hide'; seconds: number } | { action: 'switch_mode'; mode: Mode };
export type CompanionState = { mood: CharacterMood; label: string; busy: boolean; energy: number; hiddenUntil: number };
export type WakeDiagnostic = { level: number; speechCount: number; rejectedCount: number; phrase: string; confidence: number; matched: boolean; signal: string; culture: string };
export type DesktopAction = {kind:'run_invoice_tests';runId:string} | {kind:'show_invoice_demo'} | {kind:'export_summary_to_notion';destination:'new'|'existing';title:string;content:string;pageName:string;studyTaskId:string;videoUrl:string} | {kind:'notebooklm_mindmap';newNotebook:boolean;videoUrl:string;notebookUrl?:string} | { kind:'open_browser' | 'open_maps' | 'current_youtube_video' } | {kind:'search_youtube' | 'search_maps';query:string} | {kind:'open_youtube_video';videoUrl?:string;resultNumber?:number} | { kind: 'open_app' | 'close_app'; appName: string } | { kind: 'desktop_task'; appName: string; task: string } | { kind: 'type_in_app'; appName: string; text: string } | { kind:'calculate_in_app'; expression:string } | { kind: 'open_folder'; path: string } | {kind:'show_project';path:string;file?:'invoice.js'} | { kind: 'create_notion_note'; title: string; content: string };
export type DesktopTimings = { queueMs?: number | null; workerReadyMs?: number | null; firstInputMs?: number | null; executionMs?: number | null; totalMs?: number | null };
export type DesktopActionResult = { status: 'succeeded' | 'failed' | 'cancelled'; message: string; timings?: DesktopTimings; data?:{notebookUrl?:string;notionPageId?:string;destinationTitle?:string;sourceTitle?:string;mindMapTitle?:string;videoUrl?:string;title?:string;videos?:{index:number;title:string;videoUrl:string}[]} };
export type ActionState = { running: boolean; requestId: string; status: string; label: string; timings?: DesktopTimings };
export type HostState = { hotkey: string; hotkeyRegistered: boolean; wakeEnabled: boolean; wakeStatus: string; interruptStatus?: string; wakeSensitivity: 'normal' | 'sensitive'; wakeTesting: boolean; wakeDiagnostic: WakeDiagnostic | null; wakeTestResult: string; controlEnabled: boolean; stopHotkeyRegistered: boolean; desktopAction: ActionState | null };
declare global {
  interface Window {
    airaDesktop?: {
      role: 'owner' | 'overlay' | 'board'; ready(): void; prepareAudio(): Promise<void>; screenSource(): Promise<string | null>; screenSnapshot(): Promise<string>;
      publish(state: CompanionState): void; configure(config: { hotkey?: string; wakeEnabled?: boolean; wakeSensitivity?: 'normal' | 'sensitive'; controlEnabled?: boolean }): Promise<HostState>; testWake(): Promise<HostState>;
      showPalace(): void; showTasks(): void; showInvoiceDemo(): Promise<void>; command(command: CompanionCommand): void;
      runAction(action: DesktopAction, requestId?: string): Promise<DesktopActionResult>;
      stopAction(requestId?: string): Promise<void>; listApps(): Promise<string[]>;
      onCommand(callback: (value: CompanionCommand) => void): () => void;
      onState(callback: (value: CompanionState) => void): () => void;
      onHost(callback: (value: HostState) => void): () => void;
      onCursor(callback: (value: { x: number; y: number }) => void): () => void;
    };
  }
}
