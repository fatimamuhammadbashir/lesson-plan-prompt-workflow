import { ChevronDown, Clock3, Target } from 'lucide-react'
import { PageHeader } from '../components/PageHeader'
import { useMeta } from '../hooks/useMeta'

export default function CurriculumPage() {
  const { meta, loading, error, reload } = useMeta()

  if (loading) {
    return <div className="state-card">Loading approved curriculum…</div>
  }

  if (error || !meta) {
    return (
      <div className="state-card">
        <h2>Curriculum unavailable</h2>
        <p>{error || 'No curriculum data was returned.'}</p>
        <button type="button" className="button button-secondary" onClick={() => void reload()}>
          Try again
        </button>
      </div>
    )
  }

  const subjects = [...new Set(meta.topics.map((topic) => topic.subject))]

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Reference"
        title="Approved curriculum"
        description="The source of truth for every lesson plan. Topics and outcomes cannot be invented by the planner."
      />

      <div className="curriculum-list">
        {subjects.map((subject) => {
          const topics = meta.topics.filter((topic) => topic.subject === subject)
          const classNames = [...new Set(topics.map((topic) => topic.class_name))]
          return (
            <section key={subject} className="curriculum-subject">
              <div className="curriculum-subject-head">
                <h2>{subject}</h2>
                <span>{classNames.join(' · ')}</span>
              </div>
              <div className="curriculum-topics">
                {topics.map((topic) => (
                  <details key={`${topic.class_name}-${topic.topic}`} className="topic-card">
                    <summary>
                      <div>
                        <span>{topic.class_name}</span>
                        <h3>{topic.topic}</h3>
                      </div>
                      <div className="topic-meta">
                        <span>
                          <Clock3 size={13} /> {topic.min_duration_minutes}–{topic.max_duration_minutes} min
                        </span>
                        <span>
                          <Target size={13} /> {topic.outcomes.length} outcomes
                        </span>
                        <ChevronDown size={16} />
                      </div>
                    </summary>
                    <div className="topic-outcomes">
                      {topic.outcomes.map((outcome) => (
                        <div key={outcome.id} className="outcome-item">
                          <span>{outcome.id}</span>
                          <p>{outcome.text}</p>
                          <em>{outcome.assessment}</em>
                          <small>
                            Prerequisites: {outcome.prerequisite_tags.join(', ') || 'none'}
                          </small>
                        </div>
                      ))}
                    </div>
                  </details>
                ))}
              </div>
            </section>
          )
        })}
      </div>
    </div>
  )
}
