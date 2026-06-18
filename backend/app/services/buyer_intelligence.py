from __future__ import annotations

import statistics
from datetime import date, datetime, timedelta, timezone
from typing import Any

import httpx

from app.config import Settings
from app.models import (
    BudgetProfile,
    BuyerIntelligenceRequest,
    BuyerIntelligenceResponse,
    BuyerOpportunitySample,
    DiavgeiaDecisionSignal,
    Opportunity,
    SourceName,
)
from app.normalization import collect_cpv_codes, extract_records, first_text, parse_date
from app.sources.khmdhs import KhmdhsClient


SOFTWARE_CPV_PREFIXES = ("72", "48")
SMALL_SOFTWARE_BUDGET_MAX = 100_000
CPV_CATEGORY_PREFIXES = (
    ("software", ("48", "72")),
    ("food-catering", ("15", "55")),
    ("it-equipment-maintenance", ("30", "32", "50")),
    ("transport-logistics", ("34", "60", "63")),
    ("security-defence", ("35",)),
    ("laboratory-measurement", ("38",)),
    ("furniture-facilities", ("39",)),
    ("industrial-equipment", ("42", "43")),
    ("construction-works", ("44", "45")),
    ("financial-insurance", ("66",)),
    ("engineering-technical", ("71",)),
    ("research-consulting", ("73",)),
    ("business-services", ("79",)),
    ("training-education", ("80",)),
    ("health-social-care", ("85",)),
    ("waste-environment", ("90",)),
    ("culture-recreation", ("92",)),
)
SOFTWARE_PACKAGE_LABELS = {
    "Public Applications Platform",
    "Field Monitoring & Reporting App",
    "Cultural / Multimedia Digital Experience",
    "Dashboard & Data Intelligence",
    "Document & Case Management",
}
SOFTWARE_TERMS = (
    "software",
    "λογισμ",
    "πληροφοριακ",
    "πλατφόρ",
    "πλατφορ",
    "εφαρμογ",
    "web",
    "portal",
    "dashboard",
    "ψηφιακ",
)


