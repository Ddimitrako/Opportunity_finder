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
]


DEFAULT_KEYWORDS = [
    "ανάπτυξη εφαρμογής",
    "ανάπτυξη λογισμικού",
    "πληροφοριακό σύστημα",
    "πλατφόρμα",
    "διαδικτυακή πλατφόρμα",
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
    use_ai: bool = False
    page: int = Field(default=0, ge=0)
    limit: int = Field(default=40, ge=1, le=100)


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
    ai_summary: str | None = None
    source_payload: dict[str, Any] = Field(default_factory=dict)


class DocumentLink(BaseModel):
    label: str
    url: str
    document_type: str
    language: str | None = None
    reference: str | None = None


class OpportunityDetails(BaseModel):
    source: SourceName
    reference: str
    title: str | None = None
    platform_url: str | None = None
    summary: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    documents: list[DocumentLink] = Field(default_factory=list)
    related_references: dict[str, list[str]] = Field(default_factory=dict)
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
    ai_enabled: bool


class HealthResponse(BaseModel):
    status: Literal["ok"]
    app: str
    ai_enabled: bool
    sources: dict[str, str]


class ConfigResponse(BaseModel):
    default_cpv_codes: list[str]
    default_keywords: list[str]
    packages: list[dict[str, Any]]
    sources: list[dict[str, str]]
