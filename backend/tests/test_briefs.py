from __future__ import annotations

import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from app.config import Settings
from app.models import (
    BriefEvidence,
    DocumentBrief,
    OpportunityDetails,
    OpportunityGuidance,
)
from app.services.briefs import (
    DocumentBriefService,
    _analyze_procurement,
    _decide_verdict,
)


def actionable_details(*, metadata: dict | None = None, related: dict | None = None) -> OpportunityDetails:
    return OpportunityDetails(
        source="khmdhs",
        reference="26PROC000000001",
        title="Software services",
        metadata=metadata or {"deadline": (date.today() + timedelta(days=15)).isoformat()},
        related_references=related or {"notices": ["26PROC000000001"]},
        guidance=OpportunityGuidance(
            current_stage="notice",
            current_stage_label="Notice",
            is_actionable=True,
            next_action="Review",
        ),
    )


def readable_documents() -> list[dict]:
    return [{"label": "Notice", "url": "https://example.test/notice.pdf", "reference": "26PROC000000001", "readable": True, "pages": []}]


class ProcurementAnalysisTests(unittest.TestCase):
    def test_amount_below_threshold_is_not_a_no_go_by_itself(self) -> None:
        details = actionable_details(metadata={
            "deadline": (date.today() + timedelta(days=15)).isoformat(),
            "totalCostWithoutVAT": 29_500,
        })
        access, continuity, budget, _ = _analyze_procurement(details, readable_documents(), [])

        self.assertEqual(access.status, "open_competition")
        self.assertTrue(budget.direct_award_eligible)
        self.assertEqual(_decide_verdict(access, continuity, 80), "GO")

    def test_named_invitation_is_a_hard_no_go(self) -> None:
        evidence = [BriefEvidence(
            id="d1-p1-c1",
            document_label="Invitation",
            url="https://example.test/invitation.pdf",
            page=1,
            excerpt="Πρόσκληση υποβολής προσφοράς προς ACME SOFTWARE Α.Ε. για υπηρεσίες υποστήριξης.",
        )]
        access, continuity, _, _ = _analyze_procurement(actionable_details(), readable_documents(), evidence)

        self.assertEqual(access.status, "named_invitation")
        self.assertIn("ACME SOFTWARE", access.named_invitee or "")
        self.assertEqual(_decide_verdict(access, continuity, 95), "NO-GO")

    def test_generic_invitation_is_not_treated_as_named(self) -> None:
        evidence = [BriefEvidence(
            id="d1-p1-c1",
            document_label="Invitation",
            url="https://example.test/invitation.pdf",
            page=1,
            excerpt="Πρόσκληση υποβολής προσφοράς προς κάθε ενδιαφερόμενο οικονομικό φορέα για υπηρεσίες λογισμικού.",
        )]
        access, _, _, _ = _analyze_procurement(actionable_details(), readable_documents(), evidence)
        self.assertEqual(access.status, "open_competition")

    def test_contract_in_lifecycle_is_a_hard_no_go(self) -> None:
        details = actionable_details(related={"notices": ["26PROC000000001"], "contracts": ["26SYMV000000002"]})
        documents = [
            *readable_documents(),
            {"label": "Contract", "url": "https://example.test/contract.pdf", "reference": "26SYMV000000002", "readable": True, "pages": []},
        ]
        access, continuity, _, evidence = _analyze_procurement(details, documents, [])

        self.assertEqual(access.status, "contracted")
        self.assertEqual(_decide_verdict(access, continuity, 95), "NO-GO")
        self.assertTrue(access.evidence_ids)
        access_evidence = next(item for item in evidence if item.id == access.evidence_ids[0])
        self.assertTrue(access_evidence.url.endswith("contract.pdf"))

    def test_explicit_continuation_is_confirmed_but_similarity_is_not(self) -> None:
        explicit = [BriefEvidence(
            id="d1-p2-c1",
            document_label="Specifications",
            url="https://example.test/spec.pdf",
            page=2,
            excerpt="Το αντικείμενο αφορά συντήρηση του υφιστάμενου πληροφοριακού συστήματος σε συνέχεια της 25SYMV000000123.",
        )]
        access, continuity, _, _ = _analyze_procurement(actionable_details(), readable_documents(), explicit)
        self.assertEqual(continuity.status, "confirmed_continuation")
        self.assertEqual(continuity.prior_reference, "25SYMV000000123")
        self.assertEqual(_decide_verdict(access, continuity, 90), "CONDITIONAL GO")

        similar_only = [BriefEvidence(
            id="d1-p1-c1",
            document_label="Notice",
            url="https://example.test/notice.pdf",
            excerpt="Προμήθεια λογισμικού και υπηρεσιών πληροφορικής.",
        )]
        _, continuity, _, _ = _analyze_procurement(actionable_details(), readable_documents(), similar_only)
        self.assertEqual(continuity.status, "not_confirmed")

    def test_gross_only_amount_does_not_trigger_threshold(self) -> None:
        details = actionable_details(metadata={
            "deadline": (date.today() + timedelta(days=15)).isoformat(),
            "totalCostWithVAT": 29_000,
        })
        _, _, budget, _ = _analyze_procurement(details, readable_documents(), [])
        self.assertIsNone(budget.direct_award_eligible)
        self.assertIsNone(budget.amount_without_vat)
        self.assertTrue(budget.evidence_ids)


class BriefCacheTests(unittest.TestCase):
    def test_legacy_brief_is_preserved_and_marked_outdated(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            settings = Settings(bookmark_db_path=str(Path(directory) / "briefs.sqlite"))
            service = DocumentBriefService(settings)
            legacy = DocumentBrief(
                source="demo",
                reference="legacy-1",
                project_summary="Legacy brief",
                generated_at=datetime.now(timezone.utc),
            )
            service._save_brief(legacy)

            response = service.get_cached_brief("demo", "legacy-1")
            self.assertTrue(response.cached)
            self.assertTrue(response.outdated)
            self.assertEqual(response.brief.project_summary if response.brief else None, "Legacy brief")


if __name__ == "__main__":
    unittest.main()
