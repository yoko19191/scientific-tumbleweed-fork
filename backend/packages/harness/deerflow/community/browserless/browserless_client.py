from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class BrowserlessClient:
    """Client for the Browserless headless Chrome content API."""

    def __init__(self, base_url: str = "http://localhost:3032", token: str = "", timeout_s: float = 30) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout_s = timeout_s

    async def fetch_html(
        self,
        url: str,
        wait_for_event: str = "",
        wait_for_timeout_ms: int = 0,
        wait_for_selector: str = "",
        wait_for_selector_timeout_ms: int = 5000,
        reject_resource_types: list[str] | None = None,
        reject_request_pattern: list[str] | None = None,
    ) -> str:
        payload: dict[str, Any] = {"url": url}
        if self.token:
            payload["token"] = self.token
        if wait_for_event:
            payload["waitForEvent"] = wait_for_event
        if wait_for_timeout_ms > 0:
            payload["waitForTimeout"] = wait_for_timeout_ms
        if wait_for_selector:
            payload["waitForSelector"] = {
                "selector": wait_for_selector,
                "timeout": wait_for_selector_timeout_ms,
            }
        if reject_resource_types:
            payload["rejectResourceTypes"] = reject_resource_types
        if reject_request_pattern:
            payload["rejectRequestPattern"] = reject_request_pattern

        try:
            async with httpx.AsyncClient(timeout=self.timeout_s) as client:
                response = await client.post(
                    f"{self.base_url}/content",
                    json=payload,
                    headers={
                        "Cache-Control": "no-cache",
                        "Content-Type": "application/json",
                    },
                )
            if response.status_code != 200:
                return f"Error: Browserless HTTP {response.status_code}: {response.text[:200]}"
            html = response.text
            if not html or not html.strip():
                return "Error: Browserless returned empty response"
            return html
        except httpx.TimeoutException:
            return f"Error: Browserless request timed out after {self.timeout_s}s"
        except httpx.RequestError as exc:
            logger.error("Browserless request failed: %s", exc)
            return f"Error: Browserless request failed: {exc!s}"
        except Exception as exc:
            logger.error("Browserless fetch failed: %s", exc)
            return f"Error: Browserless fetch failed: {exc!s}"
