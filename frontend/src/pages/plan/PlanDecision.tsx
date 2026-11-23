import { useState } from 'react'
import { Link, useNavigate, useOutletContext } from 'react-router-dom'
import { ArrowLeft, CheckCircle2, RotateCcw, XCircle } from 'lucide-react'
import { api, ApiError } from '../../api'
import { useToast } from '../../components/ToastProvider'
import type { Decision } from '../../types'
import type { PlanContextValue } from '../PlanLayout'

const options: Array<{
  value: Decision
  title: string
  description: string
  icon: typeof CheckCircle2
}> = [
  {
    value: 'approved',
    title: 'Approve',
    description: 'The plan is ready to teach.',
    icon: CheckCircle2,
  },
  {
    value: 'needs_revision',
    title: 'Needs revision',
    description: 'Send it back with specific changes.',
    icon: RotateCcw,
  },
  {
    value: 'rejected',
    title: 'Reject',
    description: 'Do not use this draft.',
    icon: XCircle,
  },
]

export default function PlanDecision() {
  const { plan, setPlan } = useOutletContext<PlanContextValue>()
  const navigate = useNavigate()
  const { pushToast } = useToast()
  const [decision, setDecision] = useState<Decision>('approved')
  const [reviewer, setReviewer] = useState('')
  const [notes, setNotes] = useState('')
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  async function submit(event: React.FormEvent) {
    event.preventDefault()
    setError('')
    if (!reviewer.trim()) {
      setError('Add the reviewer name.')
      return
    }
    if (decision !== 'approved' && notes.trim().length < 3) {
      setError('Notes are required when requesting revision or rejecting a plan.')
      return
    }
    setSaving(true)
    try {
      const updated = await api.reviewPlan(plan.plan_id, {
        decision,
        reviewer: reviewer.trim(),
        notes: notes.trim(),
      })
      setPlan(updated)
      pushToast('success', 'Decision recorded', `${plan.plan_id} is now ${updated.status}.`)
      navigate(`/plans/${plan.plan_id}/review`)
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : 'Could not record the decision.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="form-page">
      <Link to={`/plans/${plan.plan_id}/review`} className="back-link">
        <ArrowLeft size={15} /> Back to review trail
      </Link>
      <form className="form-card" onSubmit={submit}>
        <div className="step-heading">
          <span>Teacher review</span>
          <h2>Record a decision</h2>
          <p>Your decision and notes are added to the plan audit trail.</p>
        </div>

        <div className="decision-options">
          {options.map((option) => {
            const Icon = option.icon
            return (
              <button
                key={option.value}
                type="button"
                className={`decision-option ${decision === option.value ? 'selected' : ''}`}
                onClick={() => setDecision(option.value)}
              >
                <Icon size={20} />
                <strong>{option.title}</strong>
                <span>{option.description}</span>
              </button>
            )
          })}
        </div>

        <div className="form-grid two">
          <label className="field">
            <span>Reviewer</span>
            <input
              value={reviewer}
              onChange={(event) => setReviewer(event.target.value)}
              placeholder="e.g. Ms. Rivera"
              maxLength={100}
              autoFocus
            />
          </label>
          <div className="field">
            <span>Plan</span>
            <div className="readonly">{plan.plan_id}</div>
          </div>
        </div>

        <label className="field">
          <span>
            Review notes {decision !== 'approved' ? '(required)' : '(optional)'}
          </span>
          <textarea
            rows={5}
            value={notes}
            onChange={(event) => setNotes(event.target.value)}
            maxLength={1000}
            placeholder="Explain the decision or point to a specific activity."
          />
        </label>

        {error ? <p className="form-error">{error}</p> : null}

        <div className="form-actions">
          <Link to={`/plans/${plan.plan_id}/review`} className="button button-secondary">
            Cancel
          </Link>
          <button type="submit" className="button button-primary" disabled={saving}>
            {saving ? 'Recording…' : 'Record decision'}
          </button>
        </div>
      </form>
    </div>
  )
}
