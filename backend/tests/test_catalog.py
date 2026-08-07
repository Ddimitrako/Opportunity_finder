from __future__ import annotations

import json
from pathlib import Path

import pytest
from openpyxl import load_workbook

from app.catalog import CATALOG_PATH, get_software_catalog
from app.catalog_import import DEFAULT_WORKBOOK, workbook_payload


def test_catalog_snapshot_has_expected_counts_and_version() -> None:
    catalog = get_software_catalog()
    assert catalog.schema_version == 2
    assert len(catalog.products) == 100
    assert len(catalog.departments) == 13
    assert len(catalog.categories) == 64
    assert len(catalog.licenses) == 15
    assert len(catalog.repository_health) == 100
    assert len(catalog.business_use_cases) == 32
    assert len(catalog.use_case_solutions) == 62
    assert catalog.catalog_version.startswith("v2-")
    assert len({item.slug for item in catalog.products}) == 100
    assert len({item.repository.casefold() for item in catalog.products}) == 100


def test_excel_and_runtime_json_are_identical() -> None:
    payload = workbook_payload(DEFAULT_WORKBOOK)
    snapshot = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    assert payload == snapshot


def test_workbook_validator_rejects_duplicate_product_slug(tmp_path: Path) -> None:
    workbook = load_workbook(DEFAULT_WORKBOOK)
    products = workbook["Products"]
    products["A3"] = products["A2"].value
    invalid = tmp_path / "invalid.xlsx"
    workbook.save(invalid)

    with pytest.raises(ValueError, match="Duplicate product slug"):
        workbook_payload(invalid)
