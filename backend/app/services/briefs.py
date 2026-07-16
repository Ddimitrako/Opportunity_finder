from __future__ import annotations

import io
import json
import re
import sqlite3
from contextlib import closing
from datetime import date, datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

import httpx

from app.config import Settings
from app.models import (
    BriefBudgetAssessment,
    BriefContinuityAssessment,
    BriefEvidence,
    BriefFinding,
    BriefHistoryItem,
    BriefProcurementAccess,
    BriefScoreDimension,
    DocumentBrief,
    DocumentBriefResponse,
    DocumentLink,
    OpportunityDetails,
    SourceName,
)
from app.normalization import first_text, parse_date
from app.services.bookmarks import _resolve_db_path
from app.services.buyer_intelligence import BuyerIntelligenceService, _similar_opportunities
from app.services.details import OpportunityDetailsService
from app.sources.khmdhs import KhmdhsClient


BRIEF_SCHEMA_VERSION = 2
PROCUREMENT_RULES_VERSION = "gr-4412-2026-07-09"
DIRECT_AWARD_THRESHOLD_WITHOUT_VAT = 30_000.0
LEGAL_BASIS_URL = "https://eadhsy.gr/n4412/n4412fulltextlinks.html"
MAX_DOCUMENTS = 6
MAX_DOCUMENT_BYTES = 8_000_000
MAX_PDF_PAGES = 80
MAX_PAGE_CHARS = 12_000
MAX_MODEL_EVIDENCE_CHARS = 120_000
CHUNK_CHARS = 3_000
EXCERPT_CHARS = 700

DIMENSIONS = (
    ("access_timing", "Πρόσβαση & χρόνος", 25),
    ("commercial_value", "Εμπορική αξία", 20),
    ("technical_clarity", "Τεχνική σαφήνεια", 20),
    ("qualification_burden", "Απαιτήσεις συμμετοχής", 15),
    ("contract_risk", "Συμβατικός κίνδυνος", 10),
    ("strategic_value", "Στρατηγική αξία", 10),
)

RELEVANCE_TERMS = (
    "πρόσκληση", "προσφορά", "οικονομικό φορέα", "ανάδοχ", "σύμβασ", "προϋπολογ",
    "χωρίς φπα", "με φπα", "προθεσμ", "υποβολ", "κριτήριο", "εγγυη", "πιστοποι",
    "τεχνικ", "παραδοτέ", "διάρκεια", "πληρωμ", "ρήτρα", "sla", "υποστήριξ",
    "συντήρησ", "επέκτασ", "αναβάθμισ", "υφιστάμεν", "σε συνέχεια", "αδαμ",
    "invitation", "economic operator", "award", "contract", "deadline", "submission",
    "evaluation", "guarantee", "deliverable", "maintenance", "extension", "existing system",
)
CONTINUITY_TERMS = (
    "σε συνέχεια της", "συνέχιση της", "επέκταση του υφιστάμεν", "επέκταση της υφιστάμεν",
    "συντήρηση του υφιστάμεν", "συντήρηση της υφιστάμεν", "αναβάθμιση του υφιστάμεν",
    "αναβάθμιση της υφιστάμεν", "προηγούμενη σύμβαση", "αρχική σύμβαση",
    "continuation of", "extension of the existing", "maintenance of the existing",
    "upgrade of the existing", "previous contract",
)
NAMED_INVITATION_TERMS = (
    "πρόσκληση υποβολής προσφοράς προς", "καλεί τον οικονομικό φορέα", "καλεί την εταιρεία",
    "προς τον οικονομικό φορέα", "invitation to submit an offer to", "invites the economic operator",
)


