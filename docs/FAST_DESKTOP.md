# Fast desktop actions — implementation, 2026-10-08

**Current update:** Notepad is not installed on this machine. The direct append
tool and demo now target **Notion**. Use the commands and acceptance checklist in
[NOTION_CALCULATOR_FIXES.md](NOTION_CALCULATOR_FIXES.md); the Notepad details below
describe the first implementation and are superseded.

User priority: one quick, reliable task first; use parallel coding only for work
that naturally takes longer. The user will perform acceptance testing. No tests,
desktop actions, microphone sessions or Gemini requests were run for this increment.

## Implemented

- [x] Keep two sequential JSON-line workers initialized on E: direct Windows
  controls and Windows-Use. Warming imports dependencies and caches installed-app
  metadata; it sends no desktop input and makes no model call.
- [x] Reuse worker processes across successful actions. Each unfamiliar GUI task
  still constructs a fresh agent and reads the current Gemini key.
- [x] Use one shared desktop queue. Cancellation kills the active owned worker;
  the queue waits for process exit before allowing another action. Quit ends both
  idle/active workers. Failed workers restart on a subsequent request, never replay
  a previous action automatically.
- [x] Direct open-app/open-folder/close-window actions require no desktop inference.
  Opening apps still uses visible Start/search, except an already foreground app.
  Closing requires one matching window, sends Alt+F4 and checks disappearance;
  save prompts stop completion and background processes may remain.
- [x] Add `type_in_app` to both voice agents: append exact user text to foreground
  Notepad, require a unique visible editor, check focus and read back the expected
  result. No automatic saving or selection replacement. Other editors and complex
  text edits retain Windows-Use. A request to open Notepad and type schedules both
  tools in the same ordered desktop lane.
- [x] Cache app inventory for five minutes; Refresh installed apps refreshes it.
  An unknown app triggers one inventory refresh before returning a failure.
- [x] Replace Start/search and Explorer-address fixed waits with bounded readiness
  checks. Shorten direct name/path typing delay; retain focus checks and verification.
- [x] Prefer direct tools and one short spoken acknowledgement for common requests.
- [x] Remove the blanket Windows-Use instruction prohibiting all existing-note edits;
  an exact user-requested edit is allowed within the existing task scope.
- [x] Show elapsed desktop time and first dispatched input in Desktop controls and
  tracked jobs. Record queue/startup/input/execution/total metadata locally.
- [ ] User acceptance: speed, correct target, accurate text readback, stop, repeat
  requests, generic GUI fallback and voice routing.
- [ ] Automated checks of this changed worker protocol and native workflows.
- [ ] Full end-of-speech to first-visible-action timing. Current timing starts at
  the Electron desktop command, excluding Live speech recognition/inference and
  backend task scheduling. Do not compare it to a full voice-response stopwatch.

## Restart and manual acceptance

Quit AIRA from its tray menu, then double-click **Start-AIRA-Desktop.cmd**. Quit
also lets its launcher close the backend it owns, so the new voice tools load on
restart. If you started the backend separately, restart that backend too. Merely
closing the Palace window can leave AIRA running with the old code.

Workers initialize in the background. The first request immediately after startup
or cancellation can include initialization time. Actual speed is not yet measured.

Try these separately, in order, with Ctrl+Alt+A:

- [ ] “Open Notepad.” Correct app opens visibly; a repeated request while foreground
  should acknowledge the existing window without another Start/search sequence.
- [ ] “In Notepad, append the text Hi Charan.” Read the text yourself. It is appended
  at the end and verified; it is not automatically saved.
- [ ] “Open the folder E:\Havetobuild\AIRA.” Verify Explorer's location.
- [ ] “Open Calculator”, then “Close Calculator.” Verify its window closes.
- [ ] “Open Notepad and type AIRA is ready.” Verify ordered opening and one append.
- [ ] Try a more complex ordinary GUI request through Windows-Use. The generic
  worker is still bounded to one target app; this increment does not implement
  arbitrary multi-app plans, screenshot fallback or microphone-noise calibration.
- [ ] Start a longer task, press Ctrl+Alt+Escape, then issue a fresh command.
  Inspect any partial changes; cancellation does not undo committed work.

To separate voice delay from execution delay, use **Desktop actions** buttons for
the same operations, then compare with the spoken commands. Direct Notepad typing
uses the foreground Notepad window or focuses a unique visible Notepad window.
With multiple windows, bring the intended document forward first; it refuses to
guess which document should receive text.

Timings are visible after a command in Desktop controls and Tasks. Metadata-only
JSON lines are stored at `.cache/desktop/action-timings.jsonl`, rotating at 5 MB to
one previous file. No transcript, text, screen tree or key is stored in that timing
file. Action history remains `data/db/desktop-actions.sqlite3`, with real worker
start/end for new actions and execution metadata. Old historical timestamps are
not retroactively repaired. All storage stays under this E-drive project.

Voice still uses Gemini inference. Direct actions remove additional desktop-agent
model calls, not Live voice costs. Unfamiliar tasks may still take longer; no
latency guarantee is claimed until the user measures actual runs.
