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
  Cpu,
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
  summary: string
  matched_keywords: string[]
  fit_score: number
  fit_band: 'Bid candidate' | 'Worth reading' | 'Monitor only' | 'Ignore'
  score_reasons: string[]
  red_flags: string[]
  recommendation: string
  package_match: string
  ai_summary?: string | null
}

type DocumentLink = {
  label: string
  url: string
  document_type: string
  language?: string | null
  reference?: string | null
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
  raw: Record<string, unknown>
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
  ai_enabled: boolean
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
  const [useAi, setUseAi] = useState(false)
  const [loading, setLoading] = useState(true)
  const [response, setResponse] = useState<SearchResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [detailsOpportunity, setDetailsOpportunity] = useState<Opportunity | null>(null)
  const [details, setDetails] = useState<OpportunityDetails | null>(null)
  const [detailsLoading, setDetailsLoading] = useState(false)
  const [detailsError, setDetailsError] = useState<string | null>(null)
  const [shortlist, setShortlist] = useState<string[]>(() => {
    try {
      return JSON.parse(localStorage.getItem('opportunity-shortlist') ?? '[]')
    } catch {
      return []
    }
  })

  const aiEnabled = response?.ai_enabled ?? false
  const cpvOptions = config?.default_cpv_codes ?? FALLBACK_CPV
  const cpvGroups = useMemo(() => buildCpvGroups(cpvOptions), [cpvOptions])
  const packageRows = useMemo(() => {
    const packages = response?.stats.by_package ?? {}
    return Object.entries(packages)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 5)
  }, [response])

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
          use_ai: useAi && aiEnabled,
          limit: 100,
        }),
      })
      if (!res.ok) {
        throw new Error(`API returned ${res.status}`)
      }
      const data = (await res.json()) as SearchResponse
      setResponse(data)
      if (!data.ai_enabled) {
        setUseAi(false)
      }
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : 'Search failed')
    } finally {
      setLoading(false)
    }
  }, [aiEnabled, budgetMax, budgetMin, dateFrom, dateTo, keywords, onlyOpen, query, selectedCpvs, showAllFetched, sources, useAi])

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
      await runSearch()
    }
    void boot()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    localStorage.setItem('opportunity-shortlist', JSON.stringify(shortlist))
  }, [shortlist])

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
      setDetails((await res.json()) as OpportunityDetails)
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

  const toggleShortlist = (id: string) => {
    setShortlist((current) => (current.includes(id) ? current.filter((item) => item !== id) : [...current, id]))
  }

  const shortlistItems = response?.opportunities.filter((item) => shortlist.includes(item.id)) ?? []

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

          <label className={`ai-toggle ${aiEnabled ? '' : 'disabled'}`}>
            <input type="checkbox" checked={useAi && aiEnabled} disabled={!aiEnabled} onChange={(event) => setUseAi(event.target.checked)} />
            <Cpu size={17} aria-hidden="true" />
            <span>{aiEnabled ? 'AI enrichment' : 'AI off μέχρι να μπει key'}</span>
          </label>
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
            <StatusPill ok={aiEnabled} label={aiEnabled ? 'AI ready' : 'Rules mode'} />
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
              {shortlistItems.length ? (
                shortlistItems.map((item) => (
                  <button className="shortlist-item" key={item.id} onClick={() => toggleShortlist(item.id)} type="button">
                    <span>{item.fit_score}</span>
                    {item.title}
                  </button>
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
                pinned={shortlist.includes(opportunity.id)}
                onTogglePin={() => toggleShortlist(opportunity.id)}
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
        onClose={closeDetails}
      />
    </div>
  )
}

function OpportunityRow({
  opportunity,
  pinned,
  onTogglePin,
  onOpenDetails,
}: {
  opportunity: Opportunity
  pinned: boolean
  onTogglePin: () => void
  onOpenDetails: () => void
}) {
  const bandClass = bandToClass(opportunity.fit_score)
  const daysLeft = opportunity.deadline ? daysUntil(opportunity.deadline) : null
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

        <p className="summary">{opportunity.ai_summary ?? opportunity.summary}</p>

        <div className="meta-grid">
          <Meta icon={Building2} label="Buyer" value={opportunity.buyer} />
          <Meta icon={CircleDollarSign} label="Budget" value={formatCurrency(opportunity.budget)} />
          <Meta icon={CalendarClock} label="Deadline" value={daysLeft === null ? 'Unknown' : `${formatDate(opportunity.deadline)} · ${daysLeft}d`} />
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

function DetailsDrawer({
  opportunity,
  details,
  loading,
  error,
  onClose,
}: {
  opportunity: Opportunity | null
  details: OpportunityDetails | null
  loading: boolean
  error: string | null
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
  return new Intl.DateTimeFormat('el-GR', { day: '2-digit', month: 'short' }).format(new Date(value))
}

function daysUntil(value: string) {
  const deadline = new Date(`${value}T12:00:00`)
  const now = new Date()
  return Math.ceil((deadline.getTime() - now.getTime()) / 86_400_000)
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
