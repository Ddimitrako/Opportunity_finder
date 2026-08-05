import {
  Activity,
  AlertTriangle,
  ArrowUpRight,
  Award,
  BarChart3,
  Bot,
  BookmarkCheck,
  BookmarkPlus,
  Building2,
  CalendarClock,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  CheckCircle2,
  CircleDollarSign,
  DatabaseZap,
  ExternalLink,
  FileText,
  Filter,
  Gauge,
  Globe2,
  Info,
  Layers3,
  Loader2,
  MessageSquare,
  PanelRightOpen,
  Radar,
  RefreshCw,
  Save,
  Search,
  Send,
  ShieldCheck,
  Sparkles,
  Target,
  TrendingUp,
  Users,
  Handshake,
  Tags,
  Trash2,
  UserRound,
  Plus,
  X,
  type LucideIcon,
} from 'lucide-react'
import { type CSSProperties, type FormEvent, type ReactNode, useCallback, useEffect, useMemo, useState } from 'react'
import './App.css'

type SourceName = 'khmdhs' | 'ted' | 'demo'

type SourceRun = {
  source: SourceName
  status: 'ok' | 'error' | 'skipped'
  items: number
  shown?: number
  elapsed_ms: number
  error?: string | null
}

type SoftwareProduct = {
  slug: string
  name: string
  edition: string
  repository: string
  website: string
  summary: string
  problem: string
  ideal_for: string
  department_ids: string[]
  category_ids: string[]
  buyer_roles: string[]
  company_sizes: string[]
  deployment_modes: string[]
  service_types: string[]
  license_id: string
  maturity: 'anchor' | 'established' | 'niche-leader'
  editorial_score: number
  english_support: string
  greek_support: 'verified' | 'partial' | 'unavailable' | 'unknown'
  greek_evidence?: string | null
  edition_boundary?: string | null
  featured: boolean
  last_verified_at: string
  extra_keywords_en: string[]
  extra_keywords_el: string[]
  negative_keywords: string[]
  delivery_fit: 'solo' | 'small_team' | 'partner_required'
  active: boolean
}

type SoftwareMatchDimension = {
  key: string
  label: string
  score: number
  max_score: number
  reasons: string[]
}

type ServiceRecommendation = {
  service_type: string
  label: string
  confidence: 'recommended' | 'possible'
  reasons: string[]
}

type SoftwareMatch = {
  product: SoftwareProduct
  score: number
  confidence: 'high' | 'medium' | 'low'
  source: 'deterministic' | 'ai_refined'
  dimensions: SoftwareMatchDimension[]
  matched_signals: string[]
  service_recommendations: ServiceRecommendation[]
  caveats: string[]
  evidence_ids: string[]
  catalog_version: string
}

type Opportunity = {
  id: string
  source: SourceName
  source_label: string
  title: string
  buyer: string
  buyer_type?: string | null
  procedure_type?: string | null
  cpv_codes: string[]
  budget?: number | null
  currency: string
  deadline?: string | null
  published_at?: string | null
  country: string
  location?: string | null
  url?: string | null
  platform_label?: string | null
  source_reference?: string | null
  status_label?: string | null
  notice_type?: string | null
  summary: string
  raw_text?: string
  matched_keywords: string[]
  fit_score: number
  fit_band: 'Bid candidate' | 'Worth reading' | 'Monitor only' | 'Ignore'
  score_reasons: string[]
  red_flags: string[]
  recommendation: string
  package_match: string
  software_match_status: 'matched' | 'insufficient_signals'
  software_matches: SoftwareMatch[]
  source_payload?: Record<string, unknown>
}

type DocumentLink = {
  label: string
  url: string
  document_type: string
  language?: string | null
  reference?: string | null
}

type LifecycleStep = {
  id: string
  label: string
  status: 'complete' | 'current' | 'upcoming' | 'unknown'
  description: string
  references: string[]
  url?: string | null
}

type GuidanceChecklistItem = {
  label: string
  detail: string
  status: 'done' | 'todo' | 'watch' | 'blocked'
}

type OpportunityGuidance = {
  current_stage: string
  current_stage_label: string
  is_actionable: boolean
  next_action: string
  stage_steps: LifecycleStep[]
  checklist: GuidanceChecklistItem[]
  watch_items: string[]
  primary_action_link?: string | null
}

type OpportunityDetails = {
  source: SourceName
  reference: string
  title?: string | null
  platform_url?: string | null
  summary?: string | null
  metadata: Record<string, unknown>
  documents: DocumentLink[]
  related_references: Record<string, string[]>
  guidance?: OpportunityGuidance | null
  raw: Record<string, unknown>
}

type BriefEvidence = {
  id: string
  document_label: string
  url: string
  excerpt: string
  page?: number | null
  reference?: string | null
}

type BriefFinding = {
  text: string
  evidence_ids: string[]
}

type BriefScoreDimension = {
  key: string
  label: string
  score: number
  max_score: number
  reason: string
  evidence_ids: string[]
}

type DocumentBrief = {
  source: SourceName
  reference: string
  schema_version: number
  rules_version: string
  verdict: 'GO' | 'CONDITIONAL GO' | 'NO-GO' | 'INSUFFICIENT DATA'
  score: number
  confidence: 'high' | 'medium' | 'low'
  executive_recommendation: string
  decision_reasons: BriefFinding[]
  project_summary: string
  actionable: 'yes' | 'no' | 'maybe' | 'unknown'
  procurement_access: {
    status: 'open_competition' | 'named_invitation' | 'awarded' | 'contracted' | 'paid' | 'planning_only' | 'expired' | 'unknown'
    reason: string
    procedure?: string | null
    deadline?: string | null
    days_remaining?: number | null
    submission_method: string
    named_invitee?: string | null
    evidence_ids: string[]
  }
  continuity: {
    status: 'confirmed_continuation' | 'not_confirmed' | 'unknown'
    reason: string
    incumbent_name?: string | null
    prior_reference?: string | null
    evidence_ids: string[]
  }
  budget_assessment: {
    amount_without_vat?: number | null
    amount_with_vat?: number | null
    currency: string
    direct_award_eligible?: boolean | null
    threshold_without_vat: number
    determination: string
    legal_basis_url: string
    evidence_ids: string[]
  }
  score_dimensions: BriefScoreDimension[]
  deadline_submission: string
  required_documents: string[]
  eligibility_requirements: BriefFinding[]
  evaluation_criteria: BriefFinding[]
  technical_requirements: string[]
  technical_findings: BriefFinding[]
  commercial_findings: BriefFinding[]
  contractual_findings: BriefFinding[]
  red_flags: string[]
  red_flag_findings: BriefFinding[]
  unknowns: string[]
  recommendation: string
  next_steps: string[]
  history_12_months: Array<{
    title: string
    reference?: string | null
    amount?: number | null
    published_at?: string | null
    supplier?: string | null
    url?: string | null
  }>
  evidence: BriefEvidence[]
  source_documents: DocumentLink[]
  generated_at: string
  model?: string | null
  cached: boolean
}

type DocumentBriefResponse = {
  brief?: DocumentBrief | null
  cached: boolean
  outdated: boolean
  message?: string | null
}

type OpportunityChatContextStatus = {
  ready: boolean
  prepared_at?: string | null
  available_document_count: number
  analyzed_document_count: number
  readable_document_count: number
  unreadable_document_labels: string[]
}

type OpportunityChatCitation = {
  id: string
  kind: 'evidence' | 'history'
  label: string
  url?: string | null
  page?: number | null
  reference?: string | null
  excerpt?: string | null
}

type OpportunityChatMessage = {
  id: number
  role: 'user' | 'assistant'
  content: string
  strategic_advice?: string | null
  citations: OpportunityChatCitation[]
  suggested_questions: string[]
  model?: string | null
  created_at: string
}

type OpportunityChatThreadResponse = {
  messages: OpportunityChatMessage[]
  context: OpportunityChatContextStatus
  suggested_questions: string[]
}

type OpportunityChatTurnResponse = {
  user_message: OpportunityChatMessage
  assistant_message: OpportunityChatMessage
  context: OpportunityChatContextStatus
}

type BudgetProfile = {
  count: number
  min?: number | null
  max?: number | null
  average?: number | null
  median?: number | null
  typical_range: string
}

type BuyerOpportunitySample = {
  id: string
  title: string
  source: SourceName
  source_label: string
  budget?: number | null
  published_at?: string | null
  deadline?: string | null
  cpv_codes: string[]
  fit_score: number
  package_match?: string | null
  url?: string | null
}

type DiavgeiaDecisionSignal = {
  source_label: string
  ada?: string | null
  subject: string
  decision_type?: string | null
  published_at?: string | null
  amount?: number | null
  currency: string
  winner_name?: string | null
  cpv_codes: string[]
  url?: string | null
  document_url?: string | null
  similar_to_software: boolean
}

type BuyerIntelligenceResponse = {
  buyer: string
  generated_at: string
  market_window_count: number
  visible_buyer_opportunity_count: number
  history_opportunity_count: number
  buyer_opportunity_count: number
  source_counts: Partial<Record<SourceName, number>>
  budget_profile: BudgetProfile
  small_software_count: number
  current_cpv_categories: string[]
  khmdhs_history_date_from?: string | null
  khmdhs_history_date_to?: string | null
  khmdhs_history_result_date_from?: string | null
  khmdhs_history_result_date_to?: string | null
  similar_opportunities: BuyerOpportunitySample[]
  recent_opportunities: BuyerOpportunitySample[]
  has_similar_procurement: boolean
  khmdhs_history_status: 'ok' | 'error' | 'skipped'
  khmdhs_history_message?: string | null
  diavgeia_status: 'ok' | 'error' | 'skipped'
  diavgeia_message?: string | null
  diavgeia_decisions: DiavgeiaDecisionSignal[]
  winner_signals: DiavgeiaDecisionSignal[]
  confidence_notes: string[]
  insight_flags: string[]
}

type SearchResponse = {
  generated_at: string
  opportunities: Opportunity[]
  source_runs: SourceRun[]
  stats: {
    total: number
    bid_candidates: number
    worth_reading: number
    total_budget: number
    average_score: number
    by_band: Record<string, number>
    by_package: Record<string, number>
  }
}

type PatternOpportunitySample = {
  id: string
  title: string
  buyer: string
  source: SourceName
  source_label: string
  budget?: number | null
  published_at?: string | null
  deadline?: string | null
  cpv_codes: string[]
  fit_score: number
  package_match?: string | null
}

type NeedPattern = {
  pattern_id: string
  label: string
  category: string
  recommended_package: string
  repeat_score: number
  productization_score: number
  opportunity_count: number
  buyer_count: number
  median_budget?: number | null
  min_budget?: number | null
  max_budget?: number | null
  budget_range: string
  keywords: string[]
  cpv_families: string[]
  buyers: string[]
  samples: PatternOpportunitySample[]
  recommended_products: SoftwareMatch[]
}

type NeedPatternResponse = {
  generated_at: string
  patterns: NeedPattern[]
  unmatched_count: number
  patternable_count: number
}

type DailyActivity = {
  date: string
  label: string
  total: number
  by_source: Partial<Record<SourceName, number>>
}

type CalendarDayCell = {
  date: string
  dayOfMonth: number
  offset: number
  inMonth: boolean
  isToday: boolean
  isFuture: boolean
  total: number
  by_source: Partial<Record<SourceName, number>>
}

type CalendarMonth = {
  year: number
  month: number
  label: string
  total: number
  cells: CalendarDayCell[]
}

type ActivityResponse = {
  generated_at: string
  date_from: string
  date_to: string
  daily_activity: DailyActivity[]
  source_runs: SourceRun[]
  total: number
  cached: boolean
}

type BookmarkRecord = {
  id: string
  opportunity: Opportunity
  created_at: string
  updated_at: string
}

type BookmarkListResponse = {
  bookmarks: BookmarkRecord[]
}

type ConfigResponse = {
  default_cpv_codes: string[]
  default_keywords: string[]
  packages: Array<{ name: string; label: string; keywords: string[] }>
  sources: Array<{ id: SourceName; label: string }>
  default_ai_model: string
  ai_models: AIModelOption[]
  software_catalog_version: string
  software_catalog_count: number
  software_match_ai_enabled: boolean
}

type SoftwareMatchRefineResponse = {
  matches: SoftwareMatch[]
  match_status: 'matched' | 'insufficient_signals'
  model?: string | null
  cached: boolean
  catalog_version: string
}

type AIModelOption = {
  id: string
  label: string
  description: string
  quality: string
  recommended: boolean
}

type TrackingState = 'new' | 'watching' | 'researching' | 'contact_planned' | 'contacted' | 'meeting' | 'proposal' | 'partner_target' | 'won' | 'lost' | 'archived'

type EvidenceRef = {
  source: string
  external_id?: string | null
  url?: string | null
  title: string
  published_at?: string | null
  excerpt: string
}

type MarketSignal = {
  id: string
  organization_id: string
  organization_name: string
  category: string
  kind: string
  stage: 'early' | 'open' | 'awarded' | 'historical'
  need_score: number
  confidence: number
  why_now: string
  score_reasons: string[]
  evidence: EvidenceRef
  is_new: boolean
  created_at: string
  updated_at: string
}

type MarketOrganization = {
  id: string
  name: string
  normalized_name: string
  role: 'buyer' | 'supplier' | 'both'
  country: string
  gemi_number?: string | null
  tax_id?: string | null
  khmdhs_key?: string | null
  aliases: string[]
  website?: string | null
  strongest_signal_score: number
  strongest_signal_kind?: string | null
  strongest_category?: string | null
  last_signal_at?: string | null
  incumbent_suppliers: string[]
  software_brands: string[]
  tracking_state?: TrackingState | null
  next_action?: string | null
  updated_at: string
}

type SupplierAward = {
  id: string
  buyer_id: string
  buyer_name: string
  supplier_id: string
  supplier_name: string
  title: string
  category: string
  amount?: number | null
  currency: string
  awarded_at?: string | null
  software_brands: string[]
  evidence: EvidenceRef
}

type BrandMention = {
  id: string
  brand_id: string
  brand_name: string
  product_name?: string | null
  buyer_id?: string | null
  supplier_id?: string | null
  confidence: number
  evidence: EvidenceRef
}

type TrackingEntry = {
  id: string
  entity_type: 'buyer' | 'supplier' | 'brand' | 'opportunity'
  entity_id: string
  entity_name: string
  state: TrackingState
  notes: string
  next_action?: string | null
  next_action_at?: string | null
  created_at: string
  updated_at: string
}

type WatchSource = {
  id: string
  organization_id: string
  organization_name: string
  source_type: 'careers' | 'newsroom'
  url: string
  label: string
  enabled: boolean
  last_checked_at?: string | null
  last_changed_at?: string | null
  last_error?: string | null
}

type MarketOrganizationDetail = {
  organization: MarketOrganization
  signals: MarketSignal[]
  awards_as_buyer: SupplierAward[]
  awards_as_supplier: SupplierAward[]
  brand_mentions: BrandMention[]
  tracking?: TrackingEntry | null
  watch_sources: WatchSource[]
}

type SoftwareBrand = {
  id: string
  name: string
  origin_region: 'Europe' | 'United States' | 'China' | 'Other'
  aliases: string[]
  mention_count: number
  observed_spend: number
  supplier_names: string[]
  buyer_names: string[]
  last_seen_at?: string | null
}

type MarketOverview = {
  generated_at: string
  period_days: number
  new_signals: number
  hot_buyers: number
  open_opportunities: number
  observed_public_spend: number
  tracked_entities: number
  categories: Array<{ category: string; current_count: number; previous_count: number; delta_percent?: number | null; observed_spend: number }>
  hot_organizations: MarketOrganization[]
  recent_signals: MarketSignal[]
  top_suppliers: MarketOrganization[]
  top_brands: SoftwareBrand[]
  coverage: Record<string, string>
  last_refresh_at?: string | null
}

type MarketConfig = {
  gemi_enabled: boolean
  refresh_enabled: boolean
  refresh_hour: number
  categories: string[]
  tracking_states: TrackingState[]
}

type MarketRefresh = {
  run_id: string
  status: 'running' | 'ok' | 'partial' | 'error' | 'skipped'
  started_at: string
  finished_at?: string | null
  source_results: Array<{ source: string; status: 'ok' | 'error' | 'skipped'; fetched: number; created: number; updated: number; error?: string | null }>
  message?: string | null
}

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

const CALENDAR_WEEKDAYS = ['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa']

const SOURCE_META: Record<SourceName, { label: string; icon: LucideIcon }> = {
  khmdhs: { label: 'ΚΗΜΔΗΣ', icon: DatabaseZap },
  ted: { label: 'TED', icon: Globe2 },
  demo: { label: 'Demo', icon: Sparkles },
}

const DASHBOARD_SOURCES: SourceName[] = ['khmdhs', 'ted']

const FALLBACK_CPV = [
  '72000000-5',
  '72212000-4',
  '72212100-0',
  '72262000-9',
  '72263000-6',
  '72250000-2',
  '72253000-3',
  '72261000-2',
  '72268000-1',
  '72420000-0',
  '72421000-7',
  '72413000-8',
  '72415000-2',
  '72416000-9',
  '72316000-3',
  '72320000-4',
  '72212482-0',
  '48311100-2',
  '72212311-2',
  '72267100-0',
  '30200000-1',
  '30210000-4',
  '30213000-5',
  '30213100-6',
  '30213300-8',
  '30230000-0',
  '30231300-0',
  '30232110-8',
  '32400000-7',
  '32420000-3',
  '48800000-6',
  '48820000-2',
  '50312000-5',
  '50312300-8',
  '72700000-7',
  '48730000-4',
  '48732000-8',
  '72212730-5',
  '72810000-1',
  '72500000-0',
  '72510000-3',
  '72590000-7',
  '72910000-2',
  '38221000-0',
  '71354100-5',
  '72314000-9',
  '48400000-2',
  '48440000-4',
  '48450000-7',
  '72212440-5',
  '72212450-8',
  '72212460-1',
  '72212461-8',
  '72212463-2',
  '72212481-3',
  '79999100-4',
  '72311100-9',
  '92512000-3',
  '48190000-6',
  '72212190-7',
  '80533100-0',
  '80420000-4',
  '72220000-3',
  '72221000-0',
  '72222000-7',
  '72224000-1',
  '72246000-1',
]

const CPV_DESCRIPTIONS: Record<string, string> = {
  '72000000-5': 'IT services: consulting, software development, Internet and support.',
  '72200000-7': 'Software programming and consultancy services.',
  '72210000-0': 'Programming services of packaged software products.',
  '72211000-7': 'Programming services of systems and user software.',
  '72212000-4': 'Programming services of application software. Core custom application development.',
  '72212100-0': 'Industry specific software development services. Domain-specific custom software.',
  '72250000-2': 'System and support services. Operational support around information systems.',
  '72253000-3': 'Helpdesk and support services. User support and service desk work.',
  '72261000-2': 'Software support services. Support for existing software products or applications.',
  '72262000-9': 'Software development services. Broad custom development CPV.',
  '72263000-6': 'Software implementation services. Implementation, setup and rollout.',
  '72268000-1': 'Software supply services. Supply or delivery of software services/products.',
  '72420000-0': 'Internet development services. Web and internet applications.',
  '72421000-7': 'Internet or intranet client application development services.',
  '72413000-8': 'World wide web site design services. Websites, portals and redesign work.',
  '72415000-2': 'World wide web site operation host services. Hosting/operation for websites.',
  '72416000-9': 'Application service providers. Hosted applications or managed app services.',
  '72316000-3': 'Data analysis services. Reporting, analytics and KPI/data work.',
  '72320000-4': 'Database services. Database operation, management or related services.',
  '72212482-0': 'Business intelligence software development services. BI dashboards and reporting apps.',
  '48311100-2': 'Document management system. DMS/ECM and document workflow systems.',
  '72212311-2': 'Document management software development services. Custom DMS/workflow development.',
  '72267100-0': 'Maintenance of information technology software. Software maintenance/support.',
  '30200000-1': 'Computer equipment and supplies. Broad hardware procurement category.',
  '30210000-4': 'Data-processing machines. Computers and data-processing hardware.',
  '30213000-5': 'Personal computers. Desktop/laptop workstation procurements.',
  '30213100-6': 'Portable computers. Laptop/notebook procurements.',
  '30213300-8': 'Desktop computer. Desktop PC procurements.',
  '30230000-0': 'Computer-related equipment. Peripherals and related equipment.',
  '30231300-0': 'Display screens. Monitors and display procurements.',
  '30232110-8': 'Laser printers. Printer procurements.',
  '32400000-7': 'Networks. Broad networking equipment/services category.',
  '32420000-3': 'Network equipment. Routers, switches and related network hardware.',
  '48800000-6': 'Information systems and servers. Systems/server procurements.',
  '48820000-2': 'Servers. Server hardware procurements.',
  '50312000-5': 'Maintenance and repair of computer equipment. Hardware maintenance.',
  '50312300-8': 'Maintenance and repair of data network equipment. Network equipment support.',
  '72700000-7': 'Computer network services. Network services, operation and support.',
  '48730000-4': 'Security software package. Ready-made cybersecurity software.',
  '48732000-8': 'Data security software package. Security tooling for data protection.',
  '72212730-5': 'Security software development services. Custom cybersecurity tooling.',
  '72810000-1': 'Computer audit services. IT audit, controls and compliance checks.',
  '72500000-0': 'Computer-related services. Managed or professional IT services.',
  '72510000-3': 'Computer-related management services. Management of IT operations or systems.',
  '72590000-7': 'Computer-related professional services. Specialist IT professional services.',
  '72910000-2': 'Computer back-up services. Backup, restore and continuity services.',
  '38221000-0': 'Geographic information systems. GIS platforms and related systems.',
  '71354100-5': 'Digital mapping services. Mapping, geospatial production and map updates.',
  '72314000-9': 'Data collection and collation services. Structured data gathering work.',
  '48400000-2': 'Business transaction and personal business software package. ERP/CRM-style systems.',
  '48440000-4': 'Financial analysis and accounting software package. Accounting/finance systems.',
  '48450000-7': 'Time accounting or human resources software package. HR/time management systems.',
  '72212440-5': 'Financial analysis and accounting software development services.',
  '72212450-8': 'Time accounting or human resources software development services.',
  '72212460-1': 'Analytical, scientific, mathematical or forecasting software development services.',
  '72212461-8': 'Analytical or scientific software development services.',
  '72212463-2': 'Statistical software development services.',
  '72212481-3': 'Sales, marketing and business intelligence software development services.',
  '79999100-4': 'Scanning services. Digitisation and scan-to-file work.',
  '72311100-9': 'Data conversion services. Migration, transformation and conversion work.',
  '92512000-3': 'Archive services. Archiving and records-related services.',
  '48190000-6': 'Educational software package. Learning or training software.',
  '72212190-7': 'Educational software development services. Custom e-learning platforms.',
  '80533100-0': 'Computer training services. IT training and user enablement.',
  '80420000-4': 'E-learning services. Online training services and learning delivery.',
  '72220000-3': 'Systems and technical consultancy services.',
  '72221000-0': 'Business analysis consultancy services.',
  '72222000-7': 'Information systems or technology strategic review and planning services.',
  '72224000-1': 'Project management consultancy services.',
  '72246000-1': 'Systems consultancy services.',
}

