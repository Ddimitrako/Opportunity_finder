from __future__ import annotations

import asyncio
import json
import sqlite3
import time
from contextlib import closing
from datetime import date, datetime, timedelta
from pathlib import Path

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
from app.services.bookmarks import _resolve_db_path
from app.services.pursuits import PursuitAssessmentService, PursuitSettingsService
from app.services.software_matching import SoftwareMatchingService
from app.sources.demo import demo_opportunities
from app.sources.khmdhs import KhmdhsClient
from app.sources.ted import TedClient


class OpportunityService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.db_path = _resolve_db_path(Path(settings.bookmark_db_path))
        self.software_matching = SoftwareMatchingService()
        self.pursuit_assessment = PursuitAssessmentService()
        self.pursuit_settings = PursuitSettingsService(settings)
        self._init_activity_cache()

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
        scored = self.apply_pursuit_assessment([
            self.software_matching.apply(score_opportunity(item, request))
            for item in filtered
        ])
        verdict_order = {"pursue": 2, "review": 1, "skip": 0}
        scored.sort(
            key=lambda item: (
                verdict_order.get(item.pursuit_assessment.verdict if item.pursuit_assessment else "review", 0),
                item.pursuit_assessment.priority_score if item.pursuit_assessment else item.fit_score,
                item.budget or 0,
            ),
            reverse=True,
        )
        scored = scored[: request.limit]

        return SearchResponse(
            generated_at=datetime.utcnow(),
            query=request,
            opportunities=scored,
            source_runs=source_runs,
            stats=_stats(scored),
        )

    def apply_pursuit_assessment(self, opportunities: list[Opportunity]) -> list[Opportunity]:
        """Apply the saved company profile after all matching/enrichment steps."""
        profile = self.pursuit_settings.get_company_profile()
        return [self.pursuit_assessment.assess(item, profile) for item in opportunities]

    def prepare_external_candidates(
        self,
        opportunities: list[Opportunity],
        request: ProcurementSearchRequest,
    ) -> list[Opportunity]:
        """Score and match already-qualified candidates from non-procurement sources."""
        prepared = [self.software_matching.apply(score_opportunity(item, request)) for item in opportunities]
        return self.apply_pursuit_assessment(prepared)

    async def activity(self, request: ActivityRequest) -> ActivityResponse:
        today = date.today()
        date_to = today
        date_from = today - timedelta(days=request.days - 1)
        cache_key = _activity_cache_key(request.sources, request.cpv_codes)
        cached = self._get_cached_activity(today, cache_key, request.days, request.limit)
        if cached is not None:
            return cached

        source_runs: list[SourceRun] = []
        days = [date_from + timedelta(days=index) for index in range(request.days)]
        by_day: dict[date, dict[SourceName, int]] = {
            day: {source: 0 for source in request.sources if source != "demo"}
            for day in days
        }

        if "khmdhs" in request.sources:
            run, counts = await self._run_khmdhs_activity_counts(days, request.cpv_codes)
            source_runs.append(run)
            for day, total in counts.items():
                by_day.setdefault(day, {})["khmdhs"] = total

        tasks = [
            self._run_activity_source(source, date_from, date_to, request.limit, request.cpv_codes)
            for source in request.sources
            if source not in {"demo", "khmdhs"}
        ]
        results = await asyncio.gather(*tasks) if tasks else []

        for run, source_items in results:
            source_runs.append(run)
            for item in source_items:
                if item.published_at is None or item.published_at not in by_day:
                    continue
                by_day[item.published_at][item.source] = by_day[item.published_at].get(item.source, 0) + 1

        if "demo" in request.sources:
            demo_items = [
                item
                for item in demo_opportunities()
                if item.published_at is not None and date_from <= item.published_at <= date_to
            ]
            source_runs.append(
                SourceRun(source="demo", status="ok", items=len(demo_items), shown=len(demo_items), elapsed_ms=0)
            )
            for item in demo_items:
                if item.published_at is not None:
                    by_day.setdefault(item.published_at, {})["demo"] = by_day.setdefault(item.published_at, {}).get("demo", 0) + 1

        daily_activity = _daily_activity_from_counts(by_day, request.sources, today, request.days)
        response = ActivityResponse(
            generated_at=datetime.utcnow(),
            date_from=date_from,
            date_to=date_to,
            daily_activity=daily_activity,
            source_runs=source_runs,
            total=sum(day.total for day in daily_activity),
        )
        self._save_activity_cache(today, cache_key, request.days, request.limit, response)
        return response

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
                SourceRun(
                    source=source,
                    status="error",
                    items=0,
                    elapsed_ms=elapsed_ms,
                    error=(str(exc) or exc.__class__.__name__)[:240],
                ),
                [],
            )

    async def _run_activity_source(
        self, source: SourceName, date_from: date, date_to: date, limit: int, cpv_codes: list[str] | None = None
    ) -> tuple[SourceRun, list[Opportunity]]:
        started = time.perf_counter()
        try:
            if source == "khmdhs":
                items = await KhmdhsClient(self.settings).activity(date_from, date_to, limit)
            elif source == "ted":
                items = await TedClient(self.settings).activity(date_from, date_to, limit, cpv_codes)
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
                SourceRun(
                    source=source,
                    status="error",
                    items=0,
                    shown=0,
                    elapsed_ms=elapsed_ms,
                    error=(str(exc) or exc.__class__.__name__)[:240],
                ),
                [],
            )

    async def _run_khmdhs_activity_counts(self, days: list[date], cpv_codes: list[str]) -> tuple[SourceRun, dict[date, int]]:
        started = time.perf_counter()
        client = KhmdhsClient(self.settings)
        semaphore = asyncio.Semaphore(2)

        async def fetch(day: date) -> tuple[date, int, str | None]:
            async with semaphore:
                for attempt in range(3):
                    try:
                        return day, await client.activity_count(day, day, cpv_codes), None
                    except Exception as exc:
                        message = str(exc)[:240]
                        if "429" not in message or attempt == 2:
                            return day, 0, message
                        await asyncio.sleep(1.2 * (attempt + 1))
                return day, 0, "KIMDIS activity count failed"

        results = await asyncio.gather(*(fetch(day) for day in days))
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        counts = {day: total for day, total, _error in results}
        errors = [f"{day}: {error}" for day, _total, error in results if error]
        total = sum(counts.values())
        return (
            SourceRun(
                source="khmdhs",
                status="error" if errors else "ok",
                items=total,
                shown=total,
                elapsed_ms=elapsed_ms,
                error="; ".join(errors[:3]) if errors else None,
            ),
            counts,
        )

    def _get_cached_activity(
        self, run_date: date, sources_key: str, days: int, limit: int
    ) -> ActivityResponse | None:
        with closing(self._connect()) as connection:
            row = connection.execute(
                """
                SELECT response_json
                FROM smart_calendar_activity_cache
                WHERE run_date = ? AND sources_key = ? AND days = ? AND limit_count = ?
                """,
                (run_date.isoformat(), sources_key, days, limit),
            ).fetchone()
        if row is None:
            return None
        response = ActivityResponse.model_validate(json.loads(str(row["response_json"])))
        return response.model_copy(update={"cached": True})

    def _save_activity_cache(
        self, run_date: date, sources_key: str, days: int, limit: int, response: ActivityResponse
    ) -> None:
        now = datetime.utcnow().isoformat()
        payload = json.dumps(response.model_dump(mode="json"), ensure_ascii=False)
        with closing(self._connect()) as connection:
            with connection:
                connection.execute(
                    """
                    INSERT INTO smart_calendar_activity_cache (
                        run_date, sources_key, days, limit_count, response_json, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(run_date, sources_key, days, limit_count) DO UPDATE SET
                        response_json = excluded.response_json,
                        updated_at = excluded.updated_at
                    """,
                    (run_date.isoformat(), sources_key, days, limit, payload, now, now),
                )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _init_activity_cache(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as connection:
            with connection:
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS smart_calendar_activity_cache (
                        run_date TEXT NOT NULL,
                        sources_key TEXT NOT NULL,
                        days INTEGER NOT NULL,
                        limit_count INTEGER NOT NULL,
                        response_json TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        PRIMARY KEY (run_date, sources_key, days, limit_count)
                    )
                    """
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


def _activity_cache_key(sources: list[SourceName], cpv_codes: list[str] | None = None) -> str:
    source_part = ",".join(sorted(dict.fromkeys(sources)))
    cpv_part = ",".join(sorted(dict.fromkeys(cpv_codes or [])))
    return f"{source_part}|cpv:{cpv_part}"


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


def _daily_activity_from_counts(
    counts_by_day: dict[date, dict[SourceName, int]], sources: list[SourceName], today: date, days: int
) -> list[DailyActivity]:
    selected_sources = [source for source in sources if source != "demo"]
    if "demo" in sources:
        selected_sources.append("demo")

    output: list[DailyActivity] = []
    labels = ["today", "yesterday", "day_before_yesterday"]
    for day_index in range(days):
        day = today - timedelta(days=day_index)
        by_source = {source: counts_by_day.get(day, {}).get(source, 0) for source in selected_sources}
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
            if item.candidate_type == "position_early":
                output.append(item)
                continue
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
