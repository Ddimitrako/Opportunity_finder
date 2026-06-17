import {
  Activity,
  AlertTriangle,
  BarChart3,
  BookmarkCheck,
  BookmarkPlus,
  Building2,
  CalendarClock,
  ChevronDown,
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
  PanelRightOpen,
  RefreshCw,
  Search,
  ShieldCheck,
  Sparkles,
  Target,
  X,
  type LucideIcon,
} from 'lucide-react'
import { type CSSProperties, type FormEvent, useCallback, useEffect, useMemo, useState } from 'react'
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
  matched_keywords: string[]
  fit_score: number
  fit_band: 'Bid candidate' | 'Worth reading' | 'Monitor only' | 'Ignore'
  score_reasons: string[]
  red_flags: string[]
  recommendation: string
  package_match: string
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

type DocumentBrief = {
  source: SourceName
  reference: string
  project_summary: string
  actionable: 'yes' | 'no' | 'maybe' | 'unknown'
  deadline_submission: string
  required_documents: string[]
  technical_requirements: string[]
  red_flags: string[]
  recommendation: string
  next_steps: string[]
  source_documents: DocumentLink[]
  generated_at: string
  model?: string | null
  cached: boolean
}

type DocumentBriefResponse = {
  brief?: DocumentBrief | null
  cached: boolean
  message?: string | null
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

type DailyActivity = {
  date: string
  label: string
  total: number
  by_source: Partial<Record<SourceName, number>>
}

type ActivityResponse = {
  generated_at: string
  date_from: string
  date_to: string
  daily_activity: DailyActivity[]
  source_runs: SourceRun[]
  total: number
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
}

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

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
  '72261000-2': 'Software support services. Support for existing software products or platforms.',
  '72262000-9': 'Software development services. Broad custom development CPV.',
  '72263000-6': 'Software implementation services. Implementation, setup and rollout.',
  '72268000-1': 'Software supply services. Supply or delivery of software services/products.',
  '72420000-0': 'Internet development services. Web platforms and internet applications.',
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
}

type CpvCategory = {
  id: string
  label: string
  description: string
  codes: string[]
  defaultOpen?: boolean
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
]

const FALLBACK_KEYWORDS = [
  'ανάπτυξη εφαρμογής',
  'ανάπτυξη λογισμικού',
  'πλατφόρμα',
  'dashboard',
  'workflow',
  'portal',
  'CMS',
]

