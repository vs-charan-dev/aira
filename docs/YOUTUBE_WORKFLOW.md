# Chrome → YouTube → transcript → summary / infographic

Implemented on 2026-10-08. Notion summary export and NotebookLM mind maps are now
implemented; see [destination workflows](STUDY_DESTINATIONS.md). Real account
acceptance remains pending. Earlier Notion private-only checks have been repaired.

## Implemented checklist

- [x] Visible AIRA-controlled Google Chrome window using installed Chrome and
  Playwright 1.63.0. Its separate profile is `data/browser/chrome`, with cache in
  `.cache/chrome`. No personal Chrome profile attachment, CDP listening port or
  additional Chromium download. Browser actions share the desktop queue.
- [x] Dedicated voice tools: `open_browser`, `search_youtube`,
  `open_youtube_video`, `youtube_study`. Wired into recall and capture agents
  through their existing shared tool declarations and dispatch.
- [x] YouTube search visibly enters a query and returns up to five observed
  video titles/links. A person chooses a result, or explicitly requests the first
  one. Opening a result clicks its observed link when still on that search page;
  otherwise an explicit canonical video URL is opened and verified.
- [x] Read the selected YouTube video tab in AIRA Chrome for voice requests
  such as “summarise this video”, including when the AIRA overlay takes focus.
  A focused owned tab takes precedence; otherwise use the last selected owned
  tab. Foreground personal Chrome and non-video pages require an explicit link.
- [x] Local fixed Python CLI using `youtube-transcript-api` 1.2.4. No transcript
  API key, hosted transcript service, paid proxy or model-generated terminal code.
  It requests English captions first; otherwise an available caption language.
  Manually created captions are preferred where available. Metadata preserves
  language and whether captions were automatic. No video/audio download or ASR.
- [x] Caption JSON and timestamped text saved on E:. Captions cached by video ID.
  Missing/restricted captions, network blocking and fetch timeout report failure;
  a missing transcript never becomes a fabricated summary. No automatic retry.
- [x] Background study lane, independent of desktop and coding jobs. Accepted
  jobs have progress, cancellation and persisted reports. One study request runs
  at a time. Stop-all / Ctrl+Alt+Escape cancels all lanes. Restart never replays
  work. An already-started study requires a new explicit request rather than
  blind resume; cached successful captions/summaries are reused.
- [x] Caption-based structured summary with source timestamps and caveats using
  the same saved Gemini key. Long captions are split into 24,000-character
  sections and combined. A 300,000-character caption limit bounds work; exceeding
  it fails explicitly instead of silently truncating. Large videos may require
  several text calls and take longer. Summary caches depend on captions/model.
- [x] Infographic uses the concise summary as a content brief, then one image
  request. Only a final supported image part is saved; intermediate thought
  images are ignored. Summary/caption assets remain available if image generation
  fails. Infographics are generated interpretations, not observed video frames
  or independently verified facts.
- [x] Task-board YouTube controls, observed search-result selection, model
  settings, progress, full summary viewer, infographic preview and download links.
  Model choices are frozen when a request is submitted. Default summary:
  `gemini-3.5-flash-lite`; default image: `gemini-3-pro-image` (Nano Banana Pro).
  `gemini-2.5-flash-lite` / `gemini-2.5-flash`, `gemini-3.1-flash-image` and
  `gemini-2.5-flash-image` are selectable. Access depends on the same Gemini key.
  Provider failures never silently switch to another paid model.
- [x] Dedicated defaults in `.env` / `.env.example`; existing keys/settings
  preserved. Python dependency manifests updated. Usage instrumentation reused
  for generation; unknown model pricing must not be treated as a proven bill.
- [x] Original outputs in `data/media/youtube`; desktop download copies default
  to `data/exports`. Electron downloads now default to E:. Files remain local;
  generation still sends caption-derived content to Gemini's API.
- [x] Syntax checks and frontend TypeScript/Vite build; dependencies installed.
  Final bundle: `index-B4Edq4b9.js` / `index-dTRgiRZ5.css`.
  No native browser interaction, live voice, caption-network acceptance or paid
  generation executed for testing, following the user's manual-testing preference.
- [ ] User acceptance of search, link click, current-video detection, captions,
  summary, infographic, cache reuse, download location and stop/restart behaviour.
