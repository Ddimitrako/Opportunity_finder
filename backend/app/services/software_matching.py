from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime

from app.catalog import CatalogCategory, CatalogRepositoryHealth, SoftwareCatalog, get_software_catalog
from app.models import (
    Opportunity,
    ServiceRecommendation,
    SoftwareMatch,
    SoftwareMatchDimension,
    SoftwareProduct,
)


MATCH_THRESHOLD = 55
AI_CANDIDATE_THRESHOLD = 30
GENERIC_CPV_PREFIXES = {"48", "72"}
REVIEW_THRESHOLD = 45

STOP_WORDS = {
    "and", "the", "for", "with", "from", "that", "this", "into", "your", "our", "open", "source",
    "software", "system", "platform", "service", "services", "application", "applications", "edition",
    "και", "για", "της", "των", "στο", "στη", "στην", "του", "την", "με", "απο", "προς", "λογισμικο",
    "συστημα", "υπηρεσια", "υπηρεσιες", "εφαρμογη", "εφαρμογες",
}

SERVICE_SIGNALS: dict[str, tuple[str, ...]] = {
    "Deployment": ("deployment", "deploy", "installation", "setup", "εγκατασταση", "εγκατασταση και παραμετροποιηση"),
    "Migration": ("migration", "data migration", "migrate", "μεταπτωση", "μεταφορα δεδομενων"),
    "Integration": ("integration", "api integration", "interoperability", "διασυνδεση", "διαλειτουργικοτητα"),
    "Customization": ("customization", "configuration", "extension", "παραμετροποιηση", "προσαρμογη", "επεκταση"),
    "Training": ("training", "knowledge transfer", "εκπαιδευση", "μεταφορα τεχνογνωσιας"),
    "Support": ("support", "maintenance", "helpdesk", "sla", "υποστηριξη", "συντηρηση", "τεχνικη υποστηριξη"),
    "Managed hosting": ("hosting", "managed service", "cloud hosting", "φιλοξενια", "νεφος"),
    "Security hardening": ("hardening", "security assessment", "penetration test", "ασφαλεια", "σκληρυνση"),
    "Data services": ("data pipeline", "data quality", "data cleansing", "etl", "elt", "δεδομενα", "ποιοτητα δεδομενων"),
}

SERVICE_PRIORITY = (
    "Deployment", "Integration", "Customization", "Migration", "Support", "Training",
    "Managed hosting", "Security hardening", "Data services",
)


@dataclass(frozen=True)
class SemanticMatchHints:
    category_ids: tuple[str, ...] = ()
    capability_terms: tuple[str, ...] = ()
    service_types: tuple[str, ...] = ()
    confidence: str = "medium"
    reason: str = ""
    evidence_ids: tuple[str, ...] = ()


