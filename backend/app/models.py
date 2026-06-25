from datetime import date, datetime, timedelta
from typing import Any, Literal

from pydantic import BaseModel, Field

SourceName = Literal["khmdhs", "ted", "demo"]
FitBand = Literal["Bid candidate", "Worth reading", "Monitor only", "Ignore"]


DEFAULT_CPV_CODES = [
    "72000000-5",
    "72212000-4",
    "72212100-0",
    "72262000-9",
    "72263000-6",
    "72250000-2",
    "72253000-3",
    "72261000-2",
    "72268000-1",
    "72420000-0",
    "72421000-7",
    "72413000-8",
    "72415000-2",
    "72416000-9",
    "72316000-3",
    "72320000-4",
    "72212482-0",
    "48311100-2",
    "72212311-2",
    "72267100-0",
    "30200000-1",
    "30210000-4",
    "30213000-5",
    "30213100-6",
    "30213300-8",
    "30230000-0",
    "30231300-0",
    "30232110-8",
    "32400000-7",
    "32420000-3",
    "48800000-6",
    "48820000-2",
    "50312000-5",
    "50312300-8",
    "72700000-7",
    "48730000-4",
    "48732000-8",
    "72212730-5",
    "72810000-1",
    "72500000-0",
    "72510000-3",
    "72590000-7",
    "72910000-2",
    "38221000-0",
    "71354100-5",
    "72314000-9",
    "48400000-2",
    "48440000-4",
    "48450000-7",
    "72212440-5",
    "72212450-8",
    "72212460-1",
    "72212461-8",
    "72212463-2",
    "72212481-3",
    "79999100-4",
    "72311100-9",
    "92512000-3",
    "48190000-6",
    "72212190-7",
    "80533100-0",
    "80420000-4",
    "72220000-3",
    "72221000-0",
    "72222000-7",
    "72224000-1",
    "72246000-1",
]


DEFAULT_KEYWORDS = [
    "ανάπτυξη εφαρμογής",
    "ανάπτυξη λογισμικού",
    "πληροφοριακό σύστημα",
    "web εφαρμογή",
    "dashboard",
    "αναφορές",
    "στατιστικά",
    "monitoring",
    "portal",
    "CMS",
    "workflow",
    "API",
]


class ProcurementSearchRequest(BaseModel):
    query: str = Field(default="", max_length=100)
    keywords: list[str] = Field(default_factory=lambda: DEFAULT_KEYWORDS.copy())
    cpv_codes: list[str] = Field(default_factory=lambda: DEFAULT_CPV_CODES.copy())
    budget_min: float = Field(default=5_000, ge=0)
    budget_max: float = Field(default=100_000, ge=0)
    date_from: date = Field(default_factory=lambda: date.today() - timedelta(days=180))
    date_to: date = Field(default_factory=date.today)
    deadline_after: date = Field(default_factory=date.today)
    only_open: bool = True
    show_all_fetched: bool = False
    sources: list[SourceName] = Field(default_factory=lambda: ["khmdhs", "ted", "demo"])
    include_demo_when_empty: bool = True
    page: int = Field(default=0, ge=0)
    limit: int = Field(default=40, ge=1, le=100)


class ActivityRequest(BaseModel):
    sources: list[SourceName] = Field(default_factory=lambda: ["khmdhs", "ted"])
    cpv_codes: list[str] = Field(default_factory=lambda: DEFAULT_CPV_CODES)
    days: int = Field(default=3, ge=1, le=366)
    limit: int = Field(default=100, ge=1, le=1000)


class Opportunity(BaseModel):
    id: str
    source: SourceName
    source_label: str
    title: str
    buyer: str = "Unknown buyer"
    buyer_type: str | None = None
    procedure_type: str | None = None
    cpv_codes: list[str] = Field(default_factory=list)
    budget: float | None = None
    currency: str = "EUR"
    deadline: date | None = None
    published_at: date | None = None
    country: str = "GR"
    location: str | None = None
    url: str | None = None
    platform_label: str | None = None
    source_reference: str | None = None
    status_label: str | None = None
    notice_type: str | None = None
    summary: str
    raw_text: str = ""
    matched_keywords: list[str] = Field(default_factory=list)
    fit_score: int = 0
    fit_band: FitBand = "Monitor only"
    score_reasons: list[str] = Field(default_factory=list)
    red_flags: list[str] = Field(default_factory=list)
    recommendation: str = "Monitor"
    package_match: str = "Custom software"
    source_payload: dict[str, Any] = Field(default_factory=dict)


