import { useState } from 'react'
import type { FormEvent } from 'react'
import { ApiError, createReport } from '../api'
import type { FieldError, Report, ReportCreate } from '../types'

const STATIONS = ['PROP', 'GNC', 'AVIONICS', 'TELEMETRY', 'GROUND', 'WEATHER', 'RANGE'] as const

const EMPTY = {
  engineer_name: '',
  station: 'PROP',
  wind_knots: '',
  temp_c: '',
  fuel_pct: '',
  note: '',
}

type Props = {
  onCreated: (report: Report) => void
}

function fieldMessage(errors: FieldError[], field: string): string | undefined {
  return errors.find((e) => e.field === field)?.message
}

export function ReportForm({ onCreated }: Props) {
  const [form, setForm] = useState(EMPTY)
  const [errors, setErrors] = useState<FieldError[]>([])
  const [submitting, setSubmitting] = useState(false)

  function set(field: keyof typeof EMPTY, value: string) {
    setForm((prev) => ({ ...prev, [field]: value }))
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    const local: FieldError[] = []
    if (!form.engineer_name.trim()) {
      local.push({ field: 'engineer_name', message: 'engineer_name is required' })
    }
    const wind = Number(form.wind_knots)
    const temp = Number(form.temp_c)
    const fuel = Number(form.fuel_pct)
    if (form.wind_knots.trim() === '' || Number.isNaN(wind)) {
      local.push({ field: 'wind_knots', message: 'wind_knots must be a number' })
    }
    if (form.temp_c.trim() === '' || Number.isNaN(temp)) {
      local.push({ field: 'temp_c', message: 'temp_c must be a number' })
    }
    if (form.fuel_pct.trim() === '' || Number.isNaN(fuel)) {
      local.push({ field: 'fuel_pct', message: 'fuel_pct must be a number' })
    }
    if (!form.note.trim()) {
      local.push({ field: 'note', message: 'note is required' })
    }
    if (local.length) {
      setErrors(local)
      return
    }

    const payload: ReportCreate = {
      engineer_name: form.engineer_name.trim(),
      station: form.station,
      wind_knots: wind,
      temp_c: temp,
      fuel_pct: fuel,
      note: form.note.trim(),
    }

    setSubmitting(true)
    setErrors([])
    try {
      const report = await createReport(payload)
      setForm(EMPTY)
      onCreated(report)
    } catch (err) {
      if (err instanceof ApiError && err.errors.length) {
        setErrors(err.errors)
      } else {
        setErrors([{ field: '_form', message: err instanceof Error ? err.message : 'Submit failed' }])
      }
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form className="report-form" onSubmit={onSubmit} noValidate>
      <h2>File anomaly report</h2>
      {fieldMessage(errors, '_form') ? (
        <p className="field-error" role="alert">
          {fieldMessage(errors, '_form')}
        </p>
      ) : null}

      <label>
        Engineer name
        <input
          value={form.engineer_name}
          onChange={(e) => set('engineer_name', e.target.value)}
          autoComplete="name"
        />
        {fieldMessage(errors, 'engineer_name') ? (
          <span className="field-error">{fieldMessage(errors, 'engineer_name')}</span>
        ) : null}
      </label>

      <label>
        Station
        <select value={form.station} onChange={(e) => set('station', e.target.value)}>
          {STATIONS.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
        {fieldMessage(errors, 'station') ? (
          <span className="field-error">{fieldMessage(errors, 'station')}</span>
        ) : null}
      </label>

      <label>
        Wind (knots)
        <input
          value={form.wind_knots}
          onChange={(e) => set('wind_knots', e.target.value)}
          inputMode="decimal"
        />
        {fieldMessage(errors, 'wind_knots') ? (
          <span className="field-error">{fieldMessage(errors, 'wind_knots')}</span>
        ) : null}
      </label>

      <label>
        Temp (°C)
        <input
          value={form.temp_c}
          onChange={(e) => set('temp_c', e.target.value)}
          inputMode="decimal"
        />
        {fieldMessage(errors, 'temp_c') ? (
          <span className="field-error">{fieldMessage(errors, 'temp_c')}</span>
        ) : null}
      </label>

      <label>
        Fuel (%)
        <input
          value={form.fuel_pct}
          onChange={(e) => set('fuel_pct', e.target.value)}
          inputMode="decimal"
        />
        {fieldMessage(errors, 'fuel_pct') ? (
          <span className="field-error">{fieldMessage(errors, 'fuel_pct')}</span>
        ) : null}
      </label>

      <label>
        Note
        <textarea
          value={form.note}
          onChange={(e) => set('note', e.target.value)}
          rows={4}
        />
        {fieldMessage(errors, 'note') ? (
          <span className="field-error">{fieldMessage(errors, 'note')}</span>
        ) : null}
      </label>

      <button type="submit" disabled={submitting}>
        {submitting ? 'Filing…' : 'File report'}
      </button>
    </form>
  )
}
