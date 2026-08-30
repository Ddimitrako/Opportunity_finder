from __future__ import annotations

from datetime import date
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
                "total-value",
                "classification-cpv",
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

    async def activity(self, date_from: date, date_to: date, limit: int = 100, cpv_codes: list[str] | None = None) -> list[Opportunity]:
        cpv_terms = " OR ".join(f"classification-cpv={code.split('-')[0]}" for code in cpv_codes or [])
        query = "organisation-country-buyer=GRC"
        if cpv_terms:
            query = f"{query} AND ({cpv_terms})"
        body: dict[str, Any] = {
            "query": query,
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
            "page": 1,
            "limit": min(limit, 100),
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
        opportunities = [self._to_opportunity(record) for record in records[:limit]]
        return [
            opportunity
            for opportunity in opportunities
            if opportunity.published_at is not None and date_from <= opportunity.published_at <= date_to
        ]

    async def market_records(self, date_from: date, date_to: date, limit: int = 100) -> list[dict[str, Any]]:
        """Return Greece software notices across planning, competition and result stages."""
        cpv_terms = " OR ".join(f"classification-cpv={code.split('-')[0]}" for code in request_cpv_codes())
        query = (
            f"organisation-country-buyer=GRC AND publication-date>={date_from.strftime('%Y%m%d')} "
            f"AND publication-date<={date_to.strftime('%Y%m%d')} AND ({cpv_terms})"
        )
        page_size = min(100, max(1, limit))
        body: dict[str, Any] = {
            "query": query,
            "fields": [
                "publication-number", "notice-title", "buyer-name", "organisation-country-buyer",
                "publication-date", "notice-type", "form-type", "notice-subtype", "deadline",
                "BT-131(d)-Lot", "deadline-receipt-tender-date-lot", "classification-cpv",
                "winner-name", "winner-country", "total-value",
            ],
            "page": 1,
            "limit": page_size,
            "scope": "ALL",
            "paginationMode": "PAGE_NUMBER",
        }
        url = f"{str(self.settings.ted_base_url).rstrip('/')}/v3/notices/search"
        collected: list[dict[str, Any]] = []
        async with httpx.AsyncClient(
            timeout=self.settings.ted_timeout_seconds,
            headers={"Accept": "application/json", "Content-Type": "application/json"},
        ) as client:
            for page in range(1, ((min(limit, 1000) - 1) // page_size) + 2):
                body["page"] = page
                response = await client.post(url, json=body)
                response.raise_for_status()
                records = extract_records(response.json())
                collected.extend(records)
                if len(records) < page_size or len(collected) >= min(limit, 1000):
                    break
        return [
            record for record in collected[:limit]
            if (published := parse_date(record.get("publication-date") or record.get("publicationDate")))
            and date_from <= published <= date_to
        ]

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
        notice_type_text = notice_type.casefold()
        deadline = parse_date(
            record.get("deadline")
            or record.get("BT-131(d)-Lot")
            or record.get("deadline-receipt-tender-date-lot")
        )
        summary = truncate(" ".join([title, buyer, first_text(record.get("organisation-country-buyer")), notice_type]), 300)
        url = f"https://ted.europa.eu/en/notice/-/detail/{publication_number}" if publication_number else None
        raw_budget = record.get("total-value") or record.get("totalValue")
        try:
            budget = float(first_text(raw_budget)) if raw_budget not in (None, "") else None
        except (TypeError, ValueError):
            budget = None
        if any(term in notice_type_text for term in ("award", "result")):
            procurement_stage = "award"
            candidate_type = "historical"
        elif any(term in notice_type_text for term in ("prior", "planning", "consultation", "market")):
            procurement_stage = "planning"
            candidate_type = "position_early"
        else:
            procurement_stage = "competition"
            candidate_type = "bid_now" if deadline else "review"
        return Opportunity(
            id=f"ted-{stable_id(publication_number, title, buyer)}",
            source="ted",
            source_label="TED",
            title=title,
            buyer=buyer,
            buyer_type=None,
            procedure_type=notice_type or None,
            cpv_codes=cpv_codes,
            budget=budget,
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
            candidate_type=candidate_type,
            procurement_stage=procurement_stage,
            source_payload={"publicationNumber": publication_number},
        )


def request_cpv_codes() -> list[str]:
    # Keep the market adapter independent from a UI request while sharing the same software focus.
    from app.models import DEFAULT_CPV_CODES

    return DEFAULT_CPV_CODES
