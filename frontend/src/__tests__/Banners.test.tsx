import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { Banners } from '../components/Banners'
import { makeReport } from './fixtures'

describe('Banners', () => {
  it('shows the flags banner', () => {
    render(
      <Banners
        report={makeReport({
          needs_human_review: true,
          review_reasons: ['possible_injected_instructions'],
        })}
      />,
    )
    expect(screen.getByText(/Flags require human review/i)).toBeInTheDocument()
    expect(screen.getByText(/possible_injected_instructions/i)).toBeInTheDocument()
  })

  it('shows reviewer-not-satisfied when review_passed is false', () => {
    render(
      <Banners
        report={makeReport({
          briefing: {
            text: 'x',
            rounds_used: 3,
            review_passed: false,
            last_feedback: 'no',
            status: 'pending',
            approved_by: null,
            approved_at: null,
          },
        })}
      />,
    )
    expect(screen.getByText(/Reviewer not satisfied after 3 rounds/i)).toBeInTheDocument()
  })

  it('shows DEMO MODE when health reports the fake provider', () => {
    render(<Banners provider="fake" />)
    expect(screen.getByText(/DEMO MODE/i)).toBeInTheDocument()
  })
})
