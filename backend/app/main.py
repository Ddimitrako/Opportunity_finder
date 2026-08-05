from urllib.parse import urlparse

import httpx
from fastapi import Depends, FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware

from app.config import Settings, get_settings
from app.ai_models import AI_MODEL_CATALOG, UnsupportedAIModelError, default_ai_model
from app.catalog import get_software_catalog
from app.models import (
    ActivityRequest,
    ActivityResponse,
    BookmarkListResponse,
    BookmarkStatusResponse,
    BookmarkUpsertRequest,
    BuyerIntelligenceRequest,
    BuyerIntelligenceResponse,
    ConfigResponse,
    DEFAULT_CPV_CODES,
    DEFAULT_KEYWORDS,
    DocumentBriefResponse,
    HealthResponse,
    DiscoveryProfile,
    DiscoveryProfileCreate,
    MarketBrandDetail,
    MarketBrandListResponse,
    MarketConfigResponse,
    MarketOrganizationDetail,
    MarketOrganizationListResponse,
    MarketOverviewResponse,
    MarketRefreshRequest,
    MarketRefreshResponse,
    MarketSignalListResponse,
    NeedPatternRequest,
    NeedPatternResponse,
    OpportunityDetails,
    OpportunityChatContextStatus,
    OpportunityChatRequest,
    OpportunityChatThreadResponse,
    OpportunityChatTurnResponse,
    ProcurementSearchRequest,
    SearchResponse,
    SourceName,
    SoftwareMatchRefineRequest,
    SoftwareMatchRefineResponse,
    TrackingEntry,
    TrackingEntryCreate,
    TrackingEntryUpdate,
    WatchSource,
    WatchSourceCreate,
    WatchSourceUpdate,
)
from app.scoring import PACKAGES
from app.services.bookmarks import BookmarkService
from app.services.briefs import DocumentBriefService
from app.services.chat import ChatGenerationError, ChatUnavailableError, OpportunityChatService
from app.services.buyer_intelligence import BuyerIntelligenceService
from app.services.details import OpportunityDetailsService
from app.services.opportunities import OpportunityService
from app.services.patterns import PatternDiscoveryService
from app.services.software_refinement import (
    SoftwareRefinementError,
    SoftwareRefinementService,
    SoftwareRefinementUnavailable,
)
from app.services.market import MarketService

