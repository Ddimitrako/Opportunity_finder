from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch

from app.config import Settings
from app.models import (
    BriefEvidence,
    BriefHistoryItem,
    DocumentLink,
    OpportunityAIContext,
    OpportunityDetails,
)
from app.services.briefs import OpportunityAIContextService
from app.services.chat import ChatGenerationError, OpportunityChatService, _history_catalog, select_relevant_evidence


def sample_context() -> OpportunityAIContext:
    details = OpportunityDetails(
        source="demo",
        reference="chat-1",
        title="Opportunity chat test",
        metadata={"deadline": "2026-08-20", "totalCostWithoutVAT": 25_000},
        documents=[
            DocumentLink(label="Notice", url="https://example.test/notice.pdf", document_type="notice", reference="chat-1"),
        ],
    )
    return OpportunityAIContext(
        source="demo",
        reference="chat-1",
        details=details,
        evidence=[
            BriefEvidence(
                id="d1-p2-c1",
                document_label="Notice",
                url="https://example.test/notice.pdf",
                page=2,
                reference="chat-1",
                excerpt="Η προθεσμία υποβολής είναι 20 Αυγούστου 2026 και απαιτείται τεχνική προσφορά.",
            ),
            BriefEvidence(
                id="d1-p4-c1",
                document_label="Notice",
                url="https://example.test/notice.pdf",
                page=4,
                reference="chat-1",
                excerpt="Τα παραδοτέα περιλαμβάνουν εγκατάσταση, εκπαίδευση και υποστήριξη.",
            ),
        ],
        source_documents=details.documents,
        available_document_count=1,
        analyzed_document_count=1,
        readable_document_count=1,
        history_12_months=[
            BriefHistoryItem(
                title="Prior software award",
                reference="25AWRD001",
                supplier="ACME",
                url="https://example.test/history.pdf",
            ),
        ],
        prepared_at=datetime.now(timezone.utc),
    )


class FakeContextService:
    def __init__(self, context: OpportunityAIContext) -> None:
        self.context = context
        self.prepare_calls: list[bool] = []

    async def prepare(self, source: str, reference: str, *, force_refresh: bool = False) -> OpportunityAIContext:
        self.prepare_calls.append(force_refresh)
        return self.context

    def get_cached_context(self, source: str, reference: str) -> OpportunityAIContext | None:
        return self.context


