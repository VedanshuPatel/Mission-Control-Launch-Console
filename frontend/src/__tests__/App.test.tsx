import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import App from '../App'

vi.mock('../api', () => ({
  getHealth: vi.fn().mockResolvedValue({ status: 'ok', provider: 'fake' }),
  listReports: vi.fn().mockResolvedValue([]),
  getReport: vi.fn(),
  createReport: vi.fn(),
  approveBriefing: vi.fn(),
  ApiError: class ApiError extends Error {},
}))

describe('App', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders the Mission Control title', async () => {
    render(<App />)
    expect(screen.getByRole('heading', { name: /mission control/i })).toBeInTheDocument()
    expect(await screen.findByText(/DEMO MODE/i)).toBeInTheDocument()
  })
})
