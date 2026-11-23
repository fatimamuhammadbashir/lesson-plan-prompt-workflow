import type {
  ApiErrorShape,
  Decision,
  LessonPlan,
  LessonRequest,
  Meta,
  PlanSummary,
} from './types'

const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? ''

export class ApiError extends Error {
  type: string
  field?: string
  details?: unknown

  constructor(payload: ApiErrorShape['error']) {
    super(payload.message)
    this.name = 'ApiError'
    this.type = payload.type
    this.field = payload.field
    this.details = payload.details
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
  })

  const text = await response.text()
  let payload: unknown = null
  if (text) {
    try {
      payload = JSON.parse(text)
    } catch {
      payload = null
    }
  }

  if (!response.ok) {
    const errorPayload = (payload as ApiErrorShape | null)?.error
    throw new ApiError(
      errorPayload ?? {
        type: 'network_error',
        message: `Request failed with status ${response.status}.`,
      },
    )
  }

  return payload as T
}

export interface EditPayload {
  objectives?: unknown
  materials?: string[]
  activities?: unknown
  assessment?: unknown
  conclusion?: unknown
  note?: string
}

export const api = {
  health: () =>
    request<{ status: string; version: string; plan_count: number }>('/api/health'),

  meta: () => request<Meta>('/api/meta'),

  listPlans: () => request<{ plans: PlanSummary[] }>('/api/plans'),

  getPlan: (planId: string) =>
    request<LessonPlan>(`/api/plans/${encodeURIComponent(planId)}`),

  createPlan: (payload: LessonRequest) =>
    request<LessonPlan>('/api/plans', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  editPlan: (planId: string, payload: EditPayload) =>
    request<LessonPlan>(`/api/plans/${encodeURIComponent(planId)}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }),

  reviewPlan: (
    planId: string,
    payload: { decision: Decision; reviewer: string; notes: string },
  ) =>
    request<LessonPlan>(`/api/plans/${encodeURIComponent(planId)}/review`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
}