type CpvCategory = {
  id: string
  label: string
  description: string
  codes: string[]
  defaultOpen?: boolean
  advanced?: boolean
}

const CPV_CATEGORIES: CpvCategory[] = [
  {
    id: 'software',
    label: 'Software',
    description: 'Custom development, implementation and support',
    defaultOpen: true,
    codes: [
      '72000000-5',
      '72212000-4',
      '72212100-0',
      '72262000-9',
      '72263000-6',
      '72250000-2',
      '72253000-3',
      '72261000-2',
      '72268000-1',
      '72267100-0',
    ],
  },
  {
    id: 'web',
    label: 'Web / Internet',
    description: 'Portals, websites, intranet and hosting',
    defaultOpen: true,
    codes: ['72413000-8', '72420000-0', '72421000-7', '72415000-2', '72416000-9'],
  },
  {
    id: 'data',
    label: 'Data / BI',
    description: 'Analytics, reporting, BI and database work',
    codes: ['72316000-3', '72320000-4', '72212482-0'],
  },
  {
    id: 'workflow',
    label: 'Documents / Workflow',
    description: 'Document management and case/workflow systems',
    codes: ['48311100-2', '72212311-2'],
  },
  {
    id: 'hardware',
    label: 'Computers / Hardware',
    description: 'PCs, laptops, monitors, printers and peripherals',
    codes: ['30200000-1', '30210000-4', '30213000-5', '30213100-6', '30213300-8', '30230000-0', '30231300-0', '30232110-8'],
  },
  {
    id: 'infrastructure',
    label: 'Networks / Servers / Support',
    description: 'Servers, network equipment and maintenance services',
    codes: ['32400000-7', '32420000-3', '48800000-6', '48820000-2', '50312000-5', '50312300-8', '72700000-7'],
  },
  {
    id: 'security',
    label: 'Cybersecurity',
    description: 'Security software, data protection, audit and controls',
    advanced: true,
    codes: ['48730000-4', '48732000-8', '72212730-5', '72810000-1'],
  },
  {
    id: 'managed-it',
    label: 'Cloud / Managed IT',
    description: 'Managed services, IT operations, professional services and backup',
    advanced: true,
    codes: ['72500000-0', '72510000-3', '72590000-7', '72910000-2'],
  },
  {
    id: 'gis',
    label: 'GIS / Maps',
    description: 'Geospatial systems, digital mapping and field data collection',
    advanced: true,
    codes: ['38221000-0', '71354100-5', '72314000-9'],
  },
  {
    id: 'business-systems',
    label: 'ERP / CRM / HR',
    description: 'Business systems, accounting, HR and custom enterprise modules',
    advanced: true,
    codes: ['48400000-2', '48440000-4', '48450000-7', '72212440-5', '72212450-8'],
  },
  {
    id: 'ai-analytics',
    label: 'AI / Advanced analytics',
    description: 'Analytical, statistical, forecasting and business intelligence systems',
    advanced: true,
    codes: ['72212460-1', '72212461-8', '72212463-2', '72212481-3'],
  },
  {
    id: 'digitisation',
    label: 'Digitisation / Archives',
    description: 'Scanning, data conversion and archive-related work',
    advanced: true,
    codes: ['79999100-4', '72311100-9', '92512000-3'],
  },
  {
    id: 'learning',
    label: 'E-learning / Training',
    description: 'Educational software, e-learning services and computer training',
    advanced: true,
    codes: ['48190000-6', '72212190-7', '80533100-0', '80420000-4'],
  },
  {
    id: 'consulting',
    label: 'IT consulting',
    description: 'Business analysis, technical consultancy, strategy and project management',
    advanced: true,
    codes: ['72220000-3', '72221000-0', '72222000-7', '72224000-1', '72246000-1'],
  },
]

const FALLBACK_KEYWORDS = [
  'ανάπτυξη εφαρμογής',
  'ανάπτυξη λογισμικού',
  'dashboard',
  'workflow',
  'portal',
  'CMS',
]

const fallbackAiModels: AIModelOption[] = [
  { id: 'gpt-4.1-mini', label: 'GPT-4.1 mini', description: 'Γρήγορο και οικονομικό.', quality: 'Fast', recommended: false },
  { id: 'gpt-5.6-terra', label: 'GPT-5.6 Terra', description: 'Ισορροπία ποιότητας και κόστους.', quality: 'Balanced', recommended: true },
  { id: 'gpt-5.5', label: 'GPT-5.5', description: 'Βαθύτερη επαγγελματική ανάλυση.', quality: 'Deep', recommended: false },
  { id: 'gpt-5.6', label: 'GPT-5.6 Sol', description: 'Μέγιστη ποιότητα ανάλυσης.', quality: 'Best', recommended: false },
]

