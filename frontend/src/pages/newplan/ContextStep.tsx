import { useState } from 'react'
import { useNavigate, useOutletContext } from 'react-router-dom'
import { ArrowRight, Check, Clock3 } from 'lucide-react'
import type { NewPlanContextValue } from '../NewPlanLayout'

export default function ContextStep() {
  const {
    draft,
    setDraft,
    currentTopic,
    subjects,
    classes,
    topics,
    changeSubject,
    changeClass,
    changeTopic,
    toggleOutcome,
    maxOutcomes,
  } = useOutletContext<NewPlanContextValue>()
  const navigate = useNavigate()
  const [error, setError] = useState('')

  function next() {
    if (!currentTopic) {
      setError('Choose an approved topic before continuing.')
      return
    }
    if (!draft.outcomeIds.length) {
      setError('Select at least one approved learning outcome.')
      return
    }
    navigate('/plans/new/learners')
  }

  return (
    <section className="flow-card">
      <div className="step-heading">
        <span>Step 1</span>
        <h2>Lesson context</h2>
        <p>Everything here is checked against the approved curriculum file.</p>
      </div>

      <div className="form-grid three">
        <label className="field">
          <span>Subject</span>
          <select value={draft.subject} onChange={(event) => changeSubject(event.target.value)}>
            {subjects.map((subject) => (
              <option key={subject} value={subject}>
                {subject}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          <span>Class</span>
          <select value={draft.className} onChange={(event) => changeClass(event.target.value)}>
            {classes.map((className) => (
              <option key={className} value={className}>
                {className}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          <span>Approved topic</span>
          <select value={draft.topic} onChange={(event) => changeTopic(event.target.value)}>
            {topics.map((topic) => (
              <option key={topic.topic} value={topic.topic}>
                {topic.topic}
              </option>
            ))}
          </select>
        </label>
      </div>

      {currentTopic ? (
        <div className="context-note">
          <div>
            <strong>{currentTopic.topic}</strong>
            <span>
              {currentTopic.subject} · {currentTopic.class_name}
            </span>
          </div>
          <div>
            <span>
              <Clock3 size={14} /> {currentTopic.min_duration_minutes}–{currentTopic.max_duration_minutes} min
            </span>
            <span>{currentTopic.outcomes.length} approved outcomes</span>
          </div>
        </div>
      ) : null}

      <div className="duration-block">
        <div className="duration-label">
          <div>
            <span className="field-title">Lesson duration</span>
            <p>Validated against the topic range.</p>
          </div>
          <strong>{draft.duration} minutes</strong>
        </div>
        <input
          type="range"
          min={currentTopic?.min_duration_minutes ?? 20}
          max={currentTopic?.max_duration_minutes ?? 180}
          step={5}
          value={draft.duration}
          onChange={(event) =>
            setDraft((current) => ({ ...current, duration: Number(event.target.value) }))
          }
        />
        <div className="range-labels">
          <span>{currentTopic?.min_duration_minutes ?? 20} min</span>
          <span>{currentTopic?.max_duration_minutes ?? 180} min</span>
        </div>
      </div>

      <div className="outcome-section">
        <div className="field-heading">
          <span className="field-title">Approved learning outcomes</span>
          <span>
            {draft.outcomeIds.length} of {currentTopic?.outcomes.length ?? 0} selected
            {maxOutcomes ? ` · max ${maxOutcomes}` : ''}
          </span>
        </div>
        <div className="outcome-list">
          {currentTopic?.outcomes.map((outcome) => {
            const selected = draft.outcomeIds.includes(outcome.id)
            return (
              <button
                key={outcome.id}
                type="button"
                className={`outcome-option ${selected ? 'selected' : ''}`}
                onClick={() => toggleOutcome(outcome.id)}
              >
                <span className="outcome-check">{selected ? <Check size={13} /> : null}</span>
                <span className="outcome-body">
                  <em>{outcome.id}</em>
                  <strong>{outcome.text}</strong>
                  <small>Prerequisites: {outcome.prerequisite_tags.join(', ') || 'none'}</small>
                </span>
              </button>
            )
          })}
        </div>
      </div>

      {error ? <p className="form-error">{error}</p> : null}

      <div className="flow-actions">
        <span />
        <button type="button" className="button button-primary" onClick={next}>
          Continue <ArrowRight size={16} />
        </button>
      </div>
    </section>
  )
}
