import { CheckCircle2, CircleDot, RotateCcw, XCircle } from 'lucide-react'
import { statusTone } from '../utils'

const icons = {
  approved: CheckCircle2,
  rejected: XCircle,
  revision: RotateCcw,
  pending: CircleDot,
}

export function StatusBadge({ status, short = false }: { status: string; short?: boolean }) {
  const tone = statusTone(status)
  const Icon = icons[tone as keyof typeof icons] ?? CircleDot
  const label = short && status === 'Pending Teacher Review' ? 'Pending' : status
  return (
    <span className={`status-badge status-${tone}`}>
      <Icon size={13} />
      {label}
    </span>
  )
}