function App() {
  const [activeView, setActiveView] = useState<'opportunities' | 'market'>('opportunities')
  const [config, setConfig] = useState<ConfigResponse | null>(null)
  const [selectedAiModel, setSelectedAiModel] = useState(() => window.localStorage.getItem('opportunity-ai-model') || 'gpt-4.1-mini')
  const [query, setQuery] = useState('')
  const [budgetMin, setBudgetMin] = useState(5000)
  const [budgetMax, setBudgetMax] = useState(100000)
  const [dateFrom, setDateFrom] = useState(() => toDateInput(addDays(new Date(), -180)))
  const [dateTo, setDateTo] = useState(() => toDateInput(new Date()))
  const [onlyOpen, setOnlyOpen] = useState(true)
  const [showAllFetched, setShowAllFetched] = useState(false)
  const [selectedCpvs, setSelectedCpvs] = useState<string[]>(FALLBACK_CPV.slice(0, 8))
  const [expandedCpvGroups, setExpandedCpvGroups] = useState<Record<string, boolean>>(() =>
    Object.fromEntries(CPV_CATEGORIES.map((category) => [category.id, Boolean(category.defaultOpen)])),
  )
  const [keywords, setKeywords] = useState(FALLBACK_KEYWORDS.join(', '))
  const [sources, setSources] = useState<SourceName[]>(DASHBOARD_SOURCES)
  const [loading, setLoading] = useState(true)
  const [response, setResponse] = useState<SearchResponse | null>(null)
  const [activity, setActivity] = useState<ActivityResponse | null>(null)
  const [activityLoading, setActivityLoading] = useState(true)
  const [activityError, setActivityError] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [detailsOpportunity, setDetailsOpportunity] = useState<Opportunity | null>(null)
  const [details, setDetails] = useState<OpportunityDetails | null>(null)
  const [detailsLoading, setDetailsLoading] = useState(false)
  const [detailsError, setDetailsError] = useState<string | null>(null)
  const [documentBrief, setDocumentBrief] = useState<DocumentBrief | null>(null)
  const [documentBriefOutdated, setDocumentBriefOutdated] = useState(false)
  const [documentBriefLoading, setDocumentBriefLoading] = useState(false)
  const [documentBriefGenerating, setDocumentBriefGenerating] = useState(false)
  const [documentBriefError, setDocumentBriefError] = useState<string | null>(null)
  const [buyerIntelligence, setBuyerIntelligence] = useState<BuyerIntelligenceResponse | null>(null)
  const [buyerIntelligenceLoading, setBuyerIntelligenceLoading] = useState(false)
  const [buyerIntelligenceError, setBuyerIntelligenceError] = useState<string | null>(null)
  const [bookmarks, setBookmarks] = useState<BookmarkRecord[]>([])
  const [bookmarkError, setBookmarkError] = useState<string | null>(null)
  const [guidanceByOpportunityId, setGuidanceByOpportunityId] = useState<Record<string, OpportunityGuidance>>({})
  const [patterns, setPatterns] = useState<NeedPattern[]>([])
  const [patternsLoading, setPatternsLoading] = useState(false)
  const [patternsError, setPatternsError] = useState<string | null>(null)
  const [selectedBuyer, setSelectedBuyer] = useState('all')
  const [moreCpvsOpen, setMoreCpvsOpen] = useState(false)

  const cpvOptions = config?.default_cpv_codes ?? FALLBACK_CPV
  const cpvGroups = useMemo(() => buildCpvGroups(cpvOptions), [cpvOptions])
  const primaryCpvGroups = useMemo(() => cpvGroups.filter((group) => !group.advanced), [cpvGroups])
  const moreCpvGroups = useMemo(() => cpvGroups.filter((group) => group.advanced), [cpvGroups])
  const moreCpvCodes = useMemo(() => new Set(moreCpvGroups.flatMap((group) => group.codes)), [moreCpvGroups])
  const moreSelectedCount = useMemo(() => selectedCpvs.filter((code) => moreCpvCodes.has(code)).length, [moreCpvCodes, selectedCpvs])
  const buyerOptions = useMemo(() => {
    const counts = new Map<string, number>()
    for (const opportunity of response?.opportunities ?? []) {
      const buyer = opportunity.buyer.trim() || 'Unknown buyer'
      counts.set(buyer, (counts.get(buyer) ?? 0) + 1)
    }
    return Array.from(counts.entries())
      .map(([buyer, count]) => ({ buyer, count }))
      .sort((a, b) => b.count - a.count || a.buyer.localeCompare(b.buyer))
  }, [response])
  const filteredOpportunities = useMemo(() => {
    const opportunities = response?.opportunities ?? []
    if (selectedBuyer === 'all') {
      return opportunities
    }
    return opportunities.filter((opportunity) => opportunity.buyer === selectedBuyer)
  }, [response, selectedBuyer])
  const filteredStats = useMemo(() => opportunityStats(filteredOpportunities), [filteredOpportunities])
  const packageRows = useMemo(() => {
    const packages = filteredStats.by_package
    return Object.entries(packages)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 5)
  }, [filteredStats])
  const bookmarkedIds = useMemo(() => new Set(bookmarks.map((bookmark) => bookmark.id)), [bookmarks])

  const migrateLegacyShortlist = useCallback(async (opportunities: Opportunity[]) => {
    let legacyIds: string[]
    try {
      const rawLegacy = localStorage.getItem('opportunity-shortlist')
      legacyIds = rawLegacy ? JSON.parse(rawLegacy) : []
    } catch {
      legacyIds = []
    }
    if (!legacyIds.length) {
      return
    }

    const legacySet = new Set(legacyIds)
    const matches = opportunities.filter((opportunity) => legacySet.has(opportunity.id))
    if (!matches.length) {
      return
    }

    let latestBookmarks: BookmarkListResponse | null = null
    for (const opportunity of matches) {
      const res = await fetch(`${API_BASE}/api/bookmarks`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ opportunity }),
      })
      if (!res.ok) {
        throw new Error(`Bookmarks API returned ${res.status}`)
      }
      latestBookmarks = (await res.json()) as BookmarkListResponse
    }
    if (latestBookmarks) {
      setBookmarks(latestBookmarks.bookmarks)
    }

    const migratedIds = new Set(matches.map((opportunity) => opportunity.id))
    const remainingIds = legacyIds.filter((id) => !migratedIds.has(id))
    if (remainingIds.length) {
      localStorage.setItem('opportunity-shortlist', JSON.stringify(remainingIds))
    } else {
      localStorage.removeItem('opportunity-shortlist')
    }
  }, [])

  const loadPatterns = useCallback(async (opportunities: Opportunity[]) => {
    setPatternsLoading(true)
    setPatternsError(null)
    try {
      const res = await fetch(`${API_BASE}/api/patterns/discover`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          opportunities,
          min_opportunities: 2,
          max_patterns: 8,
        }),
      })
      if (!res.ok) {
        throw new Error(`Patterns API returned ${res.status}`)
      }
      const data = (await res.json()) as NeedPatternResponse
      setPatterns(data.patterns)
    } catch (exc) {
      setPatterns([])
      setPatternsError(exc instanceof Error ? exc.message : 'Patterns discovery failed')
    } finally {
      setPatternsLoading(false)
    }
  }, [])

  const runSearch = useCallback(async (overrides?: { onlyOpen?: boolean; showAllFetched?: boolean }) => {
    setLoading(true)
    setError(null)
    setPatterns([])
    setPatternsError(null)
    setSelectedBuyer('all')
    const requestOnlyOpen = overrides?.onlyOpen ?? onlyOpen
    const requestShowAllFetched = overrides?.showAllFetched ?? showAllFetched
    try {
      const res = await fetch(`${API_BASE}/api/opportunities/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query,
          keywords: keywords
            .split(',')
            .map((keyword) => keyword.trim())
            .filter(Boolean),
          cpv_codes: selectedCpvs,
          budget_min: budgetMin,
          budget_max: budgetMax,
          date_from: dateFrom,
          date_to: dateTo,
          deadline_after: toDateInput(new Date()),
          only_open: requestOnlyOpen,
          show_all_fetched: requestShowAllFetched,
          sources,
          include_demo_when_empty: false,
          limit: 100,
        }),
      })
      if (!res.ok) {
        throw new Error(`API returned ${res.status}`)
      }
      const data = (await res.json()) as SearchResponse
      setResponse(data)
      await migrateLegacyShortlist(data.opportunities)
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : 'Search failed')
    } finally {
      setLoading(false)
    }
  }, [budgetMax, budgetMin, dateFrom, dateTo, keywords, migrateLegacyShortlist, onlyOpen, query, selectedCpvs, showAllFetched, sources])

  const runActivity = useCallback(async () => {
    setActivityLoading(true)
    setActivityError(null)
    try {
      const res = await fetch(`${API_BASE}/api/opportunities/activity`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sources: sources.filter((source) => source !== 'demo'),
          cpv_codes: selectedCpvs,
          days: daysElapsedInYear(new Date()),
          limit: 1000,
        }),
      })
      if (!res.ok) {
        throw new Error(`Activity API returned ${res.status}`)
      }
      setActivity((await res.json()) as ActivityResponse)
    } catch (exc) {
      setActivityError(exc instanceof Error ? exc.message : 'Activity fetch failed')
      setActivity(null)
    } finally {
      setActivityLoading(false)
    }
  }, [selectedCpvs, sources])

  const loadBookmarks = useCallback(async () => {
    setBookmarkError(null)
    try {
      const res = await fetch(`${API_BASE}/api/bookmarks`)
      if (!res.ok) {
        throw new Error(`Bookmarks API returned ${res.status}`)
      }
      const data = (await res.json()) as BookmarkListResponse
      setBookmarks(data.bookmarks)
    } catch (exc) {
      setBookmarkError(exc instanceof Error ? exc.message : 'Bookmarks fetch failed')
    }
  }, [])

  const loadCachedBrief = useCallback(async (opportunity: Opportunity) => {
    if (!opportunity.source_reference) {
      setDocumentBrief(null)
      setDocumentBriefOutdated(false)
      return
    }
    setDocumentBriefLoading(true)
    setDocumentBriefError(null)
    try {
      const res = await fetch(
        `${API_BASE}/api/opportunities/${opportunity.source}/${encodeURIComponent(opportunity.source_reference)}/brief`,
      )
      if (!res.ok) {
        throw new Error(`AI brief API returned ${res.status}`)
      }
      const data = (await res.json()) as DocumentBriefResponse
      setDocumentBrief(data.brief ?? null)
      setDocumentBriefOutdated(data.outdated)
    } catch (exc) {
      setDocumentBrief(null)
      setDocumentBriefOutdated(false)
      setDocumentBriefError(exc instanceof Error ? exc.message : 'AI brief fetch failed')
    } finally {
      setDocumentBriefLoading(false)
    }
  }, [])

  const loadBuyerIntelligence = useCallback(async (opportunity: Opportunity, marketOpportunities: Opportunity[]) => {
    setBuyerIntelligenceLoading(true)
    setBuyerIntelligenceError(null)
    try {
      const res = await fetch(`${API_BASE}/api/buyers/intelligence`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          buyer: opportunity.buyer,
          opportunity,
          market_opportunities: marketOpportunities,
          diavgeia_limit: 8,
          history_days: 720,
          history_limit: 40,
        }),
      })
      if (!res.ok) {
        throw new Error(`Buyer intelligence API returned ${res.status}`)
      }
      setBuyerIntelligence((await res.json()) as BuyerIntelligenceResponse)
    } catch (exc) {
      setBuyerIntelligence(null)
      setBuyerIntelligenceError(exc instanceof Error ? exc.message : 'Buyer intelligence fetch failed')
    } finally {
      setBuyerIntelligenceLoading(false)
    }
  }, [])

  useEffect(() => {
    async function boot() {
      try {
        const configRes = await fetch(`${API_BASE}/api/config`)
        if (configRes.ok) {
          const nextConfig = (await configRes.json()) as ConfigResponse
          setConfig(nextConfig)
          const savedModel = window.localStorage.getItem('opportunity-ai-model')
          const resolvedModel = savedModel && nextConfig.ai_models.some((model) => model.id === savedModel)
            ? savedModel
            : nextConfig.default_ai_model
          setSelectedAiModel(resolvedModel)
          setSelectedCpvs(nextConfig.default_cpv_codes.slice(0, 8))
          setKeywords(nextConfig.default_keywords.slice(0, 10).join(', '))
        }
      } catch {
        setConfig(null)
      }
      await loadBookmarks()
      await runSearch()
    }
    void boot()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    const activityTimer = window.setTimeout(() => {
      void runActivity()
    }, 0)
    return () => window.clearTimeout(activityTimer)
  }, [runActivity])

  useEffect(() => {
    if (!response) {
      return
    }
    // The request is intentionally synchronized with the currently visible result set.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void loadPatterns(filteredOpportunities)
  }, [filteredOpportunities, loadPatterns, response])

  const onSubmit = (event: FormEvent) => {
    event.preventDefault()
    void runSearch()
  }

  const toggleShowAllFetched = () => {
    const nextShowAll = !showAllFetched
    setShowAllFetched(nextShowAll)
    setOnlyOpen(!nextShowAll)
    void runSearch({ onlyOpen: !nextShowAll, showAllFetched: nextShowAll })
  }

  const openDetails = async (opportunity: Opportunity) => {
    setDocumentBrief(null)
    setDocumentBriefOutdated(false)
    setDocumentBriefError(null)
    setDocumentBriefLoading(false)
    setDocumentBriefGenerating(false)
    setBuyerIntelligence(null)
    setBuyerIntelligenceError(null)
    setBuyerIntelligenceLoading(false)

    if (!opportunity.source_reference) {
      setDetailsOpportunity(opportunity)
      setDetails(null)
      setDetailsError('Δεν υπάρχει reference από την πηγή για live details.')
      return
    }

    setDetailsOpportunity(opportunity)
    setDetails(null)
    setDetailsError(null)
    setDetailsLoading(true)
    try {
      const res = await fetch(
        `${API_BASE}/api/opportunities/${opportunity.source}/${encodeURIComponent(opportunity.source_reference)}/details`,
      )
      if (!res.ok) {
        throw new Error(`Details API returned ${res.status}`)
      }
      const nextDetails = (await res.json()) as OpportunityDetails
      setDetails(nextDetails)
      if (nextDetails.guidance) {
        const nextGuidance = nextDetails.guidance
        setGuidanceByOpportunityId((current) => ({
          ...current,
          [opportunity.id]: nextGuidance,
        }))
      }
      const intelligenceOpportunity = enrichOpportunityFromDetails(opportunity, nextDetails)
      void loadCachedBrief(opportunity)
      void loadBuyerIntelligence(intelligenceOpportunity, response?.opportunities ?? [])
    } catch (exc) {
      setDetailsError(exc instanceof Error ? exc.message : 'Details fetch failed')
    } finally {
      setDetailsLoading(false)
    }
  }

  const closeDetails = () => {
    setDetailsOpportunity(null)
    setDetails(null)
    setDetailsError(null)
    setDetailsLoading(false)
    setDocumentBrief(null)
    setDocumentBriefOutdated(false)
    setDocumentBriefError(null)
    setDocumentBriefLoading(false)
    setDocumentBriefGenerating(false)
    setBuyerIntelligence(null)
    setBuyerIntelligenceError(null)
    setBuyerIntelligenceLoading(false)
  }

  const toggleSource = (source: SourceName) => {
    setSources((current) => {
      if (current.includes(source)) {
        return current.length === 1 ? current : current.filter((item) => item !== source)
      }
      return [...current, source]
    })
  }

  const toggleCpv = (code: string) => {
    setSelectedCpvs((current) => (current.includes(code) ? current.filter((item) => item !== code) : [...current, code]))
  }

  const toggleCpvGroup = (groupId: string) => {
    setExpandedCpvGroups((current) => ({ ...current, [groupId]: !(current[groupId] ?? false) }))
  }

  const toggleCpvCategorySelection = (codes: string[]) => {
    setSelectedCpvs((current) => {
      const codeSet = new Set(codes)
      const allSelected = codes.every((code) => current.includes(code))

      if (allSelected) {
        return current.filter((code) => !codeSet.has(code))
      }

      return Array.from(new Set([...current, ...codes]))
    })
  }

  const toggleBookmark = async (opportunity: Opportunity) => {
    setBookmarkError(null)
    const pinned = bookmarkedIds.has(opportunity.id)
    try {
      const res = await fetch(`${API_BASE}/api/bookmarks${pinned ? `/${encodeURIComponent(opportunity.id)}` : ''}`, {
        method: pinned ? 'DELETE' : 'POST',
        headers: pinned ? undefined : { 'Content-Type': 'application/json' },
        body: pinned ? undefined : JSON.stringify({ opportunity }),
      })
      if (!res.ok) {
        throw new Error(`Bookmarks API returned ${res.status}`)
      }
      const data = (await res.json()) as BookmarkListResponse
      setBookmarks(data.bookmarks)
    } catch (exc) {
      setBookmarkError(exc instanceof Error ? exc.message : 'Bookmark update failed')
    }
  }

  const generateDocumentBrief = async (opportunity: Opportunity) => {
    if (!opportunity.source_reference) {
      setDocumentBriefError('No source reference available for this opportunity.')
      return
    }
    setDocumentBriefGenerating(true)
    setDocumentBriefError(null)
    try {
      const res = await fetch(
        `${API_BASE}/api/opportunities/${opportunity.source}/${encodeURIComponent(opportunity.source_reference)}/brief?regenerate=${documentBrief ? 'true' : 'false'}&model=${encodeURIComponent(selectedAiModel)}`,
        { method: 'POST' },
      )
      if (!res.ok) {
        throw new Error(`AI brief API returned ${res.status}`)
      }
      const data = (await res.json()) as DocumentBriefResponse
      if (data.brief) {
        setDocumentBrief(data.brief)
        setDocumentBriefOutdated(data.outdated)
        if (data.message) setDocumentBriefError(data.message)
      } else {
        setDocumentBriefError(data.message ?? 'No AI brief was generated.')
      }
    } catch (exc) {
      setDocumentBriefError(exc instanceof Error ? exc.message : 'AI brief generation failed')
    } finally {
      setDocumentBriefGenerating(false)
    }
  }

  const selectAiModel = (model: string) => {
    setSelectedAiModel(model)
    window.localStorage.setItem('opportunity-ai-model', model)
  }

  const shortlistItems = bookmarks.map((bookmark) => bookmark.opportunity)
  const renderCpvCategory = (group: CpvCategory) => {
    const expanded = expandedCpvGroups[group.id] ?? Boolean(group.defaultOpen)
    const selectedCount = group.codes.filter((code) => selectedCpvs.includes(code)).length

    return (
      <section className="cpv-category" key={group.id}>
        <div className="cpv-category-header">
          <button className="cpv-category-button" type="button" onClick={() => toggleCpvGroup(group.id)}>
            <span>
              <ChevronDown className={`cpv-chevron ${expanded ? 'expanded' : ''}`} size={16} aria-hidden="true" />
              {group.label}
            </span>
            <small>{selectedCount}/{group.codes.length}</small>
          </button>
          <button className="cpv-category-select" type="button" onClick={() => toggleCpvCategorySelection(group.codes)}>
            {selectedCount === group.codes.length ? 'Deselect' : 'Select all'}
          </button>
        </div>
        {expanded ? (
          <div className="cpv-category-body">
            <p>{group.description}</p>
            <div className="cpv-grid">
              {group.codes.map((code) => (
                <label className="cpv-chip" key={code}>
                  <input type="checkbox" checked={selectedCpvs.includes(code)} onChange={() => toggleCpv(code)} />
                  <span>{code}</span>
                  <button
                    type="button"
                    className="cpv-info"
                    aria-label={`CPV ${code}: ${cpvDescription(code)}`}
                    title={cpvDescription(code)}
                    onClick={(event) => {
                      event.preventDefault()
                      event.stopPropagation()
                    }}
                  >
                    <Info size={13} aria-hidden="true" />
                  </button>
                </label>
              ))}
            </div>
          </div>
        ) : null}
      </section>
    )
  }

  if (activeView === 'market') {
    return <MarketRadar onOpenOpportunities={() => setActiveView('opportunities')} />
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-block">
          <div className="brand-mark">
            <Target size={22} aria-hidden="true" />
          </div>
          <div>
            <p className="eyebrow">Opportunity Finder</p>
            <h1>Public software bids</h1>
          </div>
        </div>

        <form className="filter-form" onSubmit={onSubmit}>
          <div className="filter-scroll">
          <label className="field">
            <span>
              <Search size={16} aria-hidden="true" />
              Αναζήτηση
            </span>
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              maxLength={100}
              placeholder="Προαιρετική αναζήτηση"
            />
          </label>

          <div className="field-grid">
            <label className="field">
              <span>
                <CircleDollarSign size={16} aria-hidden="true" />
                Από
              </span>
              <input type="number" value={budgetMin} onChange={(event) => setBudgetMin(Number(event.target.value))} />
            </label>
            <label className="field">
              <span>
                <CircleDollarSign size={16} aria-hidden="true" />
                Έως
              </span>
              <input type="number" value={budgetMax} onChange={(event) => setBudgetMax(Number(event.target.value))} />
            </label>
          </div>

          <div className="filter-group">
            <div className="group-title">
              <CalendarClock size={16} aria-hidden="true" />
              Δημοσίευση
            </div>
            <div className="field-grid">
              <label className="field">
                <span>Από</span>
                <input type="date" value={dateFrom} max={dateTo} required onChange={(event) => setDateFrom(event.target.value)} />
              </label>
              <label className="field">
                <span>Έως</span>
                <input type="date" value={dateTo} min={dateFrom} required onChange={(event) => setDateTo(event.target.value)} />
              </label>
            </div>
            <label className={`open-toggle ${showAllFetched ? 'disabled' : ''}`}>
              <input
                type="checkbox"
                checked={onlyOpen}
                disabled={showAllFetched}
                onChange={(event) => setOnlyOpen(event.target.checked)}
              />
              <CalendarClock size={17} aria-hidden="true" />
              <span>Μόνο open opportunities</span>
            </label>
            <button className={`secondary-action ${showAllFetched ? 'active' : ''}`} type="button" onClick={toggleShowAllFetched} disabled={loading}>
              <Filter size={16} aria-hidden="true" />
              {showAllFetched ? 'Back to open filters' : 'Show all fetched'}
            </button>
            {showAllFetched ? (
              <p className="filter-note">Showing fetched records even when they are outside the date range or have no deadline.</p>
            ) : null}
          </div>

          <div className="filter-group">
            <div className="group-title">
              <Filter size={16} aria-hidden="true" />
              Πηγές
            </div>
            <div className="source-toggles">
              {DASHBOARD_SOURCES.map((source) => {
                const SourceIcon = SOURCE_META[source].icon
                return (
                  <label className="toggle-row" key={source}>
                    <input type="checkbox" checked={sources.includes(source)} onChange={() => toggleSource(source)} />
                    <SourceIcon size={16} aria-hidden="true" />
                    <span>{SOURCE_META[source].label}</span>
                  </label>
                )
              })}
            </div>
          </div>

          <div className="filter-group">
            <label className="field">
              <span>
                <Building2 size={16} aria-hidden="true" />
                Buyers
              </span>
              <select value={selectedBuyer} disabled={!buyerOptions.length || loading} onChange={(event) => setSelectedBuyer(event.target.value)}>
                <option value="all">All buyers ({response?.opportunities.length ?? 0})</option>
                {buyerOptions.map((option) => (
                  <option value={option.buyer} key={option.buyer}>
                    {option.buyer} ({option.count})
                  </option>
                ))}
              </select>
            </label>
          </div>

          <div className="filter-group">
            <div className="group-title">
              <Layers3 size={16} aria-hidden="true" />
              CPV focus
            </div>
            <div className="cpv-category-list">
              {primaryCpvGroups.map(renderCpvCategory)}
            </div>
            {moreCpvGroups.length ? (
              <>
                <button className="cpv-more-button" type="button" onClick={() => setMoreCpvsOpen(true)}>
                  More CPV categories
                  <span>{moreSelectedCount}/{moreCpvCodes.size}</span>
                </button>
                {moreCpvsOpen ? (
                  <div className="cpv-more-overlay" role="presentation" onMouseDown={() => setMoreCpvsOpen(false)}>
                    <div
                      className="cpv-more-dialog"
                      role="dialog"
                      aria-modal="true"
                      aria-labelledby="cpv-more-title"
                      onMouseDown={(event) => event.stopPropagation()}
                    >
                      <div className="cpv-more-header">
                        <div>
                          <h3 id="cpv-more-title">More CPV categories</h3>
                          <p>{moreSelectedCount} selected from {moreCpvCodes.size} extra codes</p>
                        </div>
                        <button className="icon-button" type="button" aria-label="Close CPV categories" onClick={() => setMoreCpvsOpen(false)}>
                          <X size={18} aria-hidden="true" />
                        </button>
                      </div>
                      <div className="cpv-more-list">{moreCpvGroups.map(renderCpvCategory)}</div>
                    </div>
                  </div>
                ) : null}
              </>
            ) : null}
          </div>

          </div>

          <div className="sidebar-actions">
            <button className="primary-action" type="submit" disabled={loading}>
            {loading ? <Loader2 className="spin" size={17} aria-hidden="true" /> : <RefreshCw size={17} aria-hidden="true" />}
            Search opportunities
            </button>
          </div>
        </form>
      </aside>

      <main className="workspace">
        <header className="topbar">
          <div>
            <p className="eyebrow">Greece-first procurement intelligence</p>
            <h2>Shortlist μικρών full-stack έργων</h2>
          </div>
          <div className="topbar-actions">
            <button className="market-nav-button" type="button" onClick={() => setActiveView('market')}>
              <Radar size={17} aria-hidden="true" />
              Market Radar
            </button>
            <StatusPill ok={!error} label={error ? 'API issue' : 'API live'} />
          </div>
        </header>

        {error ? (
          <section className="error-band">
            <AlertTriangle size={18} aria-hidden="true" />
            <span>{error}</span>
          </section>
        ) : null}

        <section className="metric-strip">
          <Metric icon={DatabaseZap} label="Results" value={loading ? '...' : String(filteredStats.total)} />
          <Metric icon={Target} label="Bid candidates" value={String(filteredStats.bid_candidates)} tone="green" />
          <Metric icon={Gauge} label="Average fit" value={`${filteredStats.average_score}/100`} tone="blue" />
          <Metric icon={CircleDollarSign} label="Tracked budget" value={formatCurrency(filteredStats.total_budget)} tone="amber" />
        </section>

        <section className="insight-layout">
          <SmartCalendarPanel activity={activity} loading={activityLoading} error={activityError} selectedSources={sources} />

          <PatternsPanel
            patterns={patterns}
            loading={patternsLoading}
            error={patternsError}
            opportunities={filteredOpportunities}
            onOpenOpportunity={(opportunity) => void openDetails(opportunity)}
          />

          <div className="source-panel">
            <div className="panel-heading">
              <Activity size={18} aria-hidden="true" />
              <h3>Source runs</h3>
            </div>
            <p className="panel-note">Fetched items are raw API results. Shown items are after date/open filters.</p>
            <div className="source-run-list">
              {(response?.source_runs ?? []).map((run) => (
                <div className="source-run" key={`${run.source}-${run.status}`}>
                  <div className={`run-dot ${run.status}`} />
                  <div>
                    <strong>{SOURCE_META[run.source].label}</strong>
                    <span>{run.items} fetched · {run.shown ?? 0} shown · {run.elapsed_ms}ms</span>
                  </div>
                  {run.error ? <AlertTriangle size={16} aria-label={run.error} /> : <CheckCircle2 size={16} aria-hidden="true" />}
                </div>
              ))}
            </div>
          </div>

          <div className="package-panel">
            <div className="panel-heading">
              <BarChart3 size={18} aria-hidden="true" />
              <h3>Package demand</h3>
            </div>
            <div className="package-bars">
              {packageRows.length ? (
                packageRows.map(([name, value]) => (
                  <div className="package-row" key={name}>
                    <span>{packageLabel(name)}</span>
                    <div className="bar-track">
                      <div className="bar-fill" style={{ width: `${Math.min(100, Math.max(12, value * 24))}%` }} />
                    </div>
                    <strong>{value}</strong>
                  </div>
                ))
              ) : (
                <p className="muted">No package data yet.</p>
              )}
            </div>
          </div>

          <div className="shortlist-panel">
            <div className="panel-heading">
              <BookmarkCheck size={18} aria-hidden="true" />
              <h3>Shortlist</h3>
            </div>
            <div className="shortlist-list">
              {bookmarkError ? (
                <p className="drawer-error-inline">{bookmarkError}</p>
              ) : null}
              {shortlistItems.length ? (
                shortlistItems.map((item) => (
                  <div className="shortlist-entry" key={item.id}>
                    <button className="shortlist-item" onClick={() => void openDetails(item)} type="button">
                      <span>{item.fit_score}</span>
                      {item.title}
                    </button>
                    <button className="shortlist-remove" onClick={() => void toggleBookmark(item)} type="button" aria-label="Remove from shortlist">
                      <X size={14} aria-hidden="true" />
                    </button>
                  </div>
                ))
              ) : (
                <p className="muted">Pin promising tenders as you scan.</p>
              )}
            </div>
          </div>
        </section>

        <section className="results-header">
          <div>
            <p className="eyebrow">Ranked opportunities</p>
            <h3>{loading ? 'Loading opportunities' : `${filteredOpportunities.length} matches`}</h3>
          </div>
          <div className="legend">
            <span><i className="legend-dot green" />80+</span>
            <span><i className="legend-dot blue" />60+</span>
            <span><i className="legend-dot amber" />40+</span>
          </div>
        </section>

        <section className="opportunity-list">
          {loading ? (
            <div className="loading-state">
              <Loader2 className="spin" size={24} aria-hidden="true" />
              <span>Fetching and scoring sources...</span>
            </div>
          ) : (
            filteredOpportunities.map((opportunity) => (
              <OpportunityRow
                key={opportunity.id}
                opportunity={opportunity}
                guidance={guidanceByOpportunityId[opportunity.id]}
                pinned={bookmarkedIds.has(opportunity.id)}
                onTogglePin={() => void toggleBookmark(opportunity)}
                onOpenDetails={() => void openDetails(opportunity)}
              />
            ))
          )}
        </section>
      </main>

      <DetailsDrawer
        opportunity={detailsOpportunity}
        details={details}
        loading={detailsLoading}
        error={detailsError}
        brief={documentBrief}
        briefOutdated={documentBriefOutdated}
        briefLoading={documentBriefLoading}
        briefGenerating={documentBriefGenerating}
        briefError={documentBriefError}
        buyerIntelligence={buyerIntelligence}
        buyerIntelligenceLoading={buyerIntelligenceLoading}
        buyerIntelligenceError={buyerIntelligenceError}
        aiModels={config?.ai_models ?? fallbackAiModels}
        selectedAiModel={selectedAiModel}
        softwareMatchAiEnabled={config?.software_match_ai_enabled ?? false}
        onSelectAiModel={selectAiModel}
        onGenerateBrief={() => detailsOpportunity ? void generateDocumentBrief(detailsOpportunity) : undefined}
        onClose={closeDetails}
      />
    </div>
  )
}

function MarketRadar({ onOpenOpportunities }: { onOpenOpportunities: () => void }) {
  const [config, setConfig] = useState<MarketConfig | null>(null)
  const [overview, setOverview] = useState<MarketOverview | null>(null)
  const [buyers, setBuyers] = useState<MarketOrganization[]>([])
  const [suppliers, setSuppliers] = useState<MarketOrganization[]>([])
  const [brands, setBrands] = useState<SoftwareBrand[]>([])
  const [signals, setSignals] = useState<MarketSignal[]>([])
  const [activeTab, setActiveTab] = useState<'buyers' | 'suppliers' | 'brands' | 'opportunities'>('buyers')
  const [category, setCategory] = useState('all')
  const [search, setSearch] = useState('')
  const [minScore, setMinScore] = useState(25)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [refreshStatus, setRefreshStatus] = useState<MarketRefresh | null>(null)
  const [selectedDetail, setSelectedDetail] = useState<MarketOrganizationDetail | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [profileName, setProfileName] = useState('Greek software demand')
  const [profileActivities, setProfileActivities] = useState('')
  const [profileMessage, setProfileMessage] = useState<string | null>(null)

  const loadMarket = useCallback(async () => {
    setLoading(true)
    setError(null)
    const categoryQuery = category === 'all' ? '' : `&category=${encodeURIComponent(category)}`
    const searchQuery = search.trim() ? `&search=${encodeURIComponent(search.trim())}` : ''
    try {
      const [configRes, overviewRes, buyersRes, suppliersRes, brandsRes, signalsRes, refreshRes] = await Promise.all([
        fetch(`${API_BASE}/api/market/config`),
        fetch(`${API_BASE}/api/market/overview?period_days=30`),
        fetch(`${API_BASE}/api/market/buyers?limit=100&min_score=${minScore}${categoryQuery}${searchQuery}`),
        fetch(`${API_BASE}/api/market/suppliers?limit=100${categoryQuery}${searchQuery}`),
        fetch(`${API_BASE}/api/market/brands?limit=100${search.trim() ? `&search=${encodeURIComponent(search.trim())}` : ''}`),
        fetch(`${API_BASE}/api/market/signals?limit=100&min_score=${minScore}${categoryQuery}`),
        fetch(`${API_BASE}/api/market/refresh/status`),
      ])
      const responses = [configRes, overviewRes, buyersRes, suppliersRes, brandsRes, signalsRes]
      if (responses.some((response) => !response.ok)) {
        throw new Error(`Market API returned ${responses.find((response) => !response.ok)?.status ?? 'an error'}`)
      }
      const [configData, overviewData, buyersData, suppliersData, brandsData, signalsData] = await Promise.all(responses.map((response) => response.json()))
      setConfig(configData as MarketConfig)
      setOverview(overviewData as MarketOverview)
      setBuyers((buyersData as { items: MarketOrganization[] }).items)
      setSuppliers((suppliersData as { items: MarketOrganization[] }).items)
      setBrands((brandsData as { items: SoftwareBrand[] }).items)
      setSignals((signalsData as { items: MarketSignal[] }).items)
      setRefreshStatus(refreshRes.ok ? (await refreshRes.json()) as MarketRefresh | null : null)
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : 'Market radar failed to load')
    } finally {
      setLoading(false)
    }
  }, [category, minScore, search])

  useEffect(() => {
    // Fetching is the external synchronization performed by this effect.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void loadMarket()
  }, [loadMarket])

  const runRefresh = async () => {
    setRefreshing(true)
    setError(null)
    try {
      const res = await fetch(`${API_BASE}/api/market/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      })
      if (!res.ok) throw new Error(`Refresh API returned ${res.status}`)
      setRefreshStatus((await res.json()) as MarketRefresh)
      await loadMarket()
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : 'Market refresh failed')
    } finally {
      setRefreshing(false)
    }
  }

  const openOrganization = async (organization: MarketOrganization) => {
    setDetailLoading(true)
    setSelectedDetail(null)
    try {
      const route = organization.role === 'supplier' ? 'suppliers' : 'buyers'
      const res = await fetch(`${API_BASE}/api/market/${route}/${encodeURIComponent(organization.id)}`)
      if (!res.ok) throw new Error(`Organization details returned ${res.status}`)
      setSelectedDetail((await res.json()) as MarketOrganizationDetail)
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : 'Organization details failed')
    } finally {
      setDetailLoading(false)
    }
  }

  const createDiscoveryProfile = async (event: FormEvent) => {
    event.preventDefault()
    setProfileMessage(null)
    const activities = profileActivities.split(',').map((item) => item.trim()).filter(Boolean)
    if (!activities.length) {
      setProfileMessage('Πρόσθεσε τουλάχιστον έναν ΚΑΔ.')
      return
    }
    try {
      const res = await fetch(`${API_BASE}/api/market/discovery-profiles`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: profileName, activities, prefectures: [], municipalities: [], is_active: true, enabled: true }),
      })
      if (!res.ok) throw new Error(`Discovery profile returned ${res.status}`)
      setProfileMessage('Το discovery profile αποθηκεύτηκε.')
      setProfileActivities('')
    } catch (exc) {
      setProfileMessage(exc instanceof Error ? exc.message : 'Profile save failed')
    }
  }

  const activeOrganizations = activeTab === 'suppliers' ? suppliers : buyers
  const visibleSignals = activeTab === 'opportunities' ? signals.filter((signal) => signal.stage === 'open' || signal.stage === 'early') : signals

  return (
    <div className="market-shell">
      <aside className="market-sidebar">
        <div className="brand-block market-brand-block">
          <div className="brand-mark"><Radar size={22} aria-hidden="true" /></div>
          <div><p className="eyebrow">Opportunity Finder</p><h1>Market Radar</h1></div>
        </div>

        <button className="secondary-action market-back-button" type="button" onClick={onOpenOpportunities}>
          <Target size={16} aria-hidden="true" /> Δημόσιες ευκαιρίες
        </button>

        <div className="market-filter-stack">
          <label className="field">
            <span><Search size={16} aria-hidden="true" /> Αναζήτηση οργανισμού</span>
            <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Buyer, integrator ή brand" />
          </label>
          <label className="field">
            <span><Tags size={16} aria-hidden="true" /> Κατηγορία ανάγκης</span>
            <select value={category} onChange={(event) => setCategory(event.target.value)}>
              <option value="all">Όλες οι κατηγορίες</option>
              {(config?.categories ?? []).map((item) => <option value={item} key={item}>{item}</option>)}
            </select>
          </label>
          <label className="field">
            <span><Gauge size={16} aria-hidden="true" /> Ελάχιστο need score: {minScore}</span>
            <input type="range" min="0" max="100" step="5" value={minScore} onChange={(event) => setMinScore(Number(event.target.value))} />
          </label>
        </div>

        <div className="market-source-coverage">
          <h3>Κάλυψη δεδομένων</h3>
          {Object.entries(overview?.coverage ?? {}).map(([source, status]) => (
            <div key={source}><span>{source}</span><strong>{status}</strong></div>
          ))}
        </div>

        <form className="market-discovery-form" onSubmit={createDiscoveryProfile}>
          <h3>ΓΕΜΗ discovery</h3>
          <p>{config?.gemi_enabled ? 'API ενεργό' : 'Αναμένει GEMI_API_KEY'}</p>
          <input value={profileName} onChange={(event) => setProfileName(event.target.value)} placeholder="Όνομα profile" />
          <textarea value={profileActivities} onChange={(event) => setProfileActivities(event.target.value)} placeholder="ΚΑΔ χωρισμένοι με κόμμα" rows={3} />
          <button className="secondary-action" type="submit" disabled={!config?.gemi_enabled}><Plus size={15} /> Αποθήκευση profile</button>
          {profileMessage ? <small>{profileMessage}</small> : null}
        </form>
      </aside>

      <main className="market-workspace">
        <header className="market-topbar">
          <div><p className="eyebrow">Buyer-need intelligence · Ελλάδα</p><h2>Πού κινείται η αγορά software</h2></div>
          <div className="market-refresh-actions">
            <span>{overview?.last_refresh_at ? `Τελευταίο refresh ${formatDateTime(overview.last_refresh_at)}` : 'Δεν έχει γίνει refresh'}</span>
            <button className="primary-action market-refresh-button" type="button" onClick={() => void runRefresh()} disabled={refreshing}>
              {refreshing ? <Loader2 className="spin" size={16} /> : <RefreshCw size={16} />} Refresh now
            </button>
          </div>
        </header>

        {error ? <section className="error-band"><AlertTriangle size={18} /><span>{error}</span></section> : null}

        <section className="market-metric-grid">
          <MarketMetric icon={Sparkles} label="Νέα signals" value={overview?.new_signals ?? 0} detail="Από το τελευταίο 24ωρο" tone="pink" />
          <MarketMetric icon={Users} label="Hot buyers" value={overview?.hot_buyers ?? 0} detail="Need score 75+" tone="green" />
          <MarketMetric icon={Target} label="Open opportunities" value={overview?.open_opportunities ?? 0} detail="Planning ή ενεργή αγορά" tone="blue" />
          <MarketMetric icon={CircleDollarSign} label="Observed public spend" value={formatCurrency(overview?.observed_public_spend ?? 0)} detail="Τεκμηριωμένες αναθέσεις" tone="amber" />
        </section>

        <section className="market-trends-panel">
          <div className="panel-heading"><TrendingUp size={18} /><h3>Τάσεις 30 ημερών</h3></div>
          <div className="market-trend-grid">
            {(overview?.categories ?? []).filter((item) => item.current_count || item.previous_count).map((item) => (
              <div className="market-trend-card" key={item.category}>
                <span>{item.category}</span><strong>{item.current_count}</strong>
                <small className={(item.delta_percent ?? 0) >= 0 ? 'positive' : 'negative'}>
                  {item.delta_percent === null || item.delta_percent === undefined ? 'Νέα ένδειξη' : `${item.delta_percent > 0 ? '+' : ''}${item.delta_percent}%`} vs προηγούμενες 30 ημέρες
                </small>
                <div className="trend-track"><i style={{ width: `${Math.min(100, Math.max(8, item.current_count * 12))}%` }} /></div>
              </div>
            ))}
            {!overview?.categories.some((item) => item.current_count || item.previous_count) ? <p className="muted">Οι τάσεις θα εμφανιστούν μόλις ολοκληρωθεί το πρώτο refresh.</p> : null}
          </div>
        </section>

        <nav className="market-tabs" aria-label="Market views">
          <button className={activeTab === 'buyers' ? 'active' : ''} onClick={() => setActiveTab('buyers')}><Users size={16} /> Αγοραστές <span>{buyers.length}</span></button>
          <button className={activeTab === 'suppliers' ? 'active' : ''} onClick={() => setActiveTab('suppliers')}><Handshake size={16} /> Ανάδοχοι <span>{suppliers.length}</span></button>
          <button className={activeTab === 'brands' ? 'active' : ''} onClick={() => setActiveTab('brands')}><Tags size={16} /> Software Brands <span>{brands.filter((item) => item.mention_count).length}</span></button>
          <button className={activeTab === 'opportunities' ? 'active' : ''} onClick={() => setActiveTab('opportunities')}><Target size={16} /> Ευκαιρίες <span>{signals.filter((item) => item.stage === 'open' || item.stage === 'early').length}</span></button>
        </nav>

        {loading ? <div className="loading-state"><Loader2 className="spin" size={24} /><span>Building market map...</span></div> : null}

        {!loading && (activeTab === 'buyers' || activeTab === 'suppliers') ? (
          <MarketOrganizationTable organizations={activeOrganizations} mode={activeTab} onOpen={(organization) => void openOrganization(organization)} />
        ) : null}

        {!loading && activeTab === 'brands' ? <BrandMarketGrid brands={brands} /> : null}

        {!loading && activeTab === 'opportunities' ? <MarketSignalList signals={visibleSignals} onOpenOrganization={(id) => {
          const organization = buyers.find((item) => item.id === id)
          if (organization) void openOrganization(organization)
        }} /> : null}

        {refreshStatus ? <RefreshRunSummary refresh={refreshStatus} /> : null}
      </main>

      {detailLoading ? <div className="market-detail-loading"><Loader2 className="spin" size={24} /></div> : null}
      <MarketOrganizationDrawer detail={selectedDetail} onClose={() => setSelectedDetail(null)} onChanged={async () => {
        if (selectedDetail) await openOrganization(selectedDetail.organization)
        await loadMarket()
      }} />
    </div>
  )
}

