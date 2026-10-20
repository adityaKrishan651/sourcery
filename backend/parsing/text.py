from dataclasses import dataclass


@dataclass
class Paragraph:
    """A paragraph of cleaned text with offsets into the raw input."""
    text: str
    start: int   # offset of first char into raw input
    end: int     # offset one past last char into raw input


def split_paragraphs(raw: str) -> list[Paragraph]:
    """Split raw text into paragraphs on blank lines.

    Offsets point into `raw`. Blank-line separators are not part of any
    paragraph. Leading/trailing whitespace of each paragraph is stripped
    from `text` but included in [start, end).
    """
    paragraphs: list[Paragraph] = []
    i = 0
    n = len(raw)
    while i < n:
        # skip blank lines (spaces/tabs/newlines only)
        j = i
        while j < n and raw[j] in " \t\r\n":
            j += 1
        if j >= n:
            break
        # find end of this paragraph: next blank line, or end of input
        k = j
        while k < n:
            if raw[k] == "\n" and (k + 1 >= n or raw[k + 1] == "\n"):
                break
            k += 1
        # strip trailing whitespace of the paragraph content
        content_end = k
        while content_end > j and raw[content_end - 1] in " \t\r\n":
            content_end -= 1
        paragraphs.append(Paragraph(text=raw[j:content_end], start=j, end=content_end))
        i = k
    return paragraphs