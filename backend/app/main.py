from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import Settings, get_settings
from app.models import (
    ActivityRequest,
    ActivityResponse,
    ConfigResponse,
    DEFAULT_CPV_CODES,
    DEFAULT_KEYWORDS,
    HealthResponse,
    OpportunityDetails,
    ProcurementSearchRequest,
    SearchResponse,
    SourceName,
)
from app.scoring import PACKAGES
from app.services.details import OpportunityDetailsService
from app.services.opportunities import OpportunityService

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


@app.get("/api/health", response_model=HealthResponse)
async def health(settings: Settings = Depends(get_settings)) -> HealthResponse:
    return HealthResponse(
        status="ok",
        app=settings.app_name,
        ai_enabled=bool(settings.openai_api_key),
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


@app.get("/api/opportunities/{source}/{reference}/details", response_model=OpportunityDetails)
async def opportunity_details(
    source: SourceName,
    reference: str,
    service: OpportunityDetailsService = Depends(get_details_service),
) -> OpportunityDetails:
    return await service.get_details(source, reference)
