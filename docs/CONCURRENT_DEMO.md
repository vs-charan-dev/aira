# AIRA two-job demo

Accepted sequence, 2026-10-08: create a Notion note, investigate a coding error concurrently, change the note title, show the verified coding result in VS Code, return to the note.

## Implementation checklist

- [x] Local SQLite task supervisor with separate desktop and coding lanes.
- [x] Long desktop requests return a job ID immediately; voice remains available.
- [x] Queue desktop input; never let workers type into different windows concurrently.
- [x] Follow-up instructions target an explicit job; apply after the current action finishes.
- [x] Pause/resume/cancel individual jobs and stop all jobs; preserve partial changes.
- [x] OpenCode worker uses the saved Gemini key, selected E-drive project and bounded execution.
- [x] Independent local test runner and before/after diff; distinguish diagnosis from verified fix.
- [x] Visible task board with genuine progress, job controls and project selection.
- [x] Open the selected project in VS Code through the same desktop queue (native result tracked below).
- [x] Automated concurrency, cancellation, connection ownership, restart and adapter tests.
- [x] Real isolated coding demo acceptance; no automated Notion page creation.
- [x] Build, restart AIRA, document commands and manual acceptance procedure.
- [ ] Complete the full spoken Notion + coding sequence with the user.
- [ ] Retest Show in VS Code after installed-app discovery fix.

## Verification evidence

2026-10-08: 58 backend, 37 frontend and 17 desktop checks passed (112 total); one opt-in native cancellation test skipped. Production build passed. OpenCode 1.18.35 ran with the saved Gemini key on the isolated data/projects/coding-acceptance-ecaaa40d project. Only invoice.js changed: two failed tests became three passing tests, independently rerun after correcting Node reporter parsing. The default data/projects/aira-demo fixture remains intentionally broken for the voice demo. The floating board, current project path and enabled Node runner were inspected in the native desktop app. Both actual Live receive loops were tested with accepted jobs surviving speech interruption, followed by explicit job cancellation. Quick app/folder requests join the same tracked queue; shutdown cancels running and not-yet-started jobs.

The first native Show in VS Code check truthfully failed because VS Code is installed outside standard folders. PATH/registered-app discovery was added and independently resolves E:\Microsoft VS Code\Code.exe. A subsequent native click was refused by the Computer Use helper's focus guard (the point was over another application), including one permitted activation/refresh/retry. No replacement UI input was sent. User retest is pending; the historical failed job is preserved. This is a UI verification limit, not evidence that the corrected launcher succeeded.

Actual simultaneous voice + Notion editing + coding, physical speech interruption, in-flight title change and complete pause/resume acceptance still require the manual script above. No additional Notion write was initiated. Earlier full desktop smoke issues with voice option population/wake feedback remain open in AIRA_PLAN.md; focused checks do not establish those fields.

Known first-adapter limits: only fixed Node/unittest runners; no model-driven shell/network/MCP/subagents; bounded text-file diffs (at most 1000 files/3 MB, 100 KB per file). Project .opencode directories are rejected. Worker permissions are not an OS sandbox, and local test code can do anything allowed to the Windows account. Reports can include project text and are stored locally. Worker token/cost metadata is in job reports and not combined with the main Usage panel. A diagnosis without selected tests is not a verified fix. Investigate mode denies edits; fix mode permits source edits while excluding test/config/secret patterns. Generic GUI follow-ups remain agent-reported, not independent proof of saved Notion state.

## Acceptance script

1. Select the demo project in the task board. Ask: "Create a Notion note titled AIRA Demo with content: AIRA helps me work across apps."
2. While it is running: "Fix the failing test in the selected demo project."
3. "Change the Notion task's title to Demo Plan." AIRA must identify the job and schedule a follow-up edit without creating another page.
4. "Show the coding result in VS Code." Display the project and inspect the actual test exit status/diff on the board.
5. "Open Notion." Inspect the page yourself. Notion persistence/server sync is not established by an agent's completion claim.
6. Test "Pause the coding task", "Resume the coding task", "Cancel the Notion task", and Ctrl+Alt+Escape. Cancellation stops future work; it does not undo changes.

Desktop actions take turns. Coding inference and fixed local tests can overlap desktop work. Live speech interruption stops speech, while explicit job cancellation stops detached work. All job history, worker state, reports and caches stay on E. Gemini receives the selected project context; local storage does not mean local inference.

OpenCode permissions restrict available tools but are not an OS sandbox. The first adapter denies model-driven shell commands and runs only a fixed test runner selected by the user. Start with a disposable demo project. Changes to the selected project are intentional and reviewable through a local diff.

Sources: [OpenCode CLI](https://opencode.ai/docs/cli/), [permissions](https://opencode.ai/docs/permissions/), [configuration](https://opencode.ai/docs/config/).

2026-10-09: use the dedicated [visual invoice demo](INVOICE_DEMO.md) for a
repeatable coding presentation. Its fresh fixture is
`data/projects/invoice-showcase`; the old `aira-demo` working copy is already
fixed. The new page shows live commands/test output, actual invoice evaluation,
before/after results, source diff and explicit reset. Real voice/concurrent
desktop acceptance remains with the user.
