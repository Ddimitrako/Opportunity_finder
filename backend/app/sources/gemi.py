from __future__ import annotations

from typing import Any

import httpx

from app.config import Settings


class GemiClient:
    """Small client for the official Open Data G.E.MI. API.

    The API is optional because production access requires a personal api_key.
    """

    def __init__(self, settings: Settings):
        self.settings = settings

    @property
    def enabled(self) -> bool:
        return bool(self.settings.gemi_api_key)

    async def search_companies(
        self,
        *,
        activities: list[str] | None = None,
        prefectures: list[int] | None = None,
        municipalities: list[str] | None = None,
        is_active: bool = True,
        offset: int = 0,
        size: int = 100,
    ) -> list[dict[str, Any]]:
        if not self.settings.gemi_api_key:
            return []
        params: list[tuple[str, str | int | bool]] = [
            ("isActive", is_active),
            ("resultsOffset", max(0, offset)),
            ("resultsSize", min(200, max(1, size))),
            ("resultsSortBy", "-incorporationDate"),
        ]
        for value in activities or []:
            params.append(("activities", value))
        for value in prefectures or []:
            params.append(("prefectures", value))
        for value in municipalities or []:
            params.append(("municipalities", value))
        payload = await self._get("/opendata/companies", params=params)
        results = payload.get("searchResults") if isinstance(payload, dict) else None
        return [item for item in results or [] if isinstance(item, dict)]

    async def company(self, gemi_number: str) -> dict[str, Any] | None:
        if not self.settings.gemi_api_key:
            return None
        payload = await self._get(f"/opendata/companies/{gemi_number}")
        return payload if isinstance(payload, dict) else None

    async def company_documents(self, gemi_number: str) -> list[dict[str, Any]]:
        if not self.settings.gemi_api_key:
            return []
        payload = await self._get(f"/opendata/companies/{gemi_number}/documents")
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        if isinstance(payload, dict):
            for key in ("documents", "results", "items", "data"):
                value = payload.get(key)
                if isinstance(value, list):
                    return [item for item in value if isinstance(item, dict)]
        return []

    async def _get(self, path: str, params: list[tuple[str, Any]] | None = None) -> Any:
        url = f"{str(self.settings.gemi_base_url).rstrip('/')}{path}"
        headers = {
            "Accept": "application/json",
            "api_key": str(self.settings.gemi_api_key),
            "User-Agent": self.settings.market_user_agent,
        }
        async with httpx.AsyncClient(timeout=self.settings.gemi_timeout_seconds, headers=headers) as client:
            response = await client.get(url, params=params)
            if response.status_code == 404:
                return {}
            response.raise_for_status()
            return response.json()
