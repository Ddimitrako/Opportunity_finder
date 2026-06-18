from __future__ import annotations

from datetime import date

from app.models import FitBand, Opportunity, ProcurementSearchRequest

SOFTWARE_CPV_PREFIXES = ("48", "72")
GENERIC_SOFTWARE_PACKAGE = "Custom software"

TARGET_BUYER_WORDS = (
    "δήμος",
    "δημου",
    "περιφέρεια",
    "περιφερεια",
    "πανεπιστήμιο",
    "ελκε",
    "μουσείο",
    "πολιτισ",
    "ερευνη",
    "οφυπεκα",
    "περιβαλλον",
)

HEAVY_BUYER_WORDS = (
    "υπουργείο εθνικής άμυνας",
    "λιμενικό",
    "ηδικα",
    "γγπσ",
    "κοινωνία της πληροφορίας",
)

RED_FLAG_PATTERNS = (
    ("ISO 27001 / βαριά πιστοποίηση", ("iso 27001", "iso27001", "πιστοποίηση iso")),
    ("Υψηλές απαιτήσεις κύκλου εργασιών", ("κύκλο εργασιών", "turnover", "οικονομική επάρκεια")),
    ("Μεγάλη αποκλειστική ομάδα", ("full-time", "πλήρους απασχόλησης", "τουλάχιστον 5")),
    ("Mission-critical ή διαβαθμισμένο περιβάλλον", ("διαβαθμ", "mission critical", "classified")),
    ("Προμήθεια έτοιμων αδειών αντί custom development", ("άδειες χρήσης", "licenses", "licences")),
)


PACKAGES = [
    {
        "name": "Public Applications Platform",
        "label": "Αιτήσεις / workflows",
        "keywords": ("αίτηση", "αιτήσεις", "δικαιολογητικά", "workflow", "status", "πλατφόρμα"),
    },
    {
        "name": "Field Monitoring & Reporting App",
        "label": "Monitoring / πεδίο",
        "keywords": ("monitoring", "παρακολούθηση", "επιτήρηση", "χάρτης", "incident", "γεω"),
    },
    {
        "name": "Cultural / Multimedia Digital Experience",
        "label": "Πολιτισμός / multimedia",
        "keywords": ("μουσείο", "πολιτισ", "multimedia", "πολυμέσα", "cms", "διαδρομή"),
    },
    {
        "name": "Dashboard & Data Intelligence",
        "label": "Dashboards / analytics",
        "keywords": ("dashboard", "αναφορές", "στατιστικά", "kpi", "analytics", "δείκτες"),
    },
    {
        "name": "Document & Case Management",
        "label": "Έγγραφα / υποθέσεις",
        "keywords": ("έγγραφα", "document", "case", "υπόθεση", "πρωτόκολλο", "dms"),
    },
]

PACKAGE_NAMES = {package["name"] for package in PACKAGES}

BROAD_CPV_CATEGORIES = (
    (("15", "55"), "Food / catering"),
    (("30", "32", "48"), "IT equipment / software supplies"),
    (("34", "60", "63"), "Transport / logistics"),
    (("35",), "Security / defence supplies"),
    (("38",), "Laboratory / measurement equipment"),
    (("39",), "Furniture / facility supplies"),
    (("42", "43"), "Industrial equipment"),
    (("44", "45"), "Construction / works"),
    (("50",), "Repair / maintenance services"),
    (("66",), "Financial / insurance services"),
    (("71",), "Engineering / technical services"),
    (("73",), "Research / consulting services"),
    (("79",), "Business services"),
    (("80",), "Training / education"),
    (("85",), "Health / social care"),
    (("90",), "Waste / environmental services"),
    (("92",), "Culture / recreation"),
)

TEXT_CATEGORIES = (
    (("σαλάτ", "salad", "τρόφι", "τροφ", "φαγη", "σίτιση", "catering"), "Food / catering"),
    (("υπολογιστ", "laptop", "desktop", "εκτυπωτ", "printer", "server", "δικτυακ", "router"), "IT equipment / software supplies"),
    (("όχημα", "οχημα", "μεταφορ", "logistics"), "Transport / logistics"),
)


