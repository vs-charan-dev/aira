# AIRA desktop control — apps, folders and Notion notes

Launch `Start-AIRA-Desktop.cmd`, then use Ctrl+Alt+A or enabled Hey AIRA. During conversation, say **Open Notion** or **Open the folder E:\Havetobuild\AIRA**. Desktop → Desktop actions also has no-API test buttons. Installed-app discovery is local; the spoken request uses your existing Gemini Live session/key.

For notes, sign in to Notion manually and open a **private page** in the workspace you want to use. Say **Create a Notion note titled Demo checklist with content Prepare the Memory Palace demo.** AIRA creates a new private page, writes the title and plain-text paragraphs, and reloads that page to check them. Desktop → Desktop actions also has title/content fields and a **Create private Notion note · no Gemini usage** button. Each click creates a new note; it does not edit an existing page. Notion uses its own account and internet/sync service; AIRA's memory storage remains local. No Notion API key or extra AI inference is required.

Title limit: 160 characters, one line. Content limit: 2000 characters. This increment supports plain text paragraphs; Markdown transformations, databases, templates, existing-note edits, workspace switching and sharing are outside its supported workflow. AIRA does not claim independently verified server sync.

## Implemented and verified

- [x] Typed app/folder tools in both recall and capture, with results awaited before AIRA acknowledges completion.
- [x] Exact installed-app lookup; visible Start-button click/search; foreground verification. Real Notion launch passed on this laptop.
- [x] Local-folder navigation through Explorer's address field; actual Explorer location verification. Real E-drive project navigation passed.
- [x] Single native controller, visible progress, local enable switch and Ctrl+Alt+Escape emergency stop.
- [x] Cancellation on disconnect, session cancellation, owner crash, lock/sleep or exit. Real Start/search cancellation test confirms the input helper exits before completion.
- [x] Local app inventory and native IPC permission guards; no command text interpolated into a shell.
- [x] `create_notion_note` tool in recall/capture, bounded payload validation, visible title/body entry and matching page-ID/private-header checks.
- [x] Real Notion creation and private-page detection observed. A fixed synthetic note titled **AIRA verified demo 2026-10-08** was completed; title and two paragraphs matched after reload. UI transition failures were diagnosed with structural counts, not saved page contents.
- [x] Offline workflow checks cover non-private destinations, populated pages, focus failure, multi-paragraph content and reload loss; native smoke checks controls and blocked execution during smoke.
- [ ] One uninterrupted fresh-page run through the complete desktop wrapper and spoken acceptance. Additional persistent test creation was rejected by automatic approval review to avoid duplicate test pages. Creation and writing/reload were verified separately. Some blank test pages and the synthetic interface/demo notes remain in Notion; no existing page was edited or deleted.
- [ ] User voice acceptance, disable/restart acceptance and physical emergency-hotkey timing.

## Execution and limitations

Gemini selects `open_app`, `open_folder` or `create_notion_note`. The original palace WebSocket forwards the validated request through Electron's restricted IPC. A pinned Python UI Automation helper performs the fixed workflow, sends progress, verifies the result and exits. All request text travels as JSON on stdin. The controller uses no screenshots or extra inference calls. Note creation has a 90-second native timeout; observations retry transient Chromium accessibility failures, but the creation action is never automatically repeated. UI focus is checked before each typed character.

Notion-specific details: active-document selection uses the focused document ancestry because hidden tabs can remain in accessibility; title is an edit control with localized type `page title` and must be excluded from body paragraphs. The private indicator is inside a banner/header group. Ctrl+N can open a **Create new** menu, in which only the exact **Page** item is selected. Text is entered through normal keyboard input because UI Automation `SetValue` can change Chromium's display without committing Notion's editor state. Slash/mention suggestions are dismissed before paragraph breaks. Any ambiguity, inaccessible control, focus loss, nonempty new page or failed reload produces a failure, with partial-page warnings and no automatic retry.

Windows Search here exposes the search field but not its result control to UI Automation. The controller visibly searches first, then opens the exact application from Windows' installed-app catalog. Where an exact semantic result is available it can click that result. This fallback is deliberate and visible in the progress message. It never submits an unknown best match.

App names must match an installed display name (with a few browser/Explorer aliases). Known app processes or matching window titles verify completion; an app without a recognizable foreground window can fail verification even if it launched. Administrator prompts, locked desktops, changed focus, ambiguous names and unexpected dialogs can stop an action. No arbitrary executable arguments, shell commands, remote folders or file execution are supported. Folder paths must be supplied explicitly and already exist. Start/taskbar/accessibility behavior on other Windows builds/languages needs acceptance testing.

Ctrl+Alt+Escape stops actions and Live input/output. **Stop desktop action** stops only native input. Cancellation does not undo an app/folder already opened or a partial note. Inspect Notion before retrying. One action runs at a time. The emergency shortcut must register successfully before native actions are allowed.

Dependencies are pinned in `desktop/requirements.txt` and installed by `scripts/Setup-Desktop.ps1` into the existing `.venv` on E. Controller temp/COM/Python caches remain in the E workspace. SQLite, media, the Gemini key and the approved character are retained.

## Next increments

- [ ] Accept the new private-note workflow through voice, restart and emergency stop. Keep full acceptance open until observed.
- [ ] Change one explicitly requested Windows setting with observed state before/after.
- [ ] Expand UI interaction and optional vision-based recovery after these workflows pass.

These increments remain separate from the current launch/navigation tools. The general intention executor, browser agent and gesture controls are still pending in `AIRA_PLAN.md`.

## Developer checks

```powershell
. .\scripts\Environment.ps1
node --test desktop/tests/*.cjs
& .\.venv\Scripts\python.exe -m unittest discover -s desktop/tests -p test_notion_control.py -v
```

`inspect_notion` is a read-only CLI diagnostic, not exposed by Electron IPC. The explicit `desktop/tests/native-notion.manual.js` diagnostic creates a synthetic page and is excluded from automated tests. `native_notion_finish.py` can finish only an exact recorded blank/test-title page ID, and never creates a page; it is for recovering a manually authorized test, not an application tool. Neither manual diagnostic should be run merely to repeat already-passing validation. Native cancellation is skipped during `node --test`; run its script explicitly only when a real desktop input test is intended.
