# Sourcery API Schema — v1

**Status: FROZEN.** Changes require a written amendment to this document
before any code is touched. Source of truth for `backend/app/schemas.py`.

## Conventions

- Offsets (`start`, `end`) are **character offsets** (Unicode code points,
  not bytes) into the **raw uploaded file**.
- IDs: `p{index}` for paragraphs, `p{index}s{index}` for sentences.
  Stable within one response. Sentence IDs are deterministic per content.
- `request_id` is generated server-side (UUIDv4). Never accepted from clients.
- All arrays are present in every response, possibly empty. Nothing is omitted.

## Endpoints

| Endpoint | Method | Purpose |
|---|---|---|
| `/analyze` | POST | Text or .tex (optional .bib) in; paragraphs, flagged sentences, recommendations out |
| `/feedback` | POST | Record relevant / not_relevant for a (sentence, paper) pair |
| `/health` | GET | Deployment check |

## POST /analyze

### Request

`multipart/form-data` (file uploads) or `application/json` (pasted text).

| Field | Type | Required | Semantics |
|---|---|---|---|
| `text` | string | exactly one of `text`/`file` | Pasted plain text, max 1 MB |
| `file` | file | exactly one of `text`/`file` | `.tex` or `.txt`, max 1 MB |
| `bib` | file | no | `.bib` upload for already-cited matching |
| `threshold` | float | no | Citation-worthiness cutoff, 0-1, default 0.5 |
| `max_recommendations` | int | no | Default 5, hard cap 10 |

### Response: `AnalyzeResponse`

| Field | Type | Nullable | Semantics |
|---|---|---|---|
| `request_id` | UUID | no | Joins to /feedback events |
| `input_type` | enum: `text`, `tex` | no | What we detected; drives frontend rendering |
| `paragraphs` | Paragraph[] | no | Always present; may be empty |
| `parse_warnings` | string[] | no | Non-fatal issues; never silently drop anything |
| `bib_stats` | BibStats | no | .bib match summary |

**Paragraph**

| Field | Type | Nullable | Semantics |
|---|---|---|---|
| `id` | string | no | `p{index}` |
| `text` | string | no | Cleaned prose (LaTeX stripped) |
| `start`, `end` | int >= 0 | no | Offsets into raw uploaded file; `end > start` |
| `sentences` | Sentence[] | no | Empty iff paragraph failed segmentation (then `error` set) |
| `error` | string | yes | Set iff paragraph could not be processed |

**Sentence**

| Field | Type | Nullable | Semantics |
|---|---|---|---|
| `id` | string | no | `p{i}s{j}` |
| `text` | string | no | Sentence as segmented |
| `start`, `end` | int >= 0 | no | Offsets into raw uploaded file; `end > start` |
| `has_existing_citation` | bool | no | Source contained a citation marker |
| `needs_citation` | bool | no | `citation_score >= threshold`; MUST be false if `has_existing_citation` |
| `citation_score` | float 0-1 | yes | Classifier probability; null if skipped pre-classifier |
| `recommendations` | Recommendation[] | no | Empty iff `needs_citation` false; length <= `max_recommendations` |

**Recommendation**

| Field | Type | Nullable | Semantics |
|---|---|---|---|
| `paper_id` | string | no | One namespace: `arxiv:{id}`, `doi:{doi}`, or `corpus:{internal}` |
| `title` | string | no | |
| `abstract` | string | yes | |
| `authors` | string[] | no | Empty array if unknown — never null |
| `year` | int | yes | |
| `venue` | string | yes | |
| `doi` | string | yes | |
| `url` | string | yes | Canonical landing page |
| `score` | float | no | Reranker score. Higher = more relevant within one sentence. Unbounded; NOT comparable across sentences |
| `match_source` | enum: `bm25`, `dense`, `rerank` | yes | Debug/eval only; not rendered in UI |
| `already_cited` | bool | no | Matched against uploaded .bib |
| `bib_match_confidence` | enum: `exact`, `fuzzy` | yes | Null iff `already_cited` is false. `exact` = DOI/arXiv ID, `fuzzy` = normalized title |
| `evidence` | Evidence[] | no | 1-2 items |
| `bibtex` | string | no | Pre-formatted server-side |
| `cite_key` | string | no | Suggested key for `\cite{key}` |

**Evidence**

| Field | Type | Nullable | Semantics |
|---|---|---|---|
| `text` | string | no | Abstract sentence(s) most similar to the query |
| `score` | float | no | Embedding similarity |
| `source` | enum: `abstract` | no | Reserved for Phase 2 `fulltext` |

**BibStats**

| Field | Type | Semantics |
|---|---|---|
| `total_entries` | int | |
| `matched_exact` | int | |
| `matched_fuzzy` | int | |
| `unmatched` | int | |

## POST /feedback

**Request: FeedbackRequest**

| Field | Type | Semantics |
|---|---|---|
| `request_id` | UUID | From the /analyze response being rated |
| `sentence_id` | string | From that response |
| `paper_id` | string | Corpus namespace id |
| `verdict` | enum: `relevant`, `not_relevant` | |

**Response: FeedbackResponse** — `{ "ok": true }`

## Error model

- **Whole-request failures** -> HTTP 4xx/5xx with body:
  `{"request_id": UUID, "error": {"code": ErrorCode, "message": str}}`
- **Partial failures** -> HTTP 200 with degradation inside the response
  (paragraph-level `error`, `parse_warnings`, empty `recommendations`).
  Rule: if any paragraph can still be served, return 200.
- **ErrorCode**: `empty_input`, `file_too_large` (413), `unsupported_type`,
  `unparseable_tex`, `internal` (500).

## Out of scope for v1

- `/explain` (Phase 2)
- Per-sentence latency timings
- Streaming/progress protocol (client-side paragraph chunking needs no
  schema support)
