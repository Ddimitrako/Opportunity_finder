from __future__ import annotations

import re
import statistics
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime, timezone

from app.models import (
    NeedPattern,
    NeedPatternRequest,
    NeedPatternResponse,
    Opportunity,
    PatternOpportunitySample,
    SoftwareMatch,
)


SMALL_TEAM_BUDGET_MIN = 5_000
SMALL_TEAM_BUDGET_MAX = 100_000
SWEET_SPOT_BUDGET_MIN = 10_000
SWEET_SPOT_BUDGET_MAX = 80_000


@dataclass(frozen=True)
class PatternDefinition:
    pattern_id: str
    label: str
    category: str
    recommended_package: str
    cpv_prefixes: tuple[str, ...]
    keywords: tuple[str, ...]
    package_hints: tuple[str, ...]


PATTERN_DEFINITIONS = (
    PatternDefinition(
        pattern_id="document-workflow-dms",
        label="Document workflow / DMS",
        category="Documents & workflow",
        recommended_package="DMS support and workflow dashboard package",
        cpv_prefixes=("483", "722"),
        keywords=(
            "dms",
            "document",
            "documents",
            "workflow",
            "case management",
            "protocol",
            "e-signature",
            "signatures",
            "shde",
            "side",
            "σηδε",
            "σιδε",
            "εγγραφα",
            "εγγραφων",
            "πρωτοκολλο",
            "υποθεσεων",
            "διακινηση εγγραφων",
        ),
        package_hints=("Document & Case Management",),
    ),
    PatternDefinition(
        pattern_id="dashboard-bi-reporting",
        label="Dashboards / BI reporting",
        category="Data intelligence",
        recommended_package="Dashboard and reporting implementation package",
        cpv_prefixes=("723", "722"),
        keywords=(
            "dashboard",
            "dashboards",
            "bi",
            "business intelligence",
            "report",
            "reports",
            "reporting",
            "analytics",
            "kpi",
            "statistics",
            "data analysis",
            "στατιστικα",
            "αναφορες",
            "δεικτες",
            "αναλυτικα",
        ),
        package_hints=("Dashboard & Data Intelligence",),
    ),
    PatternDefinition(
        pattern_id="portal-web-app",
        label="Portal / public web app",
        category="Public applications",
        recommended_package="Public portal and e-services workflow package",
        cpv_prefixes=("724", "722"),
        keywords=(
            "portal",
            "web app",
            "web application",
            "e-services",
            "eservices",
            "applications",
            "application form",
            "forms",
            "citizen",
            "πλατφορμα",
            "αιτησεις",
            "αιτηση",
            "δικαιολογητικα",
            "ηλεκτρονικες υπηρεσιες",
        ),
        package_hints=("Public Applications Platform",),
    ),
    PatternDefinition(
        pattern_id="cms-website-maintenance",
        label="CMS / website maintenance",
        category="Web presence",
        recommended_package="CMS maintenance and content operations package",
        cpv_prefixes=("724",),
        keywords=(
            "website",
            "site",
            "web site",
            "cms",
            "wordpress",
            "drupal",
            "joomla",
            "hosting",
            "content management",
            "maintenance",
            "ιστοσελιδα",
            "ιστοσελιδας",
            "συντηρηση ιστοσελιδας",
        ),
        package_hints=("Cultural / Multimedia Digital Experience",),
    ),
    PatternDefinition(
        pattern_id="software-support-maintenance",
        label="Software support / maintenance",
        category="Software operations",
        recommended_package="Managed software support and small enhancements retainer",
        cpv_prefixes=("7225", "72261", "72267"),
        keywords=(
            "support",
            "maintenance",
            "helpdesk",
            "technical support",
            "software support",
            "software maintenance",
            "bug fix",
            "enhancement",
            "upgrade",
            "συντηρηση",
            "τεχνικη υποστηριξη",
            "υποστηριξη",
            "καλη λειτουργια",
            "αναβαθμιση",
        ),
        package_hints=(),
    ),
    PatternDefinition(
        pattern_id="field-monitoring-reporting",
        label="Field monitoring / reporting",
        category="Field operations",
        recommended_package="Field reporting and monitoring application package",
        cpv_prefixes=("722", "723"),
        keywords=(
            "monitoring",
            "field",
            "reporting",
            "incident",
            "inspection",
            "map",
            "maps",
            "geo",
            "gis",
            "tracking",
            "παρακολουθηση",
            "πεδιο",
            "χαρτης",
            "γεω",
            "συμβαν",
            "επιθεωρηση",
        ),
        package_hints=("Field Monitoring & Reporting App",),
    ),
)


