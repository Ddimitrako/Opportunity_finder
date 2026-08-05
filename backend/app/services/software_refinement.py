from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from app.ai_models import resolve_ai_model, model_request_options
from app.config import Settings
from app.models import (
    BriefEvidence,
    Opportunity,
    SoftwareMatch,
    SoftwareMatchRefineResponse,
)
from app.services.bookmarks import _resolve_db_path
from app.services.briefs import OpportunityAIContextService, _extract_output_text
from app.services.chat import select_relevant_evidence
from app.services.software_matching import MATCH_THRESHOLD, SoftwareMatchingService


MAX_EVIDENCE_ITEMS = 6
MAX_EVIDENCE_CHARS = 8_000


class SoftwareRefinementUnavailable(RuntimeError):
    pass


class SoftwareRefinementError(RuntimeError):
    pass


class SoftwareRefinementService:
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
        self._init_db()

    async def refine(self, opportunity: Opportunity, model: str | None = None) -> SoftwareMatchRefineResponse:
        if not self.settings.openai_api_key:
            raise SoftwareRefinementUnavailable("OPENAI_API_KEY is not configured")
        selected_model = resolve_ai_model(self.settings, model)
        candidates = self.matcher.candidates(opportunity, limit=8)
        if not candidates:
            return SoftwareMatchRefineResponse(
                matches=[],
                match_status="insufficient_signals",
                model=selected_model,
                cached=False,
                catalog_version=self.matcher.catalog_version,
            )

        evidence = await self._evidence(opportunity, candidates)
        evidence_ids = [item.id for item in evidence]
        cache_key = self._cache_key(opportunity, selected_model, evidence_ids)
        cached = self._cached(cache_key)
        if cached:
            return cached.model_copy(update={"cached": True})

        try:
            parsed = await self._call_openai(opportunity, candidates, evidence, selected_model)
            response = self._validated_response(parsed, candidates, evidence_ids, selected_model)
        except (httpx.HTTPError, json.JSONDecodeError, ValueError, TypeError) as exc:
            raise SoftwareRefinementError(f"AI refinement failed safely: {exc.__class__.__name__}") from exc

        self._save(cache_key, response)
        return response

    async def _evidence(self, opportunity: Opportunity, candidates: list[SoftwareMatch]) -> list[BriefEvidence]:
        if opportunity.source == "demo" or not opportunity.source_reference:
            return []
        try:
            context = await self.context_service.prepare(opportunity.source, opportunity.source_reference)
        except Exception:
            return []
        candidate_context = " ".join(
            [opportunity.title, opportunity.summary]
            + [item.product.name for item in candidates]
            + [signal for item in candidates for signal in item.matched_signals]
        )
        return select_relevant_evidence(
            context,
            candidate_context,
            max_items=MAX_EVIDENCE_ITEMS,
            max_chars=MAX_EVIDENCE_CHARS,
        )

    async def _call_openai(
        self,
        opportunity: Opportunity,
        candidates: list[SoftwareMatch],
        evidence: list[BriefEvidence],
        model: str,
    ) -> dict[str, Any]:
        prompt = {
            "role": "You refine deterministic open-source product recommendations for a Greek procurement opportunity.",
            "language": "Greek",
            "rules": [
                "Use only the supplied candidates. Never invent or alter a slug.",
                "You may rerank, lower a score, or reject candidates, but cannot bypass deterministic exclusions.",
                "Use only supplied evidence IDs. Empty evidence IDs are valid when document evidence is unavailable.",
                "Return insufficient_signals and an empty matches array when the evidence does not support a product.",
                "Keep each reason concise and decision-oriented. Put license, edition, delivery, and repository concerns in caveats.",
            ],
            "opportunity": opportunity.model_dump(
                mode="json",
                exclude={"source_payload", "software_matches", "software_match_status", "raw_text"},
            ),
            "raw_text_excerpt": opportunity.raw_text[:4_000],
            "candidates": [
                {
                    "slug": item.product.slug,
                    "name": item.product.name,
                    "edition": item.product.edition,
                    "deterministic_score": item.score,
                    "signals": item.matched_signals,
                    "services": [service.model_dump(mode="json") for service in item.service_recommendations],
                    "caveats": item.caveats,
                }
                for item in candidates
            ],
            "evidence": [item.model_dump(mode="json") for item in evidence],
        }
        candidate_slugs = [item.product.slug for item in candidates]
        payload = {
            "model": model,
            "input": json.dumps(prompt, ensure_ascii=False),
            "store": False,
            **model_request_options(model, temperature=0.1),
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "software_match_refinement_v1",
                    "strict": True,
                    "schema": _structured_output_schema(candidate_slugs, [item.id for item in evidence]),
                }
            },
        }
        headers = {
            "Authorization": f"Bearer {self.settings.openai_api_key}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=90) as client:
            response = await client.post("https://api.openai.com/v1/responses", json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
        output = _extract_output_text(data)
        if not output:
            raise ValueError("OpenAI returned no structured output")
        parsed = json.loads(output)
        if not isinstance(parsed, dict):
            raise ValueError("OpenAI output was not an object")
        return parsed

    def _validated_response(
        self,
        parsed: dict[str, Any],
        candidates: list[SoftwareMatch],
        evidence_ids: list[str],
        model: str,
    ) -> SoftwareMatchRefineResponse:
        candidate_map = {item.product.slug: item for item in candidates}
        allowed_evidence = set(evidence_ids)
        output: list[SoftwareMatch] = []
        seen: set[str] = set()
        raw_matches = parsed.get("matches") if isinstance(parsed.get("matches"), list) else []
        for item in raw_matches:
            if not isinstance(item, dict):
                continue
            slug = str(item.get("slug") or "")
            base = candidate_map.get(slug)
            if not base or slug in seen:
                continue
            seen.add(slug)
            score = max(0, min(100, int(item.get("score", base.score))))
            if score < MATCH_THRESHOLD:
                continue
            confidence = str(item.get("confidence") or "low")
            if confidence not in {"high", "medium", "low"}:
                confidence = "low"
            reason = str(item.get("reason") or "AI refinement retained this deterministic candidate.").strip()
            valid_evidence = [
                str(value) for value in item.get("evidence_ids", [])
                if str(value) in allowed_evidence
            ]
            ai_caveats = [str(value).strip() for value in item.get("caveats", []) if str(value).strip()]
            output.append(
                base.model_copy(
                    deep=True,
                    update={
                        "score": score,
                        "confidence": confidence,
                        "source": "ai_refined",
                        "matched_signals": [reason, *base.matched_signals],
                        "caveats": list(dict.fromkeys([*base.caveats, *ai_caveats])),
                        "evidence_ids": valid_evidence,
                    },
                )
            )
        output.sort(key=lambda item: (-item.score, -item.product.editorial_score, item.product.name.casefold()))
        output = output[:3]
        requested_status = parsed.get("match_status")
        status = "matched" if output and requested_status != "insufficient_signals" else "insufficient_signals"
        if status == "insufficient_signals":
            output = []
        return SoftwareMatchRefineResponse(
            matches=output,
            match_status=status,
            model=model,
            cached=False,
            catalog_version=self.matcher.catalog_version,
        )

    def _cache_key(self, opportunity: Opportunity, model: str, evidence_ids: list[str]) -> str:
        fingerprint = {
            "opportunity": opportunity.model_dump(
                mode="json",
                exclude={"software_matches", "software_match_status", "source_payload"},
            ),
            "catalog_version": self.matcher.catalog_version,
            "model": model,
            "evidence_ids": evidence_ids,
        }
        value = json.dumps(fingerprint, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    def _cached(self, cache_key: str) -> SoftwareMatchRefineResponse | None:
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT response_json FROM software_match_refinements WHERE cache_key = ?",
                (cache_key,),
            ).fetchone()
        return SoftwareMatchRefineResponse.model_validate_json(row[0]) if row else None

    def _save(self, cache_key: str, response: SoftwareMatchRefineResponse) -> None:
        with closing(self._connect()) as connection:
            with connection:
                connection.execute(
                    """
                    INSERT INTO software_match_refinements(cache_key, response_json, created_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(cache_key) DO UPDATE SET
                        response_json = excluded.response_json,
                        created_at = excluded.created_at
                    """,
                    (
                        cache_key,
                        response.model_dump_json(),
                        datetime.now(timezone.utc).isoformat(),
                    ),
                )

    def _connect(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        return sqlite3.connect(self.db_path)

    def _init_db(self) -> None:
        with closing(self._connect()) as connection:
            with connection:
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS software_match_refinements (
                        cache_key TEXT PRIMARY KEY,
                        response_json TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    )
                    """
                )


def _structured_output_schema(candidate_slugs: list[str], evidence_ids: list[str]) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["match_status", "matches"],
        "properties": {
            "match_status": {"type": "string", "enum": ["matched", "insufficient_signals"]},
            "matches": {
                "type": "array",
                "maxItems": 3,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["slug", "score", "confidence", "reason", "caveats", "evidence_ids"],
                    "properties": {
                        "slug": {"type": "string", "enum": candidate_slugs},
                        "score": {"type": "integer", "minimum": 0, "maximum": 100},
                        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
                        "reason": {"type": "string"},
                        "caveats": {"type": "array", "items": {"type": "string"}},
                        "evidence_ids": {
                            "type": "array",
                            "items": {"type": "string", **({"enum": evidence_ids} if evidence_ids else {})},
                            "maxItems": len(evidence_ids),
                        },
                    },
                },
            },
        },
    }