class BuyerIntelligenceService:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def analyze(self, request: BuyerIntelligenceRequest) -> BuyerIntelligenceResponse:
        buyer = request.buyer.strip()
        market = _dedupe_by_id([*request.market_opportunities, *([request.opportunity] if request.opportunity else [])])
        visible_buyer_items = [item for item in market if _same_buyer(item.buyer, buyer)]
        khmdhs_org_key = _khmdhs_org_key([*visible_buyer_items, *([request.opportunity] if request.opportunity else [])], buyer)
        khmdhs_history: list[Opportunity] = []
        khmdhs_awards: list[DiavgeiaDecisionSignal] = []
        khmdhs_history_status = "skipped"
        khmdhs_history_message: str | None = None
        khmdhs_history_date_from: date | None = None
        khmdhs_history_date_to: date | None = None
        if khmdhs_org_key and request.history_days > 0 and request.history_limit > 0:
            khmdhs_history_date_to = date.today()
            khmdhs_history_date_from = khmdhs_history_date_to - timedelta(days=request.history_days)
            try:
                khmdhs_history = await self._khmdhs_history(khmdhs_org_key, request.history_days, request.history_limit)
                khmdhs_history_status = "ok"
                if not khmdhs_history:
                    khmdhs_history_message = "No KIMDIS historical records returned for this organization key."
            except Exception as exc:
                khmdhs_history_status = "error"
                khmdhs_history_message = f"KIMDIS history lookup failed: {exc.__class__.__name__}"
            if khmdhs_history_status == "ok":
                try:
                    khmdhs_awards = await self._khmdhs_awards(khmdhs_org_key, request.history_days, min(10, request.history_limit))
                except Exception as exc:
                    award_message = f"KIMDIS award lookup failed: {exc.__class__.__name__}"
                    khmdhs_history_message = f"{khmdhs_history_message} {award_message}".strip() if khmdhs_history_message else award_message
        elif request.history_days > 0 and request.history_limit > 0:
            khmdhs_history_message = "No KIMDIS organization key available for this buyer in the current data."

        buyer_items = _dedupe_by_id([*visible_buyer_items, *khmdhs_history])
        budget_profile = _budget_profile([item.budget for item in buyer_items if item.budget is not None])
        current = request.opportunity
        similar = _similar_opportunities(buyer_items, current)
        recent = sorted(buyer_items, key=lambda item: item.published_at or date.min, reverse=True)[:5]

        diavgeia_status = "skipped"
        diavgeia_message: str | None = None
        diavgeia_decisions: list[DiavgeiaDecisionSignal] = []
        if request.diavgeia_limit > 0:
            try:
                diavgeia_decisions = await self._diavgeia_search(buyer, request.diavgeia_limit)
                diavgeia_status = "ok"
                if not diavgeia_decisions:
                    diavgeia_message = "No Diavgeia decisions returned for this buyer term."
            except Exception as exc:
                diavgeia_status = "error"
                diavgeia_message = f"Diavgeia lookup failed: {exc.__class__.__name__}"

        winner_signals = [decision for decision in diavgeia_decisions if decision.winner_name or decision.amount is not None][:5]
        winner_signals = [*khmdhs_awards[:5], *winner_signals][:8]
        has_similar = bool(similar) or any(decision.similar_to_software for decision in diavgeia_decisions)
        has_similar = has_similar or any(decision.similar_to_software for decision in khmdhs_awards)
        source_counts = _source_counts(buyer_items)
        confidence_notes = _confidence_notes(market, visible_buyer_items, khmdhs_history, khmdhs_org_key, khmdhs_history_status, diavgeia_status)
        insight_flags = _insight_flags(buyer_items, budget_profile, has_similar, winner_signals)
        khmdhs_result_date_from, khmdhs_result_date_to = _published_date_range(khmdhs_history)

        return BuyerIntelligenceResponse(
            buyer=buyer,
            generated_at=datetime.utcnow(),
            market_window_count=len(market),
            visible_buyer_opportunity_count=len(visible_buyer_items),
            history_opportunity_count=len(khmdhs_history),
            buyer_opportunity_count=len(buyer_items),
            source_counts=source_counts,
            budget_profile=budget_profile,
            small_software_count=sum(1 for item in buyer_items if _is_small_software(item)),
            current_cpv_categories=sorted(_cpv_category_keys(current.cpv_codes) if current else set()),
            khmdhs_history_date_from=khmdhs_history_date_from,
            khmdhs_history_date_to=khmdhs_history_date_to,
            khmdhs_history_result_date_from=khmdhs_result_date_from,
            khmdhs_history_result_date_to=khmdhs_result_date_to,
            similar_opportunities=[_sample(item) for item in similar[:5]],
            recent_opportunities=[_sample(item) for item in recent],
            has_similar_procurement=has_similar,
            khmdhs_history_status=khmdhs_history_status,
            khmdhs_history_message=khmdhs_history_message,
            diavgeia_status=diavgeia_status,
            diavgeia_message=diavgeia_message,
            diavgeia_decisions=[*khmdhs_awards, *diavgeia_decisions[: request.diavgeia_limit]],
            winner_signals=winner_signals,
            confidence_notes=confidence_notes,
            insight_flags=insight_flags,
        )

    async def _diavgeia_search(self, buyer: str, limit: int) -> list[DiavgeiaDecisionSignal]:
        url = f"{str(self.settings.diavgeia_base_url).rstrip('/')}/search"
        params = {"term": buyer, "size": limit, "page": 0, "sort": "recent"}
        async with httpx.AsyncClient(timeout=self.settings.diavgeia_timeout_seconds) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            payload = response.json()
        return [_decision_signal(record) for record in extract_records(payload)]

    async def _khmdhs_history(self, organization_key: str, days: int, limit: int) -> list[Opportunity]:
        client = KhmdhsClient(self.settings)
        records: list[Opportunity] = []
        for endpoint in ("request", "notice"):
            for body in _khmdhs_history_bodies(organization_key, days, endpoint):
                if len(records) >= limit:
                    return _dedupe_by_id(records)
                fetched = await self._khmdhs_records(endpoint, body, page=0)
                records.extend(client._to_opportunity(record) for record in fetched[: max(0, limit - len(records))])
        return _dedupe_by_id(records)[:limit]

    async def _khmdhs_awards(self, organization_key: str, days: int, limit: int) -> list[DiavgeiaDecisionSignal]:
        signals: list[DiavgeiaDecisionSignal] = []
        for endpoint in ("auction", "contract"):
            for body in _khmdhs_history_bodies(organization_key, days, endpoint):
                if len(signals) >= limit:
                    return signals
                records = await self._khmdhs_records(endpoint, body, page=0)
                signals.extend(_khmdhs_decision_signal(record, endpoint, self.settings) for record in records[: max(0, limit - len(signals))])
        return signals[:limit]

    async def _khmdhs_records(self, endpoint: str, body: dict[str, Any], page: int) -> list[dict[str, Any]]:
        url = f"{str(self.settings.khmdhs_base_url).rstrip('/')}/khmdhs-opendata/{endpoint}"
        async with httpx.AsyncClient(
            timeout=self.settings.khmdhs_timeout_seconds,
            verify=self.settings.khmdhs_verify_ssl,
            headers={"Accept": "application/json", "Content-Type": "application/json"},
        ) as client:
            response = await client.post(url, params={"page": page}, json=body)
            if response.status_code == 404:
                return []
            response.raise_for_status()
            return extract_records(response.json())