function App() {
  const [config, setConfig] = useState<ConfigResponse | null>(null)
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
  const [documentBriefLoading, setDocumentBriefLoading] = useState(false)
  const [documentBriefGenerating, setDocumentBriefGenerating] = useState(false)
  const [documentBriefError, setDocumentBriefError] = useState<string | null>(null)
  const [buyerIntelligence, setBuyerIntelligence] = useState<BuyerIntelligenceResponse | null>(null)
  const [buyerIntelligenceLoading, setBuyerIntelligenceLoading] = useState(false)
  const [buyerIntelligenceError, setBuyerIntelligenceError] = useState<string | null>(null)
  const [bookmarks, setBookmarks] = useState<BookmarkRecord[]>([])
  const [bookmarkError, setBookmarkError] = useState<string | null>(null)
  const [guidanceByOpportunityId, setGuidanceByOpportunityId] = useState<Record<string, OpportunityGuidance>>({})

  const cpvOptions = config?.default_cpv_codes ?? FALLBACK_CPV
  const cpvGroups = useMemo(() => buildCpvGroups(cpvOptions), [cpvOptions])
  const packageRows = useMemo(() => {
    const packages = response?.stats.by_package ?? {}
    return Object.entries(packages)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 5)
  }, [response])
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

  const runSearch = useCallback(async (overrides?: { onlyOpen?: boolean; showAllFetched?: boolean }) => {
    setLoading(true)
    setError(null)
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
          days: 3,
          limit: 100,
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
  }, [sources])

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
    } catch (exc) {
      setDocumentBrief(null)
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
        `${API_BASE}/api/opportunities/${opportunity.source}/${encodeURIComponent(opportunity.source_reference)}/brief`,
        { method: 'POST' },
      )
      if (!res.ok) {
        throw new Error(`AI brief API returned ${res.status}`)
      }
      const data = (await res.json()) as DocumentBriefResponse
      if (data.brief) {
        setDocumentBrief(data.brief)
      } else {
        setDocumentBriefError(data.message ?? 'No AI brief was generated.')
      }
    } catch (exc) {
      setDocumentBriefError(exc instanceof Error ? exc.message : 'AI brief generation failed')
    } finally {
      setDocumentBriefGenerating(false)
    }
  }

  const shortlistItems = bookmarks.map((bookmark) => bookmark.opportunity)

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
            <div className="group-title">
              <Layers3 size={16} aria-hidden="true" />
              CPV focus
            </div>
            <div className="cpv-category-list">
              {cpvGroups.map((group) => {
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
              })}
            </div>
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
          <Metric icon={DatabaseZap} label="Results" value={loading ? '...' : String(response?.stats.total ?? 0)} />
          <Metric icon={Target} label="Bid candidates" value={String(response?.stats.bid_candidates ?? 0)} tone="green" />
          <Metric icon={Gauge} label="Average fit" value={`${response?.stats.average_score ?? 0}/100`} tone="blue" />
          <Metric icon={CircleDollarSign} label="Tracked budget" value={formatCurrency(response?.stats.total_budget ?? 0)} tone="amber" />
        </section>

        <section className="insight-layout">
          <SmartCalendarPanel activity={activity} loading={activityLoading} error={activityError} selectedSources={sources} />

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
            <h3>{loading ? 'Loading opportunities' : `${response?.opportunities.length ?? 0} matches`}</h3>
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
            response?.opportunities.map((opportunity) => (
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
        briefLoading={documentBriefLoading}
        briefGenerating={documentBriefGenerating}
        briefError={documentBriefError}
        buyerIntelligence={buyerIntelligence}
        buyerIntelligenceLoading={buyerIntelligenceLoading}
        buyerIntelligenceError={buyerIntelligenceError}
        onGenerateBrief={() => detailsOpportunity ? void generateDocumentBrief(detailsOpportunity) : undefined}
        onClose={closeDetails}
      />
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
  const visibleSources = selectedSources.filter((source) => source !== 'demo')

  return (
    <div className="smart-calendar-panel">
      <div className="panel-heading">
        <CalendarClock size={18} aria-hidden="true" />
        <h3>Smart calendar</h3>
      </div>
      <p className="panel-note">New publications from selected sources. Search filters do not affect this count.</p>

      {loading ? (
        <div className="calendar-state">
          <Loader2 className="spin" size={17} aria-hidden="true" />
          <span>Loading activity...</span>
        </div>
      ) : null}

      {!loading && error ? (
        <div className="calendar-state error">
          <AlertTriangle size={17} aria-hidden="true" />
          <span>{error}</span>
        </div>
      ) : null}

      {!loading && !error ? (
        <div className="calendar-list">
          {(activity?.daily_activity ?? []).map((day) => (
            <div className="calendar-row" key={day.date}>
              <div>
                <strong>{calendarLabel(day)}</strong>
                <span>{formatDate(day.date)}</span>
              </div>
              <div className="calendar-count">
                <strong>{day.total}</strong>
                <span>new</span>
              </div>
              <div className="calendar-sources">
                {visibleSources.map((source) => (
                  <span key={`${day.date}-${source}`}>
                    {SOURCE_META[source].label}: {day.by_source[source] ?? 0}
                  </span>
                ))}
              </div>
            </div>
          ))}
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
                Στην πλατφόρμα
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

        <div className="evidence-grid">
          <div>
            <h5><ShieldCheck size={15} aria-hidden="true" /> Fit reasons</h5>
            <ul>
              {opportunity.score_reasons.slice(0, 4).map((reason) => (
                <li key={reason}>{reason}</li>
              ))}
            </ul>
          </div>
          <div>
            <h5><AlertTriangle size={15} aria-hidden="true" /> Red flags</h5>
            {opportunity.red_flags.length ? (
              <ul>
                {opportunity.red_flags.slice(0, 4).map((flag) => (
                  <li key={flag}>{flag}</li>
                ))}
              </ul>
            ) : (
              <p className="quiet">No obvious red flags.</p>
            )}
          </div>
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

      <div className="lifecycle-bar">
        {guidance.stage_steps.map((step) => (
          <div className={`lifecycle-step ${step.status}`} key={step.id}>
            <span>{step.label}</span>
            <small>{step.references.length ? step.references.join(', ') : step.status}</small>
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

      <div className="checklist-block">
        <h5>Beginner checklist</h5>
        <div className="checklist-list">
          {guidance.checklist.map((item) => (
            <div className={`checklist-item ${item.status}`} key={`${item.label}-${item.status}`}>
              <CheckCircle2 size={16} aria-hidden="true" />
              <span>
                <strong>{item.label}</strong>
                <small>{item.detail}</small>
              </span>
            </div>
          ))}
        </div>
      </div>

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

function GuidanceCard({ title, value }: { title: string; value: string }) {
  return (
    <div className="guidance-card">
      <span>{title}</span>
      <strong>{value}</strong>
    </div>
  )
}

function DetailsDrawer({
  opportunity,
  details,
  loading,
  error,
  brief,
  briefLoading,
  briefGenerating,
  briefError,
  buyerIntelligence,
  buyerIntelligenceLoading,
  buyerIntelligenceError,
  onGenerateBrief,
  onClose,
}: {
  opportunity: Opportunity | null
  details: OpportunityDetails | null
  loading: boolean
  error: string | null
  brief: DocumentBrief | null
  briefLoading: boolean
  briefGenerating: boolean
  briefError: string | null
  buyerIntelligence: BuyerIntelligenceResponse | null
  buyerIntelligenceLoading: boolean
  buyerIntelligenceError: string | null
  onGenerateBrief: () => void
  onClose: () => void
}) {
  if (!opportunity) {
    return null
  }

  const metadata = details?.metadata ?? {}
  const documents = details?.documents ?? []
  const primaryLinkLabel = details?.source === 'khmdhs' ? 'Άνοιγμα βασικού εγγράφου ΚΗΜΔΗΣ' : 'Άνοιγμα record στην πλατφόρμα'

  return (
    <div className="drawer-backdrop" role="presentation">
      <aside className="details-drawer" aria-label="Opportunity details">
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
            <section className="drawer-section">
              <h4>Available information</h4>
              <div className="details-grid">
                <DetailItem label="Reference" value={details?.reference ?? opportunity.source_reference ?? 'N/A'} />
                <DetailItem label="Source" value={opportunity.source_label} />
                <DetailItem label="Buyer" value={String(metadata.buyer ?? metadata.organization ?? opportunity.buyer ?? 'N/A')} />
                <DetailItem label="Published" value={String(metadata.publicationDate ?? metadata.submissionDate ?? opportunity.published_at ?? 'N/A')} />
                <DetailItem label="Deadline" value={String(metadata.deadline ?? metadata.procurementDeliveryDate ?? opportunity.deadline ?? 'N/A')} />
                <DetailItem label="Type" value={String(metadata.noticeType ?? metadata.procedureType ?? opportunity.procedure_type ?? 'N/A')} />
                <DetailItem label="Budget" value={formatCurrency(opportunity.budget)} />
                <DetailItem label="CPV" value={opportunity.cpv_codes.join(', ') || 'N/A'} />
              </div>
              {details?.summary ? <p className="drawer-summary">{details.summary}</p> : null}
              {details?.platform_url ? (
                <a className="drawer-primary-link" href={details.platform_url} target="_blank" rel="noreferrer">
                  {primaryLinkLabel}
                  <ExternalLink size={15} aria-hidden="true" />
                </a>
              ) : null}
            </section>

            {details?.guidance ? (
              <GuidancePanel guidance={details.guidance} />
            ) : null}

            <BuyerIntelligencePanel intelligence={buyerIntelligence} loading={buyerIntelligenceLoading} error={buyerIntelligenceError} />

            <DocumentBriefPanel
              brief={brief}
              loading={briefLoading}
              generating={briefGenerating}
              error={briefError}
              canGenerate={Boolean(opportunity.source_reference)}
              onGenerate={onGenerateBrief}
            />

            <section className="drawer-section">
              <h4>Documents</h4>
              {documents.length ? (
                <div className="document-list">
                  {documents.map((document) => (
                    <a className="document-link" href={document.url} target="_blank" rel="noreferrer" key={`${document.document_type}-${document.language}-${document.reference}-${document.url}`}>
                      <FileText size={16} aria-hidden="true" />
                      <span>
                        <strong>{document.label}</strong>
                        <small>{[document.document_type, document.language, document.reference].filter(Boolean).join(' · ')}</small>
                      </span>
                      <ExternalLink size={14} aria-hidden="true" />
                    </a>
                  ))}
                </div>
              ) : (
                <p className="muted">Δεν βρέθηκαν διαθέσιμα links εγγράφων από την πηγή.</p>
              )}
            </section>

            <section className="drawer-section">
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
            <BuyerMetric label="KIMDIS history" value={String(intelligence.history_opportunity_count)} />
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

          <div className="buyer-intel-grid">
            <BuyerSampleList title="Recent visible opportunities" items={intelligence.recent_opportunities} />
            <BuyerSampleList title="Similar procurements" items={intelligence.similar_opportunities} empty="No similar procurement found in visible or KIMDIS historical records." />
          </div>

          <DiavgeiaSignals intelligence={intelligence} />

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
    </section>
  )
}

function BuyerMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="buyer-metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  )
}

function BuyerSampleList({ title, items, empty = 'No visible opportunities.' }: { title: string; items: BuyerOpportunitySample[]; empty?: string }) {
  return (
    <div className="buyer-list-block">
      <h5>{title}</h5>
      {items.length ? (
        <div className="buyer-sample-list">
          {items.map((item) => (
            <a className="buyer-sample" href={item.url ?? '#'} target={item.url ? '_blank' : undefined} rel="noreferrer" key={item.id}>
              <span>{item.source_label}</span>
              <strong>{item.title}</strong>
              <small>{[formatCurrency(item.budget), item.published_at ? formatDate(item.published_at) : null, item.package_match].filter(Boolean).join(' · ')}</small>
            </a>
          ))}
        </div>
      ) : (
        <p className="muted">{empty}</p>
      )}
    </div>
  )
}

function DiavgeiaSignals({ intelligence }: { intelligence: BuyerIntelligenceResponse }) {
  const signals = intelligence.winner_signals.length ? intelligence.winner_signals : intelligence.diavgeia_decisions.slice(0, 3)
  return (
    <div className="diavgeia-block">
      <h5>Award / winner signals</h5>
      {intelligence.khmdhs_history_message ? <p className="muted">{intelligence.khmdhs_history_message}</p> : null}
      {intelligence.diavgeia_message ? <p className="muted">{intelligence.diavgeia_message}</p> : null}
      {signals.length ? (
        <div className="diavgeia-list">
          {signals.map((decision) => (
            <a className="diavgeia-item" href={decision.document_url ?? decision.url ?? '#'} target={decision.document_url || decision.url ? '_blank' : undefined} rel="noreferrer" key={`${decision.ada}-${decision.subject}`}>
              <span>{[decision.source_label, decision.ada ?? decision.decision_type ?? 'Decision'].filter(Boolean).join(' · ')}</span>
              <strong>{decision.subject}</strong>
              <small>
                {[decision.winner_name, formatCurrency(decision.amount), decision.published_at ? formatDate(decision.published_at) : null, decision.similar_to_software ? 'software-like' : null]
                  .filter(Boolean)
                  .join(' · ')}
              </small>
            </a>
          ))}
        </div>
      ) : (
        <p className="muted">No award/winner signal returned from KIMDIS or Diavgeia for this lookup.</p>
      )}
    </div>
  )
}

function DocumentBriefPanel({
  brief,
  loading,
  generating,
  error,
  canGenerate,
  onGenerate,
}: {
  brief: DocumentBrief | null
  loading: boolean
  generating: boolean
  error: string | null
  canGenerate: boolean
  onGenerate: () => void
}) {
  const ActionIcon = generating ? Loader2 : Sparkles

  return (
    <section className="drawer-section ai-brief-section">
      <div className="ai-brief-header">
        <div>
          <h4>AI document brief</h4>
          <p>Runs only when you press the pink button. Saved briefs load from the database.</p>
        </div>
        <button className="ai-brief-button" type="button" onClick={onGenerate} disabled={!canGenerate || generating || Boolean(brief)}>
          <ActionIcon className={generating ? 'spin' : undefined} size={16} aria-hidden="true" />
          {brief ? 'Saved in DB' : generating ? 'Reading docs...' : 'Generate brief'}
        </button>
      </div>

      {loading ? (
        <div className="ai-brief-state">
          <Loader2 className="spin" size={16} aria-hidden="true" />
          <span>Checking saved brief...</span>
        </div>
      ) : null}

      {error ? (
        <div className="ai-brief-error">
          <AlertTriangle size={16} aria-hidden="true" />
          <span>{error}</span>
        </div>
      ) : null}

      {!loading && !brief ? (
        <p className="muted">No saved brief yet. Press the pink button when you want AI to read the available documents.</p>
      ) : null}

      {brief ? (
        <div className="ai-brief-content">
          <div className="brief-verdict-row">
            <span className={`brief-verdict ${brief.actionable}`}>{brief.actionable}</span>
            <strong>{brief.recommendation}</strong>
          </div>
          <p>{brief.project_summary}</p>

          <div className="brief-grid">
            <BriefBlock title="Deadline / submission" items={[brief.deadline_submission]} />
            <BriefBlock title="Required documents" items={brief.required_documents} empty="Not identified in the readable text." />
            <BriefBlock title="Technical requirements" items={brief.technical_requirements} empty="Not identified in the readable text." />
            <BriefBlock title="Red flags" items={brief.red_flags} empty="No red flags identified by the brief." />
            <BriefBlock title="Next steps" items={brief.next_steps} empty="Open the official source documents first." />
          </div>

          <div className="brief-meta">
            <span>{brief.cached ? 'Saved brief' : 'New brief'}</span>
            <span>{formatDateTime(brief.generated_at)}</span>
            {brief.model ? <span>{brief.model}</span> : null}
          </div>
        </div>
      ) : null}
    </section>
  )
}

function BriefBlock({ title, items, empty }: { title: string; items: string[]; empty?: string }) {
  const visibleItems = items.filter(Boolean)
  return (
    <div className="brief-block">
      <h5>{title}</h5>
      {visibleItems.length ? (
        <ul>
          {visibleItems.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      ) : (
        <p>{empty ?? 'Unknown'}</p>
      )}
    </div>
  )
}

function SourceDataVisualization({ details }: { details: OpportunityDetails | null }) {
  if (!details) {
    return <p className="muted">No source data loaded.</p>
  }

  if (details.source === 'khmdhs') {
    const metadata = asRecord(details.raw.metadata)
    const chain = asRecord(details.raw.adamChain)
    const objectDetails = Array.isArray(metadata.objectDetails) ? metadata.objectDetails : []
    return (
      <div className="source-visualization">
        <FieldTable title="ΚΗΜΔΗΣ metadata" data={metadata} skip={['objectDetails']} />
        <ChainTable chain={chain} />
        {objectDetails.length ? (
          <NestedSection title="Object details" value={objectDetails} />
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

function ChainTable({ chain }: { chain: Record<string, unknown> }) {
  const groups = Object.entries(chain).filter(([, value]) => Array.isArray(value))
  if (!groups.length) {
    return null
  }
  return (
    <div className="visual-block">
      <h5>Συνδεδεμένες πράξεις ΚΗΜΔΗΣ</h5>
      <div className="chain-grid">
        {groups.map(([key, value]) => {
          const refs = (value as unknown[]).filter(Boolean).map(String)
          return (
            <div className="chain-group" key={key}>
              <span>{labelize(key)}</span>
              {refs.length ? refs.map((ref) => <strong key={ref}>{ref}</strong>) : <em>None</em>}
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
            {typeof child === 'object' && child !== null ? <NestedValue value={child} depth={depth + 1} /> : <strong>{formatSourceValue(child)}</strong>}
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

function calendarLabel(day: DailyActivity) {
  if (day.label === 'today') return 'Today'
  if (day.label === 'yesterday') return 'Yesterday'
  if (day.label === 'day_before_yesterday') return 'Day before'
  return freshnessLabel(day.date)
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
    },
  ]
}

export default App
