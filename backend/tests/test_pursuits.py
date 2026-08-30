from __future__ import annotations

import tempfile
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.config import Settings
from app.config import get_settings
from app.main import _qualified_private_candidates, app
from app.models import EvidenceRef, NeedSignal, Opportunity, PursuitFeedbackRequest, PursuitUpdateRequest, PursuitUpsertRequest
from app.services.pursuits import PursuitAssessmentService, PursuitService


def opportunity(**overrides) -> Opportunity:
    values = {
        "id": "opp-1",
        "source": "khmdhs",
        "source_label": "ΚΗΜΔΗΣ",
        "source_reference": "PROC-123",
        "title": "Ανάπτυξη dashboard και διασύνδεση API",
        "buyer": "Δήμος Δοκιμής",
        "cpv_codes": ["72212000-4"],
        "budget": 18_000,
        "deadline": date.today() + timedelta(days=20),
        "published_at": date.today(),
        "summary": "Custom web dashboard με analytics και API integration.",
        "procurement_stage": "notice",
    }
    values.update(overrides)
    return Opportunity(**values)


class PursuitAssessmentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assessor = PursuitAssessmentService()

    def test_open_software_notice_can_be_pursued(self) -> None:
        from app.models import CompanyProfile

        result = self.assessor.assess(opportunity(), CompanyProfile())

        self.assertEqual(result.candidate_type, "bid_now")
        self.assertEqual(result.pursuit_assessment.verdict, "pursue")
        self.assertGreaterEqual(result.pursuit_assessment.priority_score, 70)
        self.assertFalse(result.pursuit_assessment.hard_gates)

    def test_generic_contract_word_does_not_close_an_open_notice(self) -> None:
        from app.models import CompanyProfile

        result = self.assessor.assess(
            opportunity(summary="Ανοικτή διαδικασία για δημόσια σύμβαση ανάπτυξης portal."),
            CompanyProfile(),
        )

        self.assertNotEqual(result.pursuit_assessment.verdict, "skip")

    def test_named_invitation_and_award_are_hard_gated(self) -> None:
        from app.models import CompanyProfile

        named = self.assessor.assess(
            opportunity(summary="Πρόσκληση υποβολής προσφοράς προς την ΕΤΑΙΡΕΙΑ ΑΕ."),
            CompanyProfile(),
        )
        awarded = self.assessor.assess(
            opportunity(procurement_stage="award", source_reference="AWRD-1", deadline=None),
            CompanyProfile(),
        )

        self.assertEqual(named.pursuit_assessment.verdict, "skip")
        self.assertEqual(awarded.candidate_type, "historical")
        self.assertEqual(awarded.pursuit_assessment.verdict, "skip")

    def test_open_invitation_to_all_operators_is_not_named(self) -> None:
        from app.models import CompanyProfile

        result = self.assessor.assess(
            opportunity(summary="Πρόσκληση υποβολής προσφοράς προς τους οικονομικούς φορείς της αγοράς."),
            CompanyProfile(),
        )

        self.assertFalse(any("κατονομαζόμενο" in gate for gate in result.pursuit_assessment.hard_gates))

    def test_request_is_positioning_not_bid_now(self) -> None:
        from app.models import CompanyProfile

        result = self.assessor.assess(
            opportunity(procurement_stage="request", source_reference="REQ-1", deadline=None),
            CompanyProfile(),
        )

        self.assertEqual(result.candidate_type, "position_early")
        self.assertIn("positioning", result.pursuit_assessment.factors[0].reasons[0])


class PursuitPersistenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.settings = Settings(bookmark_db_path=Path(self.tempdir.name) / "pursuits.sqlite3")
        self.service = PursuitService(self.settings)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_pipeline_and_feedback_are_persistent(self) -> None:
        created = self.service.upsert(PursuitUpsertRequest(opportunity=opportunity(), status="review"))
        updated = self.service.update(created.id, PursuitUpdateRequest(status="pursue", notes="Call buyer"))
        feedback = self.service.save_feedback(
            created.id,
            PursuitFeedbackRequest(fit=True, reason="good_fit", notes="Strong dashboard scope"),
        )

        self.assertEqual(updated.status, "pursue")
        self.assertEqual(updated.notes, "Call buyer")
        self.assertTrue(feedback.feedback.fit)
        self.assertEqual(PursuitService(self.settings).list().pursuits[0].status, "pursue")


class PrivateSignalQualificationTests(unittest.TestCase):
    def test_only_specific_recent_company_signal_enters_action_feed(self) -> None:
        qualified = NeedSignal(
            id="signal-1",
            organization_id="org-1",
            organization_name="Example ΑΕ",
            category="BI/Analytics/AI",
            kind="transformation",
            stage="early",
            need_score=82,
            confidence=78,
            why_now="Η εταιρεία αναζητά ομάδα για νέο analytics dashboard.",
            evidence=EvidenceRef(
                source="company_news",
                url="https://example.test/news/dashboard",
                title="Νέα data platform και dashboard",
                published_at=date.today(),
                excerpt="Επένδυση σε data platform, API integration και analytics dashboard.",
            ),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        generic = qualified.model_copy(update={
            "id": "signal-2",
            "evidence": qualified.evidence.model_copy(update={"title": "Annual report", "excerpt": "General growth update."}),
            "why_now": "General corporate update.",
        })
        market = SimpleNamespace(list_signals=lambda **_: SimpleNamespace(items=[qualified, generic]))

        result = _qualified_private_candidates(market)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].candidate_type, "outbound")
        self.assertEqual(result[0].source, "market")


class PursuitApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        settings = Settings(bookmark_db_path=Path(self.tempdir.name) / "api.sqlite3")
        app.dependency_overrides[get_settings] = lambda: settings
        self.client = TestClient(app)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        self.tempdir.cleanup()

    def test_profile_ai_pipeline_and_feedback_round_trip(self) -> None:
        profile = self.client.get("/api/settings/company-profile").json()
        profile["quick_win_budget_max"] = 25_000
        self.assertEqual(self.client.put("/api/settings/company-profile", json=profile).status_code, 200)

        ai = self.client.get("/api/settings/ai").json()
        ai["preset"] = "economy"
        ai["scan"]["model"] = "gpt-5.6-luna"
        self.assertEqual(self.client.put("/api/settings/ai", json=ai).status_code, 200)

        created = self.client.post("/api/pursuits", json={
            "opportunity": opportunity().model_dump(mode="json"), "status": "review",
        })
        self.assertEqual(created.status_code, 200)
        pursuit_id = created.json()["id"]
        self.assertEqual(self.client.patch(f"/api/pursuits/{pursuit_id}", json={"status": "pursue"}).json()["status"], "pursue")
        feedback = self.client.post(
            f"/api/pursuits/{pursuit_id}/feedback",
            json={"fit": True, "reason": "good_fit", "notes": ""},
        )
        self.assertTrue(feedback.json()["feedback"]["fit"])


if __name__ == "__main__":
    unittest.main()