@dataclass
class PatternMatch:
    definition: PatternDefinition
    opportunity: Opportunity
    score: int
    matched_keywords: set[str]
    matched_cpv_families: set[str]


class PatternDiscoveryService:
    def discover(self, request: NeedPatternRequest) -> NeedPatternResponse:
        assigned: dict[str, PatternMatch] = {}

        for opportunity in request.opportunities:
            match = self._best_match(opportunity)
            if match is None:
                continue
            assigned[opportunity.id] = match

        grouped: dict[str, list[PatternMatch]] = {}
        for match in assigned.values():
            grouped.setdefault(match.definition.pattern_id, []).append(match)

        patterns = [
            pattern
            for matches in grouped.values()
            if (pattern := self._build_pattern(matches, request.min_opportunities)) is not None
        ]
        patterns.sort(
            key=lambda item: (
                item.productization_score,
                item.repeat_score,
                item.opportunity_count,
                item.buyer_count,
            ),
            reverse=True,
        )

        return NeedPatternResponse(
            generated_at=datetime.now(timezone.utc),
            patterns=patterns[: request.max_patterns],
            unmatched_count=max(0, len(request.opportunities) - len(assigned)),
            patternable_count=len(assigned),
        )

    def _best_match(self, opportunity: Opportunity) -> PatternMatch | None:
        matches = [match for definition in PATTERN_DEFINITIONS if (match := _match_definition(definition, opportunity))]
        if not matches:
            return None
        matches.sort(key=lambda item: (item.score, len(item.matched_keywords), len(item.matched_cpv_families)), reverse=True)
        return matches[0]

    def _build_pattern(self, matches: list[PatternMatch], min_opportunities: int) -> NeedPattern | None:
        if len(matches) < min_opportunities:
            return None

        definition = matches[0].definition
        opportunities = [match.opportunity for match in matches]
        buyers = sorted({item.buyer for item in opportunities if item.buyer and item.buyer != "Unknown buyer"})
        cpv_families = sorted({family for match in matches for family in match.matched_cpv_families})
        keywords = _top_keywords(matches)
        budgets = sorted(item.budget for item in opportunities if item.budget is not None)
        repeat_score = _repeat_score(opportunities, len(buyers))
        productization_score = _productization_score(opportunities, repeat_score, bool(cpv_families), definition)

        if productization_score < 45:
            return None

        return NeedPattern(
            pattern_id=definition.pattern_id,
            label=definition.label,
            category=definition.category,
            recommended_package=definition.recommended_package,
            repeat_score=repeat_score,
            productization_score=productization_score,
            opportunity_count=len(opportunities),
            buyer_count=len(buyers),
            median_budget=float(statistics.median(budgets)) if budgets else None,
            min_budget=float(budgets[0]) if budgets else None,
            max_budget=float(budgets[-1]) if budgets else None,
            budget_range=_budget_range(budgets),
            keywords=keywords,
            cpv_families=cpv_families,
            buyers=buyers[:6],
            samples=[_sample(item) for item in sorted(opportunities, key=lambda item: item.fit_score, reverse=True)[:3]],
            recommended_products=_aggregate_products(opportunities),
        )


def _match_definition(definition: PatternDefinition, opportunity: Opportunity) -> PatternMatch | None:
    text = _search_text(opportunity)
    matched_keywords = {keyword for keyword in definition.keywords if _normalize(keyword) in text}
    matched_cpv_families = _matched_cpv_families(definition, opportunity)
    package_match = (opportunity.package_match or "").casefold()
    package_hit = any(hint.casefold() in package_match for hint in definition.package_hints)

    score = 0
    if matched_keywords:
        score += min(40, 14 + len(matched_keywords) * 5)
    if matched_cpv_families:
        score += min(28, 16 + len(matched_cpv_families) * 4)
    if package_hit:
        score += 18
    if opportunity.budget is not None and SMALL_TEAM_BUDGET_MIN <= opportunity.budget <= SMALL_TEAM_BUDGET_MAX:
        score += 8
    if opportunity.fit_score >= 60:
        score += 6

    if not matched_keywords and not matched_cpv_families and not package_hit:
        return None
    if not matched_keywords and not package_hit and matched_cpv_families == {"722"}:
        return None
    if (opportunity.package_match or "") == "Custom software" and not matched_keywords and not matched_cpv_families:
        return None
    if score < 22:
        return None
    return PatternMatch(definition, opportunity, score, matched_keywords, matched_cpv_families)


