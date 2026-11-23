import { Link } from 'react-router-dom'
import { ArrowRight, Inbox, Plus } from 'lucide-react'
import { PageHeader } from '../components/PageHeader'
import { PlanRow } from '../components/PlanRow'
import { StatusBadge } from '../components/StatusBadge'
import { usePlans } from '../hooks/usePlans'
import { formatDate } from '../utils'

export default function OverviewPage() {
  const { plans, loading, error, reload } = usePlans()
  const recent = plans.slice(0, 4)
  const queue = plans.filter(
    (plan) => plan.status === 'Pending Teacher Review' || plan.status === 'Needs Revision',
  )
  const approved = plans.filter((plan) => plan.status === 'Approved').length

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Workspace"
        title="Your planning workspace"
        description="Review drafts, pick up where you left off, or start a new lesson plan. Everything stays local to this machine."
      />

      <section className="summary-strip" aria-label="Workspace summary">
        <div>
          <span>Lesson drafts</span>
          <strong>{plans.length}</strong>
        </div>
        <div>
          <span>Awaiting review</span>
          <strong>{queue.length}</strong>
        </div>
        <div>
          <span>Approved</span>
          <strong>{approved}</strong>
        </div>
        <div className="summary-note">
          <span>Engine</span>
          <strong>Rule-based · local</strong>
        </div>
      </section>

      {error ? (
        <section className="state-card">
          <h2>Workspace unavailable</h2>
          <p>{error}</p>
          <button type="button" className="button button-secondary" onClick={() => void reload()}>
            Try again
          </button>
        </section>
      ) : (
        <div className="overview-grid">
          <section className="section-card">
            <div className="section-card-head">
              <div>
                <span className="eyebrow">Recent</span>
                <h2>Lesson plans</h2>
              </div>
              <Link to="/plans" className="text-link">
                View all <ArrowRight size={14} />
              </Link>
            </div>
            {loading ? (
              <div className="row-skeletons">
                <span className="skeleton" />
                <span className="skeleton" />
                <span className="skeleton" />
              </div>
            ) : recent.length ? (
              <div className="plan-list">
                {recent.map((plan) => (
                  <PlanRow key={plan.plan_id} plan={plan} />
                ))}
              </div>
            ) : (
              <div className="empty-state">
                <h3>No lesson plans yet</h3>
                <p>Start with a class, an approved topic and the outcomes you want to teach.</p>
                <Link to="/plans/new" className="button button-primary">
                  <Plus size={16} /> Start a lesson plan
                </Link>
              </div>
            )}
          </section>

          <aside className="section-card review-card">
            <div className="section-card-head">
              <div>
                <span className="eyebrow">Needs a teacher</span>
                <h2>Review queue</h2>
              </div>
              <Inbox size={18} />
            </div>
            {queue.length ? (
              <div className="queue-list">
                {queue.slice(0, 5).map((plan) => (
                  <Link key={plan.plan_id} to={`/plans/${plan.plan_id}/review`} className="queue-item">
                    <div>
                      <strong>{plan.topic}</strong>
                      <span>
                        {plan.subject} · {plan.class_name}
                      </span>
                      <em>{formatDate(plan.updated_at)}</em>
                    </div>
                    <StatusBadge status={plan.status} short />
                  </Link>
                ))}
              </div>
            ) : (
              <div className="empty-state compact">
                <h3>Queue is clear</h3>
                <p>Every draft has a teacher decision.</p>
              </div>
            )}
            <Link to="/reviews" className="text-link queue-link">
              Open review queue <ArrowRight size={14} />
            </Link>
          </aside>
        </div>
      )}
    </div>
  )
}
