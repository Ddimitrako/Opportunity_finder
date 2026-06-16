from __future__ import annotations

import json

import httpx

from app.config import Settings
from app.models import Opportunity


class AIEnricher:
    def __init__(self, settings: Settings):
        self.settings = settings

    @property
    def enabled(self) -> bool:
        return bool(self.settings.openai_api_key)

    async def enrich(self, opportunity: Opportunity) -> Opportunity:
        if not self.enabled:
            return opportunity

        prompt = {
            "task": "Summarize this public procurement opportunity for a small full-stack software vendor in Greece.",
            "return": "A concise Greek paragraph with fit, risk, and next action.",
            "opportunity": opportunity.model_dump(exclude={"source_payload"}),
        }
        payload = {
            "model": self.settings.openai_model,
            "input": json.dumps(prompt, ensure_ascii=False),
            "temperature": 0.2,
        }
        headers = {
            "Authorization": f"Bearer {self.settings.openai_api_key}",
            "Content-Type": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=25) as client:
                response = await client.post("https://api.openai.com/v1/responses", json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
        except Exception as exc:
            opportunity.red_flags.append(f"AI enrichment failed: {exc.__class__.__name__}")
            return opportunity

        text = _extract_output_text(data)
        if text:
            opportunity.ai_summary = text
        return opportunity


def _extract_output_text(payload: dict) -> str | None:
    if isinstance(payload.get("output_text"), str):
        return payload["output_text"].strip()
    for output in payload.get("output") or []:
        for content in output.get("content") or []:
            text = content.get("text")
            if isinstance(text, str) and text.strip():
                return text.strip()
    return None
