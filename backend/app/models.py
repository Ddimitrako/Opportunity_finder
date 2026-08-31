from datetime import date, datetime, timedelta
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

SourceName = Literal["khmdhs", "ted", "demo", "market"]
FitBand = Literal["Bid candidate", "Worth reading", "Monitor only", "Ignore"]
SoftwareMatchStatus = Literal["matched", "insufficient_signals"]
SoftwareMatchConfidence = Literal["high", "medium", "low"]
SoftwareMatchSource = Literal["deterministic", "ai_refined"]
DeliveryFit = Literal["solo", "small_team", "partner_required"]
SolutionType = Literal["production-platform", "specialist-component", "reference-implementation"]
SoftwareScreeningStatus = Literal["catalog_match", "needs_review", "no_match", "error"]
SoftwareScreeningStage = Literal["deterministic", "title", "summary", "documents"]
CandidateType = Literal["bid_now", "position_early", "outbound", "historical", "review"]
PursuitVerdict = Literal["pursue", "review", "skip"]
PursuitConfidence = Literal["high", "medium", "low"]
PursuitStatus = Literal["review", "pursue", "waiting", "won", "lost"]
SolutionRoute = Literal[
    "oss_configuration",
    "oss_extension",
    "custom_dashboard",
    "custom_web_app",
    "integration_data",
    "license_hardware",
    "unknown",
]


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
    keywords: list[str] = Field(default_factory=lambda: DEFAULT_KEYWORDS.copy(), max_length=50)
    cpv_codes: list[str] = Field(default_factory=lambda: DEFAULT_CPV_CODES.copy(), max_length=100)
    budget_min: float = Field(default=5_000, ge=0)
    budget_max: float = Field(default=100_000, ge=0)
    date_from: date = Field(default_factory=lambda: date.today() - timedelta(days=180))
    date_to: date = Field(default_factory=date.today)
    deadline_after: date = Field(default_factory=date.today)
    only_open: bool = True
    show_all_fetched: bool = False
    sources: list[SourceName] = Field(default_factory=lambda: ["khmdhs", "ted", "demo"], min_length=1, max_length=3)
    include_demo_when_empty: bool = True
    page: int = Field(default=0, ge=0)
    limit: int = Field(default=40, ge=1, le=100)

    @field_validator("sources")
    @classmethod
    def sources_must_be_unique(cls, sources: list[SourceName]) -> list[SourceName]:
        if len(sources) != len(set(sources)):
            raise ValueError("sources must contain unique values")
        return sources


class ActivityRequest(BaseModel):
    sources: list[SourceName] = Field(default_factory=lambda: ["khmdhs", "ted"], min_length=1, max_length=3)
    cpv_codes: list[str] = Field(default_factory=lambda: DEFAULT_CPV_CODES, max_length=100)
    days: int = Field(default=3, ge=1, le=366)
    limit: int = Field(default=100, ge=1, le=1000)

    @field_validator("sources")
    @classmethod
    def sources_must_be_unique(cls, sources: list[SourceName]) -> list[SourceName]:
        if len(sources) != len(set(sources)):
            raise ValueError("sources must contain unique values")
        return sources


class SoftwareMatchDimension(BaseModel):
    key: str
    label: str
    score: int
    max_score: int
    reasons: list[str] = Field(default_factory=list)


class ServiceRecommendation(BaseModel):
    service_type: str
    label: str
    confidence: Literal["recommended", "possible"] = "possible"
    reasons: list[str] = Field(default_factory=list)


class SoftwareProduct(BaseModel):
    slug: str
    name: str
    edition: str
    repository: str
    website: str
    summary: str
    problem: str
    ideal_for: str
    department_ids: list[str] = Field(default_factory=list)
    category_ids: list[str] = Field(default_factory=list)
    buyer_roles: list[str] = Field(default_factory=list)
    company_sizes: list[str] = Field(default_factory=list)
    deployment_modes: list[str] = Field(default_factory=list)
    service_types: list[str] = Field(default_factory=list)
    license_id: str
    maturity: Literal["anchor", "established", "niche-leader"]
    solution_type: SolutionType = "production-platform"
    editorial_score: int = Field(ge=0, le=100)
    english_support: str
    greek_support: Literal["verified", "partial", "unavailable", "unknown"]
    greek_evidence: str | None = None
    edition_boundary: str | None = None
    featured: bool = False
    last_verified_at: date
    extra_keywords_en: list[str] = Field(default_factory=list)
    extra_keywords_el: list[str] = Field(default_factory=list)
    negative_keywords: list[str] = Field(default_factory=list)
    delivery_fit: DeliveryFit = "small_team"
    active: bool = True


