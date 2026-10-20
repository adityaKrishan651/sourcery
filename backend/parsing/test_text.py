from backend.parsing.text import split_paragraphs

def test_basic_split():
    raw = "First paragraph.\n\nSecond paragraph."
    paras = split_paragraphs(raw)
    assert len(paras) == 2
    assert raw[paras[0].start:paras[0].end] == "First paragraph."
    assert raw[paras[1].start:paras[1].end] == "Second paragraph."
    # the key property, forever: offsets must slice back to the text
    for p in paras:
        assert raw[p.start:p.end] == p.text


def test_offsets_with_multiple_blank_lines_and_edges():
    raw = "\n\n  Alpha beta.  \n\n\n\nGamma.\n\n"
    paras = split_paragraphs(raw)
    assert [p.text for p in paras] == ["Alpha beta.", "Gamma."]
    for p in paras:
        assert raw[p.start:p.end] == p.text


def test_single_paragraph_no_trailing_newline():
    raw = "Only one."
    paras = split_paragraphs(raw)
    assert len(paras) == 1
    assert paras[0].text == "Only one."
    assert (paras[0].start, paras[0].end) == (0, 9)


def test_empty_and_whitespace_only():
    assert split_paragraphs("") == []
    assert split_paragraphs("  \n\n  \n") == []