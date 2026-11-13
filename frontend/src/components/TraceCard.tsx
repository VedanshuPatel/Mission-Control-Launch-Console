import type { TraceStep } from '../types'

type Props = {
  step: TraceStep
}

function kindLine(step: TraceStep): string {
  if (step.kind === 'code') return 'code · 0 tokens'
  if (step.kind === 'human') return 'human · 0 tokens'
  return `${step.model ?? 'model'} · in ${step.input_tokens} / out ${step.output_tokens}`
}

export function TraceCard({ step }: Props) {
  return (
    <article className="trace-card" data-testid={`trace-step-${step.seq}`}>
      <header>
        <span className="trace-seq">#{step.seq}</span>
        <h3>{step.name}</h3>
      </header>
      <p className="trace-kind">{kindLine(step)}</p>
      <p className="trace-tokens">
        input tokens: {step.input_tokens} · output tokens: {step.output_tokens}
      </p>
      <p className="trace-cost">cost: ${step.cost_usd}</p>
      <p className="trace-summary">{step.summary}</p>
    </article>
  )
}
