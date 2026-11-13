type Props = {
  verdict: string | null
}

export function VerdictBadge({ verdict }: Props) {
  if (verdict === 'no_go') {
    return <span className="verdict-badge no-go">NO-GO</span>
  }
  if (verdict === 'go') {
    return <span className="verdict-badge go">GO</span>
  }
  return <span className="verdict-badge unknown">—</span>
}
