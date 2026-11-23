import { useState } from 'react'
import { useNavigate, useOutletContext } from 'react-router-dom'
import { ArrowLeft, Loader2, Sparkles } from 'lucide-react'
import { api, ApiError } from '../../api'
import { useToast } from '../../components/ToastProvider'
import type { LessonRequest } from '../../types'
import type { NewPlanContextValue } from '../NewPlanLayout'

export default function ReviewStep() {
  const { draft, setDraft, currentTopic } = useOutletContext<NewPlanContextValue>()
  const navigate = useNavigate()
  const { pushToast } = useToast()
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  const outcomes =
    currentTopic?.outcomes.filter((outcome) => draft.outcomeIds.includes(outcome.id)) ?? []

  async function generate() {
    setError('')
    if (!currentTopic) return
    const payload: LessonRequest = {
      subject: draft.subject,
      class_name: draft.className,
      topic: draft.topic,
      duration_minutes: draft.duration,
      learner_preferences: draft.preferences,
      previous_results: {
        class_average: draft.classAverage,
        completion_rate: draft.completionRate,
        weak_topics: draft.weakTopics,
        mastered_tags: draft.masteredTags,
      },
      approved_outcome_ids: draft.outcomeIds,
      teacher_notes: draft.notes.trim(),
    }
    setSaving(true)
    try {
      const plan = await api.createPlan(payload)
      pushToast('success', 'Lesson plan created', 'The draft is ready for teacher review.')
      navigate(`/plans/${plan.plan_id}`)
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : 'Could not create the lesson plan.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <section className="flow-card">
      <div className="step-heading">
        <span>Step 3</span>
        <h2>Review the brief</h2>
        <p>Check the context, then create the draft. You can edit it before making a decision.</p>
      </div>

      <div className="brief-summary">
        <div className="brief-title">
          <div>
            <span>
              {draft.subject} · {draft.className}
            </span>
            <h3>{draft.topic}</h3>
          </div>
          <strong>{draft.duration} minutes</strong>
        </div>
        <div className="brief-grid">
          <div>
            <span>Approved outcomes</span>
            <ul>
              {outcomes.map((outcome) => (
                <li key={outcome.id}>
                  <em>{outcome.id}</em>
                  {outcome.text}
                </li>
              ))}
            </ul>
          </div>
          <div>
            <span>Learner preferences</span>
            <p>{draft.preferences.join(', ') || 'None selected'}</p>
            <span>Previous results</span>
            <p>
              Average {draft.classAverage}% · completion{' '}
              {Math.round(draft.completionRate * 100)}%
            </p>
            <span>Class signals</span>
            <p>
              Weak: {draft.weakTopics.join(', ') || 'none'} · mastered:{' '}
              {draft.masteredTags.join(', ') || 'none'}
            </p>
          </div>
        </div>
      </div>

      <label className="field">
        <span>Teacher notes <em>optional</em></span>
        <textarea
          rows={4}
          value={draft.notes}
          onChange={(event) =>
            setDraft((current) => ({ ...current, notes: event.target.value }))
          }
          placeholder="Anything the planner should know? For example: two students were absent last lesson."
          maxLength={500}
        />
      </label>

      <div className="create-panel">
        <div>
          <span className="eyebrow">Ready to create</span>
          <h3>Generate a structured lesson draft</h3>
          <p>
            You will get objectives, materials, an activity sequence, assessment and a
            complete explanation for every recommendation.
          </p>
        </div>
        <button type="button" className="button button-primary button-large" disabled={saving} onClick={generate}>
          {saving ? <Loader2 size={18} className="spin" /> : <Sparkles size={18} />}
          {saving ? 'Creating…' : 'Create lesson plan'}
        </button>
      </div>

      {error ? <p className="form-error">{error}</p> : null}

      <div className="flow-actions">
        <button
          type="button"
          className="button button-secondary"
          onClick={() => navigate('/plans/new/learners')}
        >
          <ArrowLeft size={16} /> Back
        </button>
        <span className="muted-note">Drafts always start in Pending Teacher Review.</span>
      </div>
    </section>
  )
}