def _search_text(opportunity: Opportunity) -> str:
    return _normalize(
        " ".join(
            part
            for part in (
                opportunity.title,
                opportunity.summary,
                opportunity.raw_text,
                opportunity.package_match,
                " ".join(opportunity.matched_keywords),
            )
            if part
        )
    )


def _normalize(value: str) -> str:
    text = unicodedata.normalize("NFD", value.casefold())
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")
    return re.sub(r"\s+", " ", text).strip()


def _cpv_digits(code: str) -> str:
    return "".join(char for char in code if char.isdigit())


def _matched_cpv_families(definition: PatternDefinition, opportunity: Opportunity) -> set[str]:
    output: set[str] = set()
    for code in opportunity.cpv_codes:
        digits = _cpv_digits(code)
        for prefix in definition.cpv_prefixes:
            if digits.startswith(prefix):
                output.add(prefix if len(prefix) >= 3 else digits[:3])
    return output


def _repeat_score(opportunities: list[Opportunity], buyer_count: int) -> int:
    count_score = min(38, len(opportunities) * 12)
    diversity_score = min(24, buyer_count * 8)
    recent_score = 0
    today = date.today()
    for item in opportunities:
        if not item.published_at:
            continue
        age_days = (today - item.published_at).days
        if age_days <= 30:
            recent_score += 8
        elif age_days <= 180:
            recent_score += 5
        elif age_days <= 720:
            recent_score += 2
    return min(100, 20 + count_score + diversity_score + min(18, recent_score))


def _productization_score(
    opportunities: list[Opportunity],
    repeat_score: int,
    has_cpv_signal: bool,
    definition: PatternDefinition,
) -> int:
    score = int(repeat_score * 0.55) + 18
    budgets = [item.budget for item in opportunities if item.budget is not None]
    if budgets:
        sweet_spot = sum(1 for budget in budgets if SWEET_SPOT_BUDGET_MIN <= budget <= SWEET_SPOT_BUDGET_MAX)
        small_team = sum(1 for budget in budgets if SMALL_TEAM_BUDGET_MIN <= budget <= SMALL_TEAM_BUDGET_MAX)
        score += min(18, sweet_spot * 7 + small_team * 3)
    if has_cpv_signal:
        score += 10
    if definition.recommended_package:
        score += 7
    red_flags = sum(len(item.red_flags) for item in opportunities)
    score -= min(18, red_flags * 4)
    return max(0, min(100, score))


def _top_keywords(matches: list[PatternMatch]) -> list[str]:
    counts: dict[str, int] = {}
    for match in matches:
        for keyword in match.matched_keywords:
            counts[keyword] = counts.get(keyword, 0) + 1
    return [
        keyword
        for keyword, _ in sorted(counts.items(), key=lambda item: (item[1], item[0]), reverse=True)[:8]
    ]


def _aggregate_products(opportunities: list[Opportunity]) -> list[SoftwareMatch]:
    grouped: dict[str, list[SoftwareMatch]] = {}
    for opportunity in opportunities:
        for match in opportunity.software_matches:
            grouped.setdefault(match.product.slug, []).append(match)

    output: list[tuple[int, int, SoftwareMatch]] = []
    for matches in grouped.values():
        count = len(matches)
        average = round(sum(item.score for item in matches) / count)
        representative = max(matches, key=lambda item: (item.score, item.product.editorial_score))
        aggregated = representative.model_copy(
            deep=True,
            update={
                "score": average,
                "matched_signals": [
                    f"Recommended for {count} of {len(opportunities)} opportunities in this repeated need",
                    *representative.matched_signals,
                ],
            },
        )
        output.append((count, average, aggregated))

    output.sort(
        key=lambda item: (-item[0], -item[1], -item[2].product.editorial_score, item[2].product.name.casefold())
    )
    return [item[2] for item in output[:3]]


def _budget_range(budgets: list[float]) -> str:
    if not budgets:
        return "Unknown"
    low = f"{budgets[0]:,.0f} EUR".replace(",", ".")
    high = f"{budgets[-1]:,.0f} EUR".replace(",", ".")
    return low if low == high else f"{low} - {high}"


def _sample(opportunity: Opportunity) -> PatternOpportunitySample:
    return PatternOpportunitySample(
        id=opportunity.id,
        title=opportunity.title,
        buyer=opportunity.buyer,
        source=opportunity.source,
        source_label=opportunity.source_label,
        budget=opportunity.budget,
        published_at=opportunity.published_at,
        deadline=opportunity.deadline,
        cpv_codes=opportunity.cpv_codes,
        fit_score=opportunity.fit_score,
        package_match=opportunity.package_match,
    )
