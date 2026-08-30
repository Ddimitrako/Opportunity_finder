from __future__ import annotations

import json
import re
import sqlite3
import unicodedata
from contextlib import closing
from datetime import date, datetime
from pathlib import Path

from app.config import Settings
from app.models import (
    AIWorkflowSettings,
    CompanyProfile,
    Opportunity,
    PursuitAssessment,
    PursuitFactor,
    PursuitFeedback,
    PursuitFeedbackRequest,
    PursuitListResponse,
    PursuitRecord,
    PursuitUpdateRequest,
    PursuitUpsertRequest,
    SolutionRoute,
)
from app.services.bookmarks import _resolve_db_path


RULES_VERSION = "pursuit-v1-2026-08"

CLOSED_TERMS = (
    "contract award notice", "contract awarded", "signed contract", "payment order",
    "απόφαση ανάθεσης", "αποφαση αναθεσης", "κατακύρωση", "κατακυρωση",
    "υπογεγραμμένη σύμβαση", "υπογεγραμμενη συμβαση", "εντολή πληρωμής", "εντολη πληρωμης",
)
NAMED_INVITATION_TERMS = (
    "πρόσκληση υποβολής προσφοράς προς", "προς τον οικονομικό φορέα",
    "καλεί την εταιρεία", "καλεί τον οικονομικό φορέα",
    "invitation to submit an offer to", "invites the economic operator",
)
CONTINUITY_TERMS = (
    "υφιστάμεν", "υφισταμεν", "σε συνέχεια", "προηγούμενη σύμβαση",
    "συντήρηση του", "συντηρηση του", "επέκταση του", "επεκταση του",
    "existing system", "previous contract", "continuation of", "maintenance of the existing",
)
HEAVY_REQUIREMENT_TERMS = (
    "iso 27001", "iso27001", "κύκλο εργασιών", "κυκλο εργασιων", "annual turnover",
    "τουλάχιστον 5", "τουλαχιστον 5", "πενταμελή ομάδα", "full-time team",
    "διαβαθμισ", "classified", "24x7", "24/7",
)
LICENSE_HARDWARE_TERMS = (
    "προμήθεια αδειών", "προμηθεια αδειων", "άδειες χρήσης", "αδειες χρησης",
    "license supply", "licenses only", "laptops", "φορητών υπολογιστών",
    "εξοπλισμού πληροφορικής", "εξοπλισμου πληροφορικης",
)
DASHBOARD_TERMS = ("dashboard", "πίνακας ελέγχου", "πινακας ελεγχου", "kpi", "analytics", "αναφορές", "αναφορες")
INTEGRATION_TERMS = ("integration", "διασύνδεση", "διασυνδεση", "api", "etl", "migration", "μετάπτωση", "μεταπτωση")
CUSTOM_WEB_TERMS = ("web εφαρμογ", "portal", "workflow", "πλατφόρ", "πλατφορ", "πληροφοριακό σύστημα", "πληροφοριακο συστημα")


def _normalize(value: str) -> str:
    text = unicodedata.normalize("NFD", value.casefold())
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")
    return re.sub(r"\s+", " ", text)


def _text(opportunity: Opportunity) -> str:
    return _normalize(" ".join(
        part for part in (
            opportunity.title,
            opportunity.summary,
            opportunity.raw_text,
            opportunity.procedure_type or "",
            opportunity.notice_type or "",
            opportunity.status_label or "",
        ) if part
    ))


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(_normalize(term) in text for term in terms)


def _is_named_invitation(text: str) -> bool:
    if not _contains_any(text, NAMED_INVITATION_TERMS):
        return False
    generic_invitees = (
        "προς τους οικονομικούς φορείς", "προς οικονομικούς φορείς",
        "προς κάθε ενδιαφερόμενο", "προς όλους τους ενδιαφερόμενους",
        "to all economic operators", "open invitation",
    )
    return not _contains_any(text, generic_invitees)


