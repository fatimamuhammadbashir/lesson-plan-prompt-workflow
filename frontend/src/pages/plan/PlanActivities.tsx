import { useOutletContext } from 'react-router-dom'
import { ActivityCard } from '../../components/ActivityCard'
import type { PlanContextValue } from '../PlanLayout'

export default function PlanActivities() {
  const { plan } = useOutletContext<PlanContextValue>()

  return (
    <div className="activities-page">
      <div className="content-heading">
        <span>Activity sequence</span>
        <h2>Why each activity earned its place</h2>
        <p>
          The score combines learner preferences, approved outcomes, prerequisites, previous
          results and weak topics. Open a card to see the breakdown.
        </p>
      </div>

      <div className="activity-list">
        {plan.activities.map((activity) => (
          <ActivityCard key={activity.activity_id} activity={activity} />
        ))}
      </div>
    </div>
  )
}
