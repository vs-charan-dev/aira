# Notion, Calculator and voice availability — 2026-10-08

Latest interruption defaults and revised Explorer/Notion launch behaviour:
[EXPLICIT_STOP_AND_NAVIGATION.md](EXPLICIT_STOP_AND_NAVIGATION.md). Its acceptance
steps supersede the interruption/navigation steps below.

User reported: Notepad unavailable; Calculator opened but calculation failed;
another spoken command received no response while AIRA displayed Listening.
User will perform testing. No test suite, native app input, microphone session,
Notion write or paid inference was run for this increment.

## Findings

Local action history records Notepad inventory failure, Calculator launch with
unverified foreground, and Calculator desktop_task reaching its limits. This
confirms those controller failures, not the exact cause of the unresponsive
microphone. We found independent voice-lifecycle gaps: a receive-loop callback
failure could end the backend session without frontend notification; audio-send
failure could mark a session closed while frontend still believed it connected.
The microphone graph also had no output connection; a silent sink and stream
watchdog now make that path explicit and observable.

## Implemented

- [x] Replace direct Notepad append and demo defaults with Notion in both voice
  agents and Desktop controls. `type_in_app(app_name=Notion,text=...)` appends exact
  plain-text paragraphs to the currently open private page, retains its identity,
  title and previous body, verifies focus and reads back the expected content.
  It never creates a page or claims server sync. Multiple windows require the
  intended page to be foreground. Incomplete append cannot be blindly resumed;
  inspect the page before making another explicit request.
- [x] Improve Notion observation: native bulk visibility query, fallback for a
  document name that differs from its window title, and fresh Create new menu
  observation instead of traversing an old page's COM tree. Once Ctrl+N is sent,
  failures warn that a partial page may remain. No automatic write retry.
- [x] Add `calculate_in_app` direct tool/button. Accept two nonnegative decimal
  operands and one basic operator; no shell, eval, functions or arbitrary code.
  Select Standard mode, resolve visible button IDs, click the expression and
  compare the result display with an independent Decimal calculation.
- [x] Recognize Calculator's executable variants and UWP host by its visible
  result control, instead of one process-name assumption. Apply this to launch,
  close and generic Windows-Use target checks.
- [x] Resolve Desktop/Documents/Downloads using Windows Known Folder APIs, including
  redirection; no invented C-drive username or hardcoded OneDrive path.
- [x] Preserve one exclusive desktop queue while voice remains available. Prompt
  explicitly accepts new commands and briefly acknowledges queued work. Explicit
  “instead” / “stop that and” commands cancel the matching job first; normal extra
  commands queue rather than silently cancelling existing work.
- [x] Keep the microphone worklet connected to a zero-gain output sink. No local
  mic playback. Report a stream stall after six seconds; stop/release that failed
  voice session and allow Ctrl+Alt+A recovery.
- [x] Show actual microphone-send freshness rather than deriving Listening only
  from nominal session status. Throttle UI telemetry to avoid per-chunk renders.
- [x] Correlate voice startup/audio/liveness with a client session ID. A local
  three-second status probe detects ended backend sessions without another model
  request. Unexpected lifecycle exit notifies the matching client. Old status
  replies cannot stop a replacement voice session. Audio sends are timeout-bounded.
- [x] On voice failure, show reconnect feedback. Accepted desktop jobs remain on
  the same authenticated connection/task board; ordinary speech interruption does
  not cancel them. Ctrl+Alt+Escape still stops the session and all jobs.
- [ ] User acceptance: real Notion editor, correct Calculator result, new command
  acknowledgement, microphone operation behind foreground apps, and recovery.
- [ ] Automated/native regression checks for this increment.

Frontend TypeScript compilation and Vite production build passed. This is a build
check only; it does not validate the native controls or voice behaviour above.

## Restart and user testing

Quit AIRA from its tray menu and relaunch **Start-AIRA-Desktop.cmd**. This loads the
new Electron, frontend and launcher-owned backend code. Restart a separately
started backend too. Closing only the Palace window does not restart the owner.

1. Open an ordinary private Notion page you want to edit. Activate AIRA, then say
   **“In Notion, append the text AIRA is ready.”** Check the body yourself. Use the
   Desktop button to compare direct execution with voice delay. Existing content
   should remain; if readback fails, inspect any partial text before retrying.
2. Say **“Calculate 78 times 87 in Calculator.”** The direct tool can open Calculator
   itself. Verify the visible answer is **6786**. You can also first say Open
   Calculator, then 78 times 87. Use the Calculate visibly button for the same
   expression without voice or desktop-agent inference.
3. Say **“Open my Desktop folder.”** Verify the actual Windows Desktop location.
4. During a longer GUI task, give that folder command. Expect a short queue
   acknowledgement. Say **“Stop the current desktop task and open my Desktop
   folder instead”** to explicitly replace it. Partial changes are not undone.
5. Keep Notion/Calculator foreground while talking. AIRA should receive the next
   command. If the mic/Live connection fails, expect explicit reconnect feedback,
   not a persistent Listening label; press Ctrl+Alt+A and repeat the command.

Notion direct entry currently requires a readable private plain-text page. It
does not promise support for databases, shared pages or arbitrary rich blocks.
An unidentified UI stops before guessing. Calculator direct arithmetic is
limited to two nonnegative decimal operands (12 integer / 8 fractional digits)
and one operator; division is checked within 1e-12 relative/absolute tolerance.
Other GUI tasks retain Windows-Use. An unresolved generic task can still be slow.

The microphone/status changes cover identified failure paths; they do not prove
the exact cause of the user's original silence or microphone recognition accuracy.
Background noise, provider VAD and hardware routing still require physical testing.

References for the fixed controls and folder identifiers:
[Microsoft Calculator source](https://github.com/microsoft/calculator/blob/main/src/Calculator/Views/Calculator.xaml),
[Windows known folders](https://learn.microsoft.com/en-us/windows/win32/shell/knownfolderid),
[Gemini Live session management](https://ai.google.dev/gemini-api/docs/live-api/session-management).
