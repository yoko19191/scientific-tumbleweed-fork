from __future__ import annotations

import logging
from typing import Any

from deerflow.community.semantic_scholar.client import SemanticScholarClient

from .bibtex import generate_bibtex, generate_bibtex_batch
from .id_detect import detect_paper_id_source
from .openalex_client import OpenAlexClient

logger = logging.getLogger(__name__)


class AcademicAggregator:
    """Orchestrates OpenAlex + Semantic Scholar with fallback logic."""

    def __init__(self, openalex: OpenAlexClient, s2: SemanticScholarClient) -> None:
        self._openalex = openalex
        self._s2 = s2

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search_papers(
        self,
        *,
        query: str,
        limit: int = 10,
        source: str = "auto",
        min_citation_count: int | None = None,
        year: int | str | None = None,
        year_from: int | None = None,
        year_to: int | None = None,
        fields_of_study: list[str] | str | None = None,
        open_access_only: bool | None = None,
        venue: str | None = None,
        sort: str | None = None,
    ) -> dict[str, Any]:
        if source == "semantic_scholar":
            return self._s2_search(
                query=query,
                limit=limit,
                min_citation_count=min_citation_count,
                year=year,
                fields_of_study=fields_of_study,
                open_access_only=open_access_only,
            )

        yfrom, yto = self._resolve_year_range(year, year_from, year_to)

        if source in ("auto", "openalex"):
            try:
                return self._openalex.search_papers(
                    query=query,
                    limit=limit,
                    year_from=yfrom,
                    year_to=yto,
                    venue=venue,
                    sort=sort,
                )
            except Exception as exc:
                if source == "openalex":
                    raise
                logger.warning("OpenAlex search failed, falling back to S2: %s", exc)

        return self._s2_search(
            query=query,
            limit=limit,
            min_citation_count=min_citation_count,
            year=year,
            fields_of_study=fields_of_study,
            open_access_only=open_access_only,
        )

    # ------------------------------------------------------------------
    # Get paper
    # ------------------------------------------------------------------

    def get_paper(self, paper_id: str) -> dict[str, Any] | None:
        source = detect_paper_id_source(paper_id)

        if source == "s2":
            return self._get_paper_s2_first(paper_id)
        if source in ("doi", "openalex", "unknown"):
            return self._get_paper_openalex_first(paper_id)
        if source == "arxiv":
            return self._get_paper_s2_first(f"ARXIV:{paper_id}" if ":" not in paper_id else paper_id)

        return self._get_paper_openalex_first(paper_id)

    # ------------------------------------------------------------------
    # Recommend (S2 only)
    # ------------------------------------------------------------------

    def recommend_papers(
        self,
        *,
        positive_paper_ids: list[str],
        negative_paper_ids: list[str] | None = None,
        limit: int = 10,
    ) -> dict[str, Any]:
        return self._s2.recommend_papers(
            positive_paper_ids=positive_paper_ids,
            negative_paper_ids=negative_paper_ids,
            limit=limit,
        )

    # ------------------------------------------------------------------
    # BibTeX
    # ------------------------------------------------------------------

    def get_bibtex(self, paper_id: str) -> str | None:
        paper = self.get_paper(paper_id)
        if not paper:
            return None
        return generate_bibtex(paper)

    def get_bibtex_batch(self, paper_ids: list[str]) -> dict[str, str | None]:
        results: dict[str, str | None] = {}
        papers: list[dict[str, Any]] = []
        for pid in paper_ids:
            paper = self.get_paper(pid)
            if paper:
                papers.append(paper)
                results[pid] = None  # placeholder
            else:
                results[pid] = None

        if papers:
            batch_str = generate_bibtex_batch(papers)
            entries = [e.strip() for e in batch_str.split("\n\n") if e.strip()]
            paper_idx = 0
            for pid in paper_ids:
                if results.get(pid) is None and paper_idx < len(entries):
                    paper = self.get_paper(pid)
                    if paper:
                        results[pid] = entries[paper_idx]
                        paper_idx += 1

        return results

    # ------------------------------------------------------------------
    # Author search
    # ------------------------------------------------------------------

    def search_by_author(
        self,
        author_name: str,
        limit: int = 20,
        year_from: int | None = None,
        year_to: int | None = None,
    ) -> dict[str, Any]:
        try:
            return self._openalex.search_by_author(
                author_name, limit=limit, year_from=year_from, year_to=year_to,
            )
        except Exception as exc:
            logger.warning("OpenAlex author search failed, falling back to S2: %s", exc)
            return self._s2.search_papers(query=f"author:{author_name}", limit=limit)

    # ------------------------------------------------------------------
    # Citation network (OpenAlex only)
    # ------------------------------------------------------------------

    def get_citation_network(
        self,
        paper_id: str,
        max_nodes: int = 50,
        direction: str = "both",
    ) -> dict[str, Any]:
        return self._openalex.get_citation_network(
            paper_id, max_nodes=max_nodes, direction=direction,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _s2_search(
        self,
        *,
        query: str,
        limit: int,
        min_citation_count: int | None = None,
        year: int | str | None = None,
        fields_of_study: list[str] | str | None = None,
        open_access_only: bool | None = None,
    ) -> dict[str, Any]:
        return self._s2.search_papers(
            query=query,
            limit=limit,
            min_citation_count=min_citation_count,
            year=year,
            fields_of_study=fields_of_study,
            open_access_only=open_access_only,
        )

    def _get_paper_openalex_first(self, paper_id: str) -> dict[str, Any] | None:
        try:
            result = self._openalex.get_paper(paper_id)
            if result:
                return result
        except Exception as exc:
            logger.debug("OpenAlex get_paper failed for %s: %s", paper_id, exc)

        try:
            s2_id = paper_id
            if paper_id.startswith("10.") or "doi.org" in paper_id.lower():
                s2_id = f"DOI:{paper_id}" if not paper_id.upper().startswith("DOI:") else paper_id
            return self._unwrap_s2_paper_details(self._s2.get_paper_details(s2_id))
        except Exception as exc:
            logger.debug("S2 get_paper fallback failed for %s: %s", paper_id, exc)
            return None

    def _get_paper_s2_first(self, paper_id: str) -> dict[str, Any] | None:
        try:
            return self._unwrap_s2_paper_details(self._s2.get_paper_details(paper_id))
        except Exception as exc:
            logger.debug("S2 get_paper failed for %s: %s", paper_id, exc)

        try:
            result = self._openalex.get_paper(paper_id)
            if result:
                return result
        except Exception as exc:
            logger.debug("OpenAlex get_paper fallback failed for %s: %s", paper_id, exc)

        return None

    @staticmethod
    def _unwrap_s2_paper_details(details: dict[str, Any]) -> dict[str, Any] | None:
        paper = details.get("paper") if isinstance(details, dict) else None
        return paper if isinstance(paper, dict) else None

    @staticmethod
    def _resolve_year_range(
        year: int | str | None,
        year_from: int | None,
        year_to: int | None,
    ) -> tuple[int | None, int | None]:
        """Convert S2-style year param to year_from/year_to range."""
        if year_from is not None or year_to is not None:
            return year_from, year_to
        if year is None:
            return None, None
        year_str = str(year).strip()
        if "-" in year_str:
            parts = year_str.split("-", 1)
            try:
                return int(parts[0]), int(parts[1])
            except ValueError:
                return None, None
        try:
            y = int(year_str)
            return y, y
        except ValueError:
            return None, None