- [x] Saved-summary export to new/existing editable Notion pages, with full
  readback and reload checks. Transcript-only transfer remains outside this increment.
- [ ] User acceptance of Notion export and NotebookLM generation.

## First run

Profile-picker follow-up: user history showed the generic `open_app` tool opening
personal Chrome and falsely treating its profile picker as a ready browser.
Chrome aliases are now redirected to `open_browser` in backend validation,
Electron IPC validation and native execution. The tracked task is normalized to
the browser tool, and launch explicitly selects `Default` in AIRA's E-drive
user-data directory. This fixes the routing at code level, independent of which
open tool the voice model chooses. It does not pick a personal signed-in account
or close personal Chrome windows. Physical acceptance remains pending.

Quit AIRA from its tray and relaunch **Start-AIRA-Desktop.cmd**. Restart a
separately managed backend too. The new Chrome window is labelled AIRA Chrome
in the controls; its native window still has Chrome/YouTube's page title.

1. Say **“Open Chrome.”** AIRA should use its dedicated browser tool.
2. Say **“Search YouTube for how an atom looks inside.”** Inspect the actual
   results on the page/task board.
3. Say **“Open the first video”**, or select **Open & select** for your chosen
   result. If a site consent/sign-in/challenge interrupts browsing, handle it
   manually before retrying. AIRA does not accept consent or enter credentials.
4. Leave that YouTube tab foreground, then say **“Get the transcript of this
   video.”** Inspect the saved timestamped text through **View video result**.
5. Say **“Summarise this video.”** View the summary on the task board. Cached
   captions should be reused. Model access errors appear as needs-attention;
   change the selected model only if your key cannot use the requested one.
6. Say **“Create an infographic from this video.”** The cached summary should be
   reused when the selected text model and captions match. Preview/download it.
   Image requests may require paid Gemini access even when text requests work.

Buttons are an alternative to voice: open **Tasks → YouTube → learn & create**,
search, choose **Open & select**, select output and **Create from video**. For
buttons, select/paste a video link because clicking Palace puts it in the
foreground. Voice can inspect the foreground tab. A pasted YouTube link can be
studied without launching Chrome at all.

## Sandbox warning and stalled search correction — 2026-10-08

The latest action history recorded `open_browser` succeeding, followed by a
generic Chrome `desktop_task` to type “how an atom looks inside” and press Enter.
Windows-Use did not finish that task. This was a routing failure; the dedicated
YouTube search was not invoked in that run.

- [x] Set `chromium_sandbox=True` for the installed Chrome persistent context.
  Playwright defaults this option to false. The warning is addressed by enabling
  the sandbox; its warning bar is not merely hidden. No unsandboxed fallback.
- [x] Backend and Electron recover bounded single literal search commands such
  as `Type 'how an atom looks inside' into the search box and press Enter.` as
  `search_youtube`. Tracked job type, title, timeout and report follow that action.
  Other generic Chrome tasks fail promptly with instructions for the dedicated
  tools. The GUI worker independently rejects generic Chrome desktop tasks.
- [x] Forward validated observed video titles/links through Electron IPC to
  backend reports. Previously the worker's browser data was dropped there.
- [x] Support fixed visible YouTube search input variants and verify the result
  URL contains the exact query. Failures distinguish submission from unloaded
  video results, without claiming success or automatically retrying.
- [x] Python syntax checks for changed modules and `node --check` for the Electron
  action controller passed. Frontend bundle is unchanged by this correction.
- [ ] Manual acceptance of the corrected launch/search/results/video selection.

Close the existing **AIRA-controlled Chrome window** first; an already-running
Chrome retains its old launch flags. Quit AIRA using its tray **Quit** command,
then relaunch **Start-AIRA-Desktop.cmd**. If a separate **Start-AIRA.cmd** server
is running, stop it with Ctrl+C and restart it too: the desktop launcher reuses
an existing backend and cannot replace its loaded code.

Say **“Search YouTube for how an atom looks inside.”** Expect **Searching
YouTube**, the typed query and real results; the task should not enter
**Preparing Windows-Use**. Then ask **“Open the first video.”** Check both the
browser and task-board links. Consent or site challenges still need manual input.
No live browser/voice or paid inference testing was performed for this correction.

