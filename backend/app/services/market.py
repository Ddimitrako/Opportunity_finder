from __future__ import annotations

import asyncio
import hashlib
import html
import ipaddress
import json
import re
import socket
import sqlite3
import unicodedata
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator
from urllib.parse import urlparse

import httpx

from app.config import Settings
from app.models import (
    DEFAULT_CPV_CODES,
    DiscoveryProfile,
    DiscoveryProfileCreate,
    EvidenceRef,
    MarketBrandDetail,
    MarketBrandListResponse,
    MarketCategoryTrend,
    MarketConfigResponse,
    MarketOrganization,
    MarketOrganizationDetail,
    MarketOrganizationListResponse,
    MarketOverviewResponse,
    MarketRefreshResponse,
    MarketRefreshSourceResult,
    MarketSignalListResponse,
    NeedSignal,
    Opportunity,
    SoftwareBrand,
    SoftwareBrandMention,
    SupplierAward,
    TrackingEntry,
    TrackingEntryCreate,
    TrackingEntryUpdate,
    WatchSource,
    WatchSourceCreate,
    WatchSourceUpdate,
)
from app.normalization import collect_cpv_codes, extract_records, first_text, parse_date, stable_id, truncate
from app.services.bookmarks import _resolve_db_path
from app.sources.gemi import GemiClient
from app.sources.khmdhs import KhmdhsClient
from app.sources.ted import TedClient


CATEGORIES = [
    "ERP/Finance",
    "HR/HCM/Payroll",
    "Project Management/DevOps",
    "ITSM/IT Operations",
    "Cloud/Infrastructure",
    "BI/Analytics/AI",
    "Cybersecurity",
    "DMS/Workflow/Collaboration",
    "Defence/Industrial",
    "General Software",
]

TRACKING_STATES = [
    "new", "watching", "researching", "contact_planned", "contacted", "meeting",
    "proposal", "partner_target", "won", "lost", "archived",
]

CATEGORY_TERMS: list[tuple[str, tuple[str, ...]]] = [
    ("ERP/Finance", ("erp", "enterprise resource", "λογιστικ", "οικονομικ", "finance", "sap", "oracle ebs", "dynamics 365 finance")),
    ("HR/HCM/Payroll", ("hris", "hcm", "payroll", "μισθοδοσ", "ανθρωπινου δυναμικ", "human resources", "workday")),
    ("Project Management/DevOps", ("devops", "jira", "project management", "pmo", "agile", "gitlab", "github", "ci/cd")),
    ("ITSM/IT Operations", ("itsm", "it service management", "service desk", "servicenow", "monitoring", "network management", "it operations")),
    ("Cloud/Infrastructure", ("cloud", "azure", "aws", "google cloud", "data center", "datacenter", "virtualization", "vmware", "infrastructure")),
    ("BI/Analytics/AI", ("business intelligence", "power bi", "tableau", "analytics", "data warehouse", "artificial intelligence", "τεχνητη νοημοσυνη", "big data")),
    ("Cybersecurity", ("cybersecurity", "cyber security", "κυβερνοασφαλ", "siem", "soc ", "firewall", "endpoint security", "zero trust")),
    ("DMS/Workflow/Collaboration", ("document management", "dms", "workflow", "collaboration", "sharepoint", "ηλεκτρονικη διακινηση", "διαχειριση εγγραφων", "portal")),
    ("Defence/Industrial", ("defence", "defense", "αμυν", "industrial", "manufacturing execution", "mes ", "maintenance management", "asset management")),
]

PRIVATE_SIGNAL_RULES: list[tuple[str, tuple[str, ...], int, str]] = [
    ("job_hiring", ("hiring", "career", "vacancy", "job opening", "προσλαμβ", "θεση εργασιας", "erp consultant", "hris", "pmo manager", "data analyst", "cloud engineer"), 54, "Νέα σχετική πρόσληψη δείχνει ενεργό επενδυτικό ή transformation project."),
    ("transformation", ("digital transformation", "ψηφιακο μετασχηματισμο", "modernization", "εκσυγχρονισμ", "new platform", "νεα πλατφορμα"), 66, "Η εταιρική ανακοίνωση αναφέρει τεχνολογικό μετασχηματισμό ή νέα πλατφόρμα."),
    ("expansion", ("new office", "new branch", "new warehouse", "νεο υποκαταστημα", "νεα εγκατασταση", "expansion", "επεκταση"), 48, "Η επέκταση λειτουργιών συνήθως δημιουργεί ανάγκες για ενοποίηση συστημάτων και reporting."),
    ("capital_change", ("capital increase", "αυξηση κεφαλαιου", "share capital"), 42, "Η κεφαλαιακή μεταβολή αποτελεί early signal για επενδύσεις και οργανωτική ανάπτυξη."),
    ("acquisition", ("acquisition", "merger", "εξαγορα", "συγχωνευση"), 60, "Εξαγορά ή συγχώνευση δημιουργεί ανάγκες για migration, ERP, HR και analytics consolidation."),
]

BRAND_CATALOG: dict[str, dict[str, Any]] = {
    "microsoft": {"name": "Microsoft", "region": "United States", "aliases": ["microsoft", "azure", "dynamics 365", "power bi", "sharepoint", "m365", "office 365"]},
    "oracle": {"name": "Oracle", "region": "United States", "aliases": ["oracle", "oracle cloud", "oracle erp", "peoplesoft"]},
    "servicenow": {"name": "ServiceNow", "region": "United States", "aliases": ["servicenow", "service now"]},
    "salesforce": {"name": "Salesforce", "region": "United States", "aliases": ["salesforce", "tableau", "mulesoft"]},
    "workday": {"name": "Workday", "region": "United States", "aliases": ["workday", "workday hcm"]},
    "atlassian": {"name": "Atlassian", "region": "United States", "aliases": ["atlassian", "jira", "confluence"]},
    "ibm": {"name": "IBM / Red Hat", "region": "United States", "aliases": ["ibm", "red hat", "openshift", "watson"]},
    "broadcom": {"name": "Broadcom / VMware", "region": "United States", "aliases": ["broadcom", "vmware", "vsphere"]},
    "sap": {"name": "SAP", "region": "Europe", "aliases": ["sap", "s/4hana", "successfactors", "ariba"]},
    "ifs": {"name": "IFS", "region": "Europe", "aliases": ["ifs cloud", "ifs applications", "ifs erp"]},
    "unit4": {"name": "Unit4", "region": "Europe", "aliases": ["unit4", "unit 4"]},
    "odoo": {"name": "Odoo", "region": "Europe", "aliases": ["odoo", "openerp"]},
    "celonis": {"name": "Celonis", "region": "Europe", "aliases": ["celonis"]},
    "jetbrains": {"name": "JetBrains", "region": "Europe", "aliases": ["jetbrains", "youtrack", "teamcity"]},
    "gitlab": {"name": "GitLab", "region": "United States", "aliases": ["gitlab"]},
    "kingdee": {"name": "Kingdee", "region": "China", "aliases": ["kingdee"]},
    "yonyou": {"name": "Yonyou", "region": "China", "aliases": ["yonyou", "yonbip", "yonsuite"]},
    "huawei": {"name": "Huawei", "region": "China", "aliases": ["huawei", "esight", "imaster nce"]},
}


