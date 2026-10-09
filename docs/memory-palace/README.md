# Personal Memory Palace

The supplied Sai Charan brief is implemented as **181 independently addressable
memories in 15 rooms**. Open `/memories`, or select **Memory rooms** in `/palace`.
The rooms also exist in the 3D palace. Signing into the local profile imports
them once, without Gemini calls. Existing captured rooms are retained.

## Context files and agent recall

- `seed-source.txt` preserves the supplied brief, including accuracy and privacy rules.
- `backend/app/data/personal_memory_seed.json` contains the atomic seed objects.
- `scripts/build_personal_memory_seed.py` documents the deterministic conversion,
  including splitting people, priorities and specifications into independent facts.
- Every record carries a source filename and original question's line number.

SQLite stores these as ordinary palace artifacts with a `personalMemory` field.
There is one canonical record, shared by cards, API queries and the agent.
The import marker prevents reopening AIRA from restoring deleted memories or
overwriting corrections. Modifying the JSON after import does **not** overwrite
existing data; use corrections or a separately versioned migration.

The Live `search_memories` tool retrieves these current records before generic
captured artifacts, returns exact room/ID references, and publishes clickable
references in the recall conversation. Agent artifact edits use the same audited
correction path. The prompt requires grounded answers, labeled inferences,
explicit conflicts, unknown answers, and no confidential details or secrets.
Illustrative sample artifacts are excluded from personal search results.

## Retrieval and accuracy

Personal queries use local semantic-concept expansion and weighted lexical
ranking, with separate retrieval for multi-part questions. This supports the
brief's questions without a key. It is deliberately a bounded local retriever,
not an embedding model; unfamiliar paraphrases may return unknown. The existing
Gemini vector search remains available for ordinary captured artifacts.

The text query interface returns an **extractive answer**, quoting only retrieved
assertions. The Live agent can phrase an answer using the same supporting records.
Every used record is returned in `references`. Unknown responses use exactly
`I don't currently have a memory about that.` Inference and uncertain labels are
preserved. Conflicts are reported for shared assertion keys when corrected active
records disagree; arbitrary contradictions outside those groups require review.

Created/import date is October 9, 2026. Historical timeline dates stay null.
Relative phrases such as “this week” and “this month” describe context as of that
date, not rolling future commitments. The detail dialog lets users add an actual
event date without changing the import date.

Corrections increment `version` and retain the complete previous fields in
`history`. `expected_version` prevents concurrent corrections from overwriting
one another. Active and uncertain memories are retrieved; outdated and superseded
ones stay browsable but are excluded from current answers. Credential-like values
are rejected by personal corrections and artifact creation.

## API and verification

All endpoints use the existing authenticated local session:

- `GET /api/v1/personal-memories`: rooms and records, including history.
- `GET /api/v1/personal-memories/search?query=...`: relevant memories.
- `POST /api/v1/personal-memories/query`: `{query, room_id?}` → grounded answer and references.
- `PATCH /api/v1/personal-memories/{id}`: `{expected_version, memory?, status?, kind?, event_date?}`.

Run from the project root:

```powershell
$env:PYTHONPATH='backend'
.venv/Scripts/python.exe -m unittest backend.tests.test_personal_memories backend.tests.test_local -q
Set-Location frontend
npm.cmd run build
```

The integration tests use an isolated temporary SQLite database and no real API
requests. They cover source provenance, all rooms/artifacts, query references,
unknowns, conflicts, status filtering, revisions, concurrent imports, event dates,
authentication, credential rejection and the agent's corrected context.
