from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from app.ai_models import model_request_options, resolve_ai_model
from app.config import Settings
from app.models import (
    BriefEvidence,
    Opportunity,
    SoftwareScreeningResponse,
    SoftwareScreeningResult,
    SoftwareScreeningRun,
)
from app.services.bookmarks import _resolve_db_path
from app.services.briefs import OpportunityAIContextService, _extract_output_text
from app.services.chat import select_relevant_evidence
from app.services.software_matching import (
    MATCH_THRESHOLD,
    REVIEW_THRESHOLD,
    SERVICE_SIGNALS,
    SemanticMatchHints,
    SoftwareMatchingService,
    _contains_term,
    _normalize,
)


PROMPT_VERSION = "software-screening-v1"
TITLE_BATCH_SIZE = 40
SUMMARY_BATCH_SIZE = 25
MAX_SUMMARY_CHARS = 1_600
MAX_RAW_TEXT_CHARS = 900
MAX_DOCUMENT_EVIDENCE = 6
MAX_DOCUMENT_CHARS = 8_000

CLASSIFICATIONS = (
    "not_software",
    "software_no_catalog_fit",
    "likely_match",
    "needs_more_context",
)

OBVIOUS_NON_SOFTWARE_TERMS = (
    "toner",
    "printer supplies",
    "office furniture",
    "medical supplies",
    "pharmaceutical products",
    "food supplies",
    "vehicle fuel",
    "καύσιμα",
    "τρόφιμα",
    "φάρμακα",
    "φαρμακευτικά προϊόντα",
    "αναλώσιμα εκτυπωτών",
    "έπιπλα γραφείου",
    "υλικά καθαριότητας",
)

SOFTWARE_GUARD_TERMS = (
    "software",
    "λογισμικό",
    "application",
    "εφαρμογή",
    "platform",
    "πλατφόρμα",
    "system",
    "σύστημα",
    "integration",
    "διασύνδεση",
    "digital",
    "ψηφιακ",
    "database",
    "βάση δεδομένων",
    "cloud",
    "cyber",
    "api",
)


class SoftwareScreeningUnavailable(RuntimeError):
    pass


class SoftwareScreeningError(RuntimeError):
    pass


@dataclass
class _Usage:
    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    document_escalations: int = 0

    def add(self, usage: "_Usage") -> None:
        self.calls += usage.calls
        self.input_tokens += usage.input_tokens
        self.output_tokens += usage.output_tokens
        self.document_escalations += usage.document_escalations


@dataclass(frozen=True)
class _Decision:
    opportunity_id: str
    classification: str
    category_ids: tuple[str, ...]
    capability_terms: tuple[str, ...]
    service_types: tuple[str, ...]
    confidence: str
    reason: str
    evidence_ids: tuple[str, ...] = ()


