from __future__ import annotations

import asyncio
import time
from datetime import date, datetime, timedelta

from app.config import Settings
from app.models import (
    ActivityRequest,
    ActivityResponse,
    DailyActivity,
    Opportunity,
    ProcurementSearchRequest,
    SearchResponse,
    SourceName,
    SourceRun,
)
from app.scoring import score_opportunity
from app.services.ai import AIEnricher
from app.sources.demo import demo_opportunities
from app.sources.khmdhs import KhmdhsClient
from app.sources.ted import TedClient


class OpportunityService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.ai = AIEnricher(settings)

    async def search(self, request: ProcurementSearchRequest) -> SearchResponse:
        source_runs: list[SourceRun] = []
        tasks = [self._run_source(source, request) for source in request.sources if source != "demo"]
        results = await asyncio.gather(*tasks) if tasks else []

        opportunities: list[Opportunity] = []
        for run, items in results:
            source_runs.append(run)
            opportunities.extend(items)

        if "demo" in request.sources or (request.include_demo_when_empty and not opportunities):
            demo_items = demo_opportunities()
            source_runs.append(SourceRun(source="demo", status="ok", items=len(demo_items), elapsed_ms=0))
            opportunities.extend(demo_items)

        deduped = _dedupe(opportunities)
        filtered = _filter_opportunities(deduped, request)
        shown_by_source = _count_by_source(filtered)
        source_runs = [
            run.model_copy(update={"shown": shown_by_source.get(run.source, 0)})
            for run in source_runs
        ]
        scored = [score_opportunity(item, request) for item in filtered]
        scored.sort(key=lambda item: (item.fit_score, item.budget or 0), reverse=True)
        scored = scored[: request.limit]

        if request.use_ai and self.ai.enabled:
            scored = await asyncio.gather(*(self.ai.enrich(item) for item in scored[:8])) + scored[8:]

        return SearchResponse(
            generated_at=datetime.utcnow(),
            query=request,
            opportunities=scored,
            source_runs=source_runs,
            stats=_stats(scored),
            ai_enabled=self.ai.enabled,
        )

    async def activity(self, request: ActivityRequest) -> ActivityResponse:
        today = date.today()
        date_to = today
        date_from = today - timedelta(days=request.days - 1)
        source_runs: list[SourceRun] = []
        tasks = [
            self._run_activity_source(source, date_from, date_to, request.limit)
            for source in request.sources
            if source != "demo"
        ]
        results = await asyncio.gather(*tasks) if tasks else []

        items: list[Opportunity] = []
        for run, source_items in results:
            source_runs.append(run)
            items.extend(source_items)

        if "demo" in request.sources:
            demo_items = [
                item
                for item in demo_opportunities()
                if item.published_at is not None and date_from <= item.published_at <= date_to
            ]
            source_runs.append(
                SourceRun(source="demo", status="ok", items=len(demo_items), shown=len(demo_items), elapsed_ms=0)
            )
            items.extend(demo_items)

        daily_activity = _daily_activity(items, request.sources, today, request.days)
        return ActivityResponse(
            generated_at=datetime.utcnow(),
            date_from=date_from,
            date_to=date_to,
            daily_activity=daily_activity,
            source_runs=source_runs,
            total=sum(day.total for day in daily_activity),
        )

    async def _run_source(
        self, source: SourceName, request: ProcurementSearchRequest
    ) -> tuple[SourceRun, list[Opportunity]]:
        started = time.perf_counter()
        try:
            if source == "khmdhs":
                items = await KhmdhsClient(self.settings).search(request)
            elif source == "ted":
                items = await TedClient(self.settings).search(request)
            else:
                items = []
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            return SourceRun(source=source, status="ok", items=len(items), elapsed_ms=elapsed_ms), items
        except Exception as exc:
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            return (
                SourceRun(source=source, status="error", items=0, elapsed_ms=elapsed_ms, error=str(exc)[:240]),
                [],
            )

    async def _run_activity_source(
        self, source: SourceName, date_from: date, date_to: date, limit: int
    ) -> tuple[SourceRun, list[Opportunity]]:
        started = time.perf_counter()
        try:
            if source == "khmdhs":
                items = await KhmdhsClient(self.settings).activity(date_from, date_to, limit)
            elif source == "ted":
                items = await TedClient(self.settings).activity(date_from, date_to, limit)
            else:
                items = []
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            return (
                SourceRun(source=source, status="ok", items=len(items), shown=len(items), elapsed_ms=elapsed_ms),
                items,
            )
        except Exception as exc:
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            return (
                SourceRun(source=source, status="error", items=0, shown=0, elapsed_ms=elapsed_ms, error=str(exc)[:240]),
                [],
            )


