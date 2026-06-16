from datetime import date, timedelta

from app.models import Opportunity


def demo_opportunities() -> list[Opportunity]:
    today = date.today()
    return [
        Opportunity(
            id="demo-green-taxi",
            source="demo",
            source_label="Demo pattern",
            title="Ανάπτυξη και υποστήριξη πλατφόρμας αιτήσεων για δημόσια δράση",
            buyer="Επιτελική Δομή ΕΣΠΑ - Υπουργείο Περιβάλλοντος",
            buyer_type="Κεντρική διοίκηση / δημόσια δράση",
            procedure_type="Πρόσκληση υποβολής προσφοράς",
            cpv_codes=["72212000-4", "72262000-9"],
            budget=38_500,
            deadline=today + timedelta(days=28),
            published_at=today - timedelta(days=4),
            location="Αθήνα",
            platform_label="Demo pattern",
            source_reference="demo-green-taxi",
            status_label="Open",
            notice_type="Call for offers",
            summary=(
                "Web εφαρμογή αιτήσεων με ρόλους χρηστών, upload δικαιολογητικών, "
                "status tracking, admin review, notifications και exports."
            ),
            raw_text="ανάπτυξη εφαρμογής πλατφόρμα αιτήσεις δικαιολογητικά dashboard reports API",
        ),
        Opportunity(
            id="demo-monitoring",
            source="demo",
            source_label="Demo pattern",
            title="Mobile-first εφαρμογή παρακολούθησης και αναφορών πεδίου",
            buyer="Οργανισμός Φυσικού Περιβάλλοντος και Κλιματικής Αλλαγής",
            buyer_type="Περιβαλλοντικός φορέας",
            procedure_type="Απευθείας ανάθεση",
            cpv_codes=["72212100-0", "72421000-7"],
            budget=14_800,
            deadline=today + timedelta(days=11),
            published_at=today - timedelta(days=6),
            location="Θεσσαλονίκη",
            platform_label="Demo pattern",
            source_reference="demo-monitoring",
            status_label="Open",
            notice_type="Direct award invitation",
            summary=(
                "Καταγραφή συμβάντων από πεδίο, geolocation, φωτογραφίες, χάρτης, "
                "πίνακας ελέγχου και αυτόματες μηνιαίες αναφορές."
            ),
            raw_text="monitoring παρακολούθηση χάρτης field reporting dashboard φωτογραφίες",
        ),
        Opportunity(
            id="demo-culture",
            source="demo",
            source_label="Demo pattern",
            title="Ψηφιακή πολιτιστική διαδρομή με CMS, QR σελίδες και multimedia υλικό",
            buyer="Δημοτικό Μουσείο Σύγχρονης Ιστορίας",
            buyer_type="Πολιτιστικός φορέας",
            procedure_type="Πρόσκληση εκδήλωσης ενδιαφέροντος",
            cpv_codes=["72413000-8", "72212224-5"],
            budget=26_000,
            deadline=today - timedelta(days=8),
            published_at=today - timedelta(days=20),
            location="Πάτρα",
            platform_label="Demo pattern",
            source_reference="demo-culture",
            status_label="Closed",
            notice_type="Expired call",
            summary=(
                "Multilingual CMS, interactive map, audio/video guides, QR landing pages, "
                "analytics και απλό admin panel για επιμελητές περιεχομένου."
            ),
            raw_text="πολιτισμός μουσείο multimedia cms χάρτης audio guide qr analytics",
        ),
        Opportunity(
            id="demo-edup-ai",
            source="demo",
            source_label="Demo pattern",
            title="Έξυπνο σύστημα forecasting εκπαιδευτικής πολιτικής και BI dashboards",
            buyer="Υπουργείο Παιδείας",
            buyer_type="Κεντρική διοίκηση",
            procedure_type="Ανοικτός διεθνής διαγωνισμός",
            cpv_codes=["72212460-1", "72212482-0"],
            budget=3_000_000,
            deadline=today + timedelta(days=40),
            published_at=today - timedelta(days=12),
            location="Αθήνα",
            platform_label="Demo pattern",
            source_reference="demo-edup-ai",
            status_label="Contract award",
            notice_type="Contract award notice",
            summary=(
                "Μεγάλο έργο data platform, predictive analytics, integrations, SLA, "
                "ασφάλεια και εκτεταμένη τεκμηρίωση."
            ),
            raw_text="forecasting business intelligence dashboard ISO 27001 κύκλο εργασιών full-time",
        ),
    ]
