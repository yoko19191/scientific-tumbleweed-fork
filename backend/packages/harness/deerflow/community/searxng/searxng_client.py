from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class SearxngClient:
    """Client for a SearXNG JSON search endpoint."""

    def __init__(self, base_url: str = "http://localhost:8088", timeout_s: float = 30) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_s = timeout_s

    async def search(
        self,
        query: str,
        max_results: int = 5,
        categories: list[str] | None = None,
        language: str = "auto",
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {
            "q": query,
            "format": "json",
            "language": language,
            "pageno": 1,
        }
        if max_results:
            params["limit"] = max_results
        if categories:
            params["categories"] = ",".join(categories)

        logger.debug("Searching SearXNG at %s with query: %s", self.base_url, query)
        async with httpx.AsyncClient(timeout=self.timeout_s) as client:
            response = await client.get(
                f"{self.base_url}/search",
                params=params,
                headers={
                    "Accept": "application/json",
                    "User-Agent": "Mozilla/5.0 (compatible; ScientificTumbleweed/1.0)",
                },
            )
            response.raise_for_status()
            data = response.json()
        results = data.get("results", [])
        return results[:max_results] if max_results else results