class SoftwareMatchingService:
    def __init__(self, catalog: SoftwareCatalog | None = None):
        self.catalog = catalog or get_software_catalog()
        self.categories = {item.id: item for item in self.catalog.categories}
        self.licenses = {item.id: item for item in self.catalog.licenses}
        self.health = {item.slug: item for item in self.catalog.repository_health}

    @property
    def catalog_version(self) -> str:
        return self.catalog.catalog_version

    def apply(self, opportunity: Opportunity) -> Opportunity:
        matches = self.match(opportunity)
        return opportunity.model_copy(
            update={
                "software_match_status": "matched" if matches else "insufficient_signals",
                "software_matches": matches,
            }
        )

    def candidates(self, opportunity: Opportunity, *, limit: int = 8) -> list[SoftwareMatch]:
        return self.match(opportunity, limit=limit, threshold=AI_CANDIDATE_THRESHOLD)

    def semantic_candidates(
        self,
        opportunity: Opportunity,
        hints: SemanticMatchHints,
        *,
        limit: int = 8,
        threshold: int = REVIEW_THRESHOLD,
    ) -> list[SoftwareMatch]:
        return self.match(opportunity, limit=limit, threshold=threshold, semantic_hints=hints)

    def match(
        self,
        opportunity: Opportunity,
        *,
        limit: int = 3,
        threshold: int = MATCH_THRESHOLD,
        semantic_hints: SemanticMatchHints | None = None,
    ) -> list[SoftwareMatch]:
        text = _opportunity_text(opportunity)
        service_hits = _service_hits(text)
        if semantic_hints:
            for service_type in semantic_hints.service_types:
                if service_type in SERVICE_SIGNALS:
                    service_hits.setdefault(service_type, ["AI semantic screening"])
        matches: list[SoftwareMatch] = []
        for product in self.catalog.products:
            health = self.health.get(product.slug)
            if not product.active or (health and health.archived):
                continue
            match = self._score_product(opportunity, text, product, health, service_hits, semantic_hints)
            if match is not None and match.score >= threshold:
                matches.append(match)
        matches.sort(key=lambda item: (-item.score, -item.product.editorial_score, item.product.name.casefold(), item.product.slug))
        return matches[:limit]

    def _score_product(
        self,
        opportunity: Opportunity,
        text: str,
        product: SoftwareProduct,
        health: CatalogRepositoryHealth | None,
        service_hits: dict[str, list[str]],
        semantic_hints: SemanticMatchHints | None = None,
    ) -> SoftwareMatch | None:
        categories = [self.categories[item] for item in product.category_ids if item in self.categories]
        category_terms = _matched_category_terms(text, categories)
        category_negative = _matched_terms(
            text,
            (term for category in categories for term in category.negative_keywords),
        )
        product_negative = _matched_terms(text, product.negative_keywords)

        cpv_prefixes = _matched_specific_cpv_prefixes(opportunity.cpv_codes, categories)
        generic_cpv = _has_generic_cpv(opportunity.cpv_codes)
        brand_terms = _brand_terms(product)
        matched_brands = _matched_terms(text, brand_terms)
        product_tokens = _product_tokens(product)
        token_hits = sorted(token for token in product_tokens if _contains_term(text, token))
        semantic_categories = set(semantic_hints.category_ids) if semantic_hints else set()
        semantic_category_match = sorted(semantic_categories.intersection(product.category_ids))
        semantic_capability_hits = (
            _matched_terms(
                _normalize(" ".join((product.summary, product.problem, product.ideal_for))),
                semantic_hints.capability_terms,
            )
            if semantic_hints
            else []
        )

        # A broad 48/72 CPV family is never sufficient by itself.
        if not category_terms and not cpv_prefixes and not matched_brands and not semantic_category_match:
            return None

        category_score = 0
        if category_terms:
            category_score = min(40, 37 + 3 * (len(category_terms) - 1))
        if semantic_category_match:
            semantic_category_score = 40 if semantic_hints and semantic_hints.confidence == "high" else 36
            category_score = max(category_score, semantic_category_score)

        cpv_score = 0
        if cpv_prefixes:
            longest = max(len(prefix) for prefix in cpv_prefixes)
            cpv_score = 25 if longest >= 6 else 21 if longest >= 4 else 16

        semantic_product_score = 0
        if semantic_category_match:
            semantic_product_score = 10 if semantic_hints and semantic_hints.confidence == "high" else 7
            semantic_product_score += min(4, len(semantic_capability_hits) * 2)
        product_score = min(15, len(matched_brands) * 10 + len(token_hits) * 3 + semantic_product_score)
        matched_service_types = [item for item in product.service_types if item in service_hits]
        service_score = min(10, len(matched_service_types) * 5)

        maturity_score = min(5, _maturity_points(product) + round(product.editorial_score / 50))
        locale_health_score = _locale_health_points(product, health)

        penalty_reasons: list[str] = []
        penalties = 0
        negative_hits = sorted(set(category_negative + product_negative))
        if negative_hits:
            penalties += min(30, 15 * len(negative_hits))
            penalty_reasons.append(f"Negative context: {', '.join(negative_hits[:3])}")
        if health and health.status == "error":
            penalties += 6
            penalty_reasons.append("Repository verification currently has an error")
        if health and health.license_drift:
            penalties += 5
            penalty_reasons.append("Observed repository license differs from catalog profile")
        if health and _is_stale(health.verified_at):
            penalties += 3
            penalty_reasons.append("Repository health snapshot is stale")

        score = max(
            0,
            min(100, category_score + cpv_score + product_score + service_score + maturity_score + locale_health_score - penalties),
        )

        strong_signals = sum((bool(category_terms or semantic_category_match), bool(cpv_prefixes), bool(matched_brands or semantic_capability_hits)))
        confidence = "high" if score >= 75 and strong_signals >= 2 else "medium" if score >= MATCH_THRESHOLD else "low"

        dimensions = [
            SoftwareMatchDimension(
                key="capability",
                label="Category / capability",
                score=category_score,
                max_score=40,
                reasons=[f"Matched capability: {term}" for term in category_terms[:4]]
                + [f"AI taxonomy category: {category_id}" for category_id in semantic_category_match[:3]],
            ),
            SoftwareMatchDimension(
                key="cpv",
                label="CPV specificity",
                score=cpv_score,
                max_score=25,
                reasons=[f"Specific CPV prefix: {prefix}" for prefix in cpv_prefixes[:3]]
                + (["Only a broad 48/72 CPV family was present"] if generic_cpv and not cpv_prefixes else []),
            ),
            SoftwareMatchDimension(
                key="product",
                label="Product relevance",
                score=product_score,
                max_score=15,
                reasons=[f"Product term: {term}" for term in (matched_brands + token_hits)[:4]]
                + [f"Semantic capability: {term}" for term in semantic_capability_hits[:3]],
            ),
            SoftwareMatchDimension(
                key="services",
                label="Service opportunity",
                score=service_score,
                max_score=10,
                reasons=[f"Requested service: {item}" for item in matched_service_types],
            ),
            SoftwareMatchDimension(
                key="maturity",
                label="Maturity / editorial strength",
                score=maturity_score,
                max_score=5,
                reasons=[f"{product.maturity} product; editorial score {product.editorial_score}/100"],
            ),
            SoftwareMatchDimension(
                key="locale_health",
                label="Locale / repository health",
                score=locale_health_score,
                max_score=5,
                reasons=_health_reasons(product, health),
            ),
        ]
        if penalties:
            dimensions.append(
                SoftwareMatchDimension(
                    key="penalties",
                    label="Penalties",
                    score=-penalties,
                    max_score=0,
                    reasons=penalty_reasons,
                )
            )

        signals = [f"Capability: {term}" for term in category_terms[:3]]
        if semantic_hints and semantic_category_match:
            signals.extend(f"AI category: {category_id}" for category_id in semantic_category_match[:2])
            if semantic_hints.reason:
                signals.insert(0, semantic_hints.reason)
        signals.extend(f"CPV: {prefix}" for prefix in cpv_prefixes[:2])
        signals.extend(f"Product: {term}" for term in matched_brands[:2])
        signals.extend(f"Service: {item}" for item in matched_service_types[:3])

        return SoftwareMatch(
            product=product,
            score=score,
            confidence=confidence,
            source="ai_refined" if semantic_hints else "deterministic",
            dimensions=dimensions,
            matched_signals=signals,
            service_recommendations=_service_recommendations(product, service_hits),
            caveats=_caveats(product, health, self.licenses.get(product.license_id)),
            evidence_ids=list(semantic_hints.evidence_ids) if semantic_hints else [],
            catalog_version=self.catalog_version,
        )


