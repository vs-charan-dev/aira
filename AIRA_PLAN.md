# AIRA — Persistent Windows Jarvis: Plan and Progress

Last updated: 2026-10-09 (Asia/Calcutta)

## 1. Purpose

Build AIRA by extending Rayan into a persistent Windows assistant that can see, hear, remember, speak, act, and resume unfinished intentions when the right context or condition returns.

**Product promise:** AIRA remembers what you meant, watches what happens next, and continues the job when the right moment arrives.

This file is the canonical plan, progress tracker, and handoff document for work across chats. Read it before starting implementation. Update it after each meaningful change, test result, or decision.

Current stage: **Core memories, screen/screenshot capture, desktop hotkey, audible replies and Hey AIRA are user-confirmed. The desktop character, voice chooser, Windows control, YouTube study, saved-summary export to new/existing editable Notion pages, NotebookLM video-source/mind-map workflow, and visual invoice coding demo are implemented. App launch, Calculator, Desktop navigation and video summarization were reported working by the user. New destination and invoice workflows passed offline checks; real account/voice acceptance is pending. Broader settings, gestures and automation remain open.**

Current infrastructure choice: **Confirmed: SQLite + local media + local FastAPI.** Replace Firebase Authentication, Firestore, Cloud Storage, and cloud hosting. All AIRA-managed persistent data, caches, development dependencies, and temporary output must live under `E:\Havetobuild\AIRA`. The user authorized local setup and baseline implementation on 2026-10-06. Additional product phases begin only after baseline validation.

Cloud boundary: AIRA storage, identity, hosting, and monitoring are local. Gemini Live/inference still call Google and require internet/model quota. The user also explicitly requested Notion exports and NotebookLM mind maps: those destination services store/sync their requested content under the user's accounts. AIRA's files/profile/caches remain on E:. Do not describe this application as fully offline. Replacing Gemini with local models would be a separate product decision.

## 2. Confirmed decisions

- [x] Extend Rayan as the application foundation.
- [x] Target Windows only.
- [x] Plan for one primary developer; the wider team has three people.
- [x] Use dependency-based milestones; a short hackathon deadline does not constrain the scope.
- [x] Preserve Rayan's existing Gemini Live approach for real-time voice and visual interaction.
- [x] The user will obtain a Gemini API key from Google AI Studio for the existing Gemini integration.
- [x] Preserve the existing Gemini inference paths initially rather than requiring an OpenRouter migration.
- [x] Treat the earlier OpenRouter-only requirement as superseded for Rayan's existing Gemini integrations. OpenRouter may be considered for additional models later, but it is not a prerequisite.
- [x] Keep cross-device continuity outside V1, as specified in the original brief.
- [x] Create a Markdown plan with checkboxes before implementation.
- [x] Validate the existing baseline first, then add and verify one feature at a time before proceeding to the next.
- [x] Replace Firebase/Firestore/cloud media with SQLite, local media, and a locally running FastAPI backend.
- [x] Keep AIRA-managed storage, caches, logs, backups, dependencies, and temporary output in the current E-drive workspace: `E:\Havetobuild\AIRA`.
- [x] Update this plan before beginning the local migration and implementation.
- [x] Name the product **AI AIRA — Memory Palace**; retain the foundation name only for source attribution.
- [x] Authorize local baseline setup, followed by feature-by-feature testing before new features.

The user saved a Gemini key through AIRA Settings under their normal Windows account. Store it only in the Windows-protected file; never put key values in this plan, source control, logs, or handoff messages.

## 3. Progress rules

- `[ ]` means pending. A task may also be in progress or blocked; record that in the handoff section.
- `[x]` means completed against its acceptance criteria, with evidence recorded below.
- Upstream code present does not mean AIRA has implemented or verified the feature.
- Keep runtime verification tasks unchecked until tested in our environment.
- A phase is complete only when its required tasks and acceptance criteria pass.
- Record partial work without checking the whole task. Split a task if part of it can be independently completed and verified.
- When a decision changes, update both the affected tasks and the decision log.
- Do not silently remove a requested feature. Explicitly record deferral or scope changes.

## 4. Upstream baseline and reusable capabilities

Repository: https://github.com/yelnady/rayan

Source reviewed at commit: `0e07ab7445198f0aad1e3f72bf1538ba22e214c9`.

Review method: README, product documentation, repository structure, and relevant frontend/backend source. The app was not run. The review copy was downloaded outside this application workspace.

| Capability | Upstream source status | AIRA work required |
| --- | --- | --- |
| Natural speech conversation and transcription | Present through Gemini Live | Configure and verify; preserve the integration |
| Speech interruption | Event handling and playback stop present | Verify responsiveness and cancellation behavior |
| Webcam and screen sharing | Browser media capture present | Verify, then add Windows context and native capture |
| Screenshot memories | Capture tool and Cloud Storage path present | Replace cloud uploads with E-drive media files and local URLs; verify |
| Automatic concept extraction | Confidence and capture-frequency controls present | Verify quality and filtering |
| Explicit memory save | Voice tools present | Verify project-linked saves |
| Persistent memory | Firestore artifacts with timestamps, text, embeddings, and media references | Replace with SQLite on E; preserve fields/relationships and verify |
| Semantic, keyword, and date retrieval | Present | Verify relevance and date handling |
| Topic rooms and clustering | Present | Preserve; add project/person/task associations |
| Deduplication | Within-session similarity merge present | Verify; extend retention and cross-session filtering |
| Memory and room management | Create/edit/delete and related operations present | Verify behavior and complete deletion semantics |
| Voice navigation | Palace navigation and artifact tools present | Preserve |
| Visual synthesis and narration | Room images, narration, and diagrams present | Verify model/storage compatibility |
| Memory interface | React/Three.js palace, map, transcripts, indicators, and tool activity present | Preserve as expanded memory view; add desktop orb/timeline |
| Web information | Gemini-grounded search helper and enrichment-related code present | Verify connected paths; add browser control separately |
| Hosting and identity | FastAPI/WebSockets, Firebase, Firestore, Cloud Storage, deployment infrastructure present | Replace cloud identity with protected local sessions; run backend/frontend locally |

Source references:

