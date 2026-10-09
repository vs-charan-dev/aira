# Explicit interruption and navigation follow-up — 2026-10-08

## Evidence

The latest local history records a successful direct Calculator operation
(`90 * 47 = 4230`). Notion is present in Windows' installed inventory as
`com.electron.notion`; its failed open was a Search-input readback failure,
not evidence that Notion was uninstalled. Desktop navigation was sent but failed
final folder verification. We have not established whether the path was dropped
or the old URL-only check missed the location on the user's machine.

## Implemented

- [x] Default to explicit-stop mode, including migration from the old enabled
  speech-interruption preference. Recall and capture configure Gemini Live with
  `NO_INTERRUPTION`; playback gates microphone forwarding to avoid speaker echo.
  Other instructions should be spoken after AIRA finishes its reply.
- [x] Retain optional speech interruption in Settings. It only interrupts speech,
  not accepted desktop jobs. Changes to provider behaviour require a new voice
  session. Lower speech-start sensitivity, 350 ms speech-start commitment and
  650 ms silence ending apply to both Live agents.
- [x] Local stop grammar includes **Hey AIRA, stop doing the work that you are
  doing**, **Hey AIRA, stop what you are doing**, **Hey AIRA, stop the current
  task**, and existing **Stop AIRA**, with supported name pronunciations.
  No dictation grammar or standalone `the`, `he`, `hello`, `leave` stop trigger.
  Overall confidence threshold is 0.80; weak word matches and sub-300 ms audio
  are rejected. Recognition remains probabilistic and requires a physical check.
- [x] Prompt does not infer desktop actions or cancellation from isolated filler
  fragments. This is a model instruction, not a transcript-based hard filter.
- [x] Notion/app opening waits briefly for asynchronous Search text readback and
  uses the exact inventory AppID if the query was not received or the result is
  unavailable. It never clicks a different best match. Focus changes still stop
  the launch. Installed inventory lookup and foreground verification remain.
- [x] Folder opening resolves the known Desktop path and navigates the observed
  Explorer window using `Navigate2`, instead of typing into the address bar.
  It verifies the final filesystem folder through `Folder.Self.Path` or a file
  URL. Multiple interfaces for the same window stop instead of selecting a tab.
- [x] Python/JavaScript/PowerShell syntax checks and frontend TypeScript/Vite build
  passed (`index-unOuYCMi.js`). No live mic, native input, paid inference or test
  suites run for this increment, respecting the user's manual-testing preference.
- [ ] User acceptance: false interruptions, long named stop request, Notion launch,
  actual Desktop contents, and new commands after task completion.

## User acceptance

1. Quit AIRA from the tray and relaunch **Start-AIRA-Desktop.cmd**. Restart a
   separately managed backend too. The new Settings checkbox is off by default.
2. Ask for a spoken reply. Say `hello`, `the`, `he` or `leave` while AIRA talks:
   those fragments should not cut off its reply or cancel a desktop job.
3. During work, say **Hey AIRA, stop doing the work that you are doing**. The local
   recognizer should stop the conversation and all desktop/coding jobs. It waits
   for a recognised phrase; it does not act on the first sound. Inspect any
   partial changes. Use Ctrl+Alt+Escape if recognition misses, then Ctrl+Alt+A to
   start a fresh conversation. Stopping does not roll back prior actions.
4. Say **Open Notion**. If Search input is dropped, the installed shortcut should
   launch it and the foreground Notion window should be verified.
5. Say **Open my Desktop folder**. Verify its contents and location, not merely
   that File Explorer appeared. Use a single-tab Explorer window if the controller
   reports multiple tab interfaces.

Sources: installed Google GenAI SDK `types.py` for supported Live settings;
[Gemini Live capabilities](https://ai.google.dev/gemini-api/docs/live-api/capabilities)
for provider voice behaviour;
[Microsoft Navigate2](https://learn.microsoft.com/en-us/previous-versions/aa752134(v=vs.85))
for Shell folder navigation.
