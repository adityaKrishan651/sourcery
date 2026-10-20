from dataclasses import dataclass, field


@dataclass
class CitationMarker:
    keys: list[str]
    raw_start: int
    raw_end: int


@dataclass
class CleanedText:
    text: str
    map: list[int]  # map[i] = raw index of text[i]
    citations: list[CitationMarker] = field(default_factory=list)

    def to_raw_span(self, clean_start: int, clean_end: int) -> tuple[int, int]:
        """Convert a half-open span in cleaned text to raw text."""
        return (self.map[clean_start], self.map[clean_end - 1] + 1)


SKIP_ARG_COMMANDS = {
    "section", "subsection", "subsubsection", "paragraph",
    "label", "usepackage", "documentclass",
    "bibliography", "bibliographystyle",
}

CITE_COMMANDS = {"cite", "citep", "citet", "citealp"}
ESCAPED_CHARS = {"%": "%", "&": "&", "$": "$", "#": "#", "_": "_"}


def _find_matching_brace(raw: str, open_idx: int) -> int:
    """Index just past the brace matching raw[open_idx], or end of string."""
    depth = 0
    for k in range(open_idx, len(raw)):
        if raw[k] == "{":
            depth += 1
        elif raw[k] == "}":
            depth -= 1
            if depth == 0:
                return k + 1
    return len(raw)  # unbalanced: swallow the rest (recorded as a warning later)


def clean_latex(raw: str) -> CleanedText:
    out: list[str] = []
    mp: list[int] = []
    cites: list[CitationMarker] = []
    n = len(raw)
    i = 0

    def emit(ch: str, raw_i: int) -> None:
        out.append(ch)
        mp.append(raw_i)

    while i < n:
        c = raw[i]

        # comments: skip to end of line (the \n itself is handled next loop)
        if c == "%":
            while i < n and raw[i] != "\n":
                i += 1
            continue

        # math: skip to closing delimiter
        if raw.startswith("$$", i):
            i += 2
            while i < n and not raw.startswith("$$", i):
                i += 1
            i = min(i + 2, n)
            continue
        if c == "$":
            i += 1
            while i < n and raw[i] != "$":
                i += 1
            i = min(i + 1, n)
            continue

        # backslash commands
        if c == "\\":
            j = i + 1
            if j < n and raw[j].isalpha():
                k = j
                while k < n and raw[k].isalpha():
                    k += 1
                name = raw[j:k]
                if name in CITE_COMMANDS:
                    b = raw.find("{", k)
                    e = raw.find("}", b) if b != -1 else -1
                    if b != -1 and e != -1:
                        keys = [x.strip() for x in raw[b + 1 : e].split(",")]
                        cites.append(CitationMarker(keys, i, e + 1))
                        i = e + 1
                        continue
                    # malformed cite: swallow command name only
                    i = k
                    continue
                if name in SKIP_ARG_COMMANDS:
                    b = raw.find("{", k)
                    i = _find_matching_brace(raw, b) if b != -1 else k
                    continue
                # default: keep the argument's content, drop command name
                i = k
                continue
            # special characters: \% \& \$ \# \_
            if j < n and raw[j] in ESCAPED_CHARS:
                emit(ESCAPED_CHARS[raw[j]], j)
                i = j + 1
                continue
            # anything else (e.g. \\, \,): skip the command entirely
            i = min(j + 1, n)
            continue

        # structural braces: skip
        if c in "{}":
            i += 1
            continue

        # Windows line endings: normalize away
        if c == "\r":
            i += 1
            continue

        emit(c, i)
        i += 1

    return CleanedText(text="".join(out), map=mp, citations=cites)