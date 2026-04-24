from __future__ import annotations

import re


def detect_paper_id_source(paper_id: str) -> str:
    """Detect the likely source from a paper ID's format.

    Returns one of: "doi", "arxiv", "s2", "openalex", "unknown".
    """
    pid = paper_id.strip()
    pid_lower = pid.lower()

    if pid.startswith("10.") or "doi.org" in pid_lower:
        return "doi"

    if pid_lower.startswith("arxiv:"):
        return "arxiv"
    if _looks_like_arxiv(pid):
        return "arxiv"

    if pid.startswith("W") and pid[1:].isdigit():
        return "openalex"

    if len(pid) == 40 and pid.isalnum():
        return "s2"

    return "unknown"


_OLD_ARXIV_RE = re.compile(r"^[a-z-]+/\d+$")
_NEW_ARXIV_RE = re.compile(r"^\d{4}\.\d{4,5}(v\d+)?$")


def _looks_like_arxiv(paper_id: str) -> bool:
    return bool(_OLD_ARXIV_RE.match(paper_id) or _NEW_ARXIV_RE.match(paper_id))
