import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { TraceList } from '../components/TraceList'
import { TEN_STEPS } from './fixtures'

describe('TraceList', () => {
  it('renders one card per step with tokens and cost; labels code/human; groups checks', () => {
    render(<TraceList steps={TEN_STEPS} />)

    expect(screen.getAllByTestId(/trace-step-/)).toHaveLength(10)

    for (const step of TEN_STEPS) {
      const card = screen.getByTestId(`trace-step-${step.seq}`)
      expect(card).toHaveTextContent(`input tokens: ${step.input_tokens}`)
      expect(card).toHaveTextContent(`output tokens: ${step.output_tokens}`)
      expect(card).toHaveTextContent(`$${step.cost_usd}`)
    }

    expect(screen.getByTestId('trace-step-2')).toHaveTextContent(/code · 0 tokens/i)
    expect(screen.getByTestId('trace-step-10')).toHaveTextContent(/human · 0 tokens/i)

    const parallel = screen.getByTestId('checks-parallel')
    expect(parallel).toHaveTextContent(/ran in parallel/i)
    expect(parallel).toHaveTextContent(/check_injection/)
    expect(parallel).toHaveTextContent(/check_missing_details/)
    expect(parallel).toHaveTextContent(/check_tone/)
  })
})
