from __future__ import annotations

import asyncio
import unittest

from app.config import Settings
from app.services.buyer_intelligence import BuyerIntelligenceService, KhmdhsHistoryLookupError


class BuyerHistoryReliabilityTests(unittest.TestCase):
    def test_keeps_successful_windows_when_another_history_window_fails(self) -> None:
        service = BuyerIntelligenceService(Settings())
        calls = 0

        async def fetch_window(endpoint: str, body: dict[str, object], page: int) -> list[dict[str, object]]:
            nonlocal calls
            calls += 1
            if calls == 1:
                raise KhmdhsHistoryLookupError("KIMDIS did not respond")
            return [{
                "referenceNumber": "26PROC000000001",
                "title": "Software services",
                "organization": "Example buyer",
                "totalCostWithoutVAT": 12_000,
            }]

        service._khmdhs_records = fetch_window  # type: ignore[method-assign]

        records, errors = asyncio.run(service._khmdhs_history_with_diagnostics("buyer-key", days=1, limit=10))

        self.assertEqual(calls, 2)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].source_reference, "26PROC000000001")
        self.assertEqual(errors, ["KIMDIS did not respond"])


if __name__ == "__main__":
    unittest.main()
