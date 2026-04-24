from __future__ import annotations

import re
import unicodedata
from typing import Any

LATEX_ESCAPES: dict[str, str] = {
    "ä": '{\\"a}',
    "ö": '{\\"o}',
    "ü": '{\\"u}',
    "Ä": '{\\"A}',
    "Ö": '{\\"O}',
    "Ü": '{\\"U}',
    "ß": "{\\ss}",
    "é": "{\\'e}",
    "è": "{\\`e}",
    "ê": "{\\^e}",
    "ë": '{\\"e}',
    "á": "{\\'a}",
    "à": "{\\`a}",
    "â": "{\\^a}",
    "ã": "{\\~a}",
    "ó": "{\\'o}",
    "ò": "{\\`o}",
    "ô": "{\\^o}",
    "õ": "{\\~o}",
    "ú": "{\\'u}",
    "ù": "{\\`u}",
    "û": "{\\^u}",
    "í": "{\\'i}",
    "ì": "{\\`i}",
    "î": "{\\^i}",
    "ï": '{\\"i}',
    "ñ": "{\\~n}",
    "ç": "{\\c{c}}",
    "Ç": "{\\c{C}}",
    "ø": "{\\o}",
    "Ø": "{\\O}",
    "å": "{\\aa}",
    "Å": "{\\AA}",
    "æ": "{\\ae}",
    "Æ": "{\\AE}",
    "œ": "{\\oe}",
    "Œ": "{\\OE}",
    "&": "\\&",
    "%": "\\%",
    "$": "\\$",
    "#": "\\#",
    "_": "\\_",
    "{": "\\{",
    "}": "\\}",
    "~": "{\\textasciitilde}",
    "^": "{\\textasciicircum}",
}

_STOP_WORDS = frozenset({"a", "an", "the", "on", "in", "of", "for", "to", "and", "with", "is", "are", "by"})

_CONFERENCE_KEYWORDS = [
    "conference",
    "proceedings",
    "workshop",
    "symposium",
    "icml",
    "neurips",
    "nips",
    "iclr",
    "cvpr",
    "iccv",
    "eccv",
    "acl",
    "emnlp",
    "naacl",
    "aaai",
    "ijcai",
    "sigchi",
    "sigmod",
    "vldb",
    "icse",
    "fse",
    "issta",
    "pldi",
]

_JOURNAL_KEYWORDS = [
    "journal",
    "transactions",
    "review",
    "letters",
    "nature",
    "science",
    "cell",
    "lancet",
    "nejm",
    "ieee",
    "acm",
    "springer",
    "elsevier",
]


def escape_latex(text: str) -> str:
    if not text:
        return ""
    return "".join(LATEX_ESCAPES.get(c, c) for c in text)


def generate_bibtex_key(paper: dict[str, Any]) -> str:
    """Generate key in format: FirstAuthorLastName + Year + FirstTitleWord."""
    parts: list[str] = []

    authors = paper.get("authors") or []
    if authors:
        first_author = authors[0] if isinstance(authors[0], str) else str(authors[0])
        if "," in first_author:
            last_name = first_author.split(",")[0].strip()
        else:
            name_parts = first_author.split()
            last_name = name_parts[-1] if name_parts else "Unknown"
        last_name = unicodedata.normalize("NFKD", last_name)
        last_name = "".join(c for c in last_name if c.isalnum())
        parts.append(last_name.capitalize())
    else:
        parts.append("Unknown")

    year = paper.get("year")
    if year:
        parts.append(str(year))

    title = paper.get("title") or ""
    if title:
        words = re.findall(r"\b[a-zA-Z]+\b", title)
        for word in words:
            if word.lower() not in _STOP_WORDS:
                word = unicodedata.normalize("NFKD", word)
                word = "".join(c for c in word if c.isalnum())
                parts.append(word.capitalize())
                break

    return "".join(parts) if parts else "unknown"


def format_authors_bibtex(authors: list[str]) -> str:
    """Format as 'Last1, First1 and Last2, First2'."""
    if not authors:
        return ""
    formatted = []
    for name in authors:
        name = name.strip()
        if "," in name:
            formatted.append(escape_latex(name))
        else:
            name_parts = name.split()
            if len(name_parts) >= 2:
                last = name_parts[-1]
                first = " ".join(name_parts[:-1])
                formatted.append(f"{escape_latex(last)}, {escape_latex(first)}")
            else:
                formatted.append(escape_latex(name))
    return " and ".join(formatted)


def determine_entry_type(paper: dict[str, Any]) -> str:
    venue = (paper.get("venue") or "").lower()

    external_ids = paper.get("externalIds") or {}
    arxiv_id = external_ids.get("ArXiv") or paper.get("arxivId")
    if arxiv_id or "arxiv" in venue:
        return "misc"

    for kw in _CONFERENCE_KEYWORDS:
        if kw in venue:
            return "inproceedings"

    for kw in _JOURNAL_KEYWORDS:
        if kw in venue:
            return "article"

    if paper.get("volume") and paper.get("pages"):
        return "article"

    return "misc"


def generate_bibtex(paper: dict[str, Any], custom_key: str | None = None) -> str:
    entry_type = determine_entry_type(paper)
    key = custom_key or generate_bibtex_key(paper)

    lines = [f"@{entry_type}{{{key},"]

    authors = paper.get("authors") or []
    if authors:
        lines.append(f"  author = {{{format_authors_bibtex(authors)}}},")

    title = paper.get("title")
    if title:
        lines.append(f"  title = {{{escape_latex(title)}}},")

    venue = paper.get("venue")
    if entry_type == "article" and venue:
        lines.append(f"  journal = {{{escape_latex(venue)}}},")
    elif entry_type == "inproceedings" and venue:
        lines.append(f"  booktitle = {{{escape_latex(venue)}}},")

    year = paper.get("year")
    if year:
        lines.append(f"  year = {{{year}}},")

    volume = paper.get("volume")
    if volume:
        lines.append(f"  volume = {{{volume}}},")

    issue = paper.get("issue")
    if issue:
        lines.append(f"  number = {{{issue}}},")

    pages = paper.get("pages")
    if pages:
        pages = pages.replace("–", "--").replace("-", "--")
        pages = re.sub(r"-{3,}", "--", pages)
        lines.append(f"  pages = {{{pages}}},")

    external_ids = paper.get("externalIds") or {}
    doi = external_ids.get("DOI") or paper.get("doi")
    if doi:
        lines.append(f"  doi = {{{doi}}},")

    arxiv_id = external_ids.get("ArXiv") or paper.get("arxivId")
    if arxiv_id:
        lines.append(f"  eprint = {{{arxiv_id}}},")
        lines.append("  archiveprefix = {arXiv},")

    url = paper.get("openAccessPdfUrl") or paper.get("url")
    if url:
        lines.append(f"  url = {{{url}}},")

    abstract = paper.get("abstract")
    if abstract:
        if len(abstract) > 1000:
            abstract = abstract[:997] + "..."
        lines.append(f"  abstract = {{{escape_latex(abstract)}}},")

    if lines[-1].endswith(","):
        lines[-1] = lines[-1][:-1]

    lines.append("}")
    return "\n".join(lines)


def generate_bibtex_batch(papers: list[dict[str, Any]]) -> str:
    entries: list[str] = []
    used_keys: set[str] = set()

    for paper in papers:
        key = generate_bibtex_key(paper)
        original_key = key
        counter = 1
        while key in used_keys:
            key = f"{original_key}{chr(ord('a') + counter - 1)}"
            counter += 1
        used_keys.add(key)
        entries.append(generate_bibtex(paper, custom_key=key))

    return "\n\n".join(entries)