def infer_solution_route(opportunity: Opportunity) -> SolutionRoute:
    text = _text(opportunity)
    if _contains_any(text, LICENSE_HARDWARE_TERMS):
        return "license_hardware"
    if opportunity.software_matches:
        services = {
            service.service_type.casefold()
            for match in opportunity.software_matches[:3]
            for service in match.service_recommendations
        }
        if {"customization", "integration"}.intersection(services):
            return "oss_extension"
        return "oss_configuration"
    if _contains_any(text, DASHBOARD_TERMS):
        return "custom_dashboard"
    if _contains_any(text, INTEGRATION_TERMS):
        return "integration_data"
    if _contains_any(text, CUSTOM_WEB_TERMS):
        return "custom_web_app"
    return "unknown"


def infer_candidate_type(opportunity: Opportunity) -> str:
    stage = (opportunity.procurement_stage or "").casefold()
    reference = (opportunity.source_reference or "").upper()
    text = _text(opportunity)
    if stage in {"award", "contract", "payment", "historical"} or any(token in reference for token in ("AWRD", "SYMV", "PAY")):
        return "historical"
    if opportunity.source == "khmdhs" and (stage in {"request", "approved_request", "planning"} or "REQ" in reference):
        return "position_early"
    if stage in {"notice", "competition", "open"} or "PROC" in reference:
        return "bid_now"
    if opportunity.source == "ted" and opportunity.deadline:
        return "bid_now"
    return opportunity.candidate_type if opportunity.candidate_type != "review" else "review"


