import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { ComponentProps } from 'react'

import { SoftwareMatchesPanel } from '../App'

type PanelOpportunity = ComponentProps<typeof SoftwareMatchesPanel>['opportunity']

const product = {
  slug: 'frappe-crm',
  name: 'Frappe CRM',
  edition: 'Open Source',
  repository: 'https://github.com/frappe/crm',
  website: 'https://frappe.io/crm',
  summary: 'An open-source CRM for sales teams.',
  problem: 'Manages a sales pipeline.',
  ideal_for: 'Sales teams.',
  department_ids: ['sales-support'],
  category_ids: ['crm-pipeline'],
  buyer_roles: ['Sales lead'],
  company_sizes: ['SMB'],
  deployment_modes: ['Docker'],
  service_types: ['Deployment', 'Integration'],
  license_id: 'agpl-3',
  maturity: 'established' as const,
  editorial_score: 90,
  english_support: 'verified',
  greek_support: 'unknown' as const,
  greek_evidence: null,
  edition_boundary: null,
  featured: false,
  last_verified_at: '2026-08-02',
  extra_keywords_en: ['Frappe CRM'],
  extra_keywords_el: [],
  negative_keywords: [],
  delivery_fit: 'small_team' as const,
  active: true,
}

const deterministicMatch = {
  product,
  score: 82,
  confidence: 'high' as const,
  source: 'deterministic' as const,
  dimensions: [{ key: 'capability', label: 'Category / capability', score: 40, max_score: 40, reasons: ['CRM'] }],
  matched_signals: ['Capability: CRM', 'CPV: 48445'],
  service_recommendations: [{ service_type: 'Integration', label: 'Integration', confidence: 'recommended' as const, reasons: ['Tender signal'] }],
  caveats: ['Review AGPL obligations.'],
  evidence_ids: [],
  catalog_version: 'v1-test',
}

const baseOpportunity: PanelOpportunity = {
  id: 'crm-opportunity',
  source: 'demo',
  source_label: 'Demo',
  title: 'CRM deployment and integration',
  buyer: 'Demo buyer',
  cpv_codes: ['48445000-8'],
  currency: 'EUR',
  country: 'GR',
  summary: 'CRM deployment and integration',
  matched_keywords: ['crm'],
  fit_score: 80,
  fit_band: 'Bid candidate',
  score_reasons: [],
  red_flags: [],
  recommendation: 'Bid',
  package_match: 'Custom software',
  software_match_status: 'matched',
  software_matches: [deterministicMatch],
}

function jsonResponse(body: unknown, status = 200): Response {
  return { ok: status >= 200 && status < 300, status, json: async () => body } as Response
}

describe('Software product matchmaking', () => {
  const fetchMock = vi.fn()

  beforeEach(() => {
    vi.stubGlobal('fetch', fetchMock)
    fetchMock.mockReset()
  })

  afterEach(() => {
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
  })

  it('renders deterministic products and an unavailable-AI state', () => {
    render(<SoftwareMatchesPanel opportunity={baseOpportunity} aiEnabled={false} selectedAiModel="gpt-4.1-mini" />)
    expect(screen.getByText('Frappe CRM')).toBeInTheDocument()
    expect(screen.getByText('Deterministic')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Refine with AI/i })).toBeDisabled()
    expect(screen.getByText(/Deterministic matching remains active/i)).toBeInTheDocument()
  })

  it('renders the explicit no-match state', () => {
    render(
      <SoftwareMatchesPanel
        opportunity={{ ...baseOpportunity, software_match_status: 'insufficient_signals', software_matches: [] }}
        aiEnabled
        selectedAiModel="gpt-4.1-mini"
      />,
    )
    expect(screen.getByText('Insufficient signals')).toBeInTheDocument()
    expect(screen.queryByText('Frappe CRM')).not.toBeInTheDocument()
  })

  it('shows cached AI refinement results after an explicit click', async () => {
    const refined = { ...deterministicMatch, score: 88, source: 'ai_refined' as const, matched_signals: ['Explicit CRM evidence'] }
    fetchMock.mockResolvedValue(jsonResponse({
      matches: [refined],
      match_status: 'matched',
      model: 'gpt-4.1-mini',
      cached: true,
      catalog_version: 'v1-test',
    }))
    const user = userEvent.setup()
    render(<SoftwareMatchesPanel opportunity={baseOpportunity} aiEnabled selectedAiModel="gpt-4.1-mini" />)

    await user.click(screen.getByRole('button', { name: /Refine with AI/i }))

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1))
    expect(await screen.findByText(/cached result/i)).toBeInTheDocument()
    expect(screen.getByText('AI refined')).toBeInTheDocument()
    expect(screen.getByText('Explicit CRM evidence')).toBeInTheDocument()
  })
})