def _normalize(value: str) -> str:
    text = unicodedata.normalize("NFD", value.casefold())
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")
    text = re.sub(r"[^\w]+", " ", text, flags=re.UNICODE)
    tokens = [token[:-1] if len(token) > 5 and token.endswith("σ") else token for token in text.split()]
    return " ".join(tokens)


def _opportunity_text(opportunity: Opportunity) -> str:
    return _normalize(
        " ".join(
            str(part)
            for part in (
                opportunity.title,
                opportunity.summary,
                opportunity.raw_text,
                opportunity.buyer,
                opportunity.buyer_type or "",
                opportunity.procedure_type or "",
                opportunity.notice_type or "",
                opportunity.status_label or "",
                opportunity.package_match,
                " ".join(opportunity.matched_keywords),
                " ".join(str(value) for value in opportunity.source_payload.values() if isinstance(value, (str, int, float))),
            )
            if part
        )
    )


def _contains_term(text: str, term: str) -> bool:
    normalized = _normalize(term)
    return bool(normalized and f" {normalized} " in f" {text} ")


def _matched_terms(text: str, terms) -> list[str]:
    output: list[str] = []
    for raw in terms:
        term = str(raw).strip()
        if term and _contains_term(text, term) and term not in output:
            output.append(term)
    return output


def _matched_category_terms(text: str, categories: list[CatalogCategory]) -> list[str]:
    return _matched_terms(text, (term for category in categories for term in (*category.keywords_en, *category.keywords_el)))


