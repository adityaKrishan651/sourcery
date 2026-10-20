from . import schemas

MOCK_RESPONSE = schemas.AnalyzeResponse(
    input_type=schemas.InputType.TEXT,
    paragraphs=[
        schemas.Paragraph(
            id="p0",
            text="Transformer models have transformed NLP. We extend prior work on sparse attention.",
            start=0,
            end=89,
            sentences=[
                schemas.Sentence(
                    id="p0s0",
                    text="Transformer models have transformed NLP.",
                    start=0,
                    end=41,
                    has_existing_citation=False,
                    needs_citation=True,
                    citation_score=0.87,
                    recommendations=[
                        schemas.Recommendation(
                            paper_id="arxiv:1706.03762",
                            title="Attention Is All You Need",
                            abstract="The dominant sequence transduction models...",
                            authors=["Ashish Vaswani", "Noam Shazeer"],
                            year=2017,
                            venue="NeurIPS",
                            doi=None,
                            url="https://arxiv.org/abs/1706.03762",
                            score=8.42,
                            match_source=schemas.MatchSource.RERANK,
                            already_cited=False,
                            bib_match_confidence=None,
                            evidence=[
                                schemas.Evidence(
                                    text="We propose a new simple network architecture, the Transformer.",
                                    score=0.91,
                                )
                            ],
                            bibtex="@inproceedings{vaswani2017attention, ...}",
                            cite_key="vaswani2017attention",
                        ),
                    ],
                ),
                schemas.Sentence(
                    id="p0s1",
                    text="We extend prior work on sparse attention.",
                    start=42,
                    end=89,
                    has_existing_citation=True,
                    needs_citation=False,
                    recommendations=[],
                ),
            ],
        ),
    ],
    parse_warnings=[],
    bib_stats=schemas.BibStats(total_entries=0),
)