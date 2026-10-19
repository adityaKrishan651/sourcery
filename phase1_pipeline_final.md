# Sourcery: Phase 1 Pipeline and Stack

## 1. What we're building

Researchers often struggle to find the most relevant papers to cite. Our system takes a researcher's **paragraphs** (pasted text or a LaTeX file, optionally with their `.bib`) and recommends papers **attributed to the specific sentences that need them**.

**Final delivery shape:** a **backend API** that runs the pipeline, plus a **minimal React frontend** where a user uploads text or `.tex` files along with a `.bib`, sees which sentences need citations, and browses recommendations for each.

**Phase 1 (this document)** is the complete system *without* an LLM. It gives us a measurable baseline and a working product.

**Phase 2 (later)** adds a RAG + LLM layer on top: grounded explanations and relevance verdicts, triggered on demand. It is deliberately out of scope here so we can measure exactly what the LLM adds.

---

## 2. Architecture

```
 React frontend                    FastAPI backend
 +--------------------+            +-------------------------------------+
 | upload text / .tex |  POST      | input handling (.tex parse + offsets)|
 | upload .bib        | ---------> | .bib parse + corpus matching         |
 | document view      | /analyze   |                                      |
 | recommendations    | <--------- |  pipeline (pure Python, no FastAPI)  |
 | feedback buttons   |   JSON     |   [1] segmentation                   |
 +--------------------+            |   [2] citation-worthiness            |
                                   |   [3] query formation                |
                                   |   [4] retrieval + reranking          |
                                   |   [5] extractive evidence            |
                                   +-------------------------------------+
                                        |                 |
                                   FAISS index       paper metadata
                                   BM25 index        (title, authors,
                                                      year, DOI, abstract)
```

**Key design rule:** the `pipeline` package never imports FastAPI. Research and evaluation scripts call it directly, and the API is a thin wrapper. That way our experiments and our product share one implementation.

---

## 3. Stack

| Layer | Choice | Notes |
|---|---|---|
| Backend API | Python, FastAPI, Pydantic | Schema-first; models loaded once at startup |
| Segmentation | spaCy (or scispaCy models) | Scientific text aware |
| Citation-worthiness | Fine-tuned SciBERT-style classifier (Hugging Face Transformers) | Trained on citation-marker labels |
| Embeddings | sentence-transformers; shortlist SPECTER2, SciNCL, BGE, E5 | Benchmark, don't assume |
| Vector search | FAISS | Qdrant is the alternative if we need filtering or persistence |
| Sparse search | BM25 (e.g. `rank_bm25`) | Strong on acronyms and exact terms |
| Fusion | Reciprocal rank fusion | Merges dense and BM25 lists |
| Reranking | Cross-encoder (sentence-transformers) | Applied to top 50 to 100 candidates |
| LaTeX parsing | `pylatexenc` or a custom tokenizer | **Must preserve character offsets** |
| BibTeX parsing | `bibtexparser` | Matched to corpus by DOI, arXiv ID, or normalized title |
| Frontend | Vite + React + TypeScript | Plain CSS or a light component library; no state library needed |
| Packaging | Docker / docker-compose | One command to run everything |

---

## 4. Pipeline stages

### Stage 0: Input handling (new)

- **Plain text:** go straight to paragraph splitting.
- **`.tex` files:** strip commands, math, comments, and environments to get readable prose, while keeping an **offset map** from cleaned text back to source positions. Split into paragraphs on blank lines.
- **Existing `\cite{...}` commands:** record them. A sentence that already has a citation does not need a recommendation.
- **`.bib` files:** parse entries and match them against our corpus. Matched papers are flagged `already_cited` in results. Matching is best effort, since some entries won't be found.
- **Safety:** treat uploads as text only. Never compile or execute anything. Enforce an upload size limit and do not log query text.
- **Output:** a list of paragraphs, each with start and end offsets in the original input.

### Stage 1: Sentence segmentation

- **Goal:** split each paragraph into sentences that can be handled independently and mapped back to the original text for highlighting.
- **Approach:** spaCy or scispaCy.
- **Watch out for:** abbreviations ("et al.", "Fig. 3", "e.g."), decimals, inline math placeholders, and leftover LaTeX artifacts.
- **Output:** sentences with character offsets.
- **Check:** manually inspect about 100 paragraphs and report the error rate.

