from __future__ import annotations

import hashlib
import re
from datetime import date, datetime
from typing import Any


def stable_id(*parts: object) -> str:
    raw = "|".join(str(part or "") for part in parts)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:14]


def first_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    if isinstance(value, str):
        return value.strip() or default
    if isinstance(value, dict):
        for key in ("value", "name", "title", "text", "label", "eng", "ell"):
            text = first_text(value.get(key))
            if text:
                return text
    if isinstance(value, list):
        for item in value:
            text = first_text(item)
            if text:
                return text
    return str(value).strip() or default


def parse_date(value: Any) -> date | None:
    if not value:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    text = str(value).strip()
    if not text:
        return None
    if re.match(r"^\d{4}-\d{2}-\d{2}", text):
        try:
            return date.fromisoformat(text[:10])
        except ValueError:
            pass
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%d/%m/%Y"):
        try:
            return datetime.strptime(text[:26], fmt).date()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def cpv_key(value: Any) -> str | None:
    text = first_text(value)
    match = re.search(r"\b(\d{8}-\d|\d{8})\b", text)
    if not match:
        return None
    code = match.group(1)
    return code if "-" in code else f"{code[:8]}"


def collect_cpv_codes(record: dict[str, Any]) -> list[str]:
    candidates: list[Any] = []
    for key in ("cpv", "cpvs", "cpvCodes", "cpvItems", "classification-cpv", "classificationCpv"):
        if key in record:
            candidates.append(record[key])

    for detail in record.get("objectDetails") or []:
        if isinstance(detail, dict):
            candidates.extend([detail.get("cpvs"), detail.get("cpv")])

    found: list[str] = []

    def visit(value: Any) -> None:
        if value is None:
            return
        if isinstance(value, list):
            for item in value:
                visit(item)
            return
        if isinstance(value, dict):
            code = cpv_key(value.get("key") or value.get("id") or value.get("code") or value.get("value"))
            if code and code not in found:
                found.append(code)
            for child in value.values():
                visit(child)
            return
        code = cpv_key(value)
        if code and code not in found:
            found.append(code)

    for candidate in candidates:
        visit(candidate)
    return found


def extract_records(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []
    for key in ("content", "notices", "results", "items", "data", "records"):
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
        if isinstance(value, dict):
            nested = extract_records(value)
            if nested:
                return nested
    return [payload] if payload else []


def truncate(text: str, limit: int = 260) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1].rstrip() + "..."
