import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type Dispatch,
  type SetStateAction,
} from 'react'
import { Link, NavLink, Outlet, useLocation, useParams } from 'react-router-dom'
import {
  ArrowLeft,
  CalendarClock,
  CheckCircle2,
  ClipboardCheck,
  Clock3,
  Edit3,
  Layers3,
  Lock,
  Target,
} from 'lucide-react'
import { api, ApiError } from '../api'
import { StatusBadge } from '../components/StatusBadge'
import type { LessonPlan } from '../types'
import { formatDate } from '../utils'

export interface PlanContextValue {
  plan: LessonPlan
  setPlan: Dispatch<SetStateAction<LessonPlan | null>>
  reload: () => Promise<void>
}

export default function PlanLayout() {
  const { planId } = useParams<{ planId: string }>()
  const location = useLocation()
  const [plan, setPlan] = useState<LessonPlan | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const reload = useCallback(async () => {
    if (!planId) return
    setLoading(true)
    setError('')
    try {
      setPlan(await api.getPlan(planId))
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : 'Could not load this lesson plan.')
    } finally {
      setLoading(false)
    }
  }, [planId])

  useEffect(() => {
    void reload()
  }, [reload])

  const canReview = useMemo(
    () => plan?.status === 'Pending Teacher Review' || plan?.status === 'Needs Revision',
    [plan],
  )
  const isSubPage = location.pathname.endsWith('/edit') || location.pathname.endsWith('/decide')
  const isReviewPage = location.pathname.endsWith('/review')

  if (loading) {
    return <div className="state-card">Loading lesson plan…</div>
  }

  if (error || !plan) {
    return (
      <div className="state-card">
        <h2>Lesson plan not found</h2>
        <p>{error || 'This lesson plan does not exist in the local store.'}</p>
        <Link to="/plans" className="button button-secondary">
          Back to lesson plans
        </Link>
      </div>
    )
  }

  return (
    <div className="plan-page">
      <Link to="/plans" className="back-link">
        <ArrowLeft size={15} /> All lesson plans
      </Link>

      <header className="plan-header">
        <div className="plan-header-main">
          <div className="plan-header-top">
            <StatusBadge status={plan.status} />
            <span>{plan.plan_id}</span>
            <em>
              <CalendarClock size={14} /> Updated {formatDate(plan.updated_at)}
            </em>
          </div>
          <h1>{plan.request.topic}</h1>
          <p>
            {plan.request.subject} · {plan.request.class_name} · {plan.curriculum.curriculum_version}
          </p>
          <div className="plan-facts">
            <span>
              <Clock3 size={14} /> {plan.timing.requested_minutes} min requested
            </span>
            <span>
              <Layers3 size={14} /> {plan.activities.length} activities
            </span>
            <span>
              <Target size={14} /> {plan.objectives.length} objectives
            </span>
            <span>
              <CheckCircle2 size={14} /> {plan.timing.planned_minutes} min planned
            </span>
          </div>
        </div>
        {!isSubPage && !isReviewPage ? (
          <div className="plan-header-actions">
            {canReview ? (
              <>
                <Link to={`/plans/${plan.plan_id}/edit`} className="button button-secondary">
                  <Edit3 size={16} /> Edit plan
                </Link>
                <Link to={`/plans/${plan.plan_id}/decide`} className="button button-primary">
                  <ClipboardCheck size={16} /> Record decision
                </Link>
              </>
            ) : (
              <span className="locked-note">
                <Lock size={15} />
                {plan.status === 'Approved' ? 'Approved plans are locked.' : 'Rejected plans are locked.'}
              </span>
            )}
          </div>
        ) : null}
      </header>

      {!isSubPage ? (
        <nav className="plan-tabs" aria-label="Lesson plan sections">
          <NavLink to={`/plans/${plan.plan_id}`} end>
            Overview
          </NavLink>
          <NavLink to={`/plans/${plan.plan_id}/activities`}>
            Activity sequence <span>{plan.activities.length}</span>
          </NavLink>
          <NavLink to={`/plans/${plan.plan_id}/review`}>
            Review trail <span>{plan.review.history.length}</span>
          </NavLink>
        </nav>
      ) : null}

      <Outlet context={{ plan, setPlan, reload } satisfies PlanContextValue} />
    </div>
  )
}
