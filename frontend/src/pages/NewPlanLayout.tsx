import {
  useEffect,
  useMemo,
  useState,
  type Dispatch,
  type SetStateAction,
} from 'react'
import { Link, NavLink, Outlet, useLocation } from 'react-router-dom'
import { ArrowLeft, Check } from 'lucide-react'
import { PageHeader } from '../components/PageHeader'
import { useMeta } from '../hooks/useMeta'
import type { Meta, Topic } from '../types'

export interface NewPlanDraft {
  subject: string
  className: string
  topic: string
  duration: number
  outcomeIds: string[]
  preferences: string[]
  classAverage: number
  completionRate: number
  weakTopics: string[]
  masteredTags: string[]
  notes: string
}

export interface NewPlanContextValue {
  meta: Meta
  draft: NewPlanDraft
  setDraft: Dispatch<SetStateAction<NewPlanDraft>>
  currentTopic: Topic | null
  subjects: string[]
  classes: string[]
  topics: Topic[]
  maxOutcomes: number
  maxPreferences: number
  changeSubject: (subject: string) => void
  changeClass: (className: string) => void
  changeTopic: (topic: string) => void
  toggleOutcome: (outcomeId: string) => void
  togglePreference: (preference: string) => void
}

const steps = [
  { path: 'context', label: 'Lesson context' },
  { path: 'learners', label: 'Learner profile' },
  { path: 'review', label: 'Review & create' },
]

export default function NewPlanLayout() {
  const { meta, loading, error, reload } = useMeta()
  const [draft, setDraft] = useState<NewPlanDraft | null>(null)
  const location = useLocation()

  useEffect(() => {
    if (!meta || draft) return
    const first = meta.topics[0]
    if (!first) return
    const preferred = ['hands-on', 'visual', 'group work'].filter((item) =>
      meta.allowed_preferences.includes(item),
    )
    setDraft({
      subject: first.subject,
      className: first.class_name,
      topic: first.topic,
      duration: Math.min(Math.max(60, first.min_duration_minutes), first.max_duration_minutes),
      outcomeIds: first.outcomes.slice(0, meta.limits.max_outcomes).map((outcome) => outcome.id),
      preferences: preferred.length ? preferred : meta.allowed_preferences.slice(0, 2),
      classAverage: 58,
      completionRate: 0.72,
      weakTopics: [],
      masteredTags: [],
      notes: '',
    })
  }, [meta, draft])

  const derived = useMemo(() => {
    if (!meta || !draft) {
      return {
        subjects: [] as string[],
        classes: [] as string[],
        topics: [] as Topic[],
        currentTopic: null as Topic | null,
      }
    }
    const subjects = [...new Set(meta.topics.map((topic) => topic.subject))]
    const classes = [
      ...new Set(
        meta.topics
          .filter((topic) => topic.subject === draft.subject)
          .map((topic) => topic.class_name),
      ),
    ]
    const topics = meta.topics.filter(
      (topic) => topic.subject === draft.subject && topic.class_name === draft.className,
    )
    const currentTopic =
      topics.find((topic) => topic.topic === draft.topic) ?? null
    return { subjects, classes, topics, currentTopic }
  }, [meta, draft])

  if (loading) {
    return <div className="state-card">Loading approved curriculum…</div>
  }

  if (error || !meta || !draft) {
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

  const activeMeta = meta
  const activeDraft = draft
  const updateDraft: Dispatch<SetStateAction<NewPlanDraft>> = (action) => {
    setDraft((current) => {
      if (!current) return current
      return typeof action === 'function'
        ? (action as (previous: NewPlanDraft) => NewPlanDraft)(current)
        : action
    })
  }

  function applyTopic(selected: Topic) {
    updateDraft((current) => ({
      ...current,
      subject: selected.subject,
      className: selected.class_name,
      topic: selected.topic,
      duration: Math.min(
        Math.max(current.duration, selected.min_duration_minutes),
        selected.max_duration_minutes,
      ),
      outcomeIds: selected.outcomes
        .slice(0, activeMeta.limits.max_outcomes)
        .map((outcome) => outcome.id),
    }))
  }

  function changeSubject(subject: string) {
    const selected = activeMeta.topics.find((topic) => topic.subject === subject)
    if (selected) applyTopic(selected)
  }

  function changeClass(className: string) {
    const selected = activeMeta.topics.find(
      (topic) => topic.subject === activeDraft.subject && topic.class_name === className,
    )
    if (selected) applyTopic(selected)
  }

  function changeTopic(topic: string) {
    const selected = derived.topics.find((item) => item.topic === topic)
    if (selected) applyTopic(selected)
  }

  function toggleOutcome(outcomeId: string) {
    updateDraft((current) => {
      if (current.outcomeIds.includes(outcomeId)) {
        return { ...current, outcomeIds: current.outcomeIds.filter((id) => id !== outcomeId) }
      }
      if (current.outcomeIds.length >= activeMeta.limits.max_outcomes) return current
      return { ...current, outcomeIds: [...current.outcomeIds, outcomeId] }
    })
  }

  function togglePreference(preference: string) {
    updateDraft((current) => {
      if (current.preferences.includes(preference)) {
        return {
          ...current,
          preferences: current.preferences.filter((item) => item !== preference),
        }
      }
      if (current.preferences.length >= activeMeta.limits.max_learner_preferences) return current
      return { ...current, preferences: [...current.preferences, preference] }
    })
  }

  const context: NewPlanContextValue = {
    meta: activeMeta,
    draft: activeDraft,
    setDraft: updateDraft,
    currentTopic: derived.currentTopic,
    subjects: derived.subjects,
    classes: derived.classes,
    topics: derived.topics,
    maxOutcomes: activeMeta.limits.max_outcomes,
    maxPreferences: activeMeta.limits.max_learner_preferences,
    changeSubject,
    changeClass,
    changeTopic,
    toggleOutcome,
    togglePreference,
  }

  const activeStep = steps.findIndex((step) => location.pathname.includes(`/plans/new/${step.path}`))

  return (
    <div className="flow-page">
      <PageHeader
        eyebrow="New lesson plan"
        title="Create a lesson plan"
        description="Three short steps: set the context, tell us about the class, then review the generated draft."
        actions={
          <Link to="/plans" className="button button-secondary">
            <ArrowLeft size={15} /> Cancel
          </Link>
        }
      />

      <nav className="flow-steps" aria-label="Lesson plan steps">
        {steps.map((step, index) => (
          <NavLink
            key={step.path}
            to={`/plans/new/${step.path}`}
            className={({ isActive }) =>
              `flow-step ${isActive ? 'active' : ''} ${index < activeStep ? 'complete' : ''}`
            }
          >
            <span className="step-number">{index < activeStep ? <Check size={13} /> : index + 1}</span>
            <span>{step.label}</span>
          </NavLink>
        ))}
      </nav>

      <Outlet context={context} />
    </div>
  )
}