class PatternOpportunitySample(BaseModel):
    id: str
    title: str
    buyer: str
    source: SourceName
    source_label: str
    budget: float | None = None
    published_at: date | None = None
    deadline: date | None = None
    cpv_codes: list[str] = Field(default_factory=list)
    fit_score: int = 0
    package_match: str | None = None


class NeedPattern(BaseModel):
    pattern_id: str
    label: str
    category: str
    recommended_package: str
    repeat_score: int
    productization_score: int
    opportunity_count: int
    buyer_count: int
    median_budget: float | None = None
    min_budget: float | None = None
    max_budget: float | None = None
    budget_range: str = "Unknown"
    keywords: list[str] = Field(default_factory=list)
    cpv_families: list[str] = Field(default_factory=list)
    buyers: list[str] = Field(default_factory=list)
    samples: list[PatternOpportunitySample] = Field(default_factory=list)


class NeedPatternRequest(BaseModel):
    opportunities: list[Opportunity] = Field(default_factory=list)
    min_opportunities: int = Field(default=2, ge=1, le=20)
    max_patterns: int = Field(default=8, ge=1, le=20)


class NeedPatternResponse(BaseModel):
    generated_at: datetime
    patterns: list[NeedPattern] = Field(default_factory=list)
    unmatched_count: int = 0
    patternable_count: int = 0


class DocumentLink(BaseModel):
    label: str
    url: str
    document_type: str
    language: str | None = None
    reference: str | None = None


class LifecycleStep(BaseModel):
    id: str
    label: str
    status: Literal["complete", "current", "upcoming", "unknown"] = "upcoming"
    description: str
    references: list[str] = Field(default_factory=list)
    url: str | None = None


class GuidanceChecklistItem(BaseModel):
    label: str
    detail: str
    status: Literal["done", "todo", "watch", "blocked"] = "todo"


class OpportunityGuidance(BaseModel):
    current_stage: str
    current_stage_label: str
    is_actionable: bool
    next_action: str
    stage_steps: list[LifecycleStep] = Field(default_factory=list)
    checklist: list[GuidanceChecklistItem] = Field(default_factory=list)
    watch_items: list[str] = Field(default_factory=list)
    primary_action_link: str | None = None


class OpportunityDetails(BaseModel):
    source: SourceName
    reference: str
    title: str | None = None
    platform_url: str | None = None
    summary: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    documents: list[DocumentLink] = Field(default_factory=list)
    related_references: dict[str, list[str]] = Field(default_factory=dict)
    guidance: OpportunityGuidance | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


class SourceRun(BaseModel):
    source: SourceName
    status: Literal["ok", "error", "skipped"]
    items: int = 0
    shown: int = 0
    elapsed_ms: int = 0
    error: str | None = None


class SearchResponse(BaseModel):
    generated_at: datetime
    query: ProcurementSearchRequest
    opportunities: list[Opportunity]
    source_runs: list[SourceRun]
    stats: dict[str, Any]


class DailyActivity(BaseModel):
    date: date
    label: str
    total: int
    by_source: dict[SourceName, int] = Field(default_factory=dict)


class ActivityResponse(BaseModel):
    generated_at: datetime
    date_from: date
    date_to: date
    daily_activity: list[DailyActivity]
    source_runs: list[SourceRun]
    total: int
    cached: bool = False


class BookmarkRecord(BaseModel):
    id: str
    opportunity: Opportunity
    created_at: datetime
    updated_at: datetime


class BookmarkListResponse(BaseModel):
    bookmarks: list[BookmarkRecord]


class BookmarkStatusResponse(BaseModel):
    db_path: str
    exists: bool
    bookmark_count: int


