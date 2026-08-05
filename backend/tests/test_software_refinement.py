from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import app, get_software_refinement_service
from app.models import Opportunity
from app.services.software_refinement import SoftwareRefinementService, SoftwareRefinementUnavailable


def opportunity() -> Opportunity:
    return Opportunity(
        id="crm-opportunity",
        source="demo",
        source_label="Demo",
        title="CRM deployment and API integration",
        summary="CRM deployment and API integration",
        raw_text="CRM deployment and API integration",
        cpv_codes=["48445000-8"],
    )


def test_refinement_validates_slugs_and_uses_cache(tmp_path: Path) -> None:
    settings = Settings(openai_api_key="test-key", bookmark_db_path=tmp_path / "cache.sqlite3")
    service = SoftwareRefinementService(settings)
    service._call_openai = AsyncMock(return_value={
        "match_status": "matched",
        "matches": [{
            "slug": "frappe-crm",
            "score": 88,
            "confidence": "high",
            "reason": "The tender explicitly requests CRM integration.",
            "caveats": ["Confirm migration volume."],
            "evidence_ids": [],
        }],
    })

    first = asyncio.run(service.refine(opportunity(), "gpt-4.1-mini"))
    second = asyncio.run(service.refine(opportunity(), "gpt-4.1-mini"))

    assert first.matches[0].product.slug == "frappe-crm"
    assert first.matches[0].source == "ai_refined"
    assert first.cached is False
    assert second.cached is True
    assert service._call_openai.await_count == 1


def test_unknown_ai_slug_cannot_escape_candidate_allow_list(tmp_path: Path) -> None:
    settings = Settings(openai_api_key="test-key", bookmark_db_path=tmp_path / "cache.sqlite3")
    service = SoftwareRefinementService(settings)
    service._call_openai = AsyncMock(return_value={
        "match_status": "matched",
        "matches": [{
            "slug": "invented-product",
            "score": 99,
            "confidence": "high",
            "reason": "Invented",
            "caveats": [],
            "evidence_ids": ["invented-evidence"],
        }],
    })

    response = asyncio.run(service.refine(opportunity()))
    assert response.match_status == "insufficient_signals"
    assert response.matches == []


def test_missing_api_key_leaves_deterministic_matching_available(tmp_path: Path) -> None:
    settings = Settings(openai_api_key=None, bookmark_db_path=tmp_path / "cache.sqlite3")
    service = SoftwareRefinementService(settings)
    assert service.matcher.match(opportunity())
    with pytest.raises(SoftwareRefinementUnavailable):
        asyncio.run(service.refine(opportunity()))


def test_refinement_endpoint_reports_unavailable_ai_without_breaking_search(tmp_path: Path) -> None:
    service = SoftwareRefinementService(
        Settings(openai_api_key=None, bookmark_db_path=tmp_path / "cache.sqlite3")
    )
    app.dependency_overrides[get_software_refinement_service] = lambda: service
    try:
        response = TestClient(app).post(
            "/api/software-matches/refine",
            json={"opportunity": opportunity().model_dump(mode="json")},
        )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 503
    assert "OPENAI_API_KEY" in response.json()["detail"]
