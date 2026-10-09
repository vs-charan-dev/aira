# Video summary → Notion and video → NotebookLM mind map

Implemented 2026-10-08. Real account writes and generation remain for user acceptance.

## What the logs showed

The saved video summary succeeded (`39a32fcc78`). Its complete file is
`data/media/youtube/jobs/39a32fcc78/summary.md`. Two subsequent Notion actions
(`57e4a339c8`, `1acef01361`) failed in AIRA's local private-only checks **before
typing or creating anything**. The model also supplied only a one-paragraph
overview to those actions. Neither failure proved a Notion server permission denial.

Earlier log entries include `audio_send_timeout`, followed by a Gemini Live
opening-handshake timeout. The most recent logged study/export attempt has no new
transport exception. Existing bounded voice recovery remains in place; a provider
or network outage is not fixed by changing Notion permissions. The new task-board
buttons do not require a Live voice session. Accepted jobs are independent of
speech interruption; closing the AIRA connection or stop-all cancels them.

## Implementation checklist

- [x] `export_summary_to_notion` resolves an owned successful study job and reads
  its complete saved summary file. Missing/incomplete summaries fail explicitly;
  no fallback to an older summary while the latest requested one is pending.
- [x] Retain title, overview, source URL, every point and caveat as text paragraphs.
  Remove Markdown presentation markers that could trigger Notion typing shortcuts.
  No summary regeneration, model-authored paraphrase or silent truncation.
- [x] New page in the selected Notion desktop workspace, with a requested/default
  title; require the new page to be empty and editable before entering content.
- [x] Append to the selected existing editable page, preserving its title/body.
  An optional exact page title uses Notion search and stops on ambiguity or changed UI.
- [x] Private, shared and workspace pages use editor editability rather than a
  Private badge. Read-only/locked pages stop; AIRA never changes permissions.
- [x] Read back the expected complete title/body and check again after reload.
  This does not independently prove Notion server synchronization.
- [x] Up to 20,000 summary characters; Unicode input in bounded 16-unit batches,
  with window/editor focus checked between batches. Other direct typing retains
  single-character focus checks. IPC handles Unicode and the larger bounded payload.
- [x] `notebooklm_mindmap`: create a new notebook by default; optionally use a
  specified notebook link or one unambiguous already-open AIRA notebook.
- [x] Use the owned, signed-in AIRA Chrome profile on E:, navigate to NotebookLM,
  observe Sources/Studio, fill/submit the video URL, wait for one imported source,
  select that source, find the Mind Map control, wait for a new mind-map artifact,
  open it and require a visible diagram with multiple labeled nodes.
- [x] Support `notebooklm.google.com` and observed `notebook.google.com` redirects.
  The user's current shared notebook exposes Sources/Studio but no Add sources
  or generation controls. Do not assume that a shared view is writable.
- [x] Source import and generation have progress and bounded waits. Missing,
  disabled, ambiguous, login or changed-layout controls stop with actionable text;
  no guessed coordinates or model-generated page scripts.
- [x] Return destination title/page ID and notebook URL in durable task results.
  Retain a created notebook link on a partial failure when available.
- [x] Serial desktop queue, cancel/stop support and request-ID deduplication.
  A started/partial export or mind-map task cannot be resumed to repeat writes.
- [x] Task-board export and NotebookLM buttons; destination reports display
  actual completion/review status, separate from coding test reports.
- [x] Offline backend/native/IPC regressions and production frontend build.
- [ ] User accepts a full new-page Notion export after desktop/backend restart.
- [ ] User accepts an existing-page append with previous text preserved after reload.
- [ ] User accepts exact-title search in this installed Notion version.
- [ ] User signs in to Google in AIRA Chrome, imports a captioned public video,
  and accepts a generated/opened NotebookLM mind map.
- [ ] User accepts cancel/partial-result handling and confirms voice continuity.

## How to try it

1. Quit AIRA from its tray. Close AIRA Chrome (personal Chrome can stay open).
   Run `Restart-AIRA-Desktop.cmd` once to reload backend, frontend and native worker.
2. Open a fully loaded page in the intended signed-in **Notion desktop workspace**.
   Say **“Put the latest video summary in a new Notion page called Video Notes.”**
3. Open an existing editable Notion page, then say **“Append the latest video
   summary to the current Notion page.”** Or say **“Append the latest video
   summary to the Notion page called Project Docs.”** Exact-title search must
   produce one match; otherwise open the page manually and use the current-page route.
4. Button alternative: **Tasks → Read latest summary → Save the complete summary
   to Notion**. Choose new/existing and use **Export saved summary**.
5. NotebookLM needs the Google website login in **AIRA's** Chrome profile. If
   missing, quit AIRA/close its Chrome, run `Sign-In-AIRA-Chrome.cmd`, sign in
   yourself, close that Chrome, then run `Restart-AIRA-Desktop.cmd`.
6. With a video selected in AIRA Chrome, say **“Create a new NotebookLM notebook
   for this video and generate a mind map.”** For a previously summarized video,
   AIRA can obtain its actual source URL from task history.
7. Button alternative: the summary result's **NotebookLM → mind map** controls
   already use that report's video link. Select **Create a new notebook** and
   **Add video & generate mind map**. The general YouTube controls also expose
   NotebookLM with the selected/pasted video link.
8. Watch Tasks for source import, generation and verification. A queued job is not
   a completed result. Inspect partial changes before any fresh retry.

Notion and NotebookLM are external destinations explicitly requested by the user;
their content uses their own account storage/sync. AIRA's job ledger, summaries,
captions, Chrome profile and caches remain on E:. No extra API key is added for
either UI workflow. NotebookLM's import/generation uses its website account,
independently of AIRA's Gemini API key and voice billing.

NotebookLM imports the transcript of a public YouTube video with captions; it
does not import the video frames. Source availability and website limits still
apply. [Google source-import help](https://support.google.com/gemininotebook/answer/16215270?hl=en).
Current layouts expose Mind Map in Studio; older layouts can expose a chat chip,
with the resulting artifact in Studio. [Google mind-map help](https://support.google.com/gemininotebook/answer/16212283?hl=en).

## Verification record

All automated checks use temporary E-drive files and mocked providers/GUI input.
No live Notion export, Google authentication or NotebookLM generation was performed.
The existing NotebookLM and Notion accessibility views were inspected read-only
using the computer-use skill; no document text was entered.

Final validation: 24 backend tests, 25 desktop controller tests (browser, Notion
and NotebookLM), 4 literal-input checks and 9 Electron IPC checks passed: 62 total.
Nine changed Python modules parsed successfully. TypeScript/Vite production build
passed: `index-BywnsJ5G.js` / `index-dTRgiRZ5.css`.
