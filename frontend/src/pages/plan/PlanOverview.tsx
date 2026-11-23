import { useOutletContext } from 'react-router-dom'
import { AlertTriangle, CheckCircle2 } from 'lucide-react'
import type { PlanContextValue } from '../PlanLayout'
import { normalizeConclusion } from '../../utils'

export default function PlanOverview() {
  const { plan } = useOutletContext<PlanContextValue>()
  const conclusion = normalizeConclusion(plan.conclusion)

  return (
    <div className="plan-content">
      <div className="plan-content-main">
        <section className="content-section">
          <div className="content-heading">
            <span>Objectives</span>
            <h2>What students should learn</h2>
          </div>
          <div className="objective-list">
            {plan.objectives.map((objective, index) => (
              <article key={objective.id} className="objective-item">
                <span className="objective-number">{String(index + 1).padStart(2, '0')}</span>
                <div>
                  <div className="objective-meta">
                    <span>{objective.id}</span>
                    {objective.source_outcome_id ? <em>{objective.source_outcome_id}</em> : null}
                  </div>
                  <h3>{objective.text}</h3>
                  {objective.success_criteria ? (
                    <p>
                      <CheckCircle2 size={14} /> {objective.success_criteria}
                    </p>
                  ) : null}
                </div>
              </article>
            ))}
          </div>
        </section>

        <section className="content-section">
          <div className="content-heading">
            <span>Assessment</span>
            <h2>How learning is checked</h2>
          </div>
          <div className="assessment-list">
            <div>
              <h3>Formative evidence</h3>
              <ul>
                {plan.assessment.formative.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
            <div>
              <h3>Summative evidence</h3>
              <p>{plan.assessment.summative}</p>
            </div>
            <div>
              <h3>Success criteria</h3>
              <ul>
                {plan.assessment.success_criteria.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
          </div>
        </section>

        <section className="content-section">
          <div className="content-heading">
            <span>Conclusion</span>
            <h2>How the lesson closes</h2>
          </div>
          <p className="lead-text">{conclusion.summary}</p>
          {conclusion.next_steps.length ? (
            <div className="next-steps">
              <h3>Next steps</h3>
              <ul>
                {conclusion.next_steps.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
          ) : null}
          {conclusion.exit_prompt ? (
            <blockquote className="exit-prompt">{conclusion.exit_prompt}</blockquote>
          ) : null}
        </section>
      </div>

      <aside className="plan-content-side">
        <section className="side-card">
          <h2>Materials</h2>
          <ul className="material-list">
            {plan.materials.map((material) => (
              <li key={material}>{material}</li>
            ))}
          </ul>
        </section>

        <section className="side-card">
          <h2>Coverage</h2>
          <dl className="coverage-list">
            {plan.coverage.requested_outcomes.map((outcomeId) => (
              <div key={outcomeId}>
                <dt>{outcomeId}</dt>
                <dd className={plan.coverage.uncovered_outcomes.includes(outcomeId) ? 'miss' : ''}>
                  {plan.coverage.uncovered_outcomes.includes(outcomeId) ? 'Not covered' : 'Covered'}
                </dd>
              </div>
            ))}
          </dl>
        </section>

        {plan.warnings.length ? (
          <section className="side-card side-warning">
            <h2>
              <AlertTriangle size={16} /> Planner notes
            </h2>
            {plan.warnings.map((warning) => (
              <p key={warning}>{warning}</p>
            ))}
          </section>
        ) : null}

        <section className="side-card">
          <h2>Teacher notes</h2>
          <p>{plan.request.teacher_notes || 'No extra notes supplied.'}</p>
        </section>
      </aside>
    </div>
  )
}