def _dedupe_by_id(items: list[Opportunity | None]) -> list[Opportunity]:
    output: list[Opportunity] = []
    seen: set[str] = set()
    for item in items:
        if item is None or item.id in seen:
            continue
        seen.add(item.id)
        output.append(item)
    return output


def _same_buyer(left: str, right: str) -> bool:
    left_norm = _normalize_buyer(left)
    right_norm = _normalize_buyer(right)
    if not left_norm or not right_norm:
        return False
    return left_norm == right_norm or left_norm in right_norm or right_norm in left_norm


def _khmdhs_org_key(items: list[Opportunity | None], buyer: str) -> str | None:
    for item in items:
        if not item or item.source != "khmdhs" or not _same_buyer(item.buyer, buyer):
            continue
        key = first_text(item.source_payload.get("organizationKey") or item.source_payload.get("organization_key"))
        if key:
            return key
    return None


def _khmdhs_history_bodies(organization_key: str, days: int, endpoint: str) -> list[dict[str, Any]]:
    today = date.today()
    start = today - timedelta(days=days)
    bodies: list[dict[str, Any]] = []
    cursor = today
    while cursor >= start:
        chunk_start = max(start, cursor - timedelta(days=179))
        body: dict[str, Any] = {
            "organizations": [organization_key],
            "dateFrom": chunk_start.isoformat(),
            "dateTo": cursor.isoformat(),
        }
        if endpoint == "request":
            body.update({"isInitial": True, "isApproved": True, "isApproval": True})
        else:
            body.update({"totalCostFrom": 0, "totalCostTo": 1_000_000_000_000})
        bodies.append(body)
        cursor = chunk_start - timedelta(days=1)
    return bodies


def _normalize_buyer(value: str) -> str:
    return " ".join(value.casefold().replace(",", " ").split())


def _budget_profile(values: list[float]) -> BudgetProfile:
    if not values:
        return BudgetProfile()
    sorted_values = sorted(values)
    median = float(statistics.median(sorted_values))
    average = float(sum(sorted_values) / len(sorted_values))
    low = _money(sorted_values[0])
    high = _money(sorted_values[-1])
    return BudgetProfile(
        count=len(sorted_values),
        min=float(sorted_values[0]),
        max=float(sorted_values[-1]),
        average=average,
        median=median,
        typical_range=f"{low} - {high}" if low != high else low,
    )


def _source_counts(items: list[Opportunity]) -> dict[SourceName, int]:
    counts: dict[SourceName, int] = {}
    for item in items:
        counts[item.source] = counts.get(item.source, 0) + 1
    return counts


def _published_date_range(items: list[Opportunity]) -> tuple[date | None, date | None]:
    dates = sorted(item.published_at for item in items if item.published_at is not None)
    if not dates:
        return None, None
    return dates[0], dates[-1]


def _similar_opportunities(items: list[Opportunity], current: Opportunity | None) -> list[Opportunity]:
    if not current:
        return [item for item in items if _is_software_like(item)]
    current_categories = _cpv_category_keys(current.cpv_codes)
    current_family_cpvs = _cpv_prefixes(current.cpv_codes, 3)
    current_terms = _term_set(f"{current.title} {current.summary}")
    output: list[Opportunity] = []
    for item in items:
        if item.id == current.id:
            continue
        item_categories = _cpv_category_keys(item.cpv_codes)
        if current_categories and not current_categories.intersection(item_categories):
            continue
        item_family_cpvs = _cpv_prefixes(item.cpv_codes, 3)
        if current_family_cpvs and current_family_cpvs.intersection(item_family_cpvs):
            output.append(item)
            continue
        if current_categories and current_categories.intersection(item_categories):
            output.append(item)
            continue
        if not current_categories and current_terms and current_terms.intersection(_term_set(f"{item.title} {item.summary}")):
            output.append(item)
    return sorted(output, key=lambda item: (item.fit_score, item.published_at or date.min), reverse=True)


