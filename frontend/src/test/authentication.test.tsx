import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import App from '../App'

function jsonResponse(body: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as Response
}

describe('Application authentication', () => {
  const fetchMock = vi.fn()

  beforeEach(() => {
    window.localStorage.clear()
    vi.stubGlobal('fetch', fetchMock)
    fetchMock.mockImplementation((input: RequestInfo | URL) => {
      if (String(input).endsWith('/api/auth/session')) {
        return Promise.resolve(jsonResponse({ authenticated: false, username: null }))
      }
      if (String(input).endsWith('/api/auth/login')) {
        return Promise.resolve(jsonResponse({ detail: 'Invalid username or password.' }, 401))
      }
      return Promise.resolve(jsonResponse({ detail: 'Unexpected request' }, 500))
    })
  })

  afterEach(() => {
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
  })

  it('shows the login page and keeps invalid credentials unauthenticated', async () => {
    const user = userEvent.setup()
    render(<App />)

    expect(await screen.findByRole('heading', { name: 'Ασφαλής πρόσβαση' })).toBeInTheDocument()
    await user.type(screen.getByLabelText('Όνομα χρήστη'), 'operator')
    await user.type(screen.getByLabelText('Κωδικός'), 'wrong password')
    await user.click(screen.getByRole('button', { name: 'Σύνδεση' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Λάθος όνομα χρήστη ή κωδικός.')
    expect(fetchMock).toHaveBeenLastCalledWith(
      expect.stringContaining('/api/auth/login'),
      expect.objectContaining({ credentials: 'include', method: 'POST' }),
    )
  })

  it('places the signed-in user and logout action inside the sidebar', async () => {
    fetchMock.mockImplementation((input: RequestInfo | URL) => {
      const url = String(input)
      if (url.endsWith('/api/auth/session')) {
        return Promise.resolve(jsonResponse({ authenticated: true, username: 'admin' }))
      }
      if (url.endsWith('/api/auth/logout')) {
        return Promise.resolve(jsonResponse({ authenticated: false, username: null }))
      }
      return Promise.resolve(jsonResponse({ detail: 'Unavailable in this test' }, 500))
    })

    const user = userEvent.setup()
    render(<App />)

    const sessionControl = await screen.findByLabelText('Συνδεδεμένος χρήστης')
    expect(sessionControl.closest('aside')).toHaveClass('sidebar')
    expect(sessionControl).toHaveTextContent('admin')

    await user.click(screen.getByRole('button', { name: 'Απόκρυψη sidebar' }))
    expect(sessionControl.closest('.app-shell')).toHaveClass('sidebar-collapsed')
    expect(window.localStorage.getItem('opportunity-sidebar')).toBe('hidden')

    await user.click(screen.getByRole('button', { name: 'Εμφάνιση sidebar' }))
    expect(sessionControl.closest('.app-shell')).not.toHaveClass('sidebar-collapsed')

    await user.click(screen.getByRole('button', { name: 'Αποσύνδεση' }))
    expect(await screen.findByRole('heading', { name: 'Ασφαλής πρόσβαση' })).toBeInTheDocument()
  })
})