class SoftwareMatch(BaseModel):
    product: SoftwareProduct
    score: int = Field(ge=0, le=100)
    confidence: SoftwareMatchConfidence
    source: SoftwareMatchSource = "deterministic"
    dimensions: list[SoftwareMatchDimension] = Field(default_factory=list)
    matched_signals: list[str] = Field(default_factory=list)
    service_recommendations: list[ServiceRecommendation] = Field(default_factory=list)
    caveats: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    catalog_version: str


class SoftwareScreeningResult(BaseModel):
    opportunity_id: str
    status: SoftwareScreeningStatus
    stage: SoftwareScreeningStage
    reason: str
    matches: list[SoftwareMatch] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    model: str | None = None
    deep_model: str | None = None
    catalog_version: str
    prompt_version: str
    scanned_at: datetime
    cached: bool = False


class PursuitFactor(BaseModel):
    key: Literal["access", "win_chance", "delivery_fit", "value_effort"]
    label: str
    score: int = Field(ge=0, le=100)
    reasons: list[str] = Field(default_factory=list)


class PursuitAssessment(BaseModel):
    verdict: PursuitVerdict = "review"
    confidence: PursuitConfidence = "low"
    priority_score: int = Field(default=0, ge=0, le=100)
    candidate_type: CandidateType = "review"
    solution_route: SolutionRoute = "unknown"
    factors: list[PursuitFactor] = Field(default_factory=list)
    hard_gates: list[str] = Field(default_factory=list)
    top_reasons: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    next_action: str = "Review the source evidence."
    assessed_at: datetime = Field(default_factory=datetime.utcnow)
    rules_version: str = "pursuit-v1"


class CompanyProfile(BaseModel):
    delivery_mode: Literal["solo_first", "small_team", "partner_network"] = "solo_first"
    core_capabilities: list[str] = Field(default_factory=lambda: [
        "open-source deployment and customization",
        "custom dashboards and web applications",
        "portals and workflows",
        "API and systems integration",
        "data and business intelligence",
    ])
    preferred_solution_routes: list[SolutionRoute] = Field(default_factory=lambda: [
        "oss_configuration",
        "oss_extension",
        "custom_dashboard",
        "custom_web_app",
        "integration_data",
    ])
    team_size: int = Field(default=1, ge=1, le=100)
    partners_available: bool = True
    quick_win_budget_max: float = Field(default=30_000, ge=0)
    core_budget_max: float = Field(default=80_000, ge=0)
    minimum_viable_budget: float = Field(default=5_000, ge=0)
    certifications: list[str] = Field(default_factory=list)
    reference_projects: list[str] = Field(default_factory=list)
    annual_turnover: float | None = Field(default=None, ge=0)
    profile_notes: str = Field(default="", max_length=4_000)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class CompanyProfileUpdate(CompanyProfile):
    pass


class AIWorkflowRoute(BaseModel):
    model: str
    reasoning_effort: Literal["none", "low", "medium", "high", "xhigh", "max"] = "low"


class AIWorkflowSettings(BaseModel):
    preset: Literal["economy", "balanced", "best", "custom"] = "balanced"
    scan: AIWorkflowRoute = Field(default_factory=lambda: AIWorkflowRoute(model="gpt-5.6-luna", reasoning_effort="low"))
    dossier: AIWorkflowRoute = Field(default_factory=lambda: AIWorkflowRoute(model="gpt-5.6-terra", reasoning_effort="medium"))
    chat: AIWorkflowRoute = Field(default_factory=lambda: AIWorkflowRoute(model="gpt-5.6-terra", reasoning_effort="medium"))
    auto_deep_limit: int = Field(default=5, ge=0, le=10)
    max_deep_runs: int = Field(default=10, ge=0, le=20)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


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
    software_match_status: SoftwareMatchStatus = "insufficient_signals"
    software_matches: list[SoftwareMatch] = Field(default_factory=list)
    software_screening: SoftwareScreeningResult | None = None
    candidate_type: CandidateType = "review"
    procurement_stage: str = "unknown"
    solution_route: SolutionRoute = "unknown"
    pursuit_assessment: PursuitAssessment | None = None
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
    recommended_products: list[SoftwareMatch] = Field(default_factory=list)


