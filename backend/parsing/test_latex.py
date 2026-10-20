from backend.parsing.latex import clean_latex


def _cleaned(raw: str) -> str:
    return clean_latex(raw).text


def test_comment_removed_newline_kept():
    assert _cleaned("Hello. % a note\nWorld.") == "Hello. \nWorld."


def test_inline_math_removed():
    assert _cleaned("The $x + y$ value.") == "The  value."


def test_display_math_removed():
    assert _cleaned("Before\n$$E = mc^2$$\nAfter") == "Before\n\nAfter"


def test_textbf_keeps_inner_text():
    assert _cleaned(r"We use \textbf{deep} networks.") == "We use deep networks."


def test_section_removed_with_argument():
    assert _cleaned("\\section{Intro}\nMethods are described.") == "\nMethods are described."

def test_nested_braces_kept():
    assert _cleaned(r"\emph{outer {inner} text}") == "outer inner text"


def test_escaped_chars_preserved():
    assert _cleaned(r"50\% of A\&B") == "50% of A&B"


def test_cite_recorded_and_removed():
    result = clean_latex(r"Prior work \cite{vaswani2017, devlin2019} shows.")
    assert result.text == "Prior work  shows."
    assert len(result.citations) == 1
    assert result.citations[0].keys == ["vaswani2017", "devlin2019"]
    # raw span covers from the backslash through the closing brace
    assert result.citations[0].raw_start == 11
    raw = r"Prior work \cite{vaswani2017, devlin2019} shows."
    assert raw[result.citations[0].raw_start : result.citations[0].raw_end] == r"\cite{vaswani2017, devlin2019}"


def test_strict_offset_invariant():
    """THE test: every emitted char must come from the raw position claimed."""
    raw = (
        r"\section{Intro}" "\n"
        r"We use \textbf{deep} networks % why not" "\n"
        r"with $O(n^2)$ cost \cite{vaswani2017} and 50\% gain." "\n\n"
        r"Second \emph{paragraph} here."
    )
    result = clean_latex(raw)
    assert len(result.map) == len(result.text)
    for clean_i, raw_i in enumerate(result.map):
        assert raw[raw_i] == result.text[clean_i], f"mismatch at cleaned index {clean_i}"


def test_to_raw_span_round_trip():
    raw = r"We use \textbf{deep} networks."
    result = clean_latex(raw)
    # locate "deep" in cleaned text
    cs = result.text.index("deep")
    ce = cs + len("deep")
    rs, re = result.to_raw_span(cs, ce)
    assert raw[rs:re] == "deep"