def _cpv_digits(value: str) -> str:
    return "".join(char for char in value if char.isdigit())


def _matched_specific_cpv_prefixes(codes: list[str], categories: list[CatalogCategory]) -> list[str]:
    output: set[str] = set()
    for category in categories:
        for prefix in category.cpv_prefixes:
            digits = _cpv_digits(prefix)
            if not digits or digits in GENERIC_CPV_PREFIXES:
                continue
            if any(_cpv_digits(code).startswith(digits) for code in codes):
                output.add(digits)
    return sorted(output, key=lambda item: (-len(item), item))


def _has_generic_cpv(codes: list[str]) -> bool:
    return any(any(_cpv_digits(code).startswith(prefix) for prefix in GENERIC_CPV_PREFIXES) for code in codes)


def _brand_terms(product: SoftwareProduct) -> list[str]:
    generic = {"community", "community edition", "open source", "open source edition"}
    values = [product.name, product.slug.replace("-", " "), *product.extra_keywords_en, *product.extra_keywords_el]
    return [value for value in dict.fromkeys(values) if _normalize(value) not in generic and len(_normalize(value)) >= 3]


def _product_tokens(product: SoftwareProduct) -> set[str]:
    text = _normalize(" ".join((product.summary, product.problem, product.ideal_for)))
    return {token for token in text.split() if len(token) >= 5 and token not in STOP_WORDS}


def _service_hits(text: str) -> dict[str, list[str]]:
    return {
        service_type: hits
        for service_type, terms in SERVICE_SIGNALS.items()
        if (hits := _matched_terms(text, terms))
    }


def _service_recommendations(product: SoftwareProduct, service_hits: dict[str, list[str]]) -> list[ServiceRecommendation]:
    output: list[ServiceRecommendation] = []
    for service_type in SERVICE_PRIORITY:
        if service_type not in product.service_types:
            continue
        hits = service_hits.get(service_type, [])
        output.append(
            ServiceRecommendation(
                service_type=service_type,
                label=service_type,
                confidence="recommended" if hits else "possible",
                reasons=[f"Tender signal: {term}" for term in hits[:2]]
                if hits
                else ["Supported by the catalog, but not explicitly requested in the opportunity"],
            )
        )
    recommended = [item for item in output if item.confidence == "recommended"]
    possible = [item for item in output if item.confidence == "possible"]
    return (recommended + possible)[:4]


def _maturity_points(product: SoftwareProduct) -> int:
    return {"anchor": 3, "established": 2, "niche-leader": 2}.get(product.maturity, 1)


def _locale_health_points(product: SoftwareProduct, health: CatalogRepositoryHealth | None) -> int:
    locale = {"verified": 2, "partial": 1}.get(product.greek_support, 0)
    repository = 0
    if health and health.status == "verified":
        repository += 2
    if health and not health.license_drift and not health.archived:
        repository += 1
    return min(5, locale + repository)


def _health_reasons(product: SoftwareProduct, health: CatalogRepositoryHealth | None) -> list[str]:
    reasons = [f"Greek support: {product.greek_support}"]
    if health:
        reasons.append(f"Repository status: {health.status}")
        if health.stars is not None:
            reasons.append(f"Repository stars snapshot: {health.stars}")
    return reasons


def _is_stale(value: str) -> bool:
    try:
        verified = datetime.fromisoformat(value.replace("Z", "+00:00")).date()
        return (date.today() - verified).days > 365
    except ValueError:
        return True


def _caveats(product: SoftwareProduct, health: CatalogRepositoryHealth | None, license_profile) -> list[str]:
    caveats: list[str] = []
    if product.delivery_fit == "partner_required":
        caveats.append("Partner or specialist implementation team is recommended.")
    elif product.delivery_fit == "small_team":
        caveats.append("Delivery is suitable for a small implementation team.")
    if product.edition_boundary:
        caveats.append(product.edition_boundary)
    if license_profile:
        caveats.append(f"License: {license_profile.name} ({license_profile.family}). Review obligations before delivery.")
    if product.greek_support in {"partial", "unknown", "unavailable"}:
        caveats.append(f"Greek-language support is {product.greek_support}.")
    if health and health.license_drift:
        caveats.append("Repository license drift requires manual verification.")
    if health and health.status != "verified":
        caveats.append(f"Repository health status is {health.status}; verify manually.")
    return caveats
