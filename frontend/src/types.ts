export interface Outcome {
  id: string
  text: string
  assessment: string
  prerequisite_tags: string[]
}

export interface Topic {
  subject: string
  class_name: string
  topic: string
  min_duration_minutes: number
  max_duration_minutes: number
  required_activity_tags: string[]
  outcomes: Outcome[]
}

export interface Limits {
  min_duration_minutes: number
  max_duration_minutes: number
  max_learner_preferences: number
  max_outcomes: number
  max_text_length: number
}

export interface Meta {
  topics: Topic[]
  allowed_preferences: string[]
  limits: Limits
  phase_order: string[]
  statuses: string[]
}

export interface PreviousResults {
  class_average: number
  completion_rate: number
  weak_topics: string[]
  mastered_tags: string[]
}

export interface LessonRequest {
  subject: string
  class_name: string
  topic: string
  duration_minutes: number
  learner_preferences: string[]
  previous_results: PreviousResults
  approved_outcome_ids: string[]
  teacher_notes: string
}

export interface ScoreFactor {
  raw: number
  weight: number
  points: number
}

export type ScoreBreakdown = Record<string, ScoreFactor>

export interface PlanActivity {
  activity_id: string
  title: string
  description: string
  subject: string
  topics: string[]
  phase: string
  duration_minutes: number
  tags: string[]
  prerequisite_tags: string[]
  targets_tags: string[]
  supports_outcomes: string[]
  materials: string[]
  assessment_evidence: string
  difficulty: string
  score: number
  score_breakdown: ScoreBreakdown
  reasons: string[]
  warnings: string[]
  sequence: number
}

export interface Objective {
  id: string
  text: string
  source_outcome_id?: string
  success_criteria?: string
}

export interface Assessment {
  formative: string[]
  summative: string
  success_criteria: string[]
}

export interface Conclusion {
  summary: string
  next_steps: string[]
  exit_prompt: string
}

export interface ReviewHistoryEntry {
  timestamp_utc: string
  action: string
  actor: string
  from_status: string | null
  to_status: string
  details: {
    changed_fields?: string[]
    note?: string
    decision?: string
    notes?: string
    message?: string
  }
}

export interface Review {
  status: string
  reviewer: string | null
  decided_at: string | null
  notes: string | null
  history: ReviewHistoryEntry[]
}

export interface Coverage {
  requested_outcomes: string[]
  supported_outcomes: string[]
  uncovered_outcomes: string[]
}

export interface LessonPlan {
  schema_version: number
  plan_id: string
  status: string
  created_at: string
  updated_at: string
  request: LessonRequest
  curriculum: {
    curriculum_version: string
    subject: string
    class_name: string
    topic: string
    outcomes: Outcome[]
  }
  objectives: Objective[]
  materials: string[]
  activities: PlanActivity[]
  assessment: Assessment
  conclusion: Conclusion | string
  timing: {
    requested_minutes: number
    planned_minutes: number
    flex_minutes: number
  }
  selection_summary: {
    candidate_count: number
    selected_count: number
    unallocated_minutes: number
  }
  warnings: string[]
  coverage: Coverage
  review: Review
}

export interface PlanSummary {
  plan_id: string
  status: string
  reviewer: string | null
  decided_at: string | null
  subject: string
  class_name: string
  topic: string
  duration_minutes: number | null
  activity_count: number
  objective_count: number
  updated_at: string
}

export type Decision = 'approved' | 'rejected' | 'needs_revision'

export interface ApiErrorShape {
  error: {
    type: string
    message: string
    field?: string
    details?: unknown
  }
}
