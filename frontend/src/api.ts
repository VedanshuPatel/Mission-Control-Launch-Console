import type { ApprovePayload, FieldError, Health, Report, ReportCreate } from './types'

export class ApiError extends Error {
  status: number
  errors: FieldError[]

  constructor(status: number, message: string, errors: FieldError[] = []) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.errors = errors
  }
}

async function parseJson(response: Response): Promise<unknown> {
  try {
    return await response.json()
  } catch {
    return null
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
    ...init,
  })
  const body = await parseJson(response)
  if (!response.ok) {
    const errors =
      body && typeof body === 'object' && Array.isArray((body as { errors?: unknown }).errors)
        ? ((body as { errors: FieldError[] }).errors)
        : []
    const detail =
      body && typeof body === 'object' && 'detail' in body
        ? String((body as { detail: unknown }).detail)
        : response.statusText
    throw new ApiError(response.status, detail || `HTTP ${response.status}`, errors)
  }
  return body as T
}

export function getHealth(): Promise<Health> {
  return request<Health>('/api/health')
}

export function listReports(): Promise<Report[]> {
  return request<Report[]>('/api/reports')
}

export function getReport(id: string): Promise<Report> {
  return request<Report>(`/api/reports/${id}`)
}

export function createReport(payload: ReportCreate): Promise<Report> {
  return request<Report>('/api/reports', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function approveBriefing(id: string, payload: ApprovePayload): Promise<Report> {
  return request<Report>(`/api/reports/${id}/briefing/approve`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}