def _dedupe(items: list[Opportunity]) -> list[Opportunity]:
    seen: set[str] = set()
    output: list[Opportunity] = []
    for item in items:
        key = f"{item.source}:{item.title.casefold()}:{item.buyer.casefold()}"
        if key in seen:
            continue
        seen.add(key)
        output.append(item)
    return output


def _count_by_source(items: list[Opportunity]) -> dict[SourceName, int]:
    counts: dict[SourceName, int] = {}
    for item in items:
        counts[item.source] = counts.get(item.source, 0) + 1
    return counts


def _daily_activity(
    items: list[Opportunity], sources: list[SourceName], today: date, days: int
) -> list[DailyActivity]:
    selected_sources = [source for source in sources if source != "demo"]
    if "demo" in sources:
        selected_sources.append("demo")

    output: list[DailyActivity] = []
    labels = ["today", "yesterday", "day_before_yesterday"]
    for day_index in range(days):
        day = today - timedelta(days=day_index)
        by_source = {source: 0 for source in selected_sources}
        for item in items:
            if item.published_at != day:
                continue
            by_source[item.source] = by_source.get(item.source, 0) + 1
        output.append(
            DailyActivity(
                date=day,
                label=labels[day_index] if day_index < len(labels) else f"{day_index}_days_ago",
                total=sum(by_source.values()),
                by_source=by_source,
            )
        )
    return output


def _filter_opportunities(items: list[Opportunity], request: ProcurementSearchRequest) -> list[Opportunity]:
    if request.show_all_fetched:
        return items

    output: list[Opportunity] = []
    for item in items:
        if item.published_at is not None and not (request.date_from <= item.published_at <= request.date_to):
            continue
        if item.published_at is None and request.only_open:
            continue
        if request.only_open:
            if item.deadline is None or item.deadline < request.deadline_after:
                continue
            if _looks_closed_or_awarded(item):
                continue
        output.append(item)
    return output


def _looks_closed_or_awarded(item: Opportunity) -> bool:
    text = " ".join(
        part
        for part in (
            item.title,
            item.summary,
            item.raw_text,
            item.procedure_type or "",
            item.status_label or "",
            item.notice_type or "",
        )
        if part
    ).casefold()
    closed_terms = (
        "contract award",
        "award notice",
        "awarded",
        "closed",
        "cancelled",
        "canceled",
        "result",
        "results",
        "σύμβαση",
        "συναφθείσα",
        "κατακύρωση",
        "κατακυρωση",
        "οριστικός ανάδοχος",
        "οριστικος αναδοχος",
        "ματαίωση",
        "ματαιωση",
        "ακύρωση",
        "ακυρωση",
        "απόφαση ανάθεσης",
        "αποφαση αναθεσης",
        "πληρωμή",
        "πληρωμη",
        "δαπάνη",
        "δαπανη",
    )
    return any(term in text for term in closed_terms)


def _stats(items: list[Opportunity]) -> dict:
    total_budget = sum(item.budget or 0 for item in items)
    by_band: dict[str, int] = {}
    by_package: dict[str, int] = {}
    for item in items:
        by_band[item.fit_band] = by_band.get(item.fit_band, 0) + 1
        by_package[item.package_match] = by_package.get(item.package_match, 0) + 1
    return {
        "total": len(items),
        "bid_candidates": sum(1 for item in items if item.fit_score >= 80),
        "worth_reading": sum(1 for item in items if item.fit_score >= 60),
        "total_budget": total_budget,
        "average_score": round(sum(item.fit_score for item in items) / len(items), 1) if items else 0,
        "by_band": by_band,
        "by_package": by_package,
    }
