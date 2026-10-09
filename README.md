# AI AIRA — Memory Palace

A Windows-local adaptation of the reviewed memory palace foundation. SQLite records and saved media live on E. Gemini supplies live voice, visual understanding, embeddings, inference, and generated images through your Google AI Studio key.

Background music and interface sound effects are disabled. AIRA's spoken replies
and voice previews remain enabled.

In the desktop app, say “Close Calculator” to gracefully close a uniquely
identified app window, or “Go to Chrome, go to Maps and search for Hyderabad”
to display Google Maps results in AIRA Chrome. “Open Google Maps” also works,
followed by a place-search request. Quit AIRA through its tray and restart
**Start-AIRA-Desktop.cmd** after updating to load the new voice tools/workers.
Multiple matching windows and unsaved-work prompts need your attention.
See [desktop commands and checks](docs/DESKTOP.md).

Timed phone reminders use Twilio: configure **Settings → Phone reminders**, then
say “Call me in five minutes to head out.” Reminders persist after the voice
session ends; the backend must stay running and the computer awake and online.
Trial accounts ring with Twilio demo audio; upgraded accounts speak your reminder.
See [setup and one-minute rehearsal](docs/PHONE_REMINDERS.md).

Charan's personal context is stored in 15 rooms with 181 individual memories.
Open **Memory rooms** from the palace, or visit `/memories`, to browse, ask cited
questions, and correct records with revision history. The Live agent retrieves
the same stored context. See the [context files and implementation notes](docs/memory-palace/README.md).

Video study can export the complete saved summary to a new or existing editable
Notion desktop page, and add a video link to a new NotebookLM notebook to generate
a mind map. Use the task-board controls or voice commands; see
[setup, commands and acceptance checklist](docs/STUDY_DESTINATIONS.md).

The [invoice coding demo](docs/INVOICE_DEMO.md) shows an ordinary invoice app.
Describe its wrong total: AIRA opens its source in VS Code, applies the configured
repair, checks tests and returns to the corrected localhost app. This known-bug
scenario defaults to a scripted repair without coding inference. Rehearse with
`Create-Fault.cmd` and `Fix-Fault.cmd`; deleting those two launchers does not
remove the voice workflow. Developer evidence is on `/invoice-workbench`.
The invoice now opens in a dedicated Chrome localhost tab, separately from
YouTube. AIRA writes three regression checks and runs all eight checks in the
VS Code integrated terminal before returning to the corrected invoice tab.

## Start

Double-click **Start-AIRA.cmd** in `E:\Havetobuild\AIRA`.

Or run from PowerShell:

```powershell
Set-Location E:\Havetobuild\AIRA
.\Start-AIRA.ps1
```

Open http://127.0.0.1:8000/palace, click **Open AIRA Memory Palace**, then **More → Settings**. Paste your Gemini key and click **Save Key**. The key is encrypted in `data\secrets\gemini.dpapi` for the Windows account running AIRA. No Firebase credentials, Google login, service account, separate Live key, or OpenRouter key is needed.

Click **Test Gemini connection** to check a short text response, a 768-dimensional embedding, and generated Live audio. This makes small API requests using your key; it does not capture microphone/camera/screen input or generate an image. Image generation is tested separately through diagram/synthesis controls and depends on model quota/access.

Keep the launch terminal running; Ctrl+C stops AIRA. If port 8000 is in use, run `Start-AIRA.ps1 -Port 8001`. Close the previous launch before opening a new one. The current baseline is one local profile and one active palace tab. Reopen the local session after a backend restart; memories persist, active Live sessions do not.

## Environment

`.env` is already created from `.env.example`. Paths and model names are configured there. `GEMINI_API_KEY` is an optional alternative to Settings; an inherited environment key is also supported. A Settings key takes priority. A populated `.env` contains a plaintext secret and must stay private/ignored. Use Settings for encrypted storage.

