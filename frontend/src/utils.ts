import type { Conclusion } from './types'

export function normalizeConclusion(value: Conclusion | string): Conclusion {
  if (typeof value === 'string') {
    return { summary: value, next_steps: [], exit_prompt: '' }
  }
  return {
    summary: value.summary ?? '',
    next_steps: value.next_steps ?? [],
    exit_prompt: value.exit_prompt ?? '',
  }
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return 'Not yet'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat('en', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date)
}

export function formatPercent(value: number): string {
  return `${Math.round(value * 100)}%`
}

export function phaseLabel(phase: string): string {
  return phase.charAt(0).toUpperCase() + phase.slice(1)
}

export function factorLabel(factor: string): string {
  return factor
    .split('_')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

export function statusTone(status: string): string {
  switch (status) {
    case 'Approved':
      return 'approved'
    case 'Rejected':
      return 'rejected'
    case 'Needs Revision':
      return 'revision'
    default:
      return 'pending'
  }
}

export function initials(name: string | null | undefined): string {
  if (!name) return 'TR'
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? '')
    .join('')
}
