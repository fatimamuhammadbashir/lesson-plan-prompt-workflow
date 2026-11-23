LESSON PLAN PROMPT WORKFLOW - DEMO
========================================================
Rule-based, offline demonstration. No API keys are used.

1. SUCCESSFUL GENERATION
--------------------------------------------------------
Plan ID: LP-DEMO-001
Status: Pending Teacher Review
Lesson: Science / Year 7 / Photosynthesis
Duration: 50 of 60 minutes
Objectives: 3 | Materials: 9 | Activities: 4

Activities and explanations:
  1. [starter] Leaf clue warm-up (10 min, score 0.6375)
      + Matches learner preferences: group work, hands-on, visual.
      + Supports approved outcome(s): SCI7-PH-01.
      + Prerequisite 'plants' is recorded as mastered.
      + Targets weak topic(s): chlorophyll.
      + Selected for the starter phase; 10 minutes fit the lesson sequence.
      ! Class average 58.0% is below 60%; this activity is not explicitly scaffolded.
  2. [main] Chlorophyll reveal (20 min, score 0.7375)
      + Matches learner preferences: group work, hands-on, visual.
      + Supports approved outcome(s): SCI7-PH-01, SCI7-PH-02.
      + Prerequisite 'cells' is recorded as mastered.
      + Prerequisite 'plants' is recorded as mastered.
      + Targets weak topic(s): chlorophyll.
      + Selected for the main phase; 20 minutes fit the lesson sequence.
      ! Class average 58.0% is below 60%; this activity is not explicitly scaffolded.
  3. [practice] Explain-it board (15 min, score 0.5375)
      + Matches learner preferences: visual.
      + Supports approved outcome(s): SCI7-PH-01, SCI7-PH-03.
      + Prerequisite 'cells' is recorded as mastered.
      + Targets weak topic(s): chlorophyll.
      + Selected for the practice phase; 15 minutes fit the lesson sequence.
      ! Class average 58.0% is below 60%; this activity is not explicitly scaffolded.
  4. [plenary] One-minute summary (5 min, score 0.4875)
      + Supports approved outcome(s): SCI7-PH-01, SCI7-PH-02, SCI7-PH-03.
      + No prerequisite tags required.
      + Selected for the plenary phase; 5 minutes fit the lesson sequence.
      ! Class average 58.0% is below 60%; this activity is not explicitly scaffolded.
Plan warnings:
  ! Class average 58.0% is below 60%; this activity is not explicitly scaffolded.
Assessment methods: 4 formative checks
Conclusion: Close the 60-minute Science lesson with a short retrieval summary and a check against the approved outcomes.
Flexible minutes: 10

2. INVALID INPUT HANDLED SAFELY
--------------------------------------------------------
Handled error (no traceback):
{
  "error": {
    "type": "validation_error",
    "message": "duration_minutes must be between 20 and 180.",
    "field": "duration_minutes"
  }
}
Handled error (no traceback):
{
  "error": {
    "type": "curriculum_error",
    "message": "Outcome 'SCI7-PH-99' is not approved for Photosynthesis.",
    "field": "approved_outcome_ids",
    "details": {
      "unknown_outcome_ids": [
        "SCI7-PH-99"
      ],
      "available_outcome_ids": [
        "SCI7-PH-01",
        "SCI7-PH-02",
        "SCI7-PH-03"
      ]
    }
  }
}

3. TEACHER EDIT BEFORE APPROVAL
--------------------------------------------------------
Status: Pending Teacher Review
Changed fields: assessment, conclusion, objectives
Edit note: Clarified the first objective, tightened the assessment criteria and added an exit prompt.
First objective: Explain how chlorophyll captures light energy and why that matters for glucose production.

4. TEACHER APPROVAL
--------------------------------------------------------
Status: Approved
Reviewer: Ms. Rivera
Notes: Objectives, assessment and timing are ready to teach.
History actions: created:Pending Teacher Review -> edited:Pending Teacher Review -> decision:Approved

5. TEACHER REJECTION
--------------------------------------------------------
Original status: Pending Teacher Review
Final status: Rejected
Reviewer: Mr. Chen
Notes: The main activity repeats the starter; choose a different practice task.

6. NEEDS REVISION, THEN RESUBMISSION
--------------------------------------------------------
After review: Needs Revision
After teacher edit: Pending Teacher Review
History actions: created:Pending Teacher Review -> decision:Needs Revision -> edited:Pending Teacher Review

DEMO COMPLETE
Plan JSON files are stored under: var\plans
Review audit log: var\review_history.jsonl
