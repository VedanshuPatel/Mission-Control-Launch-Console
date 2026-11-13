import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ApprovalPanel } from '../components/ApprovalPanel'
import { makeReport } from './fixtures'

const approveBriefing = vi.fn()

vi.mock('../api', async () => {
  const actual = await vi.importActual<typeof import('../api')>('../api')
  return {
    ...actual,
    approveBriefing: (...args: unknown[]) => approveBriefing(...args),
  }
})

describe('ApprovalPanel', () => {
  beforeEach(() => {
    approveBriefing.mockReset()
    approveBriefing.mockResolvedValue(makeReport({ status: 'approved' }))
  })

  it('disables Approve until a name is entered', () => {
    render(<ApprovalPanel report={makeReport()} onApproved={() => {}} />)
    expect(screen.getByRole('button', { name: /approve/i })).toBeDisabled()
  })

  it('requires acknowledgement for flagged reports and posts to approve', async () => {
    const user = userEvent.setup()
    const onApproved = vi.fn()
    render(
      <ApprovalPanel
        report={makeReport({ needs_human_review: true })}
        onApproved={onApproved}
      />,
    )

    await user.type(screen.getByLabelText(/approver name/i), 'Flight Director')
    expect(screen.getByRole('button', { name: /approve/i })).toBeDisabled()

    await user.click(screen.getByRole('checkbox'))
    expect(screen.getByRole('button', { name: /approve/i })).toBeEnabled()

    await user.click(screen.getByRole('button', { name: /approve/i }))
    await waitFor(() =>
      expect(approveBriefing).toHaveBeenCalledWith(
        'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee',
        { approver_name: 'Flight Director', acknowledge_flags: true },
      ),
    )
    expect(onApproved).toHaveBeenCalled()
  })

  it('is hidden once approved', () => {
    const { container } = render(
      <ApprovalPanel
        report={makeReport({
          status: 'approved',
          briefing: {
            text: 'done',
            rounds_used: 1,
            review_passed: true,
            last_feedback: '',
            status: 'approved',
            approved_by: 'FD',
            approved_at: '2026-01-01T12:00:00Z',
          },
        })}
        onApproved={() => {}}
      />,
    )
    expect(container).toBeEmptyDOMElement()
  })
})