function MarketMetric({ icon: Icon, label, value, detail, tone }: { icon: LucideIcon; label: string; value: string | number; detail: string; tone: string }) {
  return <div className={`market-metric ${tone}`}><span><Icon size={18} /></span><div><small>{label}</small><strong>{value}</strong><p>{detail}</p></div></div>
}

function MarketOrganizationTable({ organizations, mode, onOpen }: { organizations: MarketOrganization[]; mode: 'buyers' | 'suppliers'; onOpen: (organization: MarketOrganization) => void }) {
  return (
    <section className="market-table-panel">
      <div className="market-table-header">
        <span>{mode === 'buyers' ? 'Οργανισμός / Why now' : 'Ανάδοχος / market footprint'}</span>
        <span>Κατηγορία</span><span>{mode === 'buyers' ? 'Incumbent / Brands' : 'Brands / Buyers'}</span><span>Score</span><span>Επόμενη κίνηση</span>
      </div>
      {organizations.length ? organizations.map((organization) => (
        <button className="market-table-row" type="button" key={organization.id} onClick={() => onOpen(organization)}>
          <span className="market-org-name"><strong>{organization.name}</strong><small>{organization.strongest_signal_kind ? signalKindLabel(organization.strongest_signal_kind) : 'Market evidence'} · {formatDate(organization.last_signal_at)}</small></span>
          <span><i className="market-category-chip">{organization.strongest_category ?? 'General Software'}</i></span>
          <span className="market-evidence-stack"><strong>{(organization.incumbent_suppliers.length ? organization.incumbent_suppliers : organization.software_brands).slice(0, 2).join(', ') || 'Δεν έχει εντοπιστεί'}</strong><small>{organization.software_brands.slice(0, 3).join(' · ')}</small></span>
          <span><NeedScore score={organization.strongest_signal_score} /></span>
          <span className="market-next-action"><strong>{organization.tracking_state ? trackingLabel(organization.tracking_state) : 'Νέο'}</strong><small>{organization.next_action ?? 'Άνοιγμα intelligence'}</small></span>
        </button>
      )) : <p className="market-empty">Δεν υπάρχουν ακόμη οργανισμοί με αυτά τα φίλτρα. Τρέξε refresh ή χαμήλωσε το score.</p>}
    </section>
  )
}

function BrandMarketGrid({ brands }: { brands: SoftwareBrand[] }) {
  const visible = brands.filter((brand) => brand.mention_count > 0)
  return <section className="brand-market-grid">{visible.length ? visible.map((brand) => (
    <article className="brand-market-card" key={brand.id}>
      <div><span className={`region-badge ${brand.origin_region.toLowerCase().replaceAll(' ', '-')}`}>{brand.origin_region}</span><strong>{brand.name}</strong></div>
      <div className="brand-market-stats"><span><b>{brand.mention_count}</b> mentions</span><span><b>{formatCurrency(brand.observed_spend)}</b> observed spend</span></div>
      <p><b>Integrators:</b> {brand.supplier_names.slice(0, 4).join(', ') || 'Δεν έχουν εντοπιστεί'}</p>
      <p><b>Buyers:</b> {brand.buyer_names.slice(0, 4).join(', ') || 'Δεν έχουν εντοπιστεί'}</p>
      <small>Τελευταίο evidence: {formatDate(brand.last_seen_at)}</small>
    </article>
  )) : <p className="market-empty">Τα brands θα εμφανιστούν όταν εντοπιστούν μέσα σε τεκμηριωμένα source records.</p>}</section>
}

function MarketSignalList({ signals, onOpenOrganization }: { signals: MarketSignal[]; onOpenOrganization: (id: string) => void }) {
  return <section className="market-signal-list">{signals.length ? signals.map((signal) => (
    <article className={`market-signal-card ${signal.stage}`} key={signal.id}>
      <div className="market-signal-score"><NeedScore score={signal.need_score} />{signal.is_new ? <span>NEW</span> : null}</div>
      <div className="market-signal-body">
        <div className="market-signal-meta"><span>{signal.category}</span><i>{signalStageLabel(signal.stage)}</i><small>{signal.evidence.source}</small></div>
        <button type="button" onClick={() => onOpenOrganization(signal.organization_id)}>{signal.organization_name}</button>
        <strong>{signal.evidence.title}</strong><p>{signal.why_now}</p><small>{signal.evidence.excerpt}</small>
      </div>
      <div className="market-signal-actions"><span>Confidence {signal.confidence}%</span>{signal.evidence.url ? <EvidencePreviewButton evidence={signal.evidence} label="Evidence" /> : null}</div>
    </article>
  )) : <p className="market-empty">Δεν υπάρχουν early/open signals με αυτά τα φίλτρα.</p>}</section>
}

function RefreshRunSummary({ refresh }: { refresh: MarketRefresh }) {
  return <section className="refresh-summary"><div><RefreshCw size={16} /><strong>Refresh {refresh.status}</strong><span>{formatDateTime(refresh.finished_at ?? refresh.started_at)}</span></div><div>{refresh.source_results.map((item) => <span className={`refresh-source ${item.status}`} key={item.source}>{item.source}: {item.status} · {item.created} νέα</span>)}</div></section>
}

function MarketOrganizationDrawer({ detail, onClose, onChanged }: { detail: MarketOrganizationDetail | null; onClose: () => void; onChanged: () => Promise<void> }) {
  const [state, setState] = useState<TrackingState>('watching')
  const [notes, setNotes] = useState('')
  const [nextAction, setNextAction] = useState('')
  const [nextActionAt, setNextActionAt] = useState('')
  const [saving, setSaving] = useState(false)
  const [watchUrl, setWatchUrl] = useState('')
  const [watchLabel, setWatchLabel] = useState('')
  const [watchType, setWatchType] = useState<'careers' | 'newsroom'>('careers')
  const [message, setMessage] = useState<string | null>(null)

  useEffect(() => {
    if (!detail) return
    // Reset the editable form whenever a different drawer entity is loaded.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setState(detail.tracking?.state ?? 'watching')
    setNotes(detail.tracking?.notes ?? '')
    setNextAction(detail.tracking?.next_action ?? '')
    setNextActionAt(detail.tracking?.next_action_at ?? '')
    setMessage(null)
  }, [detail])

  if (!detail) return null
  const organization = detail.organization
  const awards = organization.role === 'supplier' ? detail.awards_as_supplier : detail.awards_as_buyer

  const saveTracking = async (event: FormEvent) => {
    event.preventDefault()
    setSaving(true)
    setMessage(null)
    try {
      const entityType = organization.role === 'supplier' ? 'supplier' : 'buyer'
      const res = await fetch(`${API_BASE}/api/market/tracking`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ entity_type: entityType, entity_id: organization.id, state, notes, next_action: nextAction || null, next_action_at: nextActionAt || null }),
      })
      if (!res.ok) throw new Error(`Tracking API returned ${res.status}`)
      setMessage('Το tracking ενημερώθηκε.')
      await onChanged()
    } catch (exc) {
      setMessage(exc instanceof Error ? exc.message : 'Tracking save failed')
    } finally {
      setSaving(false)
    }
  }

  const addWatchSource = async (event: FormEvent) => {
    event.preventDefault()
    setMessage(null)
    try {
      const res = await fetch(`${API_BASE}/api/market/watch-sources`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ organization_id: organization.id, source_type: watchType, url: watchUrl, label: watchLabel, enabled: true }),
      })
      const payload = await res.json().catch(() => null) as { detail?: string } | null
      if (!res.ok) throw new Error(payload?.detail ?? `Watch source returned ${res.status}`)
      setWatchUrl(''); setWatchLabel(''); setMessage('Η επίσημη πηγή προστέθηκε.')
      await onChanged()
    } catch (exc) {
      setMessage(exc instanceof Error ? exc.message : 'Watch source save failed')
    }
  }

  return (
    <div className="drawer-backdrop market-drawer-backdrop" role="presentation" onMouseDown={onClose}>
      <aside className="details-drawer market-org-drawer" role="dialog" aria-modal="true" aria-label={`Market intelligence for ${organization.name}`} onMouseDown={(event) => event.stopPropagation()}>
        <header className="drawer-header market-drawer-header">
          <div><p className="eyebrow">{organization.role === 'supplier' ? 'Integrator / Supplier' : 'Buyer intelligence'}</p><h3>{organization.name}</h3><span>{organization.strongest_category ?? 'General Software'} · {organization.country}</span></div>
          <NeedScore score={organization.strongest_signal_score} />
          <button className="icon-button" type="button" onClick={onClose} aria-label="Close"><X size={18} /></button>
        </header>

        <div className="drawer-content market-drawer-content">
          <section className="drawer-section why-now-section">
            <div className="panel-heading"><Sparkles size={18} /><h4>Why now?</h4></div>
            {detail.signals.length ? <><strong>{detail.signals[0].why_now}</strong><p>{detail.signals[0].evidence.title}</p><div className="market-signal-reasons">{detail.signals[0].score_reasons.map((reason) => <span key={reason}>{reason}</span>)}</div>{detail.signals[0].evidence.url ? <EvidencePreviewButton evidence={detail.signals[0].evidence} label="Άνοιγμα evidence" /> : null}</> : <p className="muted">Δεν υπάρχει ακόμη ενεργό need signal.</p>}
          </section>

          <section className="drawer-section">
            <div className="panel-heading"><Activity size={18} /><h4>Signal timeline</h4></div>
            <div className="market-timeline">{detail.signals.map((signal) => <div key={signal.id}><i className={signal.stage} /><span><strong>{signalKindLabel(signal.kind)} · {signal.category}</strong><small>{formatDate(signal.evidence.published_at)} · score {signal.need_score} · {signal.evidence.source}</small><p>{signal.evidence.title}</p></span></div>)}</div>
          </section>

          <section className="drawer-section">
            <div className="panel-heading"><Handshake size={18} /><h4>{organization.role === 'supplier' ? 'Observed customers' : 'Incumbents & past purchases'}</h4></div>
            <div className="market-award-list">{awards.length ? awards.map((award) => <article key={award.id}><div><strong>{organization.role === 'supplier' ? award.buyer_name : award.supplier_name}</strong><span>{formatCurrency(award.amount)} · {formatDate(award.awarded_at)}</span></div><p>{award.title}</p><small>{award.category}{award.software_brands.length ? ` · ${award.software_brands.join(', ')}` : ''}</small>{award.evidence.url ? <EvidencePreviewButton evidence={award.evidence} label="Preview evidence" compact /> : null}</article>) : <p className="muted">Δεν έχουν εντοπιστεί ακόμη τεκμηριωμένες αναθέσεις.</p>}</div>
          </section>

          <section className="drawer-section">
            <div className="panel-heading"><Tags size={18} /><h4>Software brands</h4></div>
            <div className="brand-mention-list">{detail.brand_mentions.length ? detail.brand_mentions.map((mention) => <span key={mention.id}><strong>{mention.brand_name}</strong><small>{mention.product_name ?? 'Brand mention'} · confidence {mention.confidence}%</small></span>) : <p className="muted">Δεν έχει εντοπιστεί brand με source evidence.</p>}</div>
          </section>

          <section className="drawer-section market-tracking-section">
            <div className="panel-heading"><Save size={18} /><h4>Tracking & next action</h4></div>
            <form onSubmit={saveTracking}>
              <label><span>Status</span><select value={state} onChange={(event) => setState(event.target.value as TrackingState)}>{MARKET_TRACKING_OPTIONS.map((item) => <option value={item} key={item}>{trackingLabel(item)}</option>)}</select></label>
              <label><span>Next action</span><input value={nextAction} onChange={(event) => setNextAction(event.target.value)} placeholder="π.χ. Discovery call με CIO" /></label>
              <label><span>Ημερομηνία</span><input type="date" value={nextActionAt} onChange={(event) => setNextActionAt(event.target.value)} /></label>
              <label className="tracking-notes"><span>Σημειώσεις</span><textarea rows={4} value={notes} onChange={(event) => setNotes(event.target.value)} /></label>
              <button className="primary-action" type="submit" disabled={saving}>{saving ? <Loader2 className="spin" size={15} /> : <Save size={15} />} Αποθήκευση</button>
            </form>
          </section>

          {organization.role !== 'supplier' ? <section className="drawer-section">
            <div className="panel-heading"><Globe2 size={18} /><h4>Official private signals</h4></div>
            <div className="watch-source-list">{detail.watch_sources.map((source) => <a href={source.url} target="_blank" rel="noreferrer" key={source.id}><strong>{source.label || source.source_type}</strong><small>{source.last_error ?? (source.last_checked_at ? `Checked ${formatDateTime(source.last_checked_at)}` : 'Not checked yet')}</small></a>)}</div>
            <form className="watch-source-form" onSubmit={addWatchSource}>
              <select value={watchType} onChange={(event) => setWatchType(event.target.value as 'careers' | 'newsroom')}><option value="careers">Careers</option><option value="newsroom">Newsroom</option></select>
              <input value={watchLabel} onChange={(event) => setWatchLabel(event.target.value)} placeholder="Label" />
              <input type="url" value={watchUrl} onChange={(event) => setWatchUrl(event.target.value)} placeholder="https://company.gr/careers" required />
              <button className="secondary-action" type="submit"><Plus size={15} /> Add source</button>
            </form>
          </section> : null}
          {message ? <p className="market-drawer-message">{message}</p> : null}
        </div>
      </aside>
    </div>
  )
}

function NeedScore({ score }: { score: number }) {
  const tone = score >= 75 ? 'hot' : score >= 50 ? 'warm' : score >= 25 ? 'watch' : 'context'
  return <span className={`need-score ${tone}`}><strong>{score}</strong><small>{tone === 'hot' ? 'HOT' : tone === 'warm' ? 'WARM' : tone === 'watch' ? 'WATCH' : 'CONTEXT'}</small></span>
}

const MARKET_TRACKING_OPTIONS: TrackingState[] = ['new', 'watching', 'researching', 'contact_planned', 'contacted', 'meeting', 'proposal', 'partner_target', 'won', 'lost', 'archived']

function trackingLabel(state: TrackingState): string {
  return ({ new: 'Νέο', watching: 'Παρακολούθηση', researching: 'Έρευνα', contact_planned: 'Προγραμματισμένη επαφή', contacted: 'Έγινε επαφή', meeting: 'Meeting', proposal: 'Πρόταση', partner_target: 'Partner target', won: 'Κερδήθηκε', lost: 'Χάθηκε', archived: 'Αρχείο' })[state]
}

function signalKindLabel(kind: string): string {
  const labels: Record<string, string> = { procurement_request: 'Αίτημα προμήθειας', planning_notice: 'Planning notice', open_tender: 'Ανοιχτός διαγωνισμός', job_hiring: 'Σχετική πρόσληψη', expansion: 'Επέκταση', capital_change: 'Κεφαλαιακή μεταβολή', acquisition: 'Εξαγορά / συγχώνευση', transformation: 'Digital transformation', award: 'Ανάθεση', contract: 'Σύμβαση', payment: 'Πληρωμή' }
  return labels[kind] ?? kind
}

function signalStageLabel(stage: MarketSignal['stage']): string {
  return ({ early: 'Early signal', open: 'Open opportunity', awarded: 'Awarded', historical: 'Historical' })[stage]
}

function PatternsPanel({
  patterns,
  loading,
  error,
  opportunities,
  onOpenOpportunity,
}: {
  patterns: NeedPattern[]
  loading: boolean
  error: string | null
  opportunities: Opportunity[]
  onOpenOpportunity: (opportunity: Opportunity) => void
}) {
  const opportunityById = useMemo(() => new Map(opportunities.map((opportunity) => [opportunity.id, opportunity])), [opportunities])

  return (
    <div className="pattern-panel">
      <div className="panel-heading">
        <Layers3 size={18} aria-hidden="true" />
        <h3>Repeated needs</h3>
      </div>
      <p className="panel-note">Curated product/service patterns detected in the loaded results.</p>
      {loading ? (
        <div className="pattern-state">
          <Loader2 className="spin" size={18} aria-hidden="true" />
          <span>Detecting patterns...</span>
        </div>
      ) : error ? (
        <p className="drawer-error-inline">{error}</p>
      ) : patterns.length ? (
        <div className="pattern-list scrollable">
          {patterns.map((pattern) => (
            <article className="pattern-card" key={pattern.pattern_id}>
              <div className="pattern-card-header">
                <div>
                  <span>{pattern.category}</span>
                  <h4>{pattern.label}</h4>
                </div>
                <strong>{pattern.productization_score}</strong>
              </div>
              <p>{pattern.recommended_package}</p>
              {pattern.recommended_products?.length ? (
                <div className="pattern-products" aria-label="Recommended open-source products">
                  {pattern.recommended_products.map((match) => (
                    <span key={match.product.slug}>{match.product.name} · {match.score}</span>
                  ))}
                </div>
              ) : null}
              <div className="pattern-metrics">
                <span><Target size={14} aria-hidden="true" />{pattern.opportunity_count} matches</span>
                <span><Building2 size={14} aria-hidden="true" />{pattern.buyer_count} buyers</span>
                <span><CircleDollarSign size={14} aria-hidden="true" />{formatCurrency(pattern.median_budget)}</span>
                <span><Gauge size={14} aria-hidden="true" />Repeat {pattern.repeat_score}</span>
              </div>
              {pattern.keywords.length ? (
                <div className="pattern-keywords">
                  {pattern.keywords.slice(0, 5).map((keyword) => (
                    <span key={keyword}>{keyword}</span>
                  ))}
                </div>
              ) : null}
              <div className="pattern-examples">
                {pattern.samples.slice(0, 3).map((sample) => {
                  const opportunity = opportunityById.get(sample.id)
                  return (
                    <button
                      type="button"
                      key={sample.id}
                      disabled={!opportunity}
                      onClick={() => opportunity ? onOpenOpportunity(opportunity) : undefined}
                    >
                      <strong>{sample.fit_score}</strong>
                      <span>{sample.title}</span>
                    </button>
                  )
                })}
              </div>
            </article>
          ))}
        </div>
      ) : (
        <p className="muted">No repeated need patterns yet.</p>
      )}
    </div>
  )
}

function SmartCalendarPanel({
  activity,
  loading,
  error,
  selectedSources,
}: {
  activity: ActivityResponse | null
  loading: boolean
  error: string | null
  selectedSources: SourceName[]
}) {
  const visibleSources = useMemo(() => selectedSources.filter((source) => source !== 'demo'), [selectedSources])
  const calendarYear = new Date().getFullYear()
  const [selectedMonth, setSelectedMonth] = useState(() => new Date().getMonth())
  const yearMonths = useMemo(
    () => buildCalendarYear(calendarYear, activity?.daily_activity ?? [], visibleSources),
    [activity?.daily_activity, calendarYear, visibleSources],
  )
  const currentMonth = yearMonths[selectedMonth] ?? yearMonths[new Date().getMonth()]
  const activeDayCount = currentMonth?.cells.filter((cell) => cell.inMonth && cell.total > 0).length ?? 0
  const sourceSummary = visibleSources.map((source) => SOURCE_META[source].label).join(' + ')
  const moveMonth = (direction: -1 | 1) => {
    setSelectedMonth((month) => (month + direction + 12) % 12)
  }

  return (
    <div className="smart-calendar-panel">
      <div className="calendar-panel-top">
        <div>
          <div className="panel-heading">
            <CalendarClock size={18} aria-hidden="true" />
            <h3>Smart calendar</h3>
          </div>
          <p className="panel-note">Monthly view for new publications from selected sources. Data is refreshed once per day.</p>
        </div>
        <div className="calendar-summary" aria-label={`Activity summary for ${currentMonth?.label ?? calendarYear}`}>
          <strong>{currentMonth?.total ?? 0}</strong>
          <span>{currentMonth?.label ?? calendarYear}</span>
        </div>
      </div>

      {loading ? (
        <div className="calendar-state">
          <Loader2 className="spin" size={17} aria-hidden="true" />
          <span>Loading yearly activity...</span>
        </div>
      ) : null}

      {!loading && error ? (
        <div className="calendar-state error">
          <AlertTriangle size={17} aria-hidden="true" />
          <span>{error}</span>
        </div>
      ) : null}

      {!loading && !error ? (
        <div className="calendar-month-wrap">
          <div className="calendar-toolbar" aria-label="Calendar navigation">
            <button className="calendar-nav-button" type="button" onClick={() => moveMonth(-1)} aria-label="Previous month">
              <ChevronLeft size={17} aria-hidden="true" />
            </button>
            <label className="calendar-month-picker">
              <span>Month</span>
              <select value={selectedMonth} onChange={(event) => setSelectedMonth(Number(event.target.value))}>
                {yearMonths.map((month) => (
                  <option value={month.month} key={`${month.year}-${month.month}`}>
                    {month.label}
                  </option>
                ))}
              </select>
            </label>
            <button className="calendar-nav-button" type="button" onClick={() => moveMonth(1)} aria-label="Next month">
              <ChevronRight size={17} aria-hidden="true" />
            </button>
          </div>
          <div className="calendar-year-meta">
            <span>{sourceSummary || 'No live sources selected'}</span>
            <span>{activeDayCount} active days</span>
            <span>{activity?.cached ? 'Cached today' : 'Fresh today'}</span>
            {activity ? <span>Updated {formatDateTime(activity.generated_at)}</span> : null}
          </div>
          {currentMonth ? (
            <section className="calendar-month current" key={`${currentMonth.year}-${currentMonth.month}`}>
              <div className="calendar-month-title">
                <strong>{currentMonth.label}</strong>
                <span>{currentMonth.total}</span>
              </div>
              <div className="calendar-weekdays" aria-hidden="true">
                {CALENDAR_WEEKDAYS.map((day) => (
                  <span key={`${currentMonth.label}-${day}`}>{day}</span>
                ))}
              </div>
              <div className="calendar-days">
                {currentMonth.cells.map((cell) => (
                  <div
                    className={[
                      'calendar-day',
                      cell.inMonth ? '' : 'outside',
                      cell.isToday ? 'today' : '',
                      cell.isFuture ? 'future' : '',
                      cell.total > 0 ? 'has-activity' : '',
                    ].filter(Boolean).join(' ')}
                    key={`${currentMonth.year}-${currentMonth.month}-${cell.date}-${cell.offset}`}
                    title={calendarDayTitle(cell, visibleSources)}
                    aria-label={calendarDayTitle(cell, visibleSources)}
                  >
                    <span className="calendar-day-number">{cell.dayOfMonth}</span>
                    <span className="calendar-day-count">{cell.total}</span>
                  </div>
                ))}
              </div>
            </section>
          ) : null}
        </div>
      ) : null}
    </div>
  )
}

