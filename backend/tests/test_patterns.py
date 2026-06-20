from __future__ import annotations

import unittest
from datetime import date, timedelta

from fastapi.testclient import TestClient

from app.main import app
from app.models import NeedPatternRequest, Opportunity
from app.services.patterns import PatternDiscoveryService


def opportunity(
    item_id: str,
    title: str,
    summary: str,
    *,
    buyer: str = "Demo buyer",
    budget: float | None = 20_000,
    cpv_codes: list[str] | None = None,
    fit_score: int = 72,
    package_match: str = "Custom software",
    red_flags: list[str] | None = None,
) -> Opportunity:
    return Opportunity(
        id=item_id,
        source="demo",
        source_label="Demo",
        title=title,
        buyer=buyer,
        cpv_codes=cpv_codes or ["72262000-9"],
        budget=budget,
        published_at=date.today() - timedelta(days=20),
        summary=summary,
        raw_text=summary,
        fit_score=fit_score,
        package_match=package_match,
        red_flags=red_flags or [],
    )


class PatternDiscoveryTests(unittest.TestCase):
    def test_dms_workflow_opportunities_cluster(self) -> None:
        response = PatternDiscoveryService().discover(
            NeedPatternRequest(
                opportunities=[
                    opportunity(
                        "a",
                        "DMS workflow support",
                        "Document workflow and protocol support",
                        buyer="Municipality A",
                        cpv_codes=["48311100-2", "72262000-9"],
                        package_match="Document & Case Management",
                    ),
                    opportunity(
                        "b",
                        "Document management dashboard",
                        "DMS case management and workflow dashboard",
                        buyer="Municipality B",
                        cpv_codes=["48311100-2"],
                        package_match="Document & Case Management",
                    ),
                ]
            )
        )

        self.assertEqual(response.patterns[0].pattern_id, "document-workflow-dms")
        self.assertEqual(response.patterns[0].buyer_count, 2)

    def test_dashboard_reporting_opportunities_cluster(self) -> None:
        response = PatternDiscoveryService().discover(
            NeedPatternRequest(
                opportunities=[
                    opportunity("a", "BI dashboard", "KPI reporting and analytics", cpv_codes=["72316000-3"]),
                    opportunity("b", "Reporting dashboard", "Statistics dashboard for data analysis", cpv_codes=["72212482-0"]),
                ]
            )
        )

        self.assertEqual(response.patterns[0].pattern_id, "dashboard-bi-reporting")

    def test_generic_custom_software_is_not_overclustered(self) -> None:
        response = PatternDiscoveryService().discover(
            NeedPatternRequest(
                opportunities=[
                    opportunity("a", "Custom software", "General custom software", cpv_codes=["72262000-9"]),
                    opportunity("b", "Software development", "Generic software delivery", cpv_codes=["72262000-9"]),
                ]
            )
        )

        self.assertEqual(response.patterns, [])

    def test_same_buyer_repeat_counts_with_lower_diversity(self) -> None:
        response = PatternDiscoveryService().discover(
            NeedPatternRequest(
                opportunities=[
                    opportunity("a", "Software support", "Technical support and maintenance", buyer="Same buyer", cpv_codes=["72250000-2"]),
                    opportunity("b", "Software maintenance", "Managed software support", buyer="Same buyer", cpv_codes=["72260000-5"]),
                ]
            )
        )

        self.assertEqual(response.patterns[0].pattern_id, "software-support-maintenance")
        self.assertEqual(response.patterns[0].buyer_count, 1)

    def test_missing_budget_and_dates_do_not_crash(self) -> None:
        first = opportunity("a", "Portal platform", "Citizen portal and e-services", budget=None, cpv_codes=["72420000-0"])
        second = opportunity("b", "Web portal", "Application forms portal", budget=None, cpv_codes=["72421000-7"])
        first.published_at = None
        second.published_at = None

        response = PatternDiscoveryService().discover(NeedPatternRequest(opportunities=[first, second]))

        self.assertEqual(response.patterns[0].pattern_id, "portal-web-app")
        self.assertEqual(response.patterns[0].budget_range, "Unknown")

    def test_patterns_below_threshold_are_filtered(self) -> None:
        response = PatternDiscoveryService().discover(
            NeedPatternRequest(
                min_opportunities=2,
                opportunities=[
                    opportunity("a", "CMS website maintenance", "Website CMS hosting and maintenance", cpv_codes=["72413000-8"]),
                ],
            )
        )

        self.assertEqual(response.patterns, [])


class PatternApiTests(unittest.TestCase):
    def test_patterns_endpoint_returns_empty_response(self) -> None:
        client = TestClient(app)
        response = client.post("/api/patterns/discover", json={"opportunities": []})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["patterns"], [])
        self.assertEqual(payload["unmatched_count"], 0)

    def test_patterns_endpoint_returns_non_empty_response(self) -> None:
        client = TestClient(app)
        items = [
            opportunity("a", "DMS workflow support", "Document workflow support", cpv_codes=["48311100-2"]).model_dump(mode="json"),
            opportunity("b", "Document workflow", "DMS protocol workflow", cpv_codes=["48311100-2"]).model_dump(mode="json"),
        ]

        response = client.post("/api/patterns/discover", json={"opportunities": items})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["patterns"][0]["pattern_id"], "document-workflow-dms")


if __name__ == "__main__":
    unittest.main()
