from __future__ import annotations

import json
from pathlib import Path

from app.catalog import get_software_catalog
from app.models import Opportunity
from app.services.software_matching import SoftwareMatchingService


FIXTURES = Path(__file__).parent / "fixtures" / "software_match_eval.json"


def opportunity(title: str, cpv_codes: list[str] | None = None) -> Opportunity:
    return Opportunity(
        id=title,
        source="demo",
        source_label="Demo",
        title=title,
        summary=title,
        raw_text=title,
        cpv_codes=cpv_codes or [],
    )


def test_greek_terms_are_accent_insensitive() -> None:
    service = SoftwareMatchingService()
    matches = service.match(opportunity("Εγκατάσταση και διασύνδεση συστήματος διαχείρισης εγγράφων"))
    assert matches
    assert matches[0].product.slug == "paperless-ngx"


def test_generic_cpv_family_alone_never_forces_a_match() -> None:
    service = SoftwareMatchingService()
    assert service.match(opportunity("Generic software procurement", ["72000000-5"])) == []
    assert service.match(opportunity("Packaged software", ["48000000-8"])) == []


def test_archived_and_inactive_products_are_hard_excluded() -> None:
    catalog = get_software_catalog().model_copy(deep=True)
    product = next(item for item in catalog.products if item.slug == "documenso")
    product.active = False
    archived = next(item for item in catalog.repository_health if item.slug == "paperless-ngx")
    archived.archived = True
    service = SoftwareMatchingService(catalog)

    assert not any(item.product.slug == "documenso" for item in service.match(opportunity("Electronic signature deployment", ["48311000-1"])))
    assert not any(item.product.slug == "paperless-ngx" for item in service.match(opportunity("Document management deployment", ["48311100-2"])))


def test_negative_terms_apply_a_penalty() -> None:
    catalog = get_software_catalog().model_copy(deep=True)
    category = next(item for item in catalog.categories if item.id == "crm-pipeline")
    category.negative_keywords = ["hardware only"]
    service = SoftwareMatchingService(catalog)
    clean = service.candidates(opportunity("CRM deployment and integration", ["48445000-8"]))[0]
    penalized = service.candidates(opportunity("CRM deployment and integration hardware only", ["48445000-8"]))[0]
    assert penalized.score < clean.score


def test_ties_have_stable_ordering() -> None:
    service = SoftwareMatchingService()
    first = [item.product.slug for item in service.match(opportunity("CRM deployment", ["48445000-8"]))]
    second = [item.product.slug for item in service.match(opportunity("CRM deployment", ["48445000-8"]))]
    assert first == second


def test_new_civic_and_smart_city_use_cases_match_expected_projects() -> None:
    service = SoftwareMatchingService()
    cases = [
        ("Προμήθεια πλατφόρμας για ελεγχόμενη στάθμευση", {"openparking", "parkapi"}),
        ("Σύστημα για έξυπνα υδρόμετρα και τηλεμέτρηση", {"thingsboard", "openremote"}),
        ("Πλατφόρμα για διαχείριση στόλου", {"traccar", "fleetbase"}),
        ("Συντονισμός πόρων πολιτικής προστασίας", {"sahana-eden", "ushahidi"}),
        ("Πλατφόρμα για δημόσια διαβούλευση", {"decidim", "consul-democracy"}),
    ]
    for title, expected in cases:
        slugs = {item.product.slug for item in service.match(opportunity(title), limit=6)}
        assert slugs.intersection(expected), (title, slugs)


def test_golden_eval_recall_and_false_recommendation_rate() -> None:
    service = SoftwareMatchingService()
    cases = json.loads(FIXTURES.read_text(encoding="utf-8"))
    positives = [case for case in cases if case["expected_slugs"]]
    negatives = [case for case in cases if not case["expected_slugs"]]
    positive_hits = 0
    false_recommendations = 0
    for case in cases:
        matches = service.match(opportunity(case["title"], case["cpv_codes"]))
        slugs = {item.product.slug for item in matches}
        if case["expected_slugs"]:
            positive_hits += bool(slugs.intersection(case["expected_slugs"]))
        elif matches:
            false_recommendations += 1

    assert len(cases) >= 40
    assert len(positives) >= 30
    assert len(negatives) >= 10
    assert positive_hits / len(positives) >= 0.85
    assert false_recommendations / len(negatives) <= 0.10
