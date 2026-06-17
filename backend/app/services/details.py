from __future__ import annotations

from datetime import date
from typing import Any

import httpx

from app.config import Settings
from app.models import DocumentLink, GuidanceChecklistItem, LifecycleStep, OpportunityDetails, OpportunityGuidance, SourceName
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
            guidance=_demo_guidance(),
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
            guidance=_khmdhs_guidance(reference, metadata, related_references, documents),
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
            guidance=_ted_guidance(notice, documents, platform_url),
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


def _khmdhs_guidance(
    reference: str,
    metadata: dict[str, Any],
    related_references: dict[str, list[str]],
    documents: list[DocumentLink],
) -> OpportunityGuidance:
    stage_defs = [
        ("request", "Αίτημα", "requests", "Budget/request act. Usually not ready for an economic operator bid yet."),
        ("approved_request", "Εγκεκριμένο αίτημα", "approvedRequests", "Budget/request approval. Watch for the procurement notice."),
        ("notice", "Πρόσκληση / Διακήρυξη", "notices", "Competition or invitation document. This is usually where bidding instructions appear."),
        ("award", "Ανάθεση", "auctions", "Award decision. Useful for learning, usually too late to bid."),
        ("contract", "Σύμβαση", "contracts", "Signed contract stage."),
        ("payment", "Πληρωμή", "payments", "Payment stage after contract execution."),
    ]
    refs_by_key = {key: related_references.get(key, []) for _, _, key, _ in stage_defs}
    if reference and not any(reference in refs for refs in refs_by_key.values()):
        endpoint = _khmdhs_search_endpoint(reference)
        if endpoint == "request":
            refs_by_key["requests"] = [reference, *refs_by_key.get("requests", [])]
        elif endpoint == "notice":
            refs_by_key["notices"] = [reference, *refs_by_key.get("notices", [])]
        elif endpoint == "auction":
            refs_by_key["auctions"] = [reference, *refs_by_key.get("auctions", [])]
        elif endpoint == "contract":
            refs_by_key["contracts"] = [reference, *refs_by_key.get("contracts", [])]

    current_index = 0
    for index, (_, _, key, _) in enumerate(stage_defs):
        if refs_by_key.get(key):
            current_index = index

    steps: list[LifecycleStep] = []
    for index, (stage_id, label, key, description) in enumerate(stage_defs):
        refs = refs_by_key.get(key, [])
        status = "upcoming"
        if refs:
            status = "current" if index == current_index else "complete"
        elif index < current_index:
            status = "unknown"
        url = _document_url(documents, refs[0]) if refs else None
        steps.append(
            LifecycleStep(
                id=stage_id,
                label=label,
                status=status,
                description=description,
                references=refs,
                url=url,
            )
        )

    current_stage = stage_defs[current_index][0]
    current_label = stage_defs[current_index][1]
    deadline = parse_date(metadata.get("procurementDeliveryDate"))
    notice_refs = refs_by_key.get("notices", [])
    actionable = bool(notice_refs and (deadline is None or deadline >= date.today()))
    primary_link = _document_url(documents, notice_refs[0]) if notice_refs else _document_url(documents, reference)

    if actionable:
        next_action = "Open the notice/diakiryxi document, confirm submission method and deadline, then prepare your offer."
    elif not notice_refs:
        next_action = "Not ready to bid yet. Monitor this ADAM chain until a PROC notice appears."
    else:
        next_action = "Competition notice exists, but the deadline is missing or expired. Review documents for learning or contact the buyer."

    checklist = _bid_checklist(
        source="khmdhs",
        has_source_document=bool(primary_link),
        has_competition=bool(notice_refs),
        deadline=deadline,
        actionable=actionable,
    )
    watch_items = [
        "A linked PROC notice in KIMDIS notices.",
        "Submission method: ESIDIS, email, platform, or instructions inside the notice.",
        "Clarifications, amended notices, award decisions, contract and payment records.",
    ]
    return OpportunityGuidance(
        current_stage=current_stage,
        current_stage_label=current_label,
        is_actionable=actionable,
        next_action=next_action,
        stage_steps=steps,
        checklist=checklist,
        watch_items=watch_items,
        primary_action_link=primary_link,
    )