## Mixed backend versions, search wording and manual Google sign-in — 2026-10-08

The next recorded job was `desktop_task` for Google Chrome with
`Go to YouTube and search for 'atomic structure explanation'`. Electron rejected
it promptly because that command shape was outside the earlier fallback. The job
also retained the old `open_app`/`desktop_task` types, showing the backend had not
loaded the new normalization code. Logs recorded unrelated memory/web research
before the browser task.

- [x] Recover this exact single-search wording at both backend and Electron.
- [x] Scope memory-search prompts to stored-memory questions. Browser/video
  commands use their action tools immediately rather than researching the topic.
- [x] `/health` now reports a source fingerprint captured at startup. The desktop
  launcher compares it with current backend files and refuses an older backend.
- [x] `Restart-AIRA-Desktop.cmd` restarts only a verified workspace Python/uvicorn
  loopback backend, after the desktop is quit. An unrelated or unverifiable port
  owner is not stopped. Startup errors remain visible in the launcher window.
  On Windows, the listening process can be the base Python child of the E-drive
  virtual-environment redirector: both child and live parent are checked against
  their exact executable paths and fixed AIRA command, including loopback/port.
  The base executable alone is never considered sufficient ownership evidence.
- [x] `Sign-In-AIRA-Chrome.cmd` opens ordinary installed Chrome with the same
  `data/browser/chrome` Default profile and `.cache/chrome` disk cache on E:.
  It passes no automation, remote-debugging or no-sandbox flags, and performs no
  credential entry, cookie copying or inspection. Existing profile data is retained.
- [x] Python, JavaScript and PowerShell syntax checks passed. No live browser,
  sign-in, restart execution, voice or paid inference acceptance testing performed.
- [ ] User verifies the complete restart, literal search and saved website session.
- [x] After the redirector-related restart rejection, PowerShell syntax and a
  read-only check of the actual listener confirmed the revised helper recognizes
  AIRA's backend. No process was stopped during verification.
- [x] NotebookLM source import and new-notebook mind-map workflow implemented.
- [ ] Live account acceptance; signing in alone does not verify generation.

### One-time sign-in and restart sequence

1. Quit AIRA from its tray and close the existing **AIRA Chrome** windows.
   Personal Chrome windows can stay open.
2. Run **Sign-In-AIRA-Chrome.cmd** in the workspace. On YouTube, click **Sign in**
   and complete Google sign-in manually, including any account verification.
   Signing into the website is enough; Chrome Sync is disabled and unnecessary.
3. Close that Chrome window after signing in. This releases the profile for AIRA.
4. Run **Restart-AIRA-Desktop.cmd**. This reloads the backend and launches AIRA.
5. Press Ctrl+Alt+A and say **“Search YouTube for atomic structure explanation.”**
   Check the results, then request **“Open the first video.”**

The session is stored in AIRA's persistent Chrome profile. It can be reused for
Google websites when later workflows are added, subject to expiry or Google asking
for verification again. Signing in to a different personal Chrome profile does not
sign AIRA's profile in. The Gemini API key does not log into Google websites.
Google can reject sign-in in software-controlled browsers, which is why this
helper opens normal Chrome for manual sign-in. This does not bypass Google's
verification requirements. If reauthentication is needed, repeat steps 1–3.

