from __future__ import annotations

import asyncio
import time
from datetime import date
from typing import Any

import httpx

from app.config import Settings
from app.models import Opportunity, ProcurementSearchRequest
from app.normalization import collect_cpv_codes, extract_records, first_text, parse_date, stable_id, truncate


class KhmdhsClient:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def search(self, request: ProcurementSearchRequest) -> list[Opportunity]:
        request_body: dict[str, Any] = {
            "title": request.query.strip()[:100],
            "cpvItems": request.cpv_codes,
            "dateFrom": request.date_from.isoformat(),
            "dateTo": request.date_to.isoformat(),
            "totalCostFrom": int(request.budget_min),
            "totalCostTo": int(request.budget_max),
            "isInitial": True,
            "isApproved": True,
            "isApproval": True,
        }
        notice_body: dict[str, Any] = {
            "title": request.query.strip()[:100],
            "cpvItems": request.cpv_codes,
            "dateFrom": request.date_from.isoformat(),
            "dateTo": request.date_to.isoformat(),
            "totalCostFrom": int(request.budget_min),
            "totalCostTo": int(request.budget_max),
        }
        request_records, notice_records = await asyncio.gather(
            self._search_endpoint("request", request_body, request.page),
            self._search_endpoint("notice", notice_body, request.page),
        )
        output = [self._to_opportunity(record, endpoint="notice") for record in notice_records]
        output.extend(self._to_opportunity(record, endpoint="request") for record in request_records)
        seen: set[str] = set()
        return [item for item in output if not (item.id in seen or seen.add(item.id))][: request.limit]

    async def _search_endpoint(self, endpoint: str, body: dict[str, Any], page: int) -> list[dict[str, Any]]:
        url = f"{str(self.settings.khmdhs_base_url).rstrip('/')}/khmdhs-opendata/{endpoint}"
        async with httpx.AsyncClient(
            timeout=self.settings.khmdhs_timeout_seconds,
            verify=self.settings.khmdhs_verify_ssl,
            headers={"Accept": "application/json", "Content-Type": "application/json"},
        ) as client:
            response = await client.post(url, params={"page": page}, json=body)
            if response.status_code == 404:
                return []
            response.raise_for_status()
            return extract_records(response.json())

    async def activity(self, date_from: date, date_to: date, limit: int = 100) -> list[Opportunity]:
        body: dict[str, Any] = {
            "dateFrom": date_from.isoformat(),
            "dateTo": date_to.isoformat(),
            "isInitial": True,
            "isApproved": True,
            "isApproval": True,
        }
        url = f"{str(self.settings.khmdhs_base_url).rstrip('/')}/khmdhs-opendata/request"
        async with httpx.AsyncClient(
            timeout=self.settings.khmdhs_timeout_seconds,
            verify=self.settings.khmdhs_verify_ssl,
            headers={"Accept": "application/json", "Content-Type": "application/json"},
        ) as client:
            response = await client.post(url, params={"page": 0}, json=body)
            response.raise_for_status()
            records = extract_records(response.json())
        return [self._to_opportunity(record) for record in records[:limit]]

    async def activity_count(self, date_from: date, date_to: date, cpv_codes: list[str] | None = None) -> int:
        body: dict[str, Any] = {
            "dateFrom": date_from.isoformat(),
            "dateTo": date_to.isoformat(),
        }
        if cpv_codes:
            body["cpvItems"] = cpv_codes
        url = f"{str(self.settings.khmdhs_base_url).rstrip('/')}/khmdhs-opendata/notice"
        async with httpx.AsyncClient(
            timeout=self.settings.khmdhs_timeout_seconds,
            verify=self.settings.khmdhs_verify_ssl,
            headers={"Accept": "application/json", "Content-Type": "application/json"},
        ) as client:
            response = await client.post(url, params={"page": 0}, json=body)
            if response.status_code == 404:
                return 0
            response.raise_for_status()
            payload = response.json()
        if isinstance(payload, dict) and isinstance(payload.get("totalElements"), int):
            return int(payload["totalElements"])
        return len(extract_records(payload))

    def _to_opportunity(self, record: dict[str, Any], endpoint: str | None = None) -> Opportunity:
        reference = first_text(record.get("referenceNumber"))
        title = first_text(record.get("title"), "ΚΗΜΔΗΣ πράξη χωρίς τίτλο")
        buyer = first_text(record.get("organization"), "Unknown buyer")
        buyer_type = first_text(record.get("typeOfContractingAuthority")) or first_text(
            record.get("classificationOfPublicLawOrganization")
        )
        budget = record.get("totalCostWithoutVAT") or record.get("budget") or record.get("totalCostWithVAT")
        cpv_codes = collect_cpv_codes(record)
        summary_parts = [
            title,
            first_text(record.get("procedureType")),
            " ".join(first_text(item.get("shortDescription")) for item in record.get("objectDetails") or [] if isinstance(item, dict)),
        ]
        summary = truncate(" ".join(part for part in summary_parts if part), 320)
        url = _extract_platform_url(record)
        if not url and reference:
            attachment_endpoint = _attachment_endpoint(reference)
            url = f"{str(self.settings.khmdhs_base_url).rstrip('/')}/khmdhs-opendata/{attachment_endpoint}/attachment/{reference}"
        status_label = first_text(record.get("status") or record.get("state") or record.get("approvalStatus"))
        notice_type = first_text(record.get("noticeType") or record.get("actType") or record.get("documentType"))
        organization_key = _extract_key(record.get("organization"))
        resolved_endpoint = endpoint or (_attachment_endpoint(reference) if reference else "request")
        procurement_stage = {
            "request": "approved_request",
            "notice": "notice",
            "auction": "award",
            "contract": "contract",
            "payment": "payment",
        }.get(resolved_endpoint, "unknown")
        candidate_type = "bid_now" if resolved_endpoint == "notice" else "position_early" if resolved_endpoint == "request" else "historical"
        deadline = None
        if resolved_endpoint == "notice":
            deadline = parse_date(
                record.get("deadline")
                or record.get("submissionDeadline")
                or record.get("tenderDeadline")
                or record.get("offersDeadline")
            )
        return Opportunity(
            id=f"khmdhs-{stable_id(reference, title, buyer)}",
            source="khmdhs",
            source_label="ΚΗΜΔΗΣ",
            title=title,
            buyer=buyer,
            buyer_type=buyer_type or None,
            procedure_type=first_text(record.get("procedureType")) or None,
            cpv_codes=cpv_codes,
            budget=float(budget) if budget not in (None, "") else None,
            deadline=deadline,
            published_at=parse_date(record.get("submissionDate") or record.get("signedDate")),
            location=first_text(record.get("nutsCode")) or None,
            url=url,
            platform_label="ΚΗΜΔΗΣ",
            source_reference=reference or None,
            status_label=status_label or None,
            notice_type=notice_type or None,
            summary=summary,
            raw_text=" ".join(part for part in (summary, status_label, notice_type) if part),
            candidate_type=candidate_type,
            procurement_stage=procurement_stage,
            source_payload={"referenceNumber": reference, "organizationKey": organization_key, "fetchedAt": int(time.time())},
        )


def _extract_platform_url(record: dict[str, Any]) -> str | None:
    for key in ("url", "link", "documentUrl", "documentURL", "decisionUrl", "attachmentUrl"):
        value = first_text(record.get(key))
        if value.startswith("http"):
            return value

    links = record.get("links")
    if isinstance(links, dict):
        for value in links.values():
            text = first_text(value)
            if text.startswith("http"):
                return text
    return None


def _extract_key(value: Any) -> str | None:
    if isinstance(value, dict):
        text = first_text(value.get("key") or value.get("id"))
        return text or None
    return None


def _attachment_endpoint(reference: str) -> str:
    if "PROC" in reference:
        return "notice"
    if "AWRD" in reference:
        return "auction"
    if "SYMV" in reference:
        return "contract"
    if "PAY" in reference:
        return "payment"
    return "request"