class PursuitAssessmentService:
    def assess(self, opportunity: Opportunity, profile: CompanyProfile) -> Opportunity:
        text = _text(opportunity)
        candidate_type = infer_candidate_type(opportunity)
        route = infer_solution_route(opportunity)
        hard_gates: list[str] = []
        risks: list[str] = []
        top_reasons: list[str] = []

        lifecycle_text = _normalize(" ".join(filter(None, (
            opportunity.title, opportunity.status_label, opportunity.notice_type,
        ))))
        named_invitation = _is_named_invitation(text)
        closed = candidate_type == "historical" or _contains_any(lifecycle_text, CLOSED_TERMS)
        if opportunity.deadline and opportunity.deadline < date.today():
            closed = True
            hard_gates.append("Η προθεσμία έχει λήξει.")
        if named_invitation:
            hard_gates.append("Η πρόσκληση φαίνεται να απευθύνεται σε κατονομαζόμενο οικονομικό φορέα.")
        if closed and not any("προθεσμία" in item for item in hard_gates):
            hard_gates.append("Η διαδικασία βρίσκεται σε κλειστό ή ιστορικό στάδιο.")
        if route == "license_hardware":
            hard_gates.append("Το αντικείμενο είναι κυρίως άδειες ή εξοπλισμός και όχι παραδοτέο software service.")

        access_reasons: list[str] = []
        if hard_gates:
            access = 0
        elif candidate_type == "bid_now":
            if opportunity.deadline:
                days = (opportunity.deadline - date.today()).days
                access = 100 if days >= 14 else 85 if days >= 7 else 60 if days >= 3 else 35
                access_reasons.append(f"Επιβεβαιωμένο παράθυρο υποβολής: {days} ημέρες.")
            else:
                access = 50
                access_reasons.append("Υπάρχει notice, αλλά δεν επιβεβαιώθηκε deadline.")
                risks.append("Άγνωστη προθεσμία υποβολής.")
        elif candidate_type == "position_early":
            access = 70
            access_reasons.append("Πρώιμο δημόσιο request: κατάλληλο για positioning πριν από το notice.")
        elif candidate_type == "outbound":
            access = 65
            access_reasons.append("Συγκεκριμένη ιδιωτική ανάγκη με outbound διαδρομή.")
        else:
            access = 45
            access_reasons.append("Δεν επιβεβαιώθηκε ακόμη η διαδρομή πρόσβασης.")

        win = 55
        win_reasons: list[str] = []
        if candidate_type == "position_early":
            win += 15
            win_reasons.append("Το πρώιμο στάδιο επιτρέπει προετοιμασία πριν διαμορφωθεί η πρόσκληση.")
        if opportunity.budget is not None and profile.minimum_viable_budget <= opportunity.budget <= profile.quick_win_budget_max:
            win += 8
            win_reasons.append("Το budget βρίσκεται στο quick-win εύρος.")
        continuity = _contains_any(text, CONTINUITY_TERMS)
        if continuity:
            win -= 30
            risks.append("Πιθανό incumbent advantage ή συνέχεια υφιστάμενου συστήματος.")
        heavy_requirement = _contains_any(text, HEAVY_REQUIREMENT_TERMS)
        if heavy_requirement:
            win -= 20
            risks.append("Εντοπίστηκαν πιθανές βαριές απαιτήσεις συμμετοχής ή λειτουργίας.")
        if not opportunity.buyer or opportunity.buyer == "Unknown buyer":
            win -= 10
            risks.append("Δεν έχει ταυτοποιηθεί καθαρά ο buyer.")
        win = max(0, min(100, win))

        delivery_reasons: list[str] = []
        if route == "license_hardware":
            delivery = 0
        elif opportunity.software_matches:
            fit = opportunity.software_matches[0].product.delivery_fit
            delivery = 95 if fit == "solo" else 78 if fit == "small_team" else 45
            delivery_reasons.append(f"Open-source candidate: {opportunity.software_matches[0].product.name} ({fit}).")
        elif route in {"custom_dashboard", "integration_data"}:
            delivery = 88
            delivery_reasons.append("Το scope ταιριάζει σε dashboard/integration delivery.")
        elif route == "custom_web_app":
            delivery = 78
            delivery_reasons.append("Το scope ταιριάζει σε custom full-stack web delivery.")
        elif route == "oss_configuration":
            delivery = 90
        elif route == "oss_extension":
            delivery = 82
        else:
            delivery = 50
            delivery_reasons.append("Δεν υπάρχει ακόμη αρκετή τεχνική σαφήνεια.")
        if heavy_requirement:
            delivery = max(0, delivery - 15)
        if opportunity.budget and opportunity.budget > profile.core_budget_max and not profile.partners_available:
            delivery = max(0, delivery - 25)
            risks.append("Το μέγεθος ξεπερνά το solo/core όριο χωρίς διαθέσιμο partner.")

        value_reasons: list[str] = []
        budget = opportunity.budget
        if budget is None:
            value = 55
            value_reasons.append("Το budget δεν είναι διαθέσιμο.")
        elif budget < profile.minimum_viable_budget:
            value = 40
            value_reasons.append("Το budget είναι κάτω από το ελάχιστο βιώσιμο όριο.")
        elif budget <= profile.quick_win_budget_max:
            value = 90
            value_reasons.append("Quick-win budget €5k–€30k.")
        elif budget <= profile.core_budget_max:
            value = 75
            value_reasons.append("Core budget €30k–€80k.")
        else:
            value = 50
            value_reasons.append("Stretch budget που πιθανόν χρειάζεται partner ή αυστηρό scope control.")

        priority = round(win * 0.35 + access * 0.30 + delivery * 0.25 + value * 0.10)
        known = sum((candidate_type != "review", route != "unknown", budget is not None, opportunity.buyer != "Unknown buyer"))
        confidence = "high" if known == 4 else "medium" if known >= 2 else "low"
        if hard_gates or priority < 45:
            verdict = "skip"
        elif priority >= 70 and access >= 60 and win >= 60 and delivery >= 70 and confidence != "low":
            verdict = "pursue"
        else:
            verdict = "review"

        if access_reasons:
            top_reasons.append(access_reasons[0])
        if delivery_reasons:
            top_reasons.append(delivery_reasons[0])
        if win_reasons and len(top_reasons) < 2:
            top_reasons.append(win_reasons[0])

        next_action = self._next_action(candidate_type, verdict, opportunity)
        factors = [
            PursuitFactor(key="access", label="Access", score=access, reasons=access_reasons),
            PursuitFactor(key="win_chance", label="Win chance", score=win, reasons=win_reasons),
            PursuitFactor(key="delivery_fit", label="Delivery fit", score=delivery, reasons=delivery_reasons),
            PursuitFactor(key="value_effort", label="Value / effort", score=value, reasons=value_reasons),
        ]
        assessment = PursuitAssessment(
            verdict=verdict,
            confidence=confidence,
            priority_score=priority,
            candidate_type=candidate_type,
            solution_route=route,
            factors=factors,
            hard_gates=hard_gates,
            top_reasons=top_reasons[:2],
            risks=risks[:3],
            next_action=next_action,
            rules_version=RULES_VERSION,
        )
        return opportunity.model_copy(update={
            "candidate_type": candidate_type,
            "solution_route": route,
            "pursuit_assessment": assessment,
        })

    @staticmethod
    def _next_action(candidate_type: str, verdict: str, opportunity: Opportunity) -> str:
        if verdict == "skip":
            return "Μην δεσμεύσεις bid χρόνο· κράτησέ το μόνο ως market intelligence."
        if candidate_type == "position_early":
            return "Άνοιξε το request, επιβεβαίωσε τον buyer και ετοίμασε σύντομο capability outreach πριν το notice."
        if candidate_type == "outbound":
            return "Επιβεβαίωσε τον decision maker και πρότεινε discovery call με συγκεκριμένο solution hypothesis."
        if candidate_type == "bid_now":
            if opportunity.deadline:
                return "Άνοιξε τα επίσημα έγγραφα και επιβεβαίωσε eligibility, deliverables και submission method."
            return "Βρες και επιβεβαίωσε deadline πριν επενδύσεις σε bid preparation."
        return "Άνοιξε την πηγή και επιβεβαίωσε stage, deadline και συγκεκριμένο software scope."