class NeedPatternRequest(BaseModel):
    opportunities: list[Opportunity] = Field(default_factory=list, max_length=100)
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


class PursuitUpsertRequest(BaseModel):
    opportunity: Opportunity
    status: PursuitStatus = "review"
    next_action: str | None = Field(default=None, max_length=500)
    next_action_at: date | None = None
    notes: str = Field(default="", max_length=4_000)


class PursuitUpdateRequest(BaseModel):
    status: PursuitStatus | None = None
    next_action: str | None = Field(default=None, max_length=500)
    next_action_at: date | None = None
    notes: str | None = Field(default=None, max_length=4_000)


class PursuitFeedbackRequest(BaseModel):
    fit: bool
    reason: Literal[
        "incumbent",
        "eligibility",
        "delivery_size",
        "wrong_solution",
        "low_value",
        "insufficient_evidence",
        "good_fit",
        "other",
    ]
    notes: str = Field(default="", max_length=1_000)


class PursuitFeedback(BaseModel):
    fit: bool
    reason: str
    notes: str = ""
    created_at: datetime


class PursuitRecord(BaseModel):
    id: str
    opportunity: Opportunity
    status: PursuitStatus
    next_action: str | None = None
    next_action_at: date | None = None
    notes: str = ""
    feedback: PursuitFeedback | None = None
    created_at: datetime
    updated_at: datetime


class PursuitListResponse(BaseModel):
    pursuits: list[PursuitRecord]


DocumentBriefVerdict = Literal["yes", "no", "maybe", "unknown"]
BidDecisionVerdict = Literal["GO", "CONDITIONAL GO", "NO-GO", "INSUFFICIENT DATA"]
BidDecisionConfidence = Literal["high", "medium", "low"]
ProcurementAccessStatus = Literal[
    "open_competition",
    "named_invitation",
    "awarded",
    "contracted",
    "paid",
    "planning_only",
    "expired",
    "unknown",
]
ContinuityStatus = Literal["confirmed_continuation", "not_confirmed", "unknown"]


class BriefEvidence(BaseModel):
    id: str
    document_label: str
    url: str
    excerpt: str
    page: int | None = None
    reference: str | None = None


class BriefFinding(BaseModel):
    text: str
    evidence_ids: list[str] = Field(default_factory=list)


class BriefScoreDimension(BaseModel):
    key: str
    label: str
    score: int = 0
    max_score: int
    reason: str = "Unknown"
    evidence_ids: list[str] = Field(default_factory=list)


class BriefBudgetAssessment(BaseModel):
    amount_without_vat: float | None = None
    amount_with_vat: float | None = None
    currency: str = "EUR"
    direct_award_eligible: bool | None = None
    threshold_without_vat: float = 30_000
    determination: str = "Unknown"
    legal_basis_url: str = "https://eadhsy.gr/n4412/n4412fulltextlinks.html"
    evidence_ids: list[str] = Field(default_factory=list)


class BriefProcurementAccess(BaseModel):
    status: ProcurementAccessStatus = "unknown"
    reason: str = "Unknown"
    procedure: str | None = None
    deadline: date | None = None
    days_remaining: int | None = None
    submission_method: str = "Unknown"
    named_invitee: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)


class BriefContinuityAssessment(BaseModel):
    status: ContinuityStatus = "unknown"
    reason: str = "Unknown"
    incumbent_name: str | None = None
    prior_reference: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)


class BriefHistoryItem(BaseModel):
    title: str
    reference: str | None = None
    amount: float | None = None
    published_at: date | None = None
    supplier: str | None = None
    url: str | None = None


