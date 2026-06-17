from __future__ import annotations

import io
import json
import re
import sqlite3
from contextlib import closing
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

import httpx

from app.config import Settings
from app.models import DocumentBrief, DocumentBriefResponse, DocumentLink, OpportunityDetails, SourceName
from app.services.bookmarks import _resolve_db_path
from app.services.details import OpportunityDetailsService

MAX_DOCUMENTS = 4
MAX_DOCUMENT_CHARS = 42_000
MAX_DOCUMENT_BYTES = 8_000_000


class DocumentBriefService:
    def __init__(self, settings: Settings, details_service: OpportunityDetailsService | None = None):
        self.settings = settings
        self.details_service = details_service or OpportunityDetailsService(settings)
        self.db_path = _resolve_db_path(Path(settings.bookmark_db_path))
        self._init_db()

    def get_cached_brief(self, source: SourceName, reference: str) -> DocumentBriefResponse:
        row = self._get_row(source, reference)
        if not row:
            return DocumentBriefResponse(brief=None, cached=False, message="No saved AI brief yet.")
        brief = _row_to_brief(row)
        brief.cached = True
        return DocumentBriefResponse(brief=brief, cached=True)

    async def generate_brief(self, source: SourceName, reference: str) -> DocumentBriefResponse:
        cached = self.get_cached_brief(source, reference)
        if cached.brief:
            return cached
        if not self.settings.openai_api_key:
            return DocumentBriefResponse(
                brief=None,
                cached=False,
                message="OPENAI_API_KEY is not configured. Add it to .env.local, then click the pink AI brief button again.",
            )

        details = await self.details_service.get_details(source, reference)
        document_texts = await _fetch_document_texts(details.documents)
        brief = await self._call_openai(details, document_texts)
        self._save_brief(brief)
        return DocumentBriefResponse(brief=brief, cached=False)

    async def _call_openai(self, details: OpportunityDetails, document_texts: list[dict[str, str]]) -> DocumentBrief:
        prompt = {
            "role": "You help a beginner Greek software vendor decide whether to pursue a public procurement opportunity.",
            "language": "Greek",
            "task": "Read the source metadata and available document text. Return only valid JSON with the requested keys.",
            "schema": {
                "project_summary": "2-4 short Greek sentences explaining what the project asks for.",
                "actionable": "yes | no | maybe | unknown",
                "deadline_submission": "Clear deadline/submission method summary, or Unknown.",
                "required_documents": ["Legal/company documents, declarations, certificates, guarantees, etc."],
                "technical_requirements": ["Main technical requirements or deliverables."],
                "red_flags": ["Risks, missing data, expired deadline, vague scope, short window, unclear submission."],
                "recommendation": "να ασχοληθώ; ναι/όχι/ίσως, with one concise reason.",
                "next_steps": ["Practical next steps before bidding."],
            },
            "details": details.model_dump(mode="json", exclude={"raw"}),
            "raw_metadata": details.raw,
            "documents": document_texts,
        }
        payload = {
            "model": self.settings.openai_model,
            "input": json.dumps(prompt, ensure_ascii=False),
            "temperature": 0.1,
        }
        headers = {
            "Authorization": f"Bearer {self.settings.openai_api_key}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post("https://api.openai.com/v1/responses", json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

        parsed = _parse_json_object(_extract_output_text(data) or "")
        source_documents = details.documents[:MAX_DOCUMENTS]
        return DocumentBrief(
            source=details.source,
            reference=details.reference,
            project_summary=_as_text(parsed.get("project_summary"), "No summary returned."),
            actionable=_as_verdict(parsed.get("actionable")),
            deadline_submission=_as_text(parsed.get("deadline_submission"), "Unknown"),
            required_documents=_as_list(parsed.get("required_documents")),
            technical_requirements=_as_list(parsed.get("technical_requirements")),
            red_flags=_as_list(parsed.get("red_flags")),
            recommendation=_as_text(parsed.get("recommendation"), "Maybe"),
            next_steps=_as_list(parsed.get("next_steps")),
            source_documents=source_documents,
            generated_at=datetime.utcnow(),
            model=self.settings.openai_model,
            cached=False,
        )

    def _get_row(self, source: SourceName, reference: str) -> sqlite3.Row | None:
        with closing(self._connect()) as connection:
            return connection.execute(
                """
                SELECT source, reference, brief_json, created_at, updated_at
                FROM document_briefs
                WHERE source = ? AND reference = ?
                """,
                (source, reference),
            ).fetchone()

    def _save_brief(self, brief: DocumentBrief) -> None:
        now = datetime.utcnow().isoformat()
        payload = json.dumps(brief.model_dump(mode="json"), ensure_ascii=False)
        with closing(self._connect()) as connection:
            with connection:
                connection.execute(
                    """
                    INSERT INTO document_briefs (source, reference, brief_json, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(source, reference) DO UPDATE SET
                        brief_json = excluded.brief_json,
                        updated_at = excluded.updated_at
                    """,
                    (brief.source, brief.reference, payload, now, now),
                )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _init_db(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as connection:
            with connection:
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS document_briefs (
                        source TEXT NOT NULL,
                        reference TEXT NOT NULL,
                        brief_json TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        PRIMARY KEY (source, reference)
                    )
                    """
                )


async def _fetch_document_texts(documents: list[DocumentLink]) -> list[dict[str, str]]:
    results: list[dict[str, str]] = []
    async with httpx.AsyncClient(timeout=35, follow_redirects=True) as client:
        for document in documents[:MAX_DOCUMENTS]:
            try:
                response = await client.get(document.url, headers={"Accept": "application/pdf,text/html,text/plain,application/xml,*/*"})
                response.raise_for_status()
                content_type = response.headers.get("content-type", "")
                text = _extract_document_text(response.content[:MAX_DOCUMENT_BYTES], content_type, document.url)
            except Exception as exc:
                text = f"Could not read document automatically: {exc.__class__.__name__}"
            results.append(
                {
                    "label": document.label,
                    "type": document.document_type,
                    "reference": document.reference or "",
                    "url": document.url,
                    "text": text[:MAX_DOCUMENT_CHARS],
                }
            )
    return results


def _extract_document_text(content: bytes, content_type: str, url: str) -> str:
    lower_url = url.lower()
    lower_type = content_type.lower()
    if "pdf" in lower_type or lower_url.endswith(".pdf"):
        return _extract_pdf_text(content)
    text = content.decode("utf-8", errors="ignore")
    if "html" in lower_type or "<html" in text[:500].casefold():
        return _strip_html(text)
    return re.sub(r"\s+", " ", text).strip()


def _extract_pdf_text(content: bytes) -> str:
    try:
        from pypdf import PdfReader
    except Exception:
        return "PDF document detected, but pypdf is not installed. Install backend requirements to enable PDF text extraction."

    reader = PdfReader(io.BytesIO(content))
    parts: list[str] = []
    for page in reader.pages[:12]:
        parts.append(page.extract_text() or "")
        if sum(len(part) for part in parts) >= MAX_DOCUMENT_CHARS:
            break
    return re.sub(r"\s+", " ", "\n".join(parts)).strip() or "PDF text could not be extracted automatically."


class _HTMLTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        if data.strip():
            self.parts.append(data.strip())


def _strip_html(text: str) -> str:
    parser = _HTMLTextExtractor()
    parser.feed(text)
    return re.sub(r"\s+", " ", " ".join(parser.parts)).strip()


def _parse_json_object(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
    if match:
        cleaned = match.group(0)
    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError:
        return {"project_summary": text, "actionable": "unknown", "recommendation": "Maybe"}
    return payload if isinstance(payload, dict) else {}


def _extract_output_text(payload: dict) -> str | None:
    if isinstance(payload.get("output_text"), str):
        return payload["output_text"].strip()
    for output in payload.get("output") or []:
        for content in output.get("content") or []:
            text = content.get("text")
            if isinstance(text, str) and text.strip():
                return text.strip()
    return None


def _as_text(value: Any, fallback: str) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    if value is None:
        return fallback
    return str(value).strip() or fallback


def _as_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _as_verdict(value: Any) -> str:
    verdict = str(value or "").strip().casefold()
    return verdict if verdict in {"yes", "no", "maybe", "unknown"} else "unknown"


def _row_to_brief(row: sqlite3.Row) -> DocumentBrief:
    return DocumentBrief.model_validate(json.loads(str(row["brief_json"])))
