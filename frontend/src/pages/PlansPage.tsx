import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { Plus, Search } from 'lucide-react'
import { PageHeader } from '../components/PageHeader'
import { PlanRow } from '../components/PlanRow'
import { usePlans } from '../hooks/usePlans'

const filters = ['All', 'Pending Teacher Review', 'Approved', 'Needs Revision', 'Rejected'] as const
type Filter = (typeof filters)[number]

export default function PlansPage() {
  const { plans, loading, error, reload } = usePlans()
  const [filter, setFilter] = useState<Filter>('All')
  const [query, setQuery] = useState('')

  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase()
    return plans.filter((plan) => {
      const matchesFilter = filter === 'All' || plan.status === filter
      const matchesQuery =
        !needle ||
        [plan.topic, plan.subject, plan.class_name, plan.plan_id]
          .join(' ')
          .toLowerCase()
          .includes(needle)
      return matchesFilter && matchesQuery
    })
  }, [plans, filter, query])

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Library"
        title="Lesson plans"
        description="All drafts in this workspace, with their teacher review status."
      />

      <div className="list-toolbar">
        <div className="segmented">
          {filters.map((item) => (
            <button
              key={item}
              type="button"
              className={filter === item ? 'active' : ''}
              onClick={() => setFilter(item)}
            >
              {item === 'Pending Teacher Review' ? 'Pending' : item === 'Needs Revision' ? 'Revision' : item}
            </button>
          ))}
        </div>
        <label className="search">
          <Search size={16} />
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search plans"
          />
        </label>
      </div>

      {error ? (
        <section className="state-card">
          <h2>Could not load plans</h2>
          <p>{error}</p>
          <button type="button" className="button button-secondary" onClick={() => void reload()}>
            Try again
          </button>
        </section>
      ) : loading ? (
        <div className="row-skeletons">
          <span className="skeleton" />
          <span className="skeleton" />
          <span className="skeleton" />
        </div>
      ) : filtered.length ? (
        <div className="plan-list plan-list-full">
          {filtered.map((plan) => (
            <PlanRow key={plan.plan_id} plan={plan} />
          ))}
        </div>
      ) : (
        <div className="state-card">
          <h2>No plans match this view</h2>
          <p>Change the filter or search, or create a new lesson plan.</p>
          <Link to="/plans/new" className="button button-primary">
            <Plus size={16} /> New lesson plan
          </Link>
        </div>
      )}
    </div>
  )
}