class DocumentBrief(BaseModel):
    source: SourceName
    reference: str
    schema_version: int = 1
    rules_version: str = "legacy"
    verdict: BidDecisionVerdict = "INSUFFICIENT DATA"
    score: int = Field(default=0, ge=0, le=100)
    confidence: BidDecisionConfidence = "low"
    executive_recommendation: str = "Insufficient data"
    decision_reasons: list[BriefFinding] = Field(default_factory=list)
    project_summary: str
    actionable: DocumentBriefVerdict = "unknown"
    procurement_access: BriefProcurementAccess = Field(default_factory=BriefProcurementAccess)
    continuity: BriefContinuityAssessment = Field(default_factory=BriefContinuityAssessment)
    budget_assessment: BriefBudgetAssessment = Field(default_factory=BriefBudgetAssessment)
    score_dimensions: list[BriefScoreDimension] = Field(default_factory=list)
    deadline_submission: str = "Unknown"
    required_documents: list[str] = Field(default_factory=list)
    eligibility_requirements: list[BriefFinding] = Field(default_factory=list)
    evaluation_criteria: list[BriefFinding] = Field(default_factory=list)
    technical_requirements: list[str] = Field(default_factory=list)
    technical_findings: list[BriefFinding] = Field(default_factory=list)
    commercial_findings: list[BriefFinding] = Field(default_factory=list)
    contractual_findings: list[BriefFinding] = Field(default_factory=list)
    red_flags: list[str] = Field(default_factory=list)
    red_flag_findings: list[BriefFinding] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)
    recommendation: str = "Maybe"
    next_steps: list[str] = Field(default_factory=list)
    history_12_months: list[BriefHistoryItem] = Field(default_factory=list)
    evidence: list[BriefEvidence] = Field(default_factory=list)
    source_documents: list[DocumentLink] = Field(default_factory=list)
    generated_at: datetime
    model: str | None = None
    cached: bool = False


class DocumentBriefResponse(BaseModel):
    brief: DocumentBrief | None = None
    cached: bool = False
    outdated: bool = False
    message: str | None = None


class OpportunityAIContext(BaseModel):
    source: SourceName
    reference: str
    details: OpportunityDetails
    evidence: list[BriefEvidence] = Field(default_factory=list)
    source_documents: list[DocumentLink] = Field(default_factory=list)
    available_document_count: int = 0
    analyzed_document_count: int = 0
    readable_document_count: int = 0
    unreadable_document_labels: list[str] = Field(default_factory=list)
    procurement_access: BriefProcurementAccess = Field(default_factory=BriefProcurementAccess)
    continuity: BriefContinuityAssessment = Field(default_factory=BriefContinuityAssessment)
    budget_assessment: BriefBudgetAssessment = Field(default_factory=BriefBudgetAssessment)
    history_12_months: list[BriefHistoryItem] = Field(default_factory=list)
    prepared_at: datetime


class OpportunityChatContextStatus(BaseModel):
    ready: bool = False
    prepared_at: datetime | None = None
    available_document_count: int = 0
    analyzed_document_count: int = 0
    readable_document_count: int = 0
    unreadable_document_labels: list[str] = Field(default_factory=list)


class OpportunityChatCitation(BaseModel):
    id: str
    kind: Literal["evidence", "history"]
    label: str
    url: str | None = None
    page: int | None = None
    reference: str | None = None
    excerpt: str | None = None


class OpportunityChatMessage(BaseModel):
    id: int
    role: Literal["user", "assistant"]
    content: str
    strategic_advice: str | None = None
    citations: list[OpportunityChatCitation] = Field(default_factory=list)
    suggested_questions: list[str] = Field(default_factory=list)
    model: str | None = None
    created_at: datetime


class OpportunityChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4_000)
    model: str | None = Field(default=None, min_length=1, max_length=80)


class OpportunityChatThreadResponse(BaseModel):
    messages: list[OpportunityChatMessage] = Field(default_factory=list)
    context: OpportunityChatContextStatus = Field(default_factory=OpportunityChatContextStatus)
    suggested_questions: list[str] = Field(default_factory=list)


class OpportunityChatTurnResponse(BaseModel):
    user_message: OpportunityChatMessage
    assistant_message: OpportunityChatMessage
    context: OpportunityChatContextStatus


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
    market_opportunities: list[Opportunity] = Field(default_factory=list, max_length=100)
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
    khmdhs_history_status: Literal["ok", "partial", "error", "skipped"] = "skipped"
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


class AIModelOption(BaseModel):
    id: str
    label: str
    description: str
    quality: str
    recommended: bool = False


class ConfigResponse(BaseModel):
    default_cpv_codes: list[str]
    default_keywords: list[str]
    packages: list[dict[str, Any]]
    sources: list[dict[str, str]]
    default_ai_model: str
    ai_models: list[AIModelOption]
    software_catalog_version: str
    software_catalog_count: int
    software_match_ai_enabled: bool
    software_screening_model: str
    software_screening_deep_model: str


class SoftwareMatchRefineRequest(BaseModel):
    opportunity: Opportunity
    model: str | None = Field(default=None, min_length=1, max_length=80)


class SoftwareMatchRefineResponse(BaseModel):
    matches: list[SoftwareMatch] = Field(default_factory=list)
    match_status: SoftwareMatchStatus = "insufficient_signals"
    model: str | None = None
    cached: bool = False
    catalog_version: str


