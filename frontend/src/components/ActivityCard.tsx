import { AlertTriangle, Check, ChevronDown, Clock3 } from 'lucide-react'
import type { PlanActivity } from '../types'
import { factorLabel, phaseLabel } from '../utils'

export function ActivityCard({ activity }: { activity: PlanActivity }) {
  const percent = Math.round(activity.score * 100)

  return (
    <article className="activity">
      <div className="activity-head">
        <span className="activity-index">{String(activity.sequence).padStart(2, '0')}</span>
        <div className="activity-heading">
          <div className="activity-kicker">
            <span className={`phase phase-${activity.phase}`}>{phaseLabel(activity.phase)}</span>
            <span>
              <Clock3 size={13} /> {activity.duration_minutes} min
            </span>
            <span>{activity.difficulty}</span>
          </div>
          <h2>{activity.title}</h2>
          <p>{activity.description}</p>
        </div>
        <div className="activity-score" aria-label={`Activity score ${percent} out of 100`}>
          <strong>{percent}</strong>
          <span>/100</span>
          <div className="score-bar">
            <span style={{ width: `${percent}%` }} />
          </div>
        </div>
      </div>

      <div className="activity-grid">
        <section className="activity-reasons">
          <h3>Why this activity</h3>
          <ul>
            {activity.reasons.map((reason) => (
              <li key={reason}>
                <Check size={14} />
                <span>{reason}</span>
              </li>
            ))}
          </ul>
        </section>

        <section className="activity-facts">
          <h3>Activity details</h3>
          <dl>
            <div>
              <dt>Outcomes</dt>
              <dd>{activity.supports_outcomes.join(', ')}</dd>
            </div>
            <div>
              <dt>Materials</dt>
              <dd>{activity.materials.join(', ')}</dd>
            </div>
            <div>
              <dt>Evidence</dt>
              <dd>{activity.assessment_evidence}</dd>
            </div>
          </dl>
        </section>
      </div>

      {activity.warnings.length ? (
        <div className="activity-warnings">
          {activity.warnings.map((warning) => (
            <p key={warning}>
              <AlertTriangle size={15} />
              {warning}
            </p>
          ))}
        </div>
      ) : null}

      <details className="activity-breakdown">
        <summary>
          View scoring detail
          <ChevronDown size={15} />
        </summary>
        <div className="breakdown">
          {Object.entries(activity.score_breakdown).map(([factor, part]) => (
            <div key={factor} className="breakdown-row">
              <span>{factorLabel(factor)}</span>
              <div className="breakdown-bar">
                <span style={{ width: `${Math.round(part.raw * 100)}%` }} />
              </div>
              <em>{Math.round(part.raw * 100)}%</em>
            </div>
          ))}
        </div>
      </details>
    </article>
  )
}
