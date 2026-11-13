import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ReportForm } from '../components/ReportForm'
import { ApiError } from '../api'

const createReport = vi.fn()

vi.mock('../api', async () => {
  const actual = await vi.importActual<typeof import('../api')>('../api')
  return {
    ...actual,
    createReport: (...args: unknown[]) => createReport(...args),
  }
})

describe('ReportForm', () => {
  beforeEach(() => {
    createReport.mockReset()
    createReport.mockResolvedValue({ id: 'r1' })
  })

  it('submits exactly the six fields with readings as numbers', async () => {
    const user = userEvent.setup()
    render(<ReportForm onCreated={() => {}} />)

    await user.type(screen.getByLabelText(/engineer name/i), 'Ada')
    await user.selectOptions(screen.getByLabelText(/station/i), 'PROP')
    await user.clear(screen.getByLabelText(/wind/i))
    await user.type(screen.getByLabelText(/wind/i), '12.5')
    await user.clear(screen.getByLabelText(/temp/i))
    await user.type(screen.getByLabelText(/temp/i), '18')
    await user.clear(screen.getByLabelText(/fuel/i))
    await user.type(screen.getByLabelText(/fuel/i), '99')
    await user.type(screen.getByLabelText(/note/i), 'Valve chatter.')
    await user.click(screen.getByRole('button', { name: /file report/i }))

    await waitFor(() => expect(createReport).toHaveBeenCalledTimes(1))
    expect(createReport).toHaveBeenCalledWith({
      engineer_name: 'Ada',
      station: 'PROP',
      wind_knots: 12.5,
      temp_c: 18,
      fuel_pct: 99,
      note: 'Valve chatter.',
    })
  })

  it('blocks blank name and non-numeric reading with visible messages', async () => {
    const user = userEvent.setup()
    render(<ReportForm onCreated={() => {}} />)

    await user.selectOptions(screen.getByLabelText(/station/i), 'PROP')
    await user.clear(screen.getByLabelText(/wind/i))
    await user.type(screen.getByLabelText(/wind/i), 'abc')
    await user.type(screen.getByLabelText(/note/i), 'note')
    await user.click(screen.getByRole('button', { name: /file report/i }))

    expect(await screen.findByText(/engineer_name is required/i)).toBeInTheDocument()
    expect(screen.getByText(/wind_knots must be a number/i)).toBeInTheDocument()
    expect(createReport).not.toHaveBeenCalled()
  })

  it('shows server 422 messages next to their fields', async () => {
    const user = userEvent.setup()
    createReport.mockRejectedValue(
      new ApiError(422, 'validation', [
        { field: 'fuel_pct', message: 'fuel_pct must be between 0 and 120' },
      ]),
    )
    render(<ReportForm onCreated={() => {}} />)

    await user.type(screen.getByLabelText(/engineer name/i), 'Ada')
    await user.selectOptions(screen.getByLabelText(/station/i), 'PROP')
    await user.clear(screen.getByLabelText(/wind/i))
    await user.type(screen.getByLabelText(/wind/i), '10')
    await user.clear(screen.getByLabelText(/temp/i))
    await user.type(screen.getByLabelText(/temp/i), '20')
    await user.clear(screen.getByLabelText(/fuel/i))
    await user.type(screen.getByLabelText(/fuel/i), '50')
    await user.type(screen.getByLabelText(/note/i), 'ok')
    await user.click(screen.getByRole('button', { name: /file report/i }))

    expect(
      await screen.findByText(/fuel_pct must be between 0 and 120/i),
    ).toBeInTheDocument()
  })
})