class SoftwareScreeningRequest(BaseModel):
    opportunities: list[Opportunity] = Field(min_length=1, max_length=100)
    force: bool = False
    max_document_escalations: int = Field(default=5, ge=0, le=10)


class SoftwareScreeningRun(BaseModel):
    total: int
    catalog_matches: int
    needs_review: int
    no_matches: int
    errors: int
    cached: int
    ai_calls: int
    document_escalations: int
    input_tokens: int = 0
    output_tokens: int = 0


class SoftwareScreeningResponse(BaseModel):
    opportunities: list[Opportunity]
    results: list[SoftwareScreeningResult]
    run: SoftwareScreeningRun
    catalog_version: str
    prompt_version: str
    screening_model: str
    deep_model: str


OrganizationRole = Literal["buyer", "supplier", "both"]
SignalStage = Literal["early", "open", "awarded", "historical"]
SignalKind = Literal[
    "procurement_request",
    "planning_notice",
    "open_tender",
    "job_hiring",
    "expansion",
    "capital_change",
    "acquisition",
    "transformation",
    "award",
    "contract",
    "payment",
]
TrackingState = Literal[
    "new",
    "watching",
    "researching",
    "contact_planned",
    "contacted",
    "meeting",
    "proposal",
    "partner_target",
    "won",
    "lost",
    "archived",
]
OriginRegion = Literal["Europe", "United States", "China", "Other"]
SoftwareCategory = Literal[
    "ERP/Finance",
    "HR/HCM/Payroll",
    "Project Management/DevOps",
    "ITSM/IT Operations",
    "Cloud/Infrastructure",
    "BI/Analytics/AI",
    "Cybersecurity",
    "DMS/Workflow/Collaboration",
    "Defence/Industrial",
    "General Software",
]


class EvidenceRef(BaseModel):
    source: str
    external_id: str | None = None
    url: str | None = None
    title: str
    published_at: date | None = None
    excerpt: str = ""


class MarketOrganization(BaseModel):
    id: str
    name: str
    normalized_name: str
    role: OrganizationRole
    country: str = "GR"
    gemi_number: str | None = None
    tax_id: str | None = None
    khmdhs_key: str | None = None
    aliases: list[str] = Field(default_factory=list)
    website: str | None = None
    strongest_signal_score: int = 0
    strongest_signal_kind: SignalKind | None = None
    strongest_category: SoftwareCategory | None = None
    last_signal_at: date | None = None
    incumbent_suppliers: list[str] = Field(default_factory=list)
    software_brands: list[str] = Field(default_factory=list)
    tracking_state: TrackingState | None = None
    next_action: str | None = None
    updated_at: datetime


class NeedSignal(BaseModel):
    id: str
    organization_id: str
    organization_name: str
    category: SoftwareCategory
    kind: SignalKind
    stage: SignalStage
    need_score: int = Field(ge=0, le=100)
    confidence: int = Field(ge=0, le=100)
    why_now: str
    score_reasons: list[str] = Field(default_factory=list)
    evidence: EvidenceRef
    is_new: bool = False
    created_at: datetime
    updated_at: datetime


class SupplierAward(BaseModel):
    id: str
    buyer_id: str
    buyer_name: str
    supplier_id: str
    supplier_name: str
    title: str
    category: SoftwareCategory
    amount: float | None = None
    currency: str = "EUR"
    awarded_at: date | None = None
    software_brands: list[str] = Field(default_factory=list)
    evidence: EvidenceRef


class SoftwareBrand(BaseModel):
    id: str
    name: str
    origin_region: OriginRegion
    aliases: list[str] = Field(default_factory=list)
    mention_count: int = 0
    observed_spend: float = 0
    supplier_names: list[str] = Field(default_factory=list)
    buyer_names: list[str] = Field(default_factory=list)
    last_seen_at: date | None = None


class SoftwareBrandMention(BaseModel):
    id: str
    brand_id: str
    brand_name: str
    product_name: str | None = None
    buyer_id: str | None = None
    supplier_id: str | None = None
    confidence: int = Field(ge=0, le=100)
    evidence: EvidenceRef


class TrackingEntryCreate(BaseModel):
    entity_type: Literal["buyer", "supplier", "brand", "opportunity"]
    entity_id: str
    state: TrackingState = "watching"
    notes: str = Field(default="", max_length=4000)
    next_action: str | None = Field(default=None, max_length=500)
    next_action_at: date | None = None


