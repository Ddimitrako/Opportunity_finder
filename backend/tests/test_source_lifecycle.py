from __future__ import annotations

import unittest
from datetime import date

from app.config import Settings
from app.sources.khmdhs import KhmdhsClient
from app.sources.ted import TedClient


class SourceLifecycleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = Settings()

    def test_khmdhs_request_delivery_date_is_not_a_deadline(self) -> None:
        item = KhmdhsClient(self.settings)._to_opportunity({
            "referenceNumber": "REQ-2026-1",
            "title": "Ανάπτυξη portal",
            "organization": "Δήμος Δοκιμής",
            "procurementDeliveryDate": "2026-12-31",
            "totalCostWithoutVAT": 20_000,
        }, endpoint="request")

        self.assertEqual(item.candidate_type, "position_early")
        self.assertEqual(item.procurement_stage, "approved_request")
        self.assertIsNone(item.deadline)

    def test_khmdhs_notice_uses_submission_deadline(self) -> None:
        item = KhmdhsClient(self.settings)._to_opportunity({
            "referenceNumber": "PROC-2026-1",
            "title": "Ανάπτυξη dashboard",
            "organization": "Δήμος Δοκιμής",
            "submissionDeadline": "2026-10-20",
            "procurementDeliveryDate": "2027-05-01",
        }, endpoint="notice")

        self.assertEqual(item.candidate_type, "bid_now")
        self.assertEqual(item.deadline, date(2026, 10, 20))

    def test_ted_award_is_historical_even_if_a_deadline_is_present(self) -> None:
        item = TedClient(self.settings)._to_opportunity({
            "publication-number": "123-2026",
            "notice-title": "Software contract result",
            "buyer-name": "Example buyer",
            "notice-type": "Contract award notice",
            "deadline": "2026-12-01",
        })

        self.assertEqual(item.candidate_type, "historical")
        self.assertEqual(item.procurement_stage, "award")


if __name__ == "__main__":
    unittest.main()
