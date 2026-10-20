from enum import Enum
from typing import Annotated, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, model_validator


# Enums: a field may only be one of these exact strings
class InputType(str, Enum):
    TEXT = "text"
    TEX = "tex"


class MatchSource(str, Enum):
    BM25 = "bm25"
    DENSE = "dense"
    RERANK = "rerank"


class BibMatchConfidence(str, Enum):
    EXACT = "exact"      # matched by DOI or arXiv ID
    FUZZY = "fuzzy"      # matched by normalized title


class EvidenceSource(str, Enum):
    ABSTRACT = "abstract"


# A reusable type: an offset is an int that must be >= 0
Offset = Annotated[int, Field(ge=0)]


class Evidence(BaseModel):
    text: str
    score: float
    source: EvidenceSource = EvidenceSource.ABSTRACT  # default value


class Recommendation(BaseModel):
    paper_id: str
    title: str
    abstract: Optional[str] = None   # Optional = may be null; = None is the default
    authors: list[str] = Field(default_factory=list)  # never null; empty list by default
    year: Optional[int] = None
    venue: Optional[str] = None
    doi: Optional[str] = None
    url: Optional[str] = None
    score: float                     # reranker score; deliberately unbounded
    match_source: Optional[MatchSource] = None
    already_cited: bool = False
    bib_match_confidence: Optional[BibMatchConfidence] = None
    evidence: list[Evidence] = Field(default_factory=list)
    bibtex: str
    cite_key: str

    # Relationship rule: if already_cited is False, confidence must be null
    @model_validator(mode="after")
    def _bib_match_consistency(self):
        if not self.already_cited and self.bib_match_confidence is not None:
            raise ValueError("bib_match_confidence must be null when already_cited is False")
        return self


class Sentence(BaseModel):
    id: str                       # "p{idx}s{idx}"
    text: str
    start: Offset                 # into the RAW uploaded file
    end: Offset
    has_existing_citation: bool = False
    needs_citation: bool = False
    citation_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    recommendations: list[Recommendation] = Field(default_factory=list)

    @model_validator(mode="after")
    def _offsets_and_logic(self):
        if self.end <= self.start:
            raise ValueError("end must be greater than start")
        if self.has_existing_citation and self.needs_citation:
            raise ValueError("needs_citation must be False when has_existing_citation is True")
        return self


class Paragraph(BaseModel):
    id: str
    text: str                     # cleaned prose, LaTeX stripped
    start: Offset
    end: Offset
    sentences: list[Sentence] = Field(default_factory=list)
    error: Optional[str] = None

    @model_validator(mode="after")
    def _offsets(self):
        if self.end <= self.start:
            raise ValueError("end must be greater than start")
        return self


class BibStats(BaseModel):
    total_entries: int = 0
    matched_exact: int = 0
    matched_fuzzy: int = 0
    unmatched: int = 0


class AnalyzeResponse(BaseModel):
    request_id: UUID = Field(default_factory=uuid4)  # auto-generated if not provided
    input_type: InputType
    paragraphs: list[Paragraph] = Field(default_factory=list)
    parse_warnings: list[str] = Field(default_factory=list)
    bib_stats: BibStats = Field(default_factory=BibStats)


class AnalyzeRequest(BaseModel):
    text: Optional[str] = Field(default=None, max_length=1_048_576)
    threshold: float = Field(default=0.5, ge=0.0, le=1.0)
    max_recommendations: int = Field(default=5, ge=1, le=10)


class FeedbackVerdict(str, Enum):
    RELEVANT = "relevant"
    NOT_RELEVANT = "not_relevant"


class FeedbackRequest(BaseModel):
    request_id: UUID
    sentence_id: str
    paper_id: str
    verdict: FeedbackVerdict


class FeedbackResponse(BaseModel):
    ok: bool = True


class ErrorCode(str, Enum):
    EMPTY_INPUT = "empty_input"
    FILE_TOO_LARGE = "file_too_large"
    UNSUPPORTED_TYPE = "unsupported_type"
    UNPARSEABLE_TEX = "unparseable_tex"
    INTERNAL = "internal"


class ErrorDetail(BaseModel):
    code: ErrorCode
    message: str


class ErrorResponse(BaseModel):
    request_id: UUID
    error: ErrorDetail