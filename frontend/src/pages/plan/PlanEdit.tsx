import { useState } from 'react'
import { Link, useNavigate, useOutletContext } from 'react-router-dom'
import { ArrowLeft, Plus, Save, Trash2 } from 'lucide-react'
import { api, ApiError, type EditPayload } from '../../api'
import { useToast } from '../../components/ToastProvider'
import type { Objective } from '../../types'
import type { PlanContextValue } from '../PlanLayout'
import { normalizeConclusion } from '../../utils'

interface ActivityDraft {
  activity_id: string
  title: string
  phase: string
  duration_minutes: number
}

const toLines = (items: string[]) => items.join('\n')
const fromLines = (value: string) =>
  value
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)

export default function PlanEdit() {
  const { plan, setPlan } = useOutletContext<PlanContextValue>()
  const navigate = useNavigate()
  const { pushToast } = useToast()
  const conclusion = normalizeConclusion(plan.conclusion)

  const [objectives, setObjectives] = useState<Objective[]>(plan.objectives.map((item) => ({ ...item })))
  const [materials, setMaterials] = useState(toLines(plan.materials))
  const [activities, setActivities] = useState<ActivityDraft[]>(
    plan.activities.map((activity) => ({
      activity_id: activity.activity_id,
      title: activity.title,
      phase: activity.phase,
      duration_minutes: activity.duration_minutes,
    })),
  )
  const [formative, setFormative] = useState(toLines(plan.assessment.formative))
  const [summative, setSummative] = useState(plan.assessment.summative)
  const [successCriteria, setSuccessCriteria] = useState(toLines(plan.assessment.success_criteria))
  const [summary, setSummary] = useState(conclusion.summary)
  const [nextSteps, setNextSteps] = useState(toLines(conclusion.next_steps))
  const [exitPrompt, setExitPrompt] = useState(conclusion.exit_prompt)
  const [note, setNote] = useState('')
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  function updateObjective(index: number, patch: Partial<Objective>) {
    setObjectives((current) =>
      current.map((objective, currentIndex) =>
        currentIndex === index ? { ...objective, ...patch } : objective,
      ),
    )
  }

  function updateActivity(index: number, patch: Partial<ActivityDraft>) {
    setActivities((current) =>
      current.map((activity, currentIndex) =>
        currentIndex === index ? { ...activity, ...patch } : activity,
      ),
    )
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault()
    setError('')
    if (objectives.some((objective) => !objective.text.trim())) {
      setError('Every objective needs text.')
      return
    }
    if (activities.some((activity) => !activity.title.trim())) {
      setError('Every activity needs a title.')
      return
    }
    const payload: EditPayload = {
      objectives: objectives.map((objective) => ({
        ...objective,
        text: objective.text.trim(),
        success_criteria: objective.success_criteria?.trim() || undefined,
      })),
      materials: fromLines(materials),
      activities,
      assessment: {
        formative: fromLines(formative),
        summative: summative.trim(),
        success_criteria: fromLines(successCriteria),
      },
      conclusion: {
        summary: summary.trim(),
        next_steps: fromLines(nextSteps),
        exit_prompt: exitPrompt.trim(),
      },
      note: note.trim(),
    }
    setSaving(true)
    try {
      const updated = await api.editPlan(plan.plan_id, payload)
      setPlan(updated)
      pushToast('success', 'Draft updated', 'The plan is back in Pending Teacher Review.')
      navigate(`/plans/${plan.plan_id}`)
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : 'Could not save the edits.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="form-page">
      <Link to={`/plans/${plan.plan_id}`} className="back-link">
        <ArrowLeft size={15} /> Back to lesson plan
      </Link>
      <form className="form-card form-card-wide" onSubmit={submit}>
        <div className="step-heading">
          <span>Teacher editing</span>
          <h2>Edit lesson plan</h2>
          <p>Edits are validated and return the plan to Pending Teacher Review.</p>
        </div>

        <section className="edit-block">
          <div className="edit-block-head">
            <h3>Objectives</h3>
            <button
              type="button"
              className="button button-secondary button-small"
              onClick={() =>
                setObjectives((current) => [
                  ...current,
                  { id: `OBJ-${current.length + 1}`, text: '', success_criteria: '' },
                ])
              }
            >
              <Plus size={14} /> Add objective
            </button>
          </div>
          <div className="editor-list">
            {objectives.map((objective, index) => (
              <div key={objective.id} className="editor-item">
                <div className="editor-item-head">
                  <span>{objective.id}</span>
                  {objective.source_outcome_id ? <em>{objective.source_outcome_id}</em> : null}
                  <button
                    type="button"
                    className="icon-button"
                    aria-label={`Remove objective ${index + 1}`}
                    onClick={() =>
                      setObjectives((current) => current.filter((_, itemIndex) => itemIndex !== index))
                    }
                  >
                    <Trash2 size={15} />
                  </button>
                </div>
                <label className="field">
                  <span>Objective</span>
                  <textarea
                    rows={2}
                    value={objective.text}
                    onChange={(event) => updateObjective(index, { text: event.target.value })}
                  />
                </label>
                <label className="field">
                  <span>Success criteria</span>
                  <input
                    value={objective.success_criteria ?? ''}
                    onChange={(event) =>
                      updateObjective(index, { success_criteria: event.target.value })
                    }
                  />
                </label>
              </div>
            ))}
          </div>
        </section>

        <section className="edit-block">
          <h3>Materials</h3>
          <label className="field">
            <span>One per line</span>
            <textarea rows={4} value={materials} onChange={(event) => setMaterials(event.target.value)} />
          </label>
        </section>

        <section className="edit-block">
          <h3>Activity sequence</h3>
          <div className="editor-list">
            {activities.map((activity, index) => (
              <div key={activity.activity_id} className="activity-editor">
                <span>{index + 1}</span>
                <label className="field grow">
                  <span>Title</span>
                  <input
                    value={activity.title}
                    onChange={(event) => updateActivity(index, { title: event.target.value })}
                  />
                </label>
                <label className="field phase-field">
                  <span>Phase</span>
                  <select
                    value={activity.phase}
                    onChange={(event) => updateActivity(index, { phase: event.target.value })}
                  >
                    {['starter', 'main', 'practice', 'plenary'].map((phase) => (
                      <option key={phase} value={phase}>
                        {phase}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="field minutes-field">
                  <span>Minutes</span>
                  <input
                    type="number"
                    min={1}
                    max={180}
                    value={activity.duration_minutes}
                    onChange={(event) =>
                      updateActivity(index, { duration_minutes: Number(event.target.value) })
                    }
                  />
                </label>
              </div>
            ))}
          </div>
        </section>

        <section className="edit-block">
          <h3>Assessment</h3>
          <label className="field">
            <span>Formative checks · one per line</span>
            <textarea rows={3} value={formative} onChange={(event) => setFormative(event.target.value)} />
          </label>
          <label className="field">
            <span>Summative assessment</span>
            <textarea rows={2} value={summative} onChange={(event) => setSummative(event.target.value)} />
          </label>
          <label className="field">
            <span>Success criteria · one per line</span>
            <textarea
              rows={3}
              value={successCriteria}
              onChange={(event) => setSuccessCriteria(event.target.value)}
            />
          </label>
        </section>

        <section className="edit-block">
          <h3>Conclusion</h3>
          <label className="field">
            <span>Summary</span>
            <textarea rows={2} value={summary} onChange={(event) => setSummary(event.target.value)} />
          </label>
          <label className="field">
            <span>Next steps · one per line</span>
            <textarea rows={3} value={nextSteps} onChange={(event) => setNextSteps(event.target.value)} />
          </label>
          <label className="field">
            <span>Exit prompt</span>
            <input value={exitPrompt} onChange={(event) => setExitPrompt(event.target.value)} />
          </label>
        </section>

        <section className="edit-block">
          <label className="field">
            <span>Edit note for the review history</span>
            <input
              value={note}
              onChange={(event) => setNote(event.target.value)}
              placeholder="What changed and why?"
              maxLength={500}
            />
          </label>
        </section>

        {error ? <p className="form-error">{error}</p> : null}

        <div className="form-actions">
          <Link to={`/plans/${plan.plan_id}`} className="button button-secondary">
            Cancel
          </Link>
          <button type="submit" className="button button-primary" disabled={saving}>
            <Save size={16} /> {saving ? 'Saving…' : 'Save draft'}
          </button>
        </div>
      </form>
    </div>
  )
}