class PursuitSettingsService:
    def __init__(self, settings: Settings):
        self.db_path = _resolve_db_path(Path(settings.bookmark_db_path))
        self._init_db()

    def get_company_profile(self) -> CompanyProfile:
        return self._get("company_profile", CompanyProfile)

    def save_company_profile(self, profile: CompanyProfile) -> CompanyProfile:
        saved = profile.model_copy(update={"updated_at": datetime.utcnow()})
        self._save("company_profile", saved.model_dump_json())
        return saved

    def get_ai_settings(self) -> AIWorkflowSettings:
        return self._get("ai_workflows", AIWorkflowSettings)

    def save_ai_settings(self, settings: AIWorkflowSettings) -> AIWorkflowSettings:
        saved = settings.model_copy(update={"updated_at": datetime.utcnow()})
        self._save("ai_workflows", saved.model_dump_json())
        return saved

    def _get(self, key: str, model_type):
        with closing(self._connect()) as connection:
            row = connection.execute("SELECT value_json FROM app_settings WHERE key=?", (key,)).fetchone()
        return model_type.model_validate_json(row[0]) if row else model_type()

    def _save(self, key: str, value: str) -> None:
        with closing(self._connect()) as connection, connection:
            connection.execute(
                "INSERT INTO app_settings(key,value_json,updated_at) VALUES (?,?,?) "
                "ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json, updated_at=excluded.updated_at",
                (key, value, datetime.utcnow().isoformat()),
            )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _init_db(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as connection, connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS app_settings (key TEXT PRIMARY KEY, value_json TEXT NOT NULL, updated_at TEXT NOT NULL)"
            )