def _ted_guidance(notice: dict[str, Any], documents: list[DocumentLink], platform_url: str | None) -> OpportunityGuidance:
    notice_type = first_text(notice.get("notice-type") or notice.get("noticeType")).casefold()
    deadline = parse_date(
        notice.get("deadline")
        or notice.get("BT-131(d)-Lot")
        or notice.get("deadline-receipt-tender-date-lot")
    )
    stage_defs = [
        ("planning", "Planning / consultation", "Early market signal or prior information."),
        ("competition", "Competition", "Active tender or contract notice. This is usually actionable."),
        ("submission", "Submission", "Prepare and submit response through the platform/instructions."),
        ("result", "Result / award", "Award or result notice. Usually no longer open for bidding."),
        ("modification", "Contract modification", "Post-award modification/completion information."),
    ]
    current_stage = _ted_stage(notice_type, deadline)
    current_index = next((index for index, (stage_id, _, _) in enumerate(stage_defs) if stage_id == current_stage), 0)
    actionable = current_stage in {"competition", "submission"} and (deadline is None or deadline >= date.today())
    primary_link = _preferred_document_url(documents) or platform_url

    steps = [
        LifecycleStep(
            id=stage_id,
            label=label,
            status="current" if index == current_index else "complete" if index < current_index else "upcoming",
            description=description,
            references=[],
            url=primary_link if index == current_index else None,
        )
        for index, (stage_id, label, description) in enumerate(stage_defs)
    ]

    if actionable:
        next_action = "Open the TED notice/documents, confirm eSubmission or buyer instructions, then prepare your response."
    elif current_stage in {"result", "modification"}:
        next_action = "This looks post-award. Use it for market intelligence, not a new bid."
    elif current_stage == "planning":
        next_action = "Monitor for a future competition notice and prepare capability material early."
    else:
        next_action = "Open the source record and confirm whether the notice is still open before investing time."

    return OpportunityGuidance(
        current_stage=current_stage,
        current_stage_label=stage_defs[current_index][1],
        is_actionable=actionable,
        next_action=next_action,
        stage_steps=steps,
        checklist=_bid_checklist(
            source="ted",
            has_source_document=bool(primary_link),
            has_competition=current_stage in {"competition", "submission"},
            deadline=deadline,
            actionable=actionable,
        ),
        watch_items=[
            "TED document links and buyer instructions.",
            "Deadline and submission platform, often eSubmission/eTendering or buyer portal.",
            "Clarifications, corrigenda, result/award notices and contract modifications.",
        ],
        primary_action_link=primary_link,
    )


def _demo_guidance() -> OpportunityGuidance:
    return OpportunityGuidance(
        current_stage="example",
        current_stage_label="Example",
        is_actionable=False,
        next_action="Demo records are examples. Use them to understand the workflow, not to submit a bid.",
        stage_steps=[
            LifecycleStep(id="example", label="Example", status="current", description="Local demo data."),
        ],
        checklist=[
            GuidanceChecklistItem(label="Open source document", detail="Demo data has no live source document.", status="blocked"),
        ],
        watch_items=["Switch to KIMDIS or TED for live procurement records."],
    )


def _ted_stage(notice_type: str, deadline: date | None) -> str:
    if any(term in notice_type for term in ("award", "result", "contract award")):
        return "result"
    if any(term in notice_type for term in ("modification", "change")):
        return "modification"
    if any(term in notice_type for term in ("prior", "planning", "consultation", "market")):
        return "planning"
    if deadline is not None and deadline < date.today():
        return "result"
    if any(term in notice_type for term in ("contract", "competition", "call", "tender")) or deadline is not None:
        return "competition"
    return "planning"


def _bid_checklist(
    source: str,
    has_source_document: bool,
    has_competition: bool,
    deadline: date | None,
    actionable: bool,
) -> list[GuidanceChecklistItem]:
    source_name = "KIMDIS/ESIDIS" if source == "khmdhs" else "TED/eSubmission"
    deadline_ok = deadline is not None and deadline >= date.today()
    return [
        GuidanceChecklistItem(
            label="Open source document",
            detail=f"Read the official {source_name} document before deciding.",
            status="done" if has_source_document else "blocked",
        ),
        GuidanceChecklistItem(
            label="Confirm competition notice",
            detail="A request/planning record is not enough; look for a notice/call/tender document.",
            status="done" if has_competition else "watch",
        ),
        GuidanceChecklistItem(
            label="Check deadline and submission method",
            detail="Confirm exact due date, platform, required signatures and file formats.",
            status="done" if actionable and deadline_ok else "watch" if has_competition else "blocked",
        ),
        GuidanceChecklistItem(
            label="Collect company/legal documents",
            detail="Prepare tax/social security proofs, declarations, certificates and authorization documents.",
            status="todo" if actionable else "watch",
        ),
        GuidanceChecklistItem(
            label="Prepare technical offer",
            detail="Map your solution to each technical requirement and note assumptions/exclusions.",
            status="todo" if actionable else "watch",
        ),
        GuidanceChecklistItem(
            label="Prepare financial offer",
            detail="Price the scope, VAT treatment, support, hosting, licensing and delivery milestones.",
            status="todo" if actionable else "watch",
        ),
        GuidanceChecklistItem(
            label="Submit and monitor",
            detail="Submit through the required platform/instructions, then watch clarifications and award results.",
            status="todo" if actionable else "watch",
        ),
    ]


def _document_url(documents: list[DocumentLink], reference: str | None) -> str | None:
    if not reference:
        return None
    return next((document.url for document in documents if document.reference == reference), None)


def _preferred_document_url(documents: list[DocumentLink]) -> str | None:
    for preferred in ("html", "htmlDirect", "pdfs", "pdf", "notice", "request"):
        for document in documents:
            if document.document_type == preferred and document.url:
                return document.url
    return documents[0].url if documents else None