def _term_set(text: str) -> set[str]:
    lowered = text.casefold()
    return {term for term in SOFTWARE_TERMS if term in lowered}


def _is_software_like(item: Opportunity) -> bool:
    if any(prefix.startswith(SOFTWARE_CPV_PREFIXES) for prefix in _cpv_prefixes(item.cpv_codes, 2)):
        return True
    if item.package_match in SOFTWARE_PACKAGE_LABELS:
        return True
    return bool(_term_set(f"{item.title} {item.summary}"))


def _is_small_software(item: Opportunity) -> bool:
    return _is_software_like(item) and item.budget is not None and item.budget <= SMALL_SOFTWARE_BUDGET_MAX


def _cpv_prefixes(cpv_codes: list[str], length: int) -> set[str]:
    prefixes: set[str] = set()
    for code in cpv_codes:
        digits = "".join(char for char in code if char.isdigit())
        if len(digits) >= length:
            prefixes.add(digits[:length])
    return prefixes


def _cpv_category_keys(cpv_codes: list[str]) -> set[str]:
    categories: set[str] = set()
    prefixes = _cpv_prefixes(cpv_codes, 2)
    for category, category_prefixes in CPV_CATEGORY_PREFIXES:
        if any(prefix.startswith(category_prefixes) for prefix in prefixes):
            categories.add(category)
    return categories


def _sample(item: Opportunity) -> BuyerOpportunitySample:
    return BuyerOpportunitySample(
        id=item.id,
        title=item.title,
        source=item.source,
        source_label=item.source_label,
        budget=item.budget,
        published_at=item.published_at,
        deadline=item.deadline,
        cpv_codes=item.cpv_codes,
        fit_score=item.fit_score,
        package_match=item.package_match,
        url=item.url,
    )


def _decision_signal(record: dict[str, Any]) -> DiavgeiaDecisionSignal:
    extra = record.get("extraFieldValues") if isinstance(record.get("extraFieldValues"), dict) else {}
    amount_value = extra.get("awardAmount") if isinstance(extra.get("awardAmount"), dict) else {}
    amount = amount_value.get("amount") if isinstance(amount_value, dict) else None
    currency = first_text(amount_value.get("currency"), "EUR") if isinstance(amount_value, dict) else "EUR"
    cpv_codes = collect_cpv_codes(record)
    if not cpv_codes and isinstance(extra, dict):
        cpv_codes = collect_cpv_codes(extra)
    subject = first_text(record.get("subject"), "Diavgeia decision")
    winner_name = _winner_name(extra)
    published_at = _timestamp_date(record.get("publishTimestamp") or record.get("submissionTimestamp")) or parse_date(record.get("issueDate"))
    return DiavgeiaDecisionSignal(
        source_label="Diavgeia",
        ada=first_text(record.get("ada")) or None,
        subject=subject,
        decision_type=first_text(record.get("decisionTypeId")) or None,
        published_at=published_at,
        amount=float(amount) if amount not in (None, "") else None,
        currency=currency or "EUR",
        winner_name=winner_name,
        cpv_codes=cpv_codes,
        url=first_text(record.get("url")) or None,
        document_url=first_text(record.get("documentUrl")) or None,
        similar_to_software=_looks_software(subject, cpv_codes),
    )


def _khmdhs_decision_signal(record: dict[str, Any], endpoint: str, settings: Settings) -> DiavgeiaDecisionSignal:
    reference = first_text(record.get("referenceNumber")) or None
    subject = first_text(record.get("title"), "KIMDIS decision")
    cpv_codes = collect_cpv_codes(record)
    amount = _record_budget(record)
    document_url = None
    if reference:
        document_url = f"{str(settings.khmdhs_base_url).rstrip('/')}/khmdhs-opendata/{endpoint}/attachment/{reference}"
    return DiavgeiaDecisionSignal(
        source_label="KIMDIS",
        ada=reference,
        subject=subject,
        decision_type=endpoint,
        published_at=parse_date(record.get("submissionDate") or record.get("signedDate")),
        amount=amount,
        currency="EUR",
        winner_name=_contractor_name(record),
        cpv_codes=cpv_codes,
        url=document_url,
        document_url=document_url,
        similar_to_software=_looks_software(subject, cpv_codes),
    )