def score_opportunity(opportunity: Opportunity, request: ProcurementSearchRequest) -> Opportunity:
    text = " ".join(
        [
            opportunity.title,
            opportunity.summary,
            opportunity.raw_text,
            opportunity.buyer,
            opportunity.buyer_type or "",
            opportunity.procedure_type or "",
        ]
    ).casefold()
    score = 0
    reasons: list[str] = []
    red_flags: list[str] = []

    target_cpvs = {code.split("-")[0] for code in request.cpv_codes}
    opportunity_cpvs = {code.split("-")[0] for code in opportunity.cpv_codes}
    if target_cpvs.intersection(opportunity_cpvs):
        score += 25
        reasons.append("Σχετικός CPV για custom software ή web/data εφαρμογές")

    if opportunity.budget is not None:
        if 10_000 <= opportunity.budget <= 80_000:
            score += 20
            reasons.append("Budget στο γλυκό σημείο μικρής ομάδας")
        elif request.budget_min <= opportunity.budget <= request.budget_max:
            score += 12
            reasons.append("Budget μέσα στα φίλτρα αναζήτησης")
        elif opportunity.budget > 250_000:
            score -= 15
            red_flags.append("Προϋπολογισμός πάνω από 250k")

    matched_keywords = sorted({keyword for keyword in request.keywords if keyword.casefold() in text})
    if matched_keywords:
        score += min(15, 5 + len(matched_keywords) * 2)
        reasons.append("Ταιριάζει με λέξεις-κλειδιά full-stack έργου")

    buyer_text = f"{opportunity.buyer} {opportunity.buyer_type or ''}".casefold()
    if any(word in buyer_text for word in TARGET_BUYER_WORDS):
        score += 10
        reasons.append("Φορέας με καλό fit για μικρό εξειδικευμένο ανάδοχο")
    if any(word in buyer_text for word in HEAVY_BUYER_WORDS):
        score -= 8
        red_flags.append("Φορέας/περιβάλλον με μεγαλύτερη διοικητική τριβή")

    if opportunity.deadline:
        days_left = (opportunity.deadline - date.today()).days
        if days_left >= 15:
            score += 10
            reasons.append("Υπάρχει χρόνος για ανάγνωση φακέλου και προσφορά")
        elif days_left < 5:
            score -= 10
            red_flags.append("Πολύ κοντινή προθεσμία")

    for label, patterns in RED_FLAG_PATTERNS:
        if any(pattern in text for pattern in patterns):
            score -= 15
            red_flags.append(label)

    if not red_flags:
        score += 10
        reasons.append("Δεν εντοπίστηκαν προφανή red flags στο διαθέσιμο κείμενο")

    package_match = choose_package(text, opportunity.cpv_codes)
    if package_match in PACKAGE_NAMES:
        score += 5
        reasons.append(f"Μπορεί να πακεταριστεί ως {package_match}")

    opportunity.fit_score = max(0, min(100, score))
    opportunity.fit_band = fit_band(opportunity.fit_score)
    opportunity.recommendation = recommendation(opportunity.fit_score)
    opportunity.score_reasons = reasons[:6]
    opportunity.red_flags = red_flags[:6]
    opportunity.matched_keywords = matched_keywords[:8]
    opportunity.package_match = package_match
    return opportunity


def fit_band(score: int) -> FitBand:
    if score >= 80:
        return "Bid candidate"
    if score >= 60:
        return "Worth reading"
    if score >= 40:
        return "Monitor only"
    return "Ignore"


def recommendation(score: int) -> str:
    if score >= 80:
        return "Bid candidate"
    if score >= 60:
        return "Read tender docs"
    if score >= 40:
        return "Monitor"
    return "Ignore"


def choose_package(text: str, cpv_codes: list[str] | None = None) -> str:
    scores: list[tuple[int, str]] = []
    for package in PACKAGES:
        hits = sum(1 for keyword in package["keywords"] if keyword in text)
        scores.append((hits, package["name"]))
    hits, name = max(scores, key=lambda item: item[0])
    if hits:
        return name
    if _has_software_cpv(cpv_codes or []) or _looks_software_by_text(text):
        return GENERIC_SOFTWARE_PACKAGE
    return _broad_category(text, cpv_codes or [])


def _has_software_cpv(cpv_codes: list[str]) -> bool:
    return any(_cpv_digits(code).startswith(SOFTWARE_CPV_PREFIXES) for code in cpv_codes)


def _looks_software_by_text(text: str) -> bool:
    return any(term in text for term in ("software", "λογισμ", "πληροφοριακ", "πλατφόρ", "πλατφορ", "εφαρμογ", "portal", "dashboard", "ψηφιακ"))


def _broad_category(text: str, cpv_codes: list[str]) -> str:
    for prefixes, label in BROAD_CPV_CATEGORIES:
        if any(_cpv_digits(code).startswith(prefixes) for code in cpv_codes):
            return label
    for terms, label in TEXT_CATEGORIES:
        if any(term in text for term in terms):
            return label
    return "Other procurement"


def _cpv_digits(code: str) -> str:
    return "".join(char for char in code if char.isdigit())
