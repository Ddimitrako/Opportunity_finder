from __future__ import annotations

import asyncio
import unittest

import httpx

from app.services.details import _khmdhs_json


class KhmdhsDetailsRequestTests(unittest.TestCase):
    def test_retries_a_timeout_then_returns_the_response(self) -> None:
        attempts = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                raise httpx.ReadTimeout("source timed out", request=request)
            return httpx.Response(200, json={"content": [{"referenceNumber": "26REQ019661368"}]})

        async def run() -> tuple[dict[str, object] | None, str | None]:
            async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
                return await _khmdhs_json(client, "GET", "https://example.test/details")

        payload, error = asyncio.run(run())

        self.assertEqual(attempts, 2)
        self.assertIsNone(error)
        self.assertEqual(payload, {"content": [{"referenceNumber": "26REQ019661368"}]})

    def test_returns_a_partial_data_error_after_transient_source_failures(self) -> None:
        attempts = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal attempts
            attempts += 1
            return httpx.Response(503, json={"message": "maintenance"})

        async def run() -> tuple[dict[str, object] | None, str | None]:
            async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
                return await _khmdhs_json(client, "GET", "https://example.test/details")

        payload, error = asyncio.run(run())

        self.assertEqual(attempts, 2)
        self.assertIsNone(payload)
        self.assertEqual(error, "KIMDIS is temporarily unavailable while loading live details.")


if __name__ == "__main__":
    unittest.main()
