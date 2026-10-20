# Architecture Decision Records

Short entries, newest last. Status: accepted / superseded (with date).

## D1: Offsets point into the raw uploaded file
Date: 2026-10
Status: accepted

**Context.** .tex cleaning (stripping commands/math/environments) loses
characters. The frontend must highlight spans in what the user actually sees
in their editor.

**Decision.** `start`/`end` always reference the raw uploaded file, counted
in Unicode code points (characters), not bytes.

**Consequences.** The LaTeX parser must maintain an offset map; cleaned-text
spans must map back to raw source by construction. If a span is ever
unrecoverable, that is a parser bug, not a data condition to handle silently.

## D2: Partial failures return HTTP 200 with in-body degradation
Date: 2026-10
Status: accepted

**Context.** A 10-paragraph upload where one paragraph fails segmentation
should not fail the other nine.

**Decision.** Whole-request failures (empty input, oversize file, bad type,
unparseable tex, internal error) return 4xx/5xx with an ErrorResponse body.
Recoverable per-paragraph failures return HTTP 200 with `error` set on the
failed paragraph and `parse_warnings` populated. Rule: if any paragraph can
be served, return 200.

## D3: Sentence IDs are deterministic per content
Date: 2026-10
Status: accepted

**Context.** /feedback joins on sentence IDs across requests. Random IDs
make feedback analysis depend on client-side bookkeeping.

**Decision.** IDs are `p{index}` and `p{index}s{index}` within one response,
derived deterministically from the input content, so re-analyzing the same
text yields the same IDs.

## D4: request_id is generated server-side
Date: 2026-10
Status: accepted

**Context.** Clients could otherwise forge or collide with IDs that
feedback events later join on.

**Decision.** `request_id` is a server-generated UUIDv4 present on every
response including errors. Clients never supply it to /analyze; they copy
it from the response into /feedback.

## D5: Feedback storage is SQLite, deliberately naive
Date: 2026-10
Status: accepted

**Context.** Phase 1 feedback volume is tiny (manual thumbs up/down).

**Decision.** Single-file SQLite, one table, no dedup, no migrations.
Revisit only if feedback volume or querying needs justify it; the table is
trivially exportable.

## D6: No Docker; Makefile + uv for environment management
Date: 2026-10
Status: accepted

**Context.** Original plan included docker-compose for "one command to run
everything." Team decision: containers add overhead we do not need for a
research project with a single backend process.

**Decision.** `uv` manages the Python environment; a Makefile provides
`make dev` / `make index` entry points; versions pinned exactly (==) in
pyproject.toml for reproducibility of evaluation numbers.
