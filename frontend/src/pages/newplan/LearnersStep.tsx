import { useState } from 'react'
import { useNavigate, useOutletContext } from 'react-router-dom'
import { ArrowLeft, ArrowRight, Check } from 'lucide-react'
import { TagInput } from '../../components/TagInput'
import type { NewPlanContextValue } from '../NewPlanLayout'

export default function LearnersStep() {
  const {
    draft,
    setDraft,
    meta,
    maxPreferences,
    togglePreference,
  } = useOutletContext<NewPlanContextValue>()
  const navigate = useNavigate()
  const [error, setError] = useState('')

  function next() {
    if (!draft.preferences.length) {
      setError('Select at least one learner preference.')
      return
    }
    if (draft.weakTopics.some((tag) => draft.masteredTags.includes(tag))) {
      setError('A topic cannot be both weak and mastered.')
      return
    }
    navigate('/plans/new/review')
  }

  return (
    <section className="flow-card">
      <div className="step-heading">
        <span>Step 2</span>
        <h2>Know the learners</h2>
        <p>These signals influence ranking. They are listed with every recommendation.</p>
      </div>

      <div className="field-heading">
        <span className="field-title">Learner preferences</span>
        <span>
          {draft.preferences.length} of {maxPreferences} selected
        </span>
      </div>
      <div className="preference-list">
        {meta.allowed_preferences.map((preference) => {
          const selected = draft.preferences.includes(preference)
          return (
            <button
              key={preference}
              type="button"
              className={`preference ${selected ? 'selected' : ''}`}
              onClick={() => togglePreference(preference)}
            >
              {selected ? <Check size={14} /> : null}
              {preference}
            </button>
          )
        })}
      </div>

      <div className="signals-grid">
        <div className="signal-card">
          <div className="signal-head">
            <span className="field-title">Class average</span>
            <strong>{draft.classAverage}%</strong>
          </div>
          <input
            type="range"
            min={0}
            max={100}
            value={draft.classAverage}
            onChange={(event) =>
              setDraft((current) => ({
                ...current,
                classAverage: Number(event.target.value),
              }))
            }
          />
          <p>Below 60% favours review and scaffolded activities. Above 75% favours challenge.</p>
        </div>
        <div className="signal-card">
          <div className="signal-head">
            <span className="field-title">Completion rate</span>
            <strong>{Math.round(draft.completionRate * 100)}%</strong>
          </div>
          <input
            type="range"
            min={0}
            max={100}
            value={Math.round(draft.completionRate * 100)}
            onChange={(event) =>
              setDraft((current) => ({
                ...current,
                completionRate: Number(event.target.value) / 100,
              }))
            }
          />
          <p>Below 70% favours interactive and hands-on activities.</p>
        </div>
      </div>

      <div className="signals-grid">
        <TagInput
          label="Weak topics"
          value={draft.weakTopics}
          onChange={(weakTopics) => setDraft((current) => ({ ...current, weakTopics }))}
          placeholder="e.g. chlorophyll"
          hint="Activities targeting these get a boost"
        />
        <TagInput
          label="Mastered prerequisites"
          value={draft.masteredTags}
          onChange={(masteredTags) => setDraft((current) => ({ ...current, masteredTags }))}
          placeholder="e.g. cells"
          hint="Mastered tags add prerequisite credit"
        />
      </div>

      {error ? <p className="form-error">{error}</p> : null}

      <div className="flow-actions">
        <button
          type="button"
          className="button button-secondary"
          onClick={() => navigate('/plans/new/context')}
        >
          <ArrowLeft size={16} /> Back
        </button>
        <button type="button" className="button button-primary" onClick={next}>
          Continue <ArrowRight size={16} />
        </button>
      </div>
    </section>
  )
}