The encrypted key can only be decrypted by the Windows account that saved it. If testing switches between Codex's restricted account and your normal account, save it again in the normal launch. AIRA shows a message instead of silently using another key when encrypted storage is unreadable. Removing a Settings key does not erase an environment variable; clear that variable and restart if you use both.

Models are configurable because availability changes. The initial Live default follows the current [Google SDK guide](https://ai.google.dev/gemini-api/docs/live-api/get-started-sdk); embeddings use [gemini-embedding-001](https://ai.google.dev/gemini-api/docs/embeddings). Runtime model compatibility is recorded in `AIRA_PLAN.md`, not assumed from documentation.

`scripts\Environment.ps1` configures process-only paths before setup/launch:

| Output | E-drive location |
| --- | --- |
| SQLite + WAL/SHM | `data\db\aira.sqlite3` |
| Screenshots/diagrams/synthesis | `data\media\` |
| Protected key | `data\secrets\gemini.dpapi` |
| Logs/backups/exports | `data\logs\`, `data\backups\`, `data\exports\` |
| Python dependencies | `.venv\` |
| Node dependencies/build | `frontend\node_modules\`, `frontend\dist\` |
| pip/npm/temp/Python bytecode | `.cache\pip\`, `.cache\npm\`, `.cache\tmp\`, `.cache\pycache\` |
| Future model/browser downloads | `.cache\models\`, `.cache\browsers\` |

Preinstalled Python, Node, Windows, and your regular browser may reside on C. AIRA does not relocate those programs or control Windows/browser system writes. The launch scripts keep application-controlled data/downloads on E. Gemini requires internet; the app is not an offline model.

## Reinstall / development

Python 3.11+ and Node/npm must already be available. Setup uses the pinned Python lock and npm lock; no new system runtime is installed:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Setup.ps1
```

For development, run the backend via `Start-AIRA.ps1 -NoBrowser`. In a second terminal:

```powershell
. .\scripts\Environment.ps1
Set-Location frontend
npm.cmd run dev
```

Visit http://127.0.0.1:5173. Vite proxies API, artifact, media, and WebSocket routes to the backend. Production uses a single origin on port 8000. Ports bind to loopback; local sessions, origin checks, host checks, and authenticated media replace Firebase.

## Verify one feature at a time

### Usage and cost controls

Open **Settings → API usage** to see locally recorded calls, models, token modalities, and an estimated Standard paid-tier USD cost. It refreshes against the local backend every three seconds and makes no Gemini calls. Tracking starts with this update; historical Google charges cannot be reconstructed. Counters and status are stored in SQLite on E without keys, prompts, transcripts, or media content.

The estimate is not your Google billing balance. Free allowances, missing usage metadata (including some embedding responses), search surcharges, unknown model/modalities, and late final reports can make it incomplete. Missing usage displays **Unavailable**. Live estimates replace repeated snapshots within a turn and count retained context again on later turns. Streaming inference uses its latest cumulative request snapshot. The configurable cumulative Live mode is for reconciliation with the provider, not an automatic cost discount. Validate a short session against Google usage before relying on the estimate.

Default Live safeguards, configurable in the root `.env` and applied after restarting AIRA:

| Variable | Default | Behavior |
| --- | --- | --- |
| `AIRA_LIVE_IDLE_SECONDS` | `120` | Pause after two minutes without meaningful received speech, model content, or tool activity |
| `AIRA_LIVE_MAX_SECONDS` | `600` | Pause after ten minutes total |
| `AIRA_LIVE_MAX_ESTIMATED_USD` | `0` | Estimated cost cap disabled by user choice; usage recording stays active |
| `AIRA_LIVE_USAGE_MODE` | `per_turn` | Use `session_cumulative` only if provider reconciliation demonstrates cumulative session counters |

Zero disables an individual limit. The spend threshold is a **soft Live-session limit**, not a guaranteed billing cap: usage arrives after generation, and separate embedding/inference/image/search calls are outside that threshold. Stopping a session preserves saved memories; tap to reconnect. The idle rule also applies to capture, so intentional quiet listening may need a longer configured timeout. Mute keeps Live open until a limit or explicit stop; use **Stop session** when finished.

The backend enforces one tracked Live connection per local user, closes prior modes, and closes on logout/disconnect/shutdown. Failed device access and ended microphone/screen streams send stop requests; late permission results release their tracks. Connection diagnostics are blocked while Live is active and consume API quota when explicitly run.

Rates were checked on 2026-10-06 against [Google pricing](https://ai.google.dev/gemini-api/docs/pricing); the legacy embedding rate comes from [Google's model announcement](https://developers.googleblog.com/en/gemini-embedding-available-gemini-api/). Provider billing reconciliation and measured savings remain pending. Context compression, concise prompts/replies, speech detection, changed-frame sampling, and persistent embedding caches are separate planned tasks.

Run browser-device lifecycle tests without actual microphone/camera access:

```powershell
. .\scripts\Environment.ps1
Set-Location frontend
node --test scripts/test-media.cjs
```

### Baseline tests

1. Launch and open the palace; Settings and the local WebSocket should connect.
2. Save your key; run the Gemini connection check. Resolve access/quota/model failures first.
3. Test a spoken conversation, playback, mute, and interruption.
4. Save one real memory; recall it; restart AIRA and retrieve it again.
5. Start screen sharing or webcam capture; ask for a screenshot and verify local rendering.
6. Test edit/delete/navigation, then web grounding and diagram/room synthesis.

Capture and recall remain exclusive and now have shared spoken switch tools. A first Windows desktop host, tray, hotkey and local wake recognizer are implemented; real device acceptance remains pending. Intentions, coding supervision and gestures are future phases. First launch creates an empty palace rather than personal sample memories.

Offline integration validation (uses isolated E-drive test data and mocked embeddings, no real API key):

```powershell
. .\scripts\Environment.ps1
Set-Location backend
..\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Progress, verification evidence, limitations, and the next chat handoff are maintained in [AIRA_PLAN.md](AIRA_PLAN.md). Source attribution is in [UPSTREAM.md](UPSTREAM.md). Historical upstream cloud deployment docs are under `docs\upstream` and are not setup instructions for AIRA.

Optional Telegram completion messages are available for verified coding fixes.
Create your own bot with BotFather, run **Configure-Telegram.cmd**, and restart
AIRA. No messages are sent during setup; delivery is recorded on the task board
after a real repair passes its tests. See [Telegram setup](docs/TELEGRAM.md).

The explicit `backend\check_live_agents.py` check uses your configured key and quota to generate Capture/Recall greeting audio with an empty diagnostic profile. It sends no microphone/screen/personal memory input and writes no memories. It passed during setup; repeat only when a model/agent change needs validation.

### AIRA character preview

Open `http://127.0.0.1:8000/character` for the first animated companion. Move the pointer to guide its eyes, try the blink/pose controls, play the offline hello sample, or hide it for ten seconds and watch it return. The sample is synthesized with Windows System.Speech locally at 24 kHz mono; it uses no Gemini key, microphone, or cloud service. WAV source and PCM playback assets are under `frontend/public/character`.

The small character in the palace reacts to existing capture/recall output audio through a Web Audio analyser. It does not create another Live connection. Stop/interruption releases the meter and rejects stale audio decoded after cancellation. This is audio-reactive mouth movement, not phoneme lip sync.

The first Windows overlay/tray/global-cursor/hotkey/local-wake slice and spoken switch/hide tools are now implemented. Launch **Start-AIRA-Desktop.cmd**. See [desktop controls and acceptance checklist](docs/DESKTOP.md). Actual wake accuracy, Gemini tool invocation and hardware/DPI checks remain pending; hand tracking is separate future work.

Offline device/playback checks (no API calls):

```powershell
Set-Location frontend
node --test scripts/test-media.cjs scripts/test-playback.cjs scripts/test-mode-switch.cjs
```