- [Gemini client and model configuration](https://github.com/yelnady/rayan/blob/0e07ab7445198f0aad1e3f72bf1538ba22e214c9/backend/app/core/gemini.py)
- [Capture agent](https://github.com/yelnady/rayan/blob/0e07ab7445198f0aad1e3f72bf1538ba22e214c9/backend/app/agents/capture_agent.py)
- [Recall agent](https://github.com/yelnady/rayan/blob/0e07ab7445198f0aad1e3f72bf1538ba22e214c9/backend/app/agents/recall_agent.py)
- [Agent tools](https://github.com/yelnady/rayan/blob/0e07ab7445198f0aad1e3f72bf1538ba22e214c9/backend/app/agents/tools/tools.py)
- [Search service](https://github.com/yelnady/rayan/blob/0e07ab7445198f0aad1e3f72bf1538ba22e214c9/backend/app/services/search_service.py)
- [Artifact model](https://github.com/yelnady/rayan/blob/0e07ab7445198f0aad1e3f72bf1538ba22e214c9/backend/app/models/artifact.py)
- [Capture hook](https://github.com/yelnady/rayan/blob/0e07ab7445198f0aad1e3f72bf1538ba22e214c9/frontend/src/hooks/useCapture.ts)
- [Voice hook](https://github.com/yelnady/rayan/blob/0e07ab7445198f0aad1e3f72bf1538ba22e214c9/frontend/src/hooks/useVoice.ts)
- [Media capture](https://github.com/yelnady/rayan/blob/0e07ab7445198f0aad1e3f72bf1538ba22e214c9/frontend/src/services/mediaCapture.ts)

Important implementation distinctions:

1. Capture and recall currently stop each other's local input machinery in the frontend. Simultaneous ongoing capture and conversation need adaptation and verification.
2. Browser screen sharing is an explicit session, not native awareness of active Windows applications or repositories.
3. Memory search scans Firestore records and ranks them in application code; a scalable vector-search implementation is not established by the review.
4. Grounding reduces hallucination risk but does not guarantee zero hallucinations. Show the evidence behind memory answers.
5. A stored goal or blocker is a memory artifact, not an executable intention with triggers and lifecycle state.
6. Unmodified upstream depends on Firebase/Google infrastructure. Our first baseline must replace those paths locally before launch; do not ask the user to provision Firebase, Firestore, Google storage, ADC, or a service account for the selected design.
7. Existing model IDs, SDK versions, and API compatibility require validation before relying on them.

## 5. Architecture direction

Preserve Rayan's React/TypeScript frontend, FastAPI/WebSocket foundation, memory concepts, and Gemini Live interaction. Add the following boundaries instead of putting every responsibility inside one voice agent.

| Component | Responsibility |
| --- | --- |
| Windows desktop host | Orb, tray, global hotkey, capture indicator, lifecycle, and desktop integration |
| Context collector | Active app, permitted screenshots, project identity, browser context, and idle/return events |
| Memory service | Historical knowledge, decisions, source evidence, retrieval, retention, and deletion |
| Intention engine | Durable future instructions, trigger evaluation, lifecycle, recovery, and cancellation |
| Action executor | Terminal/browser/desktop actions, approval enforcement, cancellation, and results |
| Coding-agent adapter | Work dispatch, structured progress, input requests, diffs, and verification |
| Event store | Context, job, action, and approval events used by the timeline and briefings |
| Model layer | Existing Gemini integrations; optional additional providers behind separate adapters |
| Presentation layer | Desktop orb plus expanded timeline, intentions, and existing memory palace |

Confirmed implementation choices:

- SQLite for persistent records and embeddings, with local media files served through FastAPI.
- Local profile/session identity, local settings, and protected credentials; no Firebase login dependency.
- Local frontend/backend execution; no hosted database, storage, authentication, or cloud deployment requirement.
- The E-drive directory contract below for application-controlled writes.

Remaining implementation choices, not yet finalized:

- Windows desktop host is finalized: Electron wrapping the existing React interface, with a view-only overlay and one palace voice owner. Other choices below remain pending.
- A locally running Python backend/companion that can monitor jobs independently of the visible UI.
- OpenCode as the first coding-agent integration, with a provider-neutral adapter so another agent can be added later.
- Windows accessibility/UI Automation for supported desktop operations, with explicit fallback behavior when semantic controls are unavailable.

Record final choices in the decision log before coding their dependent components.

### Selected local replacement

Replace Firestore persistence behind repository interfaces; serve saved media from the local backend; use a stable local user profile and protected loopback session instead of simply disabling authorization. Store secrets in a Windows-protected encrypted file on E, not in plaintext SQLite or source. Preserve Gemini Live, the React palace, and the WebSocket protocol where practical.

Hosted alternatives were evaluated but are not part of the selected plan. No Firebase, Supabase, Cloud Storage, Cloud Run, or managed vector database setup is required.

Technical references: [SQLite desktop suitability](https://www.sqlite.org/whentouse.html), [SQLite WAL](https://www.sqlite.org/wal.html).

Keep local memory retrieval cached/indexed and run storage/embedding/image work independently of the live audio loop. SQLite WAL allows readers and a writer to coexist but does not permit multiple simultaneous writers; serialize writes and validate behavior under concurrent voice/capture/job activity. Hosted providers should not be required for deferred-intention execution.

Validation of the selected implementation: demonstrate memory CRUD/retrieval, local media rendering, restart persistence, session protection, and concurrent recording/conversation without blocking audio. Record measured latency rather than assuming a database change improves end-to-end speech response. Gemini API quota and any model charges remain separate from infrastructure cost.

### E-drive directory and write contract

Authoritative root: `E:\Havetobuild\AIRA`. The user's reference to the A drive is resolved to this explicitly named current E-drive folder. The reported free-space amounts are estimates; measure disk space during setup.

| Purpose | Planned location under the root |
| --- | --- |
| SQLite database, WAL, and SHM files | `data\db\aira.sqlite3` and its adjacent sidecars |
| Screenshots, diagrams, generated images, and saved audio | `data\media\` with category subfolders |
| Memory/vector indexes and derived data | `data\indexes\` |
| Local profile and non-secret configuration | `data\config\` |
| Windows-protected encrypted secrets | `data\secrets\` |
| Application/action logs | `data\logs\` |
| Database/media backups and exports | `data\backups\` and `data\exports\` |
| Application/download temporary files | `.cache\tmp\` |
| pip/npm package caches | `.cache\pip\` and `.cache\npm\` |
| Model weights, embeddings-model downloads, browser automation assets | `.cache\models\` and `.cache\browsers\` |
| Desktop host user/session/cache data | `data\desktop\` |
| Python environment | `.venv\` |
| JavaScript dependencies and build output | Project-local `node_modules` and build directories on E |
| Optional portable runtimes/tooling | `.runtime\` if needed |

Implementation requirements:

- Resolve and validate all application-controlled paths against this root. SQLite sidecar files, media URLs, and export destinations must obey the same rule.
- Central path configuration implements `AIRA_DATA_DIR`/`AIRA_CACHE_DIR`, validated within the workspace root.
- Set process-scoped `TEMP`/`TMP`, pip/npm cache paths, model-cache paths, browser download paths, and desktop-host user/session data before those tools create output. Avoid machine-wide environment changes.
- Download or copy implementation/review sources directly onto E; do not create new AIRA review clones in C-drive temporary folders.
- Existing Windows, browser, Codex, or preinstalled tool files may reside on C. Do not relocate unrelated installations or promise zero operating-system writes; the requirement applies to AIRA-controlled storage and downloaded assets.
- Use selective capture, configurable retention/cache limits, free-space checks, and safe cleanup. Do not store every incoming visual/audio frame by default.
- Keep runtime data, secrets, caches, environments, and generated assets out of source control. Back up SQLite consistently, including WAL state through an appropriate backup method.

The directory contract is initialized and enforced by scripts/Environment.ps1, scripts/Setup.ps1, Start-AIRA.ps1, and backend/app/config.py. Future desktop/index/backup/retention features remain planned; their reserved directories do not imply implementation.

## 6. Implementation checklist

### Phase 0 — Establish, localize, and verify the Rayan baseline

Depends on: implementation authorization and required configuration.

#### First-run prerequisites and test order

The user already has a Google AI Studio Gemini key. Gemini Live uses a Gemini API key; there is no separate Live API key to obtain. Model availability, key restrictions, and quota still need verification. [Google Live API SDK guide](https://ai.google.dev/gemini-api/docs/live-api/get-started-sdk).

For an isolated Gemini Live connectivity test, the key and the Python SDK/runtime are sufficient prerequisites, subject to model access. For our adapted Rayan baseline, use the following local prerequisites:

| Requirement | Needed for | Configuration |
| --- | --- | --- |
| Gemini API key | Live voice and existing Gemini inference paths | Configure via adapted local Settings/secret storage; no Google sign-in prerequisite |
| Writable E-drive application folders | Database, files, logs, and caches | Initialize and validate the directory contract above |
| SQLite and schema migrations | Rooms, memories, sessions, settings, and future intentions | Create the database on E; enable appropriate concurrency handling |
| Protected local profile/session | UI/API/WebSocket identity | Replace Firebase token verification and cloud sign-in |
| Local media service | Saved screenshots, diagrams, and synthesized images | Save on E and return backend-local URLs |
| Python and Node/npm | Running on Windows | Use E-drive environments, dependencies, caches, and temporary paths |
| Local frontend/backend URLs | Browser/desktop connection | Bind backend to loopback, configure allowed origins and local session checks |

Replace upstream Firebase/project/bucket configuration with local path/session configuration. Remove Firebase Admin startup, Firebase frontend/analytics initialization, Firestore clients, and Cloud Storage upload paths from the active runtime. The exact replacement environment variable names will be documented during implementation.

No ADC, service-account JSON, Firebase configuration, storage billing account, Terraform provisioning, hosted deployment, OpenRouter key, or separate speech-provider key is required for this selected baseline. Gemini API model quota/billing is still independent.

Test in order: E-drive paths/caches → source import → local schema/media/session migration → isolated Gemini connectivity → frontend/backend startup → protected local WebSocket → local Gemini settings → voice conversation/interruption → save/retrieve/restart memory → screen sharing/local screenshots → synthesis/web paths. Resolve each failed capability before depending on it.

Known compatibility check: upstream model IDs may need updates for the current Gemini API; validate embeddings through the supported API-key path instead of introducing Vertex credentials. Preserve useful behavior while replacing all cloud persistence/identity paths.

- [x] P0.1 Bring the reviewed Rayan baseline into the application workspace and record its provenance.
- [x] P0.2 Document Windows setup, E-drive path/cache configuration, local prerequisites, and secret configuration.
- [x] P0.12 Configure E-drive data/cache/temp/dependency paths before downloads or package installation; verify actual disk space.
- [x] P0.13 Replace Firestore room/artifact/session/settings/enrichment/layout persistence with SQLite repositories and schema migrations.
- [x] P0.14 Replace Firebase sign-in, token verification, analytics initialization, and startup credentials with protected local profile/session handling.
- [x] P0.15 Replace Cloud Storage screenshot/diagram/synthesis uploads with E-drive file storage and local media routes.
- [x] P0.16 Add local Gemini settings and Windows-protected encrypted secret storage on E.
- [x] P0.17 Verify local storage/session/media CRUD and confirm startup requires no Firebase or Google Cloud infrastructure credentials.
- [x] P0.3 Configure the user's Gemini key through an appropriate settings/secret path.
- [ ] P0.4 Validate current Gemini Live, inference, image, and embedding model compatibility; record any required model update.
- [x] P0.5 Start the frontend/backend and verify authentication and WebSocket connection.
- [x] P0.6 Verify voice conversation, transcription, follow-up context, mute, and speech interruption. User reported voice controls are working after the focused test instructions; accepted as user validation, without independent device observation.
- [ ] P0.7 Verify webcam input, screen sharing, and saved screenshot artifacts.
  - [x] Verify Screen capture sees shared content and saves a screenshot that renders in the palace. Passed by user confirmation.
  - [ ] Verify webcam input separately.
- [ ] P0.8 Verify explicit saves, automatic extraction, clustering, and within-session deduplication.
  - [x] User-confirmed Voice Only explicit memory save and same-run recall.
  - [ ] Verify automatic extraction, clustering, and within-session deduplication separately.
- [ ] P0.9 Verify semantic/date retrieval, memory editing/deletion, narration, web-search paths, and visual synthesis.
- [x] P0.10 Verify saved memory survives application/backend restart. User confirmed the saved test memory appeared and could be recalled after the instructed full backend restart.
- [ ] P0.11 Fix baseline blockers and document inherited limitations.

Acceptance: the localized baseline runs with SQLite/local media and protected local sessions, without Firebase/Firestore/Cloud Storage credentials. A real spoken/screen memory is saved on E, survives restart, and is retrieved with identifiable source evidence. Voice interruption works. Data/cache paths are verified and required dependencies documented.

#### Local setup verification — 2026-10-06

User-confirmed connection checks (screenshot supplied on 2026-10-06):

- [x] Text inference: Passed in AIRA Settings.
- [x] 768-dimensional embeddings: Passed in AIRA Settings.
- [x] Live audio generation: Passed in AIRA Settings.
- [ ] Image generation: separate diagram/synthesis test pending.

This confirms model connectivity and generated audio, not microphone capture, interruption, or a real-memory save/recall workflow. P0.4 remains pending until image compatibility is tested. Later user reports confirm voice controls and memory workflows; P0.6 is now checked by user report.

- Source imported on E from reviewed commit, excluding upstream Git metadata; attribution in `UPSTREAM.md`. Historical cloud docs/infrastructure moved to `docs/upstream`.
- `README.md`, `.env.example` (and ignored `.env`), `Start-AIRA.cmd`, `Start-AIRA.ps1`, and `scripts/Setup.ps1` provide local launch/configuration. Python/npm dependencies and lockfiles are installed on E. Free space was 62,264,410,112 bytes before installation, about 58 GiB; approximately 61.4 GB remains after setup.
- SQLite schema version 1 stores hierarchical records in a JSON document table with an indexed parent column. Datetimes, embeddings, rooms, artifacts, sessions, layouts, enrichments, and local profiles are retained. WAL and atomic read-modify-write updates run off the asyncio loop. This is a local document repository, not a cloud emulator or managed vector index.
- No Firebase/Admin/Firestore/GCS/ADK/Vertex dependency remains in the active runtime. A single local profile uses an origin-checked bootstrap, memory-only bearer token, HttpOnly/SameSite session cookie, protected HTTP/media/WebSocket routes, and loopback/Host checks. One active palace tab is the current supported usage.
- Media writes use `save_media` and validated E-drive paths; same-origin authenticated routes render local screenshots/diagrams/synthesis. Latin UI/3D fonts are packaged locally. No microphone/screen/video frames are saved continuously by default.
- Gemini key storage uses user-bound Windows DPAPI on E; the user re-saved it under the normal Windows launch account after the initial restricted-account test. No plaintext key is stored in SQLite. Environment key support is optional; Settings takes priority.
- `npm.cmd run build` passes. Five offline integration tests cover concurrent increments/array unions, datetime/query/cursor handling, a fresh-process SQLite reload, palace/room/artifact/session/layout/enrichment flows, HTTP/WS/origin/Host/media protection, and encrypted key persistence/account mismatch. Test embeddings are mocked; this proves local integration, not model-backed memory quality.
- Browser verification: AIRA login → Memory Palace → More → Settings; palace remains after server restart. The normal Windows process has Gemini network access. The restricted process could not reach Gemini and was stopped.
- Real key checks: `gemini-embedding-001` returns 768 values; `gemini-3.8-flash` returns text; `gemini-3.8-live` connects and generates greeting audio in both real Capture and Recall agents with an empty diagnostic profile (`backend/check_live_agents.py`). No microphone or screen content was used for those checks.
- Compatibility fixes: old Live ID and Vertex-only embedding ID replaced with Gemini API models; configured `gemini-2.5-flash` returned 404 for this key, so text default changed to verified `gemini-3.8-flash`. Web grounding uses the configured text model. Removed explicit native-audio language parameter and incompatible `enable_affective_dialog=True`; isolated tests identify affective dialogue as causing error 1007. Empathy remains prompt-driven. Capture greeting uses current `send_client_content`, and capture startup waits for connection and reports failures. Windows `%d` replaces unsupported `%-d` dates.
- Empty first palace replaces automatic personal sample seeding. Rejected/expired WebSocket sessions stop reconnecting and return to local login. Disconnect stops live agents. This does not implement long-term Gemini session resumption.
- Image model remains configurable (`gemini-2.5-flash-image` is listed by the key's model catalog), but actual image generation/quota has not been verified. No generated image or billing setup was requested during setup.
- **Next baseline tests:** Core voice/memory/screen workflows are user-confirmed. No repeat screen-capture test is required. Manual mode-switch/stop regression after the lifecycle update remains unconfirmed and should accompany the next interaction change. Test other inherited capabilities before depending on them. Keep broader milestones unchecked; proceed to P1.1 design without claiming all of Phase 0 passed.

#### Core readiness checks and remaining regression coverage

Core checks are confirmed by user report. This does not certify every inherited Rayan feature; broader P0 items remain open. The remaining manual mode-switch regression can accompany the next interaction change and does not block P1.1 design.

- [x] Confirm a spoken follow-up retains context, displayed transcription is usable, mute works, and speaking over AIRA interrupts its reply (P0.6). Passed by user's report that voice controls are working.
- [ ] After the latest lifecycle changes, switch Voice Only → screen capture → recall, then stop explicitly; confirm the previous mode stops, no duplicate voice is heard, and microphone/screen indicators turn off after stopping.
- [x] Edit a disposable saved memory, recall the updated fact, then delete it and confirm it is absent from the palace and recall results (focused P0.9 check). Passed by user's report that memory management is working; broader P0.9 remains open.
- [ ] Record results and fix any blocker in these core paths before Phase 1 implementation.

Next begin P1.1 design: choose and document the Windows desktop host, tray/orb lifecycle, global hotkey, and on-demand foreground-window/screen access. Implement and test a minimal tray + orb + hotkey activation slice before adding wake words or background capture. Webcam, automatic extraction/clustering/deduplication, advanced retrieval, narration, grounding, and image/room synthesis remain scheduled validation rather than claimed passes.

Baseline readiness result (before the desktop slice): user confirms voice controls, memory management, and browser screen capture. Do not repeat that baseline test. At that point recall had no mode-switch/screen-start tool; the new desktop slice adds them, with separate native/source-picker acceptance pending. Current action-bar controls require stopping the active mode before starting the other. Manual mode-switch/stop regression remains unconfirmed, separate from screen capture itself; validate it with the next interaction change rather than blocking P1.1 design. Voice-triggered switching and truthful device-state feedback belong in the new companion interaction work.

#### Cost investigation and proposed optimizations — 2026-10-06

User reported about USD 0.10 consumed after less than one minute of speaking. This is an observation, not yet an attributed session bill: the usage display, billing tier, measurement interval, session-open duration, and inclusion of setup diagnostics are unconfirmed. The subsequent "OKay" followed the recommendation to implement usage measurement and session cleanup; that work is now implemented and tested offline. No paid API calls were made during the audit or this implementation validation. Measured savings and provider reconciliation are pending.

Audit findings before optimization: continuous 16 kHz PCM, mute retaining the backend Live connection, input/output transcripts, substantial prompts/tools, no context compression or usage meter, full-size 1 fps visual frames including unchanged screens, and no persistent embedding cache. Capture pace changes extraction frequency, not streaming. Recall-to-capture switching previously stopped only local input and did not explicitly close the backend recall agent. Usage instrumentation and backend/client cleanup are now added; other optimizations remain pending. This does not establish how much any issue contributed to the reported charge.

Google's current [pricing](https://ai.google.dev/gemini-api/docs/pricing) lists Gemini 3.8 Live Standard audio input at about USD 0.005/min and output at USD 0.018/min; text input USD 0.75/M tokens and text output USD 4.50/M tokens. These are pricing components, not a flat conversation-minute rate. The [Live billing guide](https://ai.google.dev/gemini-api/docs/live-api/best-practices#pricing-and-billing) documents retained-history re-billing per turn, extra transcription tokens, and permanently enabled proactive listening for 3.8. Actual cost must be derived from measured modality usage and reconciled with the provider's report. Free-tier eligibility/limits must be checked for the user's actual project; do not provision billing or promise free paid-project usage.

- [ ] P0.18 Add local per-session/per-call usage accounting for Live, embeddings, inference, grounding, and generated media; display an explicitly estimated cost with dated model rates. Handle cumulative versus per-turn metadata without double counting; reconcile a controlled test with provider usage. Do not log keys or raw personal content.
  - [x] Instrument all existing async SDK generation/embedding/Live paths; persist counter-only ledger on E; authenticated Settings meter and dated rates; flag missing/unknown usage and excluded search surcharges.
  - [x] Offline tests cover repeated within-turn snapshots, re-billed context across turns, explicitly configured session-cumulative mode, streaming final snapshots, incomplete embedding usage, and persistence/restart recovery.
  - [ ] Reconcile a controlled real session with Google usage and validate actual Live metadata timing/semantics. Estimates remain provisional until this passes.
- [x] P0.19 Enforce one active backend Live mode per local user; close the prior agent on mode switching, cancel/start failure, explicit stop, device failure, logout, and disconnect. Add configurable idle/session-duration limits and estimated-spend stop controls, acknowledging in-flight usage/reporting lag. Implemented and verified with simulated SDK/device tests; real-session regression follows P0.24.
- [ ] P0.20 Add concise spoken replies/brief confirmations, compact prompts and tool responses, and bounded relevant-memory context. Configure supported Live context compression and validate follow-up recall/interruption quality.
- [ ] P0.21 Compare push-to-talk and local speech detection with the current continuous stream. Preserve speech onset, natural pauses, and interruption; use correct stream-end/activity signals. For 3.8, distinguish reducing transmitted audio from stopping permanently enabled proactive session listening; idle close remains necessary.
- [ ] P0.22 Add changed-frame detection, adjustable visual sampling, and supported media-resolution controls; keep screenshot storage quality distinct from inference sampling. Measure text readability and time to recognize changed content.
- [ ] P0.23 Cache embeddings locally on E by profile, model, dimensionality/config, and exact text hash; reuse already-computed vectors through storage paths and coalesce duplicate in-flight calls. Cache stable summaries with invalidation when memories change. Do not enlarge prompts merely to meet provider cache thresholds.
- [ ] P0.24 Run a measured before/after short conversation and capture/recall test, reporting cost components, latency, and memory quality. Consider an alternative non-proactive Live model only after checking current key access and compatibility; no assumption that the model's base rate is cheaper. A local STT + text inference + local TTS mode is a later architectural option requiring Windows/latency/voice-quality validation.

Original defaults were idle 45 seconds, maximum session 180 seconds and a soft reported-Live-token threshold of USD 0.05. The 2026-10-08 continuity update below changes these to idle 120 seconds, maximum 600 seconds and cost threshold 0 (disabled at the user's request). Each is configurable in root `.env`; zero disables that limit. They apply to Live only, including quiet capture: separate calls and late reports can exceed a configured threshold. Limits send a stop notice, release local devices, and preserve saved memories. No actual Google balance/credit integration exists. Ledger starts at its installation and cannot explain earlier spend by itself.

Priority: reconcile the usage meter/lifecycle changes with one short user-run session; then concise context/replies and context compression; then audio/frame filtering and local caches. Keep Gemini Live as the primary interaction route. Provider prompt caching for supported standard text calls does not establish a discounted native-audio Live context; [caching documentation](https://ai.google.dev/gemini-api/docs/caching) must be checked for the specific API/model. SQLite/media remain on E. Do not run optional chargeable diagnostics automatically.

### Phase 1 — Windows companion and continuous interaction

Depends on: Phase 0.

- [x] P1.1 Finalize the desktop host and local companion lifecycle design. Electron + existing React/SVG; one palace voice owner, observer-only overlay, local Windows wake recognizer and E-drive caches/config. See docs/DESKTOP.md.
- [ ] P1.2 Add tray operation, animated AIRA character near the taskbar (replacing the generic orb design), expand/collapse, and listening/thinking/acting/error states.
  - [x] First native overlay, tray show/hide/quit, actual listening/speaking/working/capturing/muted/error state labels, and output-mouth IPC.
  - [ ] User validates native states and real speech; expanded interactions/acting state grow with future tools.
- [ ] P1.3 Add a configurable global hotkey and local wake-word activation.
  - [x] Implement configurable Ctrl+Alt+A activation, registration feedback, local preferences, and optional Windows grammar wake listening with pause/release before Live and idle rearm. Wake starts disabled. Native registration/probe and three process tests pass.
  - [ ] User validates actual hotkey outside AIRA and Hey AIRA accuracy/latency/false triggers.
- [ ] P1.4 Collect foreground app, window identity, and permitted open-window context.
- [ ] P1.5 Capture the current screen/window on request without manual upload.
- [ ] P1.6 Add screen-region selection for point-and-ask.
- [ ] P1.7 Support capture and conversation together without duplicate audio, playback echo, or losing context.
- [ ] P1.8 Resolve conversational references such as "this error," "that button," and "fix that" against recent context; clarify ambiguous targets.
- [ ] P1.9 Add visible capture status, stop/pause controls, and graceful device/disconnection handling.
- [ ] P1.10 Define behavior while the UI is hidden, Windows sleeps, the device disconnects, or the companion restarts.
- [x] P1.11 Create the reference-inspired character with controllable broad face, eye whites, pupils/highlights, eyelids, cheeks, and mouth; no visible legs or arms; a small irregular four-point star/tuft overlapping the crown matching the reference, plus a dark-blue glow along the full visible elliptical outline. Preserve large glossy eyes and a small mouth; the photographed phone is not the required outer shape. User accepted the design with one final width adjustment.
  - [x] Built layered SVG blue character with large glossy eyes, eyelids, cheeks, tiny mouth, bottom-cropped single elliptical face, no limbs, a small reference-style head tuft, and continuous dark-blue rim glow, and idle/listening/thinking poses; interactive local `/character` review page.
  - [x] User confirms the character's appearance before desktop integration: "everything is good," requesting only a little more width at the same height (2026-10-06).
- [ ] P1.12 Add natural blinking, forward idle gaze, bounded/smoothed cursor-following pupils, and return to forward gaze after pointer inactivity. Forward gaze is a visual pose, not actual face tracking.
  - [x] Browser pointer tracking, bounded pupils, smoothing, idle return, automatic/manual blinks, and reduced-motion handling implemented. Browser observations verified cursor movement and blink closure.
  - [x] Wire global Windows cursor coordinates to the view-only overlay; identical cursor polling does not prevent idle return.
  - [ ] Verify real desktop cursor/DPI/multi-monitor behavior.
- [ ] P1.13 Animate the mouth from actual AIRA audio playback; handle pauses, queued audio, interruption, output mute, and stop. Start with audio-reactive movement; phoneme/viseme lip sync is optional later work.
  - [x] Added output-only Web Audio analyser to the existing shared AudioPlayback class, used by capture/recall. Character reads smoothed RMS; sample playback verified mouth opening/closing. Added stop guards against late decode/resume and three offline playback regression tests.
  - [ ] User verifies mouth movement with actual Gemini speech in the palace; desktop ownership/output controls remain pending.
- [ ] P1.14 Add bottom entrance/exit motion with gentle settling; dock above the selected monitor's taskbar/work area. Verify DPI, monitor/taskbar changes, click-through behavior, and no unwanted keyboard focus.
  - [x] Native bottom entrance/exit, work-area placement, display-change/resume repositioning, click-through/no-focus window flags.
  - [ ] User confirms physical taskbar placement, DPI/multi-monitor changes, click-through and keyboard focus.
- [ ] P1.15 Add a real hide-character tool for requests such as "disappear for 10 seconds". Animate downward, hide the overlay, wait the requested hidden duration, then return upward using a desktop-host timer/deadline independent of Gemini. Define repeated requests, manual show/cancel, sleep/resume, and tray recovery. Hiding the character is distinct from quitting or stopping voice; keep capture/listening state available in the tray.
  - [x] Local preview button slides below a clipped bottom anchor, disappears for ten seconds after the exit animation, then returns; manual restore and deadline reconciliation on tab visibility changes. Browser verified hidden state/downward movement and automatic restored state.
  - [x] Shared Live hide tool, native animation/deadline, repeat replacement, activation/tray restore; wall-clock deadline handles overdue return after sleep.
  - [ ] User validates spoken hide/return, tray recovery and sleep duration.
- [ ] P1.16 Feed a locally recognized gesture pointer into the gaze controller when Phase 8 is ready. Ordinary cursor tracking comes first; gesture recognition is separate from eye drawing.
- [ ] P1.17 Wire spoken mode requests to actual frontend/desktop actions and acknowledge success only after activation. "Hey AIRA" outside an existing voice session depends on P1.3 wake-word activation.
  - [x] Both Live agents have switch_mode for recall/capture_voice/capture_screen/capture_camera/stop. Tool returns pending wording; actual status follows device/backend readiness. Native screen/window picker and browser permission button; old input/playback cleanup, duplicate/stale guards. Four simulated mode/permission regressions and five backend tool tests pass. Optional narrative generation is skipped on transitions.
  - [ ] User validates actual Gemini tool invocation and voice → screen → recall → stop without duplicate audio.

#### Character design proposal — 2026-10-06

Reference: attached `IMG-20261006-WA0011.jpg`, showing a blue face with large white eyes, glossy dark pupils/highlights, cheeks, and a tiny mouth on a photographed phone. User wants similar expressive eyes, a speaking mouth, cursor/gesture gaze, forward idle gaze, blinking, taskbar placement, timed disappearance, and upward/downward reveal/hide motion. The phone outline is contextual, not a requirement to draw a phone.

Selected implementation: Electron desktop host plus existing React/TypeScript, with layered SVG and procedural animation. The first native slice is installed and passes offline startup/overlay/registration checks; P1.1 is complete. Actual voice and hardware acceptance remains pending. Use a small transparent overlay, a separate expanded Memory Palace window, and one voice/playback owner to avoid duplicate Live sessions. Keep desktop data/cache/temp/art under E; use a restricted preload/IPC bridge and retain backend key storage. Validate Windows transparency, taskbar placement, click-through, and focus before promising identical behavior across configurations.

SVG provides gradients, highlights, and controllable shapes without mandatory external design software. Figma or Rive can optionally refine the art/rig. A pre-rendered video/GIF cannot be the sole interactive character because gaze, speech, and hide duration vary at runtime. SVG/local preview and first Electron overlay/tray/hotkey/local-wake integration are implemented; real microphone and hardware acceptance remain pending.

Gaze converts Electron desktop cursor coordinates into character-relative coordinates, clamps pupils inside the eyes, and interpolates smoothly. Idle centers the pupils with varied blink intervals. Phase 8 supplies the same target from hand tracking. Speech extends the existing Web Audio playback path with an analyser/envelope tied to audible playback, rather than transcript timing or chunk arrival. First-pass mouth movement conveys speech activity, not exact pronunciation. These visual behaviors require no additional model calls.

Hide requests must trigger a real tool/host action: slide below a clipped bottom anchor, hide the overlay, start the hidden-duration timer, then show and animate upward. Host timing allows return while the renderer is hidden or the Gemini session has ended. Wake-word activation is separate; initially spoken hide works in an active voice session.

Build order: static character review → interactive gaze/blink preview → Windows overlay/tray/placement → existing speech playback integration → timed hide/show tool → spoken mode requests → gesture gaze when local hand tracking exists. Check off only after validation.

Sources: [Electron window styles](https://www.electronjs.org/docs/latest/tutorial/custom-window-styles), [Electron screen API](https://www.electronjs.org/docs/latest/api/screen/), [Electron window interactions](https://www.electronjs.org/docs/latest/tutorial/custom-window-interactions), [Web Audio analyser](https://developer.mozilla.org/en-US/docs/Web/API/AnalyserNode).

Acceptance: while working in another app, the user can activate AIRA and ask about the visible screen. It identifies the selected context, answers aloud, and handles interruption.

### Phase 2 — Local-first memory and project continuity

Depends on: Phase 1 and the working SQLite/media baseline from Phase 0.

- [ ] P2.1 Extend the Phase 0 SQLite/media schema for project continuity and richer memory metadata; preserve existing records.
- [ ] P2.2 Separate historical memories, intentions, jobs, and events in the data model.
- [ ] P2.3 Attach memories to stable project identities, people, websites, and tasks.
- [ ] P2.4 Recognize an opened/selected repository using reliable project signals rather than only screenshot guesses.
- [ ] P2.5 Store decisions, rejected approaches, TODOs, errors/solutions, and supporting context.
- [ ] P2.6 Extend "remember this" to save relevant screen/context for a named project.
- [ ] P2.7 Support semantic/time-filtered recall with source app, URL/path, timestamp, and evidence.
- [ ] P2.8 Add selective screen history and comparison with previously saved views.
- [ ] P2.9 Add repetition filtering, cross-session deduplication, retention controls, and low-value capture suppression.
- [ ] P2.10 Add private mode, app/window/site exclusions, and pause-screen-memory controls.
- [ ] P2.11 Delete selected memories/sessions and associated media/index records according to documented deletion semantics.
- [ ] P2.12 Protect local credentials and document when selected content is sent to cloud models.

Acceptance: save a project decision, restart AIRA, return to the project, and retrieve the decision and its original evidence. Private/excluded contexts are not captured or sent for analysis.

### Phase 3 — Persistent intention engine

Depends on: durable storage from Phase 2. Build this before broad autonomous action.

- [ ] P3.1 Convert spoken future/conditional instructions into structured intentions.
- [ ] P3.2 Show the understood condition, target, action, timing, and permission requirements; resolve missing or ambiguous details.
- [ ] P3.3 Implement lifecycle states: waiting, triggered, awaiting approval, running, completed, failed, cancelled, and expired.
- [ ] P3.4 Persist intentions and re-register monitors after restart.
- [ ] P3.5 Add time triggers using the user's timezone, including combined time/context conditions.
- [ ] P3.6 Add managed-process completion and success/failure triggers.
- [ ] P3.7 Add file appearance/change and download-completion triggers where reliable signals are available.
- [ ] P3.8 Add application/project activation triggers.
- [ ] P3.9 Add scoped terminal-text/error-reappearance triggers; correlate with the correct project/job.
- [ ] P3.10 Add website-change, user-return, and connected-device triggers through suitable adapters.
- [ ] P3.11 Support intention listing, editing, cancellation, expiry, and explicit retry policies.
- [ ] P3.12 Prevent repeated trigger handling and duplicate actions; reconcile interrupted executions before retrying.
- [ ] P3.13 Validate required context again before acting and expire stale approvals when the action changes.
- [ ] P3.14 Turn voice notes into reminders/actions without requiring a separate task manager.
- [ ] P3.15 Add external requirement/message-arrival triggers only through explicitly connected services and defined permissions.

Acceptance: "When this test run passes, tell me" survives restart and fires once for the specified successful run. A separate "next time I open this project" reminder surfaces when that project returns. Cancelled intentions never execute.

Intention records should include: ID, original instruction, parsed condition/action, project/target IDs, originating evidence, creation time, schedule/timezone, expiry, permission scope, lifecycle state, triggering event ID, execution ID, result, and retry policy.

### Phase 4 — Terminal actions, permissions, and audit

Depends on: Phases 1–3.

- [ ] P4.1 Add managed PowerShell sessions with repository working directories.
- [ ] P4.2 Stream command output, capture exit codes, watch long-running jobs, and support cancellation.
- [ ] P4.3 Explain terminal errors and continue permitted workflows from command results.
- [ ] P4.4 Define read-only, low-risk local, approval-required, and prohibited action policies.
- [ ] P4.5 Enforce approval in the executor for configured sensitive actions such as deletion, push, deployment, and messaging.
- [ ] P4.6 Add explain-before-act proposals with exact targets and material effects.
- [ ] P4.7 Bind approval to the displayed action, target, and current context; handle rejection/expiry.
- [ ] P4.8 Persist action evidence, tool calls, approvals, changes, results, and errors with secret redaction.
- [ ] P4.9 Add a context/action timeline and pending-intention view.

Acceptance: AIRA can run a permitted test command, explain the result, and hold an approval-required action until approved. The timeline shows what ran and why.

### Phase 5 — Coding-agent supervisor

Depends on: Phase 4 and a configured coding agent.

- [x] P5.1 OpenCode 1.18.35 selected and installed under .runtime/opencode on E; saved Gemini key supplied at runtime.
- [x] P5.2 CLI adapter starts selected-project jobs asynchronously, consumes JSON events, and reuses saved worker sessions for follow-ups.
- [ ] P5.3 Observe structured status/events and requests for permission or user input.
- [x] P5.4 Bound OpenCode to 10 steps/240 seconds, tests to 90 seconds and output limits; timeouts/errors require attention and never imply success.
- [ ] P5.5 Support repository explanation, bug investigation, code changes, tests, diff review, and documentation through the agent.
- [x] P5.6 Independently run the selected Node or unittest suite; require successful exit and a nonempty suite for a verified result. No-runner diagnosis is explicitly unverified. Arbitrary/custom test commands remain unsupported.
- [x] P5.7 Task board exposes bounded worker summary, changed text files, before/after test logs, actual exit and local diff. Other concurrent writers can affect those observations; attribution is not guaranteed.
- [ ] P5.8 Add optional independent verification by another agent when requested or justified by the workflow.
- [x] P5.9 Separate floating task board monitors job progress while other apps are foreground; voice tools can list/control jobs.
- [x] P5.10 SQLite preserves task IDs/history; connection loss cancels work, restart marks interrupted work for attention, no automatic replay. UI request IDs deduplicate retries. Live calls use the existing session call-ID deduplication.

Acceptance: the user asks AIRA to have the agent fix a failure. AIRA tracks the session, surfaces required input, reports the resulting diff, and announces completion only after the specified tests pass. The bounded first adapter is implemented and isolated coding verification passed; full spoken multi-app acceptance and approval/user-input workflows remain pending. See docs/CONCURRENT_DEMO.md for current scope and checked steps.

### Phase 6 — Contextual recall, unfinished work, and briefings

Depends on: Phases 2–5.

- [ ] P6.1 Surface relevant decisions/TODOs when the associated repository returns.
- [ ] P6.2 Surface person/website memories when reliable corresponding context is available.
- [ ] P6.3 Retrieve a previous error's solution when the same error recurs.
- [ ] P6.4 Track unresolved explicit intentions, builds, and agent jobs.
- [ ] P6.5 Infer likely abandoned workflows cautiously and offer resumption without inventing completion state.
- [ ] P6.6 Detect idle/away/return and summarize events since the user left.
- [ ] P6.7 Add relevance thresholds, deduplication, cooldowns, and urgency rules for proactive interruptions.
- [ ] P6.8 Combine browser requirements, repository context, terminal results, and agent progress into one workflow summary.
- [ ] P6.9 Preserve conversational/personality preferences and Focus, Coding, Casual, Silent, and Presentation modes.

Acceptance: after switching away and returning, the user receives a grounded briefing of completed work, failures, unresolved intentions, and pending approvals. Repeated context does not produce repeated interruptions.

### Phase 7 — Browser and desktop control

Depends on: Phase 4; contextual reasoning builds on Phase 6.

Incremental exception authorized on 2026-10-07: build bounded app/folder workflows now using the existing direct Live-tool path, before the general intention executor. This does not complete Phases 4, 6 or 7.

- [x] P7.A1 Add `open_app` and `open_folder` tools to both Live agents, awaiting the original desktop owner's verified result. Reject duplicate/overlapping requests and stale acknowledgements; cancel native input on transport loss or session cancellation.
- [x] P7.A2 Implement visible Start-button click and app-name search, then verify the foreground app. Use an exact installed-app registration when Windows Search does not expose a semantic result control. Real Notion launch passed.
- [x] P7.A3 Open File Explorer and type an explicit existing local folder into its verified address field; verify the resulting Explorer location. Real `E:\Havetobuild\AIRA` navigation passed.
- [x] P7.A4 Add progress above the character, enable/disable control, no-API test buttons, installed-app inventory and Ctrl+Alt+Escape emergency stop. Keep input limited to one controller with no model-written shell/code execution.
- [x] P7.A5 Validate automated protocol/device regressions, native startup/IPC boundaries and real controller cancellation during visible Start/search. Python/controller dependencies, caches and temp remain on E.
- [ ] P7.A6 User verifies voice-triggered Notion launch, folder navigation, stop/disable behavior and persistence after restart. Use the desktop palace as the only voice owner.
- [ ] P7.A7 Add and verify creating a Notion note with a requested title/body through its visible interface. Define supported workspace/page selection first; stop on ambiguous UI or unexpected dialogs.
- [x] P7.A7a Add `create_notion_note` to recall/capture and native IPC validation, with 160-character title / 2000-character content limits, no-API desktop fields, progress, cancellation and bounded timeouts. Current workspace only; start from a signed-in private page.
- [x] P7.A7b Implement semantic active-page/private-header/empty-editor guards, visible keyboard input, transient read-only UI retries and page-ID/title/body verification after reload. Do not automate login, existing-note edits, sharing or workspace changes.
- [x] P7.A7c Observe native page creation and complete a fixed synthetic private note whose title and two paragraphs survive reload. Validate offline safeguards and native smoke controls/permissions. These stages passed separately after UI-specific fixes; do not describe this as an uninterrupted fresh-page wrapper run.
- [ ] P7.A7d Accept one fresh full note request through voice and the desktop wrapper, plus cancellation/restart. Automatic approval review rejected additional persistent test-page creation to avoid duplicates. Some blank test pages remain; no deletion was attempted. Keep parent A7 unchecked until acceptance.
- [ ] P7.A8 Add and verify one specifically requested Windows Settings workflow. Opening Settings is available; changing settings is not implemented.
- [ ] P7.A9 Expand semantic UI operations and optional vision recovery only after the bounded workflows pass acceptance.

- [ ] P7.1 Add browser navigation, search, page reading, and tab comparison.
- [ ] P7.2 Add DOM-based element interaction and appropriate form filling with action-specific permissions.
- [ ] P7.3 Capture permitted URL/tab context for memory and context triggers.
- [ ] P7.4 Add Windows application open/close, switch, move/resize, and shortcut operations.
- [ ] P7.5 Add accessibility-based clicks, field entry, scrolling, and UI element identification.
- [ ] P7.6 Define supported applications, fallback behavior, and how ambiguous targets are handled.
- [ ] P7.7 Confirm resulting state after actions and stop when a dialog or context change invalidates the plan.
- [ ] P7.8 Preserve authentication/security boundaries around sensitive browser and desktop actions.

Acceptance: AIRA completes documented browser and Windows workflows, identifies controls semantically where possible, and reports observed outcomes.

### Phase 8 — Gesture and physical point-and-ask

Depends on: Phase 1 and executor permissions from Phase 4.

- [ ] P8.1 Add local webcam hand detection with deterministic gesture recognition separate from the LLM.
- [ ] P8.2 Implement pause gesture with debounce and visible feedback.
- [ ] P8.3 Add a pinch gesture for an eligible, currently displayed approval; never treat an unrelated gesture as blanket consent.
- [ ] P8.4 Add swipe context switching, hand scrolling, and two-finger volume control.
- [ ] P8.5 Add pointing calibration for the chosen monitor/camera arrangement.
- [ ] P8.6 Combine the selected/pointed region with screenshot context and voice questions.
- [ ] P8.7 Handle low-confidence recognition, camera loss, accidental gestures, and multiple monitors without unintended actions.

Acceptance: gestures reliably control the documented commands. "What is this?" addresses the intended region; uncertain pointing requests correction.

### Phase 9 — Reliability, packaging, and hackathon presentation

Depends on: the required preceding milestones.

- [ ] P9.1 Validate Gemini session limits, reconnect/resumption, device loss, and backend restart behavior.
- [ ] P9.2 Keep monitoring operational when the visible interface is hidden; define optional Windows startup behavior.
- [ ] P9.3 Route simple classifications and difficult reasoning appropriately; make additional model providers optional.
- [ ] P9.4 Avoid continuous expensive model calls where deterministic events or local processing suffice.
- [ ] P9.5 Polish orb transitions, timeline, intention states, approval views, and expanded memory palace.
- [ ] P9.6 Package and document Windows installation, configuration, operation, and recovery.
- [ ] P9.7 Rehearse the demo with genuine events and recorded validation evidence.
- [ ] P9.8 Document known limitations and separate demonstrated capabilities from future work.
- [ ] P9.9 Verify all AIRA-managed data, desktop caches, model/browser downloads, temporary files, environments, and build output remain on E during install and operation.
- [ ] P9.10 Validate disk-space monitoring, configurable retention, consistent local backup/restore, and cleanup behavior.

Acceptance: the end-to-end demo below works repeatedly and recovers from a controlled restart without losing its memory or intention.

## 7. Integrated demo script

- [ ] D1 Open the demo repository; AIRA recalls a saved technical decision and unresolved authentication failure.
- [ ] D2 Ask "Why is this happening?" while showing the failure; AIRA connects screen evidence to the selected project.
- [ ] D3 Say "Ask the coding agent to fix it. When the tests pass, prepare a local staging launch and ask me before starting it."
- [ ] D4 Show the saved intention, its target test run, and required local staging action approval.
- [ ] D5 Switch applications while AIRA monitors the real coding-agent session.
- [ ] D6 Surface a genuine request for user input/permission if the agent needs one.
- [ ] D7 Verify the resulting diff and passing tests; prepare the local staging launch without executing before approval.
- [ ] D8 Return to the computer and hear a briefing with changes, test evidence, and pending local staging approval.
- [ ] D9 Inspect the timeline and memory palace for the original decision, error, intention, action, and outcome.
- [ ] D10 Separately demonstrate restart persistence, private mode, and cancellation of a waiting intention.

Keep the hackathon staging demonstration local; verify the local server state if the launch is demonstrated. General deployment supervision remains a future configurable capability, not a requirement to provision cloud infrastructure for AIRA.

## 8. Validation principles

- A remembered fact needs traceable source evidence; uncertainty should remain visible.
- A test-pass trigger must refer to the correct project and run. Prefer structured process results over screen text.
- Retry/recovery must not blindly repeat an action whose outcome is unknown.
- A pending approval does not automatically authorize a materially changed action.
- Persistence means data survives restart; monitoring still requires the companion to be running. Reconcile missed events after sleep/restart.
- Verify integration boundaries with meaningful tests and real workflows. Do not check tasks merely because a UI or function exists.
- Measure voice latency, interruption behavior, capture quality, retrieval relevance, trigger accuracy, and duplicate-action prevention before making performance claims.

## 9. Evidence and completion log

For each completed implementation task, append the task ID, changed files, validation command/workflow, result, and commit/reference when available. Never invent a commit or test result.

| Date | Task IDs | Work/evidence | Result | Commit/reference |
| --- | --- | --- | --- | --- |
| 2026-10-06 | Planning | Read the supplied feature brief and reviewed upstream source | Initial inventory and dependency plan prepared; runtime unverified | Upstream `0e07ab7` |
| 2026-10-06 | Planning | Recorded revised Gemini/API decision and created this tracker | Documentation only; no application implementation | This file |
| 2026-10-06 | P0 planning | Reviewed first-run config/auth paths and current Google docs; added prerequisites and incremental test order | Existing AI Studio key covers Live authentication; runtime still unverified | Phase 0 prerequisite section |
| 2026-10-06 | Infrastructure planning | Compared local storage, Supabase Free, and a Firebase/local-media hybrid against cost and latency goals | Local SQLite/media recommended; user selection pending; no migration | Architecture options above |
| 2026-10-06 | Plan update | Recorded user's SQLite/local-media selection and E-drive-only application storage requirement; replaced Firebase setup tasks and updated handoff | Documentation only; local migration and path configuration remain unchecked | Sections 2, 5, 6, and 11 |
| 2026-10-06 | P0.1/P0.2/P0.12–P0.17 | Imported reviewed source on E; migrated active persistence/auth/media to SQLite/local profile/local files; encrypted settings and E-drive scripts/docs/dependency locks; built frontend; offline integration tests | Five tests pass; local UI/API/WS/media/storage protections verified; no Firebase infrastructure | `README.md`, `UPSTREAM.md`, `backend/tests/test_local.py` |
| 2026-10-06 | P0.3/P0.5; partial P0.4/P0.6/P0.10/P0.11 | User saved key under normal Windows account; text/embedding API checks, actual Capture/Recall Live greeting audio, browser launch and controlled server restart; fixed Windows dates/model IDs/incompatible affective flag/auth retry | Local launch ready; actual microphone, real-memory roundtrip, visuals, grounding, and image quota still need validation | `backend/check_live_agents.py`, `backend/app/routers/settings.py` |
| 2026-10-06 | User validation; partial P0.4 | User stated "Yeah it worked" and supplied an AIRA Settings screenshot showing text inference, 768-dimensional embeddings, and Live audio generation passed | Three connection checks confirmed by the user; image generation and real voice/memory workflows remain pending | User screenshot attached in this chat; no key values recorded |
| 2026-10-06 | User validation; partial P0.8/P0.9 | User answered "yes, it's working" after instructions to capture a distinctive spoken test fact, inspect its saved memory, and recall both details | Basic explicit save and same-run recall confirmed by user; backend-restart recall remains pending | Confirmation in this chat; no independent artifact inspection |
| 2026-10-06 | User validation; P0.10 | User answered "yes, even this is working" after instructions to fully stop/relaunch AIRA, inspect the existing memory, and recall its details without re-entering the fact | Real-memory restart persistence passed by user report | Confirmation in this chat |
| 2026-10-06 | User validation; partial P0.7 | User stated screen capture and screenshot memories are done after the shared-window description/save/display test instructions | Screen sharing and saved screenshot display passed by user report; webcam remains pending | Confirmation in this chat |
| 2026-10-06 | Partial P0.18; P0.19 | Added local counter-only SDK ledger, Settings usage meter, Standard rate estimates/missing-usage flags; single Live connection enforcement; mode/logout/disconnect/shutdown cleanup; configurable idle/duration/soft Live cost guards; device failure and late permission cleanup | 14 backend integration tests and 4 simulated browser-device tests pass; frontend builds; normal-account backend restarted; browser Settings shows meter with 0 recorded/active calls. No chargeable Gemini validation calls made. Real provider reconciliation/savings remain pending | `backend/app/core/usage.py`, `tracked_gemini.py`, `backend/tests/test_usage.py`, `frontend/scripts/test-media.cjs`, `README.md`; `.cache/screenshots/usage-settings.jpg` |


## 10. Decision log

| Date | Decision | Reason/impact |
| --- | --- | --- |
| 2026-10-06 | Extend Rayan; Windows only; one primary builder | Confirmed by the user |
| 2026-10-06 | Keep Rayan's Gemini Live and existing Gemini inference paths | User will obtain a Google AI Studio key; mandatory OpenRouter migration removed |
| 2026-10-06 | Build durable intentions before broad autonomous control | Continuity is the distinguishing requirement; downstream automation depends on reliable state |
| 2026-10-06 | Preserve the memory palace as the expanded memory interface | Reuse the chosen foundation while adding the desktop companion |
| 2026-10-06 | Validate the baseline, then add and test one feature at a time | Confirmed by the user; checkboxes require observed working behavior |
| 2026-10-06 | SQLite + local media + local FastAPI; replace Firebase/cloud persistence and identity | User selected the local option; no hosted infrastructure spend |
| 2026-10-06 | Root all AIRA-managed data, caches, logs, backups, temp files, and dependencies under `E:\Havetobuild\AIRA` | C drive has limited free space; current E-drive workspace is authoritative |
| 2026-10-06 | Keep Gemini API usage separate from the local infrastructure decision | Earlier Gemini Live decision remains; this plan does not claim fully offline inference |
| 2026-10-06 | AI AIRA — Memory Palace; local setup authorized | User requested branding and environment setup, followed by incremental baseline tests |
| 2026-10-06 | Same-origin local UI/API/media; one profile/tab; DPAPI user-bound secrets | Loopback startup retains authorization without Firebase; serve built React UI from FastAPI; saved key is bound to normal launch account |
| 2026-10-06 | Verified Gemini 3.8 Live/Flash and Gemini embedding 001; remove incompatible affective-dialogue flag | Upstream model/Windows/config compatibility problems must be resolved before claiming baseline voice works; image validation remains pending |


## 11. Current handoff — update at the end of each work session

**Status:** Local AIRA, approved desktop character, hotkey/wake activation and voice options implemented. Desktop control opens apps/folders and creates private Notion notes. Native launch/navigation/cancellation, private page creation, and synthetic-note title/body survival after reload observed. Full fresh-page voice acceptance remains in progress.

**Completed:** Reviewed foundation imported on E; AIRA branding; SQLite repositories/schema v1; local sessions/authenticated media; Windows DPAPI settings; E-drive environments/caches/temp configuration; dependencies/locks; Windows launchers; setup guide; model connectivity; user-confirmed explicit memory save/recall/restart and screen/screenshot workflow. Added local usage meter and P0.19 lifecycle/cost safeguards; 14 backend tests and 4 simulated device tests pass.

**In progress:** User acceptance of voice-triggered app/folder control, private Notion note creation, voice previews and detailed mode/device transitions. Hotkey, Hey AIRA and audible replies are user-confirmed. Notion note creation is implemented; its native stages passed separately. Specific settings changes and general UI interaction remain unimplemented. Broader inherited features and DPI/sleep behavior remain unverified; usage optimization stays deferred.

**Blocked:** None for local launch or basic model connectivity. Actual microphone/screen/camera tests require user interaction/device permission. Image generation access/quota remains unverified; do not enable billing or provision cloud infrastructure.

**Last validation:** 2026-10-08 Notion increment: 31 backend, 24 frontend, ten desktop/wake and six Notion workflow checks pass (71 total); one explicit native-cancel test is skipped by automated discovery. Production build passes (index-KkLMMtMx.js / index-Dhxt_oNR.css). Native smoke JSON confirms the new title/content controls and note-action guard alongside existing owner/overlay/voice/audio/wake/hotkey/E-drive checks. Its host remained alive after results and was stopped explicitly before normal relaunch; record this lifecycle limitation rather than claiming a clean smoke process exit. Native private-page creation was observed; the same identified partial test page was completed with title and two paragraphs verified after reload. Extra fresh-page wrapper testing was rejected by automatic approval review to avoid duplicate persistent pages. App/folder voice acceptance and a fresh complete note voice request remain pending. No paid Gemini call or microphone diagnostic was initiated for this implementation.

**User confirmation:** The user supplied a screenshot with all three Settings connection checks passing: text inference, embeddings, and generated Live audio. The configured key survived the normal-account server restart. After the voice-test instructions, the user reported that AIRA is actually working. They subsequently confirmed basic spoken-memory save and same-run recall, then confirmed the instructed full backend-restart memory check worked. P0.10 is passed by user report. Screen sharing and saved screenshot display are also user-confirmed; webcam remains pending, so P0.7 stays partially complete. The user subsequently reported that voice controls and memory management are working; P0.6 and the focused memory edit/delete check are accepted as passed by user report. Actual desktop mode switching acceptance remains pending; shared spoken switch tools are implemented and simulated checks pass.

**Next action:** In Notion, manually open a private page in the desired signed-in workspace. Say “Hey AIRA,” wait for “Hi Charan,” then “Create a Notion note titled Demo checklist with content Prepare the Memory Palace demo.” Verify one new private note, correct title/content after reload, and one accurate reply. Desktop → Desktop actions has equivalent title/content fields and a no-Gemini button. Inspect partial notes before retrying failures; Ctrl+Alt+Escape stops actions. Keep voice-triggered app/folder, restart/disable and note cancellation acceptance open until user confirmation. After note acceptance, select P7.A8's specific non-security Windows setting.

**Running app:** Desktop palace at `http://127.0.0.1:8000/palace`, reopened under the normal Windows account on 2026-10-08 (launcher session 9968), healthy backend and zero-length normal desktop error log. Use `Start-AIRA-Desktop.cmd` after reboot or if closed. Keep one desktop palace voice owner; a separate browser palace can replace its WebSocket. The launcher starts a backend if needed. Reopen local login if requested.

**Open technical decisions:** Coding-agent adapter, repository/browser context signals, Gemini recovery, retention/backups/index improvements. Electron is the selected desktop host. Baseline schema uses indexed parent paths plus JSON fields; semantic ranking remains application-side. All infrastructure/storage stays local.

**Latest steering:** User said “Okay build that” after the proposed Notion-note increment. Implemented new private notes in the currently selected signed-in Notion workspace. The existing Gemini Live session selects typed tools and local Windows code executes them. No Notion API key or new AI inference service is required, but Notion itself uses its existing account/cloud sync; AIRA's own memory storage remains local. Appearance remains unchanged.

**Changed files this session:** Backend desktop_action_service and recall/capture dispatch (recall tool logging now omits argument contents); desktop actions.cjs/windows_control.py/main.cjs and new notion_control.py; frontend desktop types, DesktopActionControls and styles; backend/desktop tests, six Notion workflow checks, read-only readiness diagnostic and explicitly invoked native-note diagnostics; guarded native-cancel script so ordinary test discovery cannot send desktop input; docs/DESKTOP.md, docs/DESKTOP-CONTROL.md and this tracker.

**Known limitations:** Basic spoken-memory save, same-run recall, recall after backend restart, screen sharing, and saved screenshot display are user-confirmed; voice controls and memory management are now user-confirmed. Manual mode switching, webcam, visual/image synthesis, and grounding remain unverified. Both Live agents now have switch_mode tools; native device acceptance is pending. Browser screen requests need a click to authorize display capture. Usage estimates are provisional: no historical billing reconstruction, unknown/missing metadata and search charges are flagged, soft Live limits exclude separate calls and can overshoot. Quiet capture closes after 45 seconds by default; edit `.env` and restart for a longer interval. Prompt compression, shorter replies, VAD/frame filtering, and persistent embedding caches remain pending. Reduced-dimensional embeddings are normalized. Image generation remains unverified; Google's current pricing page lists October 2, 2026 shutdown for the configured legacy `gemini-2.5-flash-image`, so select and validate a supported replacement before the image-generation phase. Capture/recall remain exclusive. Initial Electron overlay/tray/hotkey/local wake and spoken control are implemented; real wake accuracy, voice transitions and hardware acceptance remain pending. A bounded coding supervisor and two-lane task board are implemented (Phase 5); complete spoken concurrency acceptance remains pending. Intentions, gestures, retention/backup and full session resumption are not implemented. Optional sample population endpoints remain unvalidated. Legacy GLB material extension, frontend bundle size, stale Browserslist warnings, and TestClient deprecation warnings remain.

**Do not lose these constraints:** AIRA branding with attribution retained; Windows only; SQLite/local media/local backend; AIRA-controlled storage under `E:\Havetobuild\AIRA`; Gemini Live retained; no required OpenRouter migration; no cross-device V1; new features added and verified incrementally.

## 12. Using this plan in another chat

Suggested starting instruction:

> Read `E:\Havetobuild\AIRA\AIRA_PLAN.md`, inspect the current workspace and recorded evidence, and continue from the Current handoff section. Preserve confirmed decisions. Complete the next dependency-ready tasks, update their checkboxes only after validation, and refresh the evidence log and handoff before finishing.

Before continuing work:

- [ ] Read confirmed decisions, upstream distinctions, current handoff, and recent evidence.
- [ ] Inspect actual files and repository state; reconcile differences with the tracker.
- [ ] Select the next dependency-ready task and its acceptance criteria.

Before ending an implementation session:

- [ ] Update completed checkboxes and record partial/blocked work accurately.
- [ ] Add changed-file and validation evidence.
- [ ] Record decisions, limitations, and the next concrete action.
- [ ] Update the date and Current handoff section without including secrets.

The workflow checkboxes in this section are reusable session reminders, not product completion milestones.

Character visual revision — 2026-10-06: user compared the first character with the reference and requested a broad cropped face. Replaced the full-body silhouette with a wider dome continuing below the SVG edge; removed limbs, top bump, ground shadow, and decorative stars; moved eyebrows inward; clipped pupil movement to eye whites; enlarged/lowered preview and palace placement. Frontend build and browser visual check pass. User appearance approval remains pending. Evidence: `.cache/screenshots/aira-character-face-v2.png`.

Character visual revision 3 — 2026-10-06: replaced the custom dome path with a true circle with side margins; breathing now scales uniformly to preserve circular proportions. Thickened eyebrows from 5 to 8 units; slightly enlarged resting mouth; added the user-requested four-point star at the top. Side edges remain fully inside the SVG during poses; only the lower part continues beneath the bottom edge. Browser appearance check and production build pass. Evidence: `.cache/screenshots/aira-character-face-v3.png`. User appearance approval remains pending.

Character visual revision 4 — 2026-10-06: increased diameter from 428 to 460 SVG units while preserving the top edge and existing eyes/mouth/layout anchors. The widest point is now near the lower crop so the visible sides scarcely turn inward. Replaced the four-point mark with a small tilted five-point star fully inside the upper face; added subtle clipped blue/lavender corner glows. Build and browser visual check pass. Evidence: `.cache/screenshots/aira-character-face-v4.png`.

Character visual revision 5 — 2026-10-06: retained the original circular upper arc and 480×270 viewport; increased only lower-cheek/base width with Bezier extensions. Replaced the conventional five-point star with a small angled/curved four-point tuft at the crown, clipped inside the face. Added gradient purple rim light and blurred halo along the upper arc; corner glows retained. User rejected the contour join in the next turn; no revision-5 screenshot was saved.

Character visual revision 6 — 2026-10-06: one SVG ellipse now defines face fill, clipping, and the entire rim. Removed mixed arc/Bezier shoulder joins. Ellipse rx=230/ry=210, crown y=60 and crop y=270, preview width increased to 98%/560px (660px on large screens) for wider/flatter proportions. Full elliptical dark-blue gradient halo and crisp rim replace the partial purple outline. Eyebrows/eyes/star adjusted to fit inside. Build and browser appearance check pass; evidence `.cache/screenshots/aira-character-face-v6.png`. User appearance approval remains pending.

Character visual revision 7 — 2026-10-06: increased ellipse width from 460 to 472 SVG units, retaining ry=210, crown y=60, crop y=270, and preview sizing. Raised the curved crown star 9 units to overlap the head boundary. Added a broad 36-unit/18-blur halo plus an 18-unit/7-blur inner glow, expanded filter bounds, and softened the crisp rim. Build and browser visual check pass; evidence `.cache/screenshots/aira-character-face-v7.png`. User appearance approval remains pending; native overlay and actual Gemini-mouth regression remain open.

Character visual revision 8 — 2026-10-06: user accepted the design and requested one final horizontal-only widening. Increased rx from 236 to 244 (about 3.4%); vertical radius, center, viewport, preview dimensions, facial features, star, and glow unchanged. Production build and browser screenshot pass; SVG height measured identically before/after. P1.11 appearance marked complete based on user confirmation; evidence `.cache/screenshots/aira-character-face-v8.png`. Native hosting and actual Gemini-mouth validation remain open.


### Windows interaction slice — 2026-10-07

User authorized global activation, Hey AIRA, real character states and spoken mode switching. Implemented Electron host/launchers, one palace microphone/WebSocket/Live/playback owner, observer-only transparent click-through overlay, global cursor and output-energy bridge, configurable Ctrl+Alt+A, optional local English Windows grammar wake recognizer, shared mode/hide tools, native screen/window picker and browser permission banner. Wake is disabled initially; no idle Gemini connection or continuous screen capture. Desktop capture uses microphone audio without system audio. Detailed lifecycle and user checklist: docs/DESKTOP.md.

Validation so far: 19 backend tests including five companion tool tests; 11 frontend device/playback/mode hook tests; three wake process tests pass offline. English en-US recognizer available. Native smoke verifies transparent overlay, view-only role, capture-state IPC, shortcut registration and E-drive profile/session paths. Actual hotkey activation, wake accent/noise/latency, Gemini tools, source selection, native focus/click-through, DPI and sleep checks remain pending. Native screenshot: .cache/screenshots/aira-desktop-overlay.png; smoke metadata: .cache/desktop/smoke.json. Final production build/startup evidence follows.

Lifecycle: closing palace hides to tray; quit exits. Lock/sleep stops input/wake; resume rearms enabled idle wake only, without restarting Live. Stop Live returns to enabled wake; Pause all microphones disables wake and stops Live. Timed hide changes only appearance and uses a deadline in the kept-alive overlay. Tray/activation restore early. AIRA's specific new Electron 42 archive was moved from Electron's default C cache to E; explicit electron_config_cache now directs future downloads to E. Existing unrelated Electron 31 cache was left intact. DPAPI key is reused under the normal Windows account.

Final offline startup result — 2026-10-07: native smoke reports ownerReady=true, ownerControls=true, viewOnly=true, transparent rgba(0,0,0,0), captureState=true, hotkeyRegistered=true; profile/session both on E. Normal-account backend restarted (PID 16560) with the new tools. Production build passed; 33 offline tests pass. Physical microphone and Gemini tool invocation are intentionally still open for user acceptance.

Final handoff — 2026-10-07: production assets index-CE0R6NaN.js / index-D8gwwAl5.css; final native smoke passes all fields including normal palace startup/owner controls. Desktop opened under the normal Windows account with wake listening initially disabled, launcher session 20585; backend session 20598 (PID 16560) remains running. 19 backend + 11 frontend + 3 wake tests = 33 passed. No Gemini diagnostic or real microphone activation was run automatically. Next user test: switch to another app, Ctrl+Alt+A, then stop and enable Hey AIRA under Desktop. Follow docs/DESKTOP.md checklist and check off only after actual confirmation.

### Audio output recovery — 2026-10-07

- [x] Read-only Windows diagnosis: Cirrus Logic and Intel audio devices report healthy; Console/Multimedia/Communications default outputs all resolve to Acer V203H, volume 98%, not muted. This is a concrete routing mismatch when the user expects laptop speakers, although actual physical audibility still requires testing. Per-app Windows mixer overrides were not inspected or changed.
- [x] Recover output after speaker/default inventory changes; close obsolete contexts and discard stale queued/decoding audio. Explicit disconnected speaker falls back to Windows default. Microphone/Gemini session is not restarted by an output reset.
- [x] Use hardware output rate with 24 kHz PCM decoding; resume interrupted/suspended output; show playback failures in controls.
- [x] Add Desktop/Settings speaker selection, Refresh speakers, Reset audio output and two local tones using the actual PCM service. Speaker selection is for the current app run; Windows default can be changed separately for persistent system routing. No microphone or Gemini usage is required by the test; stop Live first.
- [x] Owner-only speaker-selection permission; overlay remains device-free. 17 frontend tests and final production build pass. Native smoke confirms audio controls, sink-selection support, default output context running at 48000 Hz, existing owner/overlay/hotkey checks and E-drive storage paths.
- [ ] User hears both tones through laptop speakers, then Gemini greeting/reply; Bluetooth removal/reconnection produces a subsequent audible reply with no stale output. Do not check off based only on successful API scheduling.

Changed: audioOutput/audioPlayback, AudioOutputControls, DesktopControls, PalacePage, SettingsModal, desktop styling/main permissions and smoke, playback regressions, scripts/Inspect-AiraAudio.ps1, docs/DESKTOP.md and this tracker. The diagnostic is read-only and stores temporary compiler/runtime files on E via Environment.ps1. First restart smoke encountered the previous launcher's backend-shutdown race (connection refused); rerunning after shutdown passed. Normal desktop reopened under the Windows account, launcher session 32290. Existing saved Gemini key and local memories retained. No paid diagnostics, new dependencies or system volume/default changes.

### Wake recognition diagnosis — 2026-10-07

- [x] User confirms audible AIRA replies after launching desktop and using Ctrl+Alt+A. Local speaker tones and Bluetooth reconnection are not separately confirmed.
- [x] Verify installed recognizer/default input without recordings or Windows configuration changes: en-US; Digital Microphone, 83%, unmuted for Console/Multimedia/Communications. Recognition failure cause remains unproven until the actual voice test.
- [x] Add 20-second local-only wake test, microphone activity, detected/rejected speech counts, allowlisted grammar matches/confidence and retained result. Test cannot launch Gemini. No raw microphone recordings, general speech transcripts or recognition logs are stored.
- [x] Continuous asynchronous Windows recognition, additional eye-rah/air-ah/aura/era aliases, optional persisted More sensitive cutoff 0.55; original 0.70 remains default. Stop/suspend/activation cancels testing and obsolete diagnostics are ignored.
- [x] Five wake process tests plus 17 frontend device/playback/mode tests pass. Production build passes. Actual Windows recognizer accepts synthesized local WAV “hey eye rah” at 0.939 and completes test without WAKE. WAV stored on E at .cache/wake-fixture.wav; no microphone or Gemini used by this fixture.
- [ ] Actual user's microphone/voice test; wake latency and false triggers; real activation after test and microphone change. Do not mark complete from synthetic recognition or UI listening status.
- [x] User subsequently confirms Hey AIRA now activates successfully. Detailed test metrics, accent/noise/latency/false-trigger checks and microphone-change recovery remain unconfirmed.

Changed: desktop/Wake-AIRA.ps1, wake.cjs, main.cjs, preload.cjs, wake tests; frontend DesktopControls, desktop service/types and styling; read-only Inspect-AiraAudio.ps1 accepts -InputDevices; docs/DESKTOP.md and this tracker. No added dependency, API key, cloud service or system audio setting change. If input is present but Windows keeps rejecting the wake phrase, consider a dedicated local wake-word model as a separate implementation decision; a custom Hey AIRA model is not included yet.

Final startup evidence: native smoke passes wakeControls/wakeTestGuard/wakeFeedback, existing audio/default sink and owner/overlay/shortcut checks; profile/session stay on E. The guard deliberately rejects the test during smoke, producing an expected IPC error in that diagnostic log without microphone or Gemini usage. Final assets index-B6n5R8JZ.js / index-BLfbt2tc.css. Normal desktop reopened with saved wake preference preserved; no actual user's voice recognition or paid activation was performed by automated validation. Cancel wake test and Stop conversation/capture cancel the test; normal enabled idle wake can resume afterward.

### Brief activation greeting — 2026-10-07

- [x] Replace recall opening instructions requesting a warm multi-sentence room/lobby welcome with exactly “Hi Charan.” followed by waiting. Apply the same requirement in the system prompt and exclude the greeting from the memory-answer structure. Wake and hotkey both open this recall session.
- [ ] User confirms the next actual Live activation says only “Hi Charan.” No paid greeting check was run automatically.

Changed: backend/app/agents/recall_agent.py and this tracker. This personal greeting uses Charan as explicitly requested; profile names and captured memories are unchanged. The capture agent's context question is unchanged.

Validation: five existing backend companion checks pass. AIRA's desktop/owned backend restarted under the normal Windows account (launcher session 78795); local health reports healthy. No microphone test or Gemini greeting call was run automatically.

### Selectable AIRA voice and greeting previews — 2026-10-07

- [x] Settings voice chooser with 30 documented Gemini Live prebuilt IDs/style descriptions, default Aoede; explicit Save voice persists in SQLite independently of the DPAPI key. Voice-only saves cannot erase the key; key changes preserve voice. Invalid voices are rejected before any settings write.
- [x] Apply saved voice to the next recall/capture connection, new artifact narration and connection check. Existing sessions keep their configured voice until restarted.
- [x] Preview the selected voice saying exactly “Hi Charan.” via the existing Gemini Live model/key. No microphone, screen or memories sent. Bound to 20 seconds/8 seconds maximum PCM, all returned PCM parts collected, completed greeting/transcription validated. Paid requests are tracked as voice_preview.
- [x] Cache successful previews under data/media/voice-previews on E, keyed by model/voice/greeting/version. Replays require no Gemini call; duplicate simultaneous requests are serialized. Incomplete, oversized or unexpected speech is not cached; errors never expose raw SDK messages or credentials.
- [x] Preview cannot replace an existing Live session, including a racing activation check. UI disables during voice/capture; close/select/stop/activation cancels pending playback. Already-sent bounded generation may finish/cache. Preview uses the chosen speaker/output recovery and actual output meter/character speaking state.
- [x] Seven new backend voice checks plus 19 existing backend checks pass (26 total); 20 frontend device/playback/mode/preview checks and five wake tests pass. Production build passes (index-DF8vXwXD.js / index-BLfbt2tc.css). Backend tests exercise all 30 voice IDs with a fake SDK and actual E-drive temporary cache; these do not prove provider acceptance/audibility.
- [ ] User auditions real Gemini voices, hears only Hi Charan, saves a preference, verifies conversation/capture/narration voice and restart persistence. Cached replay and live interruption acceptance remain pending.

Sources verified 2026-10-07: https://ai.google.dev/gemini-api/docs/live-api/capabilities#change-voice-and-language and https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/live-api/configure-language-voice. No extra key, service, dependency or cloud storage; only existing Gemini inference is used on a first preview.

Changed: core/voices, user_settings_service, voice_preview_service, settings routes, tracked Live exclusivity option, recall/capture/narrator voice config; frontend VoiceSettings/SettingsModal/settingsApi/API error handling/companion output state; backend/frontend regressions; desktop Settings smoke; docs/DESKTOP.md and this tracker. No actual Gemini preview or microphone diagnostic was run automatically.

Final handoff: native smoke passes all fields including voiceSettings {options:30, preview:true, save:true}. Hidden compositor required an initial capture before taking the modal screenshot; corrected .cache/screenshots/aira-voice-settings.png shows the actual chooser and controls. Normal desktop reopened (launcher session 23183), local health healthy, desktop error log empty. Saved wake settings/key and local memories preserved. Voice selection remains Aoede until the user explicitly saves another option.

### Windows control increment — 2026-10-07

User authorized laptop control, starting with visible app launching and local-folder navigation; subsequently requested resuming and testing the interrupted work. P7.A1–A5 implemented and verified. Remaining voice acceptance and Notion/settings increments are recorded explicitly above.

Evidence: real helper opened Notion after visible Start/search and verified its foreground process; Explorer navigation to `E:\Havetobuild\AIRA` verified actual Shell location twice. This Windows Search exposes no semantic result control, so the app workflow uses the exact registered installed-app shortcut after visible search. The explicit native-cancel diagnostic stopped at search, confirmed a cancelled result and exited input helper without requesting app launch. No Notion note or Windows setting was changed.

Final automated verification: 30 backend, 24 frontend and nine desktop/wake tests = 63 passed. Regressions cover both agent tools/prompts, original-connection acknowledgement, duplicates/overlap, late results, disconnect/unmount, safe process arguments, stop scope and existing voice/audio/media/wake behavior. Production build passes: index-CNC_9nmQ.js / index-CvUoHEjc.css. Backend tests stalled under the restricted account before cases ran; rerunning offline under the normal Windows account passed all 30 in 9.807 seconds.

Native smoke: all fields pass, including installedApps, desktopActions, desktopActionGuard, overlayActionGuard and stopHotkeyRegistered plus existing character/state/audio/wake/voice checks. An initial hidden screenshot returned UnknownVizError; retry passed. The smoke log's owner/overlay and wake-test rejections are expected guard checks. Normal desktop then reopened (session 41161, root Electron PID 4336), health reports healthy and desktop error log is empty. All normal backend/controller/profile/temp/cache/dependencies remain in the E workspace. No paid Gemini call or microphone diagnostic was performed automatically; enabled idle wake can run normally after reopening.

Next acceptance: wake AIRA and wait for its greeting before saying Open Notion; test explicit folder navigation, Ctrl+Alt+Escape, disabling actions and restart. Desktop action test buttons provide a no-API fallback. Only after this increment's user acceptance, add Notion note creation and a specified settings change. See docs/DESKTOP-CONTROL.md.

### Notion note increment — 2026-10-08

User authorized this increment with “Okay build that.” Added a typed new-note tool to recall/capture, local validation and native execution, desktop title/content controls, progress and existing emergency cancellation. Start from a signed-in private page; create only a new private plain-text page in that workspace. No Notion API key, extra inference or AIRA cloud infrastructure. Notion itself continues using its account/sync service.

Native evidence: observed Create new → Page and new private page identification. During development, UI transitions left blank test pages; further writes were stopped on ambiguity or exceptions. Corrected active-tab disambiguation, transient COM observations, banner/private detection, null empty values and the title edit control being miscounted as a paragraph. Normal keyboard input commits editor state; UIA SetValue was unsuitable. Completed the exact identified partial test note **AIRA verified demo 2026-10-08** with two paragraphs, then reloaded and verified the same page ID/private header/title/body. Synthetic interface/demo notes and some blank test pages remain; existing notes were not edited and no deletion was attempted.

Verification: 31 backend + 24 frontend + ten desktop/wake + six offline Notion workflow checks passed (71); the manual native-cancel case is skipped during automatic discovery. Production build passed (index-KkLMMtMx.js / index-Dhxt_oNR.css). Native smoke reports new notionControls/notionActionGuard and existing fields true; its process did not exit after recording the result, so only that exact smoke host was stopped before reopening the normal desktop. New focus checks stop typing if the editable field loses focus, including a switch to another tab in the same Notion window. No automated Gemini call or microphone test.

Approval-review limitation: additional fresh persistent test creation was rejected to prevent duplicate pages. Creation and writing/reload passed separately; do not claim an uninterrupted new-note run through the wrapper or actual voice acceptance. Keep P7.A7/A7d open until that check. Normal AIRA reopened via launcher session 9968, health healthy, desktop error log length zero. Next user check is the exact spoken new-note example in the current handoff, or the corresponding desktop button without Gemini usage.

User testing choice: the user selected **“I'll test it through AIRA's voice or desktop button.”** Do not initiate additional automated Notion write tests for this acceptance check. Await their observed result before checking P7.A7d or parent P7.A7.

### Current conversation fixes and Windows-Use assessment — 2026-10-08

User authorized implementing Windows-Use and the gaze/placement changes. These are now implemented and have passed offline regression checks, a production build and native smoke verification. Character gaze faces forward during listening/speaking/capture; native placement is bottom-center. Serialized audio scheduling has an 80ms initial buffer and a speaker-safe microphone gate with a 250ms output tail. “Interrupt AIRA while speaking” enables intentional barge-in for headphone use. Actual uninterrupted speech acceptance is still pending; microphone echo remains a possible explanation, not a confirmed diagnosis.

- [x] Finish/review conversation changes, including action-state overlay gaze priority, regression checks and production build. Previous run: 40 Node/frontend/desktop checks, nine Python desktop checks and 32 backend checks passed; native smoke verified centered placement, viewer gaze and Windows-Use UI/guards.
- [ ] User confirms bottom-center placement, stable gaze and uninterrupted replies on laptop speakers.
- [ ] User verifies intentional interruption preference and emergency stop.

Windows-Use 0.8.1 is installed in a separate E-drive environment with compatible Mistral 1.9.11 and uiautomation 2.0.29. Offline import/probe passed. Telemetry is disabled before imports; worker home/media/temp/cache are redirected to E. Recall/capture expose close_app and desktop_task, backed by owner-only IPC, bounded GUI execution, emergency cancellation, progress and SQLite task/step history at data/db/desktop-actions.sqlite3. Shell/file tools are omitted from the registry; additional execution checks restrict tasks/shortcuts/focus. GUI control is not an OS sandbox. Closing a window does not prove full app exit or discard unsaved work. Token usage is stored in worker history and is not yet combined with the main Usage panel.

Recommended proposed slice: keep AIRA Live voice/wake/character/memory, hand desktop tasks to a separate E-drive Windows-Use worker using the saved Gemini key for text inference (OpenRouter optional), stream action events back to AIRA and verify final application state. Maintain stop/cancellation and enforce task permissions in execution code. Restrict raw shell and destructive actions initially; prompt instructions alone are not an enforcement boundary. Benchmark step latency/token usage rather than promising lower cost or speed. Keep existing working app/folder tools available during evaluation.

- [x] Adopt Windows-Use on the user's explicit implementation request.
- [x] Audit and pin compatible top-level dependencies in a separate E-drive environment; actual offline import probe passed.
- [x] Disable telemetry and redirect worker storage/cache/temp before imports.
- [x] Add task adapter, execution policy, cancellation, visible progress and SQLite task history; offline checks passed.
- [ ] Test a Notepad open/type/close flow with synthetic text, including a save prompt and cancellation.
- [ ] Verify Notion window close versus full app exit, then user-authorized note creation and a specified reversible Settings task.

Primary sources reviewed: [repository/README](https://github.com/Jeomon/Windows-Use), [agent](https://github.com/Jeomon/Windows-Use/blob/main/windows_use/agent/service.py), [tools and memory paths](https://github.com/Jeomon/Windows-Use/blob/main/windows_use/agent/tools/service.py), [security policy](https://github.com/Jeomon/Windows-Use/blob/main/SECURITY.md), [telemetry](https://github.com/Jeomon/Windows-Use/blob/main/windows_use/telemetry/service.py), [dependencies](https://github.com/Jeomon/Windows-Use/blob/main/pyproject.toml). Implementation/native smoke has occurred; the interrupted paid Notepad acceptance task is not recorded as completed. Do not repeat automated persistent Notion write tests; the user chose to test those personally.

### On-request screen viewing and Stop/start status — 2026-10-08

- [x] Diagnose “Desktop · disabled”: the summary displayed wake-listener status, not desktop-control availability. Saved desktop-control and wake preferences were both enabled at inspection.
- [x] Separate Controls on/off from Hey AIRA ready/off/paused in the Desktop summary. Stop preserves both preferences; explicit disable remains respected.
- [x] Wait for prior wake microphone process exit before rearming; reject obsolete rearm requests and allow activation to reset a prior failed-listener latch.
- [x] Add look_at_screen to recall and capture. A direct “Can you look at this Notion page?” request obtains a single current-monitor JPEG without switching modes, starting continuous capture or saving a Memory Palace artifact. Screen text is untrusted content.
- [x] Windows app selects the monitor under the cursor without another chooser, for both a snapshot and explicit continuous capture. Browser capture retains its required picker. Owner/session/lock guards remain; no overlay device access.
- [x] Correlate transient frames with request ID and original connection; bound image size, timeout requests, reject stale session replacements and suppress late frontend delivery after stop/disconnect/unmount. No raw frame logging or local snapshot persistence.
- [x] Offline validation: 36 backend tests, 13 focused frontend checks, six monitor/wake checks and one desktop Stop/start lifecycle test passed (56). Production build passed: index-BKlq2_ym.js / index-C80X4KD7.css.
- [x] Native checks confirm screenViewBridge, screenViewGuard, desktopStatusSeparated, stopPreservesPreferences, owner/overlay guards, centered placement and viewer-facing gaze. No microphone or Gemini request was opened during the smoke runs.
- [ ] Full native smoke acceptance: wakeFeedback remained false and voiceSettings.options remained zero, although the controls rendered and no React error code was recorded. Hidden-window rendering affected the first gaze check; visible rendering passed it. Repeated bounded checks did not resolve the wake/catalogue failures. Keep these failures open; do not claim the full smoke test passed. Offline backend catalogue tests pass, but those do not prove the native UI loads it.
- [ ] User brings Notion forward, activates AIRA and asks it to look at the page; receives an answer grounded in the visible content without a chooser. This sends one image to Gemini and uses quota.
- [ ] User says Stop, then activates again; confirms Controls on, correct wake status and successful subsequent desktop commands. Actual speech/recognition/provider behavior is separate from mocked offline checks.

Normal desktop reopened after validation (launcher session 12918). Local health is healthy; settings API reports 30 voices, saved Gemini key present and readable, desktop control enabled and wake enabled. No secret value was printed. This confirms backend catalogue availability, not that the failing native smoke UI loaded it. Real spoken screen-reading acceptance remains pending.

### Reliable interruption increment — 2026-10-08

User reported intermittent interruption while AIRA continued working. Found two code paths: the speaker-safe microphone gate could suppress user speech during playback, and both Live receive loops awaited tool completion before reading provider interruption/cancellation messages. These are confirmed code issues, not proof of every cause of the observed behavior.

- [x] Default conversational interruption on when there is no saved preference; retain explicit off preferences. Allow enabled barge-in during the greeting hold. Continue using microphone echo cancellation/noise suppression.
- [x] Execute Live tools in ordered cancellable tasks without blocking recall/capture receive loops. Process interruption and toolCallCancellation, including transcription in the same event. Do not execute cancelled/replayed calls or send late success replies; cancel and await tool cleanup on disconnect.
- [x] Cancel active voice-owned desktop action IDs on interruption. Scoped cancellations do not stop an unrelated replacement action. Already committed changes remain; never claim rollback.
- [x] Clear queued speech on provider interruption; Stop clears narration even without an active Live session.
- [x] Add a local named Stop AIRA / Cancel AIRA grammar during conversation, narration and desktop work. It invokes the existing emergency stop without a Gemini decision. Switch a single local recognizer between wake and stop modes, await old process exit, and preserve enabled preferences. Guard preparation and overlapping voice/action startup races so they cannot disarm the stop listener.
- [x] Native synthetic WAV recognition emitted INTERRUPT for “stop eye rah” at 0.773 confidence using the 0.70 cutoff. Initial 0.85 cutoff rejected that fixture and was corrected. WAV is stored on E at .cache/interrupt-fixture.wav. No user microphone or Gemini request was used for this fixture.
- [x] Offline verification: 40 backend, 28 focused frontend and 15 desktop/wake/action tests passed (83). Includes cancelling an actual pending desktop-service future from both Live receive loops, rejecting its late result, greeting interruption, narration stop and recognition handoff races.
- [x] Final production build passed: index-C9Cmh9wK.js / index-C80X4KD7.css. Restarted only verified AIRA desktop/helpers/backend (launcher session 33734). Normal health healthy; one desktop instance and one local recognizer, desktop error log empty. Real spoken acceptance remains open.
- [ ] User interrupts a long spoken reply and greeting with a new instruction, then confirms a coherent new reply with no old queued speech.
- [ ] User says Stop AIRA during a long desktop task, confirms native input and playback stop, inspects partial changes, and successfully starts a fresh session. Test speaker/headphone microphone behavior; synthetic recognition does not prove live audibility or pronunciation accuracy.

Provider behavior verified against Google's [Live capabilities/VAD guide](https://ai.google.dev/gemini-api/docs/live-api/capabilities) and [Live tools guide](https://ai.google.dev/gemini-api/docs/live-api/tools). Local named-stop recognition is independent of provider VAD/tool latency. It can miss or falsely match speech; the global stop shortcut remains available. Previously recorded full-native-smoke wake/catalogue failures remain open and are not cleared by this increment's offline tests.

### Fast desktop increment — 2026-10-08

Superseded demo target: Notepad is not installed. The current direct append tool
targets Notion. See the next increment and
[docs/NOTION_CALCULATOR_FIXES.md](docs/NOTION_CALCULATOR_FIXES.md).

User prioritizes a quick single task, with parallel coding available for longer
work. Implementation and manual acceptance are tracked in
[docs/FAST_DESKTOP.md](docs/FAST_DESKTOP.md).

- [x] Warm direct-control and Windows-Use dependencies on startup without input or
  inference; reuse workers across requests and keep a single desktop input queue.
- [x] Direct app/folder opening and window closing; cached installed-app inventory,
  bounded readiness checks instead of fixed Search/Explorer pauses, faster literal
  name/path entry and accurate final checks.
- [x] Direct Notepad append tool wired into recall/capture voice agents and Desktop
  buttons, with unique-window/editor checks and text readback. Does not save.
- [x] Short acknowledgement instructions and common-action tool preference.
- [x] Cancel active owned worker and await exit before another action; shutdown
  closes both workers. Do not automatically replay unfinished requests.
- [x] Desktop elapsed/first-input timing in UI and tracked jobs; bounded metadata
  log on E and real execution timestamps for new history records.
- [x] Frontend production bundle built (index-Bu8mi4Ld.js). No tests, native actions,
  microphone sessions or paid inference run for this increment, at user request.
- [ ] User verifies repeat actions, Notepad readback, spoken routing, actual speed,
  generic fallback and stop/restart behavior. No latency claim established yet.
- [ ] Automated regression/native checks for the changed warm-worker protocol.
- [ ] Full voice timing from end of speech. Current elapsed metric excludes voice
  inference and backend scheduling. Screenshot fallback, multi-app planning and
  microphone-noise tuning remain separate pending improvements.

### Notion, Calculator and listening follow-up — 2026-10-08

- [x] Direct text workflow now appends to the current private Notion page, preserving
  existing content and checking readback. No blind resume/retry after a partial append.
- [x] More robust Notion document/menu observation and native bulk visibility query.
- [x] Direct basic Calculator operation and independent displayed-result check;
  recognize Calculator process variants/UWP host by its result control.
- [x] Desktop/Documents/Downloads resolution via Windows Known Folder APIs.
- [x] Explicit queue/replacement instructions keep new spoken commands available.
- [x] Silent mic output connection, stream watchdog and honest microphone-send
  freshness; local correlated Live status probe and unexpected-close feedback.
- [x] Frontend TypeScript compilation and production build passed
  (index-B7-3loIk.js); live voice and native acceptance remain unchecked.
- [ ] User verifies Notion append, 78 × 87 = 6786, Desktop navigation, command queue
  acknowledgement during work, microphone continuity and reconnect recovery.
- [ ] Automated/native checks. No tests or live automation run at the user's request;
  full reported-silence root cause and actual speed remain unverified.

Restart steps, scope, source references and manual script:
[docs/NOTION_CALCULATOR_FIXES.md](docs/NOTION_CALCULATOR_FIXES.md).

### Explicit-stop and reliable navigation follow-up — 2026-10-08

- [x] Default explicit-stop replies; optional provider speech interruption is
  opt-in, with lower sensitivity. Old enabled preference is migrated to off.
- [x] Local named-stop grammar accepts the requested long sentence and checks
  whole-phrase/word confidence and audio duration. Single filler words do not
  trigger that grammar; prompt does not treat them as task commands.
- [x] Notion uses the exact installed shortcut if Search drops its query.
- [x] Desktop navigation uses the observed Explorer Shell interface and checks
  the final filesystem location. Ambiguous tab interfaces stop safely.
- [x] Syntax and frontend production build checks passed (index-unOuYCMi.js).
- [ ] User verifies interruption behaviour, named stop recognition, Notion launch
  and real Desktop folder navigation. No live automation or paid testing run.

Restart and manual checks:
[docs/EXPLICIT_STOP_AND_NAVIGATION.md](docs/EXPLICIT_STOP_AND_NAVIGATION.md).

### YouTube browser and study workflow — 2026-10-08

- [x] User confirmed opening Notion, Calculator operation and real Desktop folder.
- [ ] Notion text entry still failed; repair/export deferred at the user's request.
- [x] Owned visible Chrome profile/cache on E:, observed YouTube search results,
  chosen-link opening and foreground managed-tab video-link reading.
- [x] Local transcript CLI installed; caption metadata/cache and explicit failure
  for unavailable/blocked captions. No additional API key or paid transcript service.
- [x] Background video-study lane with progress, persisted reports, cancellation,
  section summaries for long captions and cached summary reuse.
- [x] Same saved Gemini key for selectable Flash/Flash-Lite summary and Nano Banana
  Pro infographic. Defaults/config variables added; no silent paid model fallback.
- [x] Task-board controls, result selection, model settings, summary viewer,
  infographic preview and downloads on E:.
- [x] Syntax/build checks; live voice/browser/transcript/paid acceptance left to user.
  Final frontend bundle: index-B4Edq4b9.js / index-dTRgiRZ5.css.
- [ ] User verifies Chrome search/open, current-video link, captions, summary,
  infographic, cache reuse, download location and stop/restart.
- [ ] Add transcript/summary/infographic to Notion later.

Detailed handoff and manual sequence:
[docs/YOUTUBE_WORKFLOW.md](docs/YOUTUBE_WORKFLOW.md).

### Chrome profile-picker routing correction — 2026-10-08

- [x] Action history confirmed generic Chrome opening reached the personal profile
  picker; follow-up account selection through Windows-Use failed.
- [x] Enforce Chrome → AIRA browser routing at backend, Electron and native
  boundaries. Normalize tracked tool/timeouts/report; select the dedicated
  E-drive profile's Default directory explicitly.
- [x] Prompt distinguishes personal account selection from the AIRA YouTube
  workflow. No personal profile/account preference was changed.
- [x] Action history/user screenshot confirms dedicated Chrome opening bypassed
  the account picker. YouTube search acceptance is still pending.

### Chrome sandbox and failed search correction — 2026-10-08

- [x] History confirmed the exact query was sent as a generic Chrome desktop task
  and Windows-Use stopped without completing it; no dedicated search was recorded.
- [x] Enable Chrome sandbox in Playwright launch, removing its default
  `--no-sandbox` flag rather than hiding the warning. Existing windows need relaunch.
- [x] Recover bounded literal search commands from generic Chrome tasks at backend
  and Electron boundaries. Normalize job type/title/timeouts/report to YouTube.
  Unrecognized generic Chrome tasks fail promptly; GUI worker also rejects them.
- [x] Preserve validated observed video results through Electron IPC. They were
  previously omitted from the desktop worker response and could not reach reports.
- [x] Broaden fixed visible YouTube search selectors, verify the actual query URL,
  and distinguish search submission failures from missing video results.
- [x] Python AST syntax checks passed for four changed modules; Electron action
  controller passed `node --check`. No live automation or paid testing run.
- [ ] User verifies warning-free Chrome launch, visible search, observed task-board
  result links and selected-video opening after restarting Chrome and AIRA/backend.

### Backend refresh and signed-in browser setup — 2026-10-08

- [x] Latest task report identifies rejected generic Chrome wording: “Go to
  YouTube and search for 'atomic structure explanation'”. Stored old job types
  also show the backend was still running older routing code.
- [x] Both boundaries recover this literal single-search command. Memory/web
  research prompts exclude browser action requests, avoiding unnecessary calls.
- [x] Startup backend source fingerprint and desktop version guard prevent silent
  reuse of an older backend. Startup error windows remain open for inspection.
- [x] Add `Restart-AIRA-Desktop.cmd`: requires quitting the desktop first; only
  a verified workspace Python/uvicorn loopback process can be restarted.
- [x] Add `Sign-In-AIRA-Chrome.cmd`: normal installed Chrome uses AIRA's existing
  E-drive profile/cache. User signs in manually, closes that window, then AIRA
  reopens the persistent profile. No credentials or personal cookies are copied.
- [x] Python/JavaScript/PowerShell syntax checks passed; live acceptance stays
  manual as requested. No restart or sign-in was executed on the user's behalf.
- [ ] User accepts restart, search, selected-video opening and website login reuse.
- [ ] NotebookLM automation — future increment; sign-in preparation only here.

One-time account setup and restart instructions:
[docs/YOUTUBE_WORKFLOW.md](docs/YOUTUBE_WORKFLOW.md).

### Windows Python redirector restart correction — 2026-10-08

- [x] Read-only process inspection confirmed port 8000 belongs to the base
  Python child of this workspace's E-drive virtual-environment launcher.
- [x] Restart verification accepts that child only when its executable matches
  `pyvenv.cfg`, its live parent is the exact workspace interpreter, both commands
  match the fixed AIRA uvicorn/loopback/port arguments, and creation times agree.
  Direct workspace Python remains supported. Other processes remain rejected.
- [x] Revalidate the verified target's process ID and creation time before stop.
- [x] PowerShell syntax passed; read-only verification recognized the actual
  running backend. No process was stopped and no live app testing was performed.
- [ ] User reruns Restart-AIRA-Desktop.cmd and accepts the complete launch/search.

### YouTube search submission and result clicking — 2026-10-08

- [x] Dedicated search jobs recorded a results URL but zero videos. Subsequent
  visible-window inspection showed the homepage with the query and suggestions;
  the earlier URL check did not prove visible results. Dedicated routing is active.
- [x] Search visibly types the query, then always loads the fixed encoded results
  URL. Require a successful document response and exact query in both the
  automation URL and actual document location. Replaces the Enter/button fallback
  chain; no additional Gemini inference and no separate Enter instruction.
- [x] Restore/maximize the window belonging to the exact owned browser tab and
  verify document visibility. Two Chrome profiles were observed; this alone does
  not establish that the wrong window caused the failure.
- [x] Read visible watch links and titles from classic and newer result cards,
  without relying on a `ytd-search` ancestor. Require an actual results document;
  wait for readable videos, exclude known ads/headers/search suggestions/miniplayer/
  playlists and deduplicate video IDs. Success requires readable video results.
- [x] Open/click selects an observed title or thumbnail for the canonical video;
  duplicate links no longer reject the action. Verify the final video ID even
  when YouTube changes URL parameter order. A numbered open refreshes results
  on the current search page if the earlier read failed while it was loading.
- [x] Generic Chrome fallbacks recover “type X into the search box” without a
  separate Enter instruction and “click/open/play the first/second/etc. video”.
  Tool descriptions explain automatic submission and observed-result selection.
- [x] Failed result reading writes layout counts, document host/path, visibility
  and viewport dimensions to `.cache/desktop/youtube-layout.json`; no HTML,
  cookies, account data or screenshots.
- [x] Python and embedded DOM result script syntax passed. Six offline checks
  cover query encoding, document mismatch, HTTP failure, duplicate video clicks,
  owned-window restoration and hidden-window rejection. Frontend bundle unchanged.
- [x] User accepted visible automatic search and first-video opening. Latest
  persisted reports confirm both succeeded. Second-result click remains untested.

### Voice URL and selected-video study handoff — 2026-10-08

- [x] Logs confirm successful search/open followed by `look_at_screen` in a new
  voice session; no URL-read or study call/job was created. Exact spoken
  transcription is unavailable; no caption/provider error occurred in a study job.
- [x] Expose existing `current_youtube_video` to recall and capture voice tools.
  Return observed URL/title directly; serialize with desktop navigation and
  return busy when another desktop action is running.
- [x] Read the selected owned video when the overlay takes focus. Foreground
  personal Chrome remains excluded; verify the actual document video ID.
- [x] Route URL questions to the URL reader and summary/transcript/infographic
  requests straight to `youtube_study`; no preliminary screenshot or pasted link.
- [x] Ten offline browser checks and four offline voice-wiring checks passed;
  changed Python syntax passed. Async checks needed execution outside the Windows
  sandbox because its local socket pair was blocked. No real browser/provider
  calls or production task-store writes were made by these checks.
- [ ] User verifies URL reading, captions and summary on the task board after
  restart. No live voice, caption network or paid generation test run here.
- [ ] Notion transcript/summary transfer — later increment.

### Summary discovery and voice session continuity — 2026-10-08

- [x] Actual summary jobs `278623e2ff` and `58259169dc` succeeded for the selected
  atomic-model video. First generation fetched captions; the second reused both
  caches. Outputs: `data/media/youtube/jobs/<job-id>/`.
- [x] Task-board header shows “Summary ready”. Latest-summary read/download actions
  are prominent; the full result opens at the top, above task history.
- [x] Ledger identifies estimated-cost stops after about 74 and 92 seconds.
  Earlier idle stops and audio-send/connect timeouts were separate causes.
- [x] User disabled the estimated cost cap. `.env`, `.env.example` and defaults
  use cost cap `0`, idle `120s`, duration `600s`. Usage recording stays active.
- [x] One bounded background audio sender, with six pending PCM frames maximum.
  Stale queued frames are discarded under backpressure; network writes no longer
  block websocket commands. An 8-second upload timeout ends a broken session
  with a specific reason. Shutdown cancels/drains the sender.
- [x] No microphone transmission before the server handshake. Connection-start
  allowance increased from 15 to 30 seconds.
- [x] Announce stop reasons before closing the socket and include reasons in
  inactive-session messages. Planned limits are notices, not connection errors;
  startup errors include their originating session ID to reject stale events.
- [x] One automatic fresh voice connection per explicit activation on a transport
  or startup failure. Stop cancels a pending retry; limits never auto-restart.
  Old speech/accepted commands are not replayed. A fresh connection does not
  resume the previous Gemini conversation context.
- [x] Four audio-queue, eight existing usage/session-stop and four frontend voice
  recovery checks passed offline. No real microphone/browser/provider test run.
- [x] Final TypeScript/Vite production build passed: `index-D29iBjNs.js` with
  `index-dTRgiRZ5.css`. Python syntax checks passed; README/defaults updated.
- [ ] User accepts summary discovery and multi-step voice continuity after one
  desktop/backend restart. Local limits do not guarantee provider/network uptime.
- [ ] Infographic and Notion-transfer acceptance remain separate steps.

### Saved summaries in Notion and NotebookLM mind maps — 2026-10-08

- [x] Audited a successful summary job and two local private-only Notion guard failures.
- [x] Export the complete stored summary to a new or selected/exact-title existing
  editable Notion page; preserve old content and verify body/title after reload.
- [x] Replace Private-badge gating with editability/lock checks. New page creation
  verifies the new page permission; the original need not be private or editable.
- [x] Bounded Unicode summary entry, source ownership/path checks, and durable
  destination results. No automatic repeat of partial exports or generation.
- [x] NotebookLM creates a new notebook by user decision; supports optional existing
  notebooks, imports the observed/provided YouTube link, selects its source, generates
  via visible Mind Map controls and verifies the opened diagram.
- [x] Signed-in AIRA Chrome profile on E:, task-board buttons and shared voice tools.
- [x] Offline backend/native/IPC checks and frontend production build.
- [ ] User accepts new-page export, existing-page preservation and exact-title search.
- [ ] User accepts NotebookLM sign-in, source import, generation and diagram opening.
- [ ] User accepts cancellation/partial results and voice continuity with both flows.

Details, log findings, commands and verification:
[docs/STUDY_DESTINATIONS.md](docs/STUDY_DESTINATIONS.md).
Google/Notion destination storage is external by explicit request; AIRA storage
and caches remain on E:. Earlier Live logs show provider upload/handshake timeouts,
separate from Notion's local guard; provider uptime is not guaranteed by these fixes.

## Visual invoice coding demo — 2026-10-09

User approved the proposed voice-driven invoice repair demonstration. The
dedicated working fixture is `data/projects/invoice-showcase`; the earlier
`aira-demo` working copy is already fixed and was preserved.

- [x] Prepare a fresh, deliberately broken invoice module on E: with five Node tests.
- [x] Add `/invoice-demo` with subtotal/discount inputs and actual source evaluation.
- [x] Show the observed coding commands, tool progress and test output live.
- [x] Integrate the existing coding worker; retain independent before/after tests and diff.
- [x] Refresh the preview automatically when source changes; tie passed status to source hash.
- [x] Add project selection, explicit fix button, VS Code display and voice demo opening.
- [x] Add explicit reset for the dedicated recognized fixture; block active-work resets.
- [x] Separate each reset generation from historical coding results.
- [x] Keep preview/test processes bounded and drain runtime jobs at shutdown.
- [x] Pass 32 relevant offline checks, TypeScript/production build and desktop JS syntax checks.
- [ ] User tests opening the dedicated Electron demo window after restart.
- [ ] User tests spoken fix with real Gemini/OpenCode, live output and automatic refresh.
- [ ] User tests a Windows/browser request while coding continues.
- [ ] User tests reset and repeats the voice demo.

No real inference, account write or native desktop acceptance was run this turn.
The command log is a visible panel; arbitrary model-authored shell commands
remain disabled. Preview/tests/files/history stay on E:, and Gemini inference
uses the already saved key. Full instructions and verification:
[docs/INVOICE_DEMO.md](docs/INVOICE_DEMO.md).

### Presentation revision — 2026-10-09

The user wants to describe a bug in an ordinary live app, then watch AIRA open
VS Code, investigate/edit and return to the corrected localhost application.
The app must not expose the expected answer or tell the user how to fix it.

- [x] Make `/invoice-demo` a clean Invoice Studio UI: amount, discount and total only.
- [x] Move previous coding/repair/reset controls to `/invoice-workbench`.
- [x] Add `repair_invoice_app(problem)` with the user's observation and known project mapping.
- [x] Visibly open invoice.js in VS Code before coding; editor failure prevents edits.
- [x] Investigate real source/tests; repair instructions do not supply a predetermined formula.
- [x] Run independent verification, then bring the existing invoice window forward.
- [x] Preserve invoice input values and refresh the calculation from edited source.
- [x] Give a short cause/change explanation using the verified worker report when recall voice is active.
- [x] Pass 26 relevant offline flow/API/notification/IPC checks.
- [x] Pass final TypeScript/production build and changed-module syntax checks.
- [ ] User accepts the complete ordinary-app → VS Code → corrected-app voice flow.

The invoice mapping is automatic; generic VS Code workspace discovery remains
unimplemented. Source edits are real CLI worker edits displayed by VS Code,
not simulated typing. Actual inference, editor focus and spoken explanation
remain untested live by Codex; the user performs acceptance.

### Deterministic rehearsal revision — 2026-10-09

Supersedes the default OpenCode investigation in the invoice presentation above.
The user requested a repeatable known-fault repair with two removable batch
launchers. This is a scripted scenario with real source/output changes, not
general autonomous bug diagnosis.

- [x] Default `AIRA_INVOICE_REPAIR_MODE=deterministic`; preserve optional agent mode.
- [x] Exact percentage-discount repair of the recognized faulty invoice.js.
- [x] Run five unchanged tests before/after; bind verification to source version.
- [x] Route registered-project generic fix requests through the same VS Code/app sequence.
- [x] Freeze repair mode at job submission and keep other projects on OpenCode.
- [x] Add Create-Fault.cmd and Fix-Fault.cmd with actual output verification.
- [x] Keep voice repair independent of the two removable .cmd launchers.
- [x] Refuse unknown code, altered tests/config, stale generations and competing writers.
- [x] Read existing job ledger without changing active-job status; block helper mutations during coding.
- [x] Retain ordinary localhost UI and developer evidence on the separate workbench.
- [x] Pass six deterministic/helper, fifteen supervisor, two API and one notification checks.
- [x] Pass TypeScript/production build and launcher/module syntax checks.
- [ ] User rehearses wrong ₹190 → spoken fix → VS Code → correct ₹180.
- [ ] User repeats Create/Fix helpers, then optionally deletes just the two launchers.
- [ ] User accepts real voice recognition, editor focus and completion explanation.

This mode makes no coding inference call; existing voice still uses Gemini.
The default working fixture is left faulty for rehearsal. Instructions and
boundaries: [docs/INVOICE_DEMO.md](docs/INVOICE_DEMO.md).

### Chrome invoice and visible generated tests — 2026-10-09

User requested browser localhost presentation, automatically written tests and
actual terminal results, with YouTube preserved in a separate tab.

- [x] Replace the embedded invoice desktop window with AIRA Chrome's localhost tab.
- [x] Track/reuse separate invoice and YouTube tabs; preserve inputs and selected video.
- [x] Reopen local invoice authentication when needed without a voice connection.
- [x] Write invoice.regression.test.js with three scripted regression cases per repair.
- [x] Retain the original five independent tests and run all eight after repair.
- [x] Generate a fixed VS Code process task and show the new test file automatically.
- [x] Run it in the integrated terminal; print All tests passed (8/8) only after actual success.
- [x] Require fresh run-ID/source verification before returning to the Chrome invoice tab.
- [x] Retain the local report when terminal presentation fails; never claim complete success.
- [x] Reset only recognized generated artifacts; preserve unrelated/modified configuration.
- [x] Pass offline Node, fixture/helper, editor, supervisor, API, browser/NotebookLM and IPC checks.
- [x] Pass frontend build and changed native/module syntax checks.
- [ ] User accepts real Chrome opening and tab-preserving YouTube navigation.
- [ ] User accepts the visible generated-test → terminal → corrected-browser sequence.
- [ ] User rehearses workspace trust/default build shortcut once in VS Code.

These replace the embedded-window/five-after-test presentation details above.
The invoice source repair and three new test cases remain a deterministic known-bug
scenario. No live GUI/site/voice acceptance was performed by Codex.

### Timed phone reminders with Twilio — 2026-10-09

User requested a one-number demo: speak a delay or clock time, then receive a
short reminder call when due.

- [x] Add encrypted Twilio Account SID/token/calling number/personal number settings.
- [x] Add independent SQLite reminder ledger and background scheduler in backend lifespan.
- [x] Register schedule/context/list/cancel tools in both Capture and Recall voice modes.
- [x] Resolve relative delays and explicit clock times in IST; reject past/ambiguous tool times.
- [x] Persist pending reminders across conversation disconnect and backend restart.
- [x] Atomically claim before dispatch; preserve request IDs; never redial uncertain calls.
- [x] Add two-minute overdue grace, then mark missed without placing a late call.
- [x] Send escaped inline TwiML with Say/Hangup; poll call status without a public webhook.
- [x] Add Settings setup/manual rehearsal and reminder status/cancellation on the task board.
- [x] Pass 15 isolated reminder tests and 5 existing voice interruption regression tests (20/20).
- [x] Pass frontend TypeScript and production build.
- [x] Verify the running backend and enabled, empty phone setup form in the browser.
- [x] User saves a real Twilio account; credentials and numbers verified against saved setup.
- [ ] User rehearses one real one-minute call and a spoken command on their device.

The first restricted test runs stalled in Windows asyncio socket initialization;
outside-sandbox tests passed. One existing one-second regression timeout passed
on isolated rerun and the final complete 20-test run. At initial implementation,
no real Twilio requests or calls were made and no credentials were saved. Local backend
operation, awake computer and internet are required; call initiation does not
guarantee exact-second ringing or that the recipient heard the message. See
`docs/PHONE_REMINDERS.md` for setup and failure behavior. Browser evidence is
saved in `.cache/phone-reminders-setup.jpg`.

### Missed-call correction — 2026-10-09

The user reported that no call arrived. The reminder ledger showed definitive
Twilio rejections, with no Call SID. Read-only checks confirmed valid credentials,
an active Trial account and no created calls. A diagnostic captured HTTP 400:
"Invalid or disallowed parameters provided - trial accounts have limited parameter access".

- [x] Read account type before dispatch; use the supported To/From/template Url
  request for trials, retaining inline custom reminder speech for Full accounts.
- [x] Preserve safe provider error messages and HTTP status instead of hiding them
  behind code 0; redact credentials, account IDs, encoded Basic auth and numbers.
- [x] Persist and show trial demo audio mode through the final call status.
- [x] Migrate existing reminder databases while preserving saved records.
- [x] Pass 25 reminder and voice-interruption regression tests, plus frontend build.
- [x] Activate the updated backend and verify a real trial call reported ringing
  in both AIRA and Twilio. No automatic retries or uncertain redials were used.

Trial calls currently play Twilio's template demo audio, not the saved reminder.
The account upgrade is detected on subsequent calls. Spoken-command device
rehearsal and confirmation of hearing the phone audio still require the user.

### Telegram notification after a verified repair — 2026-10-09

- [x] Add optional Telegram settings, disabled by default, with a masked bot token value in application settings.
- [x] Add Configure-Telegram.cmd: hidden token input, bot identity check, private chat discovery and preservation of existing .env settings.
- [x] Hook successful coding fixes after persisted completion and passing local tests; require invoice terminal verification when present.
- [x] Skip investigations, failures, cancellations, unchanged invoice source and historical completed jobs.
- [x] Persist one send attempt per completed run; no automatic retry or restart replay.
- [x] Show delivery status separately on the task board; preserve the verified repair on transport failure.
- [x] Keep message content to a short result, test count and task ID; no raw logs, prompts, code or credential logging.
- [x] Pass 27 mocked Telegram, task-supervisor and repair-announcement regression checks, frontend TypeScript/production build and setup PowerShell syntax validation.
- [ ] User creates a dedicated BotFather bot, sends /start, runs the local setup helper and restarts AIRA.
- [ ] User verifies one real Telegram message after the invoice repair and eight passing tests.

See `docs/TELEGRAM.md`. No real Telegram request/message or account configuration
was performed by Codex. Notification setup is separate from the Gemini key;
credentials remain on E: in the ignored root .env. Internet access is required
for the short Telegram message, with no public hosting or additional LLM call.

### Invoice voice launcher dispatch fix — 2026-10-09

Two recent `show_invoice_demo` jobs reached the desktop controller but failed
in 0 ms of worker execution. The warm native action-server allowlist omitted
`show_invoice_demo` and `run_invoice_tests`, rejecting both before their native
handlers could run. The browser handlers and Electron URL validation were present.

- [x] Register both invoice actions in the native worker dispatch allowlist.
- [x] Exercise the actual server and native dispatch functions with mocked Chrome/editor/history I/O, preserving URL/run ID and request IDs.
- [x] Verify unknown actions and invalid request IDs still fail before input, and invoice actions cannot enter the Windows-Use GUI worker.
- [x] Pass 44 offline checks: 3 worker-dispatch, 13 browser, 11 Electron action, 16 supervisor and 1 invoice editor check.
- [ ] User quits AIRA through the tray, restarts the desktop host to reload its warm workers, and repeats “Hey AIRA, show the invoice demo.”
- [ ] User confirms the complete spoken repair sequence, including the visible terminal tests and corrected localhost tab.

No live GUI/voice run or invoice source mutation was performed by Codex for this
fix. Existing failed jobs remain historical; a fresh spoken request starts a
new job. No frontend rebuild is needed for this Python worker change.

### Single-window close and Google Maps search — 2026-10-09

- [x] Add `open_maps` and `search_maps` to both voice modes, the task queue,
  Electron validation/timeouts, native worker dispatch and frontend action types.
- [x] Handle “go to Chrome, go to Maps and search for X” as one submitted Maps
  search. Recover literal Maps searches when the model selects generic Chrome
  desktop_task. Preserve YouTube and invoice tabs in a separate reusable Maps tab.
- [x] Use Google's documented URL-encoded Maps Search URL; verify Maps host/path,
  exact visible search-box query and visible place heading/results list before
  success. Consent, loading or missing results stop with an attention message.
- [x] Improve graceful close matching for VS Code/Chrome aliases, title suffixes
  and minimized windows, including Calculator's hosted/offscreen controls.
  Send WM_CLOSE to the identified window directly and verify it disappeared.
  Multiple matching windows and save prompts never force closure or discard work.
- [x] Add desktop Settings controls, example spoken commands and restart guidance.
- [x] Pass 49 offline desktop Python checks and 12 Electron action checks.
- [x] Pass 28 backend desktop/supervisor/YouTube voice regression checks and the
  frontend TypeScript/production build: 89 offline checks passed in total.
  Backend asyncio checks required execution outside the Windows sandbox; the
  sandboxed attempts stalled and their owned diagnostic processes were stopped.
- [x] Verify the real Google Maps page for “Charminar, Hyderabad” in a temporary,
  unsigned-in headless Chrome context using the implemented search/readiness
  function. The requested query and Maps place heading/results passed.
- [ ] User quits/restarts AIRA and confirms both spoken workflows, including a
  minimized app, unsaved-work prompt and Maps search for a real place.

No user application was closed during automated checks. Closure verification
uses mocked Windows controls; voice recognition/tool selection and visible
native-window acceptance remain user checks. Restart a separately launched
backend too, so the new Live tool declarations are loaded.

### Disable music and interface effects — 2026-10-09

The user requested no background music or sound effects and explicitly chose to
keep AIRA's spoken replies enabled.

- [x] Remove ambient/room music startup and the music controls on desktop/mobile.
- [x] Remove artifact-click chimes and room/map transition tones.
- [x] Remove the unused ambient music hook and music/effects engine.
- [x] Preserve voice reply playback, microphone capture, voice previews and
  explicitly requested speaker diagnostics.
- [x] Pass the frontend TypeScript/production build and all 12 existing playback
  checks. Update one stale test expectation to the already implemented explicit
  stop default and v2 preference key; speech behavior itself is unchanged.
- [ ] User refreshes/reopens AIRA to load the rebuilt UI and confirms silent
  navigation/artifact clicks with spoken replies still enabled.