function OpportunityRow({
  opportunity,
  guidance,
  pinned,
  onTogglePin,
  onOpenDetails,
}: {
  opportunity: Opportunity
  guidance?: OpportunityGuidance
  pinned: boolean
  onTogglePin: () => void
  onOpenDetails: () => void
}) {
  const bandClass = bandToClass(opportunity.fit_score)
  const daysLeft = opportunity.deadline ? daysUntil(opportunity.deadline) : null
  const window = actionWindow(opportunity)
  const stage = rowLifecycleStage(opportunity, guidance)
  const PinIcon = pinned ? BookmarkCheck : BookmarkPlus

  return (
    <article className={`opportunity-row ${bandClass}`}>
      <div className="score-cell">
        <div className="score-ring" style={{ '--score': `${opportunity.fit_score * 3.6}deg` } as CSSProperties}>
          <strong>{opportunity.fit_score}</strong>
          <span>fit</span>
        </div>
        <span className={`band ${bandClass}`}>{opportunity.fit_band}</span>
      </div>

      <div className="opportunity-main">
        <div className="title-line">
          <div>
            <div className="source-line">
              <span>{opportunity.source_label}</span>
              {opportunity.procedure_type ? <span>{opportunity.procedure_type}</span> : null}
              {opportunity.package_match ? <span>{packageLabel(opportunity.package_match)}</span> : null}
              {opportunity.software_matches?.[0] ? (
                <span className="software-match-chip">
                  <Sparkles size={12} aria-hidden="true" />
                  {opportunity.software_matches[0].product.name} · {opportunity.software_matches[0].score}
                </span>
              ) : null}
              <span className={`stage-chip ${stage.tone}`}>{stage.label}</span>
              <span className={`action-window ${window.tone}`}>{window.label}</span>
            </div>
            <h4>{opportunity.title}</h4>
          </div>
          <div className="row-actions">
            <button className="details-action" type="button" onClick={onOpenDetails}>
              Details
              <PanelRightOpen size={15} aria-hidden="true" />
            </button>
            {opportunity.url ? (
              <a className="platform-link" href={opportunity.url} target="_blank" rel="noreferrer">
                Open source
                <ExternalLink size={15} aria-hidden="true" />
              </a>
            ) : null}
            <button className="icon-action" type="button" onClick={onTogglePin} aria-label={pinned ? 'Remove from shortlist' : 'Add to shortlist'}>
              <PinIcon size={18} aria-hidden="true" />
            </button>
          </div>
        </div>

        <p className="summary">{opportunity.summary}</p>

        <div className="meta-grid">
          <Meta icon={Building2} label="Buyer" value={opportunity.buyer} />
          <Meta icon={CircleDollarSign} label="Budget" value={formatCurrency(opportunity.budget)} />
          <Meta icon={CalendarClock} label="Published" value={formatPublishedDate(opportunity.published_at)} />
          <Meta icon={CalendarClock} label="Deadline" value={daysLeft === null ? 'Unknown' : `${formatDate(opportunity.deadline)} - ${daysLeft}d`} />
          <Meta icon={Gauge} label="Action window" value={window.detail} />
          <Meta icon={FileText} label="CPV" value={opportunity.cpv_codes.slice(0, 3).join(', ') || 'N/A'} />
        </div>

        <div className="row-footer">
          <div className="keyword-stack">
            {opportunity.matched_keywords.slice(0, 5).map((keyword) => (
              <span key={keyword}>{keyword}</span>
            ))}
          </div>
        </div>
      </div>
    </article>
  )
}

function GuidancePanel({ guidance }: { guidance: OpportunityGuidance }) {
  return (
    <section className="drawer-section guidance-section">
      <div className="guidance-header">
        <div>
          <h4>Lifecycle guidance</h4>
          <p>{guidance.is_actionable ? 'This looks actionable now.' : 'This is not clearly actionable yet.'}</p>
        </div>
        <span className={`actionable-pill ${guidance.is_actionable ? 'yes' : 'no'}`}>
          {guidance.is_actionable ? 'Actionable' : 'Watch'}
        </span>
      </div>

      <div className="lifecycle-tracker" aria-label="Lifecycle tracker">
        {guidance.stage_steps.map((step, index) => (
          <div className={`lifecycle-node ${step.status}`} key={step.id}>
            <div className="lifecycle-number" aria-label={`${index + 1}. ${step.label}`}>
              {index + 1}
            </div>
            <div className="lifecycle-node-copy">
              <strong>{step.label}</strong>
              <small>{step.references.length ? step.references.join(', ') : lifecycleStatusLabel(step.status)}</small>
            </div>
          </div>
        ))}
      </div>

      <div className="guidance-cards">
        <GuidanceCard title="Where we are now" value={guidance.current_stage_label} />
        <GuidanceCard title="Can I act now?" value={guidance.is_actionable ? 'Yes, review and prepare a bid.' : 'Not yet. Monitor the next official step.'} />
        <GuidanceCard title="Next action" value={guidance.next_action} />
      </div>

      {guidance.primary_action_link ? (
        <a className="drawer-primary-link" href={guidance.primary_action_link} target="_blank" rel="noreferrer">
          Open recommended document
          <ExternalLink size={15} aria-hidden="true" />
        </a>
      ) : null}

      <CollapsiblePanel title="Checklist για αρχάριους" meta={`${guidance.checklist.length} βήματα`}>
        <div className="checklist-list">
          {guidance.checklist.map((item, index) => {
            const translatedItem = translateChecklistItem(item)
            return (
            <div className={`checklist-item ${item.status}`} key={`${item.label}-${item.status}`}>
              <span className="checklist-index">{index + 1}</span>
              <span>
                <strong>{translatedItem.label}</strong>
                <small>{translatedItem.detail}</small>
              </span>
            </div>
            )
          })}
        </div>
      </CollapsiblePanel>

      {guidance.watch_items.length ? (
        <div className="watch-block">
          <h5>What to watch next</h5>
          <ul>
            {guidance.watch_items.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  )
}

type PdfPreview = {
  title: string
  url: string
  meta: string
  mode?: 'document' | 'web'
}

function EvidencePreviewButton({ evidence, label, compact = false }: { evidence: EvidenceRef; label: string; compact?: boolean }) {
  const [preview, setPreview] = useState<PdfPreview | null>(null)
  if (!evidence.url) return null

  return (
    <>
      <button
        className={`evidence-preview-button ${compact ? 'compact' : ''}`}
        type="button"
        aria-label={`${label}: ${evidence.title}`}
        title={evidence.title}
        onClick={() => setPreview({
          title: evidence.title,
          url: evidence.url as string,
          meta: [evidence.source, formatDate(evidence.published_at)].filter(Boolean).join(' · '),
          mode: isOfficialDocumentEvidence(evidence) ? 'document' : 'web',
        })}
      >
        {compact ? null : label}
        <PanelRightOpen size={compact ? 14 : 13} aria-hidden="true" />
      </button>
      {preview ? <PdfPreviewModal preview={preview} onClose={() => setPreview(null)} /> : null}
    </>
  )
}

function DocumentsDetailItem({ documents }: { documents: DocumentLink[] }) {
  const [preview, setPreview] = useState<PdfPreview | null>(null)

  return (
    <div className="detail-item documents-detail-item">
      <span>Documents</span>
      {documents.length ? (
        <div className="document-inline-list" aria-label={`${documents.length} available source documents`}>
          {documents.map((document) => {
            const meta = [document.document_type, document.language, document.reference].filter(Boolean).join(' · ')
            const key = `${document.document_type}-${document.language}-${document.reference}-${document.url}`
            if (isPdfDocument(document)) {
              return (
                <button
                  className="document-link"
                  type="button"
                  key={key}
                  onClick={() => setPreview({ title: document.label, url: document.url, meta })}
                >
                  <FileText size={16} aria-hidden="true" />
                  <span>
                    <strong>{document.label}</strong>
                    <small>{meta}</small>
                  </span>
                  <ExternalLink size={14} aria-hidden="true" />
                </button>
              )
            }
            return (
              <a className="document-link" href={document.url} target="_blank" rel="noreferrer" key={key}>
                <FileText size={16} aria-hidden="true" />
                <span>
                  <strong>{document.label}</strong>
                  <small>{meta}</small>
                </span>
                <ExternalLink size={14} aria-hidden="true" />
              </a>
            )
          })}
        </div>
      ) : (
        <p className="muted">Δεν βρέθηκαν διαθέσιμα links εγγράφων από την πηγή.</p>
      )}
      {preview ? <PdfPreviewModal preview={preview} onClose={() => setPreview(null)} /> : null}
    </div>
  )
}

function PdfPreviewModal({ preview, onClose }: { preview: PdfPreview; onClose: () => void }) {
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onClose()
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [onClose])

  return (
    <div className="pdf-preview-backdrop" role="presentation" onClick={onClose}>
      <section className="pdf-preview-modal" role="dialog" aria-modal="true" aria-label={preview.title} onClick={(event) => event.stopPropagation()}>
        <div className="pdf-preview-header">
          <span>
            <strong>{preview.title}</strong>
            {preview.meta ? <small>{preview.meta}</small> : null}
          </span>
          <div className="pdf-preview-actions">
            <a className="icon-action" href={preview.url} target="_blank" rel="noreferrer" aria-label="Open original in new tab">
              <ExternalLink size={17} aria-hidden="true" />
            </a>
            <button className="icon-action" type="button" onClick={onClose} aria-label="Close preview">
              <X size={18} aria-hidden="true" />
            </button>
          </div>
        </div>
        <iframe className="pdf-preview-frame" src={preview.mode === 'web' ? preview.url : pdfViewerUrl(preview.url)} title={preview.title} />
      </section>
    </div>
  )
}

function pdfViewerUrl(url: string): string {
  return `${API_BASE}/api/documents/pdf?url=${encodeURIComponent(url)}`
}

function isPdfDocument(document: DocumentLink): boolean {
  const type = document.document_type.toLowerCase()
  return ['pdf', 'pdfs', 'request', 'notice', 'auction', 'contract', 'payment'].includes(type) || isPreviewableFileUrl(document.url)
}

function isPreviewableFileUrl(url?: string | null): url is string {
  if (!url) {
    return false
  }
  const lowerUrl = url.toLowerCase()
  return lowerUrl.includes('/attachment/') || lowerUrl.includes('/document') || lowerUrl.endsWith('.pdf')
}

function isOfficialDocumentEvidence(evidence: EvidenceRef): boolean {
  return ['khmdhs', 'diavgeia', 'ted'].includes(evidence.source) && isPreviewableFileUrl(evidence.url)
}

function previewFromUrl(title: string, url: string, meta: string): PdfPreview {
  return { title, url, meta }
}

function CollapsiblePanel({ title, meta, children }: { title: string; meta?: string; children: ReactNode }) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div className="collapsible-panel">
      <button className="collapsible-panel-button" type="button" aria-expanded={expanded} onClick={() => setExpanded((current) => !current)}>
        <span>
          <strong>{title}</strong>
          {meta ? <small>{meta}</small> : null}
        </span>
        <ChevronDown className={expanded ? 'expanded' : undefined} size={17} aria-hidden="true" />
      </button>
      {expanded ? <div className="collapsible-panel-body">{children}</div> : null}
    </div>
  )
}

function GuidanceCard({ title, value }: { title: string; value: string }) {
  return (
    <div className="guidance-card">
      <span>{title}</span>
      <strong>{value}</strong>
    </div>
  )
}

function lifecycleStatusLabel(status: LifecycleStep['status']) {
  if (status === 'complete') return 'Completed'
  if (status === 'current') return 'Current'
  if (status === 'upcoming') return 'Upcoming'
  return 'Unknown'
}

function translateChecklistItem(item: GuidanceChecklistItem) {
  const normalizedLabel = item.label.trim().toLowerCase()
  const translations: Record<string, { label: string; detail: string }> = {
    'open source document': {
      label: 'Άνοιξε το επίσημο έγγραφο',
      detail: 'Διάβασε πρώτα το αρχικό έγγραφο της πηγής.',
    },
    'confirm competition notice': {
      label: 'Επιβεβαίωσε διακήρυξη',
      detail: 'Ψάξε για πρόσκληση, notice ή διαγωνισμό πριν προχωρήσεις.',
    },
    'check deadline and submission method': {
      label: 'Έλεγξε προθεσμία και υποβολή',
      detail: 'Κλείδωσε ημερομηνία, τρόπο υποβολής, υπογραφές και μορφές αρχείων.',
    },
    'collect company/legal documents': {
      label: 'Μάζεψε εταιρικά δικαιολογητικά',
      detail: 'Ετοίμασε φορολογικά, ασφαλιστικά, δηλώσεις και πιστοποιητικά.',
    },
    'prepare technical offer': {
      label: 'Ετοίμασε τεχνική προσφορά',
      detail: 'Σύνδεσε τη λύση σου με κάθε τεχνική απαίτηση.',
    },
    'prepare financial offer': {
      label: 'Ετοίμασε οικονομική προσφορά',
      detail: 'Υπολόγισε κόστος, ΦΠΑ, υποστήριξη, hosting και άδειες.',
    },
    'submit and monitor': {
      label: 'Υπέβαλε και παρακολούθησε',
      detail: 'Κάνε υποβολή και έλεγχε διευκρινίσεις, ανάθεση και σύμβαση.',
    },
  }

  return translations[normalizedLabel] ?? {
    label: item.label,
    detail: item.detail,
  }
}

