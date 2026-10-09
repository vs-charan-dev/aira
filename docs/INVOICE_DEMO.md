# Invoice presentation and repeatable fault

Updated 2026-10-09. The application runs locally at
`http://127.0.0.1:8000/invoice-demo`, using the same backend as AIRA.
Its real project is `E:\Havetobuild\AIRA\data\projects\invoice-showcase`.
The earlier fixed `aira-demo` project is separate and preserved.

## What the judges see

Invoice Studio is an ordinary invoice application with an amount, percentage
discount and total. It has no repair instructions, expected-answer panel,
fix button or test dashboard. With the faulty source, **₹200 and 10% off
produce ₹190**. Explain the observable problem: ten percent of ₹200 is ₹20,
so the invoice should total ₹180. You can also use ₹1,000 and 10%:
the faulty total is ₹990 and the corrected total is ₹900.

The preview executes the actual `invoice.js` in a bounded local Node process.
The displayed wrong/correct values are not swapped UI labels. Changing the
source changes the calculation; the app notices within its polling cycle.

## Rehearsal

1. Quit AIRA from the tray and run `Restart-AIRA-Desktop.cmd` once to load
   this revision. Keep the backend and desktop running.
2. Finish or cancel active coding jobs, then double-click **Create-Fault.cmd**.
   It restores the known faulty calculation and verifies the actual output
   is 190 for the standard inputs. Read the terminal result before continuing.
3. Say **“Hey AIRA, show the invoice demo.”** This opens Invoice Studio in
   its dedicated **Google Chrome localhost tab** and registers its known project.
   Keep the default ₹200 / 10% inputs for the
   presentation. This opening request never resets or repairs the project.
4. Show the wrong total, then say **“AIRA, the application in my VS Code is
   giving the wrong total. Go to VS Code and fix the error.”** You can describe
   the discount problem without dictating the filename or formula.
5. AIRA opens the real **invoice.js in VS Code**, checks the faulty source
   against the five unchanged tests, applies the configured repair and writes
   **invoice.regression.test.js** with three new regression cases. All eight
   checks run locally; AIRA then shows the new test file in VS Code and launches
   its fixed process task in the **integrated terminal**. The real output ends
   with **“All tests passed (8/8).”** only if all checks pass. Editor or terminal
   failure prevents a successful presentation return. If VS Code shows a
   workspace trust prompt, review and trust this known demo folder once during
   rehearsal; AIRA does not bypass that prompt. The standard Ctrl+Shift+B
   binding must launch the configured default task.
6. After terminal verification, AIRA brings the existing Invoice Studio tab forward.
   It retains your inputs and recalculates the total from the repaired source:
   **₹180**. An existing active recall conversation receives a short cause
   explanation. A stopped/lost voice connection is not restarted automatically.
7. For another rehearsal, finish the job and run **Create-Fault.cmd** again.
   **Fix-Fault.cmd** applies and verifies the same repair manually; it does
   not perform the voice-driven editor/window sequence. Both helpers work
   without the backend running, but do not start the localhost server.

You may delete **only the two root .cmd rehearsal launchers** before the
presentation. AIRA's voice repair does not depend on them. Keep the backend,
`scripts`, demo template, working project, tests and marker intact.

Developer evidence is available in Tasks and at
`http://127.0.0.1:8000/invoice-workbench`: before/after test output, commands,
timestamps, real source diff and verification tied to the source hash. The
separate workbench also supports reset. If a separate browser reports
**Local session expired**, use **Open local session** there; this page opens
no voice/WebSocket connection and does not replace the desktop conversation.
The ordinary invoice page automatically establishes/reopens its local cookie
session when needed. It does not require a Google login.

## Invoice and YouTube together

Both use AIRA's persistent Chrome profile on E:, in **separate tracked tabs**.
Showing the invoice reuses its tab without reloading inputs; YouTube search
and video opening use the YouTube tab. Neither navigation replaces the other.
NotebookLM remains a separate tab as well. A request for the selected video
URL retains the last selected YouTube tab when the invoice or AIRA has focus.
You can demonstrate invoice repair, then YouTube, in one AIRA run. A closed tab
is recreated on the next matching request; no separate restart is required.

## What is deterministic

