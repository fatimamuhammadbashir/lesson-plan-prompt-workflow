import { Link } from 'react-router-dom'
import { ChevronRight, Clock3, Layers3, UserRoundCheck } from 'lucide-react'
import type { PlanSummary } from '../types'
import { formatDate, initials } from '../utils'
import { StatusBadge } from './StatusBadge'

export function PlanRow({ plan }: { plan: PlanSummary }) {
  return (
    <Link to={`/plans/${plan.plan_id}`} className="plan-row">
      <div className="plan-row-status">
        <StatusBadge status={plan.status} />
        <span className="plan-row-id">{plan.plan_id}</span>
      </div>
      <div className="plan-row-main">
        <span className="plan-row-subject">
          {plan.subject} · {plan.class_name}
        </span>
        <h3>{plan.topic}</h3>
        <div className="plan-row-meta">
          <span>
            <Clock3 size={13} /> {plan.duration_minutes ?? '—'} min
          </span>
          <span>
            <Layers3 size={13} /> {plan.activity_count} activities
          </span>
          <span>
            <UserRoundCheck size={13} />
            {plan.reviewer ?? 'Awaiting reviewer'}
          </span>
        </div>
      </div>
      <div className="plan-row-side">
        <span className="plan-row-reviewer">
          <span className="mini-avatar">{initials(plan.reviewer)}</span>
          {plan.reviewer ?? 'Unassigned'}
        </span>
        <span className="plan-row-date">{formatDate(plan.updated_at)}</span>
      </div>
      <ChevronRight size={18} className="plan-row-chevron" />
    </Link>
  )
}