class MarketService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.db_path = _resolve_db_path(Path(settings.bookmark_db_path))
        self._ensure_schema()
        self._seed_brands()

    def config(self) -> MarketConfigResponse:
        return MarketConfigResponse(
            gemi_enabled=bool(self.settings.gemi_api_key),
            refresh_enabled=self.settings.market_refresh_enabled,
            refresh_hour=self.settings.market_refresh_hour,
            categories=CATEGORIES,
            tracking_states=TRACKING_STATES,
        )

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.db_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 10000")
        connection.execute("PRAGMA journal_mode = WAL")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _ensure_schema(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS market_organizations (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    normalized_name TEXT NOT NULL,
                    role TEXT NOT NULL,
                    country TEXT NOT NULL DEFAULT 'GR',
                    gemi_number TEXT,
                    tax_id TEXT,
                    khmdhs_key TEXT,
                    website TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE UNIQUE INDEX IF NOT EXISTS idx_market_org_norm_country
                    ON market_organizations(normalized_name, country);
                CREATE TABLE IF NOT EXISTS market_organization_aliases (
                    organization_id TEXT NOT NULL,
                    alias TEXT NOT NULL,
                    normalized_alias TEXT NOT NULL,
                    PRIMARY KEY (organization_id, normalized_alias),
                    FOREIGN KEY (organization_id) REFERENCES market_organizations(id) ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS market_source_records (
                    id TEXT PRIMARY KEY,
                    source TEXT NOT NULL,
                    external_id TEXT NOT NULL,
                    record_type TEXT NOT NULL,
                    organization_id TEXT,
                    title TEXT NOT NULL,
                    url TEXT,
                    published_at TEXT,
                    content_hash TEXT NOT NULL,
                    raw_json TEXT NOT NULL,
                    first_seen_at TEXT NOT NULL,
                    last_seen_at TEXT NOT NULL,
                    UNIQUE(source, external_id, record_type),
                    FOREIGN KEY (organization_id) REFERENCES market_organizations(id) ON DELETE SET NULL
                );
                CREATE TABLE IF NOT EXISTS market_need_signals (
                    id TEXT PRIMARY KEY,
                    organization_id TEXT NOT NULL,
                    category TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    stage TEXT NOT NULL,
                    need_score INTEGER NOT NULL,
                    confidence INTEGER NOT NULL,
                    why_now TEXT NOT NULL,
                    score_reasons_json TEXT NOT NULL,
                    source_record_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(organization_id, kind, source_record_id),
                    FOREIGN KEY (organization_id) REFERENCES market_organizations(id) ON DELETE CASCADE,
                    FOREIGN KEY (source_record_id) REFERENCES market_source_records(id) ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS market_supplier_awards (
                    id TEXT PRIMARY KEY,
                    buyer_id TEXT NOT NULL,
                    supplier_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    category TEXT NOT NULL,
                    amount REAL,
                    currency TEXT NOT NULL DEFAULT 'EUR',
                    awarded_at TEXT,
                    source_record_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(buyer_id, supplier_id, source_record_id),
                    FOREIGN KEY (buyer_id) REFERENCES market_organizations(id) ON DELETE CASCADE,
                    FOREIGN KEY (supplier_id) REFERENCES market_organizations(id) ON DELETE CASCADE,
                    FOREIGN KEY (source_record_id) REFERENCES market_source_records(id) ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS market_software_brands (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    origin_region TEXT NOT NULL,
                    aliases_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS market_brand_mentions (
                    id TEXT PRIMARY KEY,
                    brand_id TEXT NOT NULL,
                    product_name TEXT,
                    buyer_id TEXT,
                    supplier_id TEXT,
                    source_record_id TEXT NOT NULL,
                    confidence INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(brand_id, source_record_id, buyer_id, supplier_id),
                    FOREIGN KEY (brand_id) REFERENCES market_software_brands(id) ON DELETE CASCADE,
                    FOREIGN KEY (buyer_id) REFERENCES market_organizations(id) ON DELETE SET NULL,
                    FOREIGN KEY (supplier_id) REFERENCES market_organizations(id) ON DELETE SET NULL,
                    FOREIGN KEY (source_record_id) REFERENCES market_source_records(id) ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS market_tracking_entries (
                    id TEXT PRIMARY KEY,
                    entity_type TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    state TEXT NOT NULL,
                    notes TEXT NOT NULL DEFAULT '',
                    next_action TEXT,
                    next_action_at TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(entity_type, entity_id)
                );
                CREATE TABLE IF NOT EXISTS market_watch_sources (
                    id TEXT PRIMARY KEY,
                    organization_id TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    url TEXT NOT NULL UNIQUE,
                    label TEXT NOT NULL DEFAULT '',
                    enabled INTEGER NOT NULL DEFAULT 1,
                    content_hash TEXT,
                    last_checked_at TEXT,
                    last_changed_at TEXT,
                    last_error TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (organization_id) REFERENCES market_organizations(id) ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS market_discovery_profiles (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    activities_json TEXT NOT NULL,
                    prefectures_json TEXT NOT NULL,
                    municipalities_json TEXT NOT NULL,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    last_run_at TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS market_refresh_runs (
                    id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    finished_at TEXT,
                    source_results_json TEXT NOT NULL DEFAULT '[]',
                    message TEXT
                );
                CREATE TABLE IF NOT EXISTS market_refresh_lease (
                    lease_key TEXT PRIMARY KEY,
                    holder TEXT NOT NULL,
                    expires_at TEXT NOT NULL
                );
                """
            )

    def _seed_brands(self) -> None:
        now = _iso_now()
        with self._connect() as connection:
            for brand_id, item in BRAND_CATALOG.items():
                connection.execute(
                    """
                    INSERT INTO market_software_brands(id, name, origin_region, aliases_json, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        name=excluded.name, origin_region=excluded.origin_region,
                        aliases_json=excluded.aliases_json, updated_at=excluded.updated_at
                    """,
                    (brand_id, item["name"], item["region"], _json(item["aliases"]), now),
                )

    def overview(self, period_days: int = 30) -> MarketOverviewResponse:
        period_days = min(365, max(1, period_days))
        today = date.today()
        current_start = today - timedelta(days=period_days - 1)
        previous_start = current_start - timedelta(days=period_days)
        with self._connect() as connection:
            current_rows = connection.execute(
                """SELECT category, COUNT(*) count
                   FROM market_need_signals s JOIN market_source_records r ON r.id=s.source_record_id
                   WHERE COALESCE(r.published_at, substr(s.created_at,1,10)) >= ?
                   GROUP BY category""",
                (current_start.isoformat(),),
            ).fetchall()
            previous_rows = connection.execute(
                """SELECT category, COUNT(*) count
                   FROM market_need_signals s JOIN market_source_records r ON r.id=s.source_record_id
                   WHERE COALESCE(r.published_at, substr(s.created_at,1,10)) >= ?
                     AND COALESCE(r.published_at, substr(s.created_at,1,10)) < ?
                   GROUP BY category""",
                (previous_start.isoformat(), current_start.isoformat()),
            ).fetchall()
            spend_rows = connection.execute(
                """SELECT category, COALESCE(SUM(amount),0) spend FROM market_supplier_awards
                   WHERE COALESCE(awarded_at, substr(created_at,1,10)) >= ? GROUP BY category""",
                (current_start.isoformat(),),
            ).fetchall()
            current = {str(row["category"]): int(row["count"]) for row in current_rows}
            previous = {str(row["category"]): int(row["count"]) for row in previous_rows}
            spend = {str(row["category"]): float(row["spend"] or 0) for row in spend_rows}
            trends = []
            for category in CATEGORIES:
                current_count = current.get(category, 0)
                previous_count = previous.get(category, 0)
                delta = None if previous_count == 0 else round(((current_count - previous_count) / previous_count) * 100, 1)
                trends.append(MarketCategoryTrend(
                    category=category,
                    current_count=current_count,
                    previous_count=previous_count,
                    delta_percent=delta,
                    observed_spend=spend.get(category, 0),
                ))

            new_signals = int(connection.execute(
                "SELECT COUNT(*) FROM market_need_signals WHERE substr(created_at,1,10) >= ?",
                ((today - timedelta(days=1)).isoformat(),),
            ).fetchone()[0])
            hot_buyers = int(connection.execute(
                "SELECT COUNT(DISTINCT organization_id) FROM market_need_signals WHERE need_score >= 75"
            ).fetchone()[0])
            open_opportunities = int(connection.execute(
                "SELECT COUNT(*) FROM market_need_signals WHERE stage='open'"
            ).fetchone()[0])
            observed_spend = float(connection.execute(
                "SELECT COALESCE(SUM(amount),0) FROM market_supplier_awards"
            ).fetchone()[0] or 0)
            tracked_entities = int(connection.execute(
                "SELECT COUNT(*) FROM market_tracking_entries WHERE state NOT IN ('archived','lost')"
            ).fetchone()[0])
            refresh_row = connection.execute(
                "SELECT finished_at FROM market_refresh_runs WHERE status IN ('ok','partial') ORDER BY started_at DESC LIMIT 1"
            ).fetchone()

        return MarketOverviewResponse(
            generated_at=_utcnow(),
            period_days=period_days,
            new_signals=new_signals,
            hot_buyers=hot_buyers,
            open_opportunities=open_opportunities,
            observed_public_spend=observed_spend,
            tracked_entities=tracked_entities,
            categories=trends,
            hot_organizations=self.list_organizations(role="buyer", min_score=50, limit=8, offset=0).items,
            recent_signals=self.list_signals(limit=8, offset=0).items,
            top_suppliers=self.list_organizations(role="supplier", limit=6, offset=0).items,
            top_brands=self.list_brands(limit=6).items,
            coverage={
                "khmdhs": "procurement lifecycle",
                "ted": "planning, competition and result notices",
                "diavgeia": "tracked-buyer decisions",
                "gemi": "enabled" if self.settings.gemi_api_key else "waiting for API key",
                "private_web": "official watched careers/news pages",
            },
            last_refresh_at=_parse_datetime(refresh_row["finished_at"]) if refresh_row else None,
        )

    def list_signals(
        self,
        *,
        category: str | None = None,
        stage: str | None = None,
        min_score: int = 0,
        source: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> MarketSignalListResponse:
        where = ["s.need_score >= ?"]
        params: list[Any] = [max(0, min(100, min_score))]
        if category:
            where.append("s.category = ?")
            params.append(category)
        if stage:
            where.append("s.stage = ?")
            params.append(stage)
        if source:
            where.append("r.source = ?")
            params.append(source)
        where_sql = " AND ".join(where)
        limit = min(200, max(1, limit))
        offset = max(0, offset)
        with self._connect() as connection:
            total = int(connection.execute(
                f"SELECT COUNT(*) FROM market_need_signals s JOIN market_source_records r ON r.id=s.source_record_id WHERE {where_sql}",
                params,
            ).fetchone()[0])
            rows = connection.execute(
                f"""SELECT s.*, o.name organization_name, r.source, r.external_id, r.title evidence_title,
                           r.url evidence_url, r.published_at evidence_published_at, r.raw_json,
                           CASE WHEN substr(s.created_at,1,10) >= ? THEN 1 ELSE 0 END is_new
                    FROM market_need_signals s
                    JOIN market_organizations o ON o.id=s.organization_id
                    JOIN market_source_records r ON r.id=s.source_record_id
                    WHERE {where_sql}
                    ORDER BY s.need_score DESC, COALESCE(r.published_at, s.updated_at) DESC
                    LIMIT ? OFFSET ?""",
                [(date.today() - timedelta(days=1)).isoformat(), *params, limit, offset],
            ).fetchall()
        return MarketSignalListResponse(items=[_signal_from_row(row) for row in rows], total=total, limit=limit, offset=offset)

    def list_organizations(
        self,
        *,
        role: str = "buyer",
        search: str | None = None,
        category: str | None = None,
        min_score: int = 0,
        tracking_state: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> MarketOrganizationListResponse:
        where = ["(o.role=? OR o.role='both')"]
        params: list[Any] = [role]
        if search:
            where.append("(o.normalized_name LIKE ? OR EXISTS (SELECT 1 FROM market_organization_aliases a WHERE a.organization_id=o.id AND a.normalized_alias LIKE ?))")
            needle = f"%{normalize_name(search)}%"
            params.extend([needle, needle])
        if category:
            where.append("EXISTS (SELECT 1 FROM market_need_signals sc WHERE sc.organization_id=o.id AND sc.category=?)")
            params.append(category)
        if tracking_state:
            where.append("t.state=?")
            params.append(tracking_state)
        where_sql = " AND ".join(where)
        limit = min(200, max(1, limit))
        offset = max(0, offset)
        with self._connect() as connection:
            total = int(connection.execute(
                f"SELECT COUNT(DISTINCT o.id) FROM market_organizations o LEFT JOIN market_tracking_entries t ON t.entity_id=o.id AND t.entity_type=? WHERE {where_sql}",
                [role, *params],
            ).fetchone()[0])
            rows = connection.execute(
                f"""SELECT o.*, t.state tracking_state, t.next_action,
                           COALESCE(MAX(s.need_score),0) strongest_signal_score,
                           (SELECT kind FROM market_need_signals s2 WHERE s2.organization_id=o.id ORDER BY need_score DESC, updated_at DESC LIMIT 1) strongest_signal_kind,
                           (SELECT category FROM market_need_signals s3 WHERE s3.organization_id=o.id ORDER BY need_score DESC, updated_at DESC LIMIT 1) strongest_category,
                           MAX(r.published_at) last_signal_at,
                           (SELECT GROUP_CONCAT(DISTINCT so.name) FROM market_supplier_awards aw JOIN market_organizations so ON so.id=aw.supplier_id WHERE aw.buyer_id=o.id) incumbent_suppliers,
                           (SELECT GROUP_CONCAT(DISTINCT b.name) FROM market_brand_mentions bm JOIN market_software_brands b ON b.id=bm.brand_id WHERE bm.buyer_id=o.id OR bm.supplier_id=o.id) software_brands,
                           (SELECT GROUP_CONCAT(alias, '||') FROM market_organization_aliases a WHERE a.organization_id=o.id) aliases
                    FROM market_organizations o
                    LEFT JOIN market_need_signals s ON s.organization_id=o.id
                    LEFT JOIN market_source_records r ON r.id=s.source_record_id
                    LEFT JOIN market_tracking_entries t ON t.entity_id=o.id AND t.entity_type=?
                    WHERE {where_sql}
                    GROUP BY o.id
                    HAVING strongest_signal_score >= ?
                    ORDER BY strongest_signal_score DESC, last_signal_at DESC, o.name
                    LIMIT ? OFFSET ?""",
                [role, *params, max(0, min(100, min_score)), limit, offset],
            ).fetchall()
        items = [_organization_from_row(row) for row in rows]
        if role == "supplier":
            items = [self._enrich_supplier_organization(item) for item in items]
            items.sort(key=lambda item: (item.strongest_signal_score, item.last_signal_at or date.min), reverse=True)
        return MarketOrganizationListResponse(items=items, total=total, limit=limit, offset=offset)

    def organization_detail(self, organization_id: str) -> MarketOrganizationDetail | None:
        with self._connect() as connection:
            row = connection.execute(
                """SELECT o.*, t.state tracking_state, t.next_action,
                          COALESCE(MAX(s.need_score),0) strongest_signal_score,
                          (SELECT kind FROM market_need_signals WHERE organization_id=o.id ORDER BY need_score DESC LIMIT 1) strongest_signal_kind,
                          (SELECT category FROM market_need_signals WHERE organization_id=o.id ORDER BY need_score DESC LIMIT 1) strongest_category,
                          MAX(r.published_at) last_signal_at,
                          (SELECT GROUP_CONCAT(DISTINCT so.name) FROM market_supplier_awards aw JOIN market_organizations so ON so.id=aw.supplier_id WHERE aw.buyer_id=o.id) incumbent_suppliers,
                          (SELECT GROUP_CONCAT(DISTINCT b.name) FROM market_brand_mentions bm JOIN market_software_brands b ON b.id=bm.brand_id WHERE bm.buyer_id=o.id OR bm.supplier_id=o.id) software_brands,
                          (SELECT GROUP_CONCAT(alias, '||') FROM market_organization_aliases a WHERE a.organization_id=o.id) aliases
                   FROM market_organizations o
                   LEFT JOIN market_need_signals s ON s.organization_id=o.id
                   LEFT JOIN market_source_records r ON r.id=s.source_record_id
                   LEFT JOIN market_tracking_entries t ON t.entity_id=o.id AND t.entity_type=CASE WHEN o.role='supplier' THEN 'supplier' ELSE 'buyer' END
                   WHERE o.id=? GROUP BY o.id""",
                (organization_id,),
            ).fetchone()
        if not row:
            return None
        organization = _organization_from_row(row)
        if organization.role == "supplier":
            organization = self._enrich_supplier_organization(organization)
        return MarketOrganizationDetail(
            organization=organization,
            signals=self._signals_for_org(organization_id),
            awards_as_buyer=self._awards_for_org(organization_id, "buyer"),
            awards_as_supplier=self._awards_for_org(organization_id, "supplier"),
            brand_mentions=self._mentions_for_entity(organization_id=organization_id),
            tracking=self.get_tracking("supplier" if organization.role == "supplier" else "buyer", organization_id),
            watch_sources=self.list_watch_sources(organization_id=organization_id),
        )

    def _enrich_supplier_organization(self, organization: MarketOrganization) -> MarketOrganization:
        with self._connect() as connection:
            metrics = connection.execute(
                """SELECT COUNT(*) award_count, MAX(awarded_at) last_award,
                          (SELECT category FROM market_supplier_awards WHERE supplier_id=? GROUP BY category ORDER BY COUNT(*) DESC LIMIT 1) top_category,
                          (SELECT GROUP_CONCAT(DISTINCT bo.name) FROM market_supplier_awards aw JOIN market_organizations bo ON bo.id=aw.buyer_id WHERE aw.supplier_id=?) buyer_names
                   FROM market_supplier_awards WHERE supplier_id=?""",
                (organization.id, organization.id, organization.id),
            ).fetchone()
        count = int(metrics["award_count"] or 0) if metrics else 0
        return organization.model_copy(update={
            "strongest_signal_score": min(100, 20 + count * 12) if count else 0,
            "strongest_signal_kind": "award" if count else organization.strongest_signal_kind,
            "strongest_category": str(metrics["top_category"]) if metrics and metrics["top_category"] else organization.strongest_category,
            "last_signal_at": parse_date(metrics["last_award"]) if metrics else organization.last_signal_at,
            "incumbent_suppliers": _split_csv(metrics["buyer_names"]) if metrics else organization.incumbent_suppliers,
        })

    def list_brands(self, *, region: str | None = None, search: str | None = None, limit: int = 100) -> MarketBrandListResponse:
        where: list[str] = []
        params: list[Any] = []
        if region:
            where.append("b.origin_region=?")
            params.append(region)
        if search:
            where.append("(lower(b.name) LIKE ? OR lower(b.aliases_json) LIKE ?)")
            needle = f"%{search.casefold()}%"
            params.extend([needle, needle])
        where_sql = f"WHERE {' AND '.join(where)}" if where else ""
        limit = min(200, max(1, limit))
        with self._connect() as connection:
            total = int(connection.execute(f"SELECT COUNT(*) FROM market_software_brands b {where_sql}", params).fetchone()[0])
            rows = connection.execute(
                f"""SELECT b.*, COUNT(DISTINCT bm.id) mention_count,
                           COALESCE(SUM(aw.amount),0) observed_spend,
                           GROUP_CONCAT(DISTINCT so.name) supplier_names,
                           GROUP_CONCAT(DISTINCT bo.name) buyer_names,
                           MAX(r.published_at) last_seen_at
                    FROM market_software_brands b
                    LEFT JOIN market_brand_mentions bm ON bm.brand_id=b.id
                    LEFT JOIN market_source_records r ON r.id=bm.source_record_id
                    LEFT JOIN market_supplier_awards aw ON aw.source_record_id=bm.source_record_id
                    LEFT JOIN market_organizations so ON so.id=bm.supplier_id
                    LEFT JOIN market_organizations bo ON bo.id=bm.buyer_id
                    {where_sql}
                    GROUP BY b.id
                    ORDER BY mention_count DESC, observed_spend DESC, b.name
                    LIMIT ?""",
                [*params, limit],
            ).fetchall()
        return MarketBrandListResponse(items=[_brand_from_row(row) for row in rows], total=total)

    def brand_detail(self, brand_id: str) -> MarketBrandDetail | None:
        brands = self.list_brands(limit=200).items
        brand = next((item for item in brands if item.id == brand_id), None)
        if not brand:
            return None
        return MarketBrandDetail(
            brand=brand,
            mentions=self._mentions_for_entity(brand_id=brand_id),
            awards=self._awards_for_brand(brand_id),
            tracking=self.get_tracking("brand", brand_id),
        )

    def list_tracking(self) -> list[TrackingEntry]:
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM market_tracking_entries ORDER BY updated_at DESC").fetchall()
        return [self._tracking_from_row(row) for row in rows]

    def get_tracking(self, entity_type: str, entity_id: str) -> TrackingEntry | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM market_tracking_entries WHERE entity_type=? AND entity_id=?",
                (entity_type, entity_id),
            ).fetchone()
        return self._tracking_from_row(row) if row else None

    def upsert_tracking(self, payload: TrackingEntryCreate) -> TrackingEntry:
        now = _iso_now()
        item_id = f"tracking-{stable_id(payload.entity_type, payload.entity_id)}"
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO market_tracking_entries
                   (id, entity_type, entity_id, state, notes, next_action, next_action_at, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(entity_type, entity_id) DO UPDATE SET
                     state=excluded.state, notes=excluded.notes, next_action=excluded.next_action,
                     next_action_at=excluded.next_action_at, updated_at=excluded.updated_at""",
                (item_id, payload.entity_type, payload.entity_id, payload.state, payload.notes,
                 payload.next_action, _date_iso(payload.next_action_at), now, now),
            )
        return self.get_tracking(payload.entity_type, payload.entity_id)  # type: ignore[return-value]

    def update_tracking(self, tracking_id: str, payload: TrackingEntryUpdate) -> TrackingEntry | None:
        updates: list[str] = []
        params: list[Any] = []
        for field in ("state", "notes", "next_action"):
            value = getattr(payload, field)
            if value is not None:
                updates.append(f"{field}=?")
                params.append(value)
        if payload.next_action_at is not None:
            updates.append("next_action_at=?")
            params.append(payload.next_action_at.isoformat())
        if not updates:
            with self._connect() as connection:
                row = connection.execute("SELECT * FROM market_tracking_entries WHERE id=?", (tracking_id,)).fetchone()
            return self._tracking_from_row(row) if row else None
        updates.append("updated_at=?")
        params.extend([_iso_now(), tracking_id])
        with self._connect() as connection:
            connection.execute(f"UPDATE market_tracking_entries SET {', '.join(updates)} WHERE id=?", params)
            row = connection.execute("SELECT * FROM market_tracking_entries WHERE id=?", (tracking_id,)).fetchone()
        return self._tracking_from_row(row) if row else None

    def delete_tracking(self, tracking_id: str) -> bool:
        with self._connect() as connection:
            cursor = connection.execute("DELETE FROM market_tracking_entries WHERE id=?", (tracking_id,))
        return cursor.rowcount > 0

    def _tracking_from_row(self, row: sqlite3.Row) -> TrackingEntry:
        entity_name = self._entity_name(str(row["entity_type"]), str(row["entity_id"]))
        return TrackingEntry(
            id=str(row["id"]), entity_type=str(row["entity_type"]), entity_id=str(row["entity_id"]),
            entity_name=entity_name, state=str(row["state"]), notes=str(row["notes"] or ""),
            next_action=str(row["next_action"]) if row["next_action"] else None,
            next_action_at=parse_date(row["next_action_at"]),
            created_at=_parse_datetime(row["created_at"]) or _utcnow(),
            updated_at=_parse_datetime(row["updated_at"]) or _utcnow(),
        )

    def _entity_name(self, entity_type: str, entity_id: str) -> str:
        with self._connect() as connection:
            if entity_type == "brand":
                row = connection.execute("SELECT name FROM market_software_brands WHERE id=?", (entity_id,)).fetchone()
            else:
                row = connection.execute("SELECT name FROM market_organizations WHERE id=?", (entity_id,)).fetchone()
        return str(row["name"]) if row else entity_id

    def list_watch_sources(self, organization_id: str | None = None) -> list[WatchSource]:
        params: list[Any] = []
        where = ""
        if organization_id:
            where = "WHERE w.organization_id=?"
            params.append(organization_id)
        with self._connect() as connection:
            rows = connection.execute(
                f"""SELECT w.*, o.name organization_name FROM market_watch_sources w
                    JOIN market_organizations o ON o.id=w.organization_id {where}
                    ORDER BY w.updated_at DESC""", params
            ).fetchall()
        return [_watch_from_row(row) for row in rows]

    def create_watch_source(self, payload: WatchSourceCreate) -> WatchSource:
        _validate_public_https_url(payload.url)
        now = _iso_now()
        item_id = f"watch-{stable_id(payload.organization_id, payload.url)}"
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO market_watch_sources
                   (id, organization_id, source_type, url, label, enabled, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(url) DO UPDATE SET organization_id=excluded.organization_id,
                     source_type=excluded.source_type, label=excluded.label, enabled=excluded.enabled, updated_at=excluded.updated_at""",
                (item_id, payload.organization_id, payload.source_type, payload.url, payload.label,
                 int(payload.enabled), now, now),
            )
        return next(item for item in self.list_watch_sources() if item.url == payload.url)

    def update_watch_source(self, watch_id: str, payload: WatchSourceUpdate) -> WatchSource | None:
        updates: list[str] = []
        params: list[Any] = []
        if payload.label is not None:
            updates.append("label=?")
            params.append(payload.label)
        if payload.enabled is not None:
            updates.append("enabled=?")
            params.append(int(payload.enabled))
        if not updates:
            return next((item for item in self.list_watch_sources() if item.id == watch_id), None)
        updates.append("updated_at=?")
        params.extend([_iso_now(), watch_id])
        with self._connect() as connection:
            connection.execute(f"UPDATE market_watch_sources SET {', '.join(updates)} WHERE id=?", params)
        return next((item for item in self.list_watch_sources() if item.id == watch_id), None)

    def delete_watch_source(self, watch_id: str) -> bool:
        with self._connect() as connection:
            cursor = connection.execute("DELETE FROM market_watch_sources WHERE id=?", (watch_id,))
        return cursor.rowcount > 0

    def list_discovery_profiles(self) -> list[DiscoveryProfile]:
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM market_discovery_profiles ORDER BY updated_at DESC").fetchall()
        return [_profile_from_row(row) for row in rows]

    def create_discovery_profile(self, payload: DiscoveryProfileCreate) -> DiscoveryProfile:
        if not payload.activities and not payload.prefectures and not payload.municipalities:
            raise ValueError("At least one GEMI discovery criterion is required.")
        now = _iso_now()
        item_id = f"profile-{stable_id(payload.name, now)}"
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO market_discovery_profiles
                   (id, name, activities_json, prefectures_json, municipalities_json, is_active, enabled, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (item_id, payload.name, _json(payload.activities), _json(payload.prefectures),
                 _json(payload.municipalities), int(payload.is_active), int(payload.enabled), now, now),
            )
        return next(item for item in self.list_discovery_profiles() if item.id == item_id)

    def delete_discovery_profile(self, profile_id: str) -> bool:
        with self._connect() as connection:
            cursor = connection.execute("DELETE FROM market_discovery_profiles WHERE id=?", (profile_id,))
        return cursor.rowcount > 0

    def ingest_opportunities(self, opportunities: Iterable[Opportunity]) -> tuple[int, int]:
        created = 0
        updated = 0
        for opportunity in opportunities:
            organization_id = self._upsert_organization(
                opportunity.buyer,
                role="buyer",
                country=opportunity.country or "GR",
                khmdhs_key=first_text((opportunity.source_payload or {}).get("organizationKey")) or None,
            )
            stage, kind, base_score, why = _opportunity_stage(opportunity)
            category, category_reasons = classify_category(
                f"{opportunity.title} {opportunity.summary} {' '.join(opportunity.matched_keywords)}",
                opportunity.cpv_codes,
            )
            score = min(100, base_score + (8 if category != "General Software" else 0) + (5 if opportunity.budget else 0))
            evidence = EvidenceRef(
                source=opportunity.source,
                external_id=opportunity.source_reference or opportunity.id,
                url=opportunity.url,
                title=opportunity.title,
                published_at=opportunity.published_at,
                excerpt=truncate(opportunity.summary, 420),
            )
            record_id, is_created, changed = self._upsert_source_record(
                source=opportunity.source,
                external_id=opportunity.source_reference or opportunity.id,
                record_type=kind,
                organization_id=organization_id,
                evidence=evidence,
                raw=opportunity.model_dump(mode="json"),
            )
            if is_created:
                created += 1
            elif changed:
                updated += 1
            self._upsert_signal(
                organization_id=organization_id,
                category=category,
                kind=kind,
                stage=stage,
                score=score,
                confidence=88 if opportunity.source in {"khmdhs", "ted"} else 65,
                why_now=why,
                reasons=[*category_reasons, f"Lifecycle stage: {stage}", opportunity.recommendation],
                source_record_id=record_id,
            )
            self._record_brand_mentions(
                f"{opportunity.title} {opportunity.summary} {opportunity.raw_text}",
                source_record_id=record_id,
                buyer_id=organization_id,
            )
        return created, updated

    async def refresh(self, backfill_days: int | None = None) -> MarketRefreshResponse:
        days = backfill_days or self.settings.market_daily_overlap_days
        run_id = f"refresh-{stable_id(_iso_now())}"
        started_at = _utcnow()
        if not self._acquire_refresh_lease(run_id):
            return MarketRefreshResponse(
                run_id=run_id, status="skipped", started_at=started_at, finished_at=_utcnow(),
                message="Another market refresh is already running.",
            )
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO market_refresh_runs(id,status,started_at,source_results_json) VALUES (?,?,?,?)",
                (run_id, "running", started_at.isoformat(), "[]"),
            )
        results: list[MarketRefreshSourceResult] = []
        try:
            for source, operation in (
                ("khmdhs", lambda: self._refresh_khmdhs(days)),
                ("ted", lambda: self._refresh_ted(days)),
                ("diavgeia", self._refresh_diavgeia),
                ("gemi", self._refresh_gemi),
                ("private_web", self._refresh_watch_sources),
            ):
                try:
                    result = await operation()
                    results.append(result)
                except Exception as exc:  # source isolation is intentional
                    results.append(MarketRefreshSourceResult(
                        source=source, status="error", error=f"{exc.__class__.__name__}: {str(exc)[:240]}"
                    ))
            errors = sum(1 for result in results if result.status == "error")
            oks = sum(1 for result in results if result.status == "ok")
            status = "ok" if not errors else ("partial" if oks else "error")
            finished_at = _utcnow()
            response = MarketRefreshResponse(
                run_id=run_id, status=status, started_at=started_at, finished_at=finished_at,
                source_results=results,
            )
            with self._connect() as connection:
                connection.execute(
                    "UPDATE market_refresh_runs SET status=?, finished_at=?, source_results_json=? WHERE id=?",
                    (status, finished_at.isoformat(), _json([item.model_dump(mode="json") for item in results]), run_id),
                )
            return response
        finally:
            self._release_refresh_lease(run_id)

    def refresh_status(self) -> MarketRefreshResponse | None:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM market_refresh_runs ORDER BY started_at DESC LIMIT 1").fetchone()
        if not row:
            return None
        payload = _loads(row["source_results_json"], [])
        return MarketRefreshResponse(
            run_id=str(row["id"]), status=str(row["status"]),
            started_at=_parse_datetime(row["started_at"]) or _utcnow(),
            finished_at=_parse_datetime(row["finished_at"]),
            source_results=[MarketRefreshSourceResult.model_validate(item) for item in payload],
            message=str(row["message"]) if row["message"] else None,
        )

    async def _refresh_khmdhs(self, days: int) -> MarketRefreshSourceResult:
        date_to = date.today()
        date_from = date_to - timedelta(days=max(1, days) - 1)
        fetched = created = updated = 0
        client = KhmdhsClient(self.settings)
        for endpoint in ("request", "notice", "auction", "contract", "payment"):
            cursor = date_to
            while cursor >= date_from:
                chunk_start = max(date_from, cursor - timedelta(days=179))
                body: dict[str, Any] = {
                    "dateFrom": chunk_start.isoformat(), "dateTo": cursor.isoformat(),
                    "cpvItems": DEFAULT_CPV_CODES, "totalCostFrom": 0, "totalCostTo": 1_000_000_000_000,
                }
                if endpoint == "request":
                    body.update({"isInitial": True, "isApproved": True, "isApproval": True})
                records = await self._khmdhs_records(endpoint, body)
                fetched += len(records)
                if endpoint in {"request", "notice"}:
                    opportunities = [client._to_opportunity(record) for record in records]
                    for opportunity in opportunities:
                        opportunity.notice_type = endpoint
                    c, u = self.ingest_opportunities(opportunities)
                    created += c
                    updated += u
                else:
                    for record in records:
                        c, u = self._ingest_khmdhs_outcome(endpoint, record)
                        created += c
                        updated += u
                cursor = chunk_start - timedelta(days=1)
        return MarketRefreshSourceResult(source="khmdhs", status="ok", fetched=fetched, created=created, updated=updated)

    async def _khmdhs_records(self, endpoint: str, body: dict[str, Any]) -> list[dict[str, Any]]:
        url = f"{str(self.settings.khmdhs_base_url).rstrip('/')}/khmdhs-opendata/{endpoint}"
        collected: list[dict[str, Any]] = []
        async with httpx.AsyncClient(
            timeout=self.settings.khmdhs_timeout_seconds,
            verify=self.settings.khmdhs_verify_ssl,
            headers={"Accept": "application/json", "Content-Type": "application/json", "User-Agent": self.settings.market_user_agent},
        ) as client:
            for page in range(20):
                response = await client.post(url, params={"page": page}, json=body)
                if response.status_code == 404:
                    break
                response.raise_for_status()
                payload = response.json()
                records = extract_records(payload)
                collected.extend(records)
                total_pages = payload.get("totalPages") if isinstance(payload, dict) else None
                if not records or (isinstance(total_pages, int) and page + 1 >= total_pages) or len(collected) >= 1000:
                    break
        return collected[:1000]

    def _ingest_khmdhs_outcome(self, endpoint: str, record: dict[str, Any]) -> tuple[int, int]:
        buyer_name = first_text(record.get("organization"), "Unknown buyer")
        buyer_id = self._upsert_organization(
            buyer_name, role="buyer", khmdhs_key=_extract_key(record.get("organization"))
        )
        supplier_name = _contractor_name(record)
        supplier_id = self._upsert_organization(supplier_name, role="supplier") if supplier_name else None
        title = first_text(record.get("title"), f"ΚΗΜΔΗΣ {endpoint}")
        reference = first_text(record.get("referenceNumber"), stable_id(title, buyer_name, endpoint))
        published_at = parse_date(record.get("submissionDate") or record.get("signedDate"))
        evidence = EvidenceRef(
            source="khmdhs", external_id=reference,
            url=f"{str(self.settings.khmdhs_base_url).rstrip('/')}/khmdhs-opendata/{endpoint}/attachment/{reference}",
            title=title, published_at=published_at,
            excerpt=truncate(" ".join([title, first_text(record.get("procedureType")), supplier_name or ""]), 420),
        )
        record_id, is_created, changed = self._upsert_source_record(
            source="khmdhs", external_id=reference, record_type=endpoint,
            organization_id=buyer_id, evidence=evidence, raw=record,
        )
        category, reasons = classify_category(json.dumps(record, ensure_ascii=False), collect_cpv_codes(record))
        kind = {"auction": "award", "contract": "contract", "payment": "payment"}[endpoint]
        self._upsert_signal(
            organization_id=buyer_id, category=category, kind=kind,
            stage="awarded" if endpoint != "payment" else "historical",
            score=18, confidence=92,
            why_now="Ολοκληρωμένη ανάθεση/σύμβαση: χρησιμεύει ως ιστορικό αγοράς και ένδειξη incumbent, όχι ως ανοιχτή ευκαιρία.",
            reasons=[*reasons, "Post-award market evidence"], source_record_id=record_id,
        )
        amount = _record_budget(record)
        if supplier_id and endpoint in {"auction", "contract"}:
            self._upsert_award(
                buyer_id=buyer_id, supplier_id=supplier_id, title=title, category=category,
                amount=amount, awarded_at=published_at, source_record_id=record_id,
            )
        self._record_brand_mentions(
            json.dumps(record, ensure_ascii=False), source_record_id=record_id,
            buyer_id=buyer_id, supplier_id=supplier_id,
        )
        return (1 if is_created else 0, 1 if changed and not is_created else 0)

    async def _refresh_ted(self, days: int) -> MarketRefreshSourceResult:
        client = TedClient(self.settings)
        records = await client.market_records(
            date.today() - timedelta(days=max(1, days) - 1),
            date.today(),
            limit=min(1000, max(100, days * 3)),
        )
        opportunities = [client._to_opportunity(record) for record in records]
        created, updated = self.ingest_opportunities(opportunities)
        for record, opportunity in zip(records, opportunities):
            supplier_name = first_text(
                record.get("winner-name") or record.get("touchpoint-name-winner") or record.get("organisation-name-winner")
            )
            if not supplier_name:
                continue
            buyer_id = self._organization_id_by_name(opportunity.buyer)
            supplier_id = self._upsert_organization(supplier_name, role="supplier", country=first_text(record.get("winner-country"), "GR"))
            source_record_id = f"source-{stable_id('ted', opportunity.source_reference, _ted_kind(opportunity.notice_type or ''))}"
            category, _ = classify_category(json.dumps(record, ensure_ascii=False), collect_cpv_codes(record))
            if buyer_id:
                self._upsert_award(
                    buyer_id=buyer_id, supplier_id=supplier_id, title=opportunity.title,
                    category=category, amount=_record_budget(record), awarded_at=opportunity.published_at,
                    source_record_id=source_record_id,
                )
                self._record_brand_mentions(json.dumps(record, ensure_ascii=False), source_record_id=source_record_id, buyer_id=buyer_id, supplier_id=supplier_id)
        return MarketRefreshSourceResult(source="ted", status="ok", fetched=len(records), created=created, updated=updated)

    async def _refresh_diavgeia(self) -> MarketRefreshSourceResult:
        with self._connect() as connection:
            rows = connection.execute(
                """SELECT DISTINCT o.id, o.name FROM market_organizations o
                   JOIN market_tracking_entries t ON t.entity_id=o.id AND t.entity_type='buyer'
                   WHERE t.state NOT IN ('archived','lost') ORDER BY t.updated_at DESC LIMIT 20"""
            ).fetchall()
        if not rows:
            return MarketRefreshSourceResult(source="diavgeia", status="skipped")
        fetched = created = updated = 0
        async with httpx.AsyncClient(timeout=self.settings.diavgeia_timeout_seconds) as client:
            for row in rows:
                response = await client.get(
                    f"{str(self.settings.diavgeia_base_url).rstrip('/')}/search",
                    params={"term": row["name"], "size": 10, "page": 0, "sort": "recent"},
                )
                response.raise_for_status()
                records = extract_records(response.json())
                fetched += len(records)
                for record in records:
                    c, u = self._ingest_diavgeia_record(str(row["id"]), record)
                    created += c
                    updated += u
        return MarketRefreshSourceResult(source="diavgeia", status="ok", fetched=fetched, created=created, updated=updated)

    def _ingest_diavgeia_record(self, buyer_id: str, record: dict[str, Any]) -> tuple[int, int]:
        title = first_text(record.get("subject"), "Απόφαση Διαύγειας")
        ada = first_text(record.get("ada"), stable_id(title, record.get("publishTimestamp")))
        published_at = _timestamp_date(record.get("publishTimestamp")) or parse_date(record.get("issueDate"))
        evidence = EvidenceRef(
            source="diavgeia", external_id=ada, url=first_text(record.get("url")) or None,
            title=title, published_at=published_at, excerpt=truncate(title, 420),
        )
        record_id, is_created, changed = self._upsert_source_record(
            source="diavgeia", external_id=ada, record_type="decision", organization_id=buyer_id,
            evidence=evidence, raw=record,
        )
        extra = record.get("extraFieldValues") if isinstance(record.get("extraFieldValues"), dict) else {}
        supplier_name = _winner_name(extra)
        supplier_id = self._upsert_organization(supplier_name, role="supplier") if supplier_name else None
        category, reasons = classify_category(json.dumps(record, ensure_ascii=False), collect_cpv_codes(record))
        self._upsert_signal(
            organization_id=buyer_id, category=category, kind="award", stage="awarded",
            score=18, confidence=74, why_now="Απόφαση/ανάθεση από τη Διαύγεια: ιστορική ένδειξη αγοράς και incumbent.",
            reasons=[*reasons, "Best-effort Diavgeia match by buyer name"], source_record_id=record_id,
        )
        if supplier_id:
            amount = _nested_amount(extra)
            self._upsert_award(
                buyer_id=buyer_id, supplier_id=supplier_id, title=title, category=category,
                amount=amount, awarded_at=published_at, source_record_id=record_id,
            )
        self._record_brand_mentions(json.dumps(record, ensure_ascii=False), source_record_id=record_id, buyer_id=buyer_id, supplier_id=supplier_id)
        return (1 if is_created else 0, 1 if changed and not is_created else 0)

    async def _refresh_gemi(self) -> MarketRefreshSourceResult:
        client = GemiClient(self.settings)
        if not client.enabled:
            return MarketRefreshSourceResult(source="gemi", status="skipped", error="GEMI_API_KEY is not configured.")
        profiles = [profile for profile in self.list_discovery_profiles() if profile.enabled]
        if not profiles:
            return MarketRefreshSourceResult(source="gemi", status="skipped")
        fetched = created = updated = 0
        for profile in profiles:
            records = await client.search_companies(
                activities=profile.activities, prefectures=profile.prefectures,
                municipalities=profile.municipalities, is_active=profile.is_active, size=100,
            )
            fetched += len(records)
            for record in records:
                name = first_text(record.get("coName") or record.get("name") or record.get("companyName"), "Unknown company")
                gemi_number = first_text(record.get("arGemi") or record.get("gemiNumber")) or None
                tax_id = first_text(record.get("afm") or record.get("taxId")) or None
                org_id = self._upsert_organization(name, role="buyer", gemi_number=gemi_number, tax_id=tax_id)
                external_id = gemi_number or stable_id(name, tax_id)
                evidence = EvidenceRef(
                    source="gemi", external_id=external_id,
                    url=f"https://www.businessregistry.gr/publicity/show/{gemi_number}" if gemi_number else None,
                    title=f"ΓΕΜΗ: {name}", published_at=parse_date(record.get("incorporationDate")),
                    excerpt=truncate(json.dumps(record, ensure_ascii=False), 420),
                )
                _, is_created, changed = self._upsert_source_record(
                    source="gemi", external_id=external_id, record_type="company",
                    organization_id=org_id, evidence=evidence, raw=record,
                )
                created += int(is_created)
                updated += int(changed and not is_created)
            with self._connect() as connection:
                connection.execute("UPDATE market_discovery_profiles SET last_run_at=?, updated_at=? WHERE id=?", (_iso_now(), _iso_now(), profile.id))
        return MarketRefreshSourceResult(source="gemi", status="ok", fetched=fetched, created=created, updated=updated)

    async def _refresh_watch_sources(self) -> MarketRefreshSourceResult:
        sources = [item for item in self.list_watch_sources() if item.enabled]
        if not sources:
            return MarketRefreshSourceResult(source="private_web", status="skipped")
        fetched = created = updated = 0
        for source in sources:
            try:
                content, content_type = await self._fetch_watch_url(source.url)
                fetched += 1
                digest = hashlib.sha256(content).hexdigest()
                with self._connect() as connection:
                    previous = connection.execute("SELECT content_hash FROM market_watch_sources WHERE id=?", (source.id,)).fetchone()
                changed = previous is None or previous["content_hash"] != digest
                text = _visible_text(content.decode("utf-8", errors="replace"), content_type)
                if changed:
                    c, u = self._ingest_private_text(source, text, digest)
                    created += c
                    updated += u
                now = _iso_now()
                with self._connect() as connection:
                    connection.execute(
                        """UPDATE market_watch_sources SET content_hash=?, last_checked_at=?,
                           last_changed_at=CASE WHEN ? THEN ? ELSE last_changed_at END,
                           last_error=NULL, updated_at=? WHERE id=?""",
                        (digest, now, int(changed), now, now, source.id),
                    )
            except Exception as exc:
                with self._connect() as connection:
                    connection.execute(
                        "UPDATE market_watch_sources SET last_checked_at=?, last_error=?, updated_at=? WHERE id=?",
                        (_iso_now(), f"{exc.__class__.__name__}: {str(exc)[:220]}", _iso_now(), source.id),
                    )
        return MarketRefreshSourceResult(source="private_web", status="ok", fetched=fetched, created=created, updated=updated)

    async def _fetch_watch_url(self, url: str) -> tuple[bytes, str]:
        await asyncio.to_thread(_validate_public_https_url, url, True)
        headers = {"User-Agent": self.settings.market_user_agent, "Accept": "text/html,application/json,text/plain"}
        async with httpx.AsyncClient(timeout=18, headers=headers, follow_redirects=True) as client:
            async with client.stream("GET", url) as response:
                response.raise_for_status()
                final_url = str(response.url)
                await asyncio.to_thread(_validate_public_https_url, final_url, True)
                content_type = response.headers.get("content-type", "").casefold()
                if not any(kind in content_type for kind in ("text/", "html", "json", "xml")):
                    raise ValueError("Watch URL returned an unsupported content type.")
                chunks: list[bytes] = []
                size = 0
                async for chunk in response.aiter_bytes():
                    size += len(chunk)
                    if size > 1_500_000:
                        raise ValueError("Watch URL response exceeded 1.5 MB.")
                    chunks.append(chunk)
        return b"".join(chunks), content_type

    def _ingest_private_text(self, source: WatchSource, text: str, digest: str) -> tuple[int, int]:
        lower = normalize_text(text)
        category, category_reasons = classify_category(lower, [])
        best_rule = next((rule for rule in PRIVATE_SIGNAL_RULES if any(term in lower for term in rule[1])), None)
        if not best_rule or category == "General Software":
            return 0, 0
        kind, _, base_score, why = best_rule
        matches = [term for term in best_rule[1] if term in lower][:4]
        external_id = f"{source.id}-{digest[:16]}"
        evidence = EvidenceRef(
            source=f"company_{source.source_type}", external_id=external_id, url=source.url,
            title=source.label or source.url, published_at=date.today(), excerpt=truncate(text, 420),
        )
        record_id, is_created, changed = self._upsert_source_record(
            source=f"company_{source.source_type}", external_id=external_id, record_type=kind,
            organization_id=source.organization_id, evidence=evidence,
            raw={"url": source.url, "content_hash": digest, "excerpt": truncate(text, 1200)},
        )
        score = min(84, base_score + min(12, len(matches) * 3))
        self._upsert_signal(
            organization_id=source.organization_id, category=category, kind=kind, stage="early",
            score=score, confidence=62, why_now=why,
            reasons=[*category_reasons, *[f"Matched private signal: {term}" for term in matches]],
            source_record_id=record_id,
        )
        self._record_brand_mentions(text, source_record_id=record_id, buyer_id=source.organization_id)
        return (1 if is_created else 0, 1 if changed and not is_created else 0)

    def _upsert_organization(
        self,
        name: str | None,
        *,
        role: str,
        country: str = "GR",
        gemi_number: str | None = None,
        tax_id: str | None = None,
        khmdhs_key: str | None = None,
        website: str | None = None,
    ) -> str:
        clean_name = " ".join((name or "Unknown organization").split())
        normalized = normalize_name(clean_name)
        country = (country or "GR").upper()[:3]
        now = _iso_now()
        with self._connect() as connection:
            row = None
            if gemi_number:
                row = connection.execute("SELECT id,role,name FROM market_organizations WHERE gemi_number=?", (gemi_number,)).fetchone()
            if not row and tax_id:
                row = connection.execute("SELECT id,role,name FROM market_organizations WHERE tax_id=?", (tax_id,)).fetchone()
            if not row and khmdhs_key:
                row = connection.execute("SELECT id,role,name FROM market_organizations WHERE khmdhs_key=?", (khmdhs_key,)).fetchone()
            if not row:
                row = connection.execute(
                    "SELECT id,role,name FROM market_organizations WHERE normalized_name=? AND country=?",
                    (normalized, country),
                ).fetchone()
            if row:
                org_id = str(row["id"])
                next_role = _merge_role(str(row["role"]), role)
                connection.execute(
                    """UPDATE market_organizations SET role=?, gemi_number=COALESCE(gemi_number,?),
                       tax_id=COALESCE(tax_id,?), khmdhs_key=COALESCE(khmdhs_key,?),
                       website=COALESCE(website,?), updated_at=? WHERE id=?""",
                    (next_role, gemi_number, tax_id, khmdhs_key, website, now, org_id),
                )
                if normalize_name(str(row["name"])) != normalized:
                    connection.execute(
                        "INSERT OR IGNORE INTO market_organization_aliases(organization_id,alias,normalized_alias) VALUES (?,?,?)",
                        (org_id, clean_name, normalized),
                    )
                return org_id
            org_id = f"org-{stable_id(country, normalized, gemi_number, tax_id, khmdhs_key)}"
            connection.execute(
                """INSERT INTO market_organizations
                   (id,name,normalized_name,role,country,gemi_number,tax_id,khmdhs_key,website,created_at,updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (org_id, clean_name, normalized, role, country, gemi_number, tax_id, khmdhs_key, website, now, now),
            )
            connection.execute(
                "INSERT OR IGNORE INTO market_organization_aliases(organization_id,alias,normalized_alias) VALUES (?,?,?)",
                (org_id, clean_name, normalized),
            )
        return org_id

    def _organization_id_by_name(self, name: str) -> str | None:
        normalized = normalize_name(name)
        with self._connect() as connection:
            row = connection.execute("SELECT id FROM market_organizations WHERE normalized_name=?", (normalized,)).fetchone()
            if not row:
                row = connection.execute("SELECT organization_id id FROM market_organization_aliases WHERE normalized_alias=?", (normalized,)).fetchone()
        return str(row["id"]) if row else None

    def _upsert_source_record(
        self,
        *,
        source: str,
        external_id: str,
        record_type: str,
        organization_id: str | None,
        evidence: EvidenceRef,
        raw: dict[str, Any],
    ) -> tuple[str, bool, bool]:
        record_id = f"source-{stable_id(source, external_id, record_type)}"
        raw_json = _json(raw)
        content_hash = hashlib.sha256(raw_json.encode("utf-8")).hexdigest()
        now = _iso_now()
        with self._connect() as connection:
            previous = connection.execute("SELECT content_hash FROM market_source_records WHERE id=?", (record_id,)).fetchone()
            is_created = previous is None
            changed = is_created or str(previous["content_hash"]) != content_hash
            connection.execute(
                """INSERT INTO market_source_records
                   (id,source,external_id,record_type,organization_id,title,url,published_at,content_hash,raw_json,first_seen_at,last_seen_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(id) DO UPDATE SET organization_id=excluded.organization_id,
                     title=excluded.title,url=excluded.url,published_at=excluded.published_at,
                     content_hash=excluded.content_hash,raw_json=excluded.raw_json,last_seen_at=excluded.last_seen_at""",
                (record_id, source, external_id, record_type, organization_id, evidence.title,
                 evidence.url, _date_iso(evidence.published_at), content_hash, raw_json, now, now),
            )
        return record_id, is_created, changed

    def _upsert_signal(
        self,
        *,
        organization_id: str,
        category: str,
        kind: str,
        stage: str,
        score: int,
        confidence: int,
        why_now: str,
        reasons: list[str],
        source_record_id: str,
    ) -> str:
        signal_id = f"signal-{stable_id(organization_id, kind, source_record_id)}"
        now = _iso_now()
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO market_need_signals
                   (id,organization_id,category,kind,stage,need_score,confidence,why_now,score_reasons_json,source_record_id,created_at,updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(id) DO UPDATE SET category=excluded.category,kind=excluded.kind,
                     stage=excluded.stage,need_score=excluded.need_score,confidence=excluded.confidence,
                     why_now=excluded.why_now,score_reasons_json=excluded.score_reasons_json,updated_at=excluded.updated_at""",
                (signal_id, organization_id, category, kind, stage, max(0, min(100, score)),
                 max(0, min(100, confidence)), why_now, _json(_dedupe_text(reasons)), source_record_id, now, now),
            )
        return signal_id

    def _upsert_award(
        self,
        *,
        buyer_id: str,
        supplier_id: str,
        title: str,
        category: str,
        amount: float | None,
        awarded_at: date | None,
        source_record_id: str,
    ) -> str:
        award_id = f"award-{stable_id(buyer_id, supplier_id, source_record_id)}"
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO market_supplier_awards
                   (id,buyer_id,supplier_id,title,category,amount,currency,awarded_at,source_record_id,created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(id) DO UPDATE SET title=excluded.title,category=excluded.category,
                     amount=excluded.amount,awarded_at=excluded.awarded_at""",
                (award_id, buyer_id, supplier_id, title, category, amount, "EUR",
                 _date_iso(awarded_at), source_record_id, _iso_now()),
            )
        return award_id

    def _record_brand_mentions(
        self,
        text: str,
        *,
        source_record_id: str,
        buyer_id: str | None = None,
        supplier_id: str | None = None,
    ) -> list[str]:
        normalized = normalize_text(text)
        found: list[str] = []
        for brand_id, item in BRAND_CATALOG.items():
            aliases = sorted(item["aliases"], key=len, reverse=True)
            matched = next((alias for alias in aliases if _contains_alias(normalized, normalize_text(alias))), None)
            if not matched:
                continue
            mention_id = f"mention-{stable_id(brand_id, source_record_id, buyer_id, supplier_id)}"
            with self._connect() as connection:
                connection.execute(
                    """INSERT INTO market_brand_mentions
                       (id,brand_id,product_name,buyer_id,supplier_id,source_record_id,confidence,created_at)
                       VALUES (?,?,?,?,?,?,?,?)
                       ON CONFLICT(id) DO UPDATE SET product_name=excluded.product_name,confidence=excluded.confidence""",
                    (mention_id, brand_id, matched if matched != brand_id else None, buyer_id, supplier_id,
                     source_record_id, 92, _iso_now()),
                )
            found.append(str(item["name"]))
        return found

    def _signals_for_org(self, organization_id: str) -> list[NeedSignal]:
        with self._connect() as connection:
            rows = connection.execute(
                """SELECT s.*, o.name organization_name, r.source, r.external_id, r.title evidence_title,
                          r.url evidence_url, r.published_at evidence_published_at, r.raw_json, 0 is_new
                   FROM market_need_signals s JOIN market_organizations o ON o.id=s.organization_id
                   JOIN market_source_records r ON r.id=s.source_record_id
                   WHERE s.organization_id=? ORDER BY s.need_score DESC, r.published_at DESC LIMIT 100""",
                (organization_id,),
            ).fetchall()
        return [_signal_from_row(row) for row in rows]

    def _awards_for_org(self, organization_id: str, side: str) -> list[SupplierAward]:
        column = "buyer_id" if side == "buyer" else "supplier_id"
        with self._connect() as connection:
            rows = connection.execute(
                f"""SELECT aw.*, bo.name buyer_name, so.name supplier_name,
                           r.source,r.external_id,r.title evidence_title,r.url evidence_url,
                           r.published_at evidence_published_at,r.raw_json
                    FROM market_supplier_awards aw
                    JOIN market_organizations bo ON bo.id=aw.buyer_id
                    JOIN market_organizations so ON so.id=aw.supplier_id
                    JOIN market_source_records r ON r.id=aw.source_record_id
                    WHERE aw.{column}=? ORDER BY aw.awarded_at DESC LIMIT 100""",
                (organization_id,),
            ).fetchall()
        return [self._award_from_row(row) for row in rows]

    def _awards_for_brand(self, brand_id: str) -> list[SupplierAward]:
        with self._connect() as connection:
            rows = connection.execute(
                """SELECT DISTINCT aw.*, bo.name buyer_name, so.name supplier_name,
                          r.source,r.external_id,r.title evidence_title,r.url evidence_url,
                          r.published_at evidence_published_at,r.raw_json
                   FROM market_supplier_awards aw
                   JOIN market_brand_mentions bm ON bm.source_record_id=aw.source_record_id AND bm.brand_id=?
                   JOIN market_organizations bo ON bo.id=aw.buyer_id
                   JOIN market_organizations so ON so.id=aw.supplier_id
                   JOIN market_source_records r ON r.id=aw.source_record_id
                   ORDER BY aw.awarded_at DESC LIMIT 100""",
                (brand_id,),
            ).fetchall()
        return [self._award_from_row(row) for row in rows]

    def _award_from_row(self, row: sqlite3.Row) -> SupplierAward:
        with self._connect() as connection:
            brands = [str(item[0]) for item in connection.execute(
                """SELECT b.name FROM market_brand_mentions bm JOIN market_software_brands b ON b.id=bm.brand_id
                   WHERE bm.source_record_id=? ORDER BY b.name""", (row["source_record_id"],)
            ).fetchall()]
        return SupplierAward(
            id=str(row["id"]), buyer_id=str(row["buyer_id"]), buyer_name=str(row["buyer_name"]),
            supplier_id=str(row["supplier_id"]), supplier_name=str(row["supplier_name"]), title=str(row["title"]),
            category=str(row["category"]), amount=float(row["amount"]) if row["amount"] is not None else None,
            currency=str(row["currency"]), awarded_at=parse_date(row["awarded_at"]), software_brands=brands,
            evidence=_evidence_from_row(row),
        )

    def _mentions_for_entity(self, *, organization_id: str | None = None, brand_id: str | None = None) -> list[SoftwareBrandMention]:
        where = "bm.brand_id=?" if brand_id else "(bm.buyer_id=? OR bm.supplier_id=?)"
        params: list[Any] = [brand_id] if brand_id else [organization_id, organization_id]
        with self._connect() as connection:
            rows = connection.execute(
                f"""SELECT bm.*, b.name brand_name, r.source,r.external_id,r.title evidence_title,
                           r.url evidence_url,r.published_at evidence_published_at,r.raw_json
                    FROM market_brand_mentions bm JOIN market_software_brands b ON b.id=bm.brand_id
                    JOIN market_source_records r ON r.id=bm.source_record_id
                    WHERE {where} ORDER BY r.published_at DESC LIMIT 100""", params
            ).fetchall()
        return [SoftwareBrandMention(
            id=str(row["id"]), brand_id=str(row["brand_id"]), brand_name=str(row["brand_name"]),
            product_name=str(row["product_name"]) if row["product_name"] else None,
            buyer_id=str(row["buyer_id"]) if row["buyer_id"] else None,
            supplier_id=str(row["supplier_id"]) if row["supplier_id"] else None,
            confidence=int(row["confidence"]), evidence=_evidence_from_row(row),
        ) for row in rows]

    def _acquire_refresh_lease(self, holder: str) -> bool:
        now = _utcnow()
        expires = now + timedelta(hours=3)
        with self._connect() as connection:
            connection.execute("DELETE FROM market_refresh_lease WHERE expires_at < ?", (now.isoformat(),))
            try:
                connection.execute(
                    "INSERT INTO market_refresh_lease(lease_key,holder,expires_at) VALUES ('market-refresh',?,?)",
                    (holder, expires.isoformat()),
                )
                return True
            except sqlite3.IntegrityError:
                return False

    def _release_refresh_lease(self, holder: str) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM market_refresh_lease WHERE lease_key='market-refresh' AND holder=?", (holder,))


def classify_category(text: str, cpv_codes: list[str]) -> tuple[str, list[str]]:
    normalized = normalize_text(text)
    scores: dict[str, int] = {}
    reasons: dict[str, list[str]] = {}
    for category, terms in CATEGORY_TERMS:
        matches = [term for term in terms if term in normalized]
        if matches:
            scores[category] = scores.get(category, 0) + min(18, len(matches) * 6)
            reasons.setdefault(category, []).extend(f"Matched term: {term}" for term in matches[:3])
    if re.search(r"(?:^|\s)erp(?:$|\s)", normalized):
        scores["ERP/Finance"] = scores.get("ERP/Finance", 0) + 12
        reasons.setdefault("ERP/Finance", []).append("Explicit ERP requirement")
    prefixes = {"".join(char for char in code if char.isdigit())[:6] for code in cpv_codes}
    cpv_mapping = [
        ("HR/HCM/Payroll", ("484500", "722124")),
        ("BI/Analytics/AI", ("723160", "722124", "723200")),
        ("Cybersecurity", ("487300", "487320", "728100")),
        ("DMS/Workflow/Collaboration", ("483111", "722123", "724200")),
        ("ITSM/IT Operations", ("722500", "722530", "503120", "727000")),
        ("Cloud/Infrastructure", ("488200", "324000", "725100")),
        ("Project Management/DevOps", ("722240", "722630", "722610")),
        ("ERP/Finance", ("484400", "484000")),
    ]
    for category, category_prefixes in cpv_mapping:
        if any(any(prefix.startswith(expected) for expected in category_prefixes) for prefix in prefixes):
            scores[category] = scores.get(category, 0) + 10
            reasons.setdefault(category, []).append("Matched software CPV family")
    if not scores:
        return "General Software", ["Software-related record without a more specific category"]
    category = max(scores, key=scores.get)
    return category, _dedupe_text(reasons.get(category, []))


def normalize_text(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    without_marks = "".join(char for char in decomposed if not unicodedata.combining(char))
    return " ".join(re.sub(r"[^a-z0-9α-ω]+", " ", without_marks).split())


def normalize_name(value: str) -> str:
    text = normalize_text(value)
    legal_terms = {"ae", "sa", "ltd", "ike", "oe", "ee", "μονοπροσωπη", "ανωνυμη", "εταιρεια"}
    tokens = text.split()
    if len(tokens) >= 2 and tokens[-2:] in (["a", "e"], ["α", "ε"]):
        tokens = tokens[:-2]
    tokens = [token for token in tokens if token not in legal_terms]
    return " ".join(tokens) or text


def _opportunity_stage(opportunity: Opportunity) -> tuple[str, str, int, str]:
    text = normalize_text(" ".join(filter(None, [opportunity.notice_type, opportunity.procedure_type, opportunity.status_label, opportunity.title])))
    if any(term in text for term in ("planning", "prior information", "consultation", "request", "αιτημα")):
        return "early", "planning_notice" if opportunity.source == "ted" else "procurement_request", 62, "Πρώιμο αίτημα/planning notice: υπάρχει χρόνος για discovery και προετοιμασία πριν τον διαγωνισμό."
    if any(term in text for term in ("award", "result", "contract", "αναθεση", "συμβαση", "awrd", "symv")):
        return "awarded", "award", 18, "Ολοκληρωμένη ανάθεση: ιστορική ένδειξη αγοράς και incumbent, όχι νέα ευκαιρία."
    if opportunity.deadline and opportunity.deadline >= date.today():
        return "open", "open_tender", 82, "Υπάρχει δημοσιευμένη ευκαιρία με ενεργή ή μελλοντική προθεσμία."
    if opportunity.source == "ted" and any(term in text for term in ("competition", "contract notice", "tender")):
        return "open", "open_tender", 75, "TED competition notice που χρειάζεται έλεγχο των εγγράφων και της προθεσμίας."
    return "early", "procurement_request", 55, "Νέα software-related κίνηση του οργανισμού που αξίζει παρακολούθηση."


def _ted_kind(notice_type: str) -> str:
    normalized = normalize_text(notice_type)
    if any(term in normalized for term in ("result", "award", "completion")):
        return "award"
    if any(term in normalized for term in ("planning", "prior", "consultation")):
        return "planning_notice"
    return "open_tender"


def _organization_from_row(row: sqlite3.Row) -> MarketOrganization:
    aliases_raw = str(row["aliases"] or "") if "aliases" in row.keys() else ""
    return MarketOrganization(
        id=str(row["id"]), name=str(row["name"]), normalized_name=str(row["normalized_name"]),
        role=str(row["role"]), country=str(row["country"] or "GR"),
        gemi_number=str(row["gemi_number"]) if row["gemi_number"] else None,
        tax_id=str(row["tax_id"]) if row["tax_id"] else None,
        khmdhs_key=str(row["khmdhs_key"]) if row["khmdhs_key"] else None,
        aliases=[item for item in aliases_raw.split("||") if item],
        website=str(row["website"]) if row["website"] else None,
        strongest_signal_score=int(row["strongest_signal_score"] or 0) if "strongest_signal_score" in row.keys() else 0,
        strongest_signal_kind=str(row["strongest_signal_kind"]) if "strongest_signal_kind" in row.keys() and row["strongest_signal_kind"] else None,
        strongest_category=str(row["strongest_category"]) if "strongest_category" in row.keys() and row["strongest_category"] else None,
        last_signal_at=parse_date(row["last_signal_at"]) if "last_signal_at" in row.keys() else None,
        incumbent_suppliers=_split_csv(row["incumbent_suppliers"]) if "incumbent_suppliers" in row.keys() else [],
        software_brands=_split_csv(row["software_brands"]) if "software_brands" in row.keys() else [],
        tracking_state=str(row["tracking_state"]) if "tracking_state" in row.keys() and row["tracking_state"] else None,
        next_action=str(row["next_action"]) if "next_action" in row.keys() and row["next_action"] else None,
        updated_at=_parse_datetime(row["updated_at"]) or _utcnow(),
    )


def _signal_from_row(row: sqlite3.Row) -> NeedSignal:
    return NeedSignal(
        id=str(row["id"]), organization_id=str(row["organization_id"]),
        organization_name=str(row["organization_name"]), category=str(row["category"]),
        kind=str(row["kind"]), stage=str(row["stage"]), need_score=int(row["need_score"]),
        confidence=int(row["confidence"]), why_now=str(row["why_now"]),
        score_reasons=_loads(row["score_reasons_json"], []), evidence=_evidence_from_row(row),
        is_new=bool(row["is_new"]) if "is_new" in row.keys() else False,
        created_at=_parse_datetime(row["created_at"]) or _utcnow(),
        updated_at=_parse_datetime(row["updated_at"]) or _utcnow(),
    )


def _evidence_from_row(row: sqlite3.Row) -> EvidenceRef:
    raw = _loads(row["raw_json"], {}) if "raw_json" in row.keys() else {}
    excerpt = first_text(raw.get("summary") or raw.get("excerpt") or raw.get("title"))
    return EvidenceRef(
        source=str(row["source"]), external_id=str(row["external_id"]) if row["external_id"] else None,
        url=str(row["evidence_url"]) if row["evidence_url"] else None,
        title=str(row["evidence_title"]), published_at=parse_date(row["evidence_published_at"]),
        excerpt=truncate(excerpt or str(row["evidence_title"]), 420),
    )


def _brand_from_row(row: sqlite3.Row) -> SoftwareBrand:
    return SoftwareBrand(
        id=str(row["id"]), name=str(row["name"]), origin_region=str(row["origin_region"]),
        aliases=_loads(row["aliases_json"], []), mention_count=int(row["mention_count"] or 0),
        observed_spend=float(row["observed_spend"] or 0), supplier_names=_split_csv(row["supplier_names"]),
        buyer_names=_split_csv(row["buyer_names"]), last_seen_at=parse_date(row["last_seen_at"]),
    )


def _watch_from_row(row: sqlite3.Row) -> WatchSource:
    return WatchSource(
        id=str(row["id"]), organization_id=str(row["organization_id"]), organization_name=str(row["organization_name"]),
        source_type=str(row["source_type"]), url=str(row["url"]), label=str(row["label"] or ""), enabled=bool(row["enabled"]),
        last_checked_at=_parse_datetime(row["last_checked_at"]), last_changed_at=_parse_datetime(row["last_changed_at"]),
        last_error=str(row["last_error"]) if row["last_error"] else None,
    )


def _profile_from_row(row: sqlite3.Row) -> DiscoveryProfile:
    return DiscoveryProfile(
        id=str(row["id"]), name=str(row["name"]), activities=_loads(row["activities_json"], []),
        prefectures=_loads(row["prefectures_json"], []), municipalities=_loads(row["municipalities_json"], []),
        is_active=bool(row["is_active"]), enabled=bool(row["enabled"]), last_run_at=_parse_datetime(row["last_run_at"]),
        created_at=_parse_datetime(row["created_at"]) or _utcnow(), updated_at=_parse_datetime(row["updated_at"]) or _utcnow(),
    )


def _validate_public_https_url(url: str, resolve_dns: bool = False) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Only public HTTPS URLs are allowed.")
    hostname = parsed.hostname.casefold()
    if hostname in {"localhost", "localhost.localdomain"} or hostname.endswith(".local"):
        raise ValueError("Local watch URLs are not allowed.")
    try:
        address = ipaddress.ip_address(hostname)
        if not address.is_global:
            raise ValueError("Private or reserved IP addresses are not allowed.")
    except ValueError as exc:
        if "not allowed" in str(exc):
            raise
    if resolve_dns:
        for result in socket.getaddrinfo(hostname, 443, type=socket.SOCK_STREAM):
            address = ipaddress.ip_address(result[4][0])
            if not address.is_global:
                raise ValueError("Watch URL resolved to a private or reserved IP address.")


def _visible_text(raw: str, content_type: str) -> str:
    if "html" not in content_type:
        return truncate(raw, 20_000)
    cleaned = re.sub(r"(?is)<(script|style|noscript).*?>.*?</\1>", " ", raw)
    cleaned = re.sub(r"(?s)<[^>]+>", " ", cleaned)
    return truncate(html.unescape(cleaned), 20_000)


def _contractor_name(record: dict[str, Any]) -> str | None:
    for key in ("contractorName", "contractor", "supplierName", "vendorName", "awardee", "economicOperator"):
        text = first_text(record.get(key))
        if text:
            return text
    for key in ("contractors", "suppliers", "economicOperators"):
        values = record.get(key)
        if isinstance(values, list) and values:
            text = first_text(values[0])
            if text:
                return text
    details = record.get("contractingDataDetails")
    if isinstance(details, dict):
        members = details.get("contractingMembersDataList")
        if isinstance(members, list) and members:
            return first_text(members[0].get("name") if isinstance(members[0], dict) else members[0]) or None
    return None


def _winner_name(extra: dict[str, Any]) -> str | None:
    for key in ("person", "sponsor", "contractor", "recipient"):
        value = extra.get(key)
        if isinstance(value, list) and value:
            return first_text(value[0].get("name") if isinstance(value[0], dict) else value[0]) or None
        if isinstance(value, dict):
            return first_text(value.get("name")) or None
    return None


def _record_budget(record: dict[str, Any]) -> float | None:
    for key in ("totalCostWithoutVAT", "totalCostWithVAT", "budget", "contractBudget", "contractValue", "amount", "total-value"):
        value = record.get(key)
        if isinstance(value, dict):
            value = value.get("amount") or value.get("value")
        try:
            if value not in (None, ""):
                return float(value)
        except (TypeError, ValueError):
            continue
    return None


def _nested_amount(extra: dict[str, Any]) -> float | None:
    value = extra.get("awardAmount")
    if isinstance(value, dict):
        try:
            return float(value.get("amount"))
        except (TypeError, ValueError):
            return None
    return None


def _extract_key(value: Any) -> str | None:
    return first_text(value.get("key") or value.get("id")) or None if isinstance(value, dict) else None


def _timestamp_date(value: Any) -> date | None:
    try:
        timestamp = int(value)
        if timestamp > 10_000_000_000:
            timestamp //= 1000
        return datetime.fromtimestamp(timestamp, tz=timezone.utc).date()
    except (TypeError, ValueError, OSError):
        return None


def _contains_alias(text: str, alias: str) -> bool:
    return bool(re.search(rf"(?:^|\s){re.escape(alias)}(?:$|\s)", text))


def _merge_role(existing: str, incoming: str) -> str:
    if existing == incoming:
        return existing
    if "both" in {existing, incoming} or {existing, incoming} == {"buyer", "supplier"}:
        return "both"
    return incoming


def _dedupe_text(values: Iterable[str]) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for value in values:
        clean = " ".join(str(value or "").split())
        key = clean.casefold()
        if clean and key not in seen:
            seen.add(key)
            output.append(clean)
    return output


def _split_csv(value: Any) -> list[str]:
    return _dedupe_text(str(value or "").split(","))


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _loads(value: Any, default: Any) -> Any:
    try:
        return json.loads(str(value))
    except (TypeError, ValueError, json.JSONDecodeError):
        return default


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso_now() -> str:
    return _utcnow().isoformat()


def _parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _date_iso(value: date | None) -> str | None:
    return value.isoformat() if value else None