class TrackingEntryUpdate(BaseModel):
    state: TrackingState | None = None
    notes: str | None = Field(default=None, max_length=4000)
    next_action: str | None = Field(default=None, max_length=500)
    next_action_at: date | None = None


class TrackingEntry(BaseModel):
    id: str
    entity_type: Literal["buyer", "supplier", "brand", "opportunity"]
    entity_id: str
    entity_name: str
    state: TrackingState
    notes: str = ""
    next_action: str | None = None
    next_action_at: date | None = None
    created_at: datetime
    updated_at: datetime


class WatchSourceCreate(BaseModel):
    organization_id: str
    source_type: Literal["careers", "newsroom"]
    url: str = Field(min_length=8, max_length=2000)
    label: str = Field(default="", max_length=200)
    enabled: bool = True


class WatchSourceUpdate(BaseModel):
    label: str | None = Field(default=None, max_length=200)
    enabled: bool | None = None


class WatchSource(BaseModel):
    id: str
    organization_id: str
    organization_name: str
    source_type: Literal["careers", "newsroom"]
    url: str
    label: str
    enabled: bool
    last_checked_at: datetime | None = None
    last_changed_at: datetime | None = None
    last_error: str | None = None


class DiscoveryProfileCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    activities: list[str] = Field(default_factory=list)
    prefectures: list[int] = Field(default_factory=list)
    municipalities: list[str] = Field(default_factory=list)
    is_active: bool = True
    enabled: bool = True


class DiscoveryProfile(BaseModel):
    id: str
    name: str
    activities: list[str] = Field(default_factory=list)
    prefectures: list[int] = Field(default_factory=list)
    municipalities: list[str] = Field(default_factory=list)
    is_active: bool
    enabled: bool
    last_run_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class MarketCategoryTrend(BaseModel):
    category: SoftwareCategory
    current_count: int
    previous_count: int
    delta_percent: float | None = None
    observed_spend: float = 0


class MarketOverviewResponse(BaseModel):
    generated_at: datetime
    period_days: int
    new_signals: int
    hot_buyers: int
    open_opportunities: int
    observed_public_spend: float
    tracked_entities: int
    categories: list[MarketCategoryTrend] = Field(default_factory=list)
    hot_organizations: list[MarketOrganization] = Field(default_factory=list)
    recent_signals: list[NeedSignal] = Field(default_factory=list)
    top_suppliers: list[MarketOrganization] = Field(default_factory=list)
    top_brands: list[SoftwareBrand] = Field(default_factory=list)
    coverage: dict[str, str] = Field(default_factory=dict)
    last_refresh_at: datetime | None = None


class MarketOrganizationListResponse(BaseModel):
    items: list[MarketOrganization]
    total: int
    limit: int
    offset: int


class MarketOrganizationDetail(BaseModel):
    organization: MarketOrganization
    signals: list[NeedSignal] = Field(default_factory=list)
    awards_as_buyer: list[SupplierAward] = Field(default_factory=list)
    awards_as_supplier: list[SupplierAward] = Field(default_factory=list)
    brand_mentions: list[SoftwareBrandMention] = Field(default_factory=list)
    tracking: TrackingEntry | None = None
    watch_sources: list[WatchSource] = Field(default_factory=list)


class MarketSignalListResponse(BaseModel):
    items: list[NeedSignal]
    total: int
    limit: int
    offset: int


class MarketBrandListResponse(BaseModel):
    items: list[SoftwareBrand]
    total: int


class MarketBrandDetail(BaseModel):
    brand: SoftwareBrand
    mentions: list[SoftwareBrandMention] = Field(default_factory=list)
    awards: list[SupplierAward] = Field(default_factory=list)
    tracking: TrackingEntry | None = None


class MarketRefreshRequest(BaseModel):
    backfill_days: int | None = Field(default=None, ge=1, le=1800)


class MarketRefreshSourceResult(BaseModel):
    source: str
    status: Literal["ok", "error", "skipped"]
    fetched: int = 0
    created: int = 0
    updated: int = 0
    error: str | None = None


class MarketRefreshResponse(BaseModel):
    run_id: str
    status: Literal["running", "ok", "partial", "error", "skipped"]
    started_at: datetime
    finished_at: datetime | None = None
    source_results: list[MarketRefreshSourceResult] = Field(default_factory=list)
    message: str | None = None


class MarketConfigResponse(BaseModel):
    gemi_enabled: bool
    refresh_enabled: bool
    refresh_hour: int
    categories: list[str]
    tracking_states: list[str]