app = FastAPI(title="Opportunity Finder API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_service(settings: Settings = Depends(get_settings)) -> OpportunityService:
    return OpportunityService(settings)


def get_details_service(settings: Settings = Depends(get_settings)) -> OpportunityDetailsService:
    return OpportunityDetailsService(settings)


def get_bookmark_service(settings: Settings = Depends(get_settings)) -> BookmarkService:
    return BookmarkService(settings)


def get_brief_service(settings: Settings = Depends(get_settings)) -> DocumentBriefService:
    return DocumentBriefService(settings)


def get_chat_service(settings: Settings = Depends(get_settings)) -> OpportunityChatService:
    return OpportunityChatService(settings)


def get_buyer_intelligence_service(settings: Settings = Depends(get_settings)) -> BuyerIntelligenceService:
    return BuyerIntelligenceService(settings)


def get_pattern_service() -> PatternDiscoveryService:
    return PatternDiscoveryService()


def get_market_service(settings: Settings = Depends(get_settings)) -> MarketService:
    return MarketService(settings)


def get_software_refinement_service(settings: Settings = Depends(get_settings)) -> SoftwareRefinementService:
    return SoftwareRefinementService(settings)


def _allowed_document_hosts(settings: Settings) -> set[str]:
    hosts = {
        urlparse(str(settings.khmdhs_base_url)).hostname,
        urlparse(str(settings.ted_base_url)).hostname,
        urlparse(str(settings.diavgeia_base_url)).hostname,
    }
    return {host for host in hosts if host}


@app.get("/api/health", response_model=HealthResponse)
async def health(settings: Settings = Depends(get_settings)) -> HealthResponse:
    return HealthResponse(
        status="ok",
        app=settings.app_name,
        brief_ai_enabled=bool(settings.openai_api_key),
        sources={
            "khmdhs": "OpenData API for Greek public procurement acts",
            "ted": "EU TED Search API for published procurement notices",
            "demo": "Curated local patterns for UI and scoring validation",
        },
    )


@app.get("/api/config", response_model=ConfigResponse)
async def config(settings: Settings = Depends(get_settings)) -> ConfigResponse:
    catalog = get_software_catalog()
    return ConfigResponse(
        default_cpv_codes=DEFAULT_CPV_CODES,
        default_keywords=DEFAULT_KEYWORDS,
        packages=PACKAGES,
        sources=[
            {"id": "khmdhs", "label": "ΚΗΜΔΗΣ"},
            {"id": "ted", "label": "TED"},
            {"id": "demo", "label": "Demo patterns"},
        ],
        default_ai_model=default_ai_model(settings),
        ai_models=list(AI_MODEL_CATALOG),
        software_catalog_version=catalog.catalog_version,
        software_catalog_count=len(catalog.products),
        software_match_ai_enabled=bool(settings.openai_api_key),
    )


@app.get("/api/documents/pdf")
async def proxy_pdf_document(
    url: str = Query(min_length=8, max_length=2000),
    settings: Settings = Depends(get_settings),
) -> Response:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or parsed.hostname not in _allowed_document_hosts(settings):
        raise HTTPException(status_code=400, detail="Document URL is not allowed.")

    verify_ssl = settings.khmdhs_verify_ssl if parsed.hostname == urlparse(str(settings.khmdhs_base_url)).hostname else True
    if parsed.hostname == urlparse(str(settings.khmdhs_base_url)).hostname:
        timeout = settings.khmdhs_timeout_seconds
    elif parsed.hostname == urlparse(str(settings.diavgeia_base_url)).hostname:
        timeout = settings.diavgeia_timeout_seconds
    else:
        timeout = settings.ted_timeout_seconds
    try:
        async with httpx.AsyncClient(timeout=timeout, verify=verify_ssl, follow_redirects=True) as client:
            upstream = await client.get(url, headers={"Accept": "application/pdf,*/*"})
            upstream.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Document fetch failed: {exc.__class__.__name__}") from exc

    content_type = upstream.headers.get("content-type") or "application/pdf"
    if "html" in content_type.lower():
        raise HTTPException(status_code=502, detail="Document endpoint returned HTML instead of a PDF.")

    return Response(
        content=upstream.content,
        media_type=content_type,
        headers={
            "Content-Disposition": 'inline; filename="document.pdf"',
            "X-Content-Type-Options": "nosniff",
        },
    )


@app.post("/api/opportunities/search", response_model=SearchResponse)
async def search_opportunities(
    request: ProcurementSearchRequest,
    service: OpportunityService = Depends(get_service),
    market: MarketService = Depends(get_market_service),
) -> SearchResponse:
    response = await service.search(request)
    market.ingest_opportunities(response.opportunities)
    return response


@app.post("/api/software-matches/refine", response_model=SoftwareMatchRefineResponse)
async def refine_software_matches(
    request: SoftwareMatchRefineRequest,
    service: SoftwareRefinementService = Depends(get_software_refinement_service),
) -> SoftwareMatchRefineResponse:
    try:
        return await service.refine(request.opportunity, request.model)
    except UnsupportedAIModelError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SoftwareRefinementUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except SoftwareRefinementError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/api/opportunities/activity", response_model=ActivityResponse)
async def opportunity_activity(
    request: ActivityRequest,
    service: OpportunityService = Depends(get_service),
) -> ActivityResponse:
    return await service.activity(request)


@app.post("/api/buyers/intelligence", response_model=BuyerIntelligenceResponse)
async def buyer_intelligence(
    request: BuyerIntelligenceRequest,
    service: BuyerIntelligenceService = Depends(get_buyer_intelligence_service),
) -> BuyerIntelligenceResponse:
    return await service.analyze(request)


@app.post("/api/patterns/discover", response_model=NeedPatternResponse)
async def discover_patterns(
    request: NeedPatternRequest,
    service: PatternDiscoveryService = Depends(get_pattern_service),
) -> NeedPatternResponse:
    return service.discover(request)


@app.get("/api/bookmarks", response_model=BookmarkListResponse)
async def list_bookmarks(service: BookmarkService = Depends(get_bookmark_service)) -> BookmarkListResponse:
    return service.list_bookmarks()


@app.get("/api/bookmarks/status", response_model=BookmarkStatusResponse)
async def bookmark_status(service: BookmarkService = Depends(get_bookmark_service)) -> BookmarkStatusResponse:
    return service.status()


@app.post("/api/bookmarks", response_model=BookmarkListResponse)
async def save_bookmark(
    request: BookmarkUpsertRequest,
    service: BookmarkService = Depends(get_bookmark_service),
) -> BookmarkListResponse:
    service.upsert_bookmark(request.opportunity)
    return service.list_bookmarks()


@app.delete("/api/bookmarks/{bookmark_id}", response_model=BookmarkListResponse)
async def delete_bookmark(
    bookmark_id: str,
    service: BookmarkService = Depends(get_bookmark_service),
) -> BookmarkListResponse:
    service.delete_bookmark(bookmark_id)
    return service.list_bookmarks()


@app.get("/api/market/config", response_model=MarketConfigResponse)
async def market_config(service: MarketService = Depends(get_market_service)) -> MarketConfigResponse:
    return service.config()


@app.get("/api/market/overview", response_model=MarketOverviewResponse)
async def market_overview(
    period_days: int = Query(default=30, ge=1, le=365),
    service: MarketService = Depends(get_market_service),
) -> MarketOverviewResponse:
    return service.overview(period_days)


@app.get("/api/market/signals", response_model=MarketSignalListResponse)
async def market_signals(
    category: str | None = None,
    stage: str | None = None,
    min_score: int = Query(default=0, ge=0, le=100),
    source: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    service: MarketService = Depends(get_market_service),
) -> MarketSignalListResponse:
    return service.list_signals(category=category, stage=stage, min_score=min_score, source=source, limit=limit, offset=offset)


@app.get("/api/market/buyers", response_model=MarketOrganizationListResponse)
async def market_buyers(
    search: str | None = None,
    category: str | None = None,
    min_score: int = Query(default=0, ge=0, le=100),
    tracking_state: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    service: MarketService = Depends(get_market_service),
) -> MarketOrganizationListResponse:
    return service.list_organizations(
        role="buyer", search=search, category=category, min_score=min_score,
        tracking_state=tracking_state, limit=limit, offset=offset,
    )


@app.get("/api/market/buyers/{organization_id}", response_model=MarketOrganizationDetail)
async def market_buyer_detail(
    organization_id: str,
    service: MarketService = Depends(get_market_service),
) -> MarketOrganizationDetail:
    detail = service.organization_detail(organization_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Buyer not found.")
    return detail


@app.get("/api/market/suppliers", response_model=MarketOrganizationListResponse)
async def market_suppliers(
    search: str | None = None,
    category: str | None = None,
    tracking_state: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    service: MarketService = Depends(get_market_service),
) -> MarketOrganizationListResponse:
    return service.list_organizations(
        role="supplier", search=search, category=category, tracking_state=tracking_state,
        limit=limit, offset=offset,
    )


@app.get("/api/market/suppliers/{organization_id}", response_model=MarketOrganizationDetail)
async def market_supplier_detail(
    organization_id: str,
    service: MarketService = Depends(get_market_service),
) -> MarketOrganizationDetail:
    detail = service.organization_detail(organization_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Supplier not found.")
    return detail


@app.get("/api/market/brands", response_model=MarketBrandListResponse)
async def market_brands(
    region: str | None = None,
    search: str | None = None,
    limit: int = Query(default=100, ge=1, le=200),
    service: MarketService = Depends(get_market_service),
) -> MarketBrandListResponse:
    return service.list_brands(region=region, search=search, limit=limit)


@app.get("/api/market/brands/{brand_id}", response_model=MarketBrandDetail)
async def market_brand_detail(
    brand_id: str,
    service: MarketService = Depends(get_market_service),
) -> MarketBrandDetail:
    detail = service.brand_detail(brand_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Software brand not found.")
    return detail


@app.get("/api/market/tracking", response_model=list[TrackingEntry])
async def market_tracking(service: MarketService = Depends(get_market_service)) -> list[TrackingEntry]:
    return service.list_tracking()


@app.post("/api/market/tracking", response_model=TrackingEntry)
async def create_market_tracking(
    payload: TrackingEntryCreate,
    service: MarketService = Depends(get_market_service),
) -> TrackingEntry:
    return service.upsert_tracking(payload)


@app.patch("/api/market/tracking/{tracking_id}", response_model=TrackingEntry)
async def update_market_tracking(
    tracking_id: str,
    payload: TrackingEntryUpdate,
    service: MarketService = Depends(get_market_service),
) -> TrackingEntry:
    item = service.update_tracking(tracking_id, payload)
    if not item:
        raise HTTPException(status_code=404, detail="Tracking entry not found.")
    return item


@app.delete("/api/market/tracking/{tracking_id}", status_code=204)
async def delete_market_tracking(
    tracking_id: str,
    service: MarketService = Depends(get_market_service),
) -> Response:
    if not service.delete_tracking(tracking_id):
        raise HTTPException(status_code=404, detail="Tracking entry not found.")
    return Response(status_code=204)


@app.get("/api/market/watch-sources", response_model=list[WatchSource])
async def market_watch_sources(service: MarketService = Depends(get_market_service)) -> list[WatchSource]:
    return service.list_watch_sources()


@app.post("/api/market/watch-sources", response_model=WatchSource)
async def create_market_watch_source(
    payload: WatchSourceCreate,
    service: MarketService = Depends(get_market_service),
) -> WatchSource:
    try:
        return service.create_watch_source(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.patch("/api/market/watch-sources/{watch_id}", response_model=WatchSource)
async def update_market_watch_source(
    watch_id: str,
    payload: WatchSourceUpdate,
    service: MarketService = Depends(get_market_service),
) -> WatchSource:
    item = service.update_watch_source(watch_id, payload)
    if not item:
        raise HTTPException(status_code=404, detail="Watch source not found.")
    return item


@app.delete("/api/market/watch-sources/{watch_id}", status_code=204)
async def delete_market_watch_source(
    watch_id: str,
    service: MarketService = Depends(get_market_service),
) -> Response:
    if not service.delete_watch_source(watch_id):
        raise HTTPException(status_code=404, detail="Watch source not found.")
    return Response(status_code=204)


@app.get("/api/market/discovery-profiles", response_model=list[DiscoveryProfile])
async def market_discovery_profiles(service: MarketService = Depends(get_market_service)) -> list[DiscoveryProfile]:
    return service.list_discovery_profiles()


@app.post("/api/market/discovery-profiles", response_model=DiscoveryProfile)
async def create_market_discovery_profile(
    payload: DiscoveryProfileCreate,
    service: MarketService = Depends(get_market_service),
) -> DiscoveryProfile:
    try:
        return service.create_discovery_profile(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.delete("/api/market/discovery-profiles/{profile_id}", status_code=204)
async def delete_market_discovery_profile(
    profile_id: str,
    service: MarketService = Depends(get_market_service),
) -> Response:
    if not service.delete_discovery_profile(profile_id):
        raise HTTPException(status_code=404, detail="Discovery profile not found.")
    return Response(status_code=204)


@app.post("/api/market/refresh", response_model=MarketRefreshResponse)
async def refresh_market(
    payload: MarketRefreshRequest,
    service: MarketService = Depends(get_market_service),
) -> MarketRefreshResponse:
    return await service.refresh(payload.backfill_days)


@app.get("/api/market/refresh/status", response_model=MarketRefreshResponse | None)
async def market_refresh_status(service: MarketService = Depends(get_market_service)) -> MarketRefreshResponse | None:
    return service.refresh_status()


@app.get("/api/opportunities/{source}/{reference}/details", response_model=OpportunityDetails)
async def opportunity_details(
    source: SourceName,
    reference: str,
    service: OpportunityDetailsService = Depends(get_details_service),
) -> OpportunityDetails:
    return await service.get_details(source, reference)


@app.get("/api/opportunities/{source}/{reference}/brief", response_model=DocumentBriefResponse)
async def cached_document_brief(
    source: SourceName,
    reference: str,
    service: DocumentBriefService = Depends(get_brief_service),
) -> DocumentBriefResponse:
    return service.get_cached_brief(source, reference)


@app.post("/api/opportunities/{source}/{reference}/brief", response_model=DocumentBriefResponse)
async def generate_document_brief(
    source: SourceName,
    reference: str,
    regenerate: bool = False,
    model: str | None = Query(default=None, max_length=80),
    service: DocumentBriefService = Depends(get_brief_service),
) -> DocumentBriefResponse:
    try:
        return await service.generate_brief(source, reference, regenerate=regenerate, model=model)
    except UnsupportedAIModelError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/opportunities/{source}/{reference}/chat", response_model=OpportunityChatThreadResponse)
async def opportunity_chat_thread(
    source: SourceName,
    reference: str,
    service: OpportunityChatService = Depends(get_chat_service),
) -> OpportunityChatThreadResponse:
    return service.get_thread(source, reference)


@app.post("/api/opportunities/{source}/{reference}/chat", response_model=OpportunityChatTurnResponse)
async def ask_about_opportunity(
    source: SourceName,
    reference: str,
    request: OpportunityChatRequest,
    service: OpportunityChatService = Depends(get_chat_service),
) -> OpportunityChatTurnResponse:
    try:
        return await service.ask(source, reference, request.message, model=request.model)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ChatUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ChatGenerationError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post(
    "/api/opportunities/{source}/{reference}/chat/context/refresh",
    response_model=OpportunityChatContextStatus,
)
async def refresh_opportunity_chat_context(
    source: SourceName,
    reference: str,
    service: OpportunityChatService = Depends(get_chat_service),
) -> OpportunityChatContextStatus:
    try:
        return await service.refresh_context(source, reference)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Context refresh failed ({exc.__class__.__name__}).") from exc


@app.delete("/api/opportunities/{source}/{reference}/chat", status_code=204)
async def clear_opportunity_chat(
    source: SourceName,
    reference: str,
    service: OpportunityChatService = Depends(get_chat_service),
) -> Response:
    service.clear_thread(source, reference)
    return Response(status_code=204)
