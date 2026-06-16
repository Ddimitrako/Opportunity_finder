from __future__ import annotations

from typing import Any

import httpx

from app.config import Settings
from app.models import Opportunity, ProcurementSearchRequest
from app.normalization import collect_cpv_codes, extract_records, first_text, parse_date, stable_id, truncate


class TedClient:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def search(self, request: ProcurementSearchRequest) -> list[Opportunity]:
        cpv_terms = " OR ".join(f"classification-cpv={code.split('-')[0]}" for code in request.cpv_codes)
        text_query = request.query.strip().replace('"', "")
        search_terms = [term for term in (cpv_terms, f'notice-title="{text_query}"' if text_query else "") if term]
        expert_query = "organisation-country-buyer=GRC"
        if search_terms:
            expert_query = f"{expert_query} AND ({' OR '.join(search_terms)})"
        body: dict[str, Any] = {
            "query": expert_query,
            "fields": [
                "publication-number",
                "notice-title",
                "buyer-name",
                "organisation-country-buyer",
                "publication-date",
                "notice-type",
                "deadline",
                "BT-131(d)-Lot",
                "deadline-receipt-tender-date-lot",
            ],
            "page": max(1, request.page + 1),
            "limit": min(request.limit, 50),
            "scope": "ACTIVE",
            "paginationMode": "PAGE_NUMBER",
        }
        url = f"{str(self.settings.ted_base_url).rstrip('/')}/v3/notices/search"
        async with httpx.AsyncClient(
            timeout=self.settings.ted_timeout_seconds,
            headers={"Accept": "application/json", "Content-Type": "application/json"},
        ) as client:
            response = await client.post(url, json=body)
            response.raise_for_status()
            records = extract_records(response.json())
        return [self._to_opportunity(record) for record in records[: request.limit]]

    def _to_opportunity(self, record: dict[str, Any]) -> Opportunity:
        title = first_text(
            record.get("notice-title")
            or record.get("noticeTitle")
            or record.get("title"),
            "TED notice without title",
        )
        buyer = first_text(record.get("buyer-name") or record.get("buyerName") or record.get("buyer"), "Unknown buyer")
        publication_number = first_text(record.get("publication-number") or record.get("publicationNumber"))
        cpv_codes = collect_cpv_codes(record)
        notice_type = first_text(record.get("notice-type") or record.get("noticeType"))
        deadline = parse_date(
            record.get("deadline")
            or record.get("BT-131(d)-Lot")
            or record.get("deadline-receipt-tender-date-lot")
        )
        summary = truncate(" ".join([title, buyer, first_text(record.get("organisation-country-buyer")), notice_type]), 300)
        url = f"https://ted.europa.eu/en/notice/-/detail/{publication_number}" if publication_number else None
        return Opportunity(
            id=f"ted-{stable_id(publication_number, title, buyer)}",
            source="ted",
            source_label="TED",
            title=title,
            buyer=buyer,
            buyer_type=None,
            procedure_type=notice_type or None,
            cpv_codes=cpv_codes,
            budget=None,
            deadline=deadline,
            published_at=parse_date(record.get("publication-date") or record.get("publicationDate")),
            country=first_text(record.get("organisation-country-buyer"), "GR"),
            url=url,
            platform_label="TED",
            source_reference=publication_number or None,
            status_label=None,
            notice_type=notice_type or None,
            summary=summary,
            raw_text=summary,
            source_payload={"publicationNumber": publication_number},
        )
