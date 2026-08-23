import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import type { ComponentProps } from 'react'

import { SoftwareMatchWorkspace } from '../App'

type WorkspaceOpportunity = ComponentProps<typeof SoftwareMatchWorkspace>['opportunities'][number]

const product = {
  slug: 'suitecrm',
  name: 'SuiteCRM',
  edition: 'Community',
  repository: 'https://github.com/salesagility/SuiteCRM-Core',
  website: 'https://suitecrm.com',
  summary: 'Open-source CRM.',
  problem: 'Relationship management.',
  ideal_for: 'Organizations.',
  department_ids: ['sales-support'],
  category_ids: ['crm-pipeline'],
  buyer_roles: ['Sales lead'],
  company_sizes: ['SMB'],
  deployment_modes: ['Docker'],
  service_types: ['Deployment'],
  license_id: 'agpl-3',
  maturity: 'established' as const,
  editorial_score: 90,
  english_support: 'verified',
  greek_support: 'unknown' as const,
  greek_evidence: null,
  edition_boundary: null,
  featured: false,
  last_verified_at: '2026-08-02',
  extra_keywords_en: [],
  extra_keywords_el: [],
  negative_keywords: [],
  delivery_fit: 'small_team' as const,
  active: true,
}

const match = {
  product,
  score: 63,
  confidence: 'medium' as const,
  source: 'ai_refined' as const,
  dimensions: [],
  matched_signals: ['CRM taxonomy fit'],
  service_recommendations: [],
  caveats: [],
  evidence_ids: ['title'],
  catalog_version: 'v1-test',
}

const baseOpportunity: WorkspaceOpportunity = {
  id: 'opportunity-1',
  source: 'demo',
  source_label: 'Demo',
  title: 'Unified constituent engagement records',
  buyer: 'Demo buyer',
  cpv_codes: [],
  currency: 'EUR',
  country: 'GR',
  summary: 'Shared constituent relationship records.',
  matched_keywords: [],
  fit_score: 60,
  fit_band: 'Worth reading',
  score_reasons: [],
  red_flags: [],
  recommendation: 'Review',
  package_match: 'Custom software',
  software_match_status: 'insufficient_signals',
  software_matches: [],
}

const screenedOpportunity: WorkspaceOpportunity = {
  ...baseOpportunity,
  software_match_status: 'matched',
  software_matches: [match],
  software_screening: {
    opportunity_id: baseOpportunity.id,
    status: 'catalog_match',
    stage: 'title',
    reason: 'Η ανάγκη αντιστοιχεί σε CRM capability.',
    matches: [match],
    evidence_ids: ['title'],
    model: 'gpt-4o-mini',
    deep_model: null,
    catalog_version: 'v1-test',
    prompt_version: 'software-screening-v1',
    scanned_at: '2026-08-05T12:00:00Z',
    cached: true,
  },
}

function props(opportunities: WorkspaceOpportunity[]) {
  return {
    opportunities,
    aiEnabled: true,
    catalogCount: 63,
    screeningModel: 'gpt-4o-mini',
    deepModel: 'gpt-4.1-mini',
    loading: false,
    error: null,
    run: null,
    onBack: vi.fn(),
    onScan: vi.fn(),
    onOpenOpportunity: vi.fn(),
    username: 'admin',
    onLogout: vi.fn(async () => undefined),
  }
}

describe('Software Match AI workspace', () => {
  it('starts scanning only after the explicit button click', async () => {
    const workspaceProps = props([baseOpportunity])
    const user = userEvent.setup()
    render(<SoftwareMatchWorkspace {...workspaceProps} />)

    expect(screen.getAllByText('Not scanned').length).toBeGreaterThan(0)
    await user.click(screen.getByRole('button', { name: /Scan current opportunities/i }))
    expect(workspaceProps.onScan).toHaveBeenCalledWith(false)
  })

  it('shows persisted match metadata and product candidates', () => {
    render(<SoftwareMatchWorkspace {...props([screenedOpportunity])} />)
    expect(screen.getAllByText('Catalog match').length).toBeGreaterThan(0)
    expect(screen.getByText('SuiteCRM')).toBeInTheDocument()
    expect(screen.getByText(/title stage/i)).toBeInTheDocument()
    expect(screen.getByText('cached')).toBeInTheDocument()
  })
})
