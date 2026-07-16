from __future__ import annotations

import tempfile
import unittest
from datetime import date
from pathlib import Path

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import app, get_market_service
from app.models import Opportunity, TrackingEntryCreate, WatchSourceCreate
from app.services.market import MarketService, classify_category, normalize_name


def market_opportunity(item_id: str = "market-1") -> Opportunity:
    return Opportunity(
        id=item_id,
        source="demo",
        source_label="Demo",
        title="Microsoft Dynamics 365 ERP implementation and Power BI analytics",
        buyer="Demo Buyer Α.Ε.",
        cpv_codes=["48400000-2", "72316000-3"],
        budget=55_000,
        deadline=date.today(),
        published_at=date.today(),
        summary="Digital transformation with Microsoft ERP and reporting",
        raw_text="Microsoft Dynamics 365 and Power BI",
        recommendation="Review",
    )


class MarketServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.settings = Settings(bookmark_db_path=Path(self.tempdir.name) / "market.sqlite3")
        self.service = MarketService(self.settings)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_ingest_is_idempotent_and_builds_buyer_signal(self) -> None:
        created, updated = self.service.ingest_opportunities([market_opportunity()])
        second_created, _ = self.service.ingest_opportunities([market_opportunity()])

        self.assertEqual(created, 1)
        self.assertEqual(updated, 0)
        self.assertEqual(second_created, 0)
        buyers = self.service.list_organizations(role="buyer").items
        self.assertEqual(len(buyers), 1)
        self.assertEqual(buyers[0].strongest_category, "ERP/Finance")
        self.assertGreaterEqual(buyers[0].strongest_signal_score, 75)

    def test_brand_mentions_require_source_evidence(self) -> None:
        self.service.ingest_opportunities([market_opportunity()])
        brands = {brand.name: brand for brand in self.service.list_brands().items}

        self.assertEqual(brands["Microsoft"].mention_count, 1)
        self.assertEqual(brands["SAP"].mention_count, 0)
        detail = self.service.brand_detail("microsoft")
        self.assertIsNotNone(detail)
        self.assertTrue(detail.mentions[0].evidence.title)

    def test_tracking_upsert_is_lightweight_and_persistent(self) -> None:
        self.service.ingest_opportunities([market_opportunity()])
        buyer = self.service.list_organizations(role="buyer").items[0]
        entry = self.service.upsert_tracking(
            TrackingEntryCreate(
                entity_type="buyer",
                entity_id=buyer.id,
                state="contact_planned",
                notes="ERP discovery",
                next_action="Call the CIO",
            )
        )

        self.assertEqual(entry.entity_name, "Demo Buyer Α.Ε.")
        self.assertEqual(entry.state, "contact_planned")
        self.assertEqual(self.service.overview().tracked_entities, 1)

    def test_watch_source_rejects_non_public_https(self) -> None:
        self.service.ingest_opportunities([market_opportunity()])
        buyer = self.service.list_organizations(role="buyer").items[0]

        with self.assertRaises(ValueError):
            self.service.create_watch_source(
                WatchSourceCreate(
                    organization_id=buyer.id,
                    source_type="careers",
                    url="http://127.0.0.1/jobs",
                )
            )

    def test_category_and_name_normalization(self) -> None:
        category, reasons = classify_category("ServiceNow IT service management platform", [])
        self.assertEqual(category, "ITSM/IT Operations")
        self.assertTrue(reasons)
        self.assertEqual(normalize_name("Demo Buyer Α.Ε."), normalize_name("DEMO BUYER AE"))


class MarketApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.service = MarketService(Settings(bookmark_db_path=Path(self.tempdir.name) / "market-api.sqlite3"))
        self.service.ingest_opportunities([market_opportunity("api-1")])
        app.dependency_overrides[get_market_service] = lambda: self.service
        self.client = TestClient(app)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        self.tempdir.cleanup()

    def test_market_overview_and_buyer_detail(self) -> None:
        overview = self.client.get("/api/market/overview")
        self.assertEqual(overview.status_code, 200)
        self.assertEqual(overview.json()["open_opportunities"], 1)

        buyers = self.client.get("/api/market/buyers?min_score=25")
        self.assertEqual(buyers.status_code, 200)
        buyer_id = buyers.json()["items"][0]["id"]
        detail = self.client.get(f"/api/market/buyers/{buyer_id}")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.json()["organization"]["name"], "Demo Buyer Α.Ε.")
        self.assertTrue(detail.json()["signals"][0]["why_now"])

    def test_tracking_api(self) -> None:
        buyer_id = self.service.list_organizations(role="buyer").items[0].id
        response = self.client.post(
            "/api/market/tracking",
            json={"entity_type": "buyer", "entity_id": buyer_id, "state": "watching", "notes": "Watch"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["entity_name"], "Demo Buyer Α.Ε.")


if __name__ == "__main__":
    unittest.main()
