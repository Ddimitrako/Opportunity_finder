from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock

import httpx
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import app, get_software_screening_service
from app.models import Opportunity
from app.services.software_screening import SoftwareScreeningService, _Usage


def semantic_crm_opportunity() -> Opportunity:
    return Opportunity(
        id="semantic-crm",
        source="demo",
        source_label="Demo",
        title="Unified constituent engagement records",
        summary="A shared register for constituent relationships and follow-up workflows.",
        cpv_codes=[],
    )


def decision(classification: str = "likely_match", confidence: str = "high") -> dict:
    return {
        "results": [{
            "opportunity_id": "semantic-crm",
            "classification": classification,
            "category_ids": ["crm-pipeline"] if classification == "likely_match" else [],
            "capability_terms": ["constituent engagement", "relationship records"],
            "service_types": ["Deployment"],
            "confidence": confidence,
            "reason": "Η ανάγκη αντιστοιχεί σε διαχείριση σχέσεων και ροής υποθέσεων.",
            "evidence_ids": ["title"],
        }]
    }


def test_title_first_screening_persists_and_reuses_results(tmp_path: Path) -> None:
    service = SoftwareScreeningService(
        Settings(openai_api_key="test-key", bookmark_db_path=tmp_path / "screening.sqlite3")
    )
    service._call_openai = AsyncMock(return_value=(decision(), _Usage(calls=1, input_tokens=120, output_tokens=30)))

    first = asyncio.run(service.scan([semantic_crm_opportunity()]))
    second = asyncio.run(service.scan([semantic_crm_opportunity()]))

    assert first.results[0].status == "catalog_match"
    assert first.results[0].stage == "title"
    assert first.opportunities[0].software_matches
    assert first.run.ai_calls == 1
    assert first.run.input_tokens == 120
    assert second.results[0].cached is True
    assert second.run.cached == 1
    assert second.run.ai_calls == 0
    assert service._call_openai.await_count == 1


def test_ambiguous_title_escalates_to_summary_not_documents(tmp_path: Path) -> None:
    service = SoftwareScreeningService(
        Settings(openai_api_key="test-key", bookmark_db_path=tmp_path / "screening.sqlite3")
    )
    service._call_openai = AsyncMock(side_effect=[
        (decision("needs_more_context", "medium"), _Usage(calls=1)),
        (decision("likely_match", "high"), _Usage(calls=1)),
    ])

    response = asyncio.run(service.scan([semantic_crm_opportunity()]))

    assert response.results[0].status == "catalog_match"
    assert response.results[0].stage == "summary"
    assert response.run.ai_calls == 2
    assert response.run.document_escalations == 0
    assert [call.args[1] for call in service._call_openai.await_args_list] == ["title", "summary"]


def test_saved_errors_remain_visible_but_are_retried_by_next_scan(tmp_path: Path) -> None:
    service = SoftwareScreeningService(
        Settings(openai_api_key="test-key", bookmark_db_path=tmp_path / "screening.sqlite3")
    )
    service._call_openai = AsyncMock(side_effect=[
        httpx.ConnectError("temporary outage"),
        (decision(), _Usage(calls=1)),
    ])

    failed = asyncio.run(service.scan([semantic_crm_opportunity()]))
    assert failed.results[0].status == "error"
    saved_error = service.apply_saved([semantic_crm_opportunity()])[0].software_screening
    assert saved_error is not None
    assert saved_error.status == "error"

    retried = asyncio.run(service.scan([semantic_crm_opportunity()]))
    assert retried.results[0].status == "catalog_match"
    assert service._call_openai.await_count == 2


def test_scan_endpoint_reports_missing_api_key(tmp_path: Path) -> None:
    service = SoftwareScreeningService(
        Settings(openai_api_key=None, bookmark_db_path=tmp_path / "screening.sqlite3")
    )
    app.dependency_overrides[get_software_screening_service] = lambda: service
    try:
        response = TestClient(app).post(
            "/api/software-matches/scan",
            json={"opportunities": [semantic_crm_opportunity().model_dump(mode="json")]},
        )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 503
    assert "OPENAI_API_KEY" in response.json()["detail"]