class PursuitService:
    def __init__(self, settings: Settings):
        self.db_path = _resolve_db_path(Path(settings.bookmark_db_path))
        self._init_db()
        self._migrate_bookmarks()

    def list(self) -> PursuitListResponse:
        with closing(self._connect()) as connection:
            rows = connection.execute("SELECT * FROM pursuits ORDER BY updated_at DESC").fetchall()
        return PursuitListResponse(pursuits=[self._from_row(row) for row in rows])

    def upsert(self, payload: PursuitUpsertRequest) -> PursuitRecord:
        now = datetime.utcnow().isoformat()
        snapshot = payload.opportunity.model_dump_json()
        with closing(self._connect()) as connection, connection:
            connection.execute(
                """INSERT INTO pursuits(id,opportunity_json,status,next_action,next_action_at,notes,feedback_json,created_at,updated_at)
                   VALUES (?,?,?,?,?,?,NULL,?,?)
                   ON CONFLICT(id) DO UPDATE SET opportunity_json=excluded.opportunity_json,status=excluded.status,
                     next_action=excluded.next_action,next_action_at=excluded.next_action_at,notes=excluded.notes,updated_at=excluded.updated_at""",
                (payload.opportunity.id, snapshot, payload.status, payload.next_action,
                 payload.next_action_at.isoformat() if payload.next_action_at else None, payload.notes, now, now),
            )
            row = connection.execute("SELECT * FROM pursuits WHERE id=?", (payload.opportunity.id,)).fetchone()
        return self._from_row(row)

    def update(self, pursuit_id: str, payload: PursuitUpdateRequest) -> PursuitRecord | None:
        updates: list[str] = []
        params: list[object] = []
        for field in ("status", "next_action", "notes"):
            value = getattr(payload, field)
            if value is not None:
                updates.append(f"{field}=?")
                params.append(value)
        if payload.next_action_at is not None:
            updates.append("next_action_at=?")
            params.append(payload.next_action_at.isoformat())
        if not updates:
            return self.get(pursuit_id)
        updates.append("updated_at=?")
        params.extend([datetime.utcnow().isoformat(), pursuit_id])
        with closing(self._connect()) as connection, connection:
            connection.execute(f"UPDATE pursuits SET {', '.join(updates)} WHERE id=?", params)
        return self.get(pursuit_id)

    def save_feedback(self, pursuit_id: str, payload: PursuitFeedbackRequest) -> PursuitRecord | None:
        feedback = PursuitFeedback(
            fit=payload.fit, reason=payload.reason, notes=payload.notes, created_at=datetime.utcnow()
        )
        with closing(self._connect()) as connection, connection:
            connection.execute(
                "UPDATE pursuits SET feedback_json=?, updated_at=? WHERE id=?",
                (feedback.model_dump_json(), datetime.utcnow().isoformat(), pursuit_id),
            )
        return self.get(pursuit_id)

    def get(self, pursuit_id: str) -> PursuitRecord | None:
        with closing(self._connect()) as connection:
            row = connection.execute("SELECT * FROM pursuits WHERE id=?", (pursuit_id,)).fetchone()
        return self._from_row(row) if row else None

    def _from_row(self, row: sqlite3.Row) -> PursuitRecord:
        return PursuitRecord(
            id=str(row["id"]),
            opportunity=Opportunity.model_validate_json(str(row["opportunity_json"])),
            status=str(row["status"]),
            next_action=str(row["next_action"]) if row["next_action"] else None,
            next_action_at=date.fromisoformat(str(row["next_action_at"])) if row["next_action_at"] else None,
            notes=str(row["notes"] or ""),
            feedback=PursuitFeedback.model_validate_json(str(row["feedback_json"])) if row["feedback_json"] else None,
            created_at=datetime.fromisoformat(str(row["created_at"])),
            updated_at=datetime.fromisoformat(str(row["updated_at"])),
        )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _init_db(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as connection, connection:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS pursuits (
                    id TEXT PRIMARY KEY, opportunity_json TEXT NOT NULL, status TEXT NOT NULL,
                    next_action TEXT, next_action_at TEXT, notes TEXT NOT NULL DEFAULT '', feedback_json TEXT,
                    created_at TEXT NOT NULL, updated_at TEXT NOT NULL
                )"""
            )

    def _migrate_bookmarks(self) -> None:
        with closing(self._connect()) as connection, connection:
            table = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='bookmarks'"
            ).fetchone()
            if not table:
                return
            rows = connection.execute("SELECT id,opportunity_json,created_at,updated_at FROM bookmarks").fetchall()
            for row in rows:
                connection.execute(
                    """INSERT OR IGNORE INTO pursuits
                       (id,opportunity_json,status,next_action,next_action_at,notes,feedback_json,created_at,updated_at)
                       VALUES (?,?, 'review', NULL, NULL, '', NULL, ?, ?)""",
                    (row["id"], row["opportunity_json"], row["created_at"], row["updated_at"]),
                )
