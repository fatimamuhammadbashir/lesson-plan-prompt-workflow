import { Link } from 'react-router-dom'
import { ArrowRight, Inbox } from 'lucide-react'
import { PageHeader } from '../components/PageHeader'
import { StatusBadge } from '../components/StatusBadge'
import { usePlans } from '../hooks/usePlans'
import { formatDate } from '../utils'

export default function ReviewQueuePage() {
  const { plans, loading, error, reload } = usePlans()
  const queue = plans.filter(
    (plan) => plan.status === 'Pending Teacher Review' || plan.status === 'Needs Revision',
  )

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Review"
        title="Review queue"
        description="Drafts that need a teacher decision. Open a plan to inspect its reasoning, edit it or record a decision."
      />

      {error ? (
        <section className="state-card">
          <h2>Could not load the queue</h2>
          <p>{error}</p>
          <button type="button" className="button button-secondary" onClick={() => void reload()}>
            Try again
          </button>
        </section>
      ) : loading ? (
        <div className="row-skeletons">
          <span className="skeleton" />
          <span className="skeleton" />
        </div>
      ) : queue.length ? (
        <div className="queue-page-list">
          {queue.map((plan) => (
            <Link key={plan.plan_id} to={`/plans/${plan.plan_id}/review`} className="queue-page-item">
              <div className="queue-page-icon">
                <Inbox size={19} />
              </div>
              <div className="queue-page-main">
                <span>
                  {plan.subject} · {plan.class_name}
                </span>
                <h2>{plan.topic}</h2>
                <p>
                  {plan.duration_minutes} minutes · {plan.activity_count} activities · updated{' '}
                  {formatDate(plan.updated_at)}
                </p>
              </div>
              <StatusBadge status={plan.status} />
              <ArrowRight size={18} />
            </Link>
          ))}
        </div>
      ) : (
        <div className="state-card">
          <h2>Nothing to review</h2>
          <p>Every draft currently has a decision. New plans will appear here automatically.</p>
          <Link to="/plans" className="button button-secondary">
            View all lesson plans
          </Link>
        </div>
      )}
    </div>
  )
}