class SoftwareScreeningService:
    """Persisted, cost-controlled semantic screening over a bounded product taxonomy."""

    def __init__(
        self,
        settings: Settings,
        matcher: SoftwareMatchingService | None = None,
        context_service: OpportunityAIContextService | None = None,
    ):
        self.settings = settings
        self.matcher = matcher or SoftwareMatchingService()
        self.context_service = context_service or OpportunityAIContextService(settings)
        self.db_path = _resolve_db_path(Path(settings.bookmark_db_path))
        self.category_ids = {item.id for item in self.matcher.catalog.categories}
        self.service_types = set(SERVICE_SIGNALS)
        self.screening_model = resolve_ai_model(settings, settings.software_screening_model)
        self.deep_model = resolve_ai_model(settings, settings.software_screening_deep_model)
        self._init_db()

    async def scan(
        self,
        opportunities: list[Opportunity],
        *,
        force: bool = False,
        max_document_escalations: int = 5,
    ) -> SoftwareScreeningResponse:
        if not self.settings.openai_api_key:
            raise SoftwareScreeningUnavailable("OPENAI_API_KEY is not configured")

        unique = _dedupe_opportunities(opportunities)
        results: dict[str, SoftwareScreeningResult] = {}
        pending: list[Opportunity] = []
        cached_count = 0
        usage = _Usage()

        for opportunity in unique:
            cached = None if force else self._cached(opportunity, include_errors=False)
            if cached:
                results[opportunity.id] = cached.model_copy(update={"cached": True})
                cached_count += 1
                continue

            deterministic_matches = self.matcher.match(opportunity)
            if deterministic_matches:
                result = self._result(
                    opportunity,
                    status="catalog_match",
                    stage="deterministic",
                    reason="The local catalog scorer found sufficient capability and/or CPV evidence; no AI call was needed.",
                    matches=deterministic_matches,
                )
                self._save(opportunity, result)
                results[opportunity.id] = result
                continue

            local_reason = _obvious_non_software_reason(opportunity)
            if local_reason:
                result = self._result(
                    opportunity,
                    status="no_match",
                    stage="deterministic",
                    reason=local_reason,
                    matches=[],
                )
                self._save(opportunity, result)
                results[opportunity.id] = result
                continue
            pending.append(opportunity)

        title_decisions, title_usage, title_errors = await self._screen_batches(pending, "title", self.screening_model, TITLE_BATCH_SIZE)
        usage.add(title_usage)
        summary_pending: list[Opportunity] = []
        decision_by_id: dict[str, _Decision] = {}

        for opportunity in pending:
            decision = title_decisions.get(opportunity.id)
            if not decision:
                result = self._error_result(opportunity, "title", title_errors.get(opportunity.id) or "The title screening returned no decision.")
                self._save(opportunity, result)
                results[opportunity.id] = result
                continue
            decision_by_id[opportunity.id] = decision
            result, should_escalate = self._evaluate(opportunity, decision, "title")
            if should_escalate:
                summary_pending.append(opportunity)
            elif result:
                self._save(opportunity, result)
                results[opportunity.id] = result

        summary_decisions, summary_usage, summary_errors = await self._screen_batches(
            summary_pending,
            "summary",
            self.screening_model,
            SUMMARY_BATCH_SIZE,
        )
        usage.add(summary_usage)
        document_pending: list[tuple[Opportunity, _Decision]] = []

        for opportunity in summary_pending:
            decision = summary_decisions.get(opportunity.id)
            if not decision:
                result = self._error_result(opportunity, "summary", summary_errors.get(opportunity.id) or "The summary screening returned no decision.")
                self._save(opportunity, result)
                results[opportunity.id] = result
                continue
            decision_by_id[opportunity.id] = decision
            result, should_escalate = self._evaluate(opportunity, decision, "summary")
            if should_escalate and len(document_pending) < max_document_escalations and opportunity.source_reference:
                document_pending.append((opportunity, decision))
            elif should_escalate:
                result = self._review_result(
                    opportunity,
                    decision,
                    "summary",
                    "The title and summary suggest possible catalog relevance, but stronger evidence is required.",
                )
            if result:
                self._save(opportunity, result)
                results[opportunity.id] = result

        for opportunity, previous_decision in document_pending:
            usage.document_escalations += 1
            evidence = await self._evidence(opportunity, previous_decision)
            if not evidence:
                result = self._review_result(
                    opportunity,
                    previous_decision,
                    "documents",
                    "Document escalation was attempted, but no readable relevant excerpt was available.",
                )
            else:
                try:
                    parsed, call_usage = await self._call_openai([opportunity], "documents", self.deep_model, {opportunity.id: evidence})
                    usage.add(call_usage)
                    decisions = self._parse_decisions(parsed, [opportunity], {opportunity.id: evidence})
                    decision = decisions.get(opportunity.id)
                    if not decision:
                        raise ValueError("Document screening returned no decision")
                    result, _ = self._evaluate(opportunity, decision, "documents")
                    if result is None:
                        result = self._review_result(opportunity, decision, "documents", decision.reason)
                except (httpx.HTTPError, json.JSONDecodeError, ValueError, TypeError) as exc:
                    result = self._error_result(opportunity, "documents", f"Document screening failed safely: {exc.__class__.__name__}")
            self._save(opportunity, result)
            results[opportunity.id] = result

        ordered_results = [results[item.id] for item in unique if item.id in results]
        enriched = [self._apply_result(item, results.get(item.id)) for item in unique]
        counts = {status: sum(result.status == status for result in ordered_results) for status in ("catalog_match", "needs_review", "no_match", "error")}
        return SoftwareScreeningResponse(
            opportunities=enriched,
            results=ordered_results,
            run=SoftwareScreeningRun(
                total=len(unique),
                catalog_matches=counts["catalog_match"],
                needs_review=counts["needs_review"],
                no_matches=counts["no_match"],
                errors=counts["error"],
                cached=cached_count,
                ai_calls=usage.calls,
                document_escalations=usage.document_escalations,
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
            ),
            catalog_version=self.matcher.catalog_version,
            prompt_version=PROMPT_VERSION,
            screening_model=self.screening_model,
            deep_model=self.deep_model,
        )

    def apply_saved(self, opportunities: list[Opportunity]) -> list[Opportunity]:
        return [self._apply_result(item, self._cached(item)) for item in opportunities]

    async def _screen_batches(
        self,
        opportunities: list[Opportunity],
        stage: str,
        model: str,
        batch_size: int,
    ) -> tuple[dict[str, _Decision], _Usage, dict[str, str]]:
        decisions: dict[str, _Decision] = {}
        errors: dict[str, str] = {}
        usage = _Usage()
        for start in range(0, len(opportunities), batch_size):
            batch = opportunities[start:start + batch_size]
            try:
                parsed, batch_usage = await self._call_openai(batch, stage, model)
                usage.add(batch_usage)
                decisions.update(self._parse_decisions(parsed, batch))
            except (httpx.HTTPError, json.JSONDecodeError, ValueError, TypeError) as exc:
                message = f"AI {stage} screening failed safely: {exc.__class__.__name__}"
                errors.update({item.id: message for item in batch})
        return decisions, usage, errors

    async def _call_openai(
        self,
        opportunities: list[Opportunity],
        stage: str,
        model: str,
        evidence_by_id: dict[str, list[BriefEvidence]] | None = None,
    ) -> tuple[dict[str, Any], _Usage]:
        static_prompt = {
            "role": "You classify procurement opportunities against a bounded open-source software taxonomy.",
            "goal": "Identify semantic software/category fit without selecting product names or slugs.",
            "rules": [
                "Return one result for every supplied opportunity_id.",
                "Use only category_ids and service_types supplied in this prompt.",
                "Do not select, mention, or invent product slugs.",
                "not_software means the procurement is primarily goods, construction, non-digital services, or unrelated hardware.",
                "software_no_catalog_fit means software is involved but none of the supplied categories fits.",
                "likely_match requires a concrete capability-to-category relationship.",
                "needs_more_context is preferred over guessing when the available stage lacks enough evidence.",
                "Evidence IDs must come only from the opportunity's supplied evidence.",
                "Keep reasons concise and in Greek.",
            ],
            "stage": stage,
            "categories": [
                {
                    "id": item.id,
                    "name": item.name,
                    "description": item.description,
                }
                for item in self.matcher.catalog.categories
            ],
            "service_types": sorted(self.service_types),
        }
        dynamic_prompt = {
            "opportunities": [self._stage_payload(item, stage, (evidence_by_id or {}).get(item.id, [])) for item in opportunities]
        }
        payload = {
            "model": model,
            "input": [
                {"role": "system", "content": json.dumps(static_prompt, ensure_ascii=False)},
                {"role": "user", "content": json.dumps(dynamic_prompt, ensure_ascii=False)},
            ],
            "store": False,
            **model_request_options(model, temperature=0.0),
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": f"software_screening_{stage}_v1",
                    "strict": True,
                    "schema": self._structured_output_schema(opportunities, evidence_by_id or {}),
                }
            },
        }
        headers = {
            "Authorization": f"Bearer {self.settings.openai_api_key}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post("https://api.openai.com/v1/responses", json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
        output = _extract_output_text(data)
        if not output:
            raise ValueError("OpenAI returned no structured screening output")
        parsed = json.loads(output)
        if not isinstance(parsed, dict):
            raise ValueError("OpenAI screening output was not an object")
        raw_usage = data.get("usage") if isinstance(data.get("usage"), dict) else {}
        return parsed, _Usage(
            calls=1,
            input_tokens=int(raw_usage.get("input_tokens") or 0),
            output_tokens=int(raw_usage.get("output_tokens") or 0),
        )

    def _stage_payload(self, opportunity: Opportunity, stage: str, evidence: list[BriefEvidence]) -> dict[str, Any]:
        base: dict[str, Any] = {
            "opportunity_id": opportunity.id,
            "title": opportunity.title,
            "allowed_evidence_ids": ["title"],
        }
        if stage in {"summary", "documents"}:
            base.update({
                "summary": opportunity.summary[:MAX_SUMMARY_CHARS],
                "raw_text_excerpt": opportunity.raw_text[:MAX_RAW_TEXT_CHARS],
                "buyer": opportunity.buyer,
                "procedure_type": opportunity.procedure_type,
                "notice_type": opportunity.notice_type,
                "cpv_codes": opportunity.cpv_codes,
                "matched_keywords": opportunity.matched_keywords,
                "allowed_evidence_ids": ["title", "summary", "cpv", "metadata"],
            })
        if stage == "documents":
            base["evidence"] = [item.model_dump(mode="json") for item in evidence]
            base["allowed_evidence_ids"] = [item.id for item in evidence]
        return base

    def _structured_output_schema(
        self,
        opportunities: list[Opportunity],
        evidence_by_id: dict[str, list[BriefEvidence]],
    ) -> dict[str, Any]:
        opportunity_ids = [item.id for item in opportunities]
        evidence_ids = sorted({evidence.id for items in evidence_by_id.values() for evidence in items})
        if not evidence_ids:
            evidence_ids = ["title", "summary", "cpv", "metadata"]
        return {
            "type": "object",
            "additionalProperties": False,
            "required": ["results"],
            "properties": {
                "results": {
                    "type": "array",
                    "minItems": len(opportunities),
                    "maxItems": len(opportunities),
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": [
                            "opportunity_id",
                            "classification",
                            "category_ids",
                            "capability_terms",
                            "service_types",
                            "confidence",
                            "reason",
                            "evidence_ids",
                        ],
                        "properties": {
                            "opportunity_id": {"type": "string", "enum": opportunity_ids},
                            "classification": {"type": "string", "enum": list(CLASSIFICATIONS)},
                            "category_ids": {
                                "type": "array",
                                "maxItems": 4,
                                "items": {"type": "string", "enum": sorted(self.category_ids)},
                            },
                            "capability_terms": {"type": "array", "maxItems": 6, "items": {"type": "string"}},
                            "service_types": {
                                "type": "array",
                                "maxItems": 5,
                                "items": {"type": "string", "enum": sorted(self.service_types)},
                            },
                            "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
                            "reason": {"type": "string"},
                            "evidence_ids": {
                                "type": "array",
                                "maxItems": 6,
                                "items": {"type": "string", "enum": evidence_ids},
                            },
                        },
                    },
                }
            },
        }

    def _parse_decisions(
        self,
        parsed: dict[str, Any],
        opportunities: list[Opportunity],
        evidence_by_id: dict[str, list[BriefEvidence]] | None = None,
    ) -> dict[str, _Decision]:
        allowed_ids = {item.id for item in opportunities}
        evidence_by_id = evidence_by_id or {}
        output: dict[str, _Decision] = {}
        raw_results = parsed.get("results") if isinstance(parsed.get("results"), list) else []
        for item in raw_results:
            if not isinstance(item, dict):
                continue
            opportunity_id = str(item.get("opportunity_id") or "")
            if opportunity_id not in allowed_ids or opportunity_id in output:
                continue
            classification = str(item.get("classification") or "needs_more_context")
            if classification not in CLASSIFICATIONS:
                classification = "needs_more_context"
            confidence = str(item.get("confidence") or "low")
            if confidence not in {"high", "medium", "low"}:
                confidence = "low"
            category_ids = tuple(dict.fromkeys(str(value) for value in item.get("category_ids", []) if str(value) in self.category_ids))
            service_types = tuple(dict.fromkeys(str(value) for value in item.get("service_types", []) if str(value) in self.service_types))
            allowed_evidence = {evidence.id for evidence in evidence_by_id.get(opportunity_id, [])}
            if not allowed_evidence:
                allowed_evidence = {"title", "summary", "cpv", "metadata"}
            evidence_ids = tuple(dict.fromkeys(str(value) for value in item.get("evidence_ids", []) if str(value) in allowed_evidence))
            output[opportunity_id] = _Decision(
                opportunity_id=opportunity_id,
                classification=classification,
                category_ids=category_ids,
                capability_terms=tuple(str(value).strip() for value in item.get("capability_terms", []) if str(value).strip())[:6],
                service_types=service_types,
                confidence=confidence,
                reason=str(item.get("reason") or "AI semantic screening completed.").strip(),
                evidence_ids=evidence_ids,
            )
        return output

    def _evaluate(
        self,
        opportunity: Opportunity,
        decision: _Decision,
        stage: str,
    ) -> tuple[SoftwareScreeningResult | None, bool]:
        if decision.classification in {"not_software", "software_no_catalog_fit"}:
            if decision.confidence == "high" or stage in {"summary", "documents"}:
                return self._result(
                    opportunity,
                    status="no_match",
                    stage=stage,
                    reason=decision.reason,
                    matches=[],
                    decision=decision,
                ), False
            return None, True

        hints = SemanticMatchHints(
            category_ids=decision.category_ids,
            capability_terms=decision.capability_terms,
            service_types=decision.service_types,
            confidence=decision.confidence,
            reason=decision.reason,
            evidence_ids=decision.evidence_ids,
        )
        candidates = self.matcher.semantic_candidates(opportunity, hints, limit=3, threshold=REVIEW_THRESHOLD)
        confirmed = [item for item in candidates if item.score >= MATCH_THRESHOLD]
        if decision.classification == "likely_match" and confirmed and (decision.confidence == "high" or stage != "title"):
            return self._result(
                opportunity,
                status="catalog_match",
                stage=stage,
                reason=decision.reason,
                matches=confirmed[:3],
                decision=decision,
            ), False
        if stage in {"title", "summary"}:
            return None, True
        if candidates:
            return self._result(
                opportunity,
                status="needs_review",
                stage="documents",
                reason=decision.reason,
                matches=candidates,
                decision=decision,
            ), False
        return self._result(
            opportunity,
            status="no_match" if decision.classification != "needs_more_context" else "needs_review",
            stage="documents",
            reason=decision.reason,
            matches=[],
            decision=decision,
        ), False

    async def _evidence(self, opportunity: Opportunity, decision: _Decision) -> list[BriefEvidence]:
        if opportunity.source == "demo" or not opportunity.source_reference:
            return []
        try:
            context = await self.context_service.prepare(opportunity.source, opportunity.source_reference)
        except Exception:
            return []
        query = " ".join((opportunity.title, opportunity.summary, *decision.category_ids, *decision.capability_terms))
        return select_relevant_evidence(
            context,
            query,
            max_items=MAX_DOCUMENT_EVIDENCE,
            max_chars=MAX_DOCUMENT_CHARS,
        )

    def _review_result(
        self,
        opportunity: Opportunity,
        decision: _Decision,
        stage: str,
        reason: str,
    ) -> SoftwareScreeningResult:
        hints = SemanticMatchHints(
            category_ids=decision.category_ids,
            capability_terms=decision.capability_terms,
            service_types=decision.service_types,
            confidence=decision.confidence,
            reason=decision.reason,
            evidence_ids=decision.evidence_ids,
        )
        candidates = self.matcher.semantic_candidates(opportunity, hints, limit=3, threshold=REVIEW_THRESHOLD)
        return self._result(
            opportunity,
            status="needs_review",
            stage=stage,
            reason=reason,
            matches=candidates,
            decision=decision,
        )

    def _result(
        self,
        opportunity: Opportunity,
        *,
        status: str,
        stage: str,
        reason: str,
        matches: list,
        decision: _Decision | None = None,
    ) -> SoftwareScreeningResult:
        return SoftwareScreeningResult(
            opportunity_id=opportunity.id,
            status=status,
            stage=stage,
            reason=reason,
            matches=matches,
            evidence_ids=list(decision.evidence_ids) if decision else [],
            model=None if stage == "deterministic" else self.screening_model,
            deep_model=self.deep_model if stage == "documents" else None,
            catalog_version=self.matcher.catalog_version,
            prompt_version=PROMPT_VERSION,
            scanned_at=datetime.now(timezone.utc),
            cached=False,
        )

    def _error_result(self, opportunity: Opportunity, stage: str, reason: str) -> SoftwareScreeningResult:
        return self._result(opportunity, status="error", stage=stage, reason=reason, matches=[])

    def _apply_result(self, opportunity: Opportunity, result: SoftwareScreeningResult | None) -> Opportunity:
        if not result:
            return opportunity
        confirmed_matches = result.matches if result.status == "catalog_match" else []
        return opportunity.model_copy(
            deep=True,
            update={
                "software_match_status": "matched" if confirmed_matches else "insufficient_signals",
                "software_matches": confirmed_matches,
                "software_screening": result,
            },
        )

    def _cache_key(self, opportunity: Opportunity) -> str:
        fingerprint = {
            "opportunity": opportunity.model_dump(
                mode="json",
                exclude={"software_matches", "software_match_status", "software_screening", "source_payload"},
            ),
            "catalog_version": self.matcher.catalog_version,
            "prompt_version": PROMPT_VERSION,
            "screening_model": self.screening_model,
            "deep_model": self.deep_model,
        }
        serialized = json.dumps(fingerprint, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def _cached(self, opportunity: Opportunity, *, include_errors: bool = True) -> SoftwareScreeningResult | None:
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT result_json FROM software_screenings WHERE cache_key = ?",
                (self._cache_key(opportunity),),
            ).fetchone()
        if not row:
            return None
        try:
            result = SoftwareScreeningResult.model_validate_json(row[0])
            return result if include_errors or result.status != "error" else None
        except ValueError:
            return None

    def _save(self, opportunity: Opportunity, result: SoftwareScreeningResult) -> None:
        with closing(self._connect()) as connection:
            with connection:
                connection.execute(
                    """
                    INSERT INTO software_screenings(cache_key, opportunity_id, result_json, created_at)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(cache_key) DO UPDATE SET
                        opportunity_id = excluded.opportunity_id,
                        result_json = excluded.result_json,
                        created_at = excluded.created_at
                    """,
                    (
                        self._cache_key(opportunity),
                        opportunity.id,
                        result.model_dump_json(),
                        datetime.now(timezone.utc).isoformat(),
                    ),
                )

    def _connect(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _init_db(self) -> None:
        with closing(self._connect()) as connection:
            with connection:
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS software_screenings (
                        cache_key TEXT PRIMARY KEY,
                        opportunity_id TEXT NOT NULL,
                        result_json TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    )
                    """
                )
                connection.execute(
                    "CREATE INDEX IF NOT EXISTS idx_software_screenings_opportunity ON software_screenings(opportunity_id)"
                )


def _dedupe_opportunities(opportunities: list[Opportunity]) -> list[Opportunity]:
    output: list[Opportunity] = []
    seen: set[str] = set()
    for opportunity in opportunities:
        if opportunity.id in seen:
            continue
        seen.add(opportunity.id)
        output.append(opportunity)
    return output


def _obvious_non_software_reason(opportunity: Opportunity) -> str | None:
    text = _normalize(" ".join((opportunity.title, opportunity.summary)))
    if any(_contains_term(text, term) for term in SOFTWARE_GUARD_TERMS):
        return None
    hit = next((term for term in OBVIOUS_NON_SOFTWARE_TERMS if _contains_term(text, term)), None)
    if not hit:
        return None
    return f"Deterministic hard filter: the opportunity is clearly about {hit}, without a software capability signal."
