import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { DocumentBriefPanel, OpportunityChatPanel } from '../App'

const emptyContext = {
  ready: false,
  prepared_at: null,
  available_document_count: 0,
  analyzed_document_count: 0,
  readable_document_count: 0,
  unreadable_document_labels: [],
}

const aiModels = [
  { id: 'gpt-4.1-mini', label: 'GPT-4.1 mini', description: 'Fast', quality: 'Fast', recommended: false },
  { id: 'gpt-5.6', label: 'GPT-5.6 Sol', description: 'Best', quality: 'Best', recommended: true },
]

const persistedAssistant = {
  id: 2,
  role: 'assistant' as const,
  content: 'Η προθεσμία επιβεβαιώνεται στις 20 Αυγούστου.',
  strategic_advice: 'Ξεκινήστε τον τεχνικό έλεγχο άμεσα.',
  citations: [
    {
      id: 'd1-p2-c1',
      kind: 'evidence' as const,
      label: 'Notice',
      url: 'https://example.test/notice.pdf',
      page: 2,
      reference: 'ref-1',
      excerpt: 'Deadline evidence',
    },
  ],
  suggested_questions: ['Ποια είναι τα παραδοτέα;'],
  model: 'gpt-5.6',
  created_at: '2026-08-04T10:00:00Z',
}

function jsonResponse(body: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as Response
}

describe('Opportunity AI workspace', () => {
  const fetchMock = vi.fn()

  beforeEach(() => {
    vi.stubGlobal('fetch', fetchMock)
    fetchMock.mockReset()
  })

  afterEach(() => {
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
  })

  it('switches from Decision Brief to independent Ask AI', async () => {
    fetchMock.mockResolvedValue(jsonResponse({ messages: [], context: emptyContext, suggested_questions: [] }))
    const user = userEvent.setup()
    const onSelectAiModel = vi.fn()
    render(
      <DocumentBriefPanel
        source="demo"
        reference="ref-1"
        availableDocumentCount={2}
        brief={null}
        outdated={false}
        loading={false}
        generating={false}
        error={null}
        aiModels={aiModels}
        selectedAiModel="gpt-5.6"
        onSelectAiModel={onSelectAiModel}
        canGenerate
        onGenerate={() => undefined}
      />,
    )

    expect(screen.getByRole('tab', { name: /Decision Brief/i })).toHaveAttribute('aria-selected', 'true')
    await user.selectOptions(screen.getByRole('combobox', { name: /AI model/i }), 'gpt-4.1-mini')
    expect(onSelectAiModel).toHaveBeenCalledWith('gpt-4.1-mini')
    await user.click(screen.getByRole('tab', { name: /Ask AI/i }))

    expect(await screen.findByText(/Δεν χρειάζεται να δημιουργήσεις πρώτα Decision Brief/)).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: /Ask AI/i })).toHaveAttribute('aria-selected', 'true')
  })

  it('restores the persisted transcript after the panel is reopened', async () => {
    const thread = { messages: [persistedAssistant], context: { ...emptyContext, ready: true }, suggested_questions: [] }
    fetchMock.mockResolvedValue(jsonResponse(thread))

    const first = render(<OpportunityChatPanel source="demo" reference="ref-1" model="gpt-5.6" />)
    expect(await screen.findByText(persistedAssistant.content)).toBeInTheDocument()
    first.unmount()
    render(<OpportunityChatPanel source="demo" reference="ref-1" model="gpt-5.6" />)

    expect(await screen.findByText(persistedAssistant.content)).toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })

  it('keeps a failed message retryable and can clear the saved chat', async () => {
    let postAttempts = 0
    fetchMock.mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
      const method = init?.method ?? 'GET'
      if (method === 'GET') return Promise.resolve(jsonResponse({ messages: [], context: emptyContext, suggested_questions: [] }))
      if (method === 'DELETE') return Promise.resolve(jsonResponse(null, 204))
      if (method === 'POST' && String(input).endsWith('/chat')) {
        postAttempts += 1
        if (postAttempts === 1) return Promise.resolve(jsonResponse({ detail: 'Provider temporarily unavailable' }, 502))
        return Promise.resolve(jsonResponse({
          user_message: { id: 1, role: 'user', content: 'Can we bid?', citations: [], suggested_questions: [], created_at: '2026-08-04T10:00:00Z' },
          assistant_message: persistedAssistant,
          context: { ...emptyContext, ready: true },
        }))
      }
      return Promise.resolve(jsonResponse({ detail: 'Unexpected request' }, 500))
    })
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    const user = userEvent.setup()
    render(<OpportunityChatPanel source="demo" reference="ref-1" model="gpt-5.6" />)
    await screen.findByText(/Ρώτησε για αυτό το opportunity/)

    await user.type(screen.getByRole('textbox'), 'Can we bid?')
    await user.click(screen.getByRole('button', { name: /Send/i }))
    expect(await screen.findByRole('button', { name: 'Retry' })).toBeInTheDocument()
    expect(screen.getByRole('textbox')).toHaveValue('Can we bid?')

    await user.click(screen.getByRole('button', { name: 'Retry' }))
    expect(await screen.findByText(persistedAssistant.content)).toBeInTheDocument()
    const chatPost = fetchMock.mock.calls.find(([, init]) => (init as RequestInit | undefined)?.method === 'POST')
    expect(JSON.parse(String((chatPost?.[1] as RequestInit).body))).toMatchObject({ message: 'Can we bid?', model: 'gpt-5.6' })
    await user.click(screen.getByRole('button', { name: 'Clear' }))

    await waitFor(() => expect(screen.queryByText(persistedAssistant.content)).not.toBeInTheDocument())
    expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining('/chat'), expect.objectContaining({ method: 'DELETE' }))
  })

  it('opens the correct citation preview', async () => {
    fetchMock.mockResolvedValue(jsonResponse({
      messages: [persistedAssistant],
      context: { ...emptyContext, ready: true },
      suggested_questions: [],
    }))
    const user = userEvent.setup()
    render(<OpportunityChatPanel source="demo" reference="ref-1" model="gpt-5.6" />)

    await user.click(await screen.findByRole('button', { name: /p\.2 · Notice/i }))

    expect(screen.getByRole('dialog', { name: 'Notice' })).toBeInTheDocument()
    expect(screen.getByTitle('Notice')).toHaveAttribute('src', expect.stringContaining(encodeURIComponent('https://example.test/notice.pdf')))
  })
})
