import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { App } from '../App'
import { amd, qty, tr, unit } from '../lib/format'

describe('format', () => {
  it('formats drams with a thin thousands separator', () => {
    expect(amd(3500)).toBe('3 500 ֏')
    expect(amd(1234567)).toBe('1 234 567 ֏')
    expect(amd(900)).toBe('900 ֏')
  })

  it('falls back across languages', () => {
    expect(tr({ hy: 'պանիր', ru: 'сыр' }, 'ru')).toBe('сыр')
    expect(tr({ hy: 'պանիր' }, 'en')).toBe('պանիր')
  })

  it('trims quantities and localizes units', () => {
    expect(qty('20.000')).toBe('20')
    expect(qty('0.500')).toBe('0.5')
    expect(unit('kg', 'hy')).toBe('կգ')
  })
})

describe('App', () => {
  beforeEach(() => localStorage.clear())

  it('shows demo sign-in when the backend allows it', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => new Response(JSON.stringify({ dev_login: true, telegram_bot_username: '' }))),
    )
    render(
      <MemoryRouter initialEntries={['/']} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <App />
      </MemoryRouter>,
    )
    expect(await screen.findByText('Cafe Arax — owner')).toBeInTheDocument()
    expect(screen.getByText('Բոլոր մատակարարները մեկ զամբյուղում։ Կարող եք սակարկել։')).toBeInTheDocument()
    vi.unstubAllGlobals()
  })
})