### Stage 2: Citation-worthiness

- **Goal:** decide which sentences need a citation. "We now describe our method" should not trigger retrieval.
- **Approach:** fine-tune a small transformer classifier as a binary sentence classifier. Sentences carrying a citation marker in the source paper are positives. Neighboring sentences can be added as context.
- **Caveat:** labels are noisy (authors skip citations for well-known facts, or cite at the end of a paragraph). We expect this and will report it.
- **Output:** a probability per sentence and a tunable threshold.
- **Metrics:** precision, recall, F1 on a held-out set. Tune the threshold against downstream results, not only F1.

### Stage 3: Query formation

- **Goal:** turn a flagged sentence into a good search query.
- **Variants to compare (ablation):**
  1. Sentence only (baseline)
  2. Sentence + neighboring sentences (window of ±1 or ±2)
  3. Sentence + the paragraph's first sentence
  4. Whole paragraph
- **Important:** strip citation markers and author-year mentions from the query, or the model can cheat during evaluation.
- **Output:** one query string per flagged sentence.

### Stage 4: Retrieval and reranking

- **Index:** title + abstract per paper. Embeddings are **precomputed offline**; only the query is embedded at request time.
- **Dense retrieval:** FAISS over the paper embeddings.
- **Sparse retrieval:** BM25 over the same text.
- **Hybrid:** merge with reciprocal rank fusion and keep the top 50 to 100.
- **Reranking:** cross-encoder over those candidates, keep the top 5 to 10.
- **Filters:** exclude the source paper, and in evaluation only allow papers published before it.
- **Output:** a ranked list per flagged sentence.

### Stage 5: Extractive evidence (explanations without an LLM)

- **Goal:** show why each paper was recommended, with no generation.
- **Approach:** pick the 1 to 2 abstract sentences most similar to the query using the same embedding model, and return them with scores. Optionally highlight overlapping key terms.
- **Why:** it cannot hallucinate, it's cheap, and it gives Phase 2 a concrete baseline to beat.

---

## 5. API contract

Agree on this first. Once it is fixed, frontend and backend can work in parallel, with a mocked `/analyze` until the real pipeline is ready.

| Endpoint | Purpose |
|---|---|
| `POST /analyze` | Text or `.tex` (and optional `.bib`) in; paragraphs, flagged sentences, and recommendations out |
| `POST /feedback` | Record relevant / not relevant for a (sentence, paper) pair |
| `GET /health` | Deployment check |
| `POST /explain` | **Reserved for Phase 2** (LLM explanations) |

Example response shape:

```json
{
  "paragraphs": [{
    "id": "p3",
    "text": "...",
    "start": 1204, "end": 1650,
    "sentences": [{
      "id": "p3s2",
      "text": "...", "start": 1260, "end": 1388,
      "needs_citation": true,
      "citation_score": 0.91,
      "recommendations": [{
        "paper_id": "arxiv:2101.00001",
        "title": "...", "authors": ["..."], "year": 2021,
        "score": 0.83,
        "evidence": [{"text": "...", "score": 0.78}],
        "already_cited": false,
        "bibtex": "@article{...}"
      }]
    }]
  }]
}
```

Offsets into the **original** input are what let the frontend highlight the right spans, so they are the most important field.

---

## 6. Frontend (minimal React)

One page with three areas:

- **Input:** paste box, `.tex` upload, optional `.bib` upload, Analyze button.
- **Document view:** paragraphs with flagged sentences highlighted; clicking a sentence selects it.
- **Recommendations panel:** for the selected sentence, each paper shows title, authors, year, the evidence snippet, and an "already in your .bib" badge where relevant.
- **Per-paper actions:** copy BibTeX, copy `\cite{key}`, open paper link, thumbs up or down.

Practical choices:
- For whole files, send paragraphs one at a time (a few in parallel) and fill in results as they arrive. This gives progress feedback without a job queue.
- Leave room in each recommendation card for a future "Explain" button (Phase 2).

---

## 7. Repo layout

```
/backend
  /app          # FastAPI routes, Pydantic schemas
  /pipeline     # segmentation, classifier, query formation, retrieval, rerank, evidence
  /parsing      # latex + bib handling, offset mapping
  /eval         # metrics, ablation scripts (import pipeline directly)
/frontend       # Vite + React + TypeScript
/docs
docker-compose.yml
```