class DocumentBriefService:
    def __init__(self, settings: Settings, details_service: OpportunityDetailsService | None = None):
        self.settings = settings
        self.details_service = details_service or OpportunityDetailsService(settings)
        self.db_path = _resolve_db_path(Path(settings.bookmark_db_path))
        self._init_db()

    def get_cached_brief(self, source: SourceName, reference: str) -> DocumentBriefResponse:
        row = self._get_row(source, reference)
        if not row:
            return DocumentBriefResponse(brief=None, cached=False, outdated=False, message="No saved AI brief yet.")
        brief = _row_to_brief(row)
        brief.cached = True
        outdated = brief.schema_version < BRIEF_SCHEMA_VERSION
        return DocumentBriefResponse(
            brief=brief,
            cached=True,
            outdated=outdated,
            message="This brief uses the previous format. Regenerate it for the v2 scorecard." if outdated else None,
        )

    async def generate_brief(self, source: SourceName, reference: str, *, regenerate: bool = False) -> DocumentBriefResponse:
        cached = self.get_cached_brief(source, reference)
        if cached.brief and not regenerate:
            return cached
        if not self.settings.openai_api_key:
            return DocumentBriefResponse(
                brief=None,
                cached=False,
                outdated=False,
                message="OPENAI_API_KEY is not configured. Add it to .env.local and try again.",
            )

        details = await self.details_service.get_details(source, reference)
        documents = await _fetch_document_texts(details.documents, reference)
        evidence = _build_evidence_catalog(documents)
        access, continuity, budget, evidence = _analyze_procurement(details, documents, evidence)
        history = await _fetch_12_month_history(details, self.settings)

        if not any(document.get("readable") for document in documents):
            brief = _fallback_brief(
                details,
                access,
                continuity,
                budget,
                history,
                evidence,
                "Τα διαθέσιμα έγγραφα δεν περιέχουν αναγνώσιμο κείμενο. Απαιτείται χειροκίνητος έλεγχος.",
            )
            self._save_brief(brief)
            return DocumentBriefResponse(brief=brief, cached=False, outdated=False)

        try:
            brief = await self._call_openai(details, evidence, access, continuity, budget, history)
        except Exception as exc:
            brief = _fallback_brief(
                details,
                access,
                continuity,
                budget,
                history,
                evidence,
                f"Η AI ανάλυση δεν ολοκληρώθηκε ({exc.__class__.__name__}). Ελέγξτε τα έγγραφα χειροκίνητα.",
            )
            return DocumentBriefResponse(
                brief=brief,
                cached=False,
                outdated=False,
                message="AI analysis failed safely; no unsupported conclusions were saved.",
            )

        self._save_brief(brief)
        return DocumentBriefResponse(brief=brief, cached=False, outdated=False)

    async def _call_openai(
        self,
        details: OpportunityDetails,
        evidence: list[BriefEvidence],
        access: BriefProcurementAccess,
        continuity: BriefContinuityAssessment,
        budget: BriefBudgetAssessment,
        history: list[BriefHistoryItem],
    ) -> DocumentBrief:
        evidence_payload = [item.model_dump(mode="json") for item in evidence]
        prompt = {
            "role": "You are a cautious bid manager and CEO adviser evaluating a Greek public-sector software opportunity for a generic software vendor.",
            "language": "Greek",
            "rules": [
                "Use only the supplied evidence. Never invent a deadline, requirement, incumbent, payment term or commercial fact.",
                "Every finding and score reason must cite one or more supplied evidence IDs. If evidence is absent, return Unknown and an empty evidence_ids list.",
                "Do not override deterministic procurement facts. A value <= EUR 30,000 without VAT is only direct-award eligibility, never proof that work is pre-awarded.",
                "Assess qualification burden for a typical software SME; no company-specific capability profile is available.",
                "Keep findings concise and decision-oriented for a CEO and bid manager.",
            ],
            "deterministic_facts": {
                "procurement_access": access.model_dump(mode="json"),
                "continuity": continuity.model_dump(mode="json"),
                "budget": budget.model_dump(mode="json"),
                "history_12_months": [item.model_dump(mode="json") for item in history],
                "rules_version": PROCUREMENT_RULES_VERSION,
            },
            "source_metadata": details.model_dump(mode="json", exclude={"raw", "documents"}),
            "evidence": evidence_payload,
            "score_weights": {key: maximum for key, _, maximum in DIMENSIONS},
        }
        payload = {
            "model": self.settings.openai_model,
            "input": json.dumps(prompt, ensure_ascii=False),
            "temperature": 0.1,
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "bid_decision_brief_v2",
                    "strict": True,
                    "schema": _structured_output_schema(),
                }
            },
        }
        headers = {"Authorization": f"Bearer {self.settings.openai_api_key}", "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=90) as client:
            response = await client.post("https://api.openai.com/v1/responses", json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

        output_text = _extract_output_text(data)
        if not output_text:
            raise ValueError("OpenAI returned no structured output")
        parsed = json.loads(output_text)
        if not isinstance(parsed, dict):
            raise ValueError("OpenAI output was not an object")
        return _build_brief(details, parsed, access, continuity, budget, history, evidence, self.settings.openai_model)

    def _get_row(self, source: SourceName, reference: str) -> sqlite3.Row | None:
        with closing(self._connect()) as connection:
            return connection.execute(
                "SELECT source, reference, brief_json, created_at, updated_at FROM document_briefs WHERE source = ? AND reference = ?",
                (source, reference),
            ).fetchone()

    def _save_brief(self, brief: DocumentBrief) -> None:
        now = datetime.now(timezone.utc).isoformat()
        payload = json.dumps(brief.model_dump(mode="json"), ensure_ascii=False)
        with closing(self._connect()) as connection:
            with connection:
                connection.execute(
                    """
                    INSERT INTO document_briefs (source, reference, brief_json, schema_version, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(source, reference) DO UPDATE SET
                        brief_json = excluded.brief_json,
                        schema_version = excluded.schema_version,
                        updated_at = excluded.updated_at
                    """,
                    (brief.source, brief.reference, payload, brief.schema_version, now, now),
                )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _init_db(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as connection:
            with connection:
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS document_briefs (
                        source TEXT NOT NULL,
                        reference TEXT NOT NULL,
                        brief_json TEXT NOT NULL,
                        schema_version INTEGER NOT NULL DEFAULT 1,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        PRIMARY KEY (source, reference)
                    )
                    """
                )
                columns = {row[1] for row in connection.execute("PRAGMA table_info(document_briefs)")}
                if "schema_version" not in columns:
                    connection.execute("ALTER TABLE document_briefs ADD COLUMN schema_version INTEGER NOT NULL DEFAULT 1")


async def _fetch_document_texts(documents: list[DocumentLink], current_reference: str) -> list[dict[str, Any]]:
    ordered = sorted(documents, key=lambda item: _document_priority(item, current_reference))[:MAX_DOCUMENTS]
    results: list[dict[str, Any]] = []
    async with httpx.AsyncClient(timeout=40, follow_redirects=True) as client:
        for document in ordered:
            pages: list[dict[str, Any]] = []
            error: str | None = None
            try:
                response = await client.get(document.url, headers={"Accept": "application/pdf,text/html,text/plain,application/xml,*/*"})
                response.raise_for_status()
                content_type = response.headers.get("content-type", "")
                pages = _extract_document_pages(response.content[:MAX_DOCUMENT_BYTES], content_type, document.url)
            except Exception as exc:
                error = f"Could not read document automatically: {exc.__class__.__name__}"
            results.append(
                {
                    "label": document.label,
                    "type": document.document_type,
                    "reference": document.reference,
                    "url": document.url,
                    "pages": pages,
                    "readable": any(str(page.get("text") or "").strip() for page in pages),
                    "error": error,
                }
            )
    return results


def _document_priority(document: DocumentLink, current_reference: str) -> tuple[int, int]:
    type_order = {"notice": 0, "pdf": 1, "pdfs": 1, "contract": 2, "auction": 3, "request": 4, "payment": 5}
    return (0 if document.reference == current_reference else 1, type_order.get(document.document_type.casefold(), 6))


def _extract_document_pages(content: bytes, content_type: str, url: str) -> list[dict[str, Any]]:
    lower_url = url.casefold()
    lower_type = content_type.casefold()
    if "pdf" in lower_type or lower_url.endswith(".pdf") or "/attachment/" in lower_url:
        return _extract_pdf_pages(content)
    text = content.decode("utf-8", errors="ignore")
    if "html" in lower_type or "<html" in text[:500].casefold():
        text = _strip_html(text)
    else:
        text = _normalize_text(text)
    return [{"page": None, "text": text[:MAX_PAGE_CHARS]}] if text else []


def _extract_pdf_pages(content: bytes) -> list[dict[str, Any]]:
    from pypdf import PdfReader

    try:
        reader = PdfReader(io.BytesIO(content))
        return [
            {"page": index, "text": _normalize_text(page.extract_text() or "")[:MAX_PAGE_CHARS]}
            for index, page in enumerate(reader.pages[:MAX_PDF_PAGES], start=1)
        ]
    except Exception:
        return []


def _build_evidence_catalog(documents: list[dict[str, Any]]) -> list[BriefEvidence]:
    candidates: list[tuple[int, int, BriefEvidence, str]] = []
    for document_index, document in enumerate(documents, start=1):
        for page in document.get("pages") or []:
            text = str(page.get("text") or "").strip()
            for chunk_index, chunk in enumerate(_chunks(text, CHUNK_CHARS), start=1):
                evidence_id = f"d{document_index}-p{page.get('page') or 0}-c{chunk_index}"
                lowered = chunk.casefold()
                relevance = sum(1 for term in RELEVANCE_TERMS if term in lowered)
                if chunk_index == 1:
                    relevance += 2
                item = BriefEvidence(
                    id=evidence_id,
                    document_label=str(document.get("label") or "Source document"),
                    url=str(document.get("url") or ""),
                    excerpt=chunk[:EXCERPT_CHARS],
                    page=page.get("page"),
                    reference=document.get("reference"),
                )
                candidates.append((relevance, len(candidates), item, chunk))

    selected: list[BriefEvidence] = []
    used_chars = 0
    for _, _, item, full_text in sorted(candidates, key=lambda value: (-value[0], value[1])):
        if used_chars + len(full_text) > MAX_MODEL_EVIDENCE_CHARS and selected:
            continue
        item.excerpt = full_text
        selected.append(item)
        used_chars += len(full_text)
        if used_chars >= MAX_MODEL_EVIDENCE_CHARS:
            break
    return sorted(selected, key=lambda item: item.id)


def _analyze_procurement(
    details: OpportunityDetails,
    documents: list[dict[str, Any]],
    evidence: list[BriefEvidence],
) -> tuple[BriefProcurementAccess, BriefContinuityAssessment, BriefBudgetAssessment, list[BriefEvidence]]:
    evidence = list(evidence)
    metadata = details.metadata
    amount_without_vat = _money_value(metadata.get("totalCostWithoutVAT"))
    amount_with_vat = _money_value(metadata.get("totalCostWithVAT"))
    if amount_without_vat is not None:
        eligible = amount_without_vat <= DIRECT_AWARD_THRESHOLD_WITHOUT_VAT
        determination = (
            f"{amount_without_vat:,.2f} € χωρίς ΦΠΑ: επιλέξιμο για απευθείας ανάθεση· αυτό δεν αποδεικνύει ότι έχει ήδη ανατεθεί."
            if eligible
            else f"{amount_without_vat:,.2f} € χωρίς ΦΠΑ: πάνω από το γενικό όριο απευθείας ανάθεσης των 30.000 €."
        )
    else:
        eligible = None
        determination = "Δεν βρέθηκε επιβεβαιωμένο ποσό χωρίς ΦΠΑ· δεν εφαρμόζεται συμπέρασμα για το όριο των 30.000 €."
    budget_evidence_ids: list[str] = []
    if amount_without_vat is not None or amount_with_vat is not None:
        evidence, budget_evidence_id = _append_metadata_evidence(
            details,
            evidence,
            "metadata-budget",
            "Budget metadata",
            " · ".join(
                part for part in (
                    f"Συνολικό κόστος χωρίς ΦΠΑ: {amount_without_vat:,.2f} €" if amount_without_vat is not None else None,
                    f"Συνολικό κόστος με ΦΠΑ: {amount_with_vat:,.2f} €" if amount_with_vat is not None else None,
                ) if part
            ),
        )
        budget_evidence_ids = [budget_evidence_id]
    budget = BriefBudgetAssessment(
        amount_without_vat=amount_without_vat,
        amount_with_vat=amount_with_vat,
        direct_award_eligible=eligible,
        threshold_without_vat=DIRECT_AWARD_THRESHOLD_WITHOUT_VAT,
        determination=determination,
        legal_basis_url=LEGAL_BASIS_URL,
        evidence_ids=budget_evidence_ids,
    )

    deadline = _metadata_deadline(metadata)
    days_remaining = (deadline - date.today()).days if deadline else None
    procedure = first_text(metadata.get("procedureType") or metadata.get("noticeType")) or None
    stage = (details.guidance.current_stage if details.guidance else "").casefold()
    related = details.related_references
    access_status = "unknown"
    access_reason = "Δεν επιβεβαιώθηκε αν η διαδικασία είναι ανοικτή."
    access_evidence: list[str] = []
    if deadline:
        evidence, deadline_evidence_id = _append_metadata_evidence(
            details,
            evidence,
            "metadata-deadline",
            "Deadline metadata",
            f"Προθεσμία υποβολής: {deadline.isoformat()}.",
        )
        access_evidence = [deadline_evidence_id]

    closed_key = next((key for key in ("payments", "contracts", "auctions") if related.get(key)), None)
    if closed_key:
        access_status = {"payments": "paid", "contracts": "contracted", "auctions": "awarded"}[closed_key]
        reference = related[closed_key][0]
        access_reason = f"Το lifecycle περιλαμβάνει {closed_key}: {reference}."
        evidence, evidence_id = _ensure_reference_evidence(evidence, documents, reference, access_reason)
        access_evidence = [evidence_id] if evidence_id else []
    elif stage in {"payment", "contract", "award", "result", "modification"} or any(token in details.reference for token in ("PAY", "SYMV", "AWRD")):
        access_status = "paid" if "PAY" in details.reference or stage == "payment" else "contracted" if "SYMV" in details.reference or stage in {"contract", "modification"} else "awarded"
        access_reason = f"Η τρέχουσα πράξη βρίσκεται στο στάδιο {stage or details.reference}."
        evidence, evidence_id = _ensure_reference_evidence(evidence, documents, details.reference, access_reason)
        access_evidence = [evidence_id] if evidence_id else []
    else:
        named_invitee, named_evidence = _confirmed_named_invitation(evidence)
        if named_invitee:
            access_status = "named_invitation"
            access_reason = f"Η πρόσκληση απευθύνεται στον κατονομαζόμενο οικονομικό φορέα: {named_invitee}."
            access_evidence = [named_evidence] if named_evidence else []
        elif deadline and days_remaining is not None and days_remaining < 0:
            access_status = "expired"
            access_reason = f"Η προθεσμία έληξε στις {deadline.isoformat()}."
        elif stage in {"request", "approved_request", "planning"} and not related.get("notices"):
            access_status = "planning_only"
            access_reason = "Υπάρχει μόνο αίτημα/προγραμματισμός και όχι πρόσκληση ή διακήρυξη."
        elif (details.guidance and details.guidance.is_actionable) or stage in {"notice", "competition"} or related.get("notices"):
            access_status = "open_competition"
            access_reason = "Υπάρχει στάδιο πρόσκλησης/διαγωνισμού χωρίς επιβεβαιωμένη κατονομαζόμενη ανάθεση."
            if not access_evidence and evidence:
                access_evidence = [evidence[0].id]

    continuity_evidence = _find_evidence_with_terms(evidence, CONTINUITY_TERMS)
    if continuity_evidence:
        continuity = BriefContinuityAssessment(
            status="confirmed_continuation",
            reason="Το έγγραφο αναφέρει ρητά συνέχεια, συντήρηση, επέκταση ή αναβάθμιση υφιστάμενου έργου/συστήματος.",
            prior_reference=_extract_procurement_reference(continuity_evidence.excerpt),
            evidence_ids=[continuity_evidence.id],
        )
    elif any(document.get("readable") for document in documents):
        continuity = BriefContinuityAssessment(
            status="not_confirmed",
            reason="Δεν εντοπίστηκε ρητή τεκμηρίωση συνέχειας ή προηγούμενης σύμβασης στα αναγνώσιμα αποσπάσματα.",
        )
    else:
        continuity = BriefContinuityAssessment(status="unknown", reason="Τα έγγραφα δεν ήταν αναγνώσιμα.")

    access = BriefProcurementAccess(
        status=access_status,
        reason=access_reason,
        procedure=procedure,
        deadline=deadline,
        days_remaining=days_remaining,
        named_invitee=named_invitee if access_status == "named_invitation" else None,
        evidence_ids=access_evidence,
    )
    return access, continuity, budget, evidence


def _build_brief(
    details: OpportunityDetails,
    parsed: dict[str, Any],
    access: BriefProcurementAccess,
    continuity: BriefContinuityAssessment,
    budget: BriefBudgetAssessment,
    history: list[BriefHistoryItem],
    evidence: list[BriefEvidence],
    model: str,
) -> DocumentBrief:
    evidence_map = {item.id: item for item in evidence}
    access, continuity = _apply_confirmed_ai_facts(parsed, access, continuity, evidence_map)
    deadline_ids = _valid_evidence_ids(parsed.get("deadline_evidence_ids"), evidence_map)
    deadline = parse_date(parsed.get("deadline_iso")) if deadline_ids else None
    if not access.deadline and deadline:
        access.deadline = deadline
        access.days_remaining = (deadline - date.today()).days
        access.evidence_ids = list(dict.fromkeys([*access.evidence_ids, *deadline_ids]))
    submission_ids = _valid_evidence_ids(parsed.get("submission_method_evidence_ids"), evidence_map)
    access.submission_method = _as_text(parsed.get("submission_method"), "Unknown") if submission_ids else "Unknown"
    access.evidence_ids = list(dict.fromkeys([*access.evidence_ids, *submission_ids]))

    dimensions: list[BriefScoreDimension] = []
    raw_dimensions = parsed.get("score_dimensions") if isinstance(parsed.get("score_dimensions"), dict) else {}
    for key, label, maximum in DIMENSIONS:
        raw = raw_dimensions.get(key) if isinstance(raw_dimensions.get(key), dict) else {}
        ids = _valid_evidence_ids(raw.get("evidence_ids"), evidence_map)
        score = _bounded_int(raw.get("score"), 0, maximum) if ids else 0
        dimensions.append(
            BriefScoreDimension(
                key=key,
                label=label,
                score=score,
                max_score=maximum,
                reason=_as_text(raw.get("reason"), "Unknown") if ids else "Δεν βρέθηκε τεκμηρίωση για ασφαλή βαθμολόγηση.",
                evidence_ids=ids,
            )
        )
    score = sum(item.score for item in dimensions)
    verdict = _decide_verdict(access, continuity, score)
    confidence = _as_confidence(parsed.get("confidence"))
    if verdict == "INSUFFICIENT DATA":
        confidence = "low"
    recommendation = _recommendation(verdict, access, continuity)

    decision_reasons = _findings(parsed.get("decision_reasons"), evidence_map)[:3]
    if not decision_reasons:
        decision_reasons = [BriefFinding(text=access.reason, evidence_ids=access.evidence_ids)]

    technical = _findings(parsed.get("technical_findings"), evidence_map)
    red_flags = _findings(parsed.get("red_flags"), evidence_map)
    next_steps = _plain_list(parsed.get("next_steps"))
    unknowns = _plain_list(parsed.get("unknowns"))
    if access.deadline is None and access.status in {"open_competition", "unknown"}:
        unknowns = ["Δεν επιβεβαιώθηκε προθεσμία υποβολής.", *unknowns]

    return DocumentBrief(
        source=details.source,
        reference=details.reference,
        schema_version=BRIEF_SCHEMA_VERSION,
        rules_version=PROCUREMENT_RULES_VERSION,
        verdict=verdict,
        score=score,
        confidence=confidence,
        executive_recommendation=recommendation,
        decision_reasons=decision_reasons,
        project_summary=_as_text(parsed.get("project_summary"), details.summary or details.title or "Unknown"),
        actionable="yes" if verdict == "GO" else "maybe" if verdict == "CONDITIONAL GO" else "no" if verdict == "NO-GO" else "unknown",
        procurement_access=access,
        continuity=continuity,
        budget_assessment=budget,
        score_dimensions=dimensions,
        deadline_submission=access.deadline.isoformat() if access.deadline else "Unknown",
        required_documents=[item.text for item in _findings(parsed.get("required_documents"), evidence_map)],
        eligibility_requirements=_findings(parsed.get("eligibility_requirements"), evidence_map),
        evaluation_criteria=_findings(parsed.get("evaluation_criteria"), evidence_map),
        technical_requirements=[item.text for item in technical],
        technical_findings=technical,
        commercial_findings=_findings(parsed.get("commercial_findings"), evidence_map),
        contractual_findings=_findings(parsed.get("contractual_findings"), evidence_map),
        red_flags=[item.text for item in red_flags],
        red_flag_findings=red_flags,
        unknowns=unknowns,
        recommendation=recommendation,
        next_steps=next_steps,
        history_12_months=history,
        evidence=[_excerpted(item) for item in evidence],
        source_documents=details.documents[:MAX_DOCUMENTS],
        generated_at=datetime.now(timezone.utc),
        model=model,
        cached=False,
    )


def _fallback_brief(
    details: OpportunityDetails,
    access: BriefProcurementAccess,
    continuity: BriefContinuityAssessment,
    budget: BriefBudgetAssessment,
    history: list[BriefHistoryItem],
    evidence: list[BriefEvidence],
    reason: str,
) -> DocumentBrief:
    forced_verdict = _decide_verdict(access, continuity, 0)
    verdict = forced_verdict if forced_verdict == "NO-GO" else "INSUFFICIENT DATA"
    return DocumentBrief(
        source=details.source,
        reference=details.reference,
        schema_version=BRIEF_SCHEMA_VERSION,
        rules_version=PROCUREMENT_RULES_VERSION,
        verdict=verdict,
        score=0,
        confidence="low",
        executive_recommendation=_recommendation(verdict, access, continuity),
        decision_reasons=[BriefFinding(text=access.reason, evidence_ids=access.evidence_ids)],
        project_summary=details.summary or details.title or "Δεν υπάρχουν αρκετά αναγνώσιμα στοιχεία.",
        actionable="no" if verdict == "NO-GO" else "unknown",
        procurement_access=access,
        continuity=continuity,
        budget_assessment=budget,
        score_dimensions=[BriefScoreDimension(key=key, label=label, max_score=maximum) for key, label, maximum in DIMENSIONS],
        red_flags=[reason],
        red_flag_findings=[BriefFinding(text=reason)],
        unknowns=["Απαιτείται χειροκίνητος έλεγχος των επίσημων εγγράφων."],
        recommendation=_recommendation(verdict, access, continuity),
        next_steps=["Ανοίξτε τα επίσημα έγγραφα και επιβεβαιώστε πρόσβαση, προθεσμία και βασικούς όρους."],
        history_12_months=history,
        evidence=[_excerpted(item) for item in evidence],
        source_documents=details.documents[:MAX_DOCUMENTS],
        generated_at=datetime.now(timezone.utc),
        model=None,
        cached=False,
    )


def _decide_verdict(access: BriefProcurementAccess, continuity: BriefContinuityAssessment, score: int) -> str:
    if access.status in {"named_invitation", "awarded", "contracted", "paid", "expired"}:
        return "NO-GO"
    if access.status in {"planning_only", "unknown"} or (access.status == "open_competition" and access.deadline is None):
        return "INSUFFICIENT DATA"
    if score < 50:
        return "NO-GO"
    if continuity.status == "confirmed_continuation" or score < 75:
        return "CONDITIONAL GO"
    return "GO"


def _recommendation(verdict: str, access: BriefProcurementAccess, continuity: BriefContinuityAssessment) -> str:
    if access.status == "named_invitation":
        return "NO-GO: η πρόσκληση απευθύνεται σε κατονομαζόμενο οικονομικό φορέα."
    if access.status in {"awarded", "contracted", "paid"}:
        return "NO-GO: η διαδικασία έχει περάσει σε ανάθεση ή εκτέλεση."
    if access.status == "expired":
        return "NO-GO: η προθεσμία έχει λήξει."
    if verdict == "INSUFFICIENT DATA":
        return "Ανεπαρκή στοιχεία: επιβεβαιώστε διακήρυξη, προθεσμία και βασικούς όρους πριν από απόφαση."
    if continuity.status == "confirmed_continuation":
        return "CONDITIONAL GO: υπάρχει τεκμηριωμένη συνέχεια υφιστάμενου έργου και πιθανό incumbent advantage."
    return f"{verdict}: αξιολογήστε τα τεκμηριωμένα κριτήρια του scorecard πριν δεσμεύσετε bid resources."


async def _fetch_12_month_history(details: OpportunityDetails, settings: Settings) -> list[BriefHistoryItem]:
    if details.source != "khmdhs":
        return []
    raw_metadata = details.raw.get("metadata") if isinstance(details.raw.get("metadata"), dict) else {}
    organization = raw_metadata.get("organization")
    organization_key = first_text(organization.get("key") or organization.get("id")) if isinstance(organization, dict) else ""
    if not organization_key or not raw_metadata:
        return []
    try:
        current = KhmdhsClient(settings)._to_opportunity(raw_metadata)
        service = BuyerIntelligenceService(settings)
        history = await service._khmdhs_history(organization_key, 365, 40)
        similar = _similar_opportunities([current, *history], current)[:6]
        awards = await service._khmdhs_awards(organization_key, 365, 12)
        items = [
            BriefHistoryItem(
                title=item.title,
                reference=item.source_reference,
                amount=item.budget,
                published_at=item.published_at,
                url=item.url,
            )
            for item in similar
        ]
        items.extend(
            BriefHistoryItem(
                title=award.subject,
                reference=award.ada,
                amount=award.amount,
                published_at=award.published_at,
                supplier=award.winner_name,
                url=award.document_url or award.url,
            )
            for award in awards
            if award.similar_to_software
        )
        return items[:8]
    except Exception:
        return []


def _apply_confirmed_ai_facts(
    parsed: dict[str, Any],
    access: BriefProcurementAccess,
    continuity: BriefContinuityAssessment,
    evidence_map: dict[str, BriefEvidence],
) -> tuple[BriefProcurementAccess, BriefContinuityAssessment]:
    invitee = _as_text(parsed.get("named_invitee"), "")
    invite_ids = _valid_evidence_ids(parsed.get("named_invitation_evidence_ids"), evidence_map)
    if invitee and not _is_generic_invitee(invitee) and invite_ids and any(_contains_term(evidence_map[item].excerpt, NAMED_INVITATION_TERMS) for item in invite_ids):
        access.status = "named_invitation"
        access.named_invitee = invitee
        access.reason = f"Η πρόσκληση απευθύνεται στον κατονομαζόμενο οικονομικό φορέα: {invitee}."
        access.evidence_ids = invite_ids

    continuity_ids = _valid_evidence_ids(parsed.get("continuity_evidence_ids"), evidence_map)
    if parsed.get("continuity_status") == "confirmed_continuation" and continuity_ids and any(
        _contains_term(evidence_map[item].excerpt, CONTINUITY_TERMS) for item in continuity_ids
    ):
        continuity.status = "confirmed_continuation"
        continuity.reason = _as_text(parsed.get("continuity_reason"), continuity.reason)
        continuity.incumbent_name = _as_text(parsed.get("incumbent_name"), "") or None
        continuity.prior_reference = _as_text(parsed.get("prior_reference"), "") or continuity.prior_reference
        continuity.evidence_ids = continuity_ids
    return access, continuity


def _confirmed_named_invitation(evidence: list[BriefEvidence]) -> tuple[str | None, str | None]:
    for item in evidence:
        text = item.excerpt
        if not _contains_term(text, NAMED_INVITATION_TERMS):
            continue
        patterns = (
            r"(?:πρόσκληση υποβολής προσφοράς προς|προς τον οικονομικό φορέα|καλεί την εταιρεία)\s*[:\-]?\s*[«\"]?(.{3,140}?)(?=[»\"]?[\.,;]|\s+(?:για|με θέμα|προκειμένου))",
            r"(?:invitation to submit an offer to|invites the economic operator)\s*[:\-]?\s*[\"]?(.{3,140}?)(?=[\"\.,;]|\s+(?:for|regarding|to provide))",
        )
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                invitee = _normalize_text(match.group(1)).strip(" :-–—\"'«»")
                if len(invitee) >= 3 and not _is_generic_invitee(invitee):
                    return invitee, item.id
    return None, None


def _is_generic_invitee(value: str) -> bool:
    lowered = value.casefold()
    generic_terms = (
        "κάθε ενδιαφερόμεν", "όλους τους ενδιαφερόμεν", "κάθε οικονομικό φορέα",
        "all interested", "any interested", "all economic operators",
    )
    return any(term.casefold() in lowered for term in generic_terms)


def _ensure_reference_evidence(
    evidence: list[BriefEvidence], documents: list[dict[str, Any]], reference: str, reason: str
) -> tuple[list[BriefEvidence], str | None]:
    existing = next((item for item in evidence if item.reference == reference), None)
    if existing:
        return evidence, existing.id
    document = next((item for item in documents if item.get("reference") == reference), None)
    if not document:
        return evidence, None
    item = BriefEvidence(
        id=f"lifecycle-{len(evidence) + 1}",
        document_label=str(document.get("label") or "Lifecycle record"),
        url=str(document.get("url") or ""),
        excerpt=reason,
        reference=reference,
    )
    return [*evidence, item], item.id


def _append_metadata_evidence(
    details: OpportunityDetails,
    evidence: list[BriefEvidence],
    evidence_id: str,
    label: str,
    excerpt: str,
) -> tuple[list[BriefEvidence], str]:
    existing = next((item for item in evidence if item.id == evidence_id), None)
    if existing:
        return evidence, existing.id
    fallback_url = next((document.url for document in details.documents if document.url), None)
    item = BriefEvidence(
        id=evidence_id,
        document_label=label,
        url=details.platform_url or fallback_url or LEGAL_BASIS_URL,
        excerpt=excerpt,
        reference=details.reference,
    )
    return [*evidence, item], item.id


def _find_evidence_with_terms(evidence: list[BriefEvidence], terms: tuple[str, ...]) -> BriefEvidence | None:
    return next((item for item in evidence if _contains_term(item.excerpt, terms)), None)


def _contains_term(text: str, terms: tuple[str, ...]) -> bool:
    lowered = text.casefold()
    return any(term.casefold() in lowered for term in terms)


def _extract_procurement_reference(text: str) -> str | None:
    match = re.search(r"\b\d{2}(?:REQ|PROC|AWRD|SYMV|PAY)\d{6,}\b", text, flags=re.IGNORECASE)
    return match.group(0).upper() if match else None


def _metadata_deadline(metadata: dict[str, Any]) -> date | None:
    for key in ("deadline", "submissionDeadline", "deadlineSubmission"):
        parsed = parse_date(metadata.get(key))
        if parsed:
            return parsed
    return None


def _money_value(value: Any) -> float | None:
    if isinstance(value, dict):
        value = value.get("amount") or value.get("value")
    if isinstance(value, (int, float)):
        return float(value)
    if not isinstance(value, str) or not value.strip():
        return None
    cleaned = re.sub(r"[^0-9,.-]", "", value)
    if "," in cleaned and "." in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    elif "," in cleaned:
        cleaned = cleaned.replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def _findings(value: Any, evidence_map: dict[str, BriefEvidence]) -> list[BriefFinding]:
    if not isinstance(value, list):
        return []
    output: list[BriefFinding] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        text = _as_text(item.get("text"), "")
        ids = _valid_evidence_ids(item.get("evidence_ids"), evidence_map)
        if text and ids:
            output.append(BriefFinding(text=text, evidence_ids=ids))
    return output


def _valid_evidence_ids(value: Any, evidence_map: dict[str, BriefEvidence]) -> list[str]:
    if not isinstance(value, list):
        return []
    return list(dict.fromkeys(str(item) for item in value if str(item) in evidence_map))


def _plain_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _bounded_int(value: Any, low: int, high: int) -> int:
    try:
        return max(low, min(high, int(value)))
    except (TypeError, ValueError):
        return low


def _as_text(value: Any, fallback: str) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return fallback


def _as_confidence(value: Any) -> str:
    normalized = str(value or "").casefold()
    return normalized if normalized in {"high", "medium", "low"} else "low"


def _excerpted(evidence: BriefEvidence) -> BriefEvidence:
    return evidence.model_copy(update={"excerpt": evidence.excerpt[:EXCERPT_CHARS]})


def _chunks(text: str, size: int) -> list[str]:
    return [text[index:index + size].strip() for index in range(0, len(text), size) if text[index:index + size].strip()]


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


class _HTMLTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        if data.strip():
            self.parts.append(data.strip())


def _strip_html(text: str) -> str:
    parser = _HTMLTextExtractor()
    parser.feed(text)
    return _normalize_text(" ".join(parser.parts))


def _extract_output_text(payload: dict[str, Any]) -> str | None:
    if isinstance(payload.get("output_text"), str):
        return payload["output_text"].strip()
    for output in payload.get("output") or []:
        for content in output.get("content") or []:
            text = content.get("text")
            if isinstance(text, str) and text.strip():
                return text.strip()
    return None


def _row_to_brief(row: sqlite3.Row) -> DocumentBrief:
    return DocumentBrief.model_validate(json.loads(str(row["brief_json"])))


def _structured_output_schema() -> dict[str, Any]:
    finding = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "text": {"type": "string"},
            "evidence_ids": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["text", "evidence_ids"],
    }
    dimension = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "score": {"type": "integer"},
            "reason": {"type": "string"},
            "evidence_ids": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["score", "reason", "evidence_ids"],
    }
    properties: dict[str, Any] = {
        "project_summary": {"type": "string"},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
        "deadline_iso": {"type": ["string", "null"]},
        "deadline_evidence_ids": {"type": "array", "items": {"type": "string"}},
        "submission_method": {"type": "string"},
        "submission_method_evidence_ids": {"type": "array", "items": {"type": "string"}},
        "named_invitee": {"type": ["string", "null"]},
        "named_invitation_evidence_ids": {"type": "array", "items": {"type": "string"}},
        "continuity_status": {"type": "string", "enum": ["confirmed_continuation", "not_confirmed", "unknown"]},
        "continuity_reason": {"type": "string"},
        "incumbent_name": {"type": ["string", "null"]},
        "prior_reference": {"type": ["string", "null"]},
        "continuity_evidence_ids": {"type": "array", "items": {"type": "string"}},
        "score_dimensions": {
            "type": "object",
            "additionalProperties": False,
            "properties": {key: dimension for key, _, _ in DIMENSIONS},
            "required": [key for key, _, _ in DIMENSIONS],
        },
        "decision_reasons": {"type": "array", "items": finding},
        "required_documents": {"type": "array", "items": finding},
        "eligibility_requirements": {"type": "array", "items": finding},
        "evaluation_criteria": {"type": "array", "items": finding},
        "technical_findings": {"type": "array", "items": finding},
        "commercial_findings": {"type": "array", "items": finding},
        "contractual_findings": {"type": "array", "items": finding},
        "red_flags": {"type": "array", "items": finding},
        "unknowns": {"type": "array", "items": {"type": "string"}},
        "next_steps": {"type": "array", "items": {"type": "string"}},
    }
    return {"type": "object", "additionalProperties": False, "properties": properties, "required": list(properties)}