export function SoftwareMatchesPanel({
  opportunity,
  aiEnabled,
  selectedAiModel,
}: {
  opportunity: Opportunity
  aiEnabled: boolean
  selectedAiModel: string
}) {
  const [matches, setMatches] = useState<SoftwareMatch[]>(opportunity.software_matches ?? [])
  const [status, setStatus] = useState<'matched' | 'insufficient_signals'>(opportunity.software_match_status ?? 'insufficient_signals')
  const [refining, setRefining] = useState(false)
  const [refinementMeta, setRefinementMeta] = useState<{ model?: string | null; cached: boolean } | null>(null)
  const [refinementError, setRefinementError] = useState<string | null>(null)

  const refine = async () => {
    setRefining(true)
    setRefinementError(null)
    try {
      const response = await fetch(`${API_BASE}/api/software-matches/refine`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ opportunity, model: selectedAiModel }),
      })
      const payload = await response.json().catch(() => null) as (SoftwareMatchRefineResponse & { detail?: string }) | null
      if (!response.ok || !payload) {
        throw new Error(payload?.detail ?? `AI refinement returned ${response.status}`)
      }
      setMatches(payload.matches)
      setStatus(payload.match_status)
      setRefinementMeta({ model: payload.model, cached: payload.cached })
    } catch (error) {
      setRefinementError(error instanceof Error ? error.message : 'AI refinement failed safely.')
    } finally {
      setRefining(false)
    }
  }

  return (
    <section className="drawer-section software-matches-section">
      <div className="software-matches-header">
        <div>
          <p className="eyebrow">Product matchmaking</p>
          <h4>Recommended open-source products</h4>
          <p>Automatic deterministic ranking from the local {matches[0]?.catalog_version ?? 'versioned'} catalog.</p>
        </div>
        <button className="software-refine-button" type="button" onClick={() => void refine()} disabled={!aiEnabled || refining}>
          {refining ? <Loader2 className="spin" size={15} aria-hidden="true" /> : <Sparkles size={15} aria-hidden="true" />}
          {refining ? 'Refining…' : 'Refine with AI'}
        </button>
      </div>

      {!aiEnabled ? <p className="software-ai-note">AI refinement is unavailable because no API key is configured. Deterministic matching remains active.</p> : null}
      {refinementMeta ? (
        <p className="software-ai-note success">
          AI refined · {refinementMeta.model ?? selectedAiModel}{refinementMeta.cached ? ' · cached result' : ''}
        </p>
      ) : null}
      {refinementError ? <p className="drawer-error-inline">{refinementError}</p> : null}

      {status === 'insufficient_signals' || !matches.length ? (
        <div className="software-no-match">
          <Info size={18} aria-hidden="true" />
          <div><strong>Insufficient signals</strong><p>No product is being forced into this opportunity. Add specific capability or CPV evidence to improve matching.</p></div>
        </div>
      ) : (
        <div className="software-match-list">
          {matches.map((match) => (
            <article className="software-match-card" key={match.product.slug}>
              <div className="software-match-card-head">
                <div>
                  <span>{match.product.edition}</span>
                  <h5>{match.product.name}</h5>
                </div>
                <div className={`software-score ${match.confidence}`}>
                  <strong>{match.score}</strong>
                  <small>{match.confidence}</small>
                </div>
              </div>
              <div className="software-source-row">
                <span>{match.source === 'ai_refined' ? 'AI refined' : 'Deterministic'}</span>
                <span>{match.product.delivery_fit.replace('_', ' ')}</span>
                <span>{match.product.license_id}</span>
              </div>
              <p>{match.product.summary}</p>
              {match.matched_signals.length ? (
                <ul className="software-reasons">
                  {match.matched_signals.slice(0, 5).map((reason, index) => <li key={`${reason}-${index}`}>{reason}</li>)}
                </ul>
              ) : null}
              {match.service_recommendations.length ? (
                <div className="software-services">
                  {match.service_recommendations.map((service) => (
                    <span className={service.confidence} key={service.service_type}>{service.label}</span>
                  ))}
                </div>
              ) : null}
              {match.caveats.length ? (
                <details className="software-caveats">
                  <summary>License, edition & health caveats ({match.caveats.length})</summary>
                  <ul>{match.caveats.map((caveat, index) => <li key={`${caveat}-${index}`}>{caveat}</li>)}</ul>
                </details>
              ) : null}
              {match.dimensions.length ? (
                <details className="software-dimensions">
                  <summary>Score breakdown</summary>
                  {match.dimensions.map((dimension) => (
                    <div key={dimension.key}><span>{dimension.label}</span><strong>{dimension.score}/{dimension.max_score}</strong></div>
                  ))}
                </details>
              ) : null}
              <div className="software-links">
                <a href={match.product.website} target="_blank" rel="noreferrer">Website <ExternalLink size={13} aria-hidden="true" /></a>
                <a href={match.product.repository} target="_blank" rel="noreferrer">Repository <ExternalLink size={13} aria-hidden="true" /></a>
                {match.evidence_ids.length ? <span>Evidence: {match.evidence_ids.join(', ')}</span> : null}
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  )
}

function DetailsDrawer({
  opportunity,
  details,
  loading,
  error,
  brief,
  briefOutdated,
  briefLoading,
  briefGenerating,
  briefError,
  buyerIntelligence,
  buyerIntelligenceLoading,
  buyerIntelligenceError,
  aiModels,
  selectedAiModel,
  softwareMatchAiEnabled,
  onSelectAiModel,
  onGenerateBrief,
  onClose,
}: {
  opportunity: Opportunity | null
  details: OpportunityDetails | null
  loading: boolean
  error: string | null
  brief: DocumentBrief | null
  briefOutdated: boolean
  briefLoading: boolean
  briefGenerating: boolean
  briefError: string | null
  buyerIntelligence: BuyerIntelligenceResponse | null
  buyerIntelligenceLoading: boolean
  buyerIntelligenceError: string | null
  aiModels: AIModelOption[]
  selectedAiModel: string
  softwareMatchAiEnabled: boolean
  onSelectAiModel: (model: string) => void
  onGenerateBrief: () => void
  onClose: () => void
}) {
  useEffect(() => {
    if (!opportunity) {
      return
    }

    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onClose()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => {
      document.body.style.overflow = previousOverflow
      window.removeEventListener('keydown', handleKeyDown)
    }
  }, [opportunity, onClose])

  if (!opportunity) {
    return null
  }

  const metadata = details?.metadata ?? {}
  const documents = details?.documents ?? []
  const primaryLinkLabel = details?.source === 'khmdhs' ? 'Άνοιγμα βασικού εγγράφου ΚΗΜΔΗΣ' : 'Άνοιγμα record'

  return (
    <div className="drawer-backdrop" role="presentation" onClick={onClose}>
      <aside className="details-drawer" role="dialog" aria-modal="true" aria-label="Opportunity details" onClick={(event) => event.stopPropagation()}>
        <div className="drawer-header">
          <div>
            <p className="eyebrow">{opportunity.source_label} details</p>
            <h3>{details?.title || opportunity.title}</h3>
          </div>
          <button className="icon-action" type="button" onClick={onClose} aria-label="Close details">
            <X size={18} aria-hidden="true" />
          </button>
        </div>

        {loading ? (
          <div className="drawer-state">
            <Loader2 className="spin" size={20} aria-hidden="true" />
            <span>Loading live details...</span>
          </div>
        ) : null}

        {error ? (
          <div className="drawer-error">
            <AlertTriangle size={17} aria-hidden="true" />
            <span>{error}</span>
          </div>
        ) : null}

        {!loading && !error ? (
          <div className="drawer-content">
            <section className="drawer-section details-overview-section">
              <h4>Available information</h4>
              <div className="details-overview-grid">
                <div className="details-grid">
                  <DetailItem label="Reference" value={details?.reference ?? opportunity.source_reference ?? 'N/A'} />
                  <DetailItem label="Source" value={opportunity.source_label} />
                  <DetailItem label="Buyer" value={formatSourceValue(metadata.buyer ?? metadata.organization ?? opportunity.buyer ?? 'N/A')} />
                  <DetailItem label="Published" value={String(metadata.publicationDate ?? metadata.submissionDate ?? opportunity.published_at ?? 'N/A')} />
                  <DetailItem label="Deadline" value={String(metadata.deadline ?? metadata.procurementDeliveryDate ?? opportunity.deadline ?? 'N/A')} />
                  <DetailItem label="Type" value={String(metadata.noticeType ?? metadata.procedureType ?? opportunity.procedure_type ?? 'N/A')} />
                  <DetailItem label="Budget" value={formatCurrency(opportunity.budget)} />
                  <CollapsibleCpvList label="CPV" value={opportunity.cpv_codes} />
                  <DocumentsDetailItem documents={documents} />
                </div>
                <div className="details-summary-panel">
                  <h5>Summary</h5>
                  <p className="drawer-summary">{details?.summary || opportunity.summary}</p>
                  {details?.platform_url ? (
                    <a className="drawer-primary-link" href={details.platform_url} target="_blank" rel="noreferrer">
                      {primaryLinkLabel}
                      <ExternalLink size={15} aria-hidden="true" />
                    </a>
                  ) : null}
                </div>
              </div>
            </section>

            <SoftwareMatchesPanel
              key={`software:${opportunity.id}`}
              opportunity={opportunity}
              aiEnabled={softwareMatchAiEnabled}
              selectedAiModel={selectedAiModel}
            />

            {details?.guidance ? (
              <GuidancePanel guidance={details.guidance} />
            ) : null}

            <div className="details-insight-grid">
              <BuyerIntelligencePanel intelligence={buyerIntelligence} loading={buyerIntelligenceLoading} error={buyerIntelligenceError} />

              <DocumentBriefPanel
                key={`${opportunity.source}:${opportunity.source_reference ?? details?.reference ?? ''}`}
                source={opportunity.source}
                reference={opportunity.source_reference ?? details?.reference ?? ''}
                availableDocumentCount={documents.length}
                brief={brief}
                outdated={briefOutdated}
                loading={briefLoading}
                generating={briefGenerating}
                error={briefError}
                aiModels={aiModels}
                selectedAiModel={selectedAiModel}
                onSelectAiModel={onSelectAiModel}
                canGenerate={Boolean(opportunity.source_reference)}
                onGenerate={onGenerateBrief}
              />
            </div>

            <section className="drawer-section source-data-section">
              <h4>Visualized source data</h4>
              <SourceDataVisualization details={details} />
            </section>

            <section className="drawer-section compact-section">
              <details className="raw-details">
                <summary>Raw JSON</summary>
                <pre>{JSON.stringify(details?.raw ?? {}, null, 2)}</pre>
              </details>
            </section>
          </div>
        ) : null}
      </aside>
    </div>
  )
}

function BuyerIntelligencePanel({
  intelligence,
  loading,
  error,
}: {
  intelligence: BuyerIntelligenceResponse | null
  loading: boolean
  error: string | null
}) {
  const [preview, setPreview] = useState<PdfPreview | null>(null)

  return (
    <section className="drawer-section buyer-intel-section">
      <div className="buyer-intel-header">
        <div>
          <h4>Buyer intelligence</h4>
          <p>Buyer history from visible rows, KIMDIS historical lookup, and best-effort award signals.</p>
        </div>
        {intelligence ? (
          <div className="buyer-status-pills">
            <span className={`source-status-pill ${intelligence.khmdhs_history_status}`}>KIMDIS history {intelligence.khmdhs_history_status}</span>
            <span className={`source-status-pill ${intelligence.diavgeia_status}`}>Diavgeia {intelligence.diavgeia_status}</span>
          </div>
        ) : null}
      </div>

      {loading ? (
        <div className="buyer-intel-state">
          <Loader2 className="spin" size={16} aria-hidden="true" />
          <span>Checking buyer history...</span>
        </div>
      ) : null}

      {error ? (
        <div className="buyer-intel-error">
          <AlertTriangle size={16} aria-hidden="true" />
          <span>{error}</span>
        </div>
      ) : null}

      {!loading && !error && !intelligence ? <p className="muted">No buyer intelligence loaded yet.</p> : null}

      {intelligence ? (
        <div className="buyer-intel-content">
          <div className="buyer-metrics">
            <BuyerMetric label="Buyer opportunities" value={String(intelligence.buyer_opportunity_count)} />
            <BuyerMetric label="KIMDIS history" value={String(intelligence.history_opportunity_count)} detail={kimdisHistoryRangeLabel(intelligence)} />
            <BuyerMetric label="Typical budget" value={intelligence.budget_profile.typical_range} />
            <BuyerMetric label="Small software" value={String(intelligence.small_software_count)} />
            <BuyerMetric label="Similar past work" value={intelligence.has_similar_procurement ? 'Yes' : 'Not found'} />
          </div>

          {intelligence.insight_flags.length ? (
            <div className="buyer-flags">
              {intelligence.insight_flags.map((flag) => (
                <span key={flag}>{flag}</span>
              ))}
            </div>
          ) : null}

          <BuyerIntelligenceGraph intelligence={intelligence} onPreview={setPreview} />

          <div className="buyer-ai-context-note">
            <DatabaseZap size={15} aria-hidden="true" />
            <span><strong>Shared AI context</strong> Το σχετικό subset των τελευταίων 12 μηνών χρησιμοποιείται από Decision Brief και Ask AI. Εμφανίζεται μόνο εδώ για να μην διπλασιάζεται.</span>
          </div>

          <div className="buyer-intel-grid">
            <BuyerSampleList title="Recent visible opportunities" items={intelligence.recent_opportunities} onPreview={setPreview} />
            <BuyerSampleList title="Similar procurements" items={intelligence.similar_opportunities} empty="No similar procurement found in visible or KIMDIS historical records." onPreview={setPreview} />
          </div>

          <DiavgeiaSignals intelligence={intelligence} onPreview={setPreview} />

          {intelligence.confidence_notes.length ? (
            <div className="confidence-notes">
              <h5>Confidence notes</h5>
              <ul>
                {intelligence.confidence_notes.map((note) => (
                  <li key={note}>{note}</li>
                ))}
              </ul>
            </div>
          ) : null}
        </div>
      ) : null}
      {preview ? <PdfPreviewModal preview={preview} onClose={() => setPreview(null)} /> : null}
    </section>
  )
}

type BuyerGraphNode = {
  id: string
  label: string
  kindLabel: string
  amount?: string | null
  source?: string | null
  date?: string | null
  detail?: string | null
  tooltip: string
  url?: string | null
  tone: 'buyer' | 'recent' | 'similar' | 'signal'
  icon: LucideIcon
}

function BuyerIntelligenceGraph({ intelligence, onPreview }: { intelligence: BuyerIntelligenceResponse; onPreview: (preview: PdfPreview) => void }) {
  const nodes = buildBuyerGraphNodes(intelligence)
  const rootNode = nodes.find((node) => node.tone === 'buyer')
  const procurementNodes = nodes.filter((node) => node.tone === 'recent' || node.tone === 'similar')
  const signalNodes = nodes.filter((node) => node.tone === 'signal')
  const linkedCount = procurementNodes.length + signalNodes.length

  if (!rootNode) {
    return null
  }

  return (
    <div className="buyer-graph-block">
      <div className="buyer-graph-header">
        <div>
          <h5><Target size={15} aria-hidden="true" /> Buyer relationship map</h5>
          <p>Only verified procurement relationships — keywords and company names are shown as context, not as signals.</p>
        </div>
        <span className="buyer-graph-count">{linkedCount} linked {linkedCount === 1 ? 'record' : 'records'}</span>
      </div>
      <div className="buyer-graph-legend" aria-label="Relationship map legend">
        <span><i className="buyer" /> Buyer</span>
        <span><i className="similar" /> Similar procurement</span>
        <span><i className="signal" /> Award evidence</span>
      </div>
      <div className="buyer-graph-canvas" aria-label="Buyer intelligence graph">
        <div className="buyer-graph-origin">
          <span className="buyer-graph-origin-label">Buyer profile</span>
          <BuyerGraphNodeView node={rootNode} onPreview={onPreview} />
        </div>
        <div className="buyer-graph-relations">
          <BuyerGraphLane label="Similar procurements" tone="similar" nodes={procurementNodes} onPreview={onPreview} />
          <BuyerGraphLane label="Award & winner evidence" tone="signal" nodes={signalNodes} onPreview={onPreview} />
          {!linkedCount ? <p className="buyer-graph-empty">No category-matched relationships were found for this buyer.</p> : null}
        </div>
      </div>
    </div>
  )
}

function BuyerGraphLane({
  label,
  tone,
  nodes,
  onPreview,
}: {
  label: string
  tone: 'similar' | 'signal'
  nodes: BuyerGraphNode[]
  onPreview: (preview: PdfPreview) => void
}) {
  if (!nodes.length) return null
  return (
    <div className={`buyer-graph-lane ${tone}`}>
      <div className="buyer-graph-lane-header"><span><i />{label}</span><b>{nodes.length}</b></div>
      <div className="buyer-graph-lane-list">
        {nodes.map((node) => <BuyerGraphNodeView node={node} onPreview={onPreview} key={node.id} />)}
      </div>
    </div>
  )
}

function BuyerGraphNodeView({ node, onPreview }: { node: BuyerGraphNode; onPreview: (preview: PdfPreview) => void }) {
  const Icon = node.icon
  const previewMeta = [node.source, node.amount, node.date, node.detail].filter(Boolean).join(' · ')
  const content = (
    <>
      <span className="buyer-graph-node-icon">
        <Icon size={16} aria-hidden="true" />
      </span>
      <span className="buyer-graph-node-content">
        <span className="buyer-graph-node-topline">
          <span className="buyer-graph-node-kind">{node.kindLabel}</span>
          {node.url ? <ArrowUpRight size={14} aria-hidden="true" /> : null}
        </span>
        <strong>{node.label}</strong>
        <span className="buyer-graph-node-facts">
          {node.amount ? <b>{node.amount}</b> : null}
          {[node.source, node.date, node.detail].filter(Boolean).map((item) => <small key={item}>{item}</small>)}
        </span>
      </span>
    </>
  )

  const previewableNodeUrl = isPreviewableFileUrl(node.url) ? node.url : null
  if (previewableNodeUrl) {
    return (
      <button
        className={`buyer-graph-node ${node.tone}`}
        type="button"
        aria-label={`Open ${node.label}`}
        data-tooltip={node.tooltip}
        title={node.tooltip}
        onClick={() => onPreview(previewFromUrl(node.label, previewableNodeUrl, previewMeta))}
      >
        {content}
      </button>
    )
  }

  if (node.url) {
    return (
      <a
        className={`buyer-graph-node ${node.tone}`}
        href={node.url}
        target="_blank"
        rel="noreferrer"
        aria-label={`Open ${node.label}`}
        data-tooltip={node.tooltip}
        title={node.tooltip}
      >
        {content}
      </a>
    )
  }

  return (
    <div className={`buyer-graph-node ${node.tone} disabled`} aria-disabled="true" data-tooltip={node.tooltip} title={node.tooltip}>
      {content}
    </div>
  )
}

function buildBuyerGraphNodes(intelligence: BuyerIntelligenceResponse): BuyerGraphNode[] {
  const relatedOpportunityNodes = intelligence.similar_opportunities
    .filter((item) => sharesCurrentCpvCategory(intelligence.current_cpv_categories, item.cpv_codes))
    .slice(0, 6)
    .map((item) => buyerOpportunityGraphNode(item, 'similar'))
  const relatedSignalNodes = (intelligence.winner_signals.length ? intelligence.winner_signals : intelligence.diavgeia_decisions)
    .filter((decision) => sharesCurrentCpvCategory(intelligence.current_cpv_categories, decision.cpv_codes))
    .slice(0, 3)
    .map((decision, index) => buyerDecisionGraphNode(decision, index))
  const nodes: BuyerGraphNode[] = [
    {
      id: 'buyer-root',
      label: intelligence.buyer,
      kindLabel: 'Buyer',
      amount: intelligence.budget_profile.typical_range,
      detail: `${intelligence.buyer_opportunity_count} opportunities`,
      tooltip: [
        `Buyer: ${intelligence.buyer}`,
        `Buyer opportunities: ${intelligence.buyer_opportunity_count}`,
        `Visible in current window: ${intelligence.visible_buyer_opportunity_count}`,
        `KIMDIS history: ${intelligence.history_opportunity_count}`,
        `Typical budget: ${intelligence.budget_profile.typical_range}`,
        `Related graph nodes: ${relatedOpportunityNodes.length + relatedSignalNodes.length}`,
      ].join('\n'),
      tone: 'buyer',
      icon: Building2,
    },
  ]

  return [...nodes, ...relatedOpportunityNodes, ...relatedSignalNodes].slice(0, 10)
}

function buyerDecisionGraphNode(decision: DiavgeiaDecisionSignal, index: number): BuyerGraphNode {
  return {
    id: `signal-${decision.ada ?? decision.url ?? decision.document_url ?? index}`,
    label: decision.subject,
    kindLabel: 'Award evidence',
    amount: decision.amount ? formatCurrency(decision.amount) : null,
    source: decision.source_label,
    date: decision.published_at ? formatDate(decision.published_at) : null,
    detail: decision.winner_name ? `Awarded supplier · ${decision.winner_name}` : decision.decision_type ?? 'Winner signal',
    tooltip: [
      `Title: ${decision.subject}`,
      `Source: ${decision.source_label}`,
      decision.ada ? `Reference: ${decision.ada}` : null,
      decision.decision_type ? `Decision type: ${decision.decision_type}` : null,
      decision.winner_name ? `Winner: ${decision.winner_name}` : null,
      decision.amount ? `Amount: ${formatCurrency(decision.amount)}` : null,
      decision.published_at ? `Published: ${formatDate(decision.published_at)}` : null,
      decision.cpv_codes.length ? `CPV: ${decision.cpv_codes.join(', ')}` : null,
      decision.document_url ?? decision.url ? `Link: ${decision.document_url ?? decision.url}` : null,
    ].filter(Boolean).join('\n'),
    url: decision.document_url ?? decision.url,
    tone: 'signal',
    icon: ShieldCheck,
  }
}

function buyerOpportunityGraphNode(item: BuyerOpportunitySample, tone: 'recent' | 'similar'): BuyerGraphNode {
  const category = buyerOpportunityTag(item)
  return {
    id: `opportunity-${item.id}`,
    label: item.title,
    kindLabel: tone === 'similar' ? 'Similar procurement' : 'Recent procurement',
    amount: item.budget != null ? formatCurrency(item.budget) : null,
    source: item.source_label,
    date: item.published_at ? formatDate(item.published_at) : null,
    detail: category,
    tooltip: [
      `Title: ${item.title}`,
      `Source: ${item.source_label}`,
      `Category: ${category}`,
      item.budget ? `Budget: ${formatCurrency(item.budget)}` : null,
      item.published_at ? `Published: ${formatDate(item.published_at)}` : null,
      item.deadline ? `Deadline: ${formatDate(item.deadline)}` : null,
      item.cpv_codes.length ? `CPV: ${item.cpv_codes.join(', ')}` : null,
      `Fit score: ${item.fit_score}`,
      item.url ? `Link: ${item.url}` : null,
    ].filter(Boolean).join('\n'),
    url: item.url,
    tone,
    icon: tone === 'similar' ? Layers3 : FileText,
  }
}

function buyerOpportunityTag(item: BuyerOpportunitySample): string {
  const broadTag = broadProcurementTag(item.cpv_codes, item.title)
  if (!item.package_match || item.package_match === 'Custom software') {
    return broadTag === 'Software' ? 'Custom software' : broadTag
  }
  if (broadTag !== 'Software' && item.package_match.toLowerCase().includes('software')) {
    return broadTag
  }
  return item.package_match
}

function broadProcurementTag(cpvCodes: string[], title = ''): string {
  const categoryLabels: Record<string, string> = {
    software: 'Software',
    'food-catering': 'Food / catering',
    'it-equipment-maintenance': 'IT equipment / maintenance',
    'transport-logistics': 'Transport / logistics',
    'security-defence': 'Security / defence',
    'laboratory-measurement': 'Laboratory / measurement',
    'furniture-facilities': 'Furniture / facilities',
    'industrial-equipment': 'Industrial equipment',
    'construction-works': 'Construction / works',
    'financial-insurance': 'Financial / insurance',
    'engineering-technical': 'Engineering / technical',
    'research-consulting': 'Research / consulting',
    'business-services': 'Business services',
    'training-education': 'Training / education',
    'health-social-care': 'Health / social care',
    'waste-environment': 'Waste / environment',
    'culture-recreation': 'Culture / recreation',
  }
  const category = cpvCategoryKeys(cpvCodes)[0]
  if (category) {
    return categoryLabels[category] ?? 'Other procurement'
  }
  const loweredTitle = title.toLocaleLowerCase('el-GR')
  if (['σαλάτ', 'salad', 'τρόφι', 'τροφ', 'φαγη', 'σίτιση', 'catering'].some((term) => loweredTitle.includes(term))) {
    return 'Food / catering'
  }
  return 'Other procurement'
}

function sharesCurrentCpvCategory(currentCategories: string[], cpvCodes: string[]): boolean {
  if (!currentCategories.length) {
    return false
  }
  const itemCategories = cpvCategoryKeys(cpvCodes)
  return currentCategories.some((category) => itemCategories.includes(category))
}

function cpvCategoryKeys(cpvCodes: string[]): string[] {
  const categoryPrefixes: Array<[string, string[]]> = [
    ['software', ['48', '72']],
    ['food-catering', ['15', '55']],
    ['it-equipment-maintenance', ['30', '32', '50']],
    ['transport-logistics', ['34', '60', '63']],
    ['security-defence', ['35']],
    ['laboratory-measurement', ['38']],
    ['furniture-facilities', ['39']],
    ['industrial-equipment', ['42', '43']],
    ['construction-works', ['44', '45']],
    ['financial-insurance', ['66']],
    ['engineering-technical', ['71']],
    ['research-consulting', ['73']],
    ['business-services', ['79']],
    ['training-education', ['80']],
    ['health-social-care', ['85']],
    ['waste-environment', ['90']],
    ['culture-recreation', ['92']],
  ]
  const prefixes = cpvCodes.map((code) => cpvDigits(code).slice(0, 2)).filter(Boolean)
  return categoryPrefixes
    .filter(([, candidates]) => prefixes.some((prefix) => candidates.includes(prefix)))
    .map(([category]) => category)
}

function cpvDigits(code: string): string {
  return code.replace(/\D/g, '')
}

function BuyerMetric({ label, value, detail }: { label: string; value: string; detail?: string | null }) {
  return (
    <div className="buyer-metric">
      <span>{label}</span>
      <strong>{value}</strong>
      {detail ? <small>{detail}</small> : null}
    </div>
  )
}

function kimdisHistoryRangeLabel(intelligence: BuyerIntelligenceResponse): string | null {
  const searchRange = dateRangeLabel(intelligence.khmdhs_history_date_from, intelligence.khmdhs_history_date_to)
  const resultRange = dateRangeLabel(intelligence.khmdhs_history_result_date_from, intelligence.khmdhs_history_result_date_to)
  if (searchRange && resultRange && searchRange !== resultRange) {
    return `Search ${searchRange} · Returned ${resultRange}`
  }
  if (searchRange) {
    return `Search ${searchRange}`
  }
  if (resultRange) {
    return `Returned ${resultRange}`
  }
  return null
}

function dateRangeLabel(from?: string | null, to?: string | null): string | null {
  if (!from && !to) {
    return null
  }
  if (from && to) {
    return `${formatDate(from)} - ${formatDate(to)}`
  }
  return formatDate(from ?? to)
}

function BuyerSampleList({
  title,
  items,
  empty = 'No visible opportunities.',
  onPreview,
}: {
  title: string
  items: BuyerOpportunitySample[]
  empty?: string
  onPreview: (preview: PdfPreview) => void
}) {
  return (
    <div className="buyer-list-block">
      <div className="buyer-list-heading"><h5>{title}</h5><span>{items.length}</span></div>
      {items.length ? (
        <div className="buyer-sample-list">
          {items.map((item) => {
            const meta = [item.source_label, formatCurrency(item.budget), item.published_at ? formatDate(item.published_at) : null, buyerOpportunityTag(item)].filter(Boolean).join(' · ')
            const content = (
              <>
                <span className="buyer-sample-topline">
                  <span className="buyer-sample-source">{item.source_label}</span>
                  {item.published_at ? <time>{formatDate(item.published_at)}</time> : null}
                </span>
                <strong>{item.title}</strong>
                <span className="buyer-sample-footer">
                  <span className="buyer-sample-category">{buyerOpportunityTag(item)}</span>
                  {item.budget != null ? <b className="money-badge"><CircleDollarSign size={13} aria-hidden="true" />{formatCurrency(item.budget)}</b> : <small>Budget unavailable</small>}
                  {item.url ? <ArrowUpRight className="buyer-sample-arrow" size={15} aria-hidden="true" /> : null}
                </span>
              </>
            )
            const previewableItemUrl = isPreviewableFileUrl(item.url) ? item.url : null
            if (previewableItemUrl) {
              return (
                <button className="buyer-sample" type="button" key={item.id} onClick={() => onPreview(previewFromUrl(item.title, previewableItemUrl, meta))}>
                  {content}
                </button>
              )
            }
            if (item.url) {
              return (
                <a className="buyer-sample" href={item.url} target="_blank" rel="noreferrer" key={item.id}>
                  {content}
                </a>
              )
            }
            return (
              <div className="buyer-sample disabled" key={item.id}>
                {content}
              </div>
            )
          })}
        </div>
      ) : (
        <p className="muted">{empty}</p>
      )}
    </div>
  )
}

function DiavgeiaSignals({ intelligence, onPreview }: { intelligence: BuyerIntelligenceResponse; onPreview: (preview: PdfPreview) => void }) {
  const signals = intelligence.winner_signals.length ? intelligence.winner_signals : intelligence.diavgeia_decisions.slice(0, 3)
  return (
    <div className="diavgeia-block">
      <div className="buyer-list-heading"><h5>Awards & awarded suppliers</h5><span>{signals.length}</span></div>
      {intelligence.khmdhs_history_message ? <p className="muted">{intelligence.khmdhs_history_message}</p> : null}
      {intelligence.diavgeia_message ? <p className="muted">{intelligence.diavgeia_message}</p> : null}
      {signals.length ? (
        <div className="diavgeia-list">
          {signals.map((decision) => {
            const href = decision.document_url ?? decision.url
            const amountLabel = decision.amount ? formatCurrency(decision.amount) : null
            const projectMeta = [amountLabel, decision.published_at ? formatDate(decision.published_at) : null, decision.similar_to_software ? 'software-like' : null].filter(Boolean)
            const linkMeta = [decision.source_label, decision.ada ?? decision.decision_type ?? 'Decision', ...projectMeta].filter(Boolean).join(' · ')
            const content = (
              <>
                <div className="diavgeia-company-block">
                  <span><Award size={13} aria-hidden="true" /> Awarded supplier</span>
                  <strong>{decision.winner_name || 'Unknown winner'}</strong>
                </div>
                <div className="diavgeia-project-block">
                  <span className="diavgeia-project-topline">
                    <span>{[decision.source_label, decision.ada ?? decision.decision_type ?? 'Decision'].filter(Boolean).join(' · ')}</span>
                    {decision.published_at ? <time>{formatDate(decision.published_at)}</time> : null}
                  </span>
                  <strong>{decision.subject}</strong>
                  <span className="diavgeia-project-footer">
                    {amountLabel ? <b className="money-badge"><CircleDollarSign size={13} aria-hidden="true" />{amountLabel}</b> : <small>Amount unavailable</small>}
                    {decision.similar_to_software ? <em>Software-like</em> : null}
                    {href ? <ArrowUpRight size={15} aria-hidden="true" /> : null}
                  </span>
                </div>
              </>
            )
            if (isPreviewableFileUrl(href)) {
              return (
                <button className="diavgeia-item" type="button" key={`${decision.ada}-${decision.subject}`} onClick={() => onPreview(previewFromUrl(decision.subject, href, linkMeta))}>
                  {content}
                </button>
              )
            }
            if (!href) {
              return (
                <div className="diavgeia-item disabled" key={`${decision.ada}-${decision.subject}`}>
                  {content}
                </div>
              )
            }
            return (
              <a className="diavgeia-item" href={href} target="_blank" rel="noreferrer" key={`${decision.ada}-${decision.subject}`}>
                {content}
              </a>
            )
          })}
        </div>
      ) : (
        <p className="muted">No award/winner signal returned from KIMDIS or Diavgeia for this lookup.</p>
      )}
    </div>
  )
}

export function DocumentBriefPanel({
  source,
  reference,
  availableDocumentCount,
  brief,
  outdated,
  loading,
  generating,
  error,
  aiModels,
  selectedAiModel,
  onSelectAiModel,
  canGenerate,
  onGenerate,
}: {
  source: SourceName
  reference: string
  availableDocumentCount: number
  brief: DocumentBrief | null
  outdated: boolean
  loading: boolean
  generating: boolean
  error: string | null
  aiModels: AIModelOption[]
  selectedAiModel: string
  onSelectAiModel: (model: string) => void
  canGenerate: boolean
  onGenerate: () => void
}) {
  const ActionIcon = generating ? Loader2 : Sparkles
  const [activeTab, setActiveTab] = useState<'brief' | 'chat'>('brief')
  const [preview, setPreview] = useState<PdfPreview | null>(null)
  const selectedModelInfo = aiModels.find((model) => model.id === selectedAiModel)
  const evidenceMap = new Map((brief?.evidence ?? []).map((item) => [item.id, item]))
  const openEvidence = (evidence: BriefEvidence) => setPreview({
    title: evidence.document_label,
    url: evidence.url,
    meta: [evidence.page ? `Σελίδα ${evidence.page}` : null, evidence.reference].filter(Boolean).join(' · '),
    mode: isPreviewableFileUrl(evidence.url) ? 'document' : 'web',
  })

  return (
    <section className="drawer-section ai-brief-section">
      <div className="ai-brief-header">
        <div className="ai-brief-title">
          <span className="ai-brief-title-icon"><Sparkles size={18} aria-hidden="true" /></span>
          <div>
            <span className="section-kicker">Decision intelligence</span>
            <h4>Opportunity AI</h4>
            <p>Decision brief και τεκμηριωμένες ερωτήσεις στο ίδιο context.</p>
          </div>
        </div>
        <div className="ai-model-controls">
          <label>
            <span>Model · Brief & Chat</span>
            <select value={selectedAiModel} onChange={(event) => onSelectAiModel(event.target.value)} disabled={generating} aria-label="AI model for Decision Brief and Ask AI">
              {aiModels.map((model) => <option value={model.id} key={model.id}>{model.label}{model.recommended ? ' · Recommended' : ''}</option>)}
            </select>
            {selectedModelInfo ? <small>{selectedModelInfo.quality} · {selectedModelInfo.description}</small> : null}
          </label>
          {activeTab === 'brief' ? (
            <button className="ai-brief-button" type="button" onClick={onGenerate} disabled={!canGenerate || generating}>
              <ActionIcon className={generating ? 'spin' : undefined} size={16} aria-hidden="true" />
              {generating ? 'Reading documents…' : brief ? 'Regenerate' : 'Generate brief'}
            </button>
          ) : null}
        </div>
      </div>

      <div className="ai-workspace-tabs" role="tablist" aria-label="Opportunity AI views">
        <button type="button" role="tab" aria-selected={activeTab === 'brief'} className={activeTab === 'brief' ? 'active' : undefined} onClick={() => setActiveTab('brief')}>
          <Sparkles size={15} aria-hidden="true" /> Decision Brief
        </button>
        <button type="button" role="tab" aria-selected={activeTab === 'chat'} className={activeTab === 'chat' ? 'active' : undefined} onClick={() => setActiveTab('chat')}>
          <MessageSquare size={15} aria-hidden="true" /> Ask AI
        </button>
      </div>

      {activeTab === 'brief' && loading ? (
        <div className="ai-brief-state">
          <Loader2 className="spin" size={16} aria-hidden="true" />
          <span>Checking saved brief...</span>
        </div>
      ) : null}

      {activeTab === 'brief' && error ? (
        <div className="ai-brief-error">
          <AlertTriangle size={16} aria-hidden="true" />
          <span>{error}</span>
        </div>
      ) : null}

      {activeTab === 'brief' && !loading && !brief ? (
        <p className="muted">Δεν υπάρχει αποθηκευμένο brief. Πάτησε Generate για ανάλυση των επίσημων εγγράφων.</p>
      ) : null}

      {activeTab === 'brief' && brief ? (
        <div className="ai-brief-content bid-scorecard">
          {outdated ? (
            <div className="brief-outdated-banner">
              <AlertTriangle size={16} aria-hidden="true" />
              <span>Outdated brief — πάτησε Regenerate για το νέο scorecard και τα evidence citations.</span>
            </div>
          ) : null}

          <div className={`brief-decision-hero ${briefVerdictClass(brief.verdict)}`}>
            <div
              className="brief-score-ring"
              aria-label={`Bid score ${brief.score} out of 100`}
              style={{ '--brief-score': `${brief.score * 3.6}deg` } as CSSProperties}
            >
              <strong>{brief.score}</strong>
              <span>/100</span>
            </div>
            <div>
              <span className="brief-decision-label">Decision</span>
              <h5>{brief.verdict}</h5>
              <p>{brief.executive_recommendation}</p>
            </div>
            <span className={`brief-confidence ${brief.confidence}`}>{brief.confidence} confidence</span>
          </div>

          <p>{brief.project_summary}</p>

          <details className="brief-source-coverage">
            <summary>
              <span><FileText size={15} aria-hidden="true" /> Αναλύθηκαν {brief.source_documents.length} από {availableDocumentCount} διαθέσιμα documents</span>
              <ChevronDown size={16} aria-hidden="true" />
            </summary>
            <div>
              {brief.source_documents.length ? brief.source_documents.map((document, index) => (
                <a href={document.url} target="_blank" rel="noreferrer" key={`${document.url}-${index}`}>
                  <span>{index + 1}</span>
                  <b>{document.label}</b>
                  <small>{[document.document_type, document.reference].filter(Boolean).join(' · ')}</small>
                  <ExternalLink size={14} aria-hidden="true" />
                </a>
              )) : <p>Δεν αναλύθηκε αναγνώσιμο source document.</p>}
            </div>
          </details>

          <BriefFindingList title="Γιατί αυτή η απόφαση" findings={brief.decision_reasons} evidenceMap={evidenceMap} onEvidence={openEvidence} />

          <div className="brief-decision-grid">
            <article className={`brief-fact-card access-${brief.procurement_access.status}`}>
              <div className="brief-fact-heading"><span><Target size={16} aria-hidden="true" /></span><small>Πρόσβαση στη διαδικασία</small></div>
              <strong>{formatAccessStatus(brief.procurement_access.status)}</strong>
              <p>{brief.procurement_access.reason}</p>
              <BriefEvidenceChips ids={brief.procurement_access.evidence_ids} evidenceMap={evidenceMap} onEvidence={openEvidence} />
            </article>
            <article className="brief-fact-card">
              <div className="brief-fact-heading"><span><CircleDollarSign size={16} aria-hidden="true" /></span><small>Budget & direct award</small></div>
              <strong className="brief-money">{brief.budget_assessment.amount_without_vat != null ? formatCurrency(brief.budget_assessment.amount_without_vat) : 'Unknown net budget'}</strong>
              {brief.budget_assessment.amount_without_vat != null ? <small className="brief-money-note">Καθαρή αξία · χωρίς ΦΠΑ</small> : null}
              <p>{brief.budget_assessment.determination}</p>
              <BriefEvidenceChips ids={brief.budget_assessment.evidence_ids} evidenceMap={evidenceMap} onEvidence={openEvidence} />
              <a href={brief.budget_assessment.legal_basis_url} target="_blank" rel="noreferrer">Ν. 4412/2016 · {brief.rules_version}</a>
            </article>
            <article className={`brief-fact-card continuity-${brief.continuity.status}`}>
              <div className="brief-fact-heading"><span><Handshake size={16} aria-hidden="true" /></span><small>Incumbent / συνέχεια</small></div>
              <strong>{formatContinuityStatus(brief.continuity.status)}</strong>
              <p>{brief.continuity.reason}</p>
              {brief.continuity.incumbent_name ? <small>Incumbent: {brief.continuity.incumbent_name}</small> : null}
              {brief.continuity.prior_reference ? <small>Previous ref: {brief.continuity.prior_reference}</small> : null}
              <BriefEvidenceChips ids={brief.continuity.evidence_ids} evidenceMap={evidenceMap} onEvidence={openEvidence} />
            </article>
          </div>

          <div className="brief-access-strip">
            <span><i><CalendarClock size={16} aria-hidden="true" /></i><b><strong>Deadline</strong>{brief.procurement_access.deadline ? `${formatDate(brief.procurement_access.deadline)}${brief.procurement_access.days_remaining != null ? ` · ${brief.procurement_access.days_remaining} ημέρες` : ''}` : 'Unknown'}</b></span>
            <span><i><Layers3 size={16} aria-hidden="true" /></i><b><strong>Procedure</strong>{brief.procurement_access.procedure || 'Unknown'}</b></span>
            <span><i><FileText size={16} aria-hidden="true" /></i><b><strong>Submission</strong>{brief.procurement_access.submission_method || 'Unknown'}</b></span>
          </div>

          <details className="brief-compact-disclosure brief-score-disclosure">
            <summary>
              <span className="brief-disclosure-copy"><strong>Bid score breakdown</strong><small>6 weighted factors · click για λεπτομέρειες</small></span>
              <span className="brief-mini-score" aria-label="Compact bid score dimensions">
                {brief.score_dimensions.map((dimension) => (
                  <i key={dimension.key} title={`${dimension.label}: ${dimension.score}/${dimension.max_score}`}>
                    <b style={{ width: `${dimension.max_score ? (dimension.score / dimension.max_score) * 100 : 0}%` }} />
                  </i>
                ))}
              </span>
              <b className="brief-summary-total">{brief.score}<small>/100</small></b>
              <ChevronDown size={17} aria-hidden="true" />
            </summary>
            <div className="brief-score-dimensions" aria-label="Bid score dimensions">
              {brief.score_dimensions.map((dimension) => (
                <div className="brief-score-dimension" key={dimension.key}>
                  <div><strong>{dimension.label}</strong><span className="brief-dimension-score">{dimension.score}<small>/{dimension.max_score}</small></span></div>
                  <div className="brief-score-track" role="progressbar" aria-label={dimension.label} aria-valuenow={dimension.score} aria-valuemin={0} aria-valuemax={dimension.max_score}><span style={{ width: `${dimension.max_score ? (dimension.score / dimension.max_score) * 100 : 0}%` }} /></div>
                  <p>{dimension.reason}</p>
                  <BriefEvidenceChips ids={dimension.evidence_ids} evidenceMap={evidenceMap} onEvidence={openEvidence} />
                </div>
              ))}
            </div>
          </details>

          <details className="brief-compact-disclosure">
            <summary>
              <span className="brief-disclosure-copy"><strong>Findings by topic</strong><small>Επιβεβαιωμένα, ελλείψεις και κίνδυνοι — όχι ξεχωριστά documents</small></span>
              <span className="brief-topic-count">6 topics</span>
              <ChevronDown size={17} aria-hidden="true" />
            </summary>
            <div className="brief-grid brief-v2-grid">
              <BriefFindingList title="Commercial" findings={brief.commercial_findings} evidenceMap={evidenceMap} onEvidence={openEvidence} empty="Δεν επιβεβαιώθηκαν εμπορικοί όροι." />
              <BriefFindingList title="Eligibility & δικαιολογητικά" findings={brief.eligibility_requirements} fallback={brief.required_documents} evidenceMap={evidenceMap} onEvidence={openEvidence} />
              <BriefFindingList title="Evaluation criteria" findings={brief.evaluation_criteria} evidenceMap={evidenceMap} onEvidence={openEvidence} />
              <BriefFindingList title="Technical & deliverables" findings={brief.technical_findings} fallback={brief.technical_requirements} evidenceMap={evidenceMap} onEvidence={openEvidence} />
              <BriefFindingList title="Contract, SLA & guarantees" findings={brief.contractual_findings} evidenceMap={evidenceMap} onEvidence={openEvidence} />
              <BriefFindingList title="Red flags" findings={brief.red_flag_findings} fallback={brief.red_flags} evidenceMap={evidenceMap} onEvidence={openEvidence} tone="risk" />
            </div>
          </details>

          <details className="brief-compact-disclosure">
            <summary>
              <span className="brief-disclosure-copy"><strong>Open questions & next steps</strong><small>{brief.unknowns.length} unknowns · {brief.next_steps.length} actions</small></span>
              <ChevronDown size={17} aria-hidden="true" />
            </summary>
            <div className="brief-lists-row">
              <BriefPlainList title="Unknown / χρειάζεται επιβεβαίωση" items={brief.unknowns} />
              <BriefPlainList title="Next steps" items={brief.next_steps} />
            </div>
          </details>

          <div className="brief-meta">
            <span>{brief.cached ? 'Saved brief' : 'New brief'}</span>
            <span>Schema v{brief.schema_version}</span>
            <span>{formatDateTime(brief.generated_at)}</span>
            {brief.model ? <span>{brief.model}</span> : null}
          </div>
        </div>
      ) : null}
      {activeTab === 'chat' ? <OpportunityChatPanel source={source} reference={reference} model={selectedAiModel} /> : null}
      {preview ? <PdfPreviewModal preview={preview} onClose={() => setPreview(null)} /> : null}
    </section>
  )
}

export function OpportunityChatPanel({ source, reference, model }: { source: SourceName; reference: string; model: string }) {
  const [thread, setThread] = useState<OpportunityChatThreadResponse | null>(null)
  const [draft, setDraft] = useState('')
  const [loading, setLoading] = useState(Boolean(reference))
  const [sending, setSending] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [clearing, setClearing] = useState(false)
  const [error, setError] = useState<string | null>(reference ? null : 'Δεν υπάρχει source reference για αυτό το opportunity.')
  const [failedMessage, setFailedMessage] = useState<string | null>(null)
  const [preview, setPreview] = useState<PdfPreview | null>(null)

  useEffect(() => {
    let cancelled = false
    if (!reference) {
      return () => { cancelled = true }
    }
    void fetch(`${API_BASE}/api/opportunities/${source}/${encodeURIComponent(reference)}/chat`)
      .then(async (response) => {
        if (!response.ok) throw new Error(await opportunityChatApiError(response))
        return response.json() as Promise<OpportunityChatThreadResponse>
      })
      .then((data) => { if (!cancelled) setThread(data) })
      .catch((exc) => { if (!cancelled) setError(exc instanceof Error ? exc.message : 'Chat history could not be loaded.') })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [source, reference])

  const sendQuestion = async (question: string) => {
    const nextMessage = question.trim()
    if (!nextMessage || !reference || sending) return
    setSending(true)
    setError(null)
    setFailedMessage(null)
    try {
      const response = await fetch(`${API_BASE}/api/opportunities/${source}/${encodeURIComponent(reference)}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: nextMessage, model }),
      })
      if (!response.ok) throw new Error(await opportunityChatApiError(response))
      const data = (await response.json()) as OpportunityChatTurnResponse
      setThread((current) => ({
        messages: [...(current?.messages ?? []), data.user_message, data.assistant_message].slice(-100),
        context: data.context,
        suggested_questions: data.assistant_message.suggested_questions,
      }))
      setDraft('')
    } catch (exc) {
      setFailedMessage(nextMessage)
      setError(exc instanceof Error ? exc.message : 'Η απάντηση δεν ολοκληρώθηκε. Το μήνυμα διατηρήθηκε για retry.')
    } finally {
      setSending(false)
    }
  }

  const refreshContext = async () => {
    if (!reference || refreshing) return
    setRefreshing(true)
    setError(null)
    try {
      const response = await fetch(`${API_BASE}/api/opportunities/${source}/${encodeURIComponent(reference)}/chat/context/refresh`, { method: 'POST' })
      if (!response.ok) throw new Error(await opportunityChatApiError(response))
      const context = (await response.json()) as OpportunityChatContextStatus
      setThread((current) => ({ messages: current?.messages ?? [], context, suggested_questions: current?.suggested_questions ?? [] }))
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : 'Το context δεν ανανεώθηκε.')
    } finally {
      setRefreshing(false)
    }
  }

  const clearChat = async () => {
    if (!reference || clearing || !window.confirm('Να διαγραφεί ολόκληρη η αποθηκευμένη συνομιλία για αυτό το opportunity;')) return
    setClearing(true)
    setError(null)
    try {
      const response = await fetch(`${API_BASE}/api/opportunities/${source}/${encodeURIComponent(reference)}/chat`, { method: 'DELETE' })
      if (!response.ok) throw new Error(await opportunityChatApiError(response))
      setThread((current) => ({
        messages: [],
        context: current?.context ?? emptyChatContext(),
        suggested_questions: initialOpportunityQuestions,
      }))
      setDraft('')
      setFailedMessage(null)
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : 'Η συνομιλία δεν διαγράφηκε.')
    } finally {
      setClearing(false)
    }
  }

  const openCitation = (citation: OpportunityChatCitation) => {
    if (!citation.url) return
    setPreview({
      title: citation.label,
      url: citation.url,
      meta: [citation.kind === 'history' ? '12μηνο buyer history' : citation.page ? `Σελίδα ${citation.page}` : 'Evidence', citation.reference].filter(Boolean).join(' · '),
      mode: isPreviewableFileUrl(citation.url) ? 'document' : 'web',
    })
  }

  const messages = thread?.messages ?? []
  const suggestions = (messages.length ? messages[messages.length - 1]?.suggested_questions : thread?.suggested_questions)?.slice(0, 3) ?? initialOpportunityQuestions
  const context = thread?.context ?? emptyChatContext()

  return (
    <div className="opportunity-chat">
      <div className="chat-context-bar">
        <span className={context.ready ? 'ready' : undefined}><DatabaseZap size={15} aria-hidden="true" />
          {context.ready ? `${context.readable_document_count} readable · ${context.analyzed_document_count}/${context.available_document_count} analyzed` : 'Το context θα δημιουργηθεί με την πρώτη ερώτηση'}
        </span>
        {context.unreadable_document_labels.length ? <span className="chat-context-warning" title={context.unreadable_document_labels.join('\n')}><AlertTriangle size={14} aria-hidden="true" /> {context.unreadable_document_labels.length} unreadable / scanned</span> : null}
        <div>
          <button type="button" onClick={() => void refreshContext()} disabled={refreshing || sending} title="Refresh source context"><RefreshCw className={refreshing ? 'spin' : undefined} size={15} aria-hidden="true" /> Refresh context</button>
          <button type="button" onClick={() => void clearChat()} disabled={clearing || !messages.length} title="Clear saved chat"><Trash2 size={15} aria-hidden="true" /> Clear</button>
        </div>
      </div>

      {loading ? <div className="chat-loading"><Loader2 className="spin" size={18} aria-hidden="true" /> Loading saved conversation…</div> : null}
      {!loading && !messages.length ? (
        <div className="chat-empty-state">
          <span><Bot size={22} aria-hidden="true" /></span>
          <div><h5>Ρώτησε για αυτό το opportunity</h5><p>Δεν χρειάζεται να δημιουργήσεις πρώτα Decision Brief. Οι απαντήσεις χρησιμοποιούν τα επίσημα documents και το σχετικό 12μηνο buyer history.</p></div>
        </div>
      ) : null}

      <div className="chat-messages" aria-live="polite">
        {messages.map((message) => (
          <article className={`chat-message ${message.role}`} key={message.id}>
            <span className="chat-avatar">{message.role === 'assistant' ? <Bot size={16} aria-hidden="true" /> : <UserRound size={16} aria-hidden="true" />}</span>
            <div className="chat-bubble">
              <p>{message.content}</p>
              {message.citations.length ? (
                <div className="chat-citations">
                  {message.citations.map((citation) => citation.url ? (
                    <button type="button" key={citation.id} onClick={() => openCitation(citation)} title={citation.excerpt ?? citation.label}>
                      {citation.kind === 'history' ? <DatabaseZap size={12} aria-hidden="true" /> : <FileText size={12} aria-hidden="true" />}
                      {citation.kind === 'history' ? 'History' : citation.page ? `p.${citation.page}` : 'Evidence'} · {citation.label}
                    </button>
                  ) : (
                    <span key={citation.id}>{citation.kind === 'history' ? 'History' : 'Evidence'} · {citation.label}</span>
                  ))}
                </div>
              ) : null}
              {message.strategic_advice ? (
                <aside className="chat-strategic-take"><Sparkles size={15} aria-hidden="true" /><span><strong>Strategic take</strong>{message.strategic_advice}</span></aside>
              ) : null}
              <footer>{message.model ? <span>{message.model}</span> : null}<time>{formatDateTime(message.created_at)}</time></footer>
            </div>
          </article>
        ))}
        {sending ? <article className="chat-message assistant"><span className="chat-avatar"><Bot size={16} /></span><div className="chat-bubble chat-thinking"><Loader2 className="spin" size={15} /> Reading evidence and preparing a cited answer…</div></article> : null}
      </div>

      {error ? <div className="chat-error"><AlertTriangle size={15} aria-hidden="true" /><span>{error}</span>{failedMessage ? <button type="button" onClick={() => void sendQuestion(failedMessage)}>Retry</button> : null}</div> : null}

      {suggestions.length ? <div className="chat-suggestions">{suggestions.map((question) => <button type="button" key={question} onClick={() => void sendQuestion(question)} disabled={sending}>{question}</button>)}</div> : null}

      <form className="chat-composer" onSubmit={(event: FormEvent) => { event.preventDefault(); void sendQuestion(draft) }}>
        <textarea
          value={draft}
          onChange={(event) => setDraft(event.target.value.slice(0, 4000))}
          onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); event.currentTarget.form?.requestSubmit() } }}
          placeholder="Ρώτησε για προθεσμία, τεχνικές απαιτήσεις, budget ή bid strategy…"
          rows={3}
          maxLength={4000}
          disabled={sending || !reference}
        />
        <div><span>{draft.length}/4000 · Enter για αποστολή, Shift+Enter για νέα γραμμή</span><button type="submit" disabled={sending || !draft.trim()}><Send size={16} aria-hidden="true" /> Send</button></div>
      </form>
      {preview ? <PdfPreviewModal preview={preview} onClose={() => setPreview(null)} /> : null}
    </div>
  )
}

const initialOpportunityQuestions = [
  'Μπορούμε πραγματικά να συμμετάσχουμε και ποια είναι η προθεσμία;',
  'Ποιες τεχνικές απαιτήσεις και παραδοτέα έχουν επιβεβαιωθεί;',
  'Ποιοι είναι οι βασικοί εμπορικοί κίνδυνοι πριν αποφασίσουμε;',
]

function emptyChatContext(): OpportunityChatContextStatus {
  return {
    ready: false,
    available_document_count: 0,
    analyzed_document_count: 0,
    readable_document_count: 0,
    unreadable_document_labels: [],
  }
}

async function opportunityChatApiError(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: string }
    return body.detail || `Opportunity chat API returned ${response.status}`
  } catch {
    return `Opportunity chat API returned ${response.status}`
  }
}

function BriefFindingList({
  title,
  findings,
  fallback = [],
  evidenceMap,
  onEvidence,
  empty = 'Δεν εντοπίστηκε στα αναγνώσιμα έγγραφα.',
  tone = 'default',
}: {
  title: string
  findings: BriefFinding[]
  fallback?: string[]
  evidenceMap: Map<string, BriefEvidence>
  onEvidence: (evidence: BriefEvidence) => void
  empty?: string
  tone?: 'default' | 'risk'
}) {
  return (
    <div className={`brief-block brief-finding-block ${tone}`}>
      <div className="brief-block-header"><h5>{title}</h5><span>{findings.length || fallback.filter(Boolean).length}</span></div>
      {findings.length ? (
        <ul>
          {findings.map((item) => (
            <li key={`${item.text}-${item.evidence_ids.join('-')}`}>
              <span>{item.text}</span>
              <BriefEvidenceChips ids={item.evidence_ids} evidenceMap={evidenceMap} onEvidence={onEvidence} />
            </li>
          ))}
        </ul>
      ) : fallback.filter(Boolean).length ? (
        <ul>{fallback.filter(Boolean).map((item) => <li key={item}><span>{item}</span></li>)}</ul>
      ) : (
        <p>{empty}</p>
      )}
    </div>
  )
}

function BriefEvidenceChips({ ids = [], evidenceMap, onEvidence }: { ids?: string[]; evidenceMap: Map<string, BriefEvidence>; onEvidence: (evidence: BriefEvidence) => void }) {
  const evidence = ids.map((id) => evidenceMap.get(id)).filter((item): item is BriefEvidence => Boolean(item))
  if (!evidence.length) return null
  return <span className="brief-evidence-chips">{evidence.map((item) => <button type="button" key={item.id} title={item.excerpt} onClick={() => onEvidence(item)}><FileText size={12} aria-hidden="true" />{item.page ? `p.${item.page}` : 'evidence'}</button>)}</span>
}

function BriefPlainList({ title, items }: { title: string; items: string[] }) {
  return <div className="brief-plain-list"><div className="brief-block-header"><h5>{title}</h5><span>{items.length}</span></div>{items.length ? <ul>{items.map((item) => <li key={item}>{item}</li>)}</ul> : <p>None identified.</p>}</div>
}

function briefVerdictClass(verdict: DocumentBrief['verdict']) {
  return verdict.toLowerCase().replaceAll(' ', '-').replace('conditional-go', 'conditional')
}

function formatAccessStatus(status: DocumentBrief['procurement_access']['status']) {
  return ({ open_competition: 'Open competition', named_invitation: 'Named invitation', awarded: 'Awarded', contracted: 'Contracted', paid: 'Paid', planning_only: 'Planning only', expired: 'Expired', unknown: 'Unknown' })[status]
}

function formatContinuityStatus(status: DocumentBrief['continuity']['status']) {
  return ({ confirmed_continuation: 'Confirmed continuation', not_confirmed: 'Not confirmed', unknown: 'Unknown' })[status]
}

function SourceDataVisualization({ details }: { details: OpportunityDetails | null }) {
  if (!details) {
    return <p className="muted">No source data loaded.</p>
  }

  if (details.source === 'khmdhs') {
    const metadata = asRecord(details.raw.metadata)
    const chain = asRecord(details.raw.adamChain)
    const objectDetails = Array.isArray(metadata.objectDetails) ? metadata.objectDetails : []
    const metadataCount = fieldRowCount(metadata, ['objectDetails'])
    return (
      <div className="source-visualization">
        <ChainSignalPanel chain={chain} />
        {metadataCount ? (
          <CollapsiblePanel title="KIMDIS metadata" meta={`${metadataCount} fields`}>
            <FieldTable title="KIMDIS metadata" data={metadata} skip={['objectDetails']} />
          </CollapsiblePanel>
        ) : null}
        {objectDetails.length ? (
          <CollapsiblePanel title="Object details" meta={`${objectDetails.length} records`}>
            <NestedSection title="Object details" value={objectDetails} />
          </CollapsiblePanel>
        ) : null}
      </div>
    )
  }

  if (details.source === 'ted') {
    const notice = asRecord(details.raw.notice)
    const links = asRecord(notice.links)
    return (
      <div className="source-visualization">
        <FieldTable title="TED notice fields" data={notice} skip={['links']} />
        <LinkGroups links={links} />
      </div>
    )
  }

  return <NestedSection title="Source payload" value={details.raw} />
}

function enrichOpportunityFromDetails(opportunity: Opportunity, details: OpportunityDetails): Opportunity {
  if (details.source !== 'khmdhs') {
    return opportunity
  }
  const metadata = asRecord(details.metadata)
  const rawMetadata = asRecord(asRecord(details.raw).metadata)
  const metadataOrganization = asRecord(metadata.organization)
  const rawOrganization = asRecord(rawMetadata.organization)
  const organizationKey = firstString(metadataOrganization.key, rawOrganization.key)
  if (!organizationKey) {
    return opportunity
  }
  return {
    ...opportunity,
    source_payload: {
      ...(opportunity.source_payload ?? {}),
      organizationKey,
    },
  }
}

function firstString(...values: unknown[]) {
  for (const value of values) {
    if (typeof value === 'string' && value.trim()) {
      return value.trim()
    }
    if (typeof value === 'number') {
      return String(value)
    }
  }
  return null
}

function fieldRowCount(data: Record<string, unknown>, skip: string[] = []) {
  return Object.entries(data).filter(([key, value]) => !skip.includes(key) && isUsefulValue(value)).length
}

function FieldTable({ title, data, skip = [] }: { title: string; data: Record<string, unknown>; skip?: string[] }) {
  const rows = Object.entries(data).filter(([key, value]) => !skip.includes(key) && isUsefulValue(value))
  if (!rows.length) {
    return null
  }
  return (
    <div className="visual-block">
      <h5>{title}</h5>
      <div className="visual-table">
        {rows.map(([key, value]) => (
          <div className="visual-row" key={key}>
            <span>{labelize(key)}</span>
            <strong>{formatSourceValue(value)}</strong>
          </div>
        ))}
      </div>
    </div>
  )
}

function ChainSignalPanel({ chain }: { chain: Record<string, unknown> }) {
  const groups = Object.entries(chain).filter(([, value]) => Array.isArray(value))
  if (!groups.length) {
    return null
  }

  return (
    <div className="visual-block chain-signal-panel">
      <h5><Activity size={15} aria-hidden="true" /> Lifecycle source signals</h5>
      <div className="chain-signal-grid">
        {groups.map(([key, value]) => {
          const refs = (value as unknown[]).filter(Boolean).map(String)
          return (
            <div className={`chain-signal-card ${refs.length ? 'active' : 'idle'}`} key={key}>
              <span className="chain-signal-icon">
                {refs.length ? <CheckCircle2 size={16} aria-hidden="true" /> : <ShieldCheck size={16} aria-hidden="true" />}
              </span>
              <span>{labelize(key)}</span>
              <strong>{refs.length}</strong>
              <small>{refs.length ? refs.slice(0, 2).join(', ') : 'No linked record'}</small>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function LinkGroups({ links }: { links: Record<string, unknown> }) {
  const groups = Object.entries(links).filter(([, value]) => isUsefulValue(value))
  if (!groups.length) {
    return null
  }
  return (
    <div className="visual-block">
      <h5>TED link groups</h5>
      <div className="link-group-grid">
        {groups.map(([key, value]) => {
          const record = asRecord(value)
          const count = Object.values(record).filter(Boolean).length
          return (
            <div className="link-group-card" key={key}>
              <span>{labelize(key)}</span>
              <strong>{count || 1} links</strong>
              <small>{Object.keys(record).slice(0, 8).join(', ') || formatSourceValue(value)}</small>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function NestedSection({ title, value }: { title: string; value: unknown }) {
  return (
    <div className="visual-block">
      <h5>{title}</h5>
      <NestedValue value={value} depth={0} />
    </div>
  )
}

function NestedValue({ value, depth }: { value: unknown; depth: number }) {
  if (!isUsefulValue(value)) {
    return <span className="muted">N/A</span>
  }

  if (Array.isArray(value)) {
    return (
      <div className="nested-list">
        {value.map((item, index) => (
          <div className="nested-card" key={`${index}-${formatSourceValue(item).slice(0, 24)}`}>
            <NestedValue value={item} depth={depth + 1} />
          </div>
        ))}
      </div>
    )
  }

  if (typeof value === 'object') {
    const rows = Object.entries(asRecord(value)).filter(([, child]) => isUsefulValue(child))
    return (
      <div className={depth > 1 ? 'nested-compact' : 'visual-table'}>
        {rows.map(([key, child]) => (
          <div className="visual-row" key={key}>
            <span>{labelize(key)}</span>
            {isCpvFieldKey(key) ? (
              <CollapsibleCpvList value={child} />
            ) : typeof child === 'object' && child !== null ? (
              <NestedValue value={child} depth={depth + 1} />
            ) : (
              <strong>{formatSourceValue(child)}</strong>
            )}
          </div>
        ))}
      </div>
    )
  }

  return <strong>{formatSourceValue(value)}</strong>
}

function DetailItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="detail-item">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  )
}

type CpvEntry = {
  code: string
  description?: string | null
}

function CollapsibleCpvList({ label, value }: { label?: string; value: unknown }) {
  const [expanded, setExpanded] = useState(false)
  const entries = normalizeCpvEntries(value)
  const contentId = label ? `cpv-list-${label.toLowerCase()}` : undefined

  const content = (() => {
    if (!entries.length) {
      return <strong>N/A</strong>
    }

    if (entries.length === 1) {
      return <strong>{formatCpvEntry(entries[0])}</strong>
    }

    return (
      <div className="cpv-collapsible">
        <div className="cpv-collapsed-row">
          <strong>
            {entries[0].code} + {entries.length - 1} more
          </strong>
          <button className="cpv-expand-button" type="button" aria-expanded={expanded} aria-controls={contentId} onClick={() => setExpanded((current) => !current)}>
            {expanded ? 'Hide CPV' : 'Show all CPV'}
            <ChevronDown className={expanded ? 'expanded' : undefined} size={15} aria-hidden="true" />
          </button>
        </div>
        {expanded ? (
          <div className="cpv-expanded-list" id={contentId}>
            {entries.map((entry) => (
              <div className="cpv-expanded-item" key={`${entry.code}-${entry.description ?? ''}`}>
                <strong>{entry.code}</strong>
                {entry.description ? <small>{entry.description}</small> : null}
              </div>
            ))}
          </div>
        ) : null}
      </div>
    )
  })()

  if (label) {
    return (
      <div className="detail-item cpv-detail-item">
        <span>{label}</span>
        {content}
      </div>
    )
  }

  return <div className="cpv-source-list">{content}</div>
}

function isCpvFieldKey(key: string) {
  return key.replace(/[-_\s]/g, '').toLowerCase() === 'cpvs'
}

function normalizeCpvEntries(value: unknown): CpvEntry[] {
  const entries: CpvEntry[] = []

  const collect = (current: unknown) => {
    if (!isUsefulValue(current)) {
      return
    }

    if (Array.isArray(current)) {
      current.forEach(collect)
      return
    }

    if (typeof current === 'string' || typeof current === 'number') {
      const text = String(current).trim()
      const codes = text.match(/\b\d{8}-\d\b/g)
      if (codes?.length) {
        codes.forEach((code) => entries.push({ code }))
      } else if (text) {
        entries.push({ code: text })
      }
      return
    }

    if (typeof current === 'object') {
      const record = asRecord(current)
      const valueText = firstString(record.value)
      const directCode = firstString(record.key, record.code, record.cpvCode, record.cpv, record.id)
      const valueCode = valueText?.match(/\b\d{8}-\d\b/)?.[0] ?? null
      const code = directCode ?? valueCode
      const description = firstString(record.description, record.label, record.name, valueCode ? null : valueText)

      if (code) {
        entries.push({ code, description: description !== code ? description : null })
        return
      }

      Object.values(record).forEach(collect)
    }
  }

  collect(value)

  const seen = new Set<string>()
  return entries.filter((entry) => {
    const key = `${entry.code}-${entry.description ?? ''}`
    if (seen.has(key)) {
      return false
    }
    seen.add(key)
    return true
  })
}

function formatCpvEntry(entry: CpvEntry) {
  return [entry.code, entry.description].filter(Boolean).join(' - ')
}

function Metric({ icon: Icon, label, value, tone = 'neutral' }: { icon: LucideIcon; label: string; value: string; tone?: string }) {
  return (
    <div className={`metric ${tone}`}>
      <Icon size={19} aria-hidden="true" />
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  )
}

function Meta({ icon: Icon, label, value }: { icon: LucideIcon; label: string; value: string }) {
  return (
    <div className="meta-item">
      <Icon size={16} aria-hidden="true" />
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  )
}

function StatusPill({ ok, label }: { ok: boolean; label: string }) {
  return (
    <span className={`status-pill ${ok ? 'ok' : 'idle'}`}>
      <i />
      {label}
    </span>
  )
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value) ? (value as Record<string, unknown>) : {}
}

function isUsefulValue(value: unknown) {
  if (value === null || value === undefined || value === '') {
    return false
  }
  if (Array.isArray(value)) {
    return value.length > 0
  }
  if (typeof value === 'object') {
    return Object.keys(value as Record<string, unknown>).length > 0
  }
  return true
}

function opportunityStats(items: Opportunity[]) {
  const totalBudget = items.reduce((sum, item) => sum + (item.budget ?? 0), 0)
  const byPackage: Record<string, number> = {}
  for (const item of items) {
    byPackage[item.package_match] = (byPackage[item.package_match] ?? 0) + 1
  }
  return {
    total: items.length,
    bid_candidates: items.filter((item) => item.fit_score >= 80).length,
    worth_reading: items.filter((item) => item.fit_score >= 60).length,
    total_budget: totalBudget,
    average_score: items.length ? Math.round((items.reduce((sum, item) => sum + item.fit_score, 0) / items.length) * 10) / 10 : 0,
    by_package: byPackage,
  }
}

function formatSourceValue(value: unknown): string {
  if (value === null || value === undefined || value === '') {
    return 'N/A'
  }
  if (Array.isArray(value)) {
    return value.map(formatSourceValue).join(', ')
  }
  if (typeof value === 'object') {
    const record = asRecord(value)
    const preferred = ['value', 'name', 'title', 'label', 'ell', 'eng', 'MUL', 'ELL', 'ENG']
    for (const key of preferred) {
      if (isUsefulValue(record[key])) {
        return formatSourceValue(record[key])
      }
    }
    return `${Object.keys(record).length} fields`
  }
  if (typeof value === 'boolean') {
    return value ? 'Yes' : 'No'
  }
  return String(value)
}

function labelize(key: string) {
  return key
    .replace(/([a-z])([A-Z])/g, '$1 $2')
    .replace(/[-_]/g, ' ')
    .replace(/\b\w/g, (letter) => letter.toUpperCase())
}

function formatCurrency(value?: number | null) {
  if (!value) {
    return 'N/A'
  }
  return new Intl.NumberFormat('el-GR', {
    style: 'currency',
    currency: 'EUR',
    maximumFractionDigits: 0,
  }).format(value)
}

function formatDate(value?: string | null) {
  if (!value) {
    return 'Unknown'
  }
  return new Intl.DateTimeFormat('el-GR', { day: '2-digit', month: 'short', year: 'numeric' }).format(parseDateOnly(value))
}

function formatDateTime(value?: string | null) {
  if (!value) {
    return 'Unknown'
  }
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return formatDate(value)
  }
  return new Intl.DateTimeFormat('el-GR', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date)
}

function formatPublishedDate(value?: string | null) {
  if (!value) {
    return 'Unknown'
  }
  return `${formatDate(value)} - ${freshnessLabel(value)}`
}

function buildCalendarYear(year: number, dailyActivity: DailyActivity[], sources: SourceName[]): CalendarMonth[] {
  const activityByDate = new Map(dailyActivity.map((day) => [day.date, day]))
  const today = startOfDay(new Date())

  return Array.from({ length: 12 }, (_, month) => {
    const firstOfMonth = new Date(year, month, 1)
    const gridStart = addDays(firstOfMonth, -firstOfMonth.getDay())
    const cells = Array.from({ length: 42 }, (__, offset) => {
      const date = addDays(gridStart, offset)
      const dateKey = toDateInput(date)
      const activity = activityByDate.get(dateKey)
      const by_source = Object.fromEntries(sources.map((source) => [source, activity?.by_source[source] ?? 0])) as Partial<Record<SourceName, number>>

      return {
        date: dateKey,
        dayOfMonth: date.getDate(),
        offset,
        inMonth: date.getMonth() === month && date.getFullYear() === year,
        isToday: isSameCalendarDay(date, today),
        isFuture: date.getTime() > today.getTime(),
        total: activity?.total ?? 0,
        by_source,
      }
    })

    return {
      year,
      month,
      label: new Intl.DateTimeFormat('en-US', { month: 'long', year: 'numeric' }).format(firstOfMonth),
      total: cells.reduce((sum, cell) => sum + (cell.inMonth ? cell.total : 0), 0),
      cells,
    }
  })
}

function calendarDayTitle(cell: CalendarDayCell, sources: SourceName[]) {
  const sourceText = sources.length
    ? sources.map((source) => `${SOURCE_META[source].label}: ${cell.by_source[source] ?? 0}`).join(' | ')
    : 'No live sources selected'
  return `${formatDate(cell.date)} - ${cell.total} new (${sourceText})`
}

function freshnessLabel(value?: string | null) {
  const age = daysSince(value)
  if (age === null) return 'Unknown'
  if (age === 0) return 'Today'
  if (age === 1) return 'Yesterday'
  return `${age}d ago`
}

function actionWindow(opportunity: Opportunity) {
  const daysLeft = opportunity.deadline ? daysUntil(opportunity.deadline) : null
  const age = daysSince(opportunity.published_at)

  if (daysLeft !== null && daysLeft <= 5) {
    return { label: 'Urgent', detail: daysLeft < 0 ? 'Deadline passed' : `${daysLeft}d left`, tone: 'urgent' }
  }
  if (age === null) {
    return { label: 'Unknown', detail: 'Missing publish date', tone: 'unknown' }
  }
  if (age <= 14 && (daysLeft === null || daysLeft >= 10)) {
    return { label: 'Fresh', detail: `${age}d old`, tone: 'fresh' }
  }
  return { label: 'Stale', detail: `${age}d old`, tone: 'stale' }
}

function rowLifecycleStage(opportunity: Opportunity, guidance?: OpportunityGuidance) {
  if (guidance) {
    return guidanceLifecycleStage(guidance)
  }

  const reference = opportunity.source_reference ?? ''
  const text = `${opportunity.procedure_type ?? ''} ${opportunity.title} ${opportunity.summary} ${opportunity.status_label ?? ''} ${opportunity.notice_type ?? ''}`.toLowerCase()

  if (opportunity.source === 'khmdhs') {
    if (text.includes('έγκριση') || text.includes('εγκρι') || text.includes('approved') || text.includes('approval')) {
      return { label: 'Εγκεκριμένο Αίτημα', tone: 'watch' }
    }
    if (text.includes('διακήρυξη') || text.includes('πρόσκληση') || text.includes('notice') || text.includes('tender')) {
      return { label: 'Διακήρυξη', tone: 'action' }
    }
    if (reference.includes('REQ')) return { label: 'Αίτημα', tone: 'watch' }
    if (reference.includes('PROC')) return { label: 'Διακήρυξη', tone: 'action' }
    if (reference.includes('AWRD')) return { label: 'Ανάθεση', tone: 'closed' }
    if (reference.includes('SYMV')) return { label: 'Σύμβαση', tone: 'closed' }
    return { label: 'KIMDIS', tone: 'unknown' }
  }

  if (opportunity.source === 'ted') {
    if (text.includes('award') || text.includes('result')) return { label: 'Result', tone: 'closed' }
    if (text.includes('prior') || text.includes('planning') || text.includes('consultation')) {
      return { label: 'Planning', tone: 'watch' }
    }
    if (opportunity.deadline && daysUntil(opportunity.deadline) >= 0) return { label: 'Competition', tone: 'action' }
    return { label: 'TED', tone: 'unknown' }
  }

  return { label: 'Example', tone: 'unknown' }
}

function guidanceLifecycleStage(guidance: OpportunityGuidance) {
  const stage = guidance.current_stage
  const label = guidance.current_stage_label || 'Unknown'

  if (guidance.is_actionable || stage === 'notice' || stage === 'competition' || stage === 'submission') {
    return { label, tone: 'action' }
  }
  if (stage === 'award' || stage === 'contract' || stage === 'payment' || stage === 'result' || stage === 'modification') {
    return { label, tone: 'closed' }
  }
  if (stage === 'request' || stage === 'approved_request' || stage === 'planning') {
    return { label, tone: 'watch' }
  }
  return { label, tone: 'unknown' }
}

function daysUntil(value: string) {
  const deadline = parseDateOnly(value)
  const today = startOfDay(new Date())
  return Math.ceil((deadline.getTime() - today.getTime()) / 86_400_000)
}

function daysSince(value?: string | null) {
  if (!value) {
    return null
  }
  const published = parseDateOnly(value)
  const today = startOfDay(new Date())
  return Math.max(0, Math.floor((today.getTime() - published.getTime()) / 86_400_000))
}

function parseDateOnly(value: string) {
  if (/^\d{4}-\d{2}-\d{2}$/.test(value)) {
    return new Date(`${value}T12:00:00`)
  }
  return new Date(value)
}

function startOfDay(value: Date) {
  return new Date(value.getFullYear(), value.getMonth(), value.getDate())
}

function isSameCalendarDay(left: Date, right: Date) {
  return left.getFullYear() === right.getFullYear() && left.getMonth() === right.getMonth() && left.getDate() === right.getDate()
}

function bandToClass(score: number) {
  if (score >= 80) return 'green'
  if (score >= 60) return 'blue'
  if (score >= 40) return 'amber'
  return 'red'
}

function addDays(date: Date, days: number) {
  const next = new Date(date)
  next.setDate(next.getDate() + days)
  return next
}

function daysElapsedInYear(date: Date) {
  const currentUtc = Date.UTC(date.getFullYear(), date.getMonth(), date.getDate())
  const startUtc = Date.UTC(date.getFullYear(), 0, 1)
  return Math.floor((currentUtc - startUtc) / 86_400_000) + 1
}

function toDateInput(date: Date) {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function packageLabel(name: string) {
  return name
    .replace('Public Applications Platform', 'Applications')
    .replace('Field Monitoring & Reporting App', 'Field reporting')
    .replace('Cultural / Multimedia Digital Experience', 'Culture media')
    .replace('Dashboard & Data Intelligence', 'Dashboards')
    .replace('Document & Case Management', 'Documents')
}

function cpvDescription(code: string) {
  return CPV_DESCRIPTIONS[code] ?? 'CPV description is not available yet.'
}

function buildCpvGroups(cpvOptions: string[]): CpvCategory[] {
  const optionSet = new Set(cpvOptions)
  const categorized = new Set(CPV_CATEGORIES.flatMap((category) => category.codes))
  const groups = CPV_CATEGORIES.map((category) => ({
    ...category,
    codes: category.codes.filter((code) => optionSet.has(code)),
  })).filter((category) => category.codes.length > 0)
  const otherCodes = cpvOptions.filter((code) => !categorized.has(code))

  if (!otherCodes.length) {
    return groups
  }

  return [
    ...groups,
    {
      id: 'other',
      label: 'Other CPV',
      description: 'Additional configured CPV codes',
      codes: otherCodes,
      advanced: true,
    },
  ]
}

export default App
