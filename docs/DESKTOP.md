# AIRA on Windows

## Close an app and search Google Maps

Say “Close Calculator”, “Close Notion”, “Close VS Code” or the display name of
another ordinary app. AIRA closes only one uniquely matched window, including
a minimized window. It sends the normal Windows close request directly to that
window and verifies the window disappeared. Multiple matches leave all windows
open; a save prompt is left for you. Closing a window can leave a tray process.

Say “Go to Google Chrome, go to Maps and search for Hyderabad”, or “Search Google
Maps for Charminar, Hyderabad”. `search_maps` opens Chrome and Maps as needed,
submits the literal place/address and verifies that the visible Maps search box
contains it and a results list or place heading loaded. “Open Google Maps” uses
`open_maps`; a later place search uses `search_maps`. Results appear in a reusable
Maps tab in AIRA's E-drive Chrome profile; existing YouTube/invoice tabs remain.
No extra Maps API key is required by the [documented Maps search URL](https://developers.google.com/maps/documentation/urls/get-started).
Consent, network/site errors and unreadable results produce an attention result.

Both commands work in Capture and Recall voice modes, with desktop actions
enabled. Maps controls are also in desktop Settings. After updating, quit AIRA
from the tray and restart **Start-AIRA-Desktop.cmd** to reload the backend and
warm workers. If the backend was launched separately, restart that launcher too.

Acceptance: close one ordinary app (also try it minimized); confirm two windows
are left untouched; try closing an unsaved document and confirm AIRA leaves its
save choice to you. Then speak a Maps search for a real place and check the
visible results. Repeat a search while a YouTube video is open to check both tabs.
89 offline checks and the frontend production build passed. A temporary headless
Chrome check also passed against the real Maps page for “Charminar, Hyderabad”.
Actual spoken invocation and the visible native-window workflows still require
user acceptance.

Launch **Start-AIRA-Desktop.cmd** from the project root. Desktop setup is `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Setup-Desktop.ps1`. The resolved Electron version is pinned in `desktop/package-lock.json`. Its runtime, download, profile, sessions, HTTP cache, settings and logs live on E. Run under your normal Windows account to reuse the existing DPAPI Gemini key.

The launcher starts a hidden loopback backend only if needed and terminates only that owned backend when desktop exits. A separately running backend stays running. The palace owns the sole microphone, WebSocket, Live session and playback. The transparent character only observes state, output energy and global cursor coordinates, with no device permissions. Close the palace to hide it to the tray; **Quit AIRA** exits. Use the desktop palace for voice: opening a separate browser palace replaces the profile's WebSocket. `/character` remains safe to leave open.

## Activation and controls

- **Ctrl+Alt+A** activates conversation from another app while AIRA is running. Repeated activation during a session does not open another session. Under **Desktop**, change the shortcut and save; registration failure is visible.
- **Desktop actions** opens installed apps and existing local folders. Say **Open Notion** or **Open the folder E:\Havetobuild\AIRA** during conversation/capture. AIRA visibly clicks Start and types the app name, or opens Explorer and types the folder in its address bar. It reports success only after checking the foreground app or actual Explorer location. On this Windows installation Search does not expose its result control; after visible search, the controller opens the exact registered installed app. It does not click guessed result coordinates. Refresh installed apps and the app/folder test buttons use no Gemini calls. Voice requests use the existing Live session. No new API key is required.
- **Ctrl+Alt+Escape** stops native input and conversation/capture. The tray also offers **Stop all actions**. Stop desktop action stops only the current controller. An already opened app/folder can remain open after cancellation. Disable **Enable app and folder actions** to block launches and cancel running input; this preference persists. Actions also stop on transport loss, owner crash, lock/sleep or quitting AIRA. Only the palace can request native actions; the overlay is view-only. The controller serializes operations, rejects command shells/network paths, and pauses idle wake recognition while acting. See [DESKTOP-CONTROL.md](DESKTOP-CONTROL.md) for supported scope and acceptance.
- Expand **Desktop**, choose **Enable Hey AIRA**, and wait for `listening`. Wake is off initially. It uses Windows' installed English System.Speech recognizer with several pronunciation variants and a 0.70 confidence threshold. Idle wake recognition has no cloud STT, additional key, model download or Gemini session. It releases its microphone process before Live starts and rearms after the session/output ends. Real accent/noise accuracy and latency require testing.
- If activation fails, stop conversation/capture and choose **Test wake phrase · no API usage**. This runs the same local recognizer for 20 seconds, suppresses activation, and shows microphone level, speech/rejection counts and grammar-match confidence. Say Hey AIRA a few times; eye-rah and air-ah variants are included. No recordings or general speech transcripts are saved. After the test, normal idle wake resumes only if enabled; the result stays visible. A zero meter alone is inconclusive: check speech detections as well. No speech detections suggests an input problem; detections/rejections without a phrase suggest pronunciation/recognizer matching. A below-cutoff match can be retried with **More sensitive** (0.55 rather than 0.70); this setting persists and may cause more false activations. Disable and re-enable wake after changing/disconnecting a microphone so Windows' current default is reopened. Recognition now runs continuously with asynchronous events instead of repeated single recognition calls.
- Say **Switch to capture mode** for voice memories, **Capture this screen** for a native screen/window picker, **Switch to recall mode** for conversation, or **Stop capture**. Tools dispatch actual device actions; the character displays starting/active/error states. New Live starts only after device access succeeds. Screen capture requires source selection, not a title or summary. The selected view goes to Gemini while capture runs. Desktop currently uses microphone audio without system audio; browser shared-audio behavior is unchanged.
- In a browser, spoken screen requests show **Choose screen and start capture** because display capture requires a click. The request remains pending until you click and grant permission.
- Say **Disappear for 10 seconds** to slide down and return. Conversation/capture continue. Repeated requests replace the deadline; tray **Show character** or activation restores it early.
- **Stop conversation and capture** releases Live input, screen and queued playback. Enabled local wake listening resumes. For a completely released microphone, use tray **Pause all microphones**, or disable Hey AIRA and stop Live.
- **Audio output** is available under Desktop and Settings. Stop conversation/capture, select the laptop speakers (or Windows default), then **Test speaker · no API usage**. Two locally generated tones use the same PCM playback service as AIRA, without Gemini or microphone access. Speaker labels may become available after the first microphone permission; use Refresh speakers. Explicit selection lasts for this app run. A disconnected selected speaker falls back to Windows default. Audio output resets when the speaker inventory/default changes, discarding speech queued for the previous device. Ask AIRA to repeat an interrupted reply. **Reset audio output** also recovers a stalled output without restarting the microphone or Gemini session. Playback failures are visible here. If tones are silent, check Windows Settings → System → Sound, including the selected output and AIRA/Electron volume/mute/output override in Volume mixer. Input disconnection still stops Live and displays an error; reactivate after reconnecting or changing the default microphone.
- **Settings → AIRA voice** offers 30 prebuilt Gemini voices with style descriptions. Choose a voice, click **Preview “Hi Charan”**, and use **Save voice** to apply it to the next conversation/capture or new memory narration. Selection alone does not change the saved voice or API key. Stop conversation/capture before previewing. The first preview per model/voice/phrase version uses a short Gemini Live request; successful previews are cached on E under `data/media/voice-previews` and replay without a new API call, including after restart. The preview sends only the greeting, with no microphone/screen/memory data. Stop preview, changing voices, closing Settings or starting a conversation prevents late playback. An already-sent short generation may finish and cache after you stop playback. Provider errors appear in Settings; failed, incomplete or unexpected greetings are not cached. Existing Live sessions retain their voice until restarted.

Listening, speaking, working, screen/camera/voice capture, muted-session and error labels follow the real session/device/playback state. Mouth movement uses audible AIRA output. Working is driven by transcription/tool activity, not hidden model reasoning.

## Lifecycle

The overlay is click-through and never requests keyboard focus. It docks to the cursor monitor's Windows work area at launch/resume/display changes. Lock/sleep stops active input and wake; unlock/resume restores placement and rearms enabled idle wake. Live does not automatically resume. Hide duration uses a wall-clock deadline, so overdue return happens after resume. Wake settings and hotkey persist locally. No idle screen capture occurs.

Foreground app context, draggable monitor choice, advanced DPI/multi-monitor acceptance, gestures, installer/start-on-login and Live session resumption remain pending.

## Validation

Offline tests:

```powershell
node --test desktop/tests/wake.cjs desktop/tests/actions.cjs
. .\scripts\Environment.ps1
Set-Location frontend
node --test scripts/test-media.cjs scripts/test-playback.cjs scripts/test-mode-switch.cjs
node --test scripts/test-voice-settings.cjs
node --test scripts/test-desktop-actions.cjs
# From project root, under your normal Windows account:
.\Start-AIRA-Desktop.ps1 -SmokeTest
```

The native smoke test uses no microphone or Gemini session. It checks transparent character rendering, state IPC, global shortcut registration, E-drive paths and normal palace startup. The English recognizer probe verifies availability, not microphone accuracy.

Desktop setup also installs the pinned `uiautomation`/`comtypes` packages into the existing E-drive Python environment. Smoke checks installed-app inventory, emergency-stop registration, action controls and owner/overlay permission guards without sending native input. The explicit `node desktop/tests/native-cancel.cjs` diagnostic opens Start/search and cancels before app launch; run under your normal Windows account, without moving focus during the test.

User acceptance (short Gemini sessions use quota):

- [ ] Say Open Notion, then Open the folder E:\Havetobuild\AIRA. Verify visible Start/search or Explorer navigation, the correct final app/folder and one accurate reply. Test emergency stop, action disable and persistence after restart. Settings changes remain pending.
- [ ] With a signed-in private Notion page open, say Create a Notion note titled Demo checklist with content Prepare the Memory Palace demo. Verify one new private page, matching title/content after reload, and one accurate reply. Inspect partial pages before retrying a failure or stop. The desktop title/content button can test this without Gemini usage. See [DESKTOP-CONTROL.md](DESKTOP-CONTROL.md) for scope and current evidence.

- [ ] Launch desktop, switch to another app and press Ctrl+Alt+A. Hear one greeting, see listening/speaking and mouth motion.
- [ ] Stop; enable Hey AIRA and say it from another app. Verify one activation, wake latency and false triggers in quiet/noise.
- [ ] Run the local wake test with your voice. Verify speech detection, phrase confidence, test completion without Live activation, sensitivity persistence and subsequent real wake activation. Hotkey remains the fallback. A synthesized Windows-voice fixture validates code only, not accent/noise accuracy.
- [ ] Say “Look at this Notion page” with Notion visible. Confirm a relevant answer without a chooser or mode switch. Say “Capture this screen” separately; confirm the active continuous-capture label and monitor under the cursor. Stop must release capture. Browser sharing still requires its native chooser.
- [ ] Say Switch to recall mode, then Stop. Confirm one voice owner, no trailing/duplicate playback and no screen sharing. Use Pause all microphones and check the Windows microphone indicator clears.
- [ ] Say Disappear for 10 seconds. Check downward/upward motion and tray recovery.
- [ ] Verify lock/sleep/resume, monitor/taskbar/DPI changes, click-through and keyboard focus.

### Screen viewing and desktop status

In the Windows desktop app, “Look at my screen”, “Read this page” and “Can you look at this Notion page?” request one current-monitor JPEG in the existing conversation. The monitor under the cursor is selected automatically. Keep the relevant app visible; the snapshot cannot see a hidden page or retrieve an unopened URL. There is no second permission dialog. The snapshot is held in memory and sent to Gemini Live using the existing key; this uses inference quota. This tool does not save a Memory Palace artifact or start continuous sharing. Ask again for an updated view.

“Capture my screen” starts continuous memory capture on that monitor without an Electron chooser. The browser version still uses the browser's required sharing picker. Stop or Ctrl+Alt+Escape ends the session/capture; screen-view replies arriving after stop, disconnect or session replacement are ignored.

The Desktop summary now separates **Controls on/off** from **Hey AIRA ready/off/paused**. “Hey AIRA paused during activity” is expected while a conversation/capture/action owns the microphone. Stop preserves both preferences, then enabled local wake listening resumes. Ctrl+Alt+A starts a conversation regardless of whether wake listening is enabled. Turning the Enable desktop actions checkbox off remains an explicit setting; Stop does not turn it off.

Windows-Use is installed in `.runtime/windows-use` on E, separately from the backend environment. It uses the saved Gemini key for GUI tasks; closing an ordinary app uses no inference. Worker history is `data/db/desktop-actions.sqlite3`; token totals there are not yet combined with the main Usage panel. The GUI-only tool policy blocks shell/file tools and a range of destructive tasks, but is not an OS sandbox. The app never force-kills an application or discards unsaved work; background processes may remain after a window closes. Actual Notepad/Notion/settings voice acceptance remains tracked in `AIRA_PLAN.md`.

Common desktop actions now use a warm direct-control worker; unfamiliar GUI tasks
use a separately warmed Windows-Use worker. Open apps/folders and close windows
avoid desktop inference. “In Notepad, append the text Hi Charan” uses focused-editor
readback without saving. The installed-app inventory is cached, and fixed Search/
Explorer delays have readiness checks. The desktop queue remains exclusive;
cancellation terminates its active worker before another action begins. See
[FAST_DESKTOP.md](FAST_DESKTOP.md) for implemented checkboxes, restart steps and
user acceptance. Timings displayed in Desktop/Tasks exclude voice recognition and
backend scheduling. This increment was built without running tests at the user's request.

The latest increment replaces the Notepad append demo with **Notion** because
Notepad is not installed. Use “In Notion, append the text AIRA is ready” with the
intended private page open. “Calculate 78 times 87 in Calculator” uses direct
visible buttons and readback; “Open my Desktop folder” resolves the real Windows
folder. Microphone freshness, a local voice-status probe and reconnect feedback
replace stale Listening state on the identified failure paths. See
[NOTION_CALCULATOR_FIXES.md](NOTION_CALCULATOR_FIXES.md) for current restart/testing
steps and pending acceptance. Earlier Notepad guidance is superseded.

### Interrupting AIRA

“Interrupt AIRA while speaking” now defaults on if no preference is saved. A previously saved off preference is respected; enable the checkbox in Desktop/Settings → Speaker to speak over a reply and give a different instruction, including during the greeting. Microphone echo cancellation/noise suppression remain enabled. If speaker echo cuts off replies, headphones or disabling conversational interruption remain available.

In the Windows desktop app, **“Stop AIRA”** or **“Cancel AIRA”** uses an English local recognizer during a conversation, narration or desktop action. It stops the session/playback and cancels desktop input without waiting for Gemini or a tool result. The Desktop controls show whether this listener is starting, ready or unavailable. Wake listening is replaced by the stop grammar during activity, then resumes while idle if enabled. Only one local recognition worker runs; the Live microphone continues separately for conversation. No local microphone recording or extra inference request is created by this recognizer. Pause all microphones ends the session and disables idle wake as before.

Stop phrases depend on microphone quality, pronunciation and speaker echo; **Ctrl+Alt+Escape** remains the immediate global stop. Ordinary conversational interruption depends on Gemini detecting speech. A local stop ends the conversation; use Ctrl+Alt+A/Hey AIRA to start again. Cancelling desktop work does not undo clicks, typing or writes that already happened; inspect partial changes before retrying.

Live tool execution is ordered but no longer blocks the receive loop. Provider interruption/tool-cancellation messages cancel active and queued voice-owned tool tasks. Accepted tracked jobs survive ordinary speech interruption so you can issue another instruction. Explicit task cancellation, Stop AIRA, Ctrl+Alt+Escape, connection loss and shutdown cancel tracked work; partial changes remain. Some background memory/image generation is outside the task supervisor.

### Two-worker task board

Open **Tasks → Float board** in Memory Palace, or **Show task board** from the AIRA tray menu. It stays visible beside other applications. Select the coding project and Node/unittest/diagnosis-only runner under Coding project. The default fixture is E:\Havetobuild\AIRA\data\projects\aira-demo; scripts/Setup-Demo.ps1 creates it without overwriting an existing project. scripts/Setup-Coding.ps1 installs pinned OpenCode 1.18.35 locally on E.

Try “Create a Notion note…” followed by “Fix the failing tests in the selected project.” Long GUI/coding jobs return task IDs immediately. Desktop input is queued through one controller; code inference and local tests run in the other lane. Say “List my tasks,” “Change the Notion task's title to Demo Plan,” “Pause the coding task,” “Resume the coding task,” “Cancel the Notion task,” or “Show the selected project in VS Code.” AIRA must obtain the matching ID and ask if several tasks match. A follow-up waits until the current worker action finishes. Pausing native work can leave a partial note; resume inspects it and avoids repeating creation.

Investigate mode denies edits; fix mode allows source changes. The model cannot run shell commands. AIRA runs the selected fixed test runner independently and displays actual exit, nonempty suite checks, changed text files and a before/after diff. Review these results: passing selected tests does not prove every behavior. Node runs with the TAP reporter for consistent counting. Tests execute trusted project code under your Windows account; the adapter is not an OS sandbox.

Jobs/settings/reports persist in data/db/tasks.sqlite3. OpenCode home/state/cache live under data/coding and .cache/coding, and the saved key is supplied only in the worker environment. Blank AIRA_CODING_MODEL uses google/GEMINI_STANDARD_MODEL. No additional API key or cloud storage is required; Gemini still receives project context. Restart never automatically retries unfinished jobs. Ordinary speech interruption leaves accepted jobs running; use task-specific cancel or stop-all to end work. Local Stop AIRA is armed during active conversation/desktop input; when only a background coding job remains, use the task board or Ctrl+Alt+Escape. Ctrl+Alt+A can start a conversation while desktop work is underway.

Full acceptance script and checked implementation plan: docs/CONCURRENT_DEMO.md. Native voice/Notion sequence remains a manual test, following the user's choice to test persistent Notion writes personally.
- [ ] With Bluetooth disconnected, choose laptop speakers and hear both local test tones, then hear AIRA's greeting/reply. Reconnect/disconnect Bluetooth during playback; verify fallback to speakers and a subsequent audible reply, with no stale queued speech. Physical audibility is separate from successful Web Audio scheduling.
- [ ] In Settings, audition at least two different voices saying Hi Charan. Replay a voice and check the cached label/no added API call; save one, restart a conversation and capture, verify the chosen voice, then verify persistence after desktop restart. Provider acceptance/actual voice differences require real Gemini playback; offline SDK fixtures do not prove them.
