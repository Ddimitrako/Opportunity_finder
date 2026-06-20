from urllib.parse import urlparse

import httpx
from fastapi import Depends, FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware

from app.config import Settings, get_settings
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
    NeedPatternRequest,
    NeedPatternResponse,
    OpportunityDetails,
    ProcurementSearchRequest,
    SearchResponse,
    SourceName,
)
from app.scoring import PACKAGES
from app.services.bookmarks import BookmarkService
from app.services.briefs import DocumentBriefService
from app.services.buyer_intelligence import BuyerIntelligenceService
from app.services.details import OpportunityDetailsService
from app.services.opportunities import OpportunityService
from app.services.patterns import PatternDiscoveryService

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


def get_buyer_intelligence_service(settings: Settings = Depends(get_settings)) -> BuyerIntelligenceService:
    return BuyerIntelligenceService(settings)


def get_pattern_service() -> PatternDiscoveryService:
    return PatternDiscoveryService()


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
async def config() -> ConfigResponse:
    return ConfigResponse(
        default_cpv_codes=DEFAULT_CPV_CODES,
        default_keywords=DEFAULT_KEYWORDS,
        packages=PACKAGES,
        sources=[
            {"id": "khmdhs", "label": "ΚΗΜΔΗΣ"},
            {"id": "ted", "label": "TED"},
            {"id": "demo", "label": "Demo patterns"},
        ],
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
) -> SearchResponse:
    return await service.search(request)


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
    service: DocumentBriefService = Depends(get_brief_service),
) -> DocumentBriefResponse:
    return await service.generate_brief(source, reference)