---

## 8. Data and ground truth

We need a corpus where we know **which sentence cites which paper**.

| Source | Notes |
|---|---|
| unarXive | arXiv full text with citation markers linked to cited papers |
| S2ORC / Semantic Scholar | Large; includes citation contexts |
| OpenAlex / arXiv | Good for metadata and abstracts |

**Building labels:** locate each citation marker's sentence, record the cited paper(s) as its label, then strip the marker so the sentence becomes a query with a hidden answer.

**Known label noise:** grouped citations like [3-7] attach to one sentence even if they support different parts of it, and some citations apply to a whole paragraph.

**Corpus requirement from the product side:** we need clean metadata (authors, venue, year, DOI) to generate BibTeX and to match uploaded `.bib` entries, so this should influence which source we choose.

**Split by paper**, not by sentence, to avoid leakage between train and test.

---

## 9. Evaluation plan

| Stage | Metrics |
|---|---|
| Segmentation | Manual error rate on a sample |
| LaTeX parsing | Offset round-trip tests on real papers (cleaned span maps back to the exact source span) |
| `.bib` matching | Match rate against corpus |
| Citation-worthiness | Precision, recall, F1 |
| Retrieval + reranking (per sentence) | Recall@k, MRR, nDCG |
| Retrieval (per paragraph, union of outputs) | Recall@k, MAP |
| Extractive evidence | Small manual review of whether the highlighted sentence supports the query |
| System | End-to-end latency per paragraph; accept / dismiss rates from feedback buttons |

**Ablations to report:**
- Query formation variants
- Embedding models
- Dense only vs BM25 only vs hybrid
- With vs without cross-encoder reranking
- Citation-worthiness filter on vs off

---

## 10. Build order

1. **Agree on the schema**, then publish a mock `/analyze` that returns fixed JSON.
2. **Frontend against the mock**, while data and pipeline work proceed.
3. **LaTeX and `.bib` parsing** with offset tests on real, messy papers.
4. **Pipeline stages** swapped into the real endpoint one at a time as each is ready.
5. **Feedback logging, Docker packaging, and built-in sample inputs.**
6. **Phase 2:** `/explain` and the RAG + LLM layer.

---

## 11. Suggested work split

| Workstream | Covers |
|---|---|
| Data pipeline | Corpus selection, citation-sentence labels, splits, metadata |
| Text processing | LaTeX and `.bib` parsing, segmentation, citation-worthiness classifier |
| Retrieval | Indexing, embeddings, BM25, fusion, reranking, extractive evidence |
| API + frontend | Schema, FastAPI service, React app, Docker |
| Cross-cutting | Evaluation code and ablation runs |

Data and labels are the dependency for everything else, so that workstream starts first. API + frontend can start immediately against the mock.

---

## 12. Risks

- **Offset bugs** between the original `.tex` and the cleaned text are the most common cause of highlights landing in the wrong place. Test early with real LaTeX.
- **Metadata quality** in the corpus limits BibTeX output and `.bib` matching.
- **Latency:** precompute all paper embeddings and keep the cross-encoder candidate set small. Cache results by paragraph hash.
- **Scope creep:** the frontend must stay minimal. The research and evaluation are what we are judged on.
- **Privacy:** uploaded manuscripts are sent to our server. State this clearly in the UI, do not log query text, and note that Phase 2 LLM calls go to a third-party API.

---

## 13. Open decisions

1. Which research field(s) and which corpus?
2. Title + abstract only, or full text as well?
3. Which embedding models to shortlist for the first benchmark?
4. Corpus size we can realistically host (memory for the vector index)?
5. Evaluation set size and split strategy.
6. Final project name. "Sourcery" is a working title; an existing developer tool already uses that name, so check trademark, domain, and GitHub availability before committing to it publicly.

---

## 14. Looking ahead: Phase 2 (RAG + LLM)

Once Phase 1 works and is measured, a hosted LLM receives each flagged sentence plus the top retrieved papers and produces grounded explanations and relevance verdicts, restricted to retrieved paper IDs and validated programmatically. Phase 1's extractive evidence and retrieval metrics become the baseline for judging that layer.