Sources: [Google's supported browser/sign-in guidance](https://support.google.com/accounts/answer/7675428?hl=en),
[Notebook help](https://support.google.com/notebooklm/answer/16206563?hl=en).

## Complete search and video click follow-up — 2026-10-08

The earlier search jobs recorded a results URL, but read zero videos. A subsequent
inspection of the visible Chrome window showed the homepage with “atomic model”
in the search box and suggestions still open. The earlier URL check did not prove
visible results. No successful video-opening job was recorded.

- [x] Search includes submission automatically. No separate “press Enter” request.
  Type into the visible search box, then always navigate to a fixed, encoded
  YouTube results URL. Require a successful document response and the exact query
  in both the automation URL and actual document location. This replaces the
  Enter/button fallback chain and needs no extra LLM call. Site challenges/consent
  are not automatically solved. No provider-generation retry.
- [x] Restore and maximize the Chrome window belonging to AIRA's exact owned tab
  through its CDP session, then check document visibility. Personal Chrome and
  AIRA Chrome can coexist; their coexistence alone does not prove which window
  caused the observed failure.
- [x] Read visible YouTube watch links rather than relying solely on legacy
  `ytd-video-renderer a#video-title`. Resolve titles from classic and newer lockup
  headings or link labels, without requiring a legacy `ytd-search` ancestor.
  Read only an actual YouTube results document; exclude known ads, headers,
  search suggestions, miniplayer and playlist containers, and deduplicate video IDs.
  Wait up to 20 seconds for readable results; ready pages return immediately.
- [x] Opening a requested result clicks its observed visible title/thumbnail and
  verifies the final canonical video ID. Duplicate links to the same video are
  accepted. On a current results page, a numbered open re-reads the observed
  results, allowing recovery after the previous read happened before loading.
- [x] Generic Chrome “type X into the search box” includes submission; named
  ordinal “click/open/play the first/second/etc. video” routes to the video tool.
  Other forms and app text entry are not blindly submitted with Enter.
- [x] Failure diagnostics save layout counts, document host/path and viewport
  visibility/dimensions in `.cache/desktop/youtube-layout.json`, without page
  HTML, cookies, account data or screenshots.
- [x] Python and embedded DOM script syntax checks passed. Six offline checks
  cover encoded results navigation, mismatched documents, failed HTTP responses,
  duplicate video links, restoring the owned window and rejecting a hidden window.
  The existing Chrome window was inspected/restored only; no live search/click
  acceptance run or paid inference was executed for this correction.
- [x] User confirmed automatic search and opening the first video. Latest task
  reports also record successful search and verified video opening.

Close AIRA Chrome and quit AIRA from its tray, then run
**Restart-AIRA-Desktop.cmd**. Say **“Search YouTube for atomic model.”** Check
the visible results and task-board links. Then say **“Click on the first video.”**
Alternatively, **“Search YouTube for atomic model and open the first video”**
enqueues those two actions in order. Search alone does not choose a video.
Opening a watch page is verified; site/browser playback restrictions may still
require a manual player click.

## Voice URL and study handoff correction — 2026-10-08

The latest backend log records `search_youtube`, `open_youtube_video`, then a
`look_at_screen` call in a new voice session. Neither `current_youtube_video` nor
`youtube_study` was called. No study task was created, so this incident does not
demonstrate a caption-fetch or Gemini-generation failure. Raw spoken turns are
not present in these logs; the exact transcription behind the refusal is unknown.

- [x] Expose the existing native `current_youtube_video` capability to both voice
  modes and dispatch it through the shared desktop lane. A URL question receives
  observed URL/title data directly, rather than a queued job acknowledgement.
  A busy desktop action returns a clear busy result without racing navigation.
- [x] Retain the selected owned video tab when AIRA's overlay takes focus. Never
  substitute an owned tab for a foreground personal Chrome tab. Validate the
  actual document's canonical video ID against the automation URL.
- [x] Both voice prompts explicitly route URL questions to the URL reader, and
  summaries/captions/infographics directly to `youtube_study`. Omit the URL to
  read the selected tab automatically; no preliminary screenshot or pasted link.
- [x] Ten offline browser checks and four offline voice-wiring checks passed,
  including overlay focus, personal-Chrome exclusion, direct observed URL results,
  desktop-lane busy handling and resolving an omitted study URL before generation.
  Async checks ran outside the sandbox because Windows' local asyncio socket pair
  was blocked there. No real browser/provider calls or production ledger writes.
- [ ] User accepts URL reading, transcript fetching and summary generation after
  restarting AIRA. No live voice, caption network request or paid generation was
  executed for this correction. Caption access/model quota can still fail later.
- [x] Saved-summary transfer to Notion implemented; see STUDY_DESTINATIONS.md.
- [ ] Transcript-only transfer and live account acceptance.

After closing AIRA Chrome and quitting AIRA from the tray, run
**Restart-AIRA-Desktop.cmd**. Open the desired video, then test separately:
**“Get this video's URL”**, **“Get the transcript of this video”**, and
**“Summarise this video.”** Transcript/summary requests should create a study job
on the task board, with a result or a concrete failure reason.

## Finding the summary and keeping voice connected — 2026-10-08

The atomic-model summary succeeded in jobs `278623e2ff` and `58259169dc`. The
second reused the transcript and summary caches. The saved Markdown is
`data/media/youtube/jobs/58259169dc/summary.md`; timestamped captions are alongside
it in `transcript.txt`. These files stay on E:.

- [x] Task-board header displays **Summary ready**. Expand **Tasks**, then use
  **Read latest summary** or **Download summary**. Full results open above the
  task history. Individual jobs also offer **Read video result**.
- [x] User disabled the estimated Live cost cap (`0`); usage is still recorded.
  The previous `$0.05` cap stopped two recent conversations after about 74 and
  92 seconds. Idle allowance is now 120 seconds and total session allowance is
  600 seconds in `.env`, `.env.example` and settings defaults.
- [x] Slow provider audio sends run in a separate bounded queue, preserving
  desktop/control message handling. At most six PCM frames wait; stale queued
  frames are discarded rather than replayed much later. Upload timeout is 8s.
  Voice connection startup allows 30s; PCM is held until the server is connected.
- [x] Planned idle/duration/cost stops keep their reason and show a notice.
  Transient upload/connection/start failures attempt one fresh voice connection
  per activation. Stop cancels recovery; planned limits never auto-restart.
  Old speech and desktop commands are not replayed. Gemini conversational
  context does not resume across this fresh connection; task results persist.
- [x] Four queue, eight usage/session-stop and four frontend recovery checks
  passed with fake devices/providers only. No new paid generation was run.
- [x] Final TypeScript/Vite build passed (`index-D29iBjNs.js`); changed Python
  syntax passed. The current running desktop still needs one restart to load it.
- [ ] User acceptance after closing AIRA Chrome, quitting AIRA's tray and running
  **Restart-AIRA-Desktop.cmd** once. Open **Tasks** to read the existing summary;
  it does not need regeneration. Speak several commands through one session.
  Genuine provider/network failures may still require attention after one retry.

## Storage / local CLI

- `data/browser/chrome`: AIRA Chrome profile, separate from personal Chrome.
- `.cache/chrome`: browser disk cache.
- `data/media/youtube/transcripts/<video-id>/transcript.json`: reusable caption
  source and cached structured summaries.
- `data/media/youtube/jobs/<job-id>/`: timestamped text, summary Markdown, final
  image and successful report JSON. SQLite stores task status/partial reports.
- `data/exports/`: download copies made through AIRA Desktop. Browser-based
  Palace downloads use that browser's own download preference.

The backend invokes this fixed local command in a hidden worker, rather than
opening a terminal window or executing a model-authored command:

```powershell
.\.venv\Scripts\python.exe .\scripts\youtube_transcript_worker.py VIDEO_ID E:\Havetobuild\AIRA\data
```

`VIDEO_ID` must be the video's eleven-character ID. The worker prints only a
small success/error JSON; it writes captions to the location above. YouTube can
block this unofficial caption API, and videos without accessible captions are
outside this increment. Cancellation cannot undo browser navigation or guarantee
that an already submitted provider request is unbilled.

## Sources

- [YouTube Transcript API](https://github.com/jdepoix/youtube-transcript-api):
  current fetch/list API, caption-language selection and blocking limitations.
- [Playwright persistent Chrome context](https://playwright.dev/python/docs/api/class-browsertype#browser-type-launch-persistent-context):
  installed Chrome channel and separate persistent user-data directory.
- [Playwright Chromium sandbox option](https://playwright.dev/python/docs/api/class-browsertype#browser-type-launch-persistent-context-option-chromium-sandbox):
  enables Chromium's sandbox; defaults to false.
- [Gemini image generation](https://ai.google.dev/gemini-api/docs/image-generation):
  Nano Banana Pro model code and caption-derived content brief approach.
- [Gemini 2.5 Flash-Lite](https://ai.google.dev/gemini-api/docs/models/gemini-2.5-flash-lite):
  existing-project access restriction; no assumption that every new key can use 2.5.
- [Gemini 3.5 Flash-Lite](https://ai.google.dev/gemini-api/docs/models/gemini-3.5-flash-lite):
  current configurable low-cost text default.