class OpportunityChatTests(unittest.IsolatedAsyncioTestCase):
    async def test_chat_works_without_a_brief_and_persists_verified_citations(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            settings = Settings(
                bookmark_db_path=Path(directory) / "chat.sqlite3",
                openai_api_key="test-key",
            )
            context = sample_context()
            fake_context = FakeContextService(context)
            service = OpportunityChatService(settings, fake_context)  # type: ignore[arg-type]
            history_id = next(iter(_history_catalog(context.history_12_months)))
            service._call_openai = AsyncMock(return_value={  # type: ignore[method-assign]
                "answer": "Η προθεσμία επιβεβαιώνεται στο notice.",
                "evidence_ids": ["d1-p2-c1", "unknown-evidence"],
                "history_ids": [history_id, "unknown-history"],
                "strategic_advice": "Ξεκινήστε άμεσα τεχνικό έλεγχο, με επιφύλαξη κόστους.",
                "suggested_questions": ["Ποια είναι τα παραδοτέα;"],
            })

            result = await service.ask("demo", "chat-1", "Ποια είναι η προθεσμία;", model="gpt-5.6")

            self.assertEqual(result.assistant_message.content, "Η προθεσμία επιβεβαιώνεται στο notice.")
            self.assertEqual(result.assistant_message.model, "gpt-5.6")
            self.assertEqual(service._call_openai.await_args.args[-1], "gpt-5.6")  # type: ignore[union-attr]
            self.assertEqual([item.id for item in result.assistant_message.citations], ["d1-p2-c1", history_id])
            self.assertEqual(result.assistant_message.citations[1].kind, "history")
            restored = service.get_thread("demo", "chat-1")
            self.assertEqual([item.role for item in restored.messages], ["user", "assistant"])
            self.assertEqual(restored.messages[-1].strategic_advice, result.assistant_message.strategic_advice)

    async def test_openai_failure_does_not_save_a_partial_turn(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            settings = Settings(
                bookmark_db_path=Path(directory) / "chat.sqlite3",
                openai_api_key="test-key",
            )
            service = OpportunityChatService(settings, FakeContextService(sample_context()))  # type: ignore[arg-type]
            service._call_openai = AsyncMock(side_effect=RuntimeError("provider down"))  # type: ignore[method-assign]

            with self.assertRaises(ChatGenerationError):
                await service.ask("demo", "chat-1", "Can we bid?")

            self.assertEqual(service.get_thread("demo", "chat-1").messages, [])

    async def test_answer_with_only_unknown_citations_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            settings = Settings(bookmark_db_path=Path(directory) / "chat.sqlite3", openai_api_key="test-key")
            service = OpportunityChatService(settings, FakeContextService(sample_context()))  # type: ignore[arg-type]
            service._call_openai = AsyncMock(return_value={  # type: ignore[method-assign]
                "answer": "Unsupported factual answer",
                "evidence_ids": ["made-up-id"],
                "history_ids": [],
                "strategic_advice": None,
                "suggested_questions": [],
            })

            with self.assertRaises(ChatGenerationError):
                await service.ask("demo", "chat-1", "What is the deadline?")

            self.assertEqual(service.get_thread("demo", "chat-1").messages, [])

    async def test_refresh_forces_context_rebuild_and_clear_keeps_context(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            settings = Settings(bookmark_db_path=Path(directory) / "chat.sqlite3", openai_api_key="test-key")
            fake_context = FakeContextService(sample_context())
            service = OpportunityChatService(settings, fake_context)  # type: ignore[arg-type]

            status = await service.refresh_context("demo", "chat-1")
            service.clear_thread("demo", "chat-1")

            self.assertTrue(status.ready)
            self.assertEqual(fake_context.prepare_calls, [True])
            self.assertTrue(service.get_thread("demo", "chat-1").context.ready)

    def test_retrieval_is_limited_and_lexically_relevant(self) -> None:
        context = sample_context()
        selected = select_relevant_evidence(context, "Ποια είναι τα παραδοτέα και η υποστήριξη;", max_items=1)
        self.assertEqual([item.id for item in selected], ["d1-p4-c1"])


class OpportunityContextTests(unittest.IsolatedAsyncioTestCase):
    async def test_cached_context_tracks_the_exact_documents_attempted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            settings = Settings(bookmark_db_path=Path(directory) / "context.sqlite3")
            first = DocumentLink(label="Payment", url="https://example.test/payment.pdf", document_type="payment", reference="old")
            second = DocumentLink(label="Current notice", url="https://example.test/current.pdf", document_type="notice", reference="current")
            third = DocumentLink(label="Contract", url="https://example.test/contract.pdf", document_type="contract", reference="old")
            details = OpportunityDetails(
                source="demo",
                reference="current",
                title="Context test",
                documents=[first, second, third],
            )
            details_service = AsyncMock()
            details_service.get_details.return_value = details
            extracted = [
                {"document": second.model_dump(mode="json"), "label": second.label, "url": second.url, "reference": second.reference, "pages": [{"page": 1, "text": "Current readable notice"}], "readable": True},
                {"document": third.model_dump(mode="json"), "label": third.label, "url": third.url, "reference": third.reference, "pages": [], "readable": False},
            ]
            service = OpportunityAIContextService(settings, details_service)

            with patch("app.services.briefs._fetch_document_texts", AsyncMock(return_value=extracted)) as fetch_documents, patch(
                "app.services.briefs._fetch_12_month_history", AsyncMock(return_value=[])
            ):
                first_context = await service.prepare("demo", "current")
                cached_context = await service.prepare("demo", "current")
                refreshed_context = await service.prepare("demo", "current", force_refresh=True)

            expected_urls = [second.url]
            self.assertEqual([item.url for item in first_context.source_documents], expected_urls)
            self.assertEqual([item.url for item in cached_context.source_documents], expected_urls)
            self.assertEqual([item.url for item in refreshed_context.source_documents], expected_urls)
            self.assertEqual(first_context.available_document_count, 3)
            self.assertEqual(first_context.analyzed_document_count, 1)
            self.assertEqual(first_context.readable_document_count, 1)
            self.assertEqual(first_context.unreadable_document_labels, [third.label])
            self.assertEqual(details_service.get_details.await_count, 2)
            self.assertEqual(fetch_documents.await_count, 2)


if __name__ == "__main__":
    unittest.main()
