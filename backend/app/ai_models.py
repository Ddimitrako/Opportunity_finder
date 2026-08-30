from __future__ import annotations

from typing import Any

from app.config import Settings
from app.models import AIModelOption


AI_MODEL_CATALOG: tuple[AIModelOption, ...] = (
    AIModelOption(
        id="gpt-4o-mini",
        label="GPT-4o mini",
        description="Πολύ οικονομικό για ταξινόμηση, tagging και structured screening.",
        quality="Economy",
    ),
    AIModelOption(
        id="gpt-4.1-mini",
        label="GPT-4.1 mini",
        description="Γρήγορο και οικονομικό για καθημερινές ερωτήσεις.",
        quality="Fast",
    ),
    AIModelOption(
        id="gpt-4.1",
        label="GPT-4.1",
        description="Ισχυρό non-reasoning model με χαμηλότερη καθυστέρηση.",
        quality="Strong",
    ),
    AIModelOption(
        id="gpt-5.6-luna",
        label="GPT-5.6 Luna",
        description="Οικονομικό model για bulk screening και υψηλό throughput.",
        quality="Economy",
    ),
    AIModelOption(
        id="gpt-5.6-terra",
        label="GPT-5.6 Terra",
        description="Ισορροπία βαθύτερης ανάλυσης, ταχύτητας και κόστους.",
        quality="Balanced",
        recommended=True,
    ),
    AIModelOption(
        id="gpt-5.5",
        label="GPT-5.5",
        description="Frontier reasoning για σύνθετη επαγγελματική ανάλυση.",
        quality="Deep",
    ),
    AIModelOption(
        id="gpt-5.6-sol",
        label="GPT-5.6 Sol",
        description="Μέγιστη ποιότητα για τα δυσκολότερα opportunities.",
        quality="Best",
    ),
)

ALLOWED_AI_MODELS = {item.id for item in AI_MODEL_CATALOG} | {"gpt-5.6"}
FALLBACK_AI_MODEL = "gpt-4.1-mini"


class UnsupportedAIModelError(ValueError):
    pass


def resolve_ai_model(settings: Settings, requested_model: str | None = None) -> str:
    model = requested_model.strip() if requested_model else default_ai_model(settings)
    if model not in ALLOWED_AI_MODELS:
        raise UnsupportedAIModelError(f"Unsupported AI model: {model}")
    return model


def default_ai_model(settings: Settings) -> str:
    configured = (settings.openai_model or FALLBACK_AI_MODEL).strip()
    return configured if configured in ALLOWED_AI_MODELS else FALLBACK_AI_MODEL


def model_request_options(model: str, *, temperature: float) -> dict[str, Any]:
    if model.startswith("gpt-5"):
        return {"reasoning": {"effort": "medium"}}
    return {"temperature": temperature}
