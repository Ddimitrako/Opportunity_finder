from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from app.models import SoftwareProduct


CATALOG_PATH = Path(__file__).resolve().parent / "data" / "software_catalog.json"


class CatalogDepartment(BaseModel):
    id: str
    name: str
    short_name: str
    description: str
    icon: str


class CatalogCategory(BaseModel):
    id: str
    department_id: str
    name: str
    description: str
    cpv_prefixes: list[str] = Field(default_factory=list)
    keywords_en: list[str] = Field(default_factory=list)
    keywords_el: list[str] = Field(default_factory=list)
    negative_keywords: list[str] = Field(default_factory=list)


class CatalogLicense(BaseModel):
    id: str
    spdx: str
    name: str
    family: Literal["permissive", "weak-copyleft", "copyleft", "network-copyleft"]
    osi_approved: bool = True
    summary: str
    obligations: list[str] = Field(default_factory=list)
    evidence: str


class CatalogRepositoryHealth(BaseModel):
    slug: str
    repo: str
    stars: int | None = None
    latest_release: str | None = None
    last_activity: str | None = None
    archived: bool = False
    observed_license: str | None = None
    license_drift: bool = False
    verified_at: str
    status: Literal["verified", "pending-refresh", "error"]


class CatalogBusinessUseCase(BaseModel):
    slug: str
    title_en: str
    title_el: str
    description_en: str
    description_el: str
    business_problem_en: str
    business_problem_el: str
    department_id: str
    category_ids: list[str] = Field(default_factory=list)
    fit: Literal["direct", "partial", "foundation"]
    status: Literal["active"] = "active"


class CatalogUseCaseSolution(BaseModel):
    use_case_slug: str
    project_slug: str
    rank: int = Field(ge=1, le=2)
    fit: Literal["direct", "partial", "foundation"]
    rationale_en: str
    rationale_el: str


class SoftwareCatalog(BaseModel):
    schema_version: int = 2
    catalog_version: str
    source: dict[str, str]
    departments: list[CatalogDepartment]
    categories: list[CatalogCategory]
    licenses: list[CatalogLicense]
    repository_health: list[CatalogRepositoryHealth]
    business_use_cases: list[CatalogBusinessUseCase] = Field(default_factory=list)
    use_case_solutions: list[CatalogUseCaseSolution] = Field(default_factory=list)
    products: list[SoftwareProduct]

    @model_validator(mode="after")
    def validate_catalog_version(self) -> "SoftwareCatalog":
        expected = catalog_version(self.model_dump(mode="json", exclude={"catalog_version"}))
        if self.catalog_version != expected:
            raise ValueError(
                f"software catalog version mismatch: expected {expected}, found {self.catalog_version}"
            )
        return self


def catalog_version(payload: dict[str, Any]) -> str:
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    return f"v{payload.get('schema_version', 1)}-{digest[:16]}"


def load_software_catalog(path: Path = CATALOG_PATH) -> SoftwareCatalog:
    if not path.exists():
        raise RuntimeError(f"Software catalog snapshot is missing: {path}")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return SoftwareCatalog.model_validate(raw)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise RuntimeError(f"Software catalog snapshot is invalid: {exc}") from exc


@lru_cache(maxsize=1)
def get_software_catalog() -> SoftwareCatalog:
    return load_software_catalog()
