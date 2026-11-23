"""Tests for transparent activity ranking."""

from __future__ import annotations

import unittest
from dataclasses import replace

from src.activities import ActivityLibrary
from src.curriculum import Curriculum
from src.ranking import ActivityRanker
from src.validation import PreviousResults, validate_request
from tests.helpers import DATA_DIR, config, sample_request


class RankingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = config()
        self.curriculum = Curriculum.load(DATA_DIR / "curriculum.json")
        self.library = ActivityLibrary.load(
            DATA_DIR / "activities.json",
            phases=self.config["phase_order"],
        )
        self.request = validate_request(sample_request(), self.curriculum, self.config)
        self.topic = self.curriculum.get_topic("Science", "Year 7", "Photosynthesis")
        self.outcomes = self.curriculum.validate_outcomes(
            self.topic,
            list(self.request.approved_outcome_ids),
        )
        self.ranker = ActivityRanker(self.config)
        self.ranked = self.ranker.rank(
            self.library.for_topic("Science", "Photosynthesis"),
            self.request,
            self.outcomes,
        )

    def by_id(self, activity_id: str) -> dict:
        return next(item for item in self.ranked if item["activity_id"] == activity_id)

    def test_results_are_sorted_by_score(self) -> None:
        scores = [item["score"] for item in self.ranked]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_score_equals_breakdown_points(self) -> None:
        for item in self.ranked:
            total = sum(part["points"] for part in item["score_breakdown"].values())
            self.assertAlmostEqual(item["score"], total, places=4)
            self.assertGreaterEqual(item["score"], 0.0)
            self.assertLessEqual(item["score"], 1.0)

    def test_every_activity_has_reasons_and_breakdown(self) -> None:
        expected = {
            "preference_match",
            "outcome_alignment",
            "prerequisite_readiness",
            "previous_results_fit",
            "weak_topic_alignment",
        }
        for item in self.ranked:
            self.assertTrue(item["reasons"])
            self.assertEqual(set(item["score_breakdown"]), expected)
            for part in item["score_breakdown"].values():
                self.assertIn("raw", part)
                self.assertIn("weight", part)
                self.assertIn("points", part)

    def test_preference_match_is_explained(self) -> None:
        activity = self.by_id("ACT-PH-03")
        self.assertEqual(activity["score_breakdown"]["preference_match"]["raw"], 1.0)
        self.assertTrue(
            any("Matches learner preferences" in reason for reason in activity["reasons"])
        )

    def test_outcome_alignment_is_explained(self) -> None:
        activity = self.by_id("ACT-PH-08")
        self.assertEqual(activity["score_breakdown"]["outcome_alignment"]["raw"], 1.0)
        self.assertTrue(
            any("Supports approved outcome" in reason for reason in activity["reasons"])
        )

    def test_mastered_prerequisite_is_rewarded(self) -> None:
        activity = self.by_id("ACT-PH-03")
        self.assertEqual(activity["score_breakdown"]["prerequisite_readiness"]["raw"], 1.0)
        self.assertTrue(
            any("recorded as mastered" in reason for reason in activity["reasons"])
        )

    def test_weak_prerequisite_creates_warning(self) -> None:
        activity = self.by_id("ACT-PH-04")
        self.assertEqual(activity["score_breakdown"]["prerequisite_readiness"]["raw"], 0.0)
        self.assertTrue(
            any("gas exchange" in warning for warning in activity["warnings"])
        )

    def test_low_average_prioritises_scaffolded_activity(self) -> None:
        scaffolded = self.by_id("ACT-PH-02")
        challenge = self.by_id("ACT-PH-06")
        self.assertGreater(
            scaffolded["score_breakdown"]["previous_results_fit"]["raw"],
            challenge["score_breakdown"]["previous_results_fit"]["raw"],
        )

    def test_high_average_prioritises_challenge(self) -> None:
        high_request = replace(
            self.request,
            previous_results=PreviousResults(
                class_average=82.0,
                completion_rate=0.92,
                weak_topics=(),
                mastered_tags=("cells", "plants"),
            ),
        )
        high_ranked = self.ranker.rank(
            self.library.for_topic("Science", "Photosynthesis"),
            high_request,
            self.outcomes,
        )
        challenge = next(item for item in high_ranked if item["activity_id"] == "ACT-PH-06")
        scaffolded = next(item for item in high_ranked if item["activity_id"] == "ACT-PH-02")
        self.assertGreater(
            challenge["score_breakdown"]["previous_results_fit"]["raw"],
            scaffolded["score_breakdown"]["previous_results_fit"]["raw"],
        )
        self.assertTrue(
            any("adds challenge" in reason for reason in challenge["reasons"])
        )

    def test_weak_topic_alignment_is_explained(self) -> None:
        activity = self.by_id("ACT-PH-03")
        self.assertEqual(activity["score_breakdown"]["weak_topic_alignment"]["raw"], 0.5)
        self.assertTrue(
            any("Targets weak topic" in reason for reason in activity["reasons"])
        )

    def test_no_weak_topics_scores_zero_alignment(self) -> None:
        request = replace(
            self.request,
            previous_results=PreviousResults(
                class_average=58.0,
                completion_rate=0.72,
                weak_topics=(),
                mastered_tags=("cells", "plants"),
            ),
        )
        ranked = self.ranker.rank(
            self.library.for_topic("Science", "Photosynthesis"),
            request,
            self.outcomes,
        )
        self.assertTrue(
            all(
                item["score_breakdown"]["weak_topic_alignment"]["raw"] == 0.0
                for item in ranked
            )
        )

    def test_activity_without_outcome_gets_warning(self) -> None:
        activities = self.library.for_topic("Science", "Photosynthesis")
        modified = [replace(activities[0], supports_outcomes=())]
        ranked = self.ranker.rank(modified, self.request, self.outcomes)
        self.assertTrue(
            any("Does not directly support" in warning for warning in ranked[0]["warnings"])
        )

    def test_ranking_is_deterministic(self) -> None:
        second = self.ranker.rank(
            self.library.for_topic("Science", "Photosynthesis"),
            self.request,
            self.outcomes,
        )
        self.assertEqual(
            [(item["activity_id"], item["score"]) for item in self.ranked],
            [(item["activity_id"], item["score"]) for item in second],
        )

    def test_no_prerequisite_activity_scores_full_readiness(self) -> None:
        activity = self.by_id("ACT-PH-08")
        self.assertEqual(activity["score_breakdown"]["prerequisite_readiness"]["raw"], 1.0)
        self.assertTrue(
            any("No prerequisite tags" in reason for reason in activity["reasons"])
        )


if __name__ == "__main__":
    unittest.main()
