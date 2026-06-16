from __future__ import annotations

from typing import Any

import httpx

from app.config import Settings
from app.models import DocumentLink, OpportunityDetails, SourceName
from app.normalization import extract_records, first_text, parse_date


KHMDHS_CHAIN_DOCUMENTS = {
    "requests": ("Αίτημα", "request"),
    "approvedRequests": ("Εγκεκριμένο αίτημα", "request"),
    "notices": ("Πρόσκληση / Διακήρυξη", "notice"),
    "auctions": ("Ανάθεση", "auction"),
    "contracts": ("Σύμβαση", "contract"),
    "payments": ("Πληρωμή", "payment"),
}

TED_DETAIL_FIELDS = [
    "publication-number",
    "notice-title",
    "buyer-name",
    "publication-date",
    "notice-type",
    "links",
    "deadline",
    "BT-131(d)-Lot",
    "deadline-receipt-tender-date-lot",
    "organisation-country-buyer",
]


class OpportunityDetailsService:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def get_details(self, source: SourceName, reference: str) -> OpportunityDetails:
        if source == "khmdhs":
            return await self._khmdhs_details(reference)
        if source == "ted":
            return await self._ted_details(reference)
        return OpportunityDetails(
            source=source,
            reference=reference,
            title="Demo opportunity",
            summary="Demo details are local examples and do not have external documents.",
        )

    async def _khmdhs_details(self, reference: str) -> OpportunityDetails:
        base = str(self.settings.khmdhs_base_url).rstrip("/")
        async with httpx.AsyncClient(
            timeout=self.settings.khmdhs_timeout_seconds,
            verify=self.settings.khmdhs_verify_ssl,
            headers={"Accept": "application/json"},
        ) as client:
            metadata = await self._khmdhs_metadata(client, reference)
            chain_response = await client.get(f"{base}/khmdhs-opendata/adamChain/{reference}")
            chain_response.raise_for_status()
            chain = chain_response.json()

        documents: list[DocumentLink] = []
        related_references: dict[str, list[str]] = {}
        for key, (label, endpoint) in KHMDHS_CHAIN_DOCUMENTS.items():
            refs = [str(item) for item in chain.get(key) or [] if item]
            related_references[key] = refs
            for item_ref in refs:
                documents.append(
                    DocumentLink(
                        label=f"{label} {item_ref}",
                        url=f"{base}/khmdhs-opendata/{endpoint}/attachment/{item_ref}",
                        document_type=endpoint,
                        language="el",
                        reference=item_ref,
                    )
                )

        title = first_text(metadata.get("title")) if metadata else None
        primary_document_url = next(
            (document.url for document in documents if document.reference == reference),
            documents[0].url if documents else None,
        )
        return OpportunityDetails(
            source="khmdhs",
            reference=reference,
            title=title,
            platform_url=primary_document_url or f"{base}/upgkimdis/unprotected/home.xhtml",
            summary=first_text(metadata.get("shortDescription")) if metadata else None,
            metadata=_compact_khmdhs_metadata(metadata),
            documents=documents,
            related_references=related_references,
            raw={"metadata": metadata, "adamChain": chain},
        )

    async def _khmdhs_metadata(self, client: httpx.AsyncClient, reference: str) -> dict[str, Any]:
        base = str(self.settings.khmdhs_base_url).rstrip("/")
        endpoint = _khmdhs_search_endpoint(reference)
        if not endpoint:
            return {}
        body = _khmdhs_reference_search_body(reference)
        response = await client.post(f"{base}/khmdhs-opendata/{endpoint}", params={"page": 0}, json=body)
        if response.status_code == 404:
            return {}
        response.raise_for_status()
        records = extract_records(response.json())
        return records[0] if records else {}

    async def _ted_details(self, reference: str) -> OpportunityDetails:
        body: dict[str, Any] = {
            "query": f"publication-number={reference}",
            "fields": TED_DETAIL_FIELDS,
            "page": 1,
            "limit": 1,
            "scope": "ALL",
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

        notice = records[0] if records else {}
        title = first_text(notice.get("notice-title") or notice.get("noticeTitle"))
        links = notice.get("links") if isinstance(notice.get("links"), dict) else {}
        documents = _ted_documents(links)
        platform_url = _preferred_ted_link(links, "html") or f"https://ted.europa.eu/en/notice/-/detail/{reference}"
        return OpportunityDetails(
            source="ted",
            reference=reference,
            title=title,
            platform_url=platform_url,
            summary=" ".join(part for part in (title, first_text(notice.get("buyer-name"))) if part),
            metadata=_compact_ted_metadata(notice),
            documents=documents,
            raw={"notice": notice},
        )


def _khmdhs_search_endpoint(reference: str) -> str | None:
    if "REQ" in reference:
        return "request"
    if "PROC" in reference:
        return "notice"
    if "AWRD" in reference:
        return "auction"
    if "SYMV" in reference:
        return "contract"
    return None


def _khmdhs_reference_search_body(reference: str) -> dict[str, Any]:
    common: dict[str, Any] = {"referenceNumber": reference}
    if "REQ" in reference:
        common.update({"isInitial": True, "isApproved": True, "isApproval": True})
    return common


def _compact_khmdhs_metadata(record: dict[str, Any]) -> dict[str, Any]:
    if not record:
        return {}
    keys = [
        "referenceNumber",
        "title",
        "organization",
        "procedureType",
        "submissionDate",
        "signedDate",
        "procurementDeliveryDate",
        "totalCostWithoutVAT",
        "totalCostWithVAT",
        "nutsCode",
    ]
    return {key: record.get(key) for key in keys if record.get(key) not in (None, "", [])}


def _compact_ted_metadata(notice: dict[str, Any]) -> dict[str, Any]:
    if not notice:
        return {}
    deadline = parse_date(
        notice.get("deadline")
        or notice.get("BT-131(d)-Lot")
        or notice.get("deadline-receipt-tender-date-lot")
    )
    return {
        "publicationNumber": first_text(notice.get("publication-number")),
        "title": first_text(notice.get("notice-title")),
        "buyer": first_text(notice.get("buyer-name")),
        "noticeType": first_text(notice.get("notice-type")),
        "publicationDate": first_text(notice.get("publication-date")),
        "deadline": deadline.isoformat() if deadline else None,
        "country": first_text(notice.get("organisation-country-buyer")),
    }


def _ted_documents(links: dict[str, Any]) -> list[DocumentLink]:
    documents: list[DocumentLink] = []
    for link_type in ("html", "htmlDirect", "pdfs", "pdf", "xml"):
        values = links.get(link_type)
        if isinstance(values, dict):
            for language, url in values.items():
                if isinstance(url, str) and url.startswith("http"):
                    documents.append(
                        DocumentLink(
                            label=f"TED {link_type.upper()} {language}",
                            url=url,
                            document_type=link_type,
                            language=language,
                        )
                    )
        elif isinstance(values, str) and values.startswith("http"):
            documents.append(DocumentLink(label=f"TED {link_type.upper()}", url=values, document_type=link_type))
    return documents


def _preferred_ted_link(links: dict[str, Any], link_type: str) -> str | None:
    values = links.get(link_type)
    if isinstance(values, dict):
        for language in ("ELL", "ENG", "MUL"):
            value = values.get(language)
            if isinstance(value, str):
                return value
        for value in values.values():
            if isinstance(value, str):
                return value
    return values if isinstance(values, str) else None