**Yes, this known-bug presentation uses a scripted repair by default.**
`AIRA_INVOICE_REPAIR_MODE=deterministic` selects an exact transformation of
the recognized invoice fault. It edits the real source from flat subtraction
to percentage subtraction and runs real independent tests before and after.
It makes no OpenCode/Gemini coding inference call. It also handles an already
fixed file without pretending to change it. Unknown source, altered tests or
package configuration, an old reset generation or another project are refused.
The three new regression cases are also scripted for this known bug. Original
tests remain unchanged. Create-Fault and workbench reset remove only recognized
generated tests/task configuration so the next repair visibly writes them again.
Modified generated files or existing unrelated VS Code configuration are preserved
and cause refusal. The terminal task cannot accept an arbitrary shell command.
It follows [VS Code's process-task/default-build mechanism](https://code.visualstudio.com/docs/debugtest/tasks).

Generic `coding_task` fix requests for the registered invoice project use
this same repair and presentation sequence. Other configured projects still
use OpenCode. The optional `AIRA_INVOICE_REPAIR_MODE=agent` setting restores
OpenCode investigation for this project after a restart; it is not the default
rehearsal path. The developer workbench identifies the configured mode.

This demonstrates voice-triggered orchestration, actual code changes,
verification and a corrected live application. It does not demonstrate
general autonomous diagnosis of an unseen bug. Arbitrary already-open VS Code
projects still need a configured filesystem path.

The repair algorithm is fixed; voice transcription/tool selection, Gemini Live
availability, VS Code installation/window focus and local process startup
still require a live rehearsal. There is no guarantee that desktop/voice
conditions cannot fail. Source changes appear through VS Code's file watcher;
AIRA does not simulate a person typing the repair. All files, test output,
history and caches remain on E:. Voice still uses the saved Gemini key.

## Implementation and acceptance checklist

- [x] Ordinary localhost app with a real faulty calculation and no solution hints.
- [x] Known project mapping and actual source opened in VS Code before repair.
- [x] Exact known-bug source repair with no coding inference.
- [x] Five unchanged baseline checks plus a newly written file with three regression tests.
- [x] Real eight-test VS Code terminal run with result tied to run ID and source hash.
- [x] Dedicated Chrome localhost tab, separate YouTube navigation and tab reuse.
- [x] Return to the app only after verification; preserve inputs and refresh source.
- [x] Short cause explanation in an existing recall voice session.
- [x] Repeatable Create-Fault.cmd and Fix-Fault.cmd independent of voice repair.
- [x] Windows file lease and read-only live-job guard for rehearsal mutations.
- [x] Refuse unknown code, changed tests/config, another project and stale generation.
- [x] Offline checks and production frontend build.
- [ ] User rehearses wrong total → voice request → VS Code → corrected app.
- [ ] User confirms spoken explanation and repeats fault/repair using the launchers.
- [ ] User deletes optional launchers and confirms voice repair still works.
- [ ] User accepts generated test file → visible terminal pass result → localhost tab return.
- [ ] User searches/opens YouTube in the same session and confirms the invoice tab remains intact.

Verification: six deterministic/helper tests use temporary E-drive projects,
real Node evaluation and five-before/eight-after test runs. A real terminal-runner
check covers actual passing and failing code, stale result rejection and task
boundaries; a native-editor check mocks GUI input and verifies the fixed shortcut.
Sixteen supervisor, two task API, five preview/fixture, one notification,
thirteen browser, four NotebookLM and eleven IPC checks cover ordering, failure
handling, existing-session behavior and tab isolation. Native GUI/voice/site
interactions are mocked. Frontend TypeScript and production build passed:
`index-Ck9FlQ-o.js`, `index-C0-4sU1I.css`. No live GUI or inference acceptance
run was performed by Codex. The working presentation fixture remains faulty.

Dispatch correction on 2026-10-09: the native warm worker now accepts
`show_invoice_demo` and `run_invoice_tests`. Both were previously missing from
its action list and failed before reaching Chrome or the editor. Three new
offline checks exercise the actual server/native routing functions with mocked
UI I/O, including rejection of unknown actions and GUI-worker isolation. The
44 focused dispatch/browser/IPC/supervisor/editor checks passed. Quit AIRA through
its tray and restart the desktop host before rehearsing the spoken command so
the already-running worker loads the corrected action list.