def _record_budget(record: dict[str, Any]) -> float | None:
    for key in ("totalCostWithoutVAT", "totalCostWithVAT", "budget", "contractBudget", "contractValue", "amount"):
        value = record.get(key)
        if value not in (None, ""):
            try:
                return float(value)
            except (TypeError, ValueError):
                continue
    return None


def _contractor_name(record: dict[str, Any]) -> str | None:
    for key in ("contractorName", "contractor", "supplierName", "vendorName", "awardee", "economicOperator"):
        text = first_text(record.get(key))
        if text:
            return text
    for key in ("contractors", "suppliers", "economicOperators"):
        value = record.get(key)
        if isinstance(value, list) and value:
            text = first_text(value[0])
            if text:
                return text
    contracting_data = record.get("contractingDataDetails")
    if isinstance(contracting_data, dict):
        members = contracting_data.get("contractingMembersDataList")
        if isinstance(members, list) and members:
            text = first_text(members[0].get("name") if isinstance(members[0], dict) else members[0])
            if text:
                return text
    return None


def _winner_name(extra: dict[str, Any]) -> str | None:
    for key in ("person", "sponsor", "contractor", "recipient"):
        values = extra.get(key)
        if isinstance(values, list) and values:
            return first_text(values[0].get("name") if isinstance(values[0], dict) else values[0]) or None
        if isinstance(values, dict):
            return first_text(values.get("name")) or None
    return None


def _timestamp_date(value: Any) -> date | None:
    if not value:
        return None
    try:
        timestamp = int(value)
    except (TypeError, ValueError):
        return None
    if timestamp > 10_000_000_000:
        timestamp = timestamp // 1000
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).date()


def _looks_software(subject: str, cpv_codes: list[str]) -> bool:
    if any(code.startswith(SOFTWARE_CPV_PREFIXES) for code in cpv_codes):
        return True
    return bool(_term_set(subject))


def _confidence_notes(
    market: list[Opportunity],
    visible_buyer_items: list[Opportunity],
    khmdhs_history: list[Opportunity],
    khmdhs_org_key: str | None,
    khmdhs_status: str,
    diavgeia_status: str,
) -> list[str]:
    notes = [
        "Visible stats come from the currently loaded opportunity window.",
    ]
    if khmdhs_status == "ok":
        notes.append("KIMDIS historical stats include buyer records fetched by organization key in 180-day API windows.")
    elif khmdhs_org_key is None:
        notes.append("KIMDIS historical lookup needs an organization key; open a KIMDIS result for this buyer to improve coverage.")
    elif khmdhs_status == "error":
        notes.append("KIMDIS historical lookup failed, so counts may rely on visible rows only.")
    if not visible_buyer_items and not khmdhs_history:
        notes.append("No matching buyer rows were found in the current window.")
    if diavgeia_status == "ok":
        notes.append("Diavgeia signals are best-effort search results by buyer name.")
    elif diavgeia_status == "error":
        notes.append("Diavgeia lookup failed, so winner signals may be missing.")
    if len(market) >= 100:
        notes.append("The market window is capped by the current source limit.")
    return notes


def _insight_flags(
    buyer_items: list[Opportunity],
    budget_profile: BudgetProfile,
    has_similar: bool,
    winner_signals: list[DiavgeiaDecisionSignal],
) -> list[str]:
    flags: list[str] = []
    if len(buyer_items) >= 3:
        flags.append("Repeat buyer in the current results.")
    if budget_profile.median is not None and budget_profile.median <= SMALL_SOFTWARE_BUDGET_MAX:
        flags.append("Typical visible budget is small-team friendly.")
    if any(_is_small_software(item) for item in buyer_items):
        flags.append("Has visible small software-style opportunities.")
    if has_similar:
        flags.append("Similar procurement signal found.")
    if winner_signals:
        flags.append("Diavgeia award/winner signals available.")
    return flags or ["Not enough buyer history in the current window yet."]


def _money(value: float) -> str:
    return f"{value:,.0f} EUR".replace(",", ".")