class BookmarkUpsertRequest(BaseModel):
    opportunity: Opportunity


DocumentBriefVerdict = Literal["yes", "no", "maybe", "unknown"]


class DocumentBrief(BaseModel):
    source: SourceName
    reference: str
    project_summary: str
    actionable: DocumentBriefVerdict = "unknown"
    deadline_submission: str = "Unknown"
    required_documents: list[str] = Field(default_factory=list)
    technical_requirements: list[str] = Field(default_factory=list)
    red_flags: list[str] = Field(default_factory=list)
    recommendation: str = "Maybe"
    next_steps: list[str] = Field(default_factory=list)
    source_documents: list[DocumentLink] = Field(default_factory=list)
    generated_at: datetime
    model: str | None = None
    cached: bool = False


class DocumentBriefResponse(BaseModel):
    brief: DocumentBrief | None = None
    cached: bool = False
    message: str | None = None


class BudgetProfile(BaseModel):
    count: int = 0
    min: float | None = None
    max: float | None = None
    average: float | None = None
    median: float | None = None
    typical_range: str = "Unknown"


class BuyerOpportunitySample(BaseModel):
    id: str
    title: str
    source: SourceName
    source_label: str
    budget: float | None = None
    published_at: date | None = None
    deadline: date | None = None
    cpv_codes: list[str] = Field(default_factory=list)
    fit_score: int = 0
    package_match: str | None = None
    url: str | None = None


class DiavgeiaDecisionSignal(BaseModel):
    source_label: str = "Diavgeia"
    ada: str | None = None
    subject: str
    decision_type: str | None = None
    published_at: date | None = None
    amount: float | None = None
    currency: str = "EUR"
    winner_name: str | None = None
    cpv_codes: list[str] = Field(default_factory=list)
    url: str | None = None
    document_url: str | None = None
    similar_to_software: bool = False


class BuyerIntelligenceRequest(BaseModel):
    buyer: str = Field(min_length=1, max_length=240)
    opportunity: Opportunity | None = None
    market_opportunities: list[Opportunity] = Field(default_factory=list)
    diavgeia_limit: int = Field(default=8, ge=0, le=30)
    history_days: int = Field(default=720, ge=0, le=1800)
    history_limit: int = Field(default=40, ge=0, le=120)


class BuyerIntelligenceResponse(BaseModel):
    buyer: str
    generated_at: datetime
    market_window_count: int
    visible_buyer_opportunity_count: int
    history_opportunity_count: int = 0
    buyer_opportunity_count: int
    source_counts: dict[SourceName, int] = Field(default_factory=dict)
    budget_profile: BudgetProfile
    small_software_count: int = 0
    current_cpv_categories: list[str] = Field(default_factory=list)
    khmdhs_history_date_from: date | None = None
    khmdhs_history_date_to: date | None = None
    khmdhs_history_result_date_from: date | None = None
    khmdhs_history_result_date_to: date | None = None
    similar_opportunities: list[BuyerOpportunitySample] = Field(default_factory=list)
    recent_opportunities: list[BuyerOpportunitySample] = Field(default_factory=list)
    has_similar_procurement: bool = False
    khmdhs_history_status: Literal["ok", "error", "skipped"] = "skipped"
    khmdhs_history_message: str | None = None
    diavgeia_status: Literal["ok", "error", "skipped"] = "skipped"
    diavgeia_message: str | None = None
    diavgeia_decisions: list[DiavgeiaDecisionSignal] = Field(default_factory=list)
    winner_signals: list[DiavgeiaDecisionSignal] = Field(default_factory=list)
    confidence_notes: list[str] = Field(default_factory=list)
    insight_flags: list[str] = Field(default_factory=list)


class HealthResponse(BaseModel):
    status: Literal["ok"]
    app: str
    brief_ai_enabled: bool
    sources: dict[str, str]


class ConfigResponse(BaseModel):
    default_cpv_codes: list[str]
    default_keywords: list[str]
    packages: list[dict[str, Any]]
    sources: list[dict[str, str]]
