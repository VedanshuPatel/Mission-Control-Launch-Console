import { useCallback, useEffect, useState } from 'react'
import './App.css'
import { getHealth, listReports } from './api'
import { Banners } from './components/Banners'
import { ReportDetail } from './components/ReportDetail'
import { ReportForm } from './components/ReportForm'
import { ReportList } from './components/ReportList'
import type { Report } from './types'

function App() {
  const [reports, setReports] = useState<Report[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [provider, setProvider] = useState<string | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    try {
      const rows = await listReports()
      setReports(rows)
      setLoadError(null)
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : 'Failed to load reports')
    }
  }, [])

  useEffect(() => {
    void refresh()
    void getHealth()
      .then((h) => setProvider(h.provider))
      .catch(() => setProvider(null))
  }, [refresh])

  function upsert(report: Report) {
    setReports((prev) => {
      const others = prev.filter((r) => r.id !== report.id)
      return [report, ...others]
    })
    setSelectedId(report.id)
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>Mission Control</h1>
        <p className="tagline">Go / No-Go Launch Console</p>
      </header>

      <Banners provider={provider} />

      <main className="app-main layout">
        <aside className="sidebar">
          <ReportForm
            onCreated={(report) => {
              upsert(report)
              void refresh()
            }}
          />
          {loadError ? (
            <p className="field-error" role="alert">
              {loadError}
            </p>
          ) : null}
          <ReportList
            reports={reports}
            selectedId={selectedId}
            onSelect={setSelectedId}
          />
        </aside>
        <section className="detail-pane">
          {selectedId ? (
            <ReportDetail reportId={selectedId} onUpdated={upsert} />
          ) : (
            <p className="muted">Select a report to inspect the briefing and trace.</p>
          )}
        </section>
      </main>
    </div>
  )
}

export default App
