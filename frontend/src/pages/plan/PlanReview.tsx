import { Link, useOutletContext } from 'react-router-dom'
import { ClipboardCheck } from 'lucide-react'
import { StatusBadge } from '../../components/StatusBadge'
import type { PlanContextValue } from '../PlanLayout'
import type { ReviewHistoryEntry } from '../../types'
import { formatDate, initials } from '../../utils'

export default function PlanReview() {
  const { plan } = useOutletContext<PlanContextValue>()
  const canReview = plan.status === 'Pending Teacher Review' || plan.status === 'Needs Revision'

  return (
    <div className="review-page">
      <section className="review-current">
        <div>
          <span className="eyebrow">Current decision</span>
          <h2>{plan.review.status}</h2>
        </div>
        <StatusBadge status={plan.review.status} />
        <dl>
          <div>
            <dt>Reviewer</dt>
            <dd>{plan.review.reviewer ?? 'Not assigned'}</dd>
          </div>
          <div>
            <dt>Decision time</dt>
            <dd>{formatDate(plan.review.decided_at)}</dd>
          </div>
          <div className="review-notes">
            <dt>Notes</dt>
            <dd>{plan.review.notes || 'No notes recorded.'}</dd>
          </div>
        </dl>
        {canReview ? (
          <Link to={`/plans/${plan.plan_id}/decide`} className="button button-primary">
            <ClipboardCheck size={16} /> Record a decision
          </Link>
        ) : null}
      </section>

      <section className="content-section">
        <div className="content-heading">
          <span>Audit trail</span>
          <h2>Every edit and decision</h2>
        </div>
        <div className="history">
          {plan.review.history.map((entry, index) => (
            <HistoryEntry
              key={`${entry.timestamp_utc}-${index}`}
              entry={entry}
              last={index === plan.review.history.length - 1}
            />
          ))}
        </div>
      </section>
    </div>
  )
}

function HistoryEntry({ entry, last }: { entry: ReviewHistoryEntry; last: boolean }) {
  return (
    <div className="history-entry">
      <div className="history-marker">
        <span />
        {!last ? <i /> : null}
      </div>
      <div className="history-content">
        <div className="history-head">
          <strong>
            {entry.action === 'created'
              ? 'Draft created'
              : entry.action === 'edited'
                ? 'Teacher edit'
                : entry.to_status}
          </strong>
          <span>{formatDate(entry.timestamp_utc)}</span>
        </div>
        <p className="history-actor">
          <span className="avatar">{initials(entry.actor)}</span>
          {entry.actor}
          {entry.from_status ? (
            <em>
              {entry.from_status} → {entry.to_status}
            </em>
          ) : null}
        </p>
        {entry.details.changed_fields?.length ? (
          <p className="history-detail">
            Changed: {entry.details.changed_fields.join(', ')}
          </p>
        ) : null}
        {entry.details.note ? <p className="history-note">{entry.details.note}</p> : null}
        {entry.details.notes ? <p className="history-note">{entry.details.notes}</p> : null}
        {entry.details.message ? <p className="history-note">{entry.details.message}</p> : null}
      </div>
    </div>
  )
}
