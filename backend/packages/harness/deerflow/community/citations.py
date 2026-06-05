from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


def truncate_evidence_snippet(value: Any, *, limit: int = 500) -> str | None:
    if not isinstance(value, str):
        return None
    snippet = " ".join(value.split())
    if not snippet:
        return None
    if len(snippet) <= limit:
        return snippet
    return snippet[: limit - 1].rstrip() + "…"


def canonical_web_result(
    *,
    title: Any,
    url: Any,
    provider: str,
    snippet: Any = None,
    citation_type: str = "web_page",
) -> dict[str, Any]:
    citation_url = url.strip() if isinstance(url, str) and url.strip() else None
    citation_title = title.strip() if isinstance(title, str) and title.strip() else None
    return {
        "citationUrl": citation_url,
        "citationTitle": citation_title,
        "citationProvider": provider,
        "citationType": citation_type,
        "evidenceSnippet": truncate_evidence_snippet(snippet),
    }


def format_fetched_document(
    *,
    title: str,
    url: str,
    provider: str,
    content: str,
    fetched_at: str | None = None,
) -> str:
    fetched_at = fetched_at or datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
    safe_title = title.strip() or "Untitled"
    header = "\n".join(
        [
            f"# {safe_title}",
            "",
            f"citationUrl: {url}",
            f"citationTitle: {safe_title}",
            f"citationProvider: {provider}",
            "citationType: web_page",
            f"fetchedAt: {fetched_at}",
        ]
    )
    return f"{header}\n\n{content[:4096]}"


def normalize_doi(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    doi = value.strip()
    if not doi:
        return None
    lower = doi.lower()
    if lower.startswith("doi:"):
        doi = doi[4:].strip()
        lower = doi.lower()
    if lower.startswith("https://doi.org/"):
        doi = doi[16:].strip()
    elif lower.startswith("http://doi.org/"):
        doi = doi[15:].strip()
    return doi or None


def doi_url(value: Any) -> str | None:
    doi = normalize_doi(value)
    if not doi:
        return None
    return f"https://doi.org/{doi}"


def semantic_scholar_paper_url(paper_id: Any) -> str | None:
    if not isinstance(paper_id, str):
        return None
    pid = paper_id.strip()
    if not pid:
        return None
    return f"https://www.semanticscholar.org/paper/{pid}"


def openalex_work_url(paper_id_or_url: Any) -> str | None:
    if not isinstance(paper_id_or_url, str):
        return None
    value = paper_id_or_url.strip()
    if not value:
        return None
    if value.startswith("https://openalex.org/"):
        return value
    if value.startswith("http://openalex.org/"):
        return "https://" + value[len("http://") :]
    if value.startswith("W") and value[1:].isdigit():
        return f"https://openalex.org/{value}"
    return None


def canonical_academic_result(
    *,
    title: Any,
    provider: str,
    paper_id: Any = None,
    doi: Any = None,
    provider_url: Any = None,
    abstract: Any = None,
    tldr: Any = None,
) -> dict[str, Any]:
    provider_name = provider or "unknown"
    if provider_name == "openalex":
        canonical_provider_url = openalex_work_url(provider_url) or openalex_work_url(paper_id)
    elif provider_name == "semantic_scholar":
        canonical_provider_url = semantic_scholar_paper_url(provider_url) if isinstance(provider_url, str) and not provider_url.startswith("http") else provider_url
        canonical_provider_url = canonical_provider_url or semantic_scholar_paper_url(paper_id)
    else:
        canonical_provider_url = provider_url if isinstance(provider_url, str) and provider_url.startswith("http") else None

    canonical_doi_url = doi_url(doi)
    citation_title = title.strip() if isinstance(title, str) and title.strip() else None
    snippet = truncate_evidence_snippet(tldr) or truncate_evidence_snippet(abstract)
    result: dict[str, Any] = {
        "citationUrl": canonical_doi_url or canonical_provider_url,
        "citationTitle": citation_title,
        "citationProvider": provider_name,
        "citationType": "academic_paper",
        "evidenceSnippet": snippet,
    }
    if canonical_doi_url:
        result["doiUrl"] = canonical_doi_url
    if canonical_provider_url:
        result["providerUrl"] = canonical_provider_url
    return result